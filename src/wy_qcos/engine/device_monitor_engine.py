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

import redis
from prefect import flow
from loguru import logger

from wy_qcos.common.constant import Constant
from wy_qcos.engine.common import init_logger
from wy_qcos.engine.job_engine import init_driver


@flow(
    persist_result=False,
    retries=Constant.DEFAULT_DEVICE_MONITOR_RETRIES,
    retry_delay_seconds=Constant.DEFAULT_DEVICE_MONITOR_RETRY_INTERVAL,
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

    # init logger
    debug = global_configs.get("DEBUG", False)
    if "debug" in device_configs:
        debug = device_configs["debug"]
    device_monitor_log_file = f"/var/log/qcos/device_monitor_{device_name}.log"
    if "monitor_log_file" in device_configs:
        device_monitor_log_file = device_configs["monitor_log_file"]

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

    while True:
        # get running device info by driver
        try:
            device_info = driver.fetch_running_info()
        except Exception as e:
            logger.error(f"Fail to fetch running info. exception: {e}")
            time.sleep(Constant.DEFAULT_DEVICE_MONITOR_INTERVAL)
            continue
        device_info["timestamp"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime()
        )
        device_info_json = json.dumps(device_info)

        # publish device info by redis
        channel_name = (
            device_name + Constant.DEVICE_RUNNING_INFO_REDIS_CHANNEL_SUFFIX
        )
        redis_instance.publish(channel_name, device_info_json)

        time.sleep(Constant.DEFAULT_DEVICE_MONITOR_INTERVAL)
