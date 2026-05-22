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
"""Passes for reallocating instruction timeslots according to context."""

from __future__ import annotations
import abc
from collections.abc import Callable
from typing import Any

import numpy as np

from wy_qcos.transpiler.cmss.circuit.parameterexpression import (
    ParameterExpression,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import (
    Schedule,
    ScheduleComponent,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.utils import (
    instruction_duration_validation,
)


class AlignmentKind(abc.ABC):
    """An abstract class for schedule alignment."""

    def __init__(self, context_params: tuple[Any, ...]):
        """Create new context."""
        self._context_params = tuple(context_params)

    @abc.abstractmethod
    def align(self, schedule: Schedule) -> Schedule:
        """Reallocate instructions according to the policy.

        Only top-level sub-schedules are aligned. If sub-schedules are nested,
        nested schedules are not recursively aligned.

        Args:
            schedule: Schedule to align.

        Returns:
            Schedule with reallocated instructions.
        """
        pass

    @property
    @abc.abstractmethod
    def is_sequential(self) -> bool:
        """Return ``True`` if this is sequential alignment context.

        This information is used to evaluate DAG equivalency of two
        :class:`.ScheduleBlock` objects.
        When the context has two pulses in different channels,
        a sequential context subtype intends to return the following
        scheduling outcome.

        .. code-block:: text

                ┌────────┐
            D0: ┤ pulse1 ├────────────
                └────────┘  ┌────────┐
            D1: ────────────┤ pulse2 ├
                            └────────┘

        On the other hand, a parallel context with
        ``is_sequential=False`` returns

        .. code-block:: text

                ┌────────┐
            D0: ┤ pulse1 ├
                ├────────┤
            D1: ┤ pulse2 ├
                └────────┘

        All subclasses must implement this method according to their
        scheduling strategy.
        """
        pass

    def __eq__(self, other: object) -> bool:
        """Check equality of two transforms."""
        if not isinstance(other, AlignmentKind):
            return False
        if type(self) is not type(other):
            return False
        if self._context_params != other._context_params:
            return False
        return True

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(self._context_params)})"


class AlignLeft(AlignmentKind):
    """Align instructions in as-soon-as-possible manner.

    Instructions are placed at earliest available timeslots.
    """

    def __init__(self):
        """Create new left-justified context."""
        super().__init__(context_params=())

    @property
    def is_sequential(self) -> bool:
        return False

    def align(self, schedule: Schedule) -> Schedule:
        """Reallocate instructions according to the policy.

        Only top-level sub-schedules are aligned. If sub-schedules are nested,
        nested schedules are not recursively aligned.

        Args:
            schedule: Schedule to align.

        Returns:
            Schedule with reallocated instructions.
        """
        aligned = Schedule.initialize_from(schedule)
        for _, child in schedule.children:
            self._push_left_append(aligned, child)

        return aligned

    @staticmethod
    def _push_left_append(
        this: Schedule, other: ScheduleComponent
    ) -> Schedule:
        """Insert ``other`` into ``this`` at the latest shared-channel slot.

        This chooses the maximum time over all channels shared between
        ``this`` and ``other``.

        Args:
            this: Input schedule to which ``other`` will be inserted.
            other: Other schedule to insert.

        Returns:
            Push left appended schedule.
        """
        this_channels = set(this.channels)
        other_channels = set(other.channels)
        shared_channels = list(this_channels & other_channels)
        ch_slacks = [
            this.stop_time
            - this.ch_stop_time(channel)
            + other.ch_start_time(channel)
            for channel in shared_channels
        ]

        if ch_slacks:
            slack_chan = shared_channels[np.argmin(ch_slacks)]
            shared_insert_time = this.ch_stop_time(
                slack_chan
            ) - other.ch_start_time(slack_chan)
        else:
            shared_insert_time = 0

        # Handle case where channels not common to both might actually start
        # after ``this`` has finished.
        other_only_insert_time = other.ch_start_time(
            *(other_channels - this_channels)
        )
        # Choose whichever is greatest.
        insert_time = max(shared_insert_time, other_only_insert_time)

        return this.insert(insert_time, other, inplace=True)


class AlignRight(AlignmentKind):
    """Align instructions in as-late-as-possible manner.

    Instructions are placed at latest available timeslots.
    """

    def __init__(self):
        """Create new right-justified context."""
        super().__init__(context_params=())

    @property
    def is_sequential(self) -> bool:
        return False

    def align(self, schedule: Schedule) -> Schedule:
        """Reallocate instructions according to the policy.

        Only top-level sub-schedules are aligned. If sub-schedules are nested,
        nested schedules are not recursively aligned.

        Args:
            schedule: Schedule to align.

        Returns:
            Schedule with reallocated instructions.
        """
        aligned = Schedule.initialize_from(schedule)
        for _, child in reversed(schedule.children):
            aligned = self._push_right_prepend(aligned, child)

        return aligned

    @staticmethod
    def _push_right_prepend(
        this: Schedule, other: ScheduleComponent
    ) -> Schedule:
        """Insert ``other`` at the latest non-overlapping time in ``this``.

        This ensures ``other`` ends before it overlaps with any part of
        ``this``.

        If required, ``this`` is shifted to start late enough so that
        there is room to insert ``other``.

        Args:
           this: Input schedule to which ``other`` will be inserted.
           other: Other schedule to insert.

        Returns:
           Push right prepended schedule.
        """
        this_channels = set(this.channels)
        other_channels = set(other.channels)
        shared_channels = list(this_channels & other_channels)
        ch_slacks = [
            this.ch_start_time(channel) - other.ch_stop_time(channel)
            for channel in shared_channels
        ]

        if ch_slacks:
            insert_time = min(ch_slacks) + other.start_time
        else:
            insert_time = this.stop_time - other.stop_time + other.start_time

        if insert_time < 0:
            this.shift(-insert_time, inplace=True)
            this.insert(0, other, inplace=True)
        else:
            this.insert(insert_time, other, inplace=True)

        return this


