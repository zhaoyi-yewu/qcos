#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import logging
from typing import List

from qcos.api import schemas
from qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from qcos.api.posiq.routes_jsonrpc.routes import device_api_v1
from qcos.common.library import Library
from qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
module_name = "DEVICE"


def _get_device_info(driver_info, transpiler):
    """
    Get device info

    :param driver_info: driver_info
    :param transpiler: transpiler instance
    :return: device_info
    """

    supported_code_types = None
    if transpiler:
        supported_code_types = transpiler.get_supported_code_types()
    else:
        supported_code_types = driver_info.get_supported_code_types()
    device_info = {
        "name": driver_info.name,
        "version": driver_info.version,
        "driver": driver_info.get_class_name(),
        "description": Library.get_brief_description(driver_info.__doc__),
        "enable": driver_info.enable,
        "status": driver_info.get_status(),
        "tech_type": driver_info.tech_type,
        "max_qubits": driver_info.get_max_qubits(),
        "transpiler": driver_info.get_transpiler(),
        "enable_transpiler": driver_info.enable_transpiler,
        "supported_transpilers": driver_info.supported_transpilers,
        "enable_circuit_aggregation": driver_info.enable_circuit_aggregation,
        "supported_code_types": supported_code_types,
        "supported_basis_gates": driver_info.get_supported_basis_gates(),
        "results_fetch_mode": driver_info.results_fetch_mode,
        # replace pwd in extra_configs to ********
        "extra_configs": Library.update_dict(driver_info.extra_configs,
                                             {"password": "*" * 8})
    }
    return device_info


@device_api_v1.method(errors=[])
def get_devices(
        body: schemas.GetDevicesRequest = None
) -> List[schemas.GetDeviceResponse]:
    """
    Get device list request

    :param body: message
    :type body: schemas.GetDevicesRequest
    :return: Get devices response
    """
    func_name = "get_devices"
    logger.info(f"Call {func_name}: {body}")

    driver_manager = scheduler.get_driver_manager()
    drivers = driver_manager.get_drivers()
    response_info = []
    for _, driver_info in sorted(drivers.items()):
        transpiler_manager = scheduler.get_transpiler_manager()
        transpiler = transpiler_manager.get_transpiler(driver_info.transpiler)
        device_info = _get_device_info(driver_info, transpiler)
        response_info.append(device_info)
    return response_info


@device_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def get_device(
        body: schemas.GetDeviceRequest
) -> schemas.GetDeviceResponse:
    """
    Get device info request

    :param body: driver_name
    :type body: schemas.GetDeviceRequest
    :return: Get device info response
    """
    func_name = "get_device"
    logger.info(f"Call {func_name}: {body}")

    driver_name = body.name

    driver_manager = scheduler.get_driver_manager()
    driver_info = driver_manager.get_driver(driver_name)
    if not driver_info:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{driver_name}' is not found")
        )
    transpiler_manager = scheduler.get_transpiler_manager()
    transpiler = transpiler_manager.get_transpiler(driver_info.transpiler)
    response_info = _get_device_info(driver_info, transpiler)
    return response_info
