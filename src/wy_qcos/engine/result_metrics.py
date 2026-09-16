#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# ----------------------------------------------------------------------

"""Metrics for comparing sampling-result probability distributions."""

import math
from numbers import Real


PROBABILITY_FIDELITY_METHOD = "squared_bhattacharyya"


def _normalize_distribution(distribution, name):
    """Validate and normalize a count or probability dictionary."""
    if not isinstance(distribution, dict) or not distribution:
        raise ValueError(f"{name} must be a non-empty dictionary")

    bit_widths = set()
    normalized = {}
    total = 0.0
    for state, value in distribution.items():
        if not isinstance(state, str) or not state or set(state) - {"0", "1"}:
            raise ValueError(
                f"{name} contains an invalid bitstring: {state!r}"
            )
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{name} contains a non-numeric value")

        value = float(value)
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} values must be finite and non-negative")

        bit_widths.add(len(state))
        normalized[state] = value
        total += value

    if len(bit_widths) != 1:
        raise ValueError(f"{name} contains different bit widths")
    if total <= 0:
        raise ValueError(f"{name} must have a positive total weight")

    return {state: value / total for state, value in normalized.items()}, (
        bit_widths.pop()
    )


def squared_bhattacharyya_coefficient(observed, expected):
    """Return the squared Bhattacharyya coefficient of two distributions.

    Inputs may contain either counts or probabilities; both are normalized
    before comparison. Missing states are treated as having zero probability.
    """
    observed, observed_width = _normalize_distribution(observed, "observed")
    expected, expected_width = _normalize_distribution(expected, "expected")
    if observed_width != expected_width:
        raise ValueError(
            "observed and expected distributions have different bit widths"
        )

    coefficient = sum(
        math.sqrt(observed.get(state, 0.0) * expected.get(state, 0.0))
        for state in observed.keys() | expected.keys()
    )
    return min(1.0, max(0.0, coefficient * coefficient))