class AlignSequential(AlignmentKind):
    """Align instructions sequentially.

    Instructions played on different channels are also arranged in a sequence.
    No buffer time is inserted in between instructions.
    """

    def __init__(self):
        """Create new sequential context."""
        super().__init__(context_params=())

    @property
    def is_sequential(self) -> bool:
        return True

    def align(self, schedule: Schedule) -> Schedule:
        """Reallocate instructions according to the policy.

        Only top-level sub-schedules are aligned. If sub-schedules are nested,
        nested schedules are not recursively aligned.

        Args:
            schedule: Schedule to align.

        Returns:
            Schedule with reallocated instructions.
        """
        aligned = Schedule.initialize_from(schedule)
        for _, child in schedule.children:
            aligned.insert(aligned.duration, child, inplace=True)

        return aligned


class AlignEquispaced(AlignmentKind):
    """Align instructions with equispaced interval within a specified duration.

    Instructions played on different channels are also arranged in a sequence.
    This alignment is convenient for creating dynamical decoupling
    sequences such as PDD.
    """

    def __init__(self, duration: int | ParameterExpression):
        """Create new equispaced context.

        Args:
            duration: Duration of this context. This should be larger than
                the schedule duration. If the specified duration is
                shorter than the schedule duration, no alignment is
                performed and the input schedule is just returned.
                This duration can be parametrized.
        """
        super().__init__(context_params=(duration,))

    @property
    def is_sequential(self) -> bool:
        return True

    @property
    def duration(self):
        """Return context duration."""
        return self._context_params[0]

    def align(self, schedule: Schedule) -> Schedule:
        """Reallocate instructions according to the policy.

        Only top-level sub-schedules are aligned. If sub-schedules are nested,
        nested schedules are not recursively aligned.

        Args:
            schedule: Schedule to align.

        Returns:
            Schedule with reallocated instructions.
        """
        instruction_duration_validation(self.duration)

        total_duration = sum(child.duration for _, child in schedule.children)
        if self.duration < total_duration:
            return schedule

        total_delay = self.duration - total_duration

        if len(schedule.children) > 1:
            # Calculate the interval in between sub-schedules.
            # If the duration cannot be divided by the number of sub-schedules,
            # the modulo is appended and prepended to the input schedule.
            interval, mod = np.divmod(total_delay, len(schedule.children) - 1)
        else:
            interval = 0
            mod = total_delay

        # Calculate pre schedule delay
        delay, mod = np.divmod(mod, 2)

        aligned = Schedule.initialize_from(schedule)
        # Insert sub-schedules with interval
        _t0 = int(aligned.stop_time + delay + mod)
        for _, child in schedule.children:
            aligned.insert(_t0, child, inplace=True)
            _t0 = int(aligned.stop_time + interval)

        return aligned


class AlignFunc(AlignmentKind):
    """Allocate instructions at position specified by callback function.

    The position is specified for each instruction of index ``j`` as a
    fractional coordinate in [0, 1] within the specified duration.

    Instructions played on different channels are also arranged in a sequence.
    This alignment is convenient for creating dynamical decoupling
    sequences such as UDD.

    For example, a UDD sequence with 10 pulses can be specified with the
    following function.

    .. code-block:: python

        import numpy as np


        def udd10_pos(j):
            return np.sin(np.pi * j / (2 * 10 + 2)) ** 2

    .. note::

        This context cannot be QPY serialized because of the callable. If
        you use this context, your program cannot be saved in QPY format.

    """

    def __init__(self, duration: int | ParameterExpression, func: Callable):
        """Create new equispaced context.

        Args:
            duration: Duration of this context. This should be larger than
                the schedule duration. If the specified duration is
                shorter than the schedule duration, no alignment is
                performed and the input schedule is just returned.
                This duration can be parametrized.
            func: A function that takes an index of sub-schedule and
                returns the
                fractional coordinate of that sub-schedule. The returned
                value should be defined within [0, 1]. The pulse index
                starts from 1.
        """
        super().__init__(context_params=(duration, func))

    @property
    def is_sequential(self) -> bool:
        return True

    @property
    def duration(self):
        """Return context duration."""
        return self._context_params[0]

    @property
    def func(self):
        """Return context alignment function."""
        return self._context_params[1]

    def align(self, schedule: Schedule) -> Schedule:
        """Reallocate instructions according to the policy.

        Only top-level sub-schedules are aligned. If sub-schedules are nested,
        nested schedules are not recursively aligned.

        Args:
            schedule: Schedule to align.

        Returns:
            Schedule with reallocated instructions.
        """
        instruction_duration_validation(self.duration)

        if self.duration < schedule.duration:
            return schedule

        aligned = Schedule.initialize_from(schedule)
        for ind, (_, child) in enumerate(schedule.children):
            _t_center = self.duration * self.func(ind + 1)
            _t0 = int(_t_center - 0.5 * child.duration)
            if _t0 < 0 or _t0 > self.duration:
                raise PulseError(
                    f"Invalid schedule position t={_t0} is specified at "
                    f"index={ind}"
                )
            aligned.insert(_t0, child, inplace=True)

        return aligned
