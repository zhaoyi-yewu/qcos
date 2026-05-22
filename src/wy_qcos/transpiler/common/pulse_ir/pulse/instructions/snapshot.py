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
"""Snapshot instruction.

This simulator instruction captures output within a simulation. Available
snapshot types depend on the simulator being used.
"""

from wy_qcos.transpiler.common.pulse_ir.pulse.channels import SnapshotChannel
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.pulse.instructions.instruction import (
    Instruction,
)
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


class Snapshot(Instruction):
    """Capture a moment in a simulation."""

    @deprecate_pulse_func
    def __init__(
        self,
        label: str,
        snapshot_type: str = "statevector",
        name: str | None = None,
    ):
        """Create new snapshot.

        Args:
            label: Snapshot label used to identify the snapshot in the
                output.
            snapshot_type: Type of snapshot, for example ``state`` to take a
                snapshot of the quantum state. Available snapshot types are
                defined by the simulator.
            name: Snapshot name, which defaults to ``label``. This parameter
                is only for display purposes and is not considered during
                comparison.
        """
        self._channel = SnapshotChannel()

        if name is None:
            name = label
        super().__init__(operands=(label, snapshot_type), name=name)

    def _validate(self):
        """Called after initialization to validate instruction data.

        Raises:
            PulseError: If snapshot label is invalid.
        """
        if not isinstance(self.label, str):
            raise PulseError("Snapshot label must be a string.")

    @property
    def label(self) -> str:
        """Label of snapshot."""
        return self.operands[0]

    @property
    def type(self) -> str:
        """Type of snapshot."""
        return self.operands[1]

    @property
    def channel(self) -> SnapshotChannel:
        """Return the ``SnapshotChannel`` used by this instruction."""
        return self._channel

    @property
    def channels(self) -> tuple[SnapshotChannel]:
        """Returns the channels that this schedule uses."""
        return (self.channel,)

    @property
    def duration(self) -> int:
        """Duration of this instruction."""
        return 0

    def is_parameterized(self) -> bool:
        """Return True iff the instruction is parameterized."""
        return False
