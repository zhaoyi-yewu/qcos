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
"""Frequency instructions.

These instructions allow the user to manipulate the frequency of a channel.
"""

from wy_qcos.transpiler.cmss.circuit.parameterexpression import (
    ParameterExpression,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.channels import PulseChannel
from wy_qcos.transpiler.common.pulse_ir.pulse.instructions.instruction import (
    Instruction,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


class SetFrequency(Instruction):
    r"""Set the channel frequency.

    This instruction operates on ``PulseChannel`` objects. A
    ``PulseChannel`` creates pulses of the form

    .. math::
        Re[\exp(i 2\pi f jdt + \phi) d_j].

    Here, :math:`f` is the channel frequency. The instruction
    ``SetFrequency`` lets the user set the value of :math:`f`. All pulses
    played on a channel after calling ``SetFrequency`` will use the new
    frequency.

    The duration of SetFrequency is 0.
    """

    @deprecate_pulse_func
    def __init__(
        self,
        frequency: float | ParameterExpression,
        channel: PulseChannel,
        name: str | None = None,
    ):
        """Creates a new set channel frequency instruction.

        Args:
            frequency: New frequency of the channel in Hz.
            channel: The channel this instruction operates on.
            name: Name of this set channel frequency instruction.
        """
        super().__init__(operands=(frequency, channel), name=name)

    def _validate(self):
        """Called after initialization to validate instruction data.

        Raises:
            PulseError: If the input ``channel`` is not of type
                :class:`PulseChannel`.
        """
        if not isinstance(self.channel, PulseChannel):
            raise PulseError(
                f"Expected a pulse channel, got {self.channel} instead."
            )

    @property
    def frequency(self) -> float | ParameterExpression:
        """New frequency."""
        return self.operands[0]

    @property
    def channel(self) -> PulseChannel:
        """Return the channel that this instruction is scheduled on."""
        return self.operands[1]

    @property
    def channels(self) -> tuple[PulseChannel]:
        """Returns the channels that this schedule uses."""
        return (self.channel,)

    @property
    def duration(self) -> int:
        """Duration of this instruction."""
        return 0


class ShiftFrequency(Instruction):
    """Shift the channel frequency away from the current frequency."""

    @deprecate_pulse_func
    def __init__(
        self,
        frequency: float | ParameterExpression,
        channel: PulseChannel,
        name: str | None = None,
    ):
        """Creates a new shift frequency instruction.

        Args:
            frequency: Frequency shift of the channel in Hz.
            channel: The channel this instruction operates on.
            name: Name of this set channel frequency instruction.
        """
        super().__init__(operands=(frequency, channel), name=name)

    def _validate(self):
        """Called after initialization to validate instruction data.

        Raises:
            PulseError: If the input ``channel`` is not of type
                :class:`PulseChannel`.
        """
        if not isinstance(self.channel, PulseChannel):
            raise PulseError(
                f"Expected a pulse channel, got {self.channel} instead."
            )

    @property
    def frequency(self) -> float | ParameterExpression:
        """Frequency shift from the set frequency."""
        return self.operands[0]

    @property
    def channel(self) -> PulseChannel:
        """Return the channel that this instruction is scheduled on."""
        return self.operands[1]

    @property
    def channels(self) -> tuple[PulseChannel]:
        """Returns the channels that this schedule uses."""
        return (self.channel,)

    @property
    def duration(self) -> int:
        """Duration of this instruction."""
        return 0
