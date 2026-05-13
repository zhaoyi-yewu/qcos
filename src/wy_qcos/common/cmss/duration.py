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

"""Duration conversion utilities for quantum circuits."""

import copy

from wy_qcos.common.cmss.delay import Delay

# Unit conversion factors to seconds
_UNIT_TO_SECONDS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
    "ps": 1e-12,
    "dt": None,  # dt is the target unit, no conversion needed
}


def convert_durations_to_dt(circuit, dt_in_sec=None, inplace=False):
    """Convert instruction durations from SI units to dt units.

    Converts the duration of each instruction in the circuit from its
    current time unit to the backend's dt (sample time) unit.

    Args:
        circuit: The QuantumCircuit to convert.
        dt_in_sec: The duration of one dt in seconds.
        inplace: If True, modify the circuit in place. Otherwise return a copy.

    Returns:
        The circuit with durations converted to dt units.
    """
    if not inplace:
        circuit = copy.deepcopy(circuit)

    if dt_in_sec is None:
        return circuit

    for instruction in getattr(circuit, "data", []):
        op = (
            instruction.operation
            if hasattr(instruction, "operation")
            else instruction
        )
        if isinstance(op, Delay) and hasattr(op, "unit") and op.unit != "dt":
            unit = op.unit
            if unit in _UNIT_TO_SECONDS and _UNIT_TO_SECONDS[unit] is not None:
                duration_in_sec = op.duration * _UNIT_TO_SECONDS[unit]
                op.duration = round(duration_in_sec / dt_in_sec)
                op._unit = "dt"

    return circuit


__all__ = ["convert_durations_to_dt"]
