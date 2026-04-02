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

"""Binding qcos transpiler cpp functions."""

from __future__ import annotations
import typing

__all__: list[str] = [
    "BaseOperation",
    "DOUBLE_QUBIT_OPERATION",
    "FIVE_QUBIT_OPERATION",
    "FOUR_QUBIT_OPERATION",
    "GateOperation",
    "MEASURE",
    "MOVE",
    "OperationType",
    "SABRE",
    "SINGLE_QUBIT_OPERATION",
    "SYNC",
    "TRIPLE_QUBIT_OPERATION",
    "load_config_file",
    "load_qasm_to_gate_list",
]

class BaseOperation:
    def __init__(
        self,
        name: str,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    @property
    def arg_value(self) -> list[float]: ...
    @property
    def name(self) -> str: ...
    @property
    def operation_type(self) -> OperationType: ...
    @property
    def targets(self) -> list[int]: ...

class GateOperation(BaseOperation):
    def __init__(
        self,
        name: str,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
        hermitian: bool = False,
    ) -> None: ...
    @property
    def hermitian(self) -> bool: ...

class OperationType:
    """Members.

    MEASURE

    SINGLE_QUBIT_OPERATION

    DOUBLE_QUBIT_OPERATION

    TRIPLE_QUBIT_OPERATION

    FOUR_QUBIT_OPERATION

    FIVE_QUBIT_OPERATION

    SYNC

    MOVE
    """

    DOUBLE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.DOUBLE_QUBIT_OPERATION: 2>
    FIVE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.FIVE_QUBIT_OPERATION: 5>
    FOUR_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.FOUR_QUBIT_OPERATION: 4>
    MEASURE: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.MEASURE: 0>
    MOVE: typing.ClassVar[OperationType]  # value = <OperationType.MOVE: -2>
    SINGLE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.SINGLE_QUBIT_OPERATION: 1>
    SYNC: typing.ClassVar[OperationType]  # value = <OperationType.SYNC: -1>
    TRIPLE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.TRIPLE_QUBIT_OPERATION: 3>
    __members__: typing.ClassVar[dict[str, OperationType]]
    # value = {'MEASURE': <OperationType.MEASURE: 0>
    # 'SINGLE_QUBIT_OPERATION': <OperationType.SINGLE_QUBIT_OPERATION: 1>
    # 'DOUBLE_QUBIT_OPERATION': <OperationType.DOUBLE_QUBIT_OPERATION: 2>
    # 'TRIPLE_QUBIT_OPERATION': <OperationType.TRIPLE_QUBIT_OPERATION: 3>
    # 'FOUR_QUBIT_OPERATION': <OperationType.FOUR_QUBIT_OPERATION: 4>
    # 'FIVE_QUBIT_OPERATION': <OperationType.FIVE_QUBIT_OPERATION: 5>
    # 'SYNC': <OperationType.SYNC: -1>
    # 'MOVE': <OperationType.MOVE: -2>}
    def __eq__(self, other: typing.Any) -> bool: ...
    def __getstate__(self) -> int: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __ne__(self, other: typing.Any) -> bool: ...
    def __repr__(self) -> str: ...
    def __setstate__(self, state: int) -> None: ...
    def __str__(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> int: ...

class SABRE:
    """SABRE quantum routing algorithm."""
    def __init__(
        self,
        coupling_list: list[tuple[int, int]],
        extention_size: int = 20,
        weight: float = 0.5,
        decay: float = 0.001,
    ) -> None:
        """SABRE constructor.

        Args:
            coupling_list (list[tuple[int, int]]): Physical qubit connectivity
                graph.
            extention_size (int, optional): Size of the lookahead set.
                Defaults to 20.
            weight (float, optional): Weight between front layer and lookahead
                cost. Defaults to 0.5.
            decay (float, optional): SWAP decay coefficient. Defaults to 0.001.
        """
    def execute(
        self, gates_list: list[GateOperation], initial_l2p: list[int] = []
    ) -> None:
        """Execute SABRE routing.

        Args:
            gates_list (list[GateOperation]): Logical gate sequence.
            initial_l2p (list[int], optional): Initial logical-to-physical
                mapping. Defaults to empty.

        Returns:
            None
        """
    def get_physical_gates(self) -> list[GateOperation]:
        """Get the sequence of mapped physical gates after routing.

        Returns:
            list[GateOperation]: The physical gate sequence.
        """

def load_config_file(filename: str) -> list[tuple[int, int]]:
    """从配置文件中加载量子芯片耦合列表.

    Args:
        filename (str): 配置文件路径

    Returns:
        list[tuple[int,int]]: 耦合对列表
    """

def load_qasm_to_gate_list(filename: str) -> list[GateOperation]:
    """将QASM文件加载为门操作列表.

    Args:
        filename (str): QASM文件路径

    Returns:
        list[GateOperation]: 解析得到的门操作列表
    """

DOUBLE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.DOUBLE_QUBIT_OPERATION: 2>
)
FIVE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.FIVE_QUBIT_OPERATION: 5>
)
FOUR_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.FOUR_QUBIT_OPERATION: 4>
)
MEASURE: OperationType  # value = <OperationType.MEASURE: 0>
MOVE: OperationType  # value = <OperationType.MOVE: -2>
SINGLE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.SINGLE_QUBIT_OPERATION: 1>
)
SYNC: OperationType  # value = <OperationType.SYNC: -1>
TRIPLE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.TRIPLE_QUBIT_OPERATION: 3>
)
