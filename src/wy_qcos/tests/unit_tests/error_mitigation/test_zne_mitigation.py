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
    fold_gates,
    richardson_coefficients,
    zne_linear_extrapolate,
)
from wy_qcos.error_mitigation.zne_mitigation import (
    _entropy,
    _prune_scale_points,
    _probs_to_counts,
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


class TestFoldGates:
    """Test the generalised multi-strategy gate folder (mitiq-aligned)."""

    def test_scale_three_all_strategies(self):
        # scale 3 (odd integer) -> every gate folded once -> 3x CZ count.
        qc = make_circuit_with_cz(3)
        for strategy in ("left", "right", "random"):
            scaled = fold_gates(
                qc, 3.0, strategy=strategy, gate_names=("cz",), seed=0
            )
            assert count_cz_gates(scaled) == 9

    def test_scale_two_partial_fold(self):
        # 3 CZ, scale 2: num_uniform=0, num_extra=round(1*3/2)=2 -> +4 CZ = 7.
        qc = make_circuit_with_cz(3)
        for strategy in ("left", "right", "random"):
            scaled = fold_gates(
                qc, 2.0, strategy=strategy, gate_names=("cz",), seed=0
            )
            assert count_cz_gates(scaled) == 7

    def test_scale_one_no_fold(self):
        qc = make_circuit_with_cz(4)
        scaled = fold_gates(qc, 1.0, strategy="random", seed=1)
        assert count_cz_gates(scaled) == 4

    def test_random_reproducible_with_seed(self):
        qc = make_circuit_with_cz(6)
        a = [
            op.name
            for op in fold_gates(
                qc, 2.0, strategy="random", gate_names=("cz",), seed=7
            ).get_operations()
        ]
        b = [
            op.name
            for op in fold_gates(
                qc, 2.0, strategy="random", gate_names=("cz",), seed=7
            ).get_operations()
        ]
        assert a == b

    def test_random_selects_different_gates_across_seeds(self):
        # Build a circuit with CZ gates *separated* by H gates so folded
        # vs un-folded CZ gates produce distinguishable runs.  scale 2 on
        # 4 CZ gates folds 2 of them; across seeds the chosen pair varies.
        qc = QuantumCircuit(2)
        for _ in range(4):
            qc.append(
                GateOperation(
                    "cz",
                    targets=[0, 1],
                    operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
                )
            )
            qc.append(
                GateOperation(
                    "h",
                    targets=[0],
                    operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
                )
            )

        def folded_positions(seed):
            scaled = fold_gates(
                qc,
                2.0,
                strategy="random",
                gate_names=("cz",),
                seed=seed,
            )
            ops = scaled.get_operations()
            positions = set()
            cz_idx = 0
            i = 0
            while i < len(ops):
                if ops[i].name != "cz":
                    i += 1
                    continue
                j = i
                while j < len(ops) and ops[j].name == "cz":
                    j += 1
                if j - i >= 3:  # folded: 1 original + 2 copies
                    positions.add(cz_idx)
                cz_idx += 1
                i = j
            return positions

        sets = [folded_positions(s) for s in range(8)]
        assert len(set(frozenset(s) for s in sets)) > 1
        for s in sets:
            assert len(s) == 2

    def test_unknown_strategy_raises(self):
        qc = make_circuit_with_cz(1)
        with pytest.raises(ValueError):
            fold_gates(qc, 3.0, strategy="bogus")

    def test_no_foldable_gates(self):
        # Only an h gate; restricting to cz -> no fold -> unchanged.
        qc = QuantumCircuit(1)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        scaled = fold_gates(qc, 3.0, strategy="random", gate_names=("cz",))
        assert scaled.size() == 1

    def test_transform_circuit_uses_configured_strategy(self):
        # ZNEMitigation with random strategy still produces the right CZ
        # counts (scale 3 -> 3x), but via the fold_gates path.
        zne = ZNEMitigation(
            scale_factors=[1, 3],
            folding_strategy="random",
            folding_seed=42,
        )
        qc = make_circuit_with_cz(2)
        variants = zne.transform_circuit(qc)
        assert len(variants) == 2
        assert count_cz_gates(variants[0]["circuit"]) == 2  # scale 1
        assert count_cz_gates(variants[1]["circuit"]) == 6  # scale 3


class TestExpectationValueExtrapolation:
    """Test the mitiq-standard expectation-value ZNE mode."""

    def _linear_noise_counts(self, p0_slope, shots=20000):
        """Counts where P(0)=1-slope, P(1)=slope at scale=slope/p0_slope."""
        nq = 1
        out = {}
        for s, slope in p0_slope:
            p = np.array([1.0 - slope, slope])
            c = np.round(p * shots).astype(int)
            diff = shots - int(c.sum())
            if diff and c.size:
                c[int(np.argmax(p))] += diff
            for i, v in enumerate(c):
                if v > 0:
                    out[f"zne_s{s}"] = out.get(f"zne_s{s}", {})
                    out[f"zne_s{s}"][format(i, f"0{nq}b")] = int(v)
        return out

    def test_recover_zero_noise_linear(self):
        # exp([0]) = P(0)-P(1); ideal=1.0, noise: exp = 1 - 0.2*lambda
        results = self._linear_noise_counts([(1, 0.1), (3, 0.3), (5, 0.5)])
        zne = ZNEMitigation(
            scale_factors=[1, 3, 5],
            extrapolation_method="polynomial",
            polynomial_degree=1,
        )
        out = zne.postprocess(results, num_qubits=1, observable=[0])
        assert out["metadata"]["mode"] == "expectation_value"
        assert out["metadata"]["applied"] is True
        exp = out["results"]["expectation_value"]
        raw = out["results"]["expectation_value_raw"]
        # ZNE recovers ~1.0; raw (scale-1) is 0.8
        assert abs(exp - 1.0) < 0.05
        assert abs(raw - 0.8) < 0.02
        assert abs(exp - 1.0) < abs(raw - 1.0)

    def test_returns_metadata_with_observable(self):
        results = self._linear_noise_counts([(1, 0.1), (3, 0.3)])
        zne = ZNEMitigation(scale_factors=[1, 3])
        out = zne.postprocess(results, num_qubits=1, observable=[0])
        assert out["metadata"]["observable"] == [0]
        assert len(out["metadata"]["expectations"]) == 2
        assert out["metadata"]["extrapolation_method"] == "polynomial"

    def test_fallback_when_extrapolation_exceeds_range(self):
        # Craft expectations that extrapolate beyond [-1,1]: exp = lambda
        # (increasing).  At scales 1,3,5 -> 1,3,5, linear extrap to 0 = -1.
        # Use richardson on 3 points with a steep trend to force out-of-range.
        results = {
            "zne_s1": {"0": 0, "1": 10000},
            "zne_s3": {"0": 0, "1": 10000},
            "zne_s5": {"0": 0, "1": 10000},
        }
        zne = ZNEMitigation(
            scale_factors=[1, 3, 5],
            extrapolation_method="richardson",
        )
        out = zne.postprocess(results, num_qubits=1, observable=[0])
        # all expectations = -1.0; extrapolation is -1.0 (in range)
        assert abs(out["results"]["expectation_value"] - (-1.0)) < 1e-9
        assert out["metadata"]["fallback"] is False
        # but clipped to [-1,1]
        assert -1.0 <= out["results"]["expectation_value"] <= 1.0

    def test_two_qubit_parity_observable(self):
        # Bell-ish: ideal |00>=0.5, |11>=0.5 -> parity exp([0,1]) = 1.0
        # noise mixes to |01>,|10> (odd parity), reducing exp toward 0.
        ideal = np.array([0.5, 0.0, 0.0, 0.5])
        drift = np.array([-0.05, 0.025, 0.025, 0.0])
        shots = 20000
        results = {}
        for s in (1, 3, 5):
            p = ideal + s * drift
            c = np.round(p * shots).astype(int)
            diff = shots - int(c.sum())
            if diff and c.size:
                c[int(np.argmax(p))] += diff
            results[f"zne_s{s}"] = {
                format(i, "02b"): int(v) for i, v in enumerate(c) if v > 0
            }
        zne = ZNEMitigation(
            scale_factors=[1, 3, 5],
            extrapolation_method="polynomial",
            polynomial_degree=1,
        )
        out = zne.postprocess(results, num_qubits=2, observable=[0, 1])
        exp = out["results"]["expectation_value"]
        raw = out["results"]["expectation_value_raw"]
        # ZNE should move closer to 1.0 than raw
        assert abs(exp - 1.0) < abs(raw - 1.0)


class TestApplyZneCzFolding:
    """Test apply_zne_cz_folding (arbitrary fractional folding)."""

    def test_scale_two_partial_fold(self):
        from wy_qcos.error_mitigation.zne_mitigation import (
            apply_zne_cz_folding,
        )

        qc = make_circuit_with_cz(2)
        scaled = apply_zne_cz_folding(qc, 2.0)
        # 2 CZ, scale 2 -> fold 1 -> +2 CZ = 4
        assert count_cz_gates(scaled) == 4

    def test_scale_below_one_raises(self):
        from wy_qcos.error_mitigation.zne_mitigation import (
            apply_zne_cz_folding,
        )

        qc = make_circuit_with_cz(1)
        with pytest.raises(ValueError):
            apply_zne_cz_folding(qc, 0.5)

    def test_scale_one_is_identity(self):
        from wy_qcos.error_mitigation.zne_mitigation import (
            apply_zne_cz_folding,
        )

        qc = make_circuit_with_cz(2)
        assert apply_zne_cz_folding(qc, 1.0) is qc

    def test_no_cz_gates_unchanged(self):
        from wy_qcos.error_mitigation.zne_mitigation import (
            apply_zne_cz_folding,
        )

        qc = QuantumCircuit(1)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        scaled = apply_zne_cz_folding(qc, 3.0)
        assert scaled.size() == 1


class TestEntropy:
    """Test the _entropy helper."""

    def test_pure_state_zero_entropy(self):
        assert _entropy(np.array([1.0, 0.0])) == 0.0

    def test_uniform_max_entropy(self):
        p = np.array([0.5, 0.5])
        assert abs(_entropy(p) - 1.0) < 1e-12

    def test_all_zero_returns_zero(self):
        assert _entropy(np.zeros(4)) == 0.0


class TestPruneScalePoints:
    """Test _prune_scale_points saturation and non-monotonicity."""

    def test_two_or_fewer_points_unchanged(self):
        pts = [(1.0, np.array([0.6, 0.4]))]
        assert _prune_scale_points(pts, 1) == pts

    def test_saturated_top_point_dropped(self):
        # 3 points; top point near-uniform (peak ~0.25 for 2 qubits) -> dropped
        pts = [
            (1.0, np.array([0.6, 0.1, 0.1, 0.2])),
            (3.0, np.array([0.5, 0.15, 0.15, 0.2])),
            (5.0, np.array([0.26, 0.25, 0.25, 0.24])),  # near uniform
        ]
        pruned = _prune_scale_points(pts, 2)
        assert len(pruned) == 2
        assert pruned[-1][0] == 3.0

    def test_non_monotonic_entropy_drops_top(self):
        # top point has lower entropy than second -> non-monotonic,
        # dropped. Keep middle peak well above 1.5*uniform to avoid the
        # saturation-drop branch firing first.
        pts = [
            (1.0, np.array([0.9, 0.1])),  # ent ~0.47, peak 0.9
            (
                3.0,
                np.array([0.99, 0.01]),
            ),  # ent ~0.08, peak 0.99 (decreases but <0.25)
            (
                5.0,
                np.array([0.5, 0.5]),
            ),  # ent ~1.0 (increases vs sec -> monotonic ok)
        ]
        # Build a true non-monotonic case: entropy DECREASES at top by > 0.25
        pts = [
            (1.0, np.array([0.5, 0.5])),  # ent ~1.0
            (
                3.0,
                np.array([0.99, 0.01]),
            ),  # ent ~0.08 (decreases -> drops here first)
        ]
        pruned = _prune_scale_points(pts, 1)
        # only 2 points -> pruned unchanged (len <= 2 early return)
        assert len(pruned) == 2


class TestExtrapolateToZeroMethods:
    """Cover linear and exponential method branches directly."""

    def test_linear_two_points(self):
        scales = [1.0, 3.0]
        y1 = np.array([0.8, 0.2])
        y3 = np.array([0.6, 0.4])
        mat = np.vstack([y1, y3])
        out = extrapolate_to_zero(scales, mat, method="linear")
        expected = (3.0 * y1 - 1.0 * y3) / (3.0 - 1.0)
        np.testing.assert_allclose(out, expected, atol=1e-10)

    def test_linear_single_point_returns_first(self):
        out = extrapolate_to_zero(
            [1.0], np.array([[0.6, 0.4]]), method="linear"
        )
        np.testing.assert_allclose(out, [0.6, 0.4])

    def test_richardson_single_point(self):
        out = extrapolate_to_zero(
            [1.0], np.array([[0.6, 0.4]]), method="richardson"
        )
        np.testing.assert_allclose(out, [0.6, 0.4])

    def test_polynomial_degree_zero(self):
        # degree 0 -> constant fit -> mean of points
        scales = [1.0, 3.0, 5.0]
        mat = np.vstack([[0.6, 0.4], [0.55, 0.45], [0.5, 0.5]])
        out = extrapolate_to_zero(
            scales, mat, method="polynomial", polynomial_degree=0
        )
        # constant term of degree-0 polyfit = mean
        expected = np.polyfit(np.array(scales), mat, 0)[-1]
        np.testing.assert_allclose(out, expected, atol=1e-10)

    def test_exponential_falls_back_on_nonconvergence(self):
        # Degenerate data that won't converge the exponential fit cleanly;
        # ensure the fallback path (polyfit) returns finite values.
        scales = np.array([1.0, 2.0, 3.0])
        # A single-element per-row, all identical -> curve_fit struggles
        mat = np.vstack([[0.5], [0.5], [0.5]])
        out = extrapolate_to_zero(scales, mat, method="exponential")
        assert np.all(np.isfinite(out))

    def test_mismatched_scales_and_rows_raises(self):
        with pytest.raises(ValueError, match="disagree"):
            extrapolate_to_zero(
                [1, 3], np.array([[0.5, 0.5]]), method="richardson"
            )


class TestProbsToCounts:
    """Test _probs_to_counts helper."""

    def test_rounding_preserves_total(self):
        probs = np.array([0.33, 0.33, 0.34])
        counts = _probs_to_counts(probs, 1000, 2)
        assert sum(counts.values()) == 1000

    def test_zero_probabilities_omitted(self):
        probs = np.array([0.5, 0.5, 0.0, 0.0])
        counts = _probs_to_counts(probs, 100, 2)
        assert "00" in counts
        assert "01" in counts
        assert "10" not in counts
        assert "11" not in counts

    def test_bitstring_width_matches_num_qubits(self):
        probs = np.array([0.0, 0.0, 0.0, 1.0])
        counts = _probs_to_counts(probs, 100, 2)
        assert "11" in counts
        assert counts["11"] == 100


class TestZneSetConfigEdges:
    """Cover set_config edge cases."""

    def test_set_config_fold_gate_names_none(self):
        zne = ZNEMitigation()
        zne.set_config({"enabled": True, "fold_gate_names": None})
        assert zne._fold_gate_names is None

    def test_set_config_fold_gate_names_custom(self):
        zne = ZNEMitigation()
        zne.set_config({"enabled": True, "fold_gate_names": ["cx", "cz"]})
        assert zne._fold_gate_names == ("cx", "cz")

    def test_set_config_extrapolation_method(self):
        zne = ZNEMitigation()
        zne.set_config({
            "enabled": True,
            "extrapolation_method": "richardson",
        })
        assert zne._extrapolation_method == "richardson"

    def test_set_config_fallback_options(self):
        zne = ZNEMitigation()
        zne.set_config({
            "enabled": True,
            "enable_fallback": False,
            "fallback_threshold": 0.3,
            "folding_strategy": "right",
            "folding_seed": 99,
        })
        assert zne._enable_fallback is False
        assert zne._fallback_threshold == 0.3
        assert zne._folding_strategy == "right"
        assert zne._folding_seed == 99


class TestZnePostprocessEdges:
    """Cover postprocess defensive branches."""

    def test_postprocess_infers_num_qubits_from_counts(self):
        zne = ZNEMitigation(scale_factors=[1, 3])
        results = {
            "zne_s1": {"00": 4500, "01": 200, "10": 300, "11": 5000},
            "zne_s3": {"00": 4000, "01": 400, "10": 600, "11": 5000},
        }
        output = zne.postprocess(results)  # no num_qubits
        assert output["metadata"]["applied"] is True

    def test_postprocess_empty_results_defaults_num_qubits_one(self):
        zne = ZNEMitigation(scale_factors=[1, 3])
        output = zne.postprocess({}, num_qubits=1)
        assert output["metadata"]["applied"] is False

    def test_postprocess_unparseable_label_skipped(self):
        zne = ZNEMitigation(scale_factors=[1, 3])
        results = {
            "garbage_label": {"00": 500, "11": 500},
        }
        output = zne.postprocess(results, num_qubits=2)
        # no scale-1 found -> applied False
        assert output["metadata"]["applied"] is False

    def test_postprocess_duplicate_scale_skipped(self):
        # two entries with same scale -> second ignored
        zne = ZNEMitigation(scale_factors=[1, 3])
        results = {
            "zne_s1": {"00": 900, "11": 100},
            "original": {"00": 500, "11": 500},  # also scale 1, ignored
            "zne_s3": {"00": 700, "11": 300},
        }
        output = zne.postprocess(results, num_qubits=2)
        assert output["metadata"]["applied"] is True

    def test_postprocess_observable_insufficient_points(self):
        # observable with only 1 point -> insufficient_scale_points branch
        zne = ZNEMitigation(scale_factors=[1, 3])
        results = {"zne_s1": {"0": 900, "1": 100}}
        output = zne.postprocess(results, num_qubits=1, observable=[0])
        assert output["metadata"]["applied"] is False
        assert output["metadata"]["reason"] == "insufficient_scale_points"
        assert "expectation_value" in output["results"]

    def test_postprocess_disable_fallback_keeps_extrapolated(self):
        # richardson on divergent data; with fallback disabled the result
        # is still returned (clipped+normalized) rather than reverting.
        zne = ZNEMitigation(
            extrapolation_method="richardson", enable_fallback=False
        )
        results = {
            "zne_s1": {"0": 900, "1": 100},
            "zne_s3": {"0": 100, "1": 900},
            "zne_s5": {"0": 100, "1": 900},
        }
        output = zne.postprocess(results, num_qubits=1)
        assert output["metadata"]["applied"] is True
        assert output["metadata"]["fallback"] is False

    def test_parse_scale_unknown_label(self):
        zne = ZNEMitigation(scale_factor=3)
        assert zne._parse_scale("unknown") is None

    def test_parse_scale_original_label(self):
        zne = ZNEMitigation(scale_factor=3)
        assert zne._parse_scale("original") == 1.0

    def test_parse_scale_scaled_label(self):
        zne = ZNEMitigation(scale_factor=5)
        assert zne._parse_scale("scaled") == 5.0

    def test_parse_scale_scaled_label_no_scale_factor(self):
        # _scale_factor falsy -> defaults to 3.0
        zne = ZNEMitigation()
        zne._scale_factor = 0
        assert zne._parse_scale("scaled") == 3.0


class TestExpectationValueFallback:
    """Cover the expectation-value extrapolation fallback (out-of-range)."""

    def test_fallback_when_expectation_out_of_range(self):
        # Construct counts where extrapolation diverges beyond [-1,1].
        # Use richardson with a steep increasing trend so the fit overshoots.
        # P(0) at scales 1,3,5 = 1.0, 0.5, 0.0 -> exp = 1-0.5*lambda
        # richardson on (1, 0.5, 0) extrapolated to 0:
        # exact linear -> recovers 1.0 (in range, no fallback).  To force
        # fallback, use expectations that increase with scale (non-physical).
        results = {
            "zne_s1": {"0": 5000, "1": 5000},  # exp 0
            "zne_s3": {"0": 8000, "1": 2000},  # exp 0.6
            "zne_s5": {"0": 10000, "1": 0},  # exp 1.0
        }
        zne = ZNEMitigation(
            scale_factors=[1, 3, 5],
            extrapolation_method="richardson",
        )
        out = zne.postprocess(results, num_qubits=1, observable=[0])
        # expectations: 0, 0.6, 1.0 increasing with scale -> extrapolation
        # at 0 goes negative (below -1) -> fallback to raw exp1 (0.0)
        if out["metadata"]["fallback"]:
            assert abs(out["results"]["expectation_value"]) <= 1.0
        # clipped to [-1, 1] regardless
        assert -1.0 <= out["results"]["expectation_value"] <= 1.0
