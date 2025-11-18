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

from .driver import GetDriversRequest, GetDriverRequest, GetDriverResponse
from .device import GetDevicesRequest, GetDeviceRequest, GetDeviceResponse
from .transpiler import (
    GetTranspilersRequest,
    GetTranspilerRequest,
    GetTranspilerResponse,
)
from .job import (
    SubmitJobRequest,
    SubmitJobResponse,
    GetJobStatusRequest,
    GetJobStatusResponse,
    GetJobResultsRequest,
    GetJobResultsResponse,
    GetJobsRequest,
    CancelJobsRequest,
    CancelJobsResponse,
    DeleteJobsRequest,
    DeleteJobsResponse,
    SetJobResultsRequest,
    SetJobResultsResponse,
    UpdateJobRequest,
    UpdateJobResponse,
)
from .system import (
    PingRequest,
    PongResponse,
    SystemInfoRequest,
    SystemInfoResponse,
)
from .version import GetVersionRequest, GetVersionResponse
