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

"""Qobj utilities and enums."""

from enum import Enum, IntEnum

from .common import QOBJ_DEPRECATION_MSG

from wy_qcos.transpiler.common.pulse_ir.utils import deprecate_func


@deprecate_func(
    since="1.2",
    removal_timeline="in the 2.0 release",
    additional_msg=QOBJ_DEPRECATION_MSG,
)
class QobjType(str, Enum):
    """Qobj.type allowed values."""

    QASM = "QASM"
    PULSE = "PULSE"


class MeasReturnType(str, Enum):
    """PulseQobjConfig meas_return allowed values."""

    AVERAGE = "avg"
    SINGLE = "single"


class MeasLevel(IntEnum):
    """MeasLevel allowed values."""

    RAW = 0
    KERNELED = 1
    CLASSIFIED = 2
