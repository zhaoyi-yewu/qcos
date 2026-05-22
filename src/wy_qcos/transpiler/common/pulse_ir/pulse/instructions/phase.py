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
"""Phase instructions.

These instructions update the modulation phase of pulses played on a
channel.

This includes ``SetPhase`` instructions which lock the modulation to a
particular phase at that moment, and ``ShiftPhase`` instructions which increase
the existing phase by a relative amount.
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


class ShiftPhase(Instruction):
    r"""Increase the phase of subsequent pulses on a channel.

    This updates the modulation phase of proceeding pulses played on the
    same :py:class:`~wy_qcos.pulse.channels.Channel`. It is a relative
    increase in phase determined by the ``phase`` operand.

    In particular, a PulseChannel creates pulses of the form

    .. math::
        Re[\exp(i 2\pi f jdt + \phi) d_j].

    The ``ShiftPhase`` instruction causes :math:`\phi` to be increased by
    the instruction's ``phase`` operand. This affects all later pulses on
    the same channel.

    The qubit phase is tracked in software, enabling instantaneous,
    nearly error-free Z-rotations by using a ShiftPhase to update the
    frame tracking the qubit state.
    """

    @deprecate_pulse_func
    def __init__(
        self,
        phase: complex | ParameterExpression,
        channel: PulseChannel,
        name: str | None = None,
    ):
        """Instantiate a shift phase instruction.

        This increases the output signal phase on ``channel`` by
        ``phase`` radians.

        Args:
            phase: The rotation angle in radians.
            channel: The channel this instruction operates on.
            name: Display name for this instruction.
        """
        super().__init__(operands=(phase, channel), name=name)

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
    def phase(self) -> complex | ParameterExpression:
        """Return the rotation angle enacted by this instruction in radians."""
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


class SetPhase(Instruction):
    r"""Set the phase of subsequent pulses on a channel.

    This sets the phase of the proceeding pulses on that channel to
    ``phase`` radians.

    In particular, a PulseChannel creates pulses of the form

    .. math::

        Re[\exp(i 2\pi f jdt + \phi) d_j]

    The ``SetPhase`` instruction sets :math:`\phi` to the instruction's
    ``phase`` operand.
    """

    @deprecate_pulse_func
    def __init__(
        self,
        phase: complex | ParameterExpression,
        channel: PulseChannel,
        name: str | None = None,
    ):
        """Instantiate a set phase instruction.

        This sets the output signal phase on ``channel`` to ``phase``
        radians.

        Args:
            phase: The rotation angle in radians.
            channel: The channel this instruction operates on.
            name: Display name for this instruction.
        """
        super().__init__(operands=(phase, channel), name=name)

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
    def phase(self) -> complex | ParameterExpression:
        """Return the rotation angle enacted by this instruction in radians."""
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
