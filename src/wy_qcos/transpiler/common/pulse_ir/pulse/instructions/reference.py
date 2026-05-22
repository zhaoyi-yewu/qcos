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
"""Reference instruction that is a placeholder for subroutine."""

from __future__ import annotations

from wy_qcos.transpiler.cmss.circuit.parameterexpression import (
    ParameterExpression,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.channels import Channel
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import (
    PulseError,
    UnassignedReferenceError,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.instructions import instruction
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


class Reference(instruction.Instruction):
    """Pulse compiler directive that refers to a subroutine.

    If a pulse program uses the same subset of instructions multiple times,
    then using the :class:`~.Reference` class may significantly reduce the
    program memory footprint. This instruction only stores the set of
    strings that identify the subroutine.

    The actual pulse program can be stored in the
    :attr:`ScheduleBlock.references` of the :class:`.ScheduleBlock` that
    this reference instruction belongs to.

    You can later assign schedules with the
    :meth:`ScheduleBlock.assign_references` method. This lets you build the
    main program without knowing the actual subroutine, which can be
    supplied later.
    """

    # Delimiter for representing nested scope.
    scope_delimiter = "::"

    # Delimiter for tuple keys.
    key_delimiter = ","

    @deprecate_pulse_func
    def __init__(self, name: str, *extra_keys: str):
        """Create new reference.

        Args:
            name: Name of subroutine.
            extra_keys: Optional. A set of string keys that may be necessary to
                refer to a particular subroutine. For example, when we use
                "sx" as a name to refer to the subroutine of an sx pulse,
                this name might be used among schedules for different qubits.
                In this example, you may specify "q0" in the extra keys
                to distinguish the sx schedule for qubit 0 from others.
                The user can use an arbitrary number of extra string keys to
                uniquely determine the subroutine.
        """
        # Run validation
        ref_keys = (name,) + tuple(extra_keys)
        super().__init__(operands=ref_keys, name=name)

    def _validate(self):
        """Called after initialization to validate instruction data.

        Raises:
            PulseError: When a key is not a string.
            PulseError: When a key in ``ref_keys`` contains the scope
                delimiter.
        """
        for key in self.ref_keys:
            if not isinstance(key, str):
                raise PulseError(
                    f"Keys must be strings. {key!r} is not a valid object."
                )
            if self.scope_delimiter in key or self.key_delimiter in key:
                raise PulseError(
                    f"'{self.scope_delimiter}' and '{self.key_delimiter}' "
                    "are reserved. "
                    f"'{key}' is not a valid key string."
                )

    @property
    def ref_keys(self) -> tuple[str, ...]:
        """Returns unique key of the subroutine."""
        return self.operands

    @property
    def duration(self) -> int | ParameterExpression:
        """Duration of this instruction."""
        raise UnassignedReferenceError(
            f"Subroutine is not assigned to {self.ref_keys}."
        )

    @property
    def channels(self) -> tuple[Channel, ...]:
        """Returns the channels that this schedule uses."""
        raise UnassignedReferenceError(
            f"Subroutine is not assigned to {self.ref_keys}."
        )

    @property
    def parameters(self) -> set:
        """Parameters which determine the instruction behavior."""
        return set()

    def __repr__(self) -> str:
        joined_keys = self.key_delimiter.join(self.ref_keys)
        return f"{self.__class__.__name__}({joined_keys})"
