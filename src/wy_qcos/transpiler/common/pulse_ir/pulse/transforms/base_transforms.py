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
"""A collection of transforms."""

# TODO: replace this with proper pulse transformation passes.
# Qiskit-terra/#6121

from collections.abc import Iterable
from typing import TypeAlias, cast

from wy_qcos.transpiler.common.pulse_ir.pulse.instructions import Instruction
from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import (
    ScheduleBlock,
    Schedule,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.transforms import (
    canonicalization,
)

InstructionSched: TypeAlias = tuple[int, Instruction] | Instruction


def target_qobj_transform(
    sched: ScheduleBlock
    | Schedule
    | InstructionSched
    | Iterable[InstructionSched],
    remove_directives: bool = True,
) -> Schedule:
    """A basic pulse program transformation for OpenPulse API execution.

    Args:
        sched: Input program to transform.
        remove_directives: Set `True` to remove compiler directives.

    Returns:
        Transformed program for execution.
    """
    if isinstance(sched, ScheduleBlock):
        sched = canonicalization.block_to_schedule(sched)
    elif isinstance(sched, Schedule):
        pass
    else:
        schedule_component = cast(
            InstructionSched | Iterable[InstructionSched], sched
        )
        sched = Schedule(*_format_schedule_component(schedule_component))

    # remove subroutines, i.e. Call instructions
    sched = canonicalization.inline_subroutines(sched)

    # inline nested schedules
    sched = canonicalization.flatten(sched)

    # remove directives, e.g. barriers
    if remove_directives:
        sched = canonicalization.remove_directives(sched)

    return sched


def _format_schedule_component(
    sched: InstructionSched | Iterable[InstructionSched],
):
    """A helper function to convert instructions into list of instructions."""
    # TODO remove schedule initialization with *args, Qiskit-terra/#5093
    if (
        isinstance(sched, tuple)
        and len(sched) == 2
        and isinstance(sched[0], int)
    ):
        return [sched]
    if isinstance(sched, Iterable) and not isinstance(sched, Instruction):
        return list(sched)
    return [sched]
