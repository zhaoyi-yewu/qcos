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


def _get_device_info(device, auth_data=None, details=False):
    """Get device info.

    Args:
        device: device
        auth_data: authentication data
        details: need detail information or not

    Returns:
        device_info
    """
    # replace pwd in extra_configs to ********
    configs = Library.mask_password(device.configs)
    _device_info = {
        "name": device.name,
        "alias_name": device.alias_name,
        "description": device.description,
        "driver_name": device.driver.get_name(),
        "enable": device.enable,
        "status": device.status,
        "tech_type": device.tech_type,
        "max_qubits": device.max_qubits,
        "configs": configs,
        "details": device.details,
    }
    if auth_data is not None:
        # only admin user can access to config info
        # remove config info in device_info for non-admin user
        _device_info.pop("configs")
    if details is False:
        _device_info.pop("details")

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
    for device_name, device in sorted(devices.items()):
        if auth_data is not None:
            if device_name not in auth_data["device_names"]:
                continue
        _response_info = _get_device_info(device, auth_data)
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
    device = device_manager.get_device(device_name)
    if auth_data is not None:
        if device_name not in auth_data["device_names"]:
            device = None
    if not device:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )
    _response_info = _get_device_info(device, auth_data, body.details)
    response_info = schemas.GetDeviceResponse.model_validate(_response_info)
    return response_info


@device_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def calibrate(
    body: schemas.CalibrateDeviceRequest,
    auth_data: dict | None = Depends(auth),
):
    """Calibrate device.

    Args:
        body(schemas.CalibrateDeviceRequest): device name
        auth_data: auth data
    """
    func_name = "calibrate"
    logger.info(f"Call {func_name}: {body}")

    device_name = body.device_name
    device_manager = scheduler.get_device_manager()
    device = device_manager.get_device(device_name)
    if auth_data is not None:
        if device_name not in auth_data["device_names"]:
            device = None
    if not device:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )
    driver = device.get_driver()
    driver.calibrate(body.options)
    device.set_status(device.DEVICE_STATUS_CALIBRATING)


@device_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def set_device_options(
    body: schemas.SetDeviceOptionsRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.SetDeviceOptionsResponse:
    """Set device Options request.

    Args:
        body(schemas.SetDeviceOptionsRequest): device name
        auth_data: auth data

    Returns:
        Set device Options response
    """
    func_name = "set_device_options"
    logger.info(f"Call {func_name}: {body}")

    device_name = body.device_name
    device_manager = scheduler.get_device_manager()
    device = device_manager.get_device(device_name)
    if auth_data is not None:
        if device_name not in auth_data["device_names"]:
            device = None
    if not device:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )
    driver = device.get_driver()
    _response_info = driver.set_device_options(body.device_options)
    response_info = schemas.SetDeviceOptionsResponse.model_validate(
        _response_info
    )
    return response_info


@device_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def enable_and_disable_qubit(
    body: schemas.EnableAndDisableQubitRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.EnableAndDisableQubitResponse:
    """Enable and Disable Qubit request.

    Args:
        body(schemas.EnableAndDisableQubitRequest): device name
        auth_data: auth data

    Returns:
        Enable and Disable Qubit response
    """
    func_name = "enable_and_disable_qubit"
    logger.info(f"Call {func_name}: {body}")

    device_name = body.device_name
    device_manager = scheduler.get_device_manager()
    device = device_manager.get_device(device_name)
    if auth_data is not None:
        if device_name not in auth_data["device_names"]:
            device = None
    if not device:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )
    driver = device.get_driver()
    _response_info = driver.enable_and_disable_qubit(body.qubits)
    response_info = schemas.EnableAndDisableQubitResponse.model_validate(
        _response_info
    )
    return response_info
