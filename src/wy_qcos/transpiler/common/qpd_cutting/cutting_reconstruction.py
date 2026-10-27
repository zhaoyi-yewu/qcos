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

"""Functions for reconstructing the results of circuit cutting experiments."""

from __future__ import annotations

from collections.abc import Sequence, Hashable, Mapping

import numpy as np
from qiskit.quantum_info import PauliList
from qiskit.primitives import (
    SamplerResult,  # for SamplerV1
    PrimitiveResult,  # for SamplerV2
)

from .utils.observable_grouping import (
    CommutingObservableGroup,
    ObservableCollection,
)
from .cutting_decomposition import decompose_observables
from .cutting_experiments import _get_pauli_indices
from .qpd import WeightType


def reconstruct_expectation_values(
    results: (
        SamplerResult
        | PrimitiveResult
        | dict[Hashable, SamplerResult | PrimitiveResult]
    ),
    coefficients: Sequence[tuple[float, WeightType]],
    observables: PauliList | dict[Hashable, PauliList],
) -> list[float]:
    r"""Reconstruct expectations from subexperiment results.

    Args:
        results: Results from running cutting subexperiments. If the circuit
            was not partitioned and run separately, this should be a
            :class:`~qiskit.primitives.SamplerResult` or a dictionary mapping
            one partition to its results. For a partitioned circuit, this
            should map partition labels to each partition's results.

            Results must follow the ordering from
            :func:`.generate_cutting_experiments`: one result per sample and
            observable, as shown below. The Qiskit Sampler primitive preserves
            submission order. Users generating experiments another way should
            order them as follows before submitting them to the sampler:

            .. math::
                [sample_{0}observable_{0}, \ldots,
                sample_{0}observable_{N-1}, \ldots,
                sample_{M-1}observable_{N-1}]

        coefficients: Coefficients for each unique subexperiment. Each element
            contains a ``float`` coefficient and its :class:`.WeightType`.
            Each subexperiment contribution is multiplied by its coefficient,
            then the terms are summed to reconstruct the expectation value.
        observables: Observables whose expectation values will be calculated.
            This should be a :class:`~qiskit.quantum_info.PauliList` when
            ``results`` is a :class:`~qiskit.primitives.SamplerResult`.
            Otherwise, it should map partition labels to their observables.

    Returns:
        A ``list`` of ``float``\ s, such that each float is an expectation
        value corresponding to the input observable in the same position

    Raises:
        ValueError: ``observables`` and ``results`` are of incompatible types.
        ValueError: An input observable has a phase not equal to 1.
    """
    # If circuit was not separated, transform input data structures to
    # dictionary format.  Perform some input validation in either case.
    if isinstance(observables, PauliList):
        if not isinstance(results, (SamplerResult, PrimitiveResult)):
            raise ValueError(
                "If observables is a PauliList, results must be a "
                "SamplerResult or PrimitiveResult instance."
            )
        if any(obs.phase != 0 for obs in observables):
            raise ValueError("An input observable has a phase not equal to 1.")
        subobservables_by_subsystem: Mapping[Hashable, PauliList] = (
            decompose_observables(observables, "A" * len(observables[0]))
        )
        results_dict: Mapping[Hashable, SamplerResult | PrimitiveResult] = {
            "A": results
        }
        expvals = np.zeros(len(observables))

    elif isinstance(observables, Mapping):
        if not isinstance(results, Mapping):
            raise ValueError(
                "If observables is a dictionary, results must also be a "
                "dictionary."
            )
        if observables.keys() != results.keys():
            raise ValueError(
                "Observable and result subsystem labels do not match."
            )
        results_dict = results
        for label, subobservable in observables.items():
            if any(obs.phase != 0 for obs in subobservable):
                raise ValueError(
                    "An input observable has a phase not equal to 1."
                )
        subobservables_by_subsystem = observables
        expvals = np.zeros(len(list(observables.values())[0]))

    else:
        raise ValueError("observables must be either a PauliList or dict.")

    subsystem_observables = {
        label: ObservableCollection(subobservables)
        for label, subobservables in subobservables_by_subsystem.items()
    }

    # Validate that the number of subexperiments executed is consistent with
    # the number of coefficients and observable groups.
    for label, so in subsystem_observables.items():
        current_result = results_dict[label]
        if isinstance(current_result, SamplerResult):
            # SamplerV1 provides a SamplerResult
            current_result = current_result.quasi_dists
        if len(current_result) != len(coefficients) * len(so.groups):
            raise ValueError(
                f"The number of subexperiments in subsystem '{label}' "
                f"({len(current_result)}) should equal the coefficient count "
                f"({len(coefficients)}) times the mutually commuting "
                f"subobservable groups ({len(so.groups)}), but it does not."
            )

    # Reconstruct the expectation values
    for i, coeff in enumerate(coefficients):
        current_expvals = np.ones((len(expvals),))
        for label, so in subsystem_observables.items():
            subsystem_expvals = [
                np.zeros(len(cog.commuting_observables)) for cog in so.groups
            ]
            current_result = results_dict[label]
            for k, cog in enumerate(so.groups):
                idx = i * len(so.groups) + k
                if isinstance(current_result, SamplerResult):
                    # SamplerV1 provides a SamplerResult
                    quasi_probs = current_result.quasi_dists[idx]
                    for outcome, quasi_prob in quasi_probs.items():
                        subsystem_expvals[k] += quasi_prob * _process_outcome(
                            cog, outcome
                        )
                else:
                    # SamplerV2 provides a PrimitiveResult
                    data_pub = current_result[idx].data
                    obs_array = data_pub.observable_measurements.array
                    qpd_array = data_pub.qpd_measurements.array
                    shots = qpd_array.shape[0]
                    for j in range(shots):
                        obs_outcomes = int.from_bytes(obs_array[j], "big")
                        qpd_outcomes = int.from_bytes(qpd_array[j], "big")
                        subsystem_expvals[k] += (
                            1 / shots
                        ) * _process_outcome_v2(
                            cog, obs_outcomes, qpd_outcomes
                        )

            for k, subobservable in enumerate(
                subobservables_by_subsystem[label]
            ):
                current_expvals[k] *= np.mean([
                    subsystem_expvals[m][n]
                    for m, n in so.lookup[subobservable]
                ])

        expvals += coeff[0] * current_expvals

    return list(expvals)


