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

from __future__ import annotations


class CircuitInstruction:
    """电路中的单条指令，对应 QuantumCircuit.instructions 中的元素.

    对应 qiskit QuantumCircuit.data 字段。

    实例包含三个核心字段：``operation`` 表示门操作对象，需具备
    ``.name``、``.params``、``.duration`` 属性；``qubits`` 为该指令
    作用的量子比特索引列表；``clbits`` 为该指令关联的经典比特索引
    列表，主要用于测量门。
    """

    __slots__ = ("operation", "qubits", "clbits")

    def __init__(self, operation, qubits: list, clbits: list | None = None):
        self.operation = operation
        self.qubits = list(qubits)
        self.clbits = list(clbits) if clbits is not None else []

    def __repr__(self) -> str:
        return (
            f"CircuitInstruction("
            f"op={self.operation!r}, "
            f"qubits={self.qubits}, "
            f"clbits={self.clbits})"
        )
