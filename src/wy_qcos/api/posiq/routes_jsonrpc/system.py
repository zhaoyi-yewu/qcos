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
from wy_qcos.api.posiq.routes_jsonrpc.routes import system_api_v1
from wy_qcos.common import errors
from wy_qcos.common.constant import Constant
from wy_qcos.task_manager import scheduler
from .dependencies.authentication import auth

logger = logging.getLogger(__name__)
module_name = "SYSTEM"


@system_api_v1.method()
def ping(body: schemas.PingRequest) -> schemas.PongResponse:
    """Ping-pong to verify the availability of the system.

    Args:
        body(schemas.PingRequest): message

    Returns:
        pong response
    """
    func_name = "ping"
    logger.info(f"Call {func_name}: {body}")

    message = body.message

    _response_info = {"message": message}
    response_info = schemas.PongResponse.model_validate(_response_info)
    return response_info


@system_api_v1.method()
def system_info(
    body: schemas.SystemInfoRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.SystemInfoResponse:
    """Get system info.

    Args:
        body(schemas.SystemInfoRequest): System Info Request
        auth_data: auth data

    Returns:
        system info response
    """
    func_name = "system_info"
    logger.info(f"Call {func_name}: {body}")

    # query jobs' results
    responses = []
    try:
        tags = None
        if auth_data is not None:
            virtual_instance_id = auth_data["instance_id"]
            tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
        responses, err = scheduler.get_jobs(tags=tags)
    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    total_jobs_count = len(responses)

    _response_info = {"total_jobs_count": total_jobs_count}
    response_info = schemas.SystemInfoResponse.model_validate(_response_info)
    return response_info