def _process_outcome(
    cog: CommutingObservableGroup, outcome: int | str, /
) -> np.typing.NDArray[np.float64]:
    """Process a single outcome of a QPD experiment with observables.

    Args:
        cog: The observable set being measured by the current experiment
        outcome: The outcome of the classical bits

    Returns:
        A 1D array of the observable measurements.  The elements of
        this vector correspond to the elements of
        ``cog.commuting_observables``,
        and each result will be either +1 or -1.
    """
    num_meas_bits = len(_get_pauli_indices(cog))

    outcome = _outcome_to_int(outcome)
    obs_outcomes = outcome & ((1 << num_meas_bits) - 1)
    qpd_outcomes = outcome >> num_meas_bits

    return _process_outcome_v2(cog, obs_outcomes, qpd_outcomes)


def _process_outcome_v2(
    cog: CommutingObservableGroup, obs_outcomes: int, qpd_outcomes: int, /
) -> np.typing.NDArray[np.float64]:
    """Process a single outcome of a QPD experiment with observables.

    Args:
        cog: The observable set being measured by the current experiment
        obs_outcomes: Integer containing the outcome bits of the
            ``observable_measurements`` register.
        qpd_outcomes: Integer containing the outcome bits of the
            ``qpd_measurements`` register.

    Returns:
        A 1D array of the observable measurements.  The elements of
        this vector correspond to the elements of
        ``cog.commuting_observables``,
        and each result will be either +1 or -1.
    """
    # qpd_factor will be -1 or +1, depending on the overall parity of qpd
    # measurements.
    qpd_factor = 1 - 2 * (qpd_outcomes.bit_count() & 1)

    rv = np.zeros(len(cog.pauli_bitmasks))
    for i, mask in enumerate(cog.pauli_bitmasks):
        # obs will be -1 or +1, depending on the measurement
        # of the current operator.
        obs = 1 - 2 * ((obs_outcomes & mask).bit_count() & 1)
        rv[i] = qpd_factor * obs

    return rv


def _outcome_to_int(outcome: int | str) -> int:
    if isinstance(outcome, int):
        return outcome
    outcome = outcome.replace(" ", "")
    if len(outcome) < 2 or outcome[1] in ("0", "1"):
        outcome = outcome.replace(" ", "")
        return int(f"0b{outcome}", 0)
    return int(outcome, 0)
