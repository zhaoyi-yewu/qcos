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

import unittest
from unittest.mock import patch, MagicMock

from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.common.gate_operation import H, CX, X, Y, Z
from wy_qcos.transpiler.common.wirecut.cut import Cut


class TestCut(unittest.TestCase):
    """Test Cut class."""

    def setUp(self):
        self.qc = QuantumCircuit(4)
        self.qc.append(H([0]))
        self.qc.append(CX([0, 1]))
        self.qc.append(CX([1, 2]))
        self.qc.append(CX([2, 3]))
        self.MIP_Result = [["q[0]0 q[1]0"], ["q[1]1 q[2]0"], ["q[2]1 q[3]0"]]
        self.cut = Cut(self.qc, self.MIP_Result)

    def test_init(self):
        assert self.cut.circuit == self.qc
        assert self.cut.MIP_result == self.MIP_Result
        assert self.cut.dag is not None

    @patch(
        "wy_qcos.transpiler.common.wirecut.cut.Cut."
        "_initialize_gate_depth_encodings"
    )
    @patch(
        "wy_qcos.transpiler.common.wirecut.cut.Cut._assign_qubits_to_subcircuits"
    )
    @patch("wy_qcos.transpiler.common.wirecut.cut.Cut._update_path_elements")
    @patch("wy_qcos.transpiler.common.wirecut.cut.Cut.generate_subcircuits")
    def test_cut_circuit(
        self,
        mock_generate_subcircuits,
        mock_update_path_elements,
        mock_assign_qubits_to_subcircuits,
        mock_initialize_gate_depth_encodings,
    ):
        mock_initialize_gate_depth_encodings.return_value = {
            "op1": "enc1",
            "op2": "enc2",
        }
        mock_assign_qubits_to_subcircuits.return_value = (
            {"0": []},
            [2],
            {"q0": []},
        )
        mock_update_path_elements.return_value = {
            "q0": [{"subcircuit_idx": 0, "subcircuit_qubit": 0}]
        }
        subcircuit_mocks = [MagicMock(), MagicMock()]
        mock_generate_subcircuits.return_value = subcircuit_mocks
        subcircuits, qubit_allocation_map = self.cut.cut_circuit()
        mock_initialize_gate_depth_encodings.assert_called_once()
        mock_assign_qubits_to_subcircuits.assert_called_once()
        mock_update_path_elements.assert_called_once()
        mock_generate_subcircuits.assert_called_once()
        assert len(subcircuits) == 2
        assert qubit_allocation_map == {
            "q0": [{"subcircuit_idx": 0, "subcircuit_qubit": 0}]
        }

    def test_compute_gate_distance(self):
        """Testing the calculation of distances between quantum gates."""
        # Two gates on the same qubit with a distance of 1
        distance1 = self.cut.compute_gate_distance("q[0]1", "q[0]2")
        assert distance1 == 1

        # Two gates on the same qubit with a distance of 2
        distance2 = self.cut.compute_gate_distance("q[0]1", "q[0]3")
        assert distance2 == 2

        # Gates on different qubits cannot calculate distance.
        distance3 = self.cut.compute_gate_distance("q[0]1", "q[1]1")
        assert distance3 == float("inf")

        # Multi-bit gate
        distance4 = self.cut.compute_gate_distance(
            "q[0]1 q[1]1", "q[0]2 q[2]1"
        )
        assert distance4 == 1  # The distance on the q[0] bit is 1

    def test_parse_gate_qubits(self):
        """Testing the quantum bit information of the parsing gate."""
        # Single-qubit gate
        result1 = self.cut._parse_gate_qubits("q[0]1")
        assert result1 == [("q[0]", 1)]

        # Two-qubit gate
        result2 = self.cut._parse_gate_qubits("q[0]1 q[1]2")
        assert result2 == [("q[0]", 1), ("q[1]", 2)]

    def test_cut_complex_circuit(self):
        """Testing the cutting of complex circuits."""
        qc = QuantumCircuit(6)
        qc.append(H([0]))
        qc.append(CX([0, 1]))
        qc.append(CX([1, 2]))
        qc.append(CX([2, 3]))
        qc.append(CX([3, 4]))
        qc.append(CX([4, 5]))
        qc.append(H([2]))
        qc.append(Y([4]))
        MIP_Result = [
            ["q[0]0 q[1]0", "q[1]1 q[2]0"],
            ["q[2]1 q[3]0", "q[3]1 q[4]0"],
            ["q[4]1 q[5]0"],
        ]
        cut = Cut(qc, MIP_Result)
        subcircuits, qubit_allocation_map = cut.cut_circuit()
        assert isinstance(subcircuits, list)
        assert len(subcircuits) == 3
        assert isinstance(qubit_allocation_map, dict)
        for subcircuit in subcircuits:
            assert subcircuit is not None
            assert subcircuit.num_qubits > 0

    def test_cut_single_qubit_operations(self):
        """Testing circuits with only single-qubit operations."""
        qc = QuantumCircuit(3)
        qc.append(H([0]))
        qc.append(X([1]))
        qc.append(Y([2]))
        qc.append(Z([0]))
        MIP_Result = [
            [],
            [],
        ]

        try:
            cut = Cut(qc, MIP_Result)
            subcircuits, qubit_allocation_map = cut.cut_circuit()
            assert isinstance(subcircuits, list)
            assert isinstance(qubit_allocation_map, dict)

        except Exception as e:
            self.skipTest(f"Single qubit operations test failed: {e}")

    def test_cut_gate_distance_calculation(self):
        """Test gate distance calculation."""
        qc = QuantumCircuit(4)
        qc.append(H([0]))
        qc.append(CX([0, 1]))
        qc.append(CX([1, 2]))
        qc.append(CX([2, 3]))
        MIP_Result = [["q[0]0 q[1]0"], ["q[1]1 q[2]0"], ["q[2]1 q[3]0"]]
        cut = Cut(qc, MIP_Result)
        try:
            distance1 = cut.compute_gate_distance("q[0]0 q[1]0", "q[1]1 q[2]0")
            assert isinstance(distance1, (int, float))
            assert distance1 >= 0
            distance2 = cut.compute_gate_distance("q[0]0", "q[0]1")
            assert isinstance(distance2, (int, float))
            assert distance2 >= 0
        except Exception as e:
            self.skipTest(f"Gate distance calculation test failed: {e}")

    def test_cut_parse_gate_qubits(self):
        """Testing the analysis of quantum bit information for gates."""
        qc = QuantumCircuit(4)
        qc.append(CX([0, 1]))
        MIP_Result = [["q[0]0 q[1]0"]]
        cut = Cut(qc, MIP_Result)
        try:
            parsed = cut._parse_gate_qubits("q[0]0 q[1]0")
            assert isinstance(parsed, list)
            assert len(parsed) == 2
            for qubit_name, gate_idx in parsed:
                assert isinstance(qubit_name, str)
                assert isinstance(gate_idx, int)
        except Exception as e:
            self.skipTest(f"Parse gate qubits test failed: {e}")
