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


from prefect import flow
from loguru import logger

from wy_qcos.engine.common import init_logger
from wy_qcos.engine.job_engine import init_driver


def call_device_method(driver, method, *args, **kwargs):
    """Dynamic call method in driver.

    :param driver: driver
    :param method: the method called
    :param args: args
    :param kwargs: kwargs

    :return: results
    """
    if hasattr(driver, method):
        method_func = getattr(driver, method)
        results = method_func(*args, **kwargs)
        return results
    else:
        raise AttributeError(f"driver has no {method} method")


@flow(
    persist_result=False,
)
def device_manager_flow(device_mgr_info):
    """Device manager flow.

    Args:
        device_mgr_info: device manager info

    Returns:
        None
    """
    data = device_mgr_info["data"]
    device_name = data["device_name"]
    device = device_mgr_info["device"]

    device_configs = device["configs"]
    global_configs = device_mgr_info["global"]["configs"]

    # init logger
    debug = global_configs.get("DEBUG", False)
    if "debug" in device_configs:
        debug = device_configs["debug"]
    log_file = f"/var/log/qcos/device_mgr_{device_name}.log"
    if "device_log_file" in device_configs:
        log_file = device_configs["mgr_log_file"]
    init_logger(log_file_path=log_file, debug=debug)
    logger.info(f"Processing device manage flow:device_name: {device_name}")

    # init driver
    future_driver = init_driver.submit(
        driver_class_info=device_mgr_info["driver"],
        device=device,
    )
    driver_task_result = future_driver.result()
    # init driver: error handling
    err_msg = driver_task_result.get("error", None)
    if err_msg:
        raise ValueError(str(err_msg))
    driver = driver_task_result["driver"]
    method_str = data["method"]
    results = call_device_method(driver, method_str, device_mgr_info["data"])
    return results
