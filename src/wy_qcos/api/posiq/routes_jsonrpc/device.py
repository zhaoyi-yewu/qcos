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
import time

from fastapi import Depends

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import device_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.db.utils.db_utils import get_repository
from wy_qcos.task_manager import scheduler
from .dependencies.authentication import auth, validate_virtual_instance

logger = logging.getLogger(__name__)
module_name = "DEVICE"


def _get_job_count(device_name, job_repo=None):
    """Get job count grouped by job status for a device.

    Uses a single GROUP BY query (count_by_status) instead of N
    separate COUNT queries so the job table is scanned only once.

    Args:
        device_name: device name (matches job.backend column)
        job_repo: JobRepository instance. When None or not a real
            repository, returns empty dict to avoid blocking device
            queries when the database is unavailable.

    Returns:
        dict mapping each job status in Constant.JOB_STATUSES to
        its count for the given device, plus a TOTAL entry that
        sums all statuses.
    """
    job_count = {status: 0 for status in Constant.JOB_STATUSES}
    if not isinstance(job_repo, JobRepository):
        job_count[Constant.JOB_STATUS_TOTAL] = 0
        return job_count
    try:
        counts = job_repo.count_by_status(device_name)
    except Exception as e:
        logger.warning(f"Failed to get job counts for {device_name}: {e}")
        job_count[Constant.JOB_STATUS_TOTAL] = 0
        return job_count
    # Fill in statuses present in the database; others stay 0
    total = 0
    for status, count in counts.items():
        job_count[status] = count
        total += count
    job_count[Constant.JOB_STATUS_TOTAL] = total
    return job_count


def _get_device_info(device, auth_data=None, details=False, job_repo=None):
    """Get device info.

    Args:
        device: device
        auth_data: authentication data
        details: need detail information or not
        job_repo: JobRepository instance for querying job counts.
            When None, job_count is an empty dict.

    Returns:
        device_info
    """
    last_updated_at = None
    if device.last_updated_at:
        last_updated_at = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(last_updated_at)
        )
    _device_info = {
        "name": device.name,
        "alias_name": device.alias_name,
        "description": device.description,
        "driver_name": device.driver.get_name(),
        "enable": device.enable,
        "status": device.status,
        "tech_type": device.tech_type,
        "max_qubits": device.max_qubits,
        "details": device.details,
        "last_updated_at": last_updated_at,
        "job_count": _get_job_count(device.name, job_repo),
    }
    if not details:
        _device_info.pop("details")

    return _device_info


@device_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES}, errors=[]
)
def get_devices(
    body: schemas.GetDevicesRequest | None = None,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> dict[str, schemas.GetDeviceResponse]:
    """Get device dict request.

    Args:
        body(schemas.GetDevicesRequest): devices request
        auth_data: auth data
        job_repo: JobRepository instance for querying job counts

    Returns:
        Get devices response
    """
    func_name = "get_devices"
    logger.info(f"Call {func_name}: {body}")

    device_manager = scheduler.get_device_manager()
    devices = device_manager.get_devices()
    response_info = {}
    for device_name, device in sorted(devices.items()):
        success, _ = validate_virtual_instance(auth_data, backend=device_name)
        if not success:
            continue
        _response_info = _get_device_info(device, auth_data, job_repo=job_repo)
        response_info[device_name] = schemas.GetDeviceResponse.model_validate(
            _response_info
        )
    return response_info


@device_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_device(
    body: schemas.GetDeviceRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> schemas.GetDeviceResponse:
    """Get device info request.

    Args:
        body(schemas.GetDeviceRequest): device name
        auth_data: auth data
        job_repo: JobRepository instance for querying job counts

    Returns:
        Get device info response
    """
    func_name = "get_device"
    logger.info(f"Call {func_name}: {body}")

    device_name = body.name
    device_manager = scheduler.get_device_manager()
    device = device_manager.get_device(device_name)
    if device is None:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )
    success, _ = validate_virtual_instance(auth_data, backend=device_name)
    if not success:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )
    _response_info = _get_device_info(
        device, auth_data, body.details, job_repo=job_repo
    )
    response_info = schemas.GetDeviceResponse.model_validate(_response_info)
    return response_info


