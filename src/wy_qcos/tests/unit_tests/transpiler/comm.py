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

from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.utils import is_equal
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator


def validate_gate_ir(
    actual: GateOperation,
    name: str,
    targets: list,
    q_type: int,
    q_hermitian: bool,
):
    assert actual.hermitian == q_hermitian
    assert actual.name == name
    assert actual.targets == targets
    assert actual.operation_type == q_type


def validate_non_gate_ir(
    actual: GateOperation, name: str, targets: list, q_type: int
):
    assert actual.name == name
    assert actual.targets == targets
    assert actual.operation_type == q_type


def validate_ir_equals(source, result):
    source_qc = QuantumCircuit.from_ir(source)
    source_op = Operator(source_qc)

    result_qc = QuantumCircuit.from_ir(result)
    result_op = Operator(result_qc)
    assert source_op.equiv(result_op) is True


def validate_gates_in_targets(final_gates, targets):
    for gate in final_gates:
        if gate.name not in targets:
            assert False, f"{gate.name} is not in targets"
    assert True


def read_qasm_from_file(file_path):
    try:
        with open(file_path, encoding="utf-8") as file:
            qasm_data = file.read()
            return qasm_data
    except FileNotFoundError:
        print(f"{file_path} not found.")
    except Exception as e:
        print(f"读取文件时发生错误: {str(e)}")
    return None


def validate_optimize_result(
    circ1: QuantumCircuit | DAGCircuit | list,
    circ2: QuantumCircuit | DAGCircuit | list,
    num_qubits1: int = 0,
    num_qubits2: int = 0,
):
    """Assert that whether two circuits are equal after optimization.

    Args:
        circ1 (QuantumCircuit | DAGCircuit | list): first circuit.
        circ2 (QuantumCircuit | DAGCircuit | list): second circuit.
        num_qubits1 (int, optional): The number of qubits in circ1, It must be
            provided only if optimization could alter the circuit width.
        num_qubits2 (int, optional): Like above.
    """
    # convert circ1 to QuantumCircuit
    if isinstance(circ1, list):
        circ1 = QuantumCircuit.from_ir(circ1, num_qubits1)
    elif isinstance(circ1, DAGCircuit):
        circ1 = DAGCircuit.dag_to_circuit(circ1, num_qubits1)
    # convert circ2 to QuantumCircuit
    if isinstance(circ2, list):
        circ2 = QuantumCircuit.from_ir(circ2, num_qubits2)
    elif isinstance(circ2, DAGCircuit):
        circ2 = DAGCircuit.dag_to_circuit(circ2, num_qubits2)

    if not isinstance(circ1, QuantumCircuit) or not isinstance(
        circ2, QuantumCircuit
    ):
        raise ValueError("input should be QuantumCircuit.")
    # validate
    assert is_equal(circ1, circ2)
