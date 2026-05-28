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
r"""Pulse package.

===========================
Pulse (:mod:`wy_qcos.pulse`).
===========================

.. currentmodule:: wy_qcos.pulse

Qiskit-Pulse is a pulse-level quantum programming kit. This lower level of
programming offers the user more control than programming with
:py:class:`~wy_qcos.transpiler.cmss.circuit.quantum_circuit.QuantumCircuit`\ s.

Extracting the greatest performance from quantum hardware requires real-time
pulse-level instructions. Pulse answers that need: it enables the quantum
physicist *user* to specify the exact time dynamics of an experiment.
It is especially powerful for error mitigation techniques.

The input is given as arbitrary, time-ordered signals
(see: :ref:`Instructions <pulse-insts>`) scheduled in parallel over
multiple virtual hardware or simulator resources
(see: :ref:`Channels <pulse-channels>`). The system also allows the user
to recover the time dynamics of the measured output.

This is sufficient to allow the quantum physicist to explore and correct for
noise in a quantum system.

.. automodule:: wy_qcos.pulse.instructions
.. automodule:: wy_qcos.pulse.library
.. automodule:: wy_qcos.pulse.channels
.. automodule:: wy_qcos.pulse.schedule
.. automodule:: wy_qcos.pulse.transforms
.. automodule:: wy_qcos.pulse.builder

.. currentmodule:: wy_qcos.pulse

Configuration
=============

.. autosummary::
   :toctree: ../stubs/

   InstructionScheduleMap

Exceptions
==========

.. autoexception:: PulseError
.. autoexception:: BackendNotSet
.. autoexception:: NoActiveBuilder
.. autoexception:: UnassignedDurationError
.. autoexception:: UnassignedReferenceError
"""

# Builder imports.
from .builder import (
    # Construction methods.
    active_backend,
    build,
    num_qubits,
    qubit_channels,
    samples_to_seconds,
    seconds_to_samples,
    # Instructions.
    acquire,
    barrier,
    call,
    delay,
    play,
    reference,
    set_frequency,
    set_phase,
    shift_frequency,
    shift_phase,
    snapshot,
    # Channels.
    acquire_channel,
    control_channels,
    drive_channel,
    measure_channel,
    # Contexts.
    align_equispaced,
    align_func,
    align_left,
    align_right,
    align_sequential,
    frequency_offset,
    phase_offset,
    # Macros.
    macro,
    measure,
    measure_all,
    delay_qubits,
)
from .channels import (
    AcquireChannel,
    ControlChannel,
    DriveChannel,
    MeasureChannel,
    MemorySlot,
    RegisterSlot,
    SnapshotChannel,
)
from .configuration import (
    Discriminator,
    Kernel,
    LoConfig,
    LoRange,
)
from .exceptions import (
    PulseError,
    BackendNotSet,
    NoActiveBuilder,
    UnassignedDurationError,
    UnassignedReferenceError,
)
from .instruction_schedule_map import InstructionScheduleMap
from .instructions import (
    Acquire,
    Delay,
    Instruction,
    Play,
    SetFrequency,
    SetPhase,
    ShiftFrequency,
    ShiftPhase,
    Snapshot,
)
from .library import (
    Constant,
    Drag,
    Gaussian,
    GaussianSquare,
    GaussianSquareDrag,
    gaussian_square_echo,
    Sin,
    Cos,
    Sawtooth,
    Triangle,
    Square,
    GaussianDeriv,
    Sech,
    SechDeriv,
    SymbolicPulse,
    ScalableSymbolicPulse,
    Waveform,
)
from .library.samplers.decorators import functional_pulse
from .schedule import Schedule, ScheduleBlock
