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
"""A collection of functions that filter instructions in a pulse program."""

from __future__ import annotations
import abc
from functools import singledispatch
from collections.abc import Iterable
from typing import Any
from collections.abc import Callable

import numpy as np

from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import (
    Schedule,
    ScheduleBlock,
    Instruction,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.channels import Channel
from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import Interval
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError


@singledispatch
def filter_instructions(
    sched,
    filters: list[Callable[..., bool]],
    negate: bool = False,
    recurse_subroutines: bool = True,
):
    """Fallback implementation for unsupported schedule types.

    This is called only when neither ``handle_schedule`` nor
    ``handle_scheduleblock`` accepts the input type.
    """
    raise TypeError(
        f"Type '{type(sched)}' is not valid data format as an input to "
        "filter_instructions."
    )


@filter_instructions.register
def handle_schedule(
    sched: Schedule,
    filters: list[Callable[..., bool]],
    negate: bool = False,
    recurse_subroutines: bool = True,
) -> Schedule:
    """Filter a schedule and return the accepted instructions.

    This returns a schedule consisting only of instructions accepted by
    the supplied filters.

    Args:
        sched: A pulse schedule to be filtered.
        filters: List of callback functions that take an instruction and
            return a boolean.
        negate: Set ``True`` to accept an instruction if a filter function
            returns ``False``. Otherwise the instruction is accepted when
            the filter function returns ``True``.
        recurse_subroutines: Set ``True`` to individually filter
            instructions inside a subroutine defined by the
            :py:class:`~wy_qcos.pulse.instructions.Call` instruction.

    Returns:
        Filtered pulse schedule.
    """
    from wy_qcos.transpiler.common.pulse_ir.pulse.transforms import (
        flatten,
        inline_subroutines,
    )

    target_sched = flatten(sched)
    if recurse_subroutines:
        inlined_sched = inline_subroutines(target_sched)
        if isinstance(inlined_sched, Schedule):
            target_sched = inlined_sched
        else:
            raise PulseError("Expected inline_subroutines to return Schedule.")

    time_inst_tuples = np.array(target_sched.instructions)

    valid_insts = np.ones(len(time_inst_tuples), dtype=bool)
    for filt in filters:
        valid_insts = np.logical_and(
            valid_insts, np.array(list(map(filt, time_inst_tuples)))
        )

    if negate and len(filters) > 0:
        valid_insts = ~valid_insts

    filter_schedule = Schedule.initialize_from(sched)
    for time, inst in time_inst_tuples[valid_insts]:
        filter_schedule.insert(time, inst, inplace=True)

    return filter_schedule


@filter_instructions.register
def handle_scheduleblock(
    sched_blk: ScheduleBlock,
    filters: list[Callable[..., bool]],
    negate: bool = False,
    recurse_subroutines: bool = True,
) -> ScheduleBlock:
    """Filter a schedule block and return the accepted instructions.

    This returns a schedule block consisting only of instructions
    accepted by the supplied filters.

    Args:
        sched_blk: A pulse schedule_block to be filtered.
        filters: List of callback functions that take an instruction and
            return a boolean.
        negate: Set ``True`` to accept an instruction if a filter function
            returns ``False``. Otherwise the instruction is accepted when
            the filter function returns ``True``.
        recurse_subroutines: Set ``True`` to individually filter
            instructions inside a subroutine defined by the
            :py:class:`~wy_qcos.pulse.instructions.Call` instruction.

    Returns:
        Filtered pulse schedule_block.
    """
    from wy_qcos.transpiler.common.pulse_ir.pulse.transforms import (
        inline_subroutines,
    )

    target_sched_blk = sched_blk
    if recurse_subroutines:
        inlined_sched_blk = inline_subroutines(target_sched_blk)
        if isinstance(inlined_sched_blk, ScheduleBlock):
            target_sched_blk = inlined_sched_blk
        else:
            raise PulseError(
                "Expected inline_subroutines to return ScheduleBlock."
            )

    def apply_filters_to_insts_in_scheblk(blk: ScheduleBlock) -> ScheduleBlock:
        blk_new = ScheduleBlock.initialize_from(blk)
        for element in blk.blocks:
            if isinstance(element, ScheduleBlock):
                inner_blk = apply_filters_to_insts_in_scheblk(element)
                if len(inner_blk) > 0:
                    blk_new.append(inner_blk)

            elif isinstance(element, Instruction):
                valid_inst = all(filt(element) for filt in filters)
                if negate:
                    valid_inst ^= True
                if valid_inst:
                    blk_new.append(element)

            else:
                raise PulseError(
                    f"An unexpected element '{element}' is included in "
                    "ScheduleBlock.blocks."
                )
        return blk_new

    filter_sched_blk = apply_filters_to_insts_in_scheblk(target_sched_blk)
    return filter_sched_blk


def composite_filter(
    channels: Iterable[Channel] | Channel | None = None,
    instruction_types: Iterable[abc.ABCMeta] | abc.ABCMeta | None = None,
    time_ranges: Iterable[tuple[int, int]] | None = None,
    intervals: Iterable[Interval] | None = None,
) -> list[Callable]:
    """Generate filter functions for common selection criteria.

    This helper builds a list of filter functions from typical filtering
    inputs.

    Args:
        channels: For example, ``[DriveChannel(0), AcquireChannel(0)]``.
        instruction_types: For example,
            ``[PulseInstruction, AcquireInstruction]``.
        time_ranges: For example, ``[(0, 5), (6, 10)]``.
        intervals: For example, ``[(0, 5), (6, 10)]``.

    Returns:
        List of filtering functions.
    """
    filters = []

    # An empty list is also valid input for filter generators.
    # See unittest
    # test.python.pulse.test_schedule.TestScheduleFilter.test_empty_filters.
    if channels is not None:
        filters.append(with_channels(channels))
    if instruction_types is not None:
        filters.append(with_instruction_types(instruction_types))
    if time_ranges is not None:
        filters.append(with_intervals(time_ranges))
    if intervals is not None:
        filters.append(with_intervals(intervals))

    return filters


def with_channels(channels: Iterable[Channel] | Channel) -> Callable:
    """Channel filter generator.

    Args:
        channels: List of channels to filter.

    Returns:
        A callback function to filter channels.
    """
    channels = _if_scalar_cast_to_list(channels)

    @singledispatch
    def channel_filter(time_inst):
        """Fallback implementation for unsupported channel-filter inputs.

        This is called only when neither ``handle_numpyndarray`` nor
        ``handle_instruction`` accepts the input type.
        """
        raise TypeError(
            f"Type '{type(time_inst)}' is not valid data format as an "
            "input to channel_filter."
        )

    @channel_filter.register
    def handle_numpyndarray(time_inst: np.ndarray) -> bool:
        """Filter channel.

        Args:
            time_inst (numpy.ndarray([int, Instruction])): Time

        Returns:
            If instruction matches with condition.
        """
        inst = time_inst[1]
        return isinstance(inst, Instruction) and any(
            chan in channels for chan in inst.channels
        )

    @channel_filter.register
    def handle_instruction(inst: Instruction) -> bool:
        """Filter channel.

        Args:
            inst: Instruction

        Returns:
            If instruction matches with condition.
        """
        return any(chan in channels for chan in inst.channels)

    return channel_filter


def with_instruction_types(
    types: Iterable[abc.ABCMeta] | abc.ABCMeta,
) -> Callable:
    """Instruction type filter generator.

    Args:
        types: List of instruction types to filter.

    Returns:
        A callback function to filter instructions.
    """
    types = _if_scalar_cast_to_list(types)

    @singledispatch
    def instruction_filter(time_inst) -> bool:
        """Fallback implementation for unsupported instruction inputs.

        This is called only when neither ``handle_numpyndarray`` nor
        ``handle_instruction`` accepts the input type.
        """
        raise TypeError(
            f"Type '{type(time_inst)}' is not valid data format as an "
            "input to instruction_filter."
        )

    @instruction_filter.register
    def handle_numpyndarray(time_inst: np.ndarray) -> bool:
        """Filter instruction.

        Args:
            time_inst (numpy.ndarray([int, Instruction])): Time

        Returns:
            If instruction matches with condition.
        """
        return isinstance(time_inst[1], tuple(types))

    @instruction_filter.register
    def handle_instruction(inst: Instruction) -> bool:
        """Filter instruction.

        Args:
            inst: Instruction

        Returns:
            If instruction matches with condition.
        """
        return isinstance(inst, tuple(types))

    return instruction_filter


def with_intervals(ranges: Iterable[Interval] | Interval) -> Callable:
    """Interval filter generator.

    Args:
        ranges: List of intervals ``[t0, t1]`` to filter.

    Returns:
        A callback function to filter intervals.
    """
    ranges = _if_scalar_cast_to_list(ranges)

    def interval_filter(time_inst) -> bool:
        """Filter interval.

        Args:
            time_inst (Tuple[int, Instruction]): Time.

        Returns:
            If instruction matches with condition.
        """
        for t0, t1 in ranges:
            inst_start = time_inst[0]
            inst_stop = inst_start + time_inst[1].duration
            if t0 <= inst_start and inst_stop <= t1:
                return True
        return False

    return interval_filter


def _if_scalar_cast_to_list(to_list: Any) -> list[Any]:
    """A helper function to create python list of input arguments.

    Args:
        to_list: Arbitrary object can be converted into a python list.

    Returns:
        Python list of input object.
    """
    try:
        iter(to_list)
    except TypeError:
        to_list = [to_list]
    return to_list
