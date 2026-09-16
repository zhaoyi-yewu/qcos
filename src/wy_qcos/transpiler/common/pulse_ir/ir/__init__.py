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
# WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY
# OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""IR module for default gate-to-pulse calibrations.

Provides a default InstructionScheduleMap with pulse calibrations for
a standard gate set. Users can override individual gates or use the
provided defaults as-is.

Usage::

    from wy_qcos.ir import build_default_inst_map

    inst_map = build_default_inst_map(
        num_qubits=2,
        dt=1 / 4.5,
        duration_1q=160,
        duration_2q=640,
    )
"""

from wy_qcos.transpiler.common.pulse_ir.ir.default_calibrations import (
    build_default_inst_map,
)

__all__ = ["build_default_inst_map"]
