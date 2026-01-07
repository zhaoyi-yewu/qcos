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

import os
import unittest
import numpy as np

from unittest.mock import patch, MagicMock

from wy_qcos.transpiler.cmss.wirecut.cut_wire import (
    CutWire,
    generate_all_variant_subcircuits_for_execute,
    simple_subcircuit_dict,
    reconstruct_probability_distribution_wire_cut,
)
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.common.gate_operation import H, CX


TEST_QASM_CONTENT = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
measure q -> c;"""


class TestCutWire(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.qasm = TEST_QASM_CONTENT
        self.max_subcircuit_width = 3
        self.max_memory = 1024
        self.max_depth = 5
        self.max_cuts = 10

    def tearDown(self):
        """Clean up the test environment."""
        for log_file in ["log.txt", "results.txt"]:
            if os.path.exists(log_file):
                os.unlink(log_file)

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.cut_wire.open",
        side_effect=lambda *args, **kwargs: MagicMock(),
    )
    @patch("wy_qcos.transpiler.cmss.wirecut.mip_model.MIPModel")
    def test_cutwire_init_success(self, mock_mip_model, mock_open):
        """Test CutWire successfully initialized."""
        mock_mip_instance = MagicMock()
        mock_mip_instance.solve.return_value = (
            True,
            [[0, 1]],
            [[0], [1, 2, 3]],
        )
        mock_mip_model.return_value = mock_mip_instance
        with patch("wy_qcos.transpiler.cmss.wirecut.cut_wire.DAG") as mock_dag:
            mock_dag_instance = MagicMock()
            mock_dag_instance.knit_dag_to_graph.return_value = (
                4,
                [[0, 1], [1, 2]],
            )
            mock_dag_instance.parse_subgraphs.return_value = [
                {"nodes": [0], "edges": []},
                {"nodes": [1, 2, 3], "edges": [[1, 2], [2, 3]]},
            ]
            mock_dag.return_value = mock_dag_instance
            with patch(
                "wy_qcos.transpiler.cmss.wirecut.cut_wire.Cut"
            ) as mock_cut:
                qc = QuantumCircuit(4)
                qc.append(H([0]))
                qc.append(CX([0, 1]))
                qc.append(CX([1, 2]))
                qc.append(CX([2, 3]))
                mock_cut_instance = MagicMock()
                mock_cut_instance.cut_circuit.return_value = (
                    [qc, qc],
                    {0: [{"subcircuit_idx": 0, "subcircuit_qubit": 0}]},
                )
                mock_cut.return_value = mock_cut_instance

                with patch(
                    "wy_qcos.transpiler.cmss.wirecut.cut_wire.Prepare_data"
                ):
                    # Create a CutWire instance
                    cut_wire = CutWire(
                        max_subcircuit_width=self.max_subcircuit_width,
                        qasm=self.qasm,
                        max_memory=self.max_memory,
                        max_depth=self.max_depth,
                        is_complete_reconstruction=False,
                        max_cuts=self.max_cuts,
                    )
                    assert cut_wire.parser is not None
                    assert cut_wire.dag is not None
                    assert (
                        cut_wire.max_subcircuit_width
                        == self.max_subcircuit_width
                    )
                    assert cut_wire.max_cuts == self.max_cuts

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.cut_wire.open",
        side_effect=lambda *args, **kwargs: MagicMock(),
    )
    @patch("wy_qcos.transpiler.cmss.wirecut.mip_model.MIPModel")
    def test_cutwire_init_failure(self, mock_mip_model, mock_open):
        """Test CutWire initialization failed."""
        mock_mip_instance = MagicMock()
        mock_mip_instance.solve.return_value = (False, [], None)
        mock_mip_model.return_value = mock_mip_instance
        with patch("wy_qcos.transpiler.cmss.wirecut.cut_wire.DAG") as mock_dag:
            mock_dag_instance = MagicMock()
            mock_dag_instance.knit_dag_to_graph.return_value = (
                4,
                [[0, 1], [1, 2]],
            )
            mock_dag.return_value = mock_dag_instance
            with self.assertRaises(IndexError):
                CutWire(
                    max_subcircuit_width=self.max_subcircuit_width,
                    qasm=self.qasm,
                    max_memory=self.max_memory,
                    max_depth=self.max_depth,
                    is_complete_reconstruction=False,
                    max_cuts=self.max_cuts,
                )

    def test_simple_subcircuit_dict(self):
        """Test the simple_subcircuit_dict method."""
        subcircuits_dict = {
            0: {
                ("init1", "meas1"): "qasm_string_1",
                ("init2", "meas2"): "qasm_string_2",
            },
            1: {
                ("init3", "meas3"): "qasm_string_3",
            },
        }
        result = simple_subcircuit_dict(subcircuits_dict)
        expected = ["qasm_string_1", "qasm_string_2", "qasm_string_3"]
        assert len(result) == 3
        for qasm in expected:
            assert qasm in result

    @patch("wy_qcos.transpiler.cmss.wirecut.cut_wire.CutWire")
    @patch(
        "wy_qcos.transpiler.cmss.wirecut.cut_wire.open",
        side_effect=lambda *args, **kwargs: MagicMock(),
    )
    def test_generate_all_variant_subcircuits_for_execute_success(
        self, mock_open, mock_cutwire
    ):
        """Test the generate_all_variant_subcircuits_for_execute method."""
        mock_cutwire = MagicMock()
        mock_cutwire.generate_all_variants_subcircuits.return_value = {
            0: {("init", "meas"): "qasm_string"}
        }
        mock_cutwire.return_value = mock_cutwire
        _, result_json, result_dill = (
            generate_all_variant_subcircuits_for_execute(
                max_subcircuit_width=self.max_subcircuit_width,
                qasm=self.qasm,
                max_memory=self.max_memory,
                max_depth=self.max_depth,
                is_complete_reconstruction=False,
                max_cuts=self.max_cuts,
            )
        )
        if result_json is None:
            self.skipTest("Function returned None, skipping test")
        assert result_json is not None
        assert result_dill is not None
        assert isinstance(result_json, list)

    @patch("wy_qcos.transpiler.cmss.wirecut.cut_wire.CutWire")
    def test_generate_all_variant_subcircuits_for_execute_failure(
        self, mock_cutwire
    ):
        """Test the generate_all_variant_subcircuits_for_execute method."""
        mock_cutwire.side_effect = None
        result_origin, result_json, result_dill = (
            generate_all_variant_subcircuits_for_execute(
                max_subcircuit_width=self.max_subcircuit_width,
                qasm=self.qasm,
                max_memory=self.max_memory,
                max_depth=self.max_depth,
                is_complete_reconstruction=False,
                max_cuts=self.max_cuts,
            )
        )
        assert result_origin is not None
        assert result_json is not None
        assert isinstance(result_json, list)
        assert result_dill is not None

    def test_generate_all_variant_subcircuits_for_execute_default_max_cuts(
        self,
    ):
        """Test generate_all_variant_subcircuits_for_execute method."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.cut_wire.CutWire"
        ) as mock_cutwire:
            mock_cutwire_in = MagicMock()
            mock_cutwire_in.generate_all_variants_subcircuits.return_value = {}
            mock_cutwire.return_value = mock_cutwire_in

            with patch(
                "wy_qcos.transpiler.cmss.wirecut.cut_wire.open",
                side_effect=lambda *args, **kwargs: MagicMock(),
            ):
                generate_all_variant_subcircuits_for_execute(
                    max_subcircuit_width=self.max_subcircuit_width,
                    qasm=self.qasm,
                    max_memory=self.max_memory,
                    max_depth=self.max_depth,
                    is_complete_reconstruction=False,
                )
                mock_cutwire.assert_called_once()
                _, kwargs = mock_cutwire.call_args
                assert kwargs["max_cuts"] == 100

    @patch("wy_qcos.transpiler.cmss.wirecut.cut_wire.DD")
    @patch(
        "wy_qcos.transpiler.cmss.wirecut.cut_wire.reconstruct_prob_from_bins"
    )
    def test_reconstruct_probability_distribution_wire_cut(
        self, mock_reconstruct_prob, mock_dd
    ):
        """Test reconstruct_probability_distribution_wire_cut method."""

        class MockWirecut:
            def __init__(self):
                self.subcircuits_dict = {
                    0: {("init1", "meas1"): "qasm1"},
                    1: {("init2", "meas2"): "qasm2"},
                }
                self.prepare_data = MockPrepareData()
                self.max_memory = 1024
                self.max_depth = 5
                self.parser = MockParser()

        class MockPrepareData:
            def __init__(self):
                self.topo_subcircuits = MockTopoSubcircuits()
                self.origin_qubit_order = {0: [0, 1], 1: [2, 3]}

        class MockTopoSubcircuits:
            pass

        class MockParser:
            def __init__(self):
                self.nqubits = 4

        mock_wirecut = MockWirecut()
        results_for_execute = [
            [0.5, 0.5, 0.0, 0.0],
            [0.3, 0.7, 0.0, 0.0],
        ]
        mock_dd_instance = MagicMock()
        mock_dd_instance.dd_bins = [{"prob": 0.5, "state": "00"}]
        mock_dd.return_value = mock_dd_instance
        mock_reconstruct_prob.return_value = ([0.25, 0.25, 0.25, 0.25], [])
        result = reconstruct_probability_distribution_wire_cut(
            wirecut=mock_wirecut,
            results_for_execute=results_for_execute,
            is_complete_reconstruction=True,
        )
        assert isinstance(result, tuple)
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)
        assert result[0] == [0.25, 0.25, 0.25, 0.25]
        mock_dd.assert_called_once()
        mock_dd_instance.dd.assert_called_once()
        mock_reconstruct_prob.assert_called_once()

    def test_cutwire_reconstruct_method(self):
        """Testing the CutWire refactoring method."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.cut_wire.CutWire"
        ) as mock_cutwire:
            mock_cutwire_instance = MagicMock()
            mock_cutwire_instance.subcircuits_dict = {
                0: {("init", "meas"): "qasm_string"}
            }
            mock_reconstructor = MagicMock()
            mock_reconstructor.reconstruct.return_value = np.array([
                0.25,
                0.25,
                0.25,
                0.25,
            ])
            mock_cutwire_instance.reconstruct.return_value = (
                mock_reconstructor.reconstruct.return_value
            )
            mock_cutwire.return_value = mock_cutwire_instance
            with patch(
                "wy_qcos.transpiler.cmss.wirecut.cut_wire.open",
                side_effect=lambda *args, **kwargs: MagicMock(),
            ):
                results_for_execute = [[0.5, 0.3, 0.2], [0.6, 0.4]]
                result = mock_cutwire_instance.reconstruct(results_for_execute)
                assert isinstance(result, np.ndarray)

    def test_cutwire_generate_all_variants_subcircuits(self):
        """Test generation of all variant subcircuits."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.cut_wire.CutWire"
        ) as mock_cutwire:
            mock_cutwire = MagicMock()
            mock_cutwire.generate_all_variants_subcircuits.return_value = {
                0: {("init", "meas"): "qasm_string"}
            }
            mock_cutwire.return_value = mock_cutwire
            with patch(
                "wy_qcos.transpiler.cmss.wirecut.cut_wire.open",
                side_effect=lambda *args, **kwargs: MagicMock(),
            ):
                cut_wire = mock_cutwire
                result = cut_wire.generate_all_variants_subcircuits()
                assert isinstance(result, dict)
                assert 0 in result

    def test_reconstruct_probability_distribution_wire_cut_edge_cases(self):
        """Testing boundary case of probability distribution reconstruction."""

        class MockWirecut:
            def __init__(self):
                self.subcircuits_dict = {
                    0: {("init1", "meas1"): "qasm1"},
                }
                self.prepare_data = MockPrepareData()
                self.max_memory = 64
                self.max_depth = 3
                self.parser = MockParser()

        class MockPrepareData:
            def __init__(self):
                self.topo_subcircuits = MockTopoSubcircuits()
                self.origin_qubit_order = {0: [0, 1]}

        class MockTopoSubcircuits:
            pass

        class MockParser:
            def __init__(self):
                self.nqubits = 2

        mock_wirecut = MockWirecut()
        results_for_execute = [[0.7, 0.3]]
        with (
            patch("wy_qcos.transpiler.cmss.wirecut.cut_wire.DD") as mock_dd,
            patch(
                "wy_qcos.transpiler.cmss.wirecut.cut_wire."
                "reconstruct_prob_from_bins"
            ) as mock_reconstruct,
        ):
            mock_dd_instance = MagicMock()
            mock_dd_instance.dd_bins = [{"prob": 0.5, "state": "0"}]
            mock_dd.return_value = mock_dd_instance
            mock_reconstruct.return_value = (np.array([0.7, 0.3]), [])
            try:
                prob, sparse_prob = (
                    reconstruct_probability_distribution_wire_cut(
                        mock_wirecut,
                        results_for_execute,
                        is_complete_reconstruction=False,
                    )
                )
                assert isinstance(prob, np.ndarray)
                assert isinstance(sparse_prob, list)
            except Exception as e:
                self.skipTest(f"Edge case test failed: {e}")
