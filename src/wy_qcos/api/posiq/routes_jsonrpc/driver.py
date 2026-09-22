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
from wy_qcos.api.posiq.routes_jsonrpc.routes import driver_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.pagination import (
    apply_memory_filters,
    apply_memory_sort,
    paginate_list,
    parse_query,
)
from wy_qcos.task_manager import scheduler
from .dependencies.authentication import auth

logger = logging.getLogger(__name__)
module_name = "DRIVER"


def _get_driver_info(driver, transpiler):
    """Get driver info.

    Args:
        driver: driver
        transpiler: transpiler instance

    Returns:
        device_info
    """
    supported_code_types = []
    if transpiler:
        supported_code_types = transpiler.get_supported_code_types()
    if supported_code_types is None or len(supported_code_types) == 0:
        supported_code_types = driver.get_supported_code_types()
    driver.set_supported_code_types(supported_code_types)
    _driver_info = {
        "name": driver.get_class_name(),
        "alias_name": driver.alias_name,
        "version": driver.version,
        "description": driver.get_description(),
        "tech_type": driver.tech_type,
        "max_qubits": driver.get_max_qubits(),
        "transpiler": driver.get_transpiler(),
        "supported_transpilers": driver.supported_transpilers,
        "enable_circuit_aggregation": driver.enable_circuit_aggregation,
        "supported_code_types": supported_code_types,
        "supported_basis_gates": driver.get_supported_basis_gates(),
        "results_fetch_mode": driver.results_fetch_mode,
    }
    return _driver_info


@driver_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[],
)
def get_drivers(
    body: schemas.GetDriversRequest | None = None,
    query: dict | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.GetDriverResponse] | schemas.PaginatedResponse:
    """Get driver dict request with optional pagination.

    Args:
        body(schemas.GetDriversRequest): message
        query: dict containing optional filters, pagination, and sort
        auth_data: auth data

    Returns:
        Get drivers response, or PaginatedResponse when pagination is provided
    """
    func_name = "get_drivers"
    logger.info(f"Call {func_name}: body={body}, query={query}")

    # Extract filters/pagination/sort from query dict
    filters, pagination, sort = parse_query(query)

    driver_manager = scheduler.get_driver_manager()
    drivers = driver_manager.get_drivers()
    response_info = {}
    for driver_name, driver in drivers.items():
        transpiler_manager = scheduler.get_transpiler_manager()
        transpiler = transpiler_manager.get_transpiler(driver.transpiler)
        _response_info = _get_driver_info(driver, transpiler)
        response_info[driver_name] = schemas.GetDriverResponse.model_validate(
            _response_info
        )
    items = list(response_info.values())
    if filters:
        items = apply_memory_filters(items, filters)
        # Rebuild dict with only filtered items
        response_info = {getattr(item, "name", ""): item for item in items}
    if sort:
        items = apply_memory_sort(items, sort)
        response_info = {getattr(item, "name", ""): item for item in items}
    if pagination:
        return paginate_list(items, pagination.page, pagination.page_size)
    return response_info


@driver_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_driver(
    body: schemas.GetDriverRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetDriverResponse:
    """Get driver info request.

    Args:
        body(schemas.GetDriverRequest): driver_name
        auth_data: auth data

    Returns:
        Get driver info response
    """
    func_name = "get_driver"
    logger.info(f"Call {func_name}: {body}")

    driver_name = body.name

    driver_manager = scheduler.get_driver_manager()
    driver = driver_manager.get_driver(driver_name)
    if not driver:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Driver: '{driver_name}' is not found"),
        )
    transpiler_manager = scheduler.get_transpiler_manager()
    transpiler = transpiler_manager.get_transpiler(driver.transpiler)
    _response_info = _get_driver_info(driver, transpiler)
    response_info = schemas.GetDriverResponse.model_validate(_response_info)
    return response_info
