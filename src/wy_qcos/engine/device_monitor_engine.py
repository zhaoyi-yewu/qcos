#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import json
import time
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FuturesTimeoutError,
)

import redis
from prefect import flow
from loguru import logger

from wy_qcos.common import args_schema
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.engine.common import init_logger
from wy_qcos.engine.job_engine import init_driver


def validate_device_info(device_info):
    """Validate device info.

    Args:
        device_info: device info
    """
    success, err_msgs = Library.validate_schema(
        device_info, args_schema.DEVICE_INFO_SCHEMA, allow_none=True
    )
    if not success:
        logger.warning(f"Invalid device info. Reason: {'; '.join(err_msgs)}")


@flow(
    persist_result=False,
    retries=Constant.DEFAULT_DEVICE_MONITOR_RETRIES,
    retry_delay_seconds=Constant.DEFAULT_DEVICE_MONITOR_RETRY_DELAY_INTERVAL,
)
def device_monitor_flow(device_monitor_info):
    """Device monitor flow.

    Args:
        device_monitor_info: device info

    Returns:
        None
    """
    device_name = device_monitor_info["name"]
    device = device_monitor_info["device"]
    device_configs = device["configs"]
    global_configs = device_monitor_info["global"]["configs"]

    # polling interval: read from [device.device_monitor] config table,
    # fall back to the default constant when not configured.
    device_monitor_configs = device_configs.get("device_monitor", {})
    polling_interval = device_monitor_configs.get(
        "polling_interval",
        Constant.DEFAULT_DEVICE_MONITOR_POLLING_INTERVAL,
    )

    # init logger
    debug = global_configs.get("DEBUG", False)
    if "debug" in device_configs:
        debug = device_configs["debug"]
    device_monitor_log_file = f"/var/log/qcos/device_monitor_{device_name}.log"
    # monitor_log_file now lives under the [device.device_monitor]
    # sub-table; fall back to the top-level key for backward
    # compatibility.

    if "monitor_log_file" in device_monitor_configs:
        device_monitor_log_file = device_monitor_configs["monitor_log_file"]

    # Extract logging configuration parameters
    log_format = device_configs.get("log_format")
    log_rotate_max_size_mb = device_configs.get("log_rotate_max_size_mb")
    log_rotate_backup_count = device_configs.get("log_rotate_backup_count")
    log_rotate_compression = device_configs.get("log_rotate_compression")

    init_logger(
        log_file_path=device_monitor_log_file,
        debug=debug,
        log_format=log_format,
        log_rotate_max_size_mb=log_rotate_max_size_mb,
        log_rotate_backup_count=log_rotate_backup_count,
        log_rotate_compression=log_rotate_compression,
    )
    logger.info(
        f"Processing device monitor flow: job_engine. "
        f"device_name: {device_name}"
    )

    # init driver
    future_driver = init_driver.submit(
        driver_class_info=device_monitor_info["driver"],
        device=device,
    )
    driver_task_result = future_driver.result()
    # init driver: error handling
    err_msg = driver_task_result.get("error", None)
    if err_msg:
        raise ValueError(str(err_msg))
    driver = driver_task_result["driver"]

    # generate redis instance
    redis_instance = redis.Redis(
        host=device_monitor_info["redis"]["ip"],
        port=device_monitor_info["redis"]["port"],
        decode_responses=True,
    )

    # set init device status
    device_running_info = {
        "status": Device.DEVICE_STATUS_UNKNOWN,
        "available_qubits": None,
    }
    device_info_json = json.dumps(device_running_info)
    channel_name = (
        f"{Constant.REDIS_CHANNEL_DEVICE_RUNNING_INFO_PREFIX}/{device_name}"
    )
    redis_instance.publish(channel_name, device_info_json)

    # poll device running info periodically (in {polling_interval} secs)
    fetch_timeout = Constant.DEFAULT_DEVICE_MONITOR_FETCH_TIMEOUT
    while True:
        # get running device info by driver with a timeout
        # to avoid long hangs when the device is unreachable
        device_running_info = {}
        disconnected = True
        # NOTE: ThreadPoolExecutor workers cannot be forcibly killed.
        # future.result(timeout=...) only abandons the wait while the
        # underlying thread keeps running. Exiting a
        # `with ThreadPoolExecutor(...)` block calls shutdown(wait=True)
        # which blocks until the worker finishes, effectively negating
        # the timeout. We therefore manage the executor manually and
        # shut it down without waiting so a hung device call does not
        # block the monitor loop.
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(driver.fetch_running_info)
            device_running_info = future.result(timeout=fetch_timeout)
            disconnected = False
            if (
                device_running_info.get("status")
                == Device.DEVICE_STATUS_DISCONNECTED
            ):
                disconnected = True
        except FuturesTimeoutError:
            logger.error(
                f"[{device_name}] fetch_running_info timed out after "
                f"{fetch_timeout}s, treating as disconnected"
            )
            disconnected = True
        except Exception as e:
            logger.error(f"Fail to fetch running info. exception: {e}")
            disconnected = True
        finally:
            # do not wait (wait=False) for the possibly hung worker
            # thread, otherwise the loop blocks here until the device
            # call eventually returns.
            executor.shutdown(wait=False)

        # set updated time
        current_ts = Library.get_current_datetime(timestamp=True)
        device_running_info["last_updated_at"] = Library.to_iso(current_ts)
        if disconnected:
            # when connection fails, publish disconnected status
            device_running_info["status"] = Device.DEVICE_STATUS_DISCONNECTED
            device_running_info["available_qubits"] = None
        else:
            # validate device_info schema
            validate_device_info(device_running_info)

        # convert device info to json format and publish by redis
        device_info_json = json.dumps(device_running_info)
        channel_name = (
            f"{Constant.REDIS_CHANNEL_DEVICE_RUNNING_INFO_PREFIX}/"
            f"{device_name}"
        )
        redis_instance.publish(channel_name, device_info_json)
        time.sleep(polling_interval)