@device_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def calibrate_device(
    body: schemas.CalibrateDeviceRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.CalibrateDeviceResponse:
    """Calibrate device.

    Args:
        body(schemas.CalibrateDeviceRequest): CalibrateDeviceRequest body
        auth_data: auth data
    """
    func_name = "calibrate_device"
    logger.info(f"Call {func_name}: {body}")

    body.method = func_name
    details = scheduler.submit_manage_job(body)
    _response_info = {"details": details}
    response_info = schemas.CalibrateDeviceResponse.model_validate(
        _response_info
    )
    return response_info


@device_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_calibrate_results(
    body: schemas.GetCalibrateResultRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetCalibrateResultResponse:
    """Get Calibrate result.

    Args:
        body(schemas.GetCalibrateResultRequest): GetCalibrateResultRequest body
        auth_data: auth data
    """
    func_name = "get_calibrate_results"
    logger.info(f"Call {func_name}: {body}")

    device_manager = scheduler.get_device_manager()
    device = device_manager.get_device(body.device_name)
    if not device:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{body.device_name}' is not found"),
        )
    _response_info = {"details": device.calibrate_info}
    response_info = schemas.GetCalibrateResultResponse.model_validate(
        _response_info
    )
    return response_info


@device_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def set_device_options(
    body: schemas.SetDeviceOptionsRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.SetDeviceOptionsResponse:
    """Set device Options request.

    Args:
        body(schemas.SetDeviceOptionsRequest): SetDeviceOptionsRequest body
        auth_data: auth data

    Returns:
        Set device Options response
    """
    func_name = "set_device_options"
    logger.info(f"Call {func_name}: {body}")
    body.method = func_name
    details = scheduler.submit_manage_job(body)
    _response_info = {"details": details}
    response_info = schemas.SetDeviceOptionsResponse.model_validate(
        _response_info
    )
    return response_info


@device_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_device_options(
    body: schemas.GetDeviceOptionsRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetDeviceOptionsResponse:
    """Get device Options request.

    Args:
        body(schemas.GetDeviceOptionsRequest): GetDeviceOptionsRequest body
        auth_data: auth data

    Returns:
        Set device Options response
    """
    func_name = "get_device_options"
    logger.info(f"Call {func_name}: {body}")
    body.method = func_name
    device_manager = scheduler.get_device_manager()
    device = device_manager.get_device(body.device_name)
    if not device:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{body.device_name}' is not found"),
        )
    _response_info = {"details": device.device_options_info}
    response_info = schemas.GetDeviceOptionsResponse.model_validate(
        _response_info
    )
    return response_info


@device_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def set_device_maintain_mode(
    body: schemas.SetDeviceMaintainModeRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.SetDeviceMaintainModeResponse:
    """Set device maintain mode.

    Args:
        body: SetDeviceMaintainModeRequest body
        auth_data: auth data

    Returns:
        Set device maintain mode response
    """
    func_name = "set_device_maintain_mode"
    logger.info(f"Call {func_name}: {body}")

    device_name = body.device_name
    mode = body.mode

    device_manager = scheduler.get_device_manager()
    device = device_manager.get_device(device_name)
    if device is None:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Device: '{device_name}' is not found"),
        )

    if mode == "on":
        device.set_manual_maintain_mode(True)
        device.set_status(device.DEVICE_STATUS_MAINTAIN)
    elif mode == "off":
        device.set_manual_maintain_mode(False)
        device.set_status(device.DEVICE_STATUS_ONLINE)
    else:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Invalid mode: '{mode}'. Must be 'on' or 'off'"),
        )

    _response_info = {
        "name": device.name,
        "status": device.status,
    }
    response_info = schemas.SetDeviceMaintainModeResponse.model_validate(
        _response_info
    )
    return response_info
