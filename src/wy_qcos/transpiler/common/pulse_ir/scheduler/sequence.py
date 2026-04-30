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

"""Map a scheduled QuantumCircuit to a pulse Schedule."""

from collections import defaultdict

from wy_qcos.transpiler.cmss.circuit.barrier import Barrier
from wy_qcos.transpiler.cmss.common.measure import Measure
from wy_qcos.transpiler.common.pulse_ir.compatible.exceptions import (
    QiskitError,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import Schedule
from wy_qcos.transpiler.common.pulse_ir.pulse.transforms import pad
from wy_qcos.transpiler.common.pulse_ir.scheduler._typing import (
    SchedulableCircuitLike,
)
from wy_qcos.transpiler.common.pulse_ir.scheduler.config import ScheduleConfig
from wy_qcos.transpiler.common.pulse_ir.scheduler.lowering import lower_gates
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_dependency,
)
from qiskit.providers import BackendV1, BackendV2


@deprecate_pulse_dependency(moving_to_dynamics=True)
def sequence(
    scheduled_circuit: SchedulableCircuitLike,
    schedule_config: ScheduleConfig,
    backend: BackendV1 | BackendV2 | None = None,
) -> Schedule:
    """Return the pulse schedule for the input scheduled circuit.

    Assume all measurements are done at once at the last of the circuit.
    Scheduling follows the command definition given by schedule_config.

    Args:
        scheduled_circuit: The scheduled quantum circuit to translate.
        schedule_config: Backend-specific parameters for building schedules.
        backend: Backend used to build schedules. It may be BackendV1 or
            BackendV2.

    Returns:
        A schedule corresponding to the input ``circuit``.

    Raises:
        QiskitError: If invalid scheduled circuit is supplied.
    """
    circ_pulse_defs = lower_gates(scheduled_circuit, schedule_config, backend)

    # find the measurement start time (assume measurement once)
    def _meas_start_time():
        _qubit_time_available = defaultdict(int)
        for instruction in scheduled_circuit.data:
            if isinstance(instruction.operation, Measure):
                return _qubit_time_available[instruction.qubits[0]]
            for q in instruction.qubits:
                _qubit_time_available[q] += instruction.operation.duration
        return None

    meas_time = _meas_start_time()

    # restore start times
    qubit_time_available = {}
    start_times = []
    out_circ_pulse_defs = []
    for circ_pulse_def in circ_pulse_defs:
        active_qubits = [
            q for q in circ_pulse_def.qubits if q in qubit_time_available
        ]

        start_time = max(
            (qubit_time_available[q] for q in active_qubits),
            default=0,
        )

        for q in active_qubits:
            if qubit_time_available[q] != start_time:
                # print(q, ":", qubit_time_available[q], "!=", start_time)
                raise QiskitError("Invalid scheduled circuit.")

        stop_time = start_time
        if not isinstance(circ_pulse_def.schedule, Barrier):
            stop_time += circ_pulse_def.schedule.duration

        delay_overlaps_meas = False
        for q in circ_pulse_def.qubits:
            qubit_time_available[q] = stop_time
            if (
                meas_time is not None
                and circ_pulse_def.schedule.name == "delay"
                and stop_time > meas_time
            ):
                qubit_time_available[q] = meas_time
                delay_overlaps_meas = True
        # skip to delays overlapping measures and barriers
        if not delay_overlaps_meas and not isinstance(
            circ_pulse_def.schedule, Barrier
        ):
            start_times.append(start_time)
            out_circ_pulse_defs.append(circ_pulse_def)

    timed_schedules = [
        (time, cpd.schedule)
        for time, cpd in zip(start_times, out_circ_pulse_defs)
    ]
    sched = Schedule(*timed_schedules, name=scheduled_circuit.name)
    return pad(sched)
