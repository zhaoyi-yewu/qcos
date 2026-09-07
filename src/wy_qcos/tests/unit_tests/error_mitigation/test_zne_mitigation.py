#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You may use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Unit tests for the zero-noise extrapolation (ZNE) mitigation module."""

import numpy as np
import pytest

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.error_mitigation.zne_mitigation import (
    ZNEMitigation,
    apply_zne_cz_scaling,
    apply_zne_cz_tripling,
    count_cz_gates,
    extrapolate_to_zero,
    richardson_coefficients,
    zne_linear_extrapolate,
)


def make_circuit_with_cz(num_cz):
    """Helper to create a circuit with the specified number of CZ gates."""
    qc = QuantumCircuit(2)
    qc.append(
        GateOperation(
            "h",
            targets=[0],
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
        )
    )
    for _ in range(num_cz):
        qc.append(
            GateOperation(
                "cz",
                targets=[0, 1],
                operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
            )
        )
    return qc


def probs_to_counts(probs, shots=10000):
    """Convert a probability vector to integer counts (rounding)."""
    probs = np.asarray(probs, dtype=float)
    counts = np.round(probs * shots).astype(int)
    diff = shots - int(counts.sum())
    if diff != 0 and counts.size:
        counts[int(np.argmax(probs))] += diff
    nq = int(round(np.log2(counts.size)))
    return {
        format(i, f"0{nq}b"): int(c) for i, c in enumerate(counts) if c > 0
    }


class TestApplyZneCzScaling:
    """Test the generalised CZ-folding helper."""

    def test_scale_three(self):
        qc = make_circuit_with_cz(1)
        scaled = apply_zne_cz_scaling(qc, 3)
        cz = sum(1 for op in scaled.get_operations() if op.name == "cz")
        assert cz == 3

    def test_scale_five(self):
        qc = make_circuit_with_cz(2)
        scaled = apply_zne_cz_scaling(qc, 5)
        cz = sum(1 for op in scaled.get_operations() if op.name == "cz")
        assert cz == 10

    def test_scale_one_is_identity(self):
        qc = make_circuit_with_cz(3)
        scaled = apply_zne_cz_scaling(qc, 1)
        assert scaled is qc

    def test_even_scale_raises(self):
        qc = make_circuit_with_cz(1)
        with pytest.raises(ValueError):
            apply_zne_cz_scaling(qc, 2)

    def test_non_positive_scale_raises(self):
        qc = make_circuit_with_cz(1)
        with pytest.raises(ValueError):
            apply_zne_cz_scaling(qc, 0)

    def test_non_cz_gates_preserved(self):
        qc = QuantumCircuit(2)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        qc.append(
            GateOperation(
                "cx",
                targets=[0, 1],
                operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
            )
        )
        qc.append(
            GateOperation(
                "cz",
                targets=[0, 1],
                operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
            )
        )
        scaled = apply_zne_cz_scaling(qc, 3)
        names = [op.name for op in scaled.get_operations()]
        assert names.count("h") == 1
        assert names.count("cx") == 1
        assert names.count("cz") == 3

    def test_original_unchanged(self):
        qc = make_circuit_with_cz(2)
        original_size = qc.size()
        apply_zne_cz_scaling(qc, 5)
        assert qc.size() == original_size


class TestApplyZneCzTripling:
    """Test the backwards-compatible tripling alias."""

    def test_single_cz(self):
        qc = make_circuit_with_cz(1)
        scaled = apply_zne_cz_tripling(qc)
        cz = sum(1 for op in scaled.get_operations() if op.name == "cz")
        assert cz == 3

    def test_multiple_cz(self):
        qc = make_circuit_with_cz(3)
        scaled = apply_zne_cz_tripling(qc)
        cz = sum(1 for op in scaled.get_operations() if op.name == "cz")
        assert cz == 9

    def test_no_cz(self):
        qc = QuantumCircuit(1)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        scaled = apply_zne_cz_tripling(qc)
        assert scaled.size() == 1


class TestCountCzGates:
    """Test count_cz_gates."""

    def test_no_cz(self):
        qc = QuantumCircuit(1)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        assert count_cz_gates(qc) == 0

    def test_with_cz(self):
        qc = make_circuit_with_cz(5)
        assert count_cz_gates(qc) == 5


class TestZneLinearExtrapolate:
    """Test the legacy two-point linear extrapolation."""

    def test_formula_correctness(self):
        probs_1 = np.array([0.8, 0.2])
        probs_3 = np.array([0.6, 0.4])
        result = zne_linear_extrapolate(probs_1, probs_3)
        expected = (3.0 * probs_1 - probs_3) / 2.0
        np.testing.assert_allclose(result, expected)

    def test_identical_inputs(self):
        probs = np.array([0.5, 0.5])
        result = zne_linear_extrapolate(probs, probs)
        np.testing.assert_allclose(result, probs)

    def test_scalar_inputs(self):
        result = zne_linear_extrapolate(0.8, 0.6)
        expected = (3.0 * 0.8 - 0.6) / 2.0
        np.testing.assert_allclose(result, expected)

    def test_zero_noise_recovery(self):
        true_val = np.array([0.7, 0.3])
        drift = np.array([0.1, -0.1])
        probs_1 = true_val - drift
        probs_3 = true_val - 3 * drift
        result = zne_linear_extrapolate(probs_1, probs_3)
        np.testing.assert_allclose(result, true_val, atol=1e-10)


