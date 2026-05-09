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

"""Scheduling container classes."""

from wy_qcos.transpiler.common.pulse_ir.pulse.instruction_schedule_map import (
    InstructionScheduleMap,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.utils import format_meas_map
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_dependency,
)


class ScheduleConfig:
    """Configuration for pulse scheduling."""

    @deprecate_pulse_dependency(moving_to_dynamics=True)
    def __init__(
        self,
        inst_map: InstructionScheduleMap,
        meas_map: list[list[int]],
        dt: float,
    ):
        """Create a container for circuit scheduling inputs.

        Args:
            inst_map: The schedule definition for all gates on a backend.
            meas_map: Groups of qubits that must be measured together.
            dt: Sample duration.
        """
        self.inst_map = inst_map
        self.meas_map = format_meas_map(meas_map)
        self.dt = dt
