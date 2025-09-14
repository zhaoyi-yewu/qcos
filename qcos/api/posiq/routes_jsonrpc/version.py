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
from qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
module_name = "VERSION"


@base_api.method()
def version(
    body: schemas.GetVersionRequest = None
) -> schemas.GetVersionResponse:
    """Get server version

    Args:
        body: schemas.GetVersionRequest:  (Default value = None)
    """
    func_name = "version"
    logger.info(f"Call {func_name}: {body}")

    driver_name_mapping = {}
    transpiler_name_mappings = {}
    driver_transpiler_mappings = {}
    driver_manager = scheduler.get_driver_manager()
    drivers = driver_manager.get_drivers()
    transpiler_manager = scheduler.get_transpiler_manager()
    for driver_name, driver in drivers.items():
        driver_name_mapping[driver_name] = {
            "enable_transpiler": driver.enable_transpiler,
            "supported_code_types": driver.get_supported_code_types(),
            "description": driver.get_description()
        }
        if driver_name not in driver_transpiler_mappings:
            driver_transpiler_mappings[driver_name] = set()
        transpiler_names = driver.get_supported_transpilers()
        for transpiler_name in transpiler_names:
            if transpiler_name not in transpiler_name_mappings:
                transpiler = transpiler_manager.get_transpiler(transpiler_name)
                transpiler_alias_name = transpiler.get_alias_name()
                supported_code_types = transpiler.get_supported_code_types()
                transpiler_name_mappings[transpiler_name] = {
                    "alias_name": transpiler_alias_name,
                    "supported_code_types": supported_code_types
                }
            driver_transpiler_mappings[driver_name].add(transpiler_name)

    capabilities = {
        "job_types": Constant.JOB_TYPES,
        "job_sched_policy": Constant.JOB_SCHED_POLICIES,
        "drivers": driver_name_mapping,
        "transpilers": transpiler_name_mappings,
        "tech_types": Constant.TECH_TYPE_INFO,
        "profiling": Constant.PROFILING_INFO,
        "driver_transpiler_mappings": driver_transpiler_mappings
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
