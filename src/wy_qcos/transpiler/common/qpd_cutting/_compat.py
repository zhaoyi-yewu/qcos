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

"""Dispatch shared entry points without changing either workflow's semantics.

Qiskit circuits, partition dictionaries, and sampler results are passed
directly to the vendored upstream implementation, with all arguments and
exceptions preserved.  The existing :class:`Circuit`,
:class:`WireCuttingProblem`, and :class:`CuttingExperimentResults` objects
continue to select this project's original backend-neutral workflow.

The two workflows keep their own argument names and return types.  In
particular, the native experiment generator accepts ``problem=...`` and the
upstream generator accepts ``circuits=...``.  No implicit conversion or
fallback on an exception is performed.  Use :func:`conversion.to_qiskit`
explicitly to run a native circuit through the upstream cutting algorithms.
The exposed introspection signatures and documentation match upstream.
"""

from __future__ import annotations

from functools import wraps

from . import _wire_cutting_service as _legacy
from ._wire_cutting_core import Circuit
from .automated_cut_finding import find_cuts as _find_cuts
from .cutting_decomposition import partition_problem as _partition_problem
from .cutting_experiments import (
    generate_cutting_experiments as _generate_cutting_experiments,
)
from .cutting_reconstruction import (
    reconstruct_expectation_values as _reconstruct_expectation_values,
)
from .wire_cutting_transforms import cut_wires as _cut_wires


@wraps(_find_cuts)
def find_cuts(*args, **kwargs):
    circuit = args[0] if args else kwargs.get("circuit")
    if isinstance(circuit, Circuit):
        return _legacy.find_cuts(*args, **kwargs)
    return _find_cuts(*args, **kwargs)


@wraps(_cut_wires)
def cut_wires(*args, **kwargs):
    circuit = args[0] if args else kwargs.get("circuit")
    if isinstance(circuit, Circuit):
        return _legacy.cut_wires(*args, **kwargs)
    return _cut_wires(*args, **kwargs)


@wraps(_partition_problem)
def partition_problem(*args, **kwargs):
    circuit = args[0] if args else kwargs.get("circuit")
    if isinstance(circuit, Circuit):
        return _legacy.partition_problem(*args, **kwargs)
    return _partition_problem(*args, **kwargs)


@wraps(_generate_cutting_experiments)
def generate_cutting_experiments(*args, **kwargs):
    problem = args[0] if args else kwargs.get("problem")
    if isinstance(problem, _legacy.WireCuttingProblem):
        return _legacy.generate_cutting_experiments(*args, **kwargs)
    return _generate_cutting_experiments(*args, **kwargs)


@wraps(_reconstruct_expectation_values)
def reconstruct_expectation_values(*args, **kwargs):
    results = args[0] if args else kwargs.get("results")
    if isinstance(results, _legacy.CuttingExperimentResults):
        return _legacy.reconstruct_expectation_values(*args, **kwargs)
    return _reconstruct_expectation_values(*args, **kwargs)


__all__ = [
    "find_cuts",
    "cut_wires",
    "partition_problem",
    "generate_cutting_experiments",
    "reconstruct_expectation_values",
]
