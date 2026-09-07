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

import pytest
import numpy as np

from wy_qcos.error_mitigation.readout_mitigation import (
    ReadoutMitigation,
    build_local_confusion_matrix,
    mitigate_readout,
    build_confusion_matrix_from_counts,
    expectation_from_samples_unbiased,
    mitigate_observable_from_samples,
)


class TestBuildLocalConfusionMatrix:
    """Test build_local_confusion_matrix function."""

    def test_single_qubit(self):
        cm = {0: np.array([[0.95, 0.05], [0.05, 0.95]])}
        result = build_local_confusion_matrix(cm, [0])
        expected = np.array([[0.95, 0.05], [0.05, 0.95]])
        np.testing.assert_allclose(result, expected)

    def test_two_qubits_kronecker(self):
        cm0 = np.array([[0.9, 0.1], [0.1, 0.9]])
        cm1 = np.array([[0.8, 0.2], [0.2, 0.8]])
        result = build_local_confusion_matrix({0: cm0, 1: cm1}, [0, 1])
        expected = np.kron(cm0, cm1)
        np.testing.assert_allclose(result, expected)
        assert result.shape == (4, 4)

    def test_identity_confusion(self):
        cm = {0: np.eye(2), 1: np.eye(2)}
        result = build_local_confusion_matrix(cm, [0, 1])
        np.testing.assert_allclose(result, np.eye(4))

    def test_empty_qubits_raises(self):
        cm = {0: np.eye(2)}
        with pytest.raises(ValueError, match="target_qubits is empty"):
            build_local_confusion_matrix(cm, [])

    def test_column_stochastic(self):
        cm0 = np.array([[0.95, 0.03], [0.05, 0.97]])
        cm1 = np.array([[0.92, 0.08], [0.08, 0.92]])
        result = build_local_confusion_matrix({0: cm0, 1: cm1}, [0, 1])
        column_sums = result.sum(axis=0)
        np.testing.assert_allclose(column_sums, np.ones(4), atol=1e-10)


class TestMitigateReadout:
    """Test mitigate_readout function."""

    def test_identity_confusion(self):
        probs = np.array([0.3, 0.7])
        cm = np.eye(2)
        result = mitigate_readout(probs, cm)
        np.testing.assert_allclose(result, probs, atol=1e-10)

    def test_perfect_correction(self):
        cm = np.array([[0.9, 0.1], [0.1, 0.9]])
        true_probs = np.array([0.6, 0.4])
        measured = cm @ true_probs
        result = mitigate_readout(measured, cm)
        np.testing.assert_allclose(result, true_probs, atol=1e-6)

    def test_clipping_negative(self):
        cm = np.array([[0.9, 0.1], [0.1, 0.9]])
        probs = np.array([0.01, 0.99])
        result = mitigate_readout(probs, cm)
        assert np.all(result >= 0)
        np.testing.assert_allclose(np.sum(result), 1.0)

    def test_normalization(self):
        cm = np.array([[0.95, 0.05], [0.05, 0.95]])
        probs = np.array([0.5, 0.5])
        result = mitigate_readout(probs, cm)
        np.testing.assert_allclose(np.sum(result), 1.0, atol=1e-10)

    def test_non_square_raises(self):
        with pytest.raises(ValueError, match="must be square"):
            mitigate_readout(
                np.array([0.5, 0.5]), np.array([[1, 2, 3], [4, 5, 6]])
            )


class TestBuildConfusionMatrixFromCounts:
    """Test build_confusion_matrix_from_counts function."""

    def test_perfect_readout(self):
        counts_0 = {"0": 1000}
        counts_1 = {"1": 1000}
        cm = build_confusion_matrix_from_counts([counts_0, counts_1], 1)
        expected = np.eye(2)
        np.testing.assert_allclose(cm, expected)

    def test_noisy_readout(self):
        counts_0 = {"0": 950, "1": 50}
        counts_1 = {"0": 30, "1": 970}
        cm = build_confusion_matrix_from_counts([counts_0, counts_1], 1)
        assert cm.shape == (2, 2)
        np.testing.assert_allclose(cm[:, 0], [0.95, 0.05])
        np.testing.assert_allclose(cm[:, 1], [0.03, 0.97], atol=1e-6)

    def test_column_stochastic(self):
        counts_0 = {"0": 900, "1": 100}
        counts_1 = {"0": 200, "1": 800}
        cm = build_confusion_matrix_from_counts([counts_0, counts_1], 1)
        column_sums = cm.sum(axis=0)
        np.testing.assert_allclose(column_sums, np.ones(2), atol=1e-10)


