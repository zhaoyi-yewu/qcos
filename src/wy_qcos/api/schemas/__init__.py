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

from .auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from .version import GetVersionRequest, GetVersionResponse
from .user import (
    GetUserMgmtRequest,
    GetUserMgmtResponse,
    SetUserMgmtRequest,
    SetUserMgmtResponse,
    CreateUserRequest,
    CreateUserResponse,
    GetUserRequest,
    GetUserResponse,
    UpdateUserRequest,
    UpdateUserResponse,
    GetUsersRequest,
    DeleteUserRequest,
    DeleteUserResponse,
    LockUserRequest,
    LockUserResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    GetLoginLogsRequest,
    LoginLogResponse,
    CreateRoleRequest,
    CreateRoleResponse,
    GetRoleRequest,
    GetRoleResponse,
    GetRolesRequest,
    UpdateRoleRequest,
    UpdateRoleResponse,
    DeleteRoleRequest,
    DeleteRoleResponse,
)
from .driver import GetDriversRequest, GetDriverRequest, GetDriverResponse
from .device import (
    GetDevicesRequest,
    GetDeviceRequest,
    GetDeviceResponse,
    CalibrateDeviceRequest,
    CalibrateDeviceResponse,
    SetDeviceOptionsRequest,
    SetDeviceOptionsResponse,
    GetCalibrateResultRequest,
    GetCalibrateResultResponse,
    GetDeviceOptionsRequest,
    GetDeviceOptionsResponse,
    SetDeviceMaintainModeRequest,
    SetDeviceMaintainModeResponse,
)
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
    ShowMemRequest,
    ShowMemResponse,
    GcMemRequest,
    GcMemResponse,
    TraceMemRequest,
    TraceMemStatItem,
    TraceMemResponse,
)
from .metrics import (
    GetMetricsRequest,
    GetMetricsResponse,
    GetSystemHealthRequest,
    GetSystemHealthResponse,
    GetApiStatsRequest,
    GetApiStatsResponse,
    GetJobStatsRequest,
    GetJobStatsResponse,
)
from .flavor import (
    CreateFlavorRequest,
    FlavorResponse,
    GetFlavorRequest,
    GetFlavorsRequest,
    UpdateFlavorRequest,
    DeleteFlavorsRequest,
    DeleteFlavorResponseItem,
    DeleteFlavorsResponse,
)
from .device_group import (
    CreateDeviceGroupRequest,
    UpdateDeviceGroupRequest,
    GetDeviceGroupRequest,
    GetDeviceGroupsRequest,
    DeleteDeviceGroupsRequest,
    DeleteDeviceGroupResponseItem,
    DeleteDeviceGroupsResponse,
    DeviceGroupResponse,
)
