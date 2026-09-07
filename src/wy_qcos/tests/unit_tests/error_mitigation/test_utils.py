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

from wy_qcos.error_mitigation.utils import (
    counts_to_probabilities,
    counts_to_samples,
    samples_to_probabilities,
    marginal_samples,
    expectation_from_probabilities,
    clip_and_normalize,
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