class TestRichardsonCoefficients:
    """Test Richardson coefficient computation."""

    def test_two_points_match_linear(self):
        coeffs = richardson_coefficients([1, 3])
        np.testing.assert_allclose(coeffs, [1.5, -0.5])

    def test_sum_to_one(self):
        for scales in ([1, 3], [1, 3, 5], [1, 3, 5, 7]):
            coeffs = richardson_coefficients(scales)
            assert np.isclose(coeffs.sum(), 1.0)

    def test_cancels_higher_moments(self):
        scales = np.array([1.0, 3.0, 5.0])
        coeffs = richardson_coefficients(scales)
        for k in range(1, len(scales)):
            moment = np.sum(coeffs * scales**k)
            assert abs(moment) < 1e-10

    def test_recovers_linear_signal(self):
        scales = np.array([1.0, 3.0, 5.0])
        a, b = 0.4, 0.05
        y = a + b * scales
        coeffs = richardson_coefficients(scales)
        np.testing.assert_allclose(np.dot(coeffs, y), a, atol=1e-10)


class TestExtrapolateToZero:
    """Test the extrapolate_to_zero dispatcher."""

    def test_richardson_recovers_linear_noise(self):
        scales = [1.0, 3.0, 5.0]
        ideal = np.array([0.7, 0.0, 0.0, 0.3])
        drift = np.array([0.1, -0.05, -0.05, 0.0])
        mat = np.vstack([ideal + s * drift for s in scales])
        out = extrapolate_to_zero(scales, mat, method="richardson")
        np.testing.assert_allclose(out, ideal, atol=1e-10)

    def test_polynomial_degree_one(self):
        scales = [1.0, 3.0, 5.0]
        ideal = np.array([0.6, 0.4])
        drift = np.array([0.05, -0.05])
        mat = np.vstack([ideal + s * drift for s in scales])
        out = extrapolate_to_zero(
            scales, mat, method="polynomial", polynomial_degree=1
        )
        np.testing.assert_allclose(out, ideal, atol=1e-10)

    def test_exponential_runs_and_finite(self):
        scales = [1.0, 3.0, 5.0]
        base = np.array([0.5, 0.5])
        mat = np.vstack([
            base + 0.02 * np.array([1.0, -1.0]) * s for s in scales
        ])
        out = extrapolate_to_zero(scales, mat, method="exponential")
        assert np.all(np.isfinite(out))

    def test_unknown_method_raises(self):
        mat = np.vstack([[0.5, 0.5], [0.4, 0.6]])
        with pytest.raises(ValueError):
            extrapolate_to_zero([1, 3], mat, method="bogus")


