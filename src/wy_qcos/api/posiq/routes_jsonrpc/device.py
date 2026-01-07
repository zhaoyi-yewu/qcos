#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from fastapi import Depends

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import device_api_v1
from wy_qcos.common.library import Library
from wy_qcos.task_manager import scheduler
from .dependencies.authentication import auth

logger = logging.getLogger(__name__)
module_name = "DEVICE"


def _get_device_info(device_info, auth_data=None):
    """Get device info.

    Args:
        device_info: device info
        auth_data: authentication data

    Returns:
        device_info
    """
    # replace pwd in extra_configs to ********
    configs = Library.mask_password(device_info.configs)
    _device_info = {
        "name": device_info.name,
        "alias_name": device_info.alias_name,
        "description": device_info.description,
        "driver_name": device_info.driver.get_name(),
        "enable": device_info.enable,
        "status": device_info.status,
        "tech_type": device_info.tech_type,
        "max_qubits": device_info.max_qubits,
        "configs": configs,
    }
    if auth_data is not None:
        # only admin user can access to config info
        # remove config info in device_info for non-admin user
        _device_info.pop("configs")
    return _device_info


@device_api_v1.method(errors=[])
def get_devices(
    body: schemas.GetDevicesRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.GetDeviceResponse]:
    """Get device dict request.

    Args:
        body(schemas.GetDevicesRequest): devices request
        auth_data: auth data

    Returns:
        Get devices response
    """
    func_name = "get_devices"
    logger.info(f"Call {func_name}: {body}")

    device_manager = scheduler.get_device_manager()
    devices = device_manager.get_devices()
    response_info = {}
    for device_name, device_info in sorted(devices.items()):
        if auth_data is not None:
            if device_name not in auth_data["device_names"]:
                continue
        _response_info = _get_device_info(device_info, auth_data)
        response_info[device_name] = schemas.GetDeviceResponse.model_validate(
            _response_info
        )
    return response_info


@device_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def get_device(
    body: schemas.GetDeviceRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetDeviceResponse:
    """Get device info request.

    Args:
        body(schemas.GetDeviceRequest): device name
        auth_data: auth data

    Returns:
        Get device info response
    """
    func_name = "get_device"
    logger.info(f"Call {func_name}: {body}")

    device_name = body.name

    device_manager = scheduler.get_device_manager()
    device_info = device_manager.get_device(device_name)
    if auth_data is not None:
        if device_name not in auth_data["device_names"]:
            device_info = None
    if not device_info:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )
    _response_info = _get_device_info(device_info, auth_data)
    response_info = schemas.GetDeviceResponse.model_validate(_response_info)
    return response_info
