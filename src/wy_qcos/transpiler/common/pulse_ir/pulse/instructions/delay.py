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
"""Delay instruction.

This blocks time on a channel and is useful for schedule alignment.
"""

from __future__ import annotations

from wy_qcos.transpiler.cmss.circuit.parameterexpression import (
    ParameterExpression,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.channels import Channel
from wy_qcos.transpiler.common.pulse_ir.pulse.instructions.instruction import (
    Instruction,
)
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


class Delay(Instruction):
    """A blocking instruction with no other effect.

    The delay is used for aligning and scheduling other instructions.

    Example:
        To schedule an instruction at time 10 on a channel assigned to the
        variable ``channel``, the following could be used::

            sched = Schedule(name="Delay instruction example")
            sched += Delay(10, channel)
            sched += Gaussian(duration, amp, sigma, channel)

        The ``channel`` will output no signal from time=0 up until time=10.
    """

    @deprecate_pulse_func
    def __init__(
        self,
        duration: int | ParameterExpression,
        channel: Channel,
        name: str | None = None,
    ):
        """Create a new delay instruction.

        No other instruction may be scheduled within a ``Delay``.

        Args:
            duration: Length of time of the delay in terms of dt.
            channel: The channel that will have the delay.
            name: Name of the delay for display purposes.
        """
        super().__init__(operands=(duration, channel), name=name)

    @property
    def channel(self) -> Channel:
        """Return the channel that this instruction is scheduled on."""
        return self.operands[1]

    @property
    def channels(self) -> tuple[Channel]:
        """Returns the channels that this schedule uses."""
        return (self.channel,)

    @property
    def duration(self) -> int | ParameterExpression:
        """Duration of this instruction."""
        return self.operands[0]