class TestZNEMitigation:
    """Test the ZNEMitigation class."""

    def test_default_initialization(self):
        zne = ZNEMitigation()
        assert zne.name == "zne"
        assert zne._scale_factors == (1.0, 2.0, 3.0)
        assert zne._scale_factor == 3.0

    def test_legacy_scale_factor(self):
        zne = ZNEMitigation(scale_factor=3)
        assert zne._scale_factors == (1, 3)
        assert zne._scale_factor == 3

    def test_set_config_scale_factor(self):
        zne = ZNEMitigation()
        zne.set_config({"enabled": True, "scale_factor": 5})
        assert zne.enabled is True
        assert zne._scale_factors == (1, 5)
        assert zne._scale_factor == 5

    def test_set_config_scale_factors(self):
        zne = ZNEMitigation()
        zne.set_config({
            "enabled": True,
            "scale_factors": [1, 3, 5, 7],
            "extrapolation_method": "polynomial",
            "polynomial_degree": 1,
        })
        assert zne._scale_factors == (1, 3, 5, 7)
        assert zne._extrapolation_method == "polynomial"
        assert zne._polynomial_degree == 1

    def test_validate_device_with_cz(self):
        zne = ZNEMitigation()
        valid, msg = zne.validate_device({
            "basis_gates": ["u3", "cz", "measure"]
        })
        assert valid is True
        assert msg is None

    def test_validate_device_without_cz(self):
        zne = ZNEMitigation()
        valid, msg = zne.validate_device({
            "basis_gates": ["u3", "cx", "measure"]
        })
        assert valid is False
        assert "CZ" in msg

    def test_transform_circuit_default(self):
        zne = ZNEMitigation()
        qc = make_circuit_with_cz(2)
        variants = zne.transform_circuit(qc)
        assert len(variants) == 3
        assert [v["label"] for v in variants] == ["zne_s1", "zne_s2", "zne_s3"]
        assert [v["scale_factor"] for v in variants] == [1.0, 2.0, 3.0]
        assert count_cz_gates(variants[0]["circuit"]) == 2
        assert count_cz_gates(variants[1]["circuit"]) == 4
        assert count_cz_gates(variants[2]["circuit"]) == 6

    def test_transform_circuit_custom_scales(self):
        zne = ZNEMitigation(scale_factors=[1, 3])
        qc = make_circuit_with_cz(1)
        variants = zne.transform_circuit(qc)
        assert len(variants) == 2
        assert variants[0]["label"] == "zne_s1"
        assert variants[1]["label"] == "zne_s3"

    def test_transform_circuit_no_cz(self):
        zne = ZNEMitigation()
        qc = QuantumCircuit(1)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        variants = zne.transform_circuit(qc)
        assert len(variants) == 1
        assert variants[0]["label"] == "zne_s1"

    def test_postprocess_three_points(self):
        zne = ZNEMitigation()
        results = {
            "zne_s1": probs_to_counts([0.6, 0.1, 0.1, 0.2]),
            "zne_s3": probs_to_counts([0.55, 0.12, 0.13, 0.2]),
            "zne_s5": probs_to_counts([0.5, 0.14, 0.16, 0.2]),
        }
        output = zne.postprocess(results, num_qubits=2)
        assert output["metadata"]["applied"] is True
        assert "extrapolated" in output["results"]
        assert output["metadata"]["extrapolation_method"] == "polynomial"
        assert output["metadata"]["scale_factors"] == [1.0, 3.0, 5.0]

    def test_postprocess_two_points(self):
        zne = ZNEMitigation(scale_factors=[1, 3])
        results = {
            "zne_s1": {"00": 4500, "01": 200, "10": 300, "11": 5000},
            "zne_s3": {"00": 4000, "01": 400, "10": 600, "11": 5000},
        }
        output = zne.postprocess(results, num_qubits=2)
        assert output["metadata"]["applied"] is True
        np.testing.assert_allclose(
            output["metadata"]["scale_factors"], [1.0, 3.0]
        )

    def test_postprocess_legacy_labels(self):
        zne = ZNEMitigation(scale_factors=[1, 3])
        results = {
            "original": {"00": 4500, "01": 200, "10": 300, "11": 5000},
            "scaled": {"00": 4000, "01": 400, "10": 600, "11": 5000},
        }
        output = zne.postprocess(results, num_qubits=2)
        assert output["metadata"]["applied"] is True

    def test_postprocess_no_scaled(self):
        zne = ZNEMitigation()
        results = {"zne_s1": {"00": 5000, "11": 5000}}
        output = zne.postprocess(results, num_qubits=2)
        assert output["metadata"]["applied"] is False

    def test_postprocess_no_original(self):
        zne = ZNEMitigation()
        results = {"zne_s3": {"00": 5000, "11": 5000}}
        output = zne.postprocess(results, num_qubits=2)
        assert output["metadata"]["applied"] is False

    def test_postprocess_result_normalization(self):
        zne = ZNEMitigation()
        results = {
            "zne_s1": probs_to_counts([0.6, 0.1, 0.1, 0.2]),
            "zne_s3": probs_to_counts([0.55, 0.12, 0.13, 0.2]),
            "zne_s5": probs_to_counts([0.5, 0.14, 0.16, 0.2]),
        }
        output = zne.postprocess(results, num_qubits=2)
        mitigated = output["results"]["extrapolated"]
        assert sum(mitigated.values()) > 0

    def test_fallback_on_divergence(self):
        zne = ZNEMitigation(extrapolation_method="richardson")
        results = {
            "zne_s1": {"0": 900, "1": 100},
            "zne_s3": {"0": 100, "1": 900},
            "zne_s5": {"0": 100, "1": 900},
        }
        output = zne.postprocess(results, num_qubits=1)
        assert output["metadata"]["applied"] is True
        assert output["metadata"]["fallback"] is True
        assert output["metadata"]["negative_mass"] > 0.3
        mitigated = output["results"]["extrapolated"]
        assert mitigated.get("0", 0) == 900
        assert mitigated.get("1", 0) == 100

    def test_zero_noise_recovery(self):
        zne = ZNEMitigation(scale_factors=[1, 3, 5])
        ideal = np.array([0.7, 0.0, 0.0, 0.3])
        drift = np.array([0.06, -0.02, -0.02, -0.02])
        results = {
            f"zne_s{int(s)}": probs_to_counts(ideal + s * drift)
            for s in (1, 3, 5)
        }
        output = zne.postprocess(results, num_qubits=2)
        mitigated = output["results"]["extrapolated"]
        recovered = np.zeros(4)
        total = sum(mitigated.values())
        for bitstring, count in mitigated.items():
            recovered[int(bitstring, 2)] = count / total
        raw = ideal + drift
        err_raw = np.sum(np.abs(raw - ideal))
        err_zne = np.sum(np.abs(recovered - ideal))
        assert err_zne < err_raw
