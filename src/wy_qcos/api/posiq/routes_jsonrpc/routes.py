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

from fastapi import Depends
import fastapi_jsonrpc as jsonrpc

from wy_qcos.common.constant import Constant
from .dependencies.authentication import auth


BASE_ENDPOINT = f"/{Constant.API_VERSION}"
base_api = jsonrpc.Entrypoint("")

# Auth API entrypoint (no auth required for login endpoint)
auth_api_v1 = jsonrpc.Entrypoint(f"{BASE_ENDPOINT}/auth")
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
user_api_v1 = jsonrpc.Entrypoint(
    f"{BASE_ENDPOINT}/user", common_dependencies=[Depends(auth)]
)
metrics_api_v1 = jsonrpc.Entrypoint(
    f"{BASE_ENDPOINT}/metrics", common_dependencies=[Depends(auth)]
)
# All API entrypoints including auth
all_api_v1 = [
    base_api,
    auth_api_v1,
    driver_api_v1,
    device_api_v1,
    transpiler_api_v1,
    job_api_v1,
    user_api_v1,
    system_api_v1,
    metrics_api_v1,
]
all_api = all_api_v1
