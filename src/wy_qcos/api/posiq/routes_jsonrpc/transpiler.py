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
from wy_qcos.api.posiq.routes_jsonrpc.routes import transpiler_api_v1
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
module_name = "TRANSPILER"


def _get_transpiler_info(transpiler_info):
    """Get transpiler info.

    Args:
        transpiler_info: transpiler info

    Returns:
        transpiler_info
    """
    _transpiler_info = {
        "name": transpiler_info.name,
        "alias_name": transpiler_info.alias_name,
        "version": transpiler_info.get_version(),
        "enable": transpiler_info.enable,
        "supported_code_types": transpiler_info.supported_code_types,
    }
    return _transpiler_info


@transpiler_api_v1.method(errors=[])
def get_transpilers(
    body: schemas.GetTranspilersRequest | None = None,
) -> dict[str, schemas.GetTranspilerResponse]:
    """Get transpiler list request.

    Args:
        body(schemas.GetTranspilersRequest): message

    Returns:
        Get transpilers response
    """
    func_name = "get_transpilers"
    logger.info(f"Call {func_name}: {body}")

    transpiler_manager = scheduler.get_transpiler_manager()
    transpilers = transpiler_manager.get_transpilers()
    response_info = {}
    for transpiler_name, transpiler_info in sorted(transpilers.items()):
        _response_info = _get_transpiler_info(transpiler_info)
        response_info[transpiler_name] = (
            schemas.GetTranspilerResponse.model_validate(_response_info)
        )
    return response_info


@transpiler_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def get_transpiler(
    body: schemas.GetTranspilerRequest,
) -> schemas.GetTranspilerResponse:
    """Get transpiler info request.

    Args:
        body(schemas.GetTranspilerRequest): driver_name

    Returns:
        Get transpiler info response
    """
    func_name = "get_transpiler"
    logger.info(f"Call {func_name}: {body}")

    transpiler_name = body.name

    transpiler_manager = scheduler.get_transpiler_manager()
    transpiler_info = transpiler_manager.get_transpiler(transpiler_name)
    if not transpiler_info:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Transpiler: '{transpiler_name}' is not found"),
        )
    _response_info = _get_transpiler_info(transpiler_info)
    response_info = schemas.GetTranspilerResponse.model_validate(
        _response_info
    )
    return response_info
