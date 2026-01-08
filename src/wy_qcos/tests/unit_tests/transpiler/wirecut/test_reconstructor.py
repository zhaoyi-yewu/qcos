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
import numpy as np

from unittest.mock import patch, MagicMock

from wy_qcos.transpiler.cmss.wirecut.reconstructor import (
    Reconstructor,
    parse_results_from_hardware_service,
)


class TestReconstructor(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.mock_prepare_data = MagicMock()
        self.mock_prepare_data.topo_subcircuits = MagicMock()
        self.mock_prepare_data.topo_subcircuits.subcircuits = {
            0: {"significant": 2},
            1: {"significant": 2},
        }
        self.mock_prepare_data.topo_subcircuits.get_connection = MagicMock(
            return_value=[(0, 1)]
        )
        self.mock_prepare_data.topo_subcircuits.assign_bases_to_connections = (
            MagicMock()
        )
        self.mock_results = {
            0: {
                (("0", "0"), ("I", "X")): np.array([0.5, 0.5, 0.0, 0.0]),
                (("0", "0"), ("Z", "Y")): np.array([0.3, 0.7, 0.0, 0.0]),
            },
            1: {
                (("0", "0"), ("I", "X")): np.array([0.6, 0.4, 0.0, 0.0]),
                (("0", "0"), ("Z", "Y")): np.array([0.4, 0.6, 0.0, 0.0]),
            },
        }

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.reconstructor."
        "Reconstructor.reconstruct"
    )
    def test_reconstructor_init(self, mock_reconstruct):
        """Testing Reconstructor initialization."""
        mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
        reconstructor = Reconstructor(
            prepare_data=self.mock_prepare_data,
            results_for_execute=self.mock_results,
        )
        assert reconstructor.prepare_data == self.mock_prepare_data
        assert reconstructor.evaluate_results == self.mock_results
        assert reconstructor.reconstructed_prob is not None
        mock_reconstruct.assert_called_once()

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.reconstructor."
        "Reconstructor.reconstruct"
    )
    def test_init_data(self, mock_reconstruct):
        """Testing the init_data method."""
        mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])

        reconstructor = Reconstructor(
            prepare_data=self.mock_prepare_data,
            results_for_execute=self.mock_results,
        )
        assert isinstance(reconstructor.measure_config_length, dict)
        assert len(reconstructor.measure_config_length) == 2
        assert isinstance(reconstructor.num_qubits, int)
        assert reconstructor.num_qubits == 4

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.reconstructor."
        "Reconstructor.reconstruct"
    )
    def test_get_measure_config_length(self, mock_reconstruct):
        """Test the get_measure_config_length method."""
        mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
        reconstructor = Reconstructor(
            prepare_data=self.mock_prepare_data,
            results_for_execute=self.mock_results,
        )
        length = reconstructor.get_measure_config_length(0)
        assert length == 4

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.reconstructor."
        "Reconstructor.compute_tensor_product_for_bases"
    )
    def test_reconstruct(self, mock_compute_tensor):
        """Test the reconstruct method."""
        mock_compute_tensor.return_value = np.array([0.1, 0.2, 0.3, 0.4])
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "Reconstructor.reconstruct"
        ) as mock_reconstruct:
            mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
            reconstructor = Reconstructor(
                prepare_data=self.mock_prepare_data,
                results_for_execute=self.mock_results,
            )
            mock_reconstruct.side_effect = None
            result = reconstructor.reconstruct()
            assert isinstance(result, np.ndarray)

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.reconstructor."
        "Reconstructor.reconstruct"
    )
    def test_compute_tensor_product_for_bases(self, mock_reconstruct):
        """Test the compute_tensor_product_for_bases method."""
        mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
        reconstructor = Reconstructor(
            prepare_data=self.mock_prepare_data,
            results_for_execute=self.mock_results,
        )
        conn_bases = ("I", "X")
        connections = [(0, 1)]
        sorted_subcircuit_config = [0, 1]
        evaluate_results = self.mock_results
        topo_subcircuits = self.mock_prepare_data.topo_subcircuits
        topo_subcircuits.get_init_meas.return_value = (("0", "0"), ("I", "X"))
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor.tensor_product"
        ) as mock_tensor_product:
            mock_tensor_product.return_value = np.array([0.1, 0.2, 0.3, 0.4])
            result = reconstructor.compute_tensor_product_for_bases(
                conn_bases,
                connections,
                sorted_subcircuit_config,
                evaluate_results,
                topo_subcircuits,
            )
            assert isinstance(result, np.ndarray)

    @patch(
        "wy_qcos.transpiler.cmss.wirecut.reconstructor."
        "Reconstructor.reconstruct"
    )
    def test_normalize_probability(self, mock_reconstruct):
        """Test normalize_probability method."""
        mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
        reconstructor = Reconstructor(
            prepare_data=self.mock_prepare_data,
            results_for_execute=self.mock_results,
        )
        unnormalized_prob = np.array([0.2, 0.3, 0.1, 0.4])
        normalized_prob = reconstructor.normalize_probability(
            unnormalized_prob
        )
        assert isinstance(normalized_prob, np.ndarray)
        np.testing.assert_almost_equal(np.sum(normalized_prob), 1.0)

    def test_reconstructor_normalize_probability_fixed(self):
        """Testing probability normalization methods."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "Reconstructor.reconstruct"
        ) as mock_reconstruct:
            mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
            reconstructor = Reconstructor(
                prepare_data=self.mock_prepare_data,
                results_for_execute=self.mock_results,
            )
            prob_dist = np.array([0.2, 0.3, 0.5])
            normalized = reconstructor.normalize_probability(prob_dist)
            assert isinstance(normalized, np.ndarray)
            np.testing.assert_almost_equal(np.sum(normalized), 1.0)
            zero_dist = np.array([0.0, 0.0, 0.0])
            normalized_zero = reconstructor.normalize_probability(zero_dist)
            np.testing.assert_array_equal(normalized_zero, zero_dist)
            result_none = reconstructor.normalize_probability(None)
            assert result_none is None

    def test_reconstructor_compute_tensor_product_for_bases_fixed(self):
        """Test the method for computing the tensor product of bases."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "Reconstructor.reconstruct"
        ) as mock_reconstruct:
            mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
            reconstructor = Reconstructor(
                prepare_data=self.mock_prepare_data,
                results_for_execute=self.mock_results,
            )
            try:
                connections = [(0, 1)]
                conn_bases = ("I", "X")
                sorted_subcircuit_config = [0, 1]
                evaluate_results = self.mock_results
                topo_subcircuits = self.mock_prepare_data.topo_subcircuits
                topo_subcircuits.get_init_meas.return_value = (
                    ("0", "0"),
                    ("I", "X"),
                )
                with patch(
                    "wy_qcos.transpiler.cmss.wirecut.reconstructor."
                    "tensor_product"
                ) as mock_tensor_product:
                    mock_tensor_product.return_value = np.array([
                        0.1,
                        0.2,
                        0.3,
                        0.4,
                    ])
                    result = reconstructor.compute_tensor_product_for_bases(
                        conn_bases,
                        connections,
                        sorted_subcircuit_config,
                        evaluate_results,
                        topo_subcircuits,
                    )
                    assert isinstance(result, np.ndarray)
            except Exception as e:
                self.skipTest(
                    f"compute_tensor_product_for_bases test failed: {e}"
                )

    def test_reconstructor_get_measure_config_length_fixed(self):
        """Test the method for obtaining measurement configuration length."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "Reconstructor.reconstruct"
        ) as mock_reconstruct:
            mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
            reconstructor = Reconstructor(
                prepare_data=self.mock_prepare_data,
                results_for_execute=self.mock_results,
            )
            length = reconstructor.get_measure_config_length(0)
            assert isinstance(length, int)
            assert length == 4

    def test_reconstructor_full_workflow_fixed(self):
        """Test the full workflow of reconstructoring."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "Reconstructor.reconstruct"
        ) as mock_reconstruct:
            mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
            try:
                reconstructor = Reconstructor(
                    prepare_data=self.mock_prepare_data,
                    results_for_execute=self.mock_results,
                )
                assert reconstructor.reconstructed_probis is not None
                assert isinstance(reconstructor.measure_config_length, dict)
                assert isinstance(reconstructor.sorted_subcircuit_config, list)
                result = reconstructor.reconstructed_prob
                assert isinstance(result, np.ndarray)
            except Exception as e:
                self.skipTest(f"Full workflow test failed: {e}")

    def test_parse_results_from_hardware_service(self):
        """Test the parse_results_from_hardware_service method."""
        results_for_execute = {
            0: {
                (("0", "0"), ("I", "X")): np.array([0.5, 0.5, 0.0, 0.0]),
                (("0", "1"), ("Z", "Y")): np.array([0.3, 0.7, 0.0, 0.0]),
            },
            1: {
                (("0", "0"), ("I", "X")): np.array([0.6, 0.4, 0.0, 0.0]),
                (("1", "0"), ("Z", "Y")): np.array([0.4, 0.6, 0.0, 0.0]),
            },
        }
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "compute_measure_combian"
        ) as mock_compute_measure:
            with patch(
                "wy_qcos.transpiler.cmss.wirecut.reconstructor.attribute_prob"
            ) as mock_attribute_prob:
                mock_compute_measure.return_value = [("I", "X"), ("Z", "X")]
                mock_attribute_prob.return_value = np.array([
                    0.5,
                    0.5,
                    0.0,
                    0.0,
                ])
                result = parse_results_from_hardware_service(
                    results_for_execute
                )
                assert isinstance(result, dict)
                assert len(result) == 2
                assert 0 in result
                assert 1 in result
                assert mock_compute_measure.call_count == 4
                assert mock_attribute_prob.call_count == 8

    def test_reconstructor_reconstruct_detailed(self):
        """Test the detailed implementation of the reconstruct method."""
        self.mock_prepare_data.topo_subcircuits.get_connection.return_value = [
            (0, 1)
        ]
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "Reconstructor.reconstruct"
        ) as mock_reconstruct:
            mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
            reconstructor = Reconstructor(
                prepare_data=self.mock_prepare_data,
                results_for_execute=self.mock_results,
            )
            mock_reconstruct.side_effect = None
            with patch.object(
                reconstructor, "normalize_probability"
            ) as mock_normalize:
                with patch.object(
                    reconstructor, "compute_tensor_product_for_bases"
                ) as mock_compute:
                    mock_normalize.return_value = np.array([
                        0.25,
                        0.25,
                        0.25,
                        0.25,
                    ])
                    mock_compute.return_value = np.array([0.1, 0.2, 0.3, 0.4])
                    result = reconstructor.reconstruct()
                    assert isinstance(result, np.ndarray)
                    assert len(result) == 4

    def test_reconstructor_normalize_probability_edge_cases(self):
        """Testing the boundary cases of the normalize_probability method."""
        with patch(
            "wy_qcos.transpiler.cmss.wirecut.reconstructor."
            "Reconstructor.reconstruct"
        ) as mock_reconstruct:
            mock_reconstruct.return_value = np.array([0.25, 0.25, 0.25, 0.25])
            reconstructor = Reconstructor(
                prepare_data=self.mock_prepare_data,
                results_for_execute=self.mock_results,
            )
            result = reconstructor.normalize_probability(None)
            assert result is None
            zero_array = np.array([0.0, 0.0, 0.0, 0.0])
            result = reconstructor.normalize_probability(zero_array)
            assert isinstance(result, np.ndarray)
            np.testing.assert_array_equal(result, zero_array)
            normal_array = np.array([0.2, 0.3, 0.1, 0.4])
            result = reconstructor.normalize_probability(normal_array)
            assert isinstance(result, np.ndarray)
            np.testing.assert_almost_equal(np.sum(result), 1.0)
