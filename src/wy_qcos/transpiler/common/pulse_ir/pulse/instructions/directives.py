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
"""Compiler directives for pulse programs."""

from __future__ import annotations

from abc import ABC

from wy_qcos.transpiler.common.pulse_ir.pulse import channels as chans
from wy_qcos.transpiler.common.pulse_ir.pulse.instructions import instruction
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


class Directive(instruction.Instruction, ABC):
    """A compiler directive.

    This is a hint to the pulse compiler and is not loaded into hardware.
    """

    @property
    def duration(self) -> int:
        """Duration of this instruction."""
        return 0


class RelativeBarrier(Directive):
    """Pulse ``RelativeBarrier`` directive."""

    @deprecate_pulse_func
    def __init__(self, *channels: chans.Channel, name: str | None = None):
        """Create a relative barrier directive.

        The barrier directive blocks instructions within the same schedule
        as the barrier on channels contained within this barrier from moving
        through the barrier in time.

        Args:
            channels: The channel that the barrier applies to.
            name: Name of the directive for display purposes.
        """
        super().__init__(operands=tuple(channels), name=name)

    @property
    def channels(self) -> tuple[chans.Channel, ...]:
        """Returns the channels that this schedule uses."""
        return self.operands

    def __eq__(self, other: object) -> bool:
        """Verify two barriers are equivalent."""
        return isinstance(other, type(self)) and set(self.channels) == set(
            other.channels
        )


class TimeBlockade(Directive):
    """Pulse ``TimeBlockade`` directive.

    This instruction is intended for internal use within the pulse builder
    when converting :class:`.Schedule` into :class:`.ScheduleBlock`.
    Because :class:`.ScheduleBlock` cannot take an absolute instruction
    time interval, this directive helps the block representation find an
    instruction start time.

    Example:
        This schedule plays constant pulse at t0 = 120.

        .. code-block:: python

            from wy_qcos.transpiler.common.pulse_ir.pulse import (
                Schedule,
                Play,
                Constant,
                DriveChannel,
            )

            schedule = Schedule()
            schedule.insert(120, Play(Constant(10, 0.1), DriveChannel(0)))

        This schedule block is expected to be identical to the schedule
        above at execution time.

        .. code-block:: python

            from wy_qcos.transpiler.common.pulse_ir.pulse import (
                ScheduleBlock,
                Play,
                Constant,
                DriveChannel,
            )
            from wy_qcos.transpiler.common.pulse_ir.pulse.instructions import (
                TimeBlockade,
            )

            block = ScheduleBlock()
            block.append(TimeBlockade(120, DriveChannel(0)))
            block.append(Play(Constant(10, 0.1), DriveChannel(0)))

        Such conversion may be done by

        .. code-block:: python

            from wy_qcos.transpiler.common.pulse_ir.pulse.transforms import (
                block_to_schedule,
                remove_directives,
            )

            schedule = remove_directives(block_to_schedule(block))


    .. note::

        The TimeBlockade instruction behaves almost identically
        to :class:`~wy_qcos.pulse.instructions.Delay` instruction.
        However, ``TimeBlockade`` is only a compiler directive and must be
        removed before execution. This may be done by the
        :func:`~wy_qcos.pulse.transforms.remove_directives` transform. Once
        these directives are removed, occupied timeslots are released and
        the user can insert another instruction without timing overlap.
    """

    @deprecate_pulse_func
    def __init__(
        self,
        duration: int,
        channel: chans.Channel,
        name: str | None = None,
    ):
        """Create a time blockade directive.

        Args:
            duration: Length of time of the occupation in terms of dt.
            channel: The channel that will be the occupied.
            name: Name of the time blockade for display purposes.
        """
        super().__init__(operands=(duration, channel), name=name)

    def _validate(self):
        """Called after initialization to validate instruction data.

        Raises:
            PulseError: If the input ``duration`` is not integer value.
        """
        if not isinstance(self.duration, int):
            raise PulseError(
                "TimeBlockade duration cannot be parameterized. Specify an "
                "integer duration value."
            )

    @property
    def channel(self) -> chans.Channel:
        """Return the channel that this instruction is scheduled on."""
        return self.operands[1]

    @property
    def channels(self) -> tuple[chans.Channel]:
        """Returns the channels that this schedule uses."""
        return (self.channel,)

    @property
    def duration(self) -> int:
        """Duration of this instruction."""
        return self.operands[0]
