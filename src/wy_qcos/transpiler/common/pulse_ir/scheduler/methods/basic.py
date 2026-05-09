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

"""Basic scheduling methods."""

from collections import defaultdict

from wy_qcos.transpiler.cmss.circuit.barrier import Barrier
from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import Schedule
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
def as_soon_as_possible(
    circuit: SchedulableCircuitLike,
    schedule_config: ScheduleConfig,
    backend: BackendV1 | BackendV2 | None = None,
) -> Schedule:
    """Schedule the circuit as soon as possible.

    Circuit instructions are first mapped to equivalent pulse schedules
    according to the command definition in schedule_config. Each schedule
    is then appended at the earliest time that all involved qubits are
    available.

    Args:
        circuit: The quantum circuit to translate.
        schedule_config: Backend-specific parameters for building schedules.
        backend: Backend used to build schedules. It may be BackendV1 or
            BackendV2.

    Returns:
        A schedule with pulses occurring as early as possible.
    """
    qubit_time_available = defaultdict(int)

    def update_times(inst_qubits: list[int], time: int = 0) -> None:
        """Update the time tracker for all inst_qubits to the given time."""
        for q in inst_qubits:
            qubit_time_available[q] = time

    start_times = []
    circ_pulse_defs = lower_gates(circuit, schedule_config, backend)
    for circ_pulse_def in circ_pulse_defs:
        start_time = max(
            qubit_time_available[q] for q in circ_pulse_def.qubits
        )
        stop_time = start_time
        if not isinstance(circ_pulse_def.schedule, Barrier):
            stop_time += circ_pulse_def.schedule.duration

        start_times.append(start_time)
        update_times(circ_pulse_def.qubits, stop_time)

    timed_schedules = [
        (time, cpd.schedule)
        for time, cpd in zip(start_times, circ_pulse_defs)
        if not isinstance(cpd.schedule, Barrier)
    ]
    schedule = Schedule.initialize_from(circuit)
    for time, inst in timed_schedules:
        schedule.insert(time, inst, inplace=True)
    return schedule


@deprecate_pulse_dependency(moving_to_dynamics=True)
def as_late_as_possible(
    circuit: SchedulableCircuitLike,
    schedule_config: ScheduleConfig,
    backend: BackendV1 | BackendV2 | None = None,
) -> Schedule:
    """Schedule the circuit as late as possible.

    Circuit instructions are first mapped to equivalent pulse schedules
    according to the command definition in schedule_config. Each schedule
    is then appended at the latest time that avoids unnecessary gaps and
    overlapping use of common qubits.

    This can improve fidelity over ASAP scheduling by maximizing the time
    that qubits remain in the ground state.

    Args:
        circuit: The quantum circuit to translate.
        schedule_config: Backend-specific parameters for building schedules.
        backend: Backend used to build schedules. It may be BackendV1 or
            BackendV2.

    Returns:
        A schedule with pulses occurring as late as possible.
    """
    qubit_time_available = defaultdict(int)

    def update_times(inst_qubits: list[int], time: int = 0) -> None:
        """Update the time tracker for all inst_qubits to the given time."""
        for q in inst_qubits:
            qubit_time_available[q] = time

    rev_stop_times = []
    circ_pulse_defs = lower_gates(circuit, schedule_config, backend)
    for circ_pulse_def in reversed(circ_pulse_defs):
        start_time = max(
            qubit_time_available[q] for q in circ_pulse_def.qubits
        )
        stop_time = start_time
        if not isinstance(circ_pulse_def.schedule, Barrier):
            stop_time += circ_pulse_def.schedule.duration

        rev_stop_times.append(stop_time)
        update_times(circ_pulse_def.qubits, stop_time)

    last_stop = (
        max(t for t in qubit_time_available.values())
        if qubit_time_available
        else 0
    )
    start_times = [last_stop - t for t in reversed(rev_stop_times)]

    timed_schedules = [
        (time, cpd.schedule)
        for time, cpd in zip(start_times, circ_pulse_defs)
        if not isinstance(cpd.schedule, Barrier)
    ]
    schedule = Schedule.initialize_from(circuit)
    for time, inst in timed_schedules:
        schedule.insert(time, inst, inplace=True)
    return schedule
