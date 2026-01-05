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

from fastapi import Depends
import fastapi_jsonrpc as jsonrpc

from wy_qcos.common.config import Config
from .dependencies.authentication import auth


BASE_ENDPOINT = f"/{Config.API_VERSION}"
base_api = jsonrpc.Entrypoint("")
system_api_v1 = jsonrpc.Entrypoint(
    f"{BASE_ENDPOINT}/system", common_dependencies=[Depends(auth)]
)
job_api_v1 = jsonrpc.Entrypoint(
    f"{BASE_ENDPOINT}/job", common_dependencies=[Depends(auth)]
)
driver_api_v1 = jsonrpc.Entrypoint(
    f"{BASE_ENDPOINT}/driver", common_dependencies=[Depends(auth)]
)
device_api_v1 = jsonrpc.Entrypoint(
    f"{BASE_ENDPOINT}/device", common_dependencies=[Depends(auth)]
)
transpiler_api_v1 = jsonrpc.Entrypoint(
    f"{BASE_ENDPOINT}/transpiler", common_dependencies=[Depends(auth)]
)
