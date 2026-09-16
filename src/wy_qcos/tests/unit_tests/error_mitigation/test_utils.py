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

import numpy as np

from wy_qcos.error_mitigation.utils import (
    counts_to_probabilities,
    counts_to_samples,
    samples_to_probabilities,
    marginal_samples,
    expectation_from_probabilities,
    clip_and_normalize,
    closest_positive_distribution,
)


class TestCountsToProbabilities:
    """Test counts_to_probabilities function."""

    def test_uniform_distribution(self):
        counts = {"00": 250, "01": 250, "10": 250, "11": 250}
        probs = counts_to_probabilities(counts, 2)
        np.testing.assert_allclose(probs, [0.25, 0.25, 0.25, 0.25])

    def test_single_outcome(self):
        counts = {"00": 1000}
        probs = counts_to_probabilities(counts, 2)
        assert probs[0] == 1.0
        assert np.sum(probs[1:]) == 0.0

    def test_empty_counts(self):
        counts = {}
        probs = counts_to_probabilities(counts, 2)
        np.testing.assert_allclose(probs, np.zeros(4))

    def test_three_qubits(self):
        counts = {"000": 500, "111": 500}
        probs = counts_to_probabilities(counts, 3)
        assert len(probs) == 8
        assert probs[0] == 0.5
        assert probs[7] == 0.5
        assert np.sum(probs[1:7]) == 0.0

    def test_probabilities_sum_to_one(self):
        counts = {"00": 300, "01": 200, "10": 100, "11": 400}
        probs = counts_to_probabilities(counts, 2)
        np.testing.assert_allclose(np.sum(probs), 1.0)


class TestCountsToSamples:
    """Test counts_to_samples function."""

    def test_basic_expansion(self):
        counts = {"00": 2, "11": 3}
        samples = counts_to_samples(counts, 2)
        assert samples.shape == (5, 2)
        assert samples.dtype == int

    def test_correct_counts_in_samples(self):
        counts = {"00": 100, "11": 200}
        samples = counts_to_samples(counts, 2)
        zeros = np.sum(np.all(samples == 0, axis=1))
        ones = np.sum(np.all(samples == 1, axis=1))
        assert zeros == 100
        assert ones == 200

    def test_single_qubit(self):
        counts = {"0": 600, "1": 400}
        samples = counts_to_samples(counts, 1)
        assert samples.shape == (1000, 1)
        assert np.sum(samples[:, 0] == 0) == 600
        assert np.sum(samples[:, 0] == 1) == 400


class TestSamplesToProbabilities:
    """Test samples_to_probabilities function."""

    def test_basic_conversion(self):
        samples = np.array([[0, 0], [0, 0], [1, 1], [1, 1]])
        probs = samples_to_probabilities(samples, 2)
        np.testing.assert_allclose(probs, [0.5, 0.0, 0.0, 0.5])

    def test_empty_samples(self):
        samples = np.zeros((0, 2), dtype=int)
        probs = samples_to_probabilities(samples, 2)
        np.testing.assert_allclose(probs, np.zeros(4))

    def test_roundtrip_with_counts(self):
        original_counts = {"00": 300, "01": 200, "10": 100, "11": 400}
        samples = counts_to_samples(original_counts, 2)
        probs = samples_to_probabilities(samples, 2)
        np.testing.assert_allclose(np.sum(probs), 1.0, atol=1e-10)


class TestMarginalSamples:
    """Test marginal_samples function."""

    def test_extract_subset(self):
        samples = np.array([[0, 1, 0], [1, 0, 1], [0, 0, 1]])
        marginal = marginal_samples(samples, [0, 2])
        expected = np.array([[0, 0], [1, 1], [0, 1]])
        np.testing.assert_array_equal(marginal, expected)

    def test_empty_support(self):
        samples = np.array([[0, 1], [1, 0]])
        marginal = marginal_samples(samples, [])
        assert marginal.shape == (2, 0)

    def test_single_qubit(self):
        samples = np.array([[0, 1, 0], [1, 0, 1]])
        marginal = marginal_samples(samples, [1])
        expected = np.array([[1], [0]])
        np.testing.assert_array_equal(marginal, expected)