class TestExpectationFromSamplesUnbiased:
    """Test expectation_from_samples_unbiased function."""

    def test_perfect_readout(self):
        samples = np.array([[0], [0], [1], [1]])
        cm = [np.eye(2)]
        result = expectation_from_samples_unbiased(samples, cm)
        np.testing.assert_allclose(result, 0.0, atol=1e-6)

    def test_empty_samples(self):
        samples = np.zeros((0, 1), dtype=int)
        cm = [np.eye(2)]
        result = expectation_from_samples_unbiased(samples, cm)
        assert result == 0.0

    def test_empty_support(self):
        samples = np.zeros((2, 0), dtype=int)
        result = expectation_from_samples_unbiased(samples, [])
        assert result == 1.0

    def test_invalid_ndim_raises(self):
        with pytest.raises(ValueError, match="must be 2D"):
            expectation_from_samples_unbiased(np.array([0, 1]), [np.eye(2)])

    def test_mismatched_length_raises(self):
        samples = np.array([[0, 1]])
        with pytest.raises(ValueError, match="length must equal"):
            expectation_from_samples_unbiased(samples, [np.eye(2)])


class TestMitigateObservableFromSamples:
    """Test mitigate_observable_from_samples function."""

    def test_empty_support(self):
        samples = np.array([[0, 1]])
        result = mitigate_observable_from_samples(
            samples, [], {0: np.eye(2), 1: np.eye(2)}, [0, 1]
        )
        assert result == 1.0

    def test_small_support_exact(self):
        samples = np.array([[0, 0], [0, 0], [1, 1], [1, 1]])
        per_qubit = {0: np.eye(2), 1: np.eye(2)}
        result = mitigate_observable_from_samples(
            samples, [0, 1], per_qubit, [0, 1], marginal_max_support=10
        )
        np.testing.assert_allclose(result, 1.0, atol=1e-6)


class TestReadoutMitigation:
    """Test ReadoutMitigation class."""

    def test_initialization(self):
        rem = ReadoutMitigation(calibration_shots=4096, cache_ttl=3600)
        assert rem.name == "readout"
        assert rem._calibration_shots == 4096
        assert rem._cache_ttl == 3600

    def test_set_config(self):
        rem = ReadoutMitigation()
        rem.set_config({"enabled": True, "calibration_shots": 2048})
        assert rem.enabled is True
        assert rem._calibration_shots == 2048

    def test_needs_calibration(self):
        rem = ReadoutMitigation()
        assert rem.needs_calibration() is True

    def test_build_calibration_circuits(self):
        rem = ReadoutMitigation(calibration_shots=1024)
        circuits = rem.build_calibration_circuits([0, 1])
        assert len(circuits) == 4
        qubits = [c["qubit"] for c in circuits]
        assert qubits == [0, 0, 1, 1]
        states = [c["prepared_state"] for c in circuits]
        assert states == ["0", "1", "0", "1"]

    def test_calibration_circuit_structure(self):
        rem = ReadoutMitigation()
        circuits = rem.build_calibration_circuits([0])
        c0 = circuits[0]["circuit"]
        c1 = circuits[1]["circuit"]
        assert c0.size() == 1
        assert c1.size() == 2
        assert c1.get_operations()[0].name == "x"

    def test_process_calibration_results(self):
        rem = ReadoutMitigation()
        results = {
            0: {"0": {"0": 950, "1": 50}, "1": {"0": 30, "1": 970}},
            1: {"0": {"0": 960, "1": 40}, "1": {"0": 20, "1": 980}},
        }
        calib = rem.process_calibration_results(results, [0, 1])
        assert 0 in calib["per_qubit_confusion"]
        assert 1 in calib["per_qubit_confusion"]
        assert calib["target_qubits"] == [0, 1]

    def test_postprocess_no_calibration(self):
        rem = ReadoutMitigation()
        results = {"original": {"00": 500, "11": 500}}
        output = rem.postprocess(results)
        assert output["metadata"]["applied"] is False

    def test_postprocess_with_calibration(self):
        rem = ReadoutMitigation()
        rem.process_calibration_results(
            {0: {"0": {"0": 950, "1": 50}, "1": {"0": 30, "1": 970}}},
            [0],
        )
        results = {"original": {"0": 600, "1": 400}}
        output = rem.postprocess(results, num_qubits=1, target_qubits=[0])
        assert output["metadata"]["variants"][0]["applied"] is True
        assert "max_correction" in output["metadata"]["variants"][0]

    def test_postprocess_preserves_total_counts(self):
        rem = ReadoutMitigation()
        rem.process_calibration_results(
            {0: {"0": {"0": 950, "1": 50}, "1": {"0": 50, "1": 950}}},
            [0],
        )
        results = {"original": {"0": 600, "1": 400}}
        output = rem.postprocess(results, num_qubits=1, target_qubits=[0])
        mitigated = output["results"]["original"]
        total = sum(mitigated.values())
        assert abs(total - 1000) < 50
