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
"""Instruction base class.

``Instruction`` objects are single operations within a
:py:class:`~wy_qcos.pulse.Schedule` and can be used the same way as
:py:class:`~wy_qcos.pulse.Schedule` objects.

For example::

    duration = 10
    channel = DriveChannel(0)
    sched = Schedule()
    sched += Delay(
        duration, channel
    )  # Delay is a specific subclass of Instruction
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import cast

from wy_qcos.transpiler.cmss.circuit.parameter import Parameter
from wy_qcos.transpiler.cmss.circuit.parameterexpression import (
    ParameterExpression,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.channels import Channel
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


# pylint: disable=bad-docstring-quotes


class Instruction(ABC):
    """The smallest schedulable unit.

    An instruction has a fixed duration and a set of specified channels.
    """

    @deprecate_pulse_func
    def __init__(
        self,
        operands: tuple,
        name: str | None = None,
    ):
        """Instruction initializer.

        Args:
            operands: The argument list.
            name: Optional display name for this instruction.
        """
        self._operands = operands
        self._name = name
        self._validate()

    def _validate(self):
        """Called after initialization to validate instruction data.

        Raises:
            PulseError: If the input ``channels`` are not all of type
                :class:`Channel`.
        """
        for channel in self.channels:
            if not isinstance(channel, Channel):
                raise PulseError(f"Expected a channel, got {channel} instead.")

    @property
    def name(self) -> str | None:
        """Name of this instruction."""
        return self._name

    @property
    def id(self) -> int:  # pylint: disable=invalid-name
        """Unique identifier for this instruction."""
        return id(self)

    @property
    def operands(self) -> tuple:
        """Return instruction operands."""
        return self._operands

    @property
    @abstractmethod
    def channels(self) -> tuple[Channel, ...]:
        """Returns the channels that this schedule uses."""
        raise NotImplementedError

    @property
    def start_time(self) -> int:
        """Relative begin time of this instruction."""
        return 0

    @property
    def stop_time(self) -> int:
        """Relative end time of this instruction."""
        return cast(int, self.duration)

    @property
    def duration(self) -> int | ParameterExpression:
        """Duration of this instruction."""
        raise NotImplementedError

    @property
    def _children(self) -> tuple[Instruction, ...]:
        """Instruction has no child nodes."""
        return ()

    @property
    def instructions(self) -> tuple[tuple[int, Instruction], ...]:
        """Iterable for getting instructions from Schedule tree."""
        return tuple(self._instructions())

    def ch_duration(self, *channels: Channel) -> int:
        """Return duration of the supplied channels in this Instruction.

        Args:
            *channels: Supplied channels
        """
        return self.ch_stop_time(*channels)

    def ch_start_time(self, *channels: Channel) -> int:
        # pylint: disable=unused-argument
        """Return minimum start time for supplied channels.

        Args:
            *channels: Supplied channels
        """
        return 0

    def ch_stop_time(self, *channels: Channel) -> int:
        """Return maximum start time for supplied channels.

        Args:
            *channels: Supplied channels
        """
        if any(chan in self.channels for chan in channels):
            return cast(int, self.duration)
        return 0

    def _instructions(
        self, time: int = 0
    ) -> Iterable[tuple[int, Instruction]]:
        """Iterable for flattening Schedule tree.

        Args:
            time: Shifted time of this node due to parent

        Yields:
            Tuple[int, Union['Schedule, 'Instruction']]: Tuple of the form
                (start_time, instruction).
        """
        yield (time, self)

    def shift(self, time: int, name: str | None = None):
        """Return a new schedule shifted forward by `time`.

        Args:
            time: Time to shift by
            name: Name of the new schedule. Defaults to name of self

        Returns:
            Schedule: The shifted schedule.
        """
        from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import Schedule

        if name is None:
            name = self.name
        return Schedule((time, self), name=name)

    def insert(self, start_time: int, schedule, name: str | None = None):
        """Insert ``schedule`` into this instruction at ``start_time``.

        This returns a new :class:`~wy_qcos.pulse.Schedule` containing both
        objects.

        Args:
            start_time: Time to insert the schedule.
            schedule (Union['Schedule', 'Instruction']): Schedule or
                instruction to insert.
            name: Name of the new schedule. Defaults to this instruction's
                name.

        Returns:
            Schedule: A new schedule with ``schedule`` inserted alongside
                this instruction at t=0.
        """
        from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import Schedule

        if name is None:
            name = self.name
        return Schedule(self, (start_time, schedule), name=name)

    def append(self, schedule, name: str | None = None):
        """Append ``schedule`` after this instruction.

        The insertion point is the maximum time over all channels shared by
        ``self`` and ``schedule``.

        Args:
            schedule (Union['Schedule', 'Instruction']): Schedule or
                instruction to append.
            name: Name of the new schedule. Defaults to this instruction's
                name.

        Returns:
            Schedule: A new schedule with ``schedule`` appended after this
                instruction at t=0.
        """
        common_channels = set(self.channels) & set(schedule.channels)
        time = self.ch_stop_time(*common_channels)
        return self.insert(time, schedule, name=name)

    @property
    def parameters(self) -> set:
        """Parameters which determine the instruction behavior."""

        def _get_parameters_recursive(obj):
            params = set()
            if hasattr(obj, "parameters"):
                for param in obj.parameters:
                    if isinstance(param, Parameter):
                        params.add(param)
                    else:
                        params |= _get_parameters_recursive(param)
            return params

        parameters = set()
        for op in self.operands:
            parameters |= _get_parameters_recursive(op)
        return parameters

    def is_parameterized(self) -> bool:
        """Return True iff the instruction is parameterized."""
        return any(self.parameters)

    def __eq__(self, other: object) -> bool:
        """Check if this Instruction is equal to the `other` instruction.

        Equality is determined by the instruction sharing the same operands
        and channels.
        """
        if not isinstance(other, Instruction):
            return NotImplemented
        return (
            isinstance(other, type(self)) and self.operands == other.operands
        )

    def __hash__(self) -> int:
        return hash((type(self), self.operands, self.name))

    def __add__(self, other):
        """Append ``other`` after this instruction.

        Args:
            other (Union['Schedule', 'Instruction']): Schedule or
                instruction to append.

        Returns:
            Schedule: A new schedule with ``other`` appended after this
                instruction at t=0.
        """
        return self.append(other)

    def __or__(self, other):
        """Return a new schedule which is the union of `self` and `other`.

        Args:
            other (Union['Schedule', 'Instruction']): Schedule or
                instruction to union with.

        Returns:
            Schedule: A new schedule with ``other`` inserted alongside this
                instruction at t=0.
        """
        return self.insert(0, other)

    def __lshift__(self, time: int):
        """Return a new schedule which is shifted forward by `time`.

        Returns:
            Schedule: The shifted schedule
        """
        return self.shift(time)

    def __repr__(self) -> str:
        operands = ", ".join(str(op) for op in self.operands)
        name_repr = f", name='{self.name}'" if self.name else ""
        return f"{self.__class__.__name__}({operands}{name_repr})"
