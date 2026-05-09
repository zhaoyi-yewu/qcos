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

"""Lower gates to schedules.

The relative timing within gates is respected. This module handles the
translation, but does not handle timing.
"""

from collections import namedtuple

from wy_qcos.transpiler.cmss.circuit.barrier import Barrier
from wy_qcos.transpiler.cmss.circuit.delay import Delay
from wy_qcos.transpiler.cmss.circuit.duration import convert_durations_to_dt
from wy_qcos.common.cmss.measure import Measure
from wy_qcos.transpiler.common.pulse_ir.compatible.exceptions import (
    QiskitError,
)
from wy_qcos.transpiler.common.pulse_ir.pulse import Schedule
from wy_qcos.transpiler.common.pulse_ir.pulse import instructions as pulse_inst
from wy_qcos.transpiler.common.pulse_ir.pulse.channels import (
    AcquireChannel,
    DriveChannel,
    MemorySlot,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.pulse.macros import measure
from wy_qcos.transpiler.common.pulse_ir.scheduler._typing import (
    SchedulableCircuitLike,
)
from wy_qcos.transpiler.common.pulse_ir.scheduler.config import ScheduleConfig
from qiskit.providers import BackendV1, BackendV2

CircuitPulseDef = namedtuple("CircuitPulseDef", ["schedule", "qubits"])


def lower_gates(
    circuit: SchedulableCircuitLike,
    schedule_config: ScheduleConfig,
    backend: BackendV1 | BackendV2 | None = None,
) -> list[CircuitPulseDef]:
    """Return pulse definitions for each element in the input circuit.

    Without concern for the final schedule, extract schedules and qubits
    for each circuit element. Measures are grouped when possible, so
    ``qc.measure(q0, c0)`` or ``qc.measure(q1, c1)`` generates a
    synchronous measurement pulse.

    Args:
        circuit: The quantum circuit to translate.
        schedule_config: Backend-specific parameters for building schedules.
        backend: Backend used to build schedules. It may be BackendV1 or
            BackendV2.

    Returns:
        The pulse definition for each circuit element.

    Raises:
        QiskitError: If circuit uses a command that isn't defined in
            config.inst_map.
    """
    from wy_qcos.transpiler.common.pulse_ir.pulse.transforms import (
        base_transforms,
    )

    target_qobj_transform = base_transforms.target_qobj_transform

    circ_pulse_defs = []

    inst_map = schedule_config.inst_map
    qubit_mem_slots = {}  # Map measured qubit index to classical bit index

    # convert the unit of durations from SI to dt before lowering
    circuit = convert_durations_to_dt(
        circuit,
        dt_in_sec=schedule_config.dt,
        inplace=False,
    )

    def get_measure_schedule(
        qubit_mem_slots: dict[int, int],
    ) -> CircuitPulseDef:
        """Create a schedule to measure the qubits queued for measuring."""
        sched = Schedule()
        # Exclude acquisition on qubits handled by user calibrations.
        acquire_excludes = {}
        if Measure().name in circuit.calibrations.keys():
            calib_qubits = tuple(sorted(qubit_mem_slots.keys()))
            params = ()
            for qubit in calib_qubits:
                try:
                    meas_q = circuit.calibrations[Measure().name][
                        ((qubit,), params)
                    ]
                    meas_q = target_qobj_transform(meas_q)
                    acquire_q = meas_q.filter(channels=[AcquireChannel(qubit)])
                    mem_slot_index = [
                        chan.index
                        for chan in acquire_q.channels
                        if isinstance(chan, MemorySlot)
                    ][0]
                    if mem_slot_index != qubit_mem_slots[qubit]:
                        raise KeyError(
                            "The measurement calibration is not defined on "
                            "the requested classical bits"
                        )
                    sched |= meas_q
                    del qubit_mem_slots[qubit]
                    acquire_excludes[qubit] = mem_slot_index
                except KeyError:
                    pass

        if qubit_mem_slots:
            meas_qubits = list(qubit_mem_slots.keys())
            qubit_mem_slots.update(acquire_excludes)
            meas_sched = measure(
                qubits=meas_qubits,
                backend=backend,
                inst_map=inst_map,
                meas_map=schedule_config.meas_map,
                qubit_mem_slots=qubit_mem_slots,
            )
            meas_sched = target_qobj_transform(meas_sched)
            meas_sched = meas_sched.exclude(
                channels=[AcquireChannel(qubit) for qubit in acquire_excludes]
            )
            sched |= meas_sched
        qubit_mem_slots.clear()
        return CircuitPulseDef(
            schedule=sched,
            qubits=[
                chan.index
                for chan in sched.channels
                if isinstance(chan, AcquireChannel)
            ],
        )

    qubit_indices = {bit: idx for idx, bit in enumerate(circuit.qubits)}
    clbit_indices = {bit: idx for idx, bit in enumerate(circuit.clbits)}

    for instruction in circuit.data:
        inst_qubits = [qubit_indices[qubit] for qubit in instruction.qubits]

        if any(q in qubit_mem_slots for q in inst_qubits):
            # Flush pending measurements before reusing those qubits.
            circ_pulse_defs.append(get_measure_schedule(qubit_mem_slots))

        if isinstance(instruction.operation, Barrier):
            circ_pulse_defs.append(
                CircuitPulseDef(
                    schedule=instruction.operation,
                    qubits=inst_qubits,
                )
            )
        elif isinstance(instruction.operation, Delay):
            sched = Schedule(name=instruction.operation.name)
            for qubit in inst_qubits:
                for channel in [DriveChannel]:
                    sched += pulse_inst.Delay(
                        duration=instruction.operation.duration,
                        channel=channel(qubit),
                    )
            circ_pulse_defs.append(
                CircuitPulseDef(schedule=sched, qubits=inst_qubits)
            )
        elif isinstance(instruction.operation, Measure):
            if len(inst_qubits) != 1 and len(instruction.clbits) != 1:
                raise QiskitError(
                    f"Qubit '{inst_qubits}' or classical bit "
                    f"'{instruction.clbits}' errored because the "
                    "circuit Measure instruction only takes one of each."
                )
            qubit_mem_slots[inst_qubits[0]] = clbit_indices[
                instruction.clbits[0]
            ]
        else:
            try:
                gate_cals = circuit.calibrations[instruction.operation.name]
                schedule = gate_cals[
                    (
                        tuple(inst_qubits),
                        tuple(
                            p if getattr(p, "parameters", None) else float(p)
                            for p in instruction.operation.params
                        ),
                    )
                ]
                schedule = target_qobj_transform(schedule)
                circ_pulse_defs.append(
                    CircuitPulseDef(schedule=schedule, qubits=inst_qubits)
                )
                continue
            except KeyError:
                pass  # Calibration not defined for this operation

            try:
                schedule = inst_map.get(
                    instruction.operation,
                    inst_qubits,
                    *instruction.operation.params,
                )
                schedule = target_qobj_transform(schedule)
                circ_pulse_defs.append(
                    CircuitPulseDef(schedule=schedule, qubits=inst_qubits)
                )
            except PulseError as ex:
                raise QiskitError(
                    f"Operation '{instruction.operation.name}' on qubit(s) "
                    f"{inst_qubits} "
                    "not supported by the backend command definition. "
                    "Did you remember to "
                    "transpile your input circuit for the same backend?"
                ) from ex

    if qubit_mem_slots:
        circ_pulse_defs.append(get_measure_schedule(qubit_mem_slots))

    return circ_pulse_defs
