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
from qcos.api.posiq.routes_jsonrpc.routes import base_api
from qcos.common.config import Config
from qcos.common.constant import Constant

logger = logging.getLogger(__name__)


@base_api.method()
def version(
    body: schemas.GetVersionRequest = None
) -> schemas.GetVersionResponse:
    """
    Get server version

    :return: version response
    """
    logger.info(f"Call version: {body}")

    capabilities = {
        "job_types": Constant.JOB_TYPES,
        "job_sched_policy": Constant.JOB_SCHED_POLICIES,
        "transpilers": Constant.TRANSPILERS,
        "drivers": Constant.DRIVERS,
        "profiling": Constant.PROFILING_TYPES
    }

    response_info = {
        "version": Config.VERSION,
        "api_version": Config.API_VERSION_V1,
        "supported_api_versions": [
            {
                "version": Config.API_VERSION_V1,
                "status": "CURRENT"
            }
        ],
        "platform_version": Config.PLATFORM_VERSION,
        "capabilities": capabilities
    }
    return response_info
