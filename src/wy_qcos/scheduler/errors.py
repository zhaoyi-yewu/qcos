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

from wy_qcos.common import errors


class NoValidDeviceError(errors.BaseException):
    """No valid device error."""

    module_name = "Scheduler"
    error_code = -200
    err_type = "NoValidDeviceError"


class DeviceQubitExceededError(NoValidDeviceError):
    """Device qubit count exceeded error.

    Raised when the only failing filter is QubitCountFilter,
    meaning all available devices have insufficient qubits for
    the requested circuit. This is a subclass of NoValidDeviceError
    so existing handlers continue to work, but allows callers to
    distinguish qubit-exceeded failures for wirecut fallback.
    """

    module_name = "Scheduler"
    error_code = -201
    err_type = "DeviceQubitExceededError"
