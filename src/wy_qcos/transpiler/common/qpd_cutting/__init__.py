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

"""Dependency-free circuit cutting.

The public workflow is implemented in this package and uses the local
:class:`Circuit` representation.  Legacy SDK-bound modules in this source tree
are retained for source-history reference but are no longer part of the
package's public import surface.
"""

from __future__ import annotations
from importlib.metadata import version, PackageNotFoundError

from ._wire_cutting_core import (
    Circuit,
    Operation,
    WireCut,
    exact_expectations_without_cut,
)
from ._wire_cutting_service import (
    CuttingExperiment,
    CuttingExperimentBatch,
    CuttingExperimentResults,
    Reconstruction,
    WireCuttingProblem,
    cut_wires,
    evaluate_and_reconstruct,
    evaluate_and_reconstruct_tensor_network,
    execute_experiments,
    execute_tensor_network_experiments,
    find_cuts,
    find_width_limited_wire_cuts,
    generate_cutting_experiments,
    generate_tensor_network_experiments,
    partition_problem,
    reconstruct_expectation_values,
    reconstruct_tensor_network,
    restrict_to_causal_cone,
)
from ._wire_cutting_workflow import (
    CutLocation,
    CutPlan,
    Fragment,
    FragmentExperiment,
    LocalTensorExperiment,
    LocalTensorExperimentBatch,
    LocalTensorExperimentResults,
    ShotAllocation,
    allocate_shots_by_variance,
)
from .observables import (
    PauliSum,
    PauliTerm,
    gather_unique_observable_terms,
    group_qubitwise_commuting,
    reconstruct_observable_expvals_from_terms,
)
from ._gate_cutting import (
    CuttingPlan as GateCuttingPlan,
    exact_expectation_values as exact_gate_expectation_values,
    find_cuts as find_gate_cuts,
    reconstruct_expectation_values as reconstruct_gate_cut_expectation_values,
)
from ._quarkstudio import QuarkStudioFragmentEvaluator

# Migration alias for the local lightweight circuit implementation.
QuantumCircuit = Circuit

try:
    __version__ = version("qiskit-addon-cutting")
except PackageNotFoundError:  # pragma: no cover
    # Package is not installed
    pass

__all__ = [
    "Circuit",
    "QuantumCircuit",
    "Operation",
    "WireCut",
    "CutLocation",
    "CutPlan",
    "exact_expectations_without_cut",
    "Fragment",
    "FragmentExperiment",
    "LocalTensorExperiment",
    "LocalTensorExperimentBatch",
    "LocalTensorExperimentResults",
    "ShotAllocation",
    "WireCuttingProblem",
    "CuttingExperiment",
    "CuttingExperimentBatch",
    "CuttingExperimentResults",
    "Reconstruction",
    "find_cuts",
    "find_width_limited_wire_cuts",
    "cut_wires",
    "partition_problem",
    "generate_cutting_experiments",
    "execute_experiments",
    "reconstruct_expectation_values",
    "evaluate_and_reconstruct",
    "restrict_to_causal_cone",
    "generate_tensor_network_experiments",
    "execute_tensor_network_experiments",
    "reconstruct_tensor_network",
    "evaluate_and_reconstruct_tensor_network",
    "allocate_shots_by_variance",
    "PauliTerm",
    "PauliSum",
    "group_qubitwise_commuting",
    "gather_unique_observable_terms",
    "reconstruct_observable_expvals_from_terms",
    "GateCuttingPlan",
    "find_gate_cuts",
    "reconstruct_gate_cut_expectation_values",
    "exact_gate_expectation_values",
    "QuarkStudioFragmentEvaluator",
]
