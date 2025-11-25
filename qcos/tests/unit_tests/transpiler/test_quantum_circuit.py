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

import pytest
from pathlib import Path

from qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from qcos.transpiler.cmss.common.gate_operation import X, H, CX
from qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from qcos.transpiler.cmss.transpiler_cmd_line import (
    read_qasm_from_file,
)
from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir


@pytest.mark.usefixtures("global_configs")
class TestQuantumCircuit:
    def test_quantum_circuit_init(self):
        qc = QuantumCircuit(num_qubits=2, num_clbits=2)

        assert qc.num_qubits == 2
        assert qc.num_clbits == 2
        assert len(qc.get_operations()) == 0

    def test_quantum_circuit_append(self):
        qc = QuantumCircuit(num_qubits=2, num_clbits=2)
        gate1 = X([0])
        gate2 = CX([0, 1])
        gate3 = H([1])
        gates_list = [gate1, gate2, gate3]
        for gate in gates_list:
            qc.append(gate)

        gates = qc.get_operations()
        assert len(gates) == 3
        assert gates[0].name == "x" and gates[0].targets == [0]
        assert gates[1].name == "cx" and gates[1].targets == [0, 1]
        assert gates[2].name == "h" and gates[2].targets == [1]

    def test_quantum_circuit_append_operations(self):
        qc = QuantumCircuit()
        gate1 = X([0])
        gate2 = CX([0, 1])
        gate3 = H([1])
        qc.set_num_qubits(2)
        qc.set_num_clbits(2)
        assert qc.num_qubits == 2 and qc.num_clbits == 2

        gates_list = [gate1, gate2, gate3]
        qc.append_operations(gates_list)
        gates = qc.get_operations()
        assert len(gates) == 3
        assert gates[0].name == "x" and gates[0].targets == [0]
        assert gates[1].name == "cx" and gates[1].targets == [0, 1]
        assert gates[2].name == "h" and gates[2].targets == [1]

    def test_quantum_circuit_depth_width(self):
        qasm_path = GLOBAL_CONFIGS["samples_dir"]
        qasm_file = f"{qasm_path}/qasm/2.0/simple-qasm.qasm"
        file_path = Path(qasm_file).resolve()
        qasm_data = read_qasm_from_file(str(file_path))
        cir = get_ir(get_abs_tree(qasm_data))
        depth = cir.depth()
        width = cir.width()
        assert depth == 2
        assert width == 4
        assert cir.num_qubits == 2
