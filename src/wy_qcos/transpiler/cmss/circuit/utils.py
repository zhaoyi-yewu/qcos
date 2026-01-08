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

import random
import numpy as np

from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator
from wy_qcos.transpiler.cmss.common.gate_operation import create_gate
from wy_qcos.common.constant import Constant


def random_circuit(
    num_qubits: int,
    num_gates: int,
    basis_gates: tuple = ("x", "s", "sdg", "t", "tdg", "z", "h", "rz", "cx"),
    seed=None,
):
    """Generate a random ir.

    Args:
        num_qubits (int): number of qubits.
        num_gates (int): number of gates.
        basis_gates (tuple, optional): basis gates. Defaults to ("x", "s",
            "sdg", "t", "tdg", "z", "h", "rz", "cx").
        seed: random seed.

    Returns:
        list: random ir list.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    ir = []
    for _ in range(num_gates):
        gate_name = random.choice(basis_gates)
        if gate_name in Constant.SINGLE_QUBIT_GATE_LIST:
            qubit = random.randint(0, num_qubits - 1)
            gate = create_gate(gate_name, targets=[qubit])
        elif gate_name in Constant.TWO_QUBIT_GATE_LIST:
            if num_qubits < 2:
                raise ValueError(f"{gate_name} gate need at least 2 qubits")
            qubits = random.sample(range(num_qubits), 2)
            gate = create_gate(gate_name, targets=qubits)
        elif gate_name in Constant.THREE_QUBIT_GATE_LIST:
            if num_qubits < 3:
                raise ValueError(f"{gate_name} gate need at least 3 qubits")
            qubits = random.sample(range(num_qubits), 3)
            gate = create_gate(gate_name, targets=qubits)
        else:
            raise NotImplementedError(f"{gate_name} gate is not implemented")

        if gate_name in ("rz", "rx", "ry"):
            angle = np.random.uniform(0, 2 * np.pi)
            gate.arg_value = [angle]

        ir.append(gate)

    return ir


def is_equal(circ1: QuantumCircuit, circ2: QuantumCircuit) -> bool:
    """Compare two quantum circuits.

    Args:
        circ1 (QuantumCircuit): the first quantum circuit.
        circ2 (QuantumCircuit): the second quantum circuit.

    Returns:
        bool: equal or not.
    """
    op1 = Operator(circ1)
    op2 = Operator(circ2)
    return op1.equiv(op2)