class TestExpectationFromProbabilities:
    """Test expectation_from_probabilities function."""

    def test_pure_zero_state(self):
        probs = np.array([1.0, 0.0])
        exp = expectation_from_probabilities(probs, [0])
        assert exp == 1.0

    def test_pure_one_state(self):
        probs = np.array([0.0, 1.0])
        exp = expectation_from_probabilities(probs, [0])
        assert exp == -1.0

    def test_maximally_mixed(self):
        probs = np.array([0.5, 0.5])
        exp = expectation_from_probabilities(probs, [0])
        np.testing.assert_allclose(exp, 0.0, atol=1e-10)

    def test_empty_support(self):
        probs = np.array([1.0])
        exp = expectation_from_probabilities(probs, [])
        assert exp == 1.0

    def test_two_qubit_parity(self):
        probs = np.array([0.5, 0.0, 0.0, 0.5])
        exp = expectation_from_probabilities(probs, [0, 1])
        np.testing.assert_allclose(exp, 1.0, atol=1e-10)

    def test_anti_correlated(self):
        probs = np.array([0.0, 0.5, 0.5, 0.0])
        exp = expectation_from_probabilities(probs, [0, 1])
        np.testing.assert_allclose(exp, -1.0, atol=1e-10)


class TestClipAndNormalize:
    """Test clip_and_normalize function."""

    def test_already_valid(self):
        probs = np.array([0.3, 0.7])
        result = clip_and_normalize(probs)
        np.testing.assert_allclose(result, [0.3, 0.7])

    def test_negative_values(self):
        probs = np.array([-0.1, 0.6, 0.5])
        result = clip_and_normalize(probs)
        assert np.all(result >= 0)
        np.testing.assert_allclose(np.sum(result), 1.0)

    def test_overflow_values(self):
        probs = np.array([1.2, 0.3])
        result = clip_and_normalize(probs)
        assert np.all(result <= 1)
        np.testing.assert_allclose(np.sum(result), 1.0)

    def test_all_zeros(self):
        probs = np.array([0.0, 0.0, 0.0])
        result = clip_and_normalize(probs)
        np.testing.assert_allclose(result, [0.0, 0.0, 0.0])

    def test_mixed_invalid(self):
        probs = np.array([-0.2, 0.8, 1.1, 0.3])
        result = clip_and_normalize(probs)
        assert np.all(result >= 0)
        assert np.all(result <= 1)
        np.testing.assert_allclose(np.sum(result), 1.0)


class TestClosestPositiveDistribution:
    """Test closest_positive_distribution (mitiq-style L2 projection)."""

    def test_already_valid(self):
        probs = np.array([0.3, 0.7])
        result = closest_positive_distribution(probs)
        np.testing.assert_allclose(result, [0.3, 0.7])

    def test_negative_elements_reach_zero(self):
        # [-1, 0.1, -1, 0.2] -> [0, ~0.4503, 0, ~0.5497]
        result = closest_positive_distribution(
            np.array([-1.0, 0.1, -1.0, 0.2])
        )
        assert np.all(result >= 0)
        np.testing.assert_allclose(np.sum(result), 1.0)
        np.testing.assert_allclose(result[0], 0.0, atol=1e-6)
        np.testing.assert_allclose(result[2], 0.0, atol=1e-6)
        # Positive mass redistributed proportionally, not equally.
        assert result[3] > result[1] > 0.0

    def test_matches_mitiq_reference_values(self):
        # Reference values from mitiq's test_closest_positive_distribution.
        cases = [
            ([0.3, 0.7], [0.3, 0.7]),
            ([-0.1, 1.1], [0.0, 1.0]),
            ([10, 10], [0.5, 0.5]),
            ([-1, 1, -1, 1], [0.0, 0.5, 0.0, 0.5]),
            ([-1, 0.1, -1, 0.2], [0.0, 0.450317, 0.0, 0.549683]),
        ]
        for quasi, expected in cases:
            result = closest_positive_distribution(np.array(quasi))
            np.testing.assert_allclose(result, expected, atol=1e-4)

    def test_sum_to_one_and_nonneg(self):
        rng = np.random.default_rng(0)
        for _ in range(20):
            q = rng.normal(-0.5, 1.5, size=8)
            result = closest_positive_distribution(q)
            assert np.all(result >= -1e-9)
            np.testing.assert_allclose(np.sum(result), 1.0, atol=1e-6)

    def test_all_zero_input(self):
        # Degenerate input: projection is the uniform distribution.
        result = closest_positive_distribution(np.zeros(4))
        np.testing.assert_allclose(result, [0.25, 0.25, 0.25, 0.25])


