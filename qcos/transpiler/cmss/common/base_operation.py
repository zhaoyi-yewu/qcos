#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from enum import Enum


class OperationType(Enum):
    """操作类型."""

    SINGLE_QUBIT_OPERATION = 1
    DOUBLE_QUBIT_OPERATION = 2
    TRIPLE_QUBIT_OPERATION = 3
    FOUR_QUBIT_OPERATION = 4
    FIVE_QUBIT_OPERATION = 5
    MEASURE = 0
    SYNC = -1
    MOVE = -2
    RESET = -3


class BaseOperation:
    """中间表示类基类."""

    def __init__(
        self,
        name,
        targets=None,
        arg_value=None,
        operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
    ) -> None:
        """Init BaseOperation.

        Args:
            name: 操作名称
            targets: 目标量子比特. Defaults to None.
            arg_value: 参数（旋转门所需）. Defaults to None.
            operation_type: 操作类型
        """
        self.name = name
        self.targets = targets
        # pylint: disable=use-list-literal
        self.arg_value = arg_value if arg_value is not None else list()
        if not isinstance(self.arg_value, list):
            self.arg_value = [self.arg_value]
        self.operation_type = operation_type

    def __repr__(self):
        return (
            f"{type(self).__name__}(targets={self.targets},"
            f"arg_value={self.arg_value})"
        )

    def to_openqasm(self, qubit_prefix: str = "q") -> str:
        """Convert the current operation into an OpenQASM statement.

        Examples:
            H               -> h q[0];
            RX(pi/2)        -> rx(pi/2) q[1];
            CX(0, 1)        -> cx q[0], q[1];

        Args:
            qubit_prefix (str):
                The prefix used for qubit identifiers in the output QASM code
                (e.g., "q" results in q[0], q[1], ...).

        Returns:
            str: A formatted OpenQASM instruction string.

        Raises:
            ValueError: If the operation contains no target qubits.
        """
        # Ensure that the operation has at least one target qubit
        if not self.targets:
            raise ValueError(
                "targets cannot be empty when generating OpenQASM statement."
            )

        # Build the argument part (e.g., rx(1.57))
        if self.arg_value:
            arg_str = "(" + ", ".join(map(str, self.arg_value)) + ")"
        else:
            arg_str = ""

        # Build the qubit target part (e.g., q[0], q[1])
        targets_str = ", ".join(f"{qubit_prefix}[{t}]" for t in self.targets)

        # Construct the full OpenQASM instruction
        return f"{self.name}{arg_str} {targets_str};"
