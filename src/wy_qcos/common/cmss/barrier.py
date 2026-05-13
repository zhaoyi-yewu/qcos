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

"""Circuit-level Barrier instruction."""

from wy_qcos.common.cmss.base_operation import (
    BaseOperation,
    OperationType,
)


class Barrier(BaseOperation):
    """For PulseIR: Barrier instruction.

    It prevents instruction reordering across the barrier.
    """

    def __init__(self, num_qubits=0, name="barrier"):
        targets = list(range(num_qubits)) if num_qubits > 0 else []
        super().__init__(
            name=name,
            targets=targets,
            operation_type=OperationType.SYNC.value,
        )
        self._num_qubits = num_qubits

    @property
    def duration(self):
        """Barrier has zero duration."""
        return 0

    @property
    def params(self):
        """Return instruction params."""
        return []

    def __repr__(self):
        return f"Barrier(num_qubits={self._num_qubits})"


__all__ = ["Barrier"]
