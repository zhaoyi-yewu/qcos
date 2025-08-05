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

from qcos.api import schemas
from qcos.api.posiq.routes_jsonrpc.routes import system_api_v1

logger = logging.getLogger(__name__)
module_name = "SYSTEM"


@system_api_v1.method()
def ping(
        body: schemas.PingRequest
) -> schemas.PongResponse:
    """
    Ping-pong to verify the availability of the system

    :param body: message
    :type body: schemas.PingRequest
    :return: pong response
    """
    module_name = "ping"
    logger.info(f"Call {module_name}: {body}")

    message = body.message

    response_info = {
        "message": message,
    }
    return response_info
