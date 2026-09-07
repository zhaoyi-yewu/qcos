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

"""Shared utility functions for error mitigation."""

from __future__ import annotations

from typing import Dict, Sequence

import numpy as np


def counts_to_probabilities(
    counts: Dict[str, int], num_qubits: int
) -> np.ndarray:
    """Convert measurement counts to a probability vector.

    Args:
        counts: Counts dictionary mapping bitstrings to occurrence counts.
        num_qubits: Number of qubits.

    Returns:
        Probability vector of length 2**num_qubits.
    """
    dim = 2**num_qubits
    probs = np.zeros(dim, dtype=float)
    total = sum(counts.values())
    if total == 0:
        return probs
    for bitstring, count in counts.items():
        idx = int(bitstring, 2)
        if idx < dim:
            probs[idx] = count
    return probs / total


def counts_to_samples(counts: Dict[str, int], num_qubits: int) -> np.ndarray:
    """Expand counts into a sample array.

    Args:
        counts: Counts dictionary mapping bitstrings to occurrence counts.
        num_qubits: Number of qubits.

    Returns:
        2-D array of shape (total_shots, num_qubits) with 0/1 entries.
    """
    samples = []
    for bitstring, count in counts.items():
        bits = [int(b) for b in bitstring]
        if len(bits) < num_qubits:
            bits = [0] * (num_qubits - len(bits)) + bits
        samples.extend([bits] * count)
    return np.asarray(samples, dtype=int).reshape(-1, num_qubits)


def samples_to_probabilities(
    samples: np.ndarray, num_qubits: int
) -> np.ndarray:
    """Compute probability vector from sample rows.

    Args:
        samples: 2-D array of shape (nshots, num_qubits) with 0/1 entries.
        num_qubits: Number of qubits.

    Returns:
        Probability vector of length 2**num_qubits.
    """
    if samples.size == 0:
        return np.zeros(2**num_qubits, dtype=float)
    weights = 2 ** np.arange(num_qubits - 1, -1, -1)
    indices = (samples * weights).sum(axis=1)
    counts = np.bincount(indices, minlength=2**num_qubits).astype(float)
    total = counts.sum()
    if total == 0:
        return counts
    return counts / total


def marginal_samples(
    samples: np.ndarray, support: Sequence[int]
) -> np.ndarray:
    """Extract marginal samples on a subset of qubits.

    Args:
        samples: 2-D array of shape (nshots, num_qubits).
        support: Qubit column indices to extract.

    Returns:
        2-D array of shape (nshots, len(support)).
    """
    if not support:
        return np.zeros((samples.shape[0], 0), dtype=int)
    return samples[:, list(support)]


def expectation_from_probabilities(
    probabilities: np.ndarray, support: Sequence[int]
) -> float:
    """Compute Z-basis parity expectation value from probabilities.

    Args:
        probabilities: 1-D probability vector of length 2**len(support).
        support: Qubit indices for the parity observable.

    Returns:
        Z-parity expectation value in [-1, 1].
    """
    if not support:
        return 1.0
    num = len(support)
    probs = probabilities.reshape([2] * num)
    parity = np.zeros([2] * num, dtype=int)
    for i in range(num):
        shape = [1] * num
        shape[i] = 2
        parity += np.arange(2).reshape(shape)
    sign = 1.0 - 2.0 * (parity % 2)
    return float((probs * sign).sum())


def clip_and_normalize(probs: np.ndarray) -> np.ndarray:
    """Clip probabilities to [0, 1] and renormalize.

    Args:
        probs: Input probability vector.

    Returns:
        Clipped and renormalized probability vector.
    """
    clipped = np.clip(probs, 0.0, 1.0)
    total = clipped.sum()
    if total == 0:
        return clipped
    return clipped / total