class TestCountsToSamplesPadding:
    """Cover the short-bitstring padding branch."""

    def test_short_bitstring_padded(self):
        # "1" for 2 qubits -> padded to "01"
        counts = {"1": 2}
        samples = counts_to_samples(counts, 2)
        assert samples.shape == (2, 2)
        # padded to [0, 1]
        assert np.all(samples == [0, 1])

    def test_mixed_length_bitstrings(self):
        counts = {"0": 1, "11": 1}
        samples = counts_to_samples(counts, 2)
        assert samples.shape == (2, 2)
        # "0" -> [0,0], "11" -> [1,1]
        assert np.all(samples[0] == [0, 0])
        assert np.all(samples[1] == [1, 1])


class TestSamplesToProbabilitiesZeroTotal:
    """Cover the total==0 early-return branch."""

    def test_all_zero_samples(self):
        # samples of all-zero rows -> bincount all at index 0, total = n
        # To hit the total==0 branch we need an empty-ish array; a (0,2)
        # array is already covered. Use a 2-row all-zero with num_qubits=0
        # is not meaningful. Instead verify the guard exists: a zero-length
        # weights path. The empty case is the practical trigger.
        samples = np.zeros((0, 2), dtype=int)
        probs = samples_to_probabilities(samples, 2)
        np.testing.assert_allclose(probs, np.zeros(4))


class TestClosestPositiveDistributionFallback:
    """Cover the scipy-unavailable / non-converging fallback branch."""

    def test_fallback_to_clip_and_normalize_when_scipy_missing(
        self, monkeypatch
    ):
        import wy_qcos.error_mitigation.utils as utils_mod

        # Force scipy.optimize import to fail inside the function so the
        # except branch runs and falls back to clip_and_normalize.
        real_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def fake_import(name, *args, **kwargs):
            if name == "scipy.optimize":
                raise ImportError("simulated missing scipy")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fake_import)
        # quasi with a large negative -> clip_and_normalize zeroes the negative
        result = utils_mod.closest_positive_distribution(
            np.array([-0.5, 0.6, 0.0, 0.9])
        )
        assert np.all(result >= 0)
        np.testing.assert_allclose(np.sum(result), 1.0)

    def test_fallback_when_optimizer_does_not_succeed(self, monkeypatch):
        import wy_qcos.error_mitigation.utils as utils_mod

        class _FakeResult:
            success = False
            x = None

        class _FakeOptimize:
            @staticmethod
            def minimize(*args, **kwargs):
                return _FakeResult()

            class Bounds:
                def __init__(self, *a, **k):
                    pass

            class LinearConstraint:
                def __init__(self, *a, **k):
                    pass

        # Pre-import scipy.optimize in the real module, then patch it.
        import scipy.optimize  # noqa: F401  ensure real import works first

        import sys

        monkeypatch.setitem(sys.modules, "scipy.optimize", _FakeOptimize)
        result = utils_mod.closest_positive_distribution(
            np.array([-0.3, 0.8, 0.2, 0.3])
        )
        # falls back to clip_and_normalize
        assert np.all(result >= 0)
        np.testing.assert_allclose(np.sum(result), 1.0)
