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
r"""Instruction reference.

.. _pulse-insts:

===============================================
Instructions (:mod:`wy_qcos.transpiler.common.pulse_ir.pulse.instructions`)
===============================================

The ``instructions`` module holds the various :obj:`Instruction`\ s
supported by Qiskit Pulse. Instructions have operands, which typically
include at least one :py:class:`~wy_qcos.pulse.channels.Channel`
specifying where the instruction will be applied.

Every instruction has a duration, whether explicitly included as an
operand or implicitly defined. For instance, a
:py:class:`~wy_qcos.pulse.instructions.ShiftPhase` instruction can be
instantiated with operands *phase* and *channel*, for some float
``phase`` and a
:py:class:`~wy_qcos.pulse.channels.Channel` ``channel``::

    ShiftPhase(phase, channel)

The duration of this instruction is implicitly zero. On the other hand,
the :py:class:`~wy_qcos.pulse.instructions.Delay` instruction takes an
explicit duration::

    Delay(duration, channel)

An instruction can be added to a :py:class:`~wy_qcos.pulse.Schedule`,
which is a sequence of scheduled Pulse ``Instruction`` s over many
channels. ``Instruction`` s and ``Schedule`` s implement the same
interface.

.. autosummary::
   :toctree: ../stubs/

   Acquire
   Reference
   Delay
   Play
   RelativeBarrier
   SetFrequency
   ShiftFrequency
   SetPhase
   ShiftPhase
   Snapshot
   TimeBlockade

These are all instances of the same base class:

.. autoclass:: Instruction
"""

from .acquire import Acquire
from .delay import Delay
from .directives import Directive, RelativeBarrier, TimeBlockade
from .instruction import Instruction
from .frequency import SetFrequency, ShiftFrequency
from .phase import ShiftPhase, SetPhase
from .play import Play
from .snapshot import Snapshot
from .reference import Reference
