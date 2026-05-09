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

from unittest.mock import patch
from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.common.cmss.gate_operation import X, H, CX
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit


class TestDG:
    def test_get_shared_qubits(self):
        dg = DG()
        gate1 = ("x", (0,), [])
        gate2 = ("h", (1,), [])
        gate3 = ("cx", (0, 1), [])
        node_id1 = dg.add_gate(gate1)
        node_id2 = dg.add_gate(gate2)
        node_id3 = dg.add_gate(gate3)

        shared_1_2 = dg.get_shared_qubits(node_id1, node_id2)
        shared_1_3 = dg.get_shared_qubits(node_id1, node_id3)
        assert len(shared_1_2) == 0
        assert shared_1_3 == [0]

    def test_add_gate(self):
        dg = DG()
        gate1 = ("x", (0,), [])
        assert dg.qubit_to_node[0] is None
        node_id1 = dg.add_gate(gate1)
        assert dg.node_count == 1
        assert dg.num_gate_1q == 1
        assert dg.qubit_to_node[0] is node_id1

        gate2 = ("cx", (0, 1), [])
        node_id2 = dg.add_gate(gate2)
        assert dg.node_count == 2
        assert dg.num_gate_2q == 1
        assert dg.qubit_to_node[0] is node_id2
        assert dg.qubit_to_node[1] is node_id2

    def test_add_line(self):
        dg = DG()
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        node_id1 = dg.add_gate(gate1, add_edges=False)
        node_id2 = dg.add_gate(gate2, add_edges=False)
        assert not dg.has_edge(node_id1, node_id2)
        dg.add_line(node_id1, node_id2)
        assert dg.has_edge(node_id1, node_id2)

    def test_get_node_depth(self):
        dg = DG()
        gate1 = ("x", (0,), [])
        gate2 = ("cx", (0, 1), [])
        node_id1 = dg.add_gate_absorb(gate1)
        assert dg.get_node_depth(node_id1) == 1
        node_id2 = dg.add_gate_absorb(gate2)
        assert dg.get_node_depth(node_id1) == 2
        assert node_id1 == node_id2

    def test_check_direct_dependency(self):
        dg = DG()
        gate1 = ("x", (0,), [])
        gate2 = ("h", (1,), [])
        node_id1 = dg.add_gate(gate1)
        node_id2 = dg.add_gate(gate2)
        assert not dg.check_direct_dependency(node_id1, node_id2)

        gate3 = ("h", (0,), [])
        node_id3 = dg.add_gate(gate3)
        assert dg.check_direct_dependency(node_id1, node_id3)
        assert not dg.check_direct_dependency(node_id2, node_id3)

        gate4 = ("cx", (0, 1), [])
        node_id4 = dg.add_gate(gate4)
        assert not dg.check_direct_dependency(node_id1, node_id4)
        assert dg.check_direct_dependency(node_id2, node_id4)
        assert dg.check_direct_dependency(node_id3, node_id4)

    @patch.object(DG, "check_direct_dependency")
    def test_check_absorbable(self, mock_check_direct_dependency):
        dg = DG()
        gate1 = ("x", (0,), [])
        gate2 = ("h", (1,), [])
        node_id1 = dg.add_gate(gate1)
        node_id2 = dg.add_gate(gate2)
        assert not dg.check_absorbable(node_id1, node_id2)
        assert mock_check_direct_dependency.call_count == 0

        gate3 = ("h", (0,), [])
        node_id3 = dg.add_gate(gate3)
        assert dg.check_absorbable(node_id1, node_id3)
        assert mock_check_direct_dependency.call_count == 1

    def test_check_parallel(self):
        dg = DG()
        gate1 = ("x", (0,), [])
        gate2 = ("h", (1,), [])
        gate3 = ("h", (0,), [])
        node_id1 = dg.add_gate(gate1)
        node_id2 = dg.add_gate(gate2)
        node_id3 = dg.add_gate(gate3)
        assert dg.check_parallel(node_id1, node_id2)
        assert not dg.check_parallel(node_id1, node_id3)
        assert dg.check_parallel(node_id2, node_id3)

    def test_cascade_node_direct_dependency(self):
        dg = DG()
        gate1 = ("x", (0,), [])
        gate2 = ("h", (1,), [])
        gate3 = ("h", (0,), [])
        node_id1 = dg.add_gate(gate1)
        node_id2 = dg.add_gate(gate2)
        node_id3 = dg.add_gate(gate3)
        assert len(dg.nodes[node_id1]["gates"]) == 1
        assert len(dg.nodes[node_id1]["qubits"]) == 1
        dg.cascade_node(node_id1, node_id3)
        assert len(dg.nodes[node_id1]["gates"]) == 2
        assert len(dg.nodes[node_id1]["qubits"]) == 1

        gate4 = ("cx", (0, 1), [])
        node_id4 = dg.add_gate(gate4)
        assert len(dg.nodes[node_id2]["gates"]) == 1
        assert len(dg.nodes[node_id2]["qubits"]) == 1
        assert dg.nodes[node_id2]["num_gate_2q"] == 0
        dg.cascade_node(node_id2, node_id4)
        assert len(dg.nodes[node_id2]["gates"]) == 2
        assert len(dg.nodes[node_id2]["qubits"]) == 2
        assert dg.nodes[node_id2]["num_gate_1q"] == 1
        assert dg.nodes[node_id2]["num_gate_2q"] == 1

    def test_cascade_node_parallel(self):
        dg = DG()
        gate1 = ("cx", (0, 1), [])
        gate2 = ("x", (0,), [])
        gate3 = ("h", (1,), [])
        gate4 = ("cx", (0, 1), [])
        dg.add_gate(gate1)
        node_id2 = dg.add_gate(gate2)
        node_id3 = dg.add_gate(gate3)
        dg.add_gate(gate4)
        assert len(dg.nodes[node_id2]["gates"]) == 1
        assert len(dg.nodes[node_id2]["qubits"]) == 1
        dg.cascade_node(node_id2, node_id3)
        assert len(dg.nodes[node_id2]["gates"]) == 2
        assert len(dg.nodes[node_id2]["qubits"]) == 2

    def test_add_gate_absorb(self):
        dg = DG()
        gate1 = ("x", (0,), [])
        node_id1 = dg.add_gate_absorb(gate1)
        assert len(dg.nodes[node_id1]["gates"]) == 1

        gate2 = ("x", (0,), [])
        node_id2 = dg.add_gate_absorb(gate2)
        assert len(dg.nodes[node_id1]["gates"]) == 2
        assert node_id1 == node_id2

        gate3 = ("x", (1,), [])
        node_id3 = dg.add_gate_absorb(gate3)
        assert node_id1 != node_id3
        assert len(dg.nodes[node_id1]["gates"]) == 2
        assert len(dg.nodes[node_id3]["gates"]) == 1

    def test_from_qasm_string(self):
        qasm_str = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        h q[0];
        cx q[0], q[1];
        h q[1];
        """
        dg = DG()
        assert dg.num_q is None
        assert dg.num_gate_1q == 0
        assert dg.num_gate_2q == 0
        dg.from_qasm_string(qasm_str)
        assert dg.num_q == 2
        assert dg.num_gate_1q == 2
        assert dg.num_gate_2q == 1

    def test_from_ir(self):
        dg = DG()
        gate1 = X([0])
        gate2 = CX([0, 1])
        gate3 = H([1])
        gates_list = [gate1, gate2, gate3]
        assert dg.num_gate_1q == 0
        assert dg.num_gate_2q == 0
        cir = QuantumCircuit()
        for gate in gates_list:
            cir.append(gate)
        dg.from_ir(cir)
        assert dg.num_gate_1q == 2
        assert dg.num_gate_2q == 1
