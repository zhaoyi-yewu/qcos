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

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import driver_api_v1
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
module_name = "DRIVER"


def _get_driver_info(driver_info, transpiler):
    """Get driver info.

    Args:
        driver_info: driver_info
        transpiler: transpiler instance

    Returns:
        device_info
    """
    supported_code_types = None
    if transpiler:
        supported_code_types = transpiler.get_supported_code_types()
    else:
        supported_code_types = driver_info.get_supported_code_types()
    _driver_info = {
        "name": driver_info.get_class_name(),
        "alias_name": driver_info.alias_name,
        "version": driver_info.version,
        "description": driver_info.get_description(),
        "tech_type": driver_info.tech_type,
        "max_qubits": driver_info.get_max_qubits(),
        "transpiler": driver_info.get_transpiler(),
        "enable_transpiler": driver_info.enable_transpiler,
        "supported_transpilers": driver_info.supported_transpilers,
        "enable_circuit_aggregation": driver_info.enable_circuit_aggregation,
        "supported_code_types": supported_code_types,
        "supported_basis_gates": driver_info.get_supported_basis_gates(),
        "results_fetch_mode": driver_info.results_fetch_mode,
    }
    return _driver_info


@driver_api_v1.method(errors=[])
def get_drivers(
    body: schemas.GetDriversRequest | None = None,
) -> dict[str, schemas.GetDriverResponse]:
    """Get driver dict request.

    Args:
        body(schemas.GetDriversRequest): message

    Returns:
        Get drivers response
    """
    func_name = "get_drivers"
    logger.info(f"Call {func_name}: {body}")

    driver_manager = scheduler.get_driver_manager()
    drivers = driver_manager.get_drivers()
    response_info = {}
    for driver_name, driver_info in drivers.items():
        transpiler_manager = scheduler.get_transpiler_manager()
        transpiler = transpiler_manager.get_transpiler(driver_info.transpiler)
        _response_info = _get_driver_info(driver_info, transpiler)
        response_info[driver_name] = schemas.GetDriverResponse.model_validate(
            _response_info
        )
    return response_info


@driver_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def get_driver(body: schemas.GetDriverRequest) -> schemas.GetDriverResponse:
    """Get driver info request.

    Args:
        body(schemas.GetDriverRequest): driver_name

    Returns:
        Get driver info response
    """
    func_name = "get_driver"
    logger.info(f"Call {func_name}: {body}")

    driver_name = body.name

    driver_manager = scheduler.get_driver_manager()
    driver_info = driver_manager.get_driver(driver_name)
    if not driver_info:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Driver: '{driver_name}' is not found"),
        )
    transpiler = None
    if driver_info.enable_transpiler:
        transpiler_manager = scheduler.get_transpiler_manager()
        transpiler = transpiler_manager.get_transpiler(driver_info.transpiler)
    _response_info = _get_driver_info(driver_info, transpiler)
    response_info = schemas.GetDriverResponse.model_validate(_response_info)
    return response_info
