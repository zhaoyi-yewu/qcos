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

"""Public, backend-neutral API for Qiskit-free wire cutting.

This module mirrors the useful separation in ``qiskit_addon_cutting`` while
remaining independent of Qiskit:

1. mark or automatically find wire cuts;
2. partition a static unitary circuit;
3. generate concrete fragment measurement experiments;
4. execute them with a user-supplied evaluator; and
5. reconstruct product-Pauli expectation values.

An observable is a mapping such as ``{0: "X", 3: "Z"}``.  It describes the
product measurement in the corresponding local Pauli bases; omitted qubits are
identities.  To measure in another local basis, append that basis rotation to
the input circuit and request a ``"Z"`` measurement on that qubit.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Iterable, Mapping, Sequence

from ._wire_cutting_core import Circuit, PauliWord, WireCut, _PAULIS
from ._wire_cutting_workflow import (
    CutLocation,
    CutPlan,
    FragmentExperiment,
    GeneratedWireCuttingExperiments,
    LocalTensorExperimentBatch,
    LocalTensorExperimentResults,
    QPDTerm,
    apply_wire_cuts,
    contract_local_tensor_results,
    evaluate_exact_fragment,
    execute_local_tensor_experiments,
    find_wire_cuts,
    find_width_limited_wire_cuts as _find_width_limited_wire_cuts,
    generate_wire_cutting_experiments as _compile_wire_cutting_experiments,
    generate_local_tensor_experiments as _generate_local_tensor_experiments,
    restrict_to_observable_causal_cone,
)


@dataclass(frozen=True)
class WireCuttingProblem:
    """A partitioned wire-cut circuit and optional requested observables.

    ``subcircuits`` contains independent fragments.  It is deliberately a
    tuple of plain standalone fragment objects rather than a backend-specific
    circuit type; an adapter can serialize each :class:`FragmentExperiment`
    to OpenQASM, a vendor SDK, or another executor.
    """

    compiled: GeneratedWireCuttingExperiments
    observables: tuple[dict[int, str], ...] | None

    @property
    def subcircuits(self):
        """Independent fragments in deterministic label order."""
        return self.compiled.fragments

    @property
    def sampling_overhead(self) -> float:
        """Exact QPD overhead of this marked wire-cut problem."""
        return self.compiled.sampling_overhead


@dataclass(frozen=True)
class CuttingExperiment:
    """One executable local experiment for one QPD term and observable."""

    term_index: int
    observable_index: int
    fragment_label: int
    fragment_experiment: FragmentExperiment
    observable: Mapping[int, str]


@dataclass(frozen=True)
class CuttingExperimentBatch:
    """All concrete fragment experiments and their QPD coefficients."""

    problem: WireCuttingProblem
    observables: tuple[dict[int, str], ...]
    terms: tuple[QPDTerm, ...]
    experiments: tuple[CuttingExperiment, ...]

    @property
    def coefficients(self) -> tuple[float, ...]:
        """One quasiprobability coefficient for every joint QPD term."""
        return tuple(term.coefficient for term in self.terms)


@dataclass(frozen=True)
class CuttingExperimentResults:
    """Local expectation values in exactly the batch's experiment order."""

    batch: CuttingExperimentBatch
    values: tuple[float, ...]


@dataclass(frozen=True)
class Reconstruction:
    """Global expectation values reconstructed from independent fragments."""

    expectations: tuple[float, ...]
    sampling_overhead: float
    term_count: int


ExperimentEvaluator = Callable[[FragmentExperiment, Mapping[int, str]], float]


def find_cuts(
    circuit: Circuit, max_subcircuit_qubits: int, **kwargs
) -> CutPlan:
    """Automatically find a pure wire-cut plan for a width constraint.

    This is the public wire-only counterpart to Qiskit's cut finder.  It never
    replaces or decomposes a gate.
    """
    return find_wire_cuts(circuit, max_subcircuit_qubits, **kwargs)


def find_width_limited_wire_cuts(
    circuit: Circuit,
    max_subcircuit_qubits: int,
    *,
    max_search_states: int | None = None,
) -> CutPlan:
    """Find a globally minimum pure-LO wire-cut plan for two-qubit circuits.

    By default this runs the complete Dijkstra search and proves the minimum
    number of wire cuts.  Set ``max_search_states`` only to bound the search;
    a complete plan returned after that bound is marked non-optimal, and the
    function raises if the bound is reached before a plan is found.
    """
    return _find_width_limited_wire_cuts(
        circuit, max_subcircuit_qubits, max_search_states=max_search_states
    )


def cut_wires(
    circuit: Circuit, plan: CutPlan | Sequence[CutLocation] | None = None
) -> Circuit:
    """Return a marked wire-cut circuit.

    With ``plan``, insert the plan's markers into an unmarked circuit.  Without
    a plan, validate and return a copy of a circuit where the user has already
    called :meth:`Circuit.cut_wire`.  Unlike Qiskit's transformation, no hidden
    Qiskit instruction is introduced; QPD expansion happens in
    :func:`generate_cutting_experiments`.
    """
    if plan is not None:
        return apply_wire_cuts(circuit, plan)
    if not any(
        isinstance(instruction, WireCut)
        for instruction in circuit.instructions
    ):
        raise ValueError(
            "Provide a cut plan or mark at least one wire with "
            "circuit.cut_wire()."
        )
    copy = Circuit(circuit.num_qubits)
    copy.instructions.extend(circuit.instructions)
    return copy


def partition_problem(
    circuit: Circuit,
    observables: Iterable[PauliWord] | None = None,
    *,
    max_qpd_terms: int = 65_536,
    num_samples: int | None = None,
    seed: int | None = None,
) -> WireCuttingProblem:
    """Partition a marked wire-cut circuit into backend-neutral fragments.

    The input can contain zero or more ``WireCut`` markers.  Markers are
    inserted manually or via ``cut_wires(circuit, find_cuts(...))``; an uncut
    circuit simply produces one fragment and one unit-coefficient term.  The
    input may use arbitrary static unitary matrices through
    :meth:`Circuit.unitary`; dynamic control flow, reset, and classical bits
    are intentionally outside this lightweight circuit model.
    """
    compiled = _compile_wire_cutting_experiments(
        circuit,
        max_qpd_terms=max_qpd_terms,
        num_samples=num_samples,
        seed=seed,
    )
    normalized = (
        None
        if observables is None
        else _normalize_observables(observables, circuit.num_qubits)
    )
    return WireCuttingProblem(compiled, normalized)


def generate_cutting_experiments(
    problem: WireCuttingProblem,
    observables: Iterable[PauliWord] | None = None,
) -> CuttingExperimentBatch:
    """Generate local experiments per term, observable, and fragment.

    The experiment's ``fragment_experiment`` includes the QPD preparation and
    terminal QPD measurements.  Its ``observable`` is expressed with local
    fragment-qubit indices.  This is the object a backend adapter executes.
    """
    normalized = (
        problem.observables
        if observables is None
        else _normalize_observables(
            observables, len(problem.compiled.output_wires)
        )
    )
    if normalized is None:
        raise ValueError(
            "Provide observables to partition_problem or "
            "generate_cutting_experiments."
        )
    by_wire = _fragment_by_wire(problem.compiled)
    experiments: list[CuttingExperiment] = []
    for term_index, term in enumerate(problem.compiled.terms):
        for observable_index, observable in enumerate(normalized):
            output_observable = {
                problem.compiled.output_wires[logical_qubit]: pauli
                for logical_qubit, pauli in observable.items()
            }
            for fragment_experiment in problem.compiled.experiments_for_term(
                term
            ):
                local_observable = {
                    by_wire[wire][1]: pauli
                    for wire, pauli in output_observable.items()
                    if by_wire[wire][0] == fragment_experiment.fragment.label
                }
                experiments.append(
                    CuttingExperiment(
                        term_index,
                        observable_index,
                        fragment_experiment.fragment.label,
                        fragment_experiment,
                        local_observable,
                    )
                )
    return CuttingExperimentBatch(
        problem, normalized, problem.compiled.terms, tuple(experiments)
    )


def execute_experiments(
    batch: CuttingExperimentBatch, evaluator: ExperimentEvaluator | None = None
) -> CuttingExperimentResults:
    """Evaluate each local experiment with the supplied backend adapter.

    Omit ``evaluator`` to use the exact NumPy reference evaluator.  A hardware
    evaluator must return the local Pauli expectation multiplied by the parity
    of all QPD terminal measurements in ``FragmentExperiment``.
    """
    evaluator = evaluate_exact_fragment if evaluator is None else evaluator
    return CuttingExperimentResults(
        batch,
        tuple(
            float(
                evaluator(
                    experiment.fragment_experiment, experiment.observable
                )
            )
            for experiment in batch.experiments
        ),
    )


def reconstruct_expectation_values(
    results: CuttingExperimentResults,
) -> Reconstruction:
    """Reconstruct requested global Pauli-basis expectation values."""
    if len(results.values) != len(results.batch.experiments):
        raise ValueError(
            "Result count does not match the generated experiment batch."
        )
    local_values = {
        (
            experiment.term_index,
            experiment.observable_index,
            experiment.fragment_label,
        ): value
        for experiment, value in zip(
            results.batch.experiments, results.values, strict=True
        )
    }
    expected_count = (
        len(results.batch.terms)
        * len(results.batch.observables)
        * len(results.batch.problem.compiled.fragments)
    )
    if len(local_values) != expected_count:
        raise ValueError(
            "Experiment batch contains duplicate or missing "
            "term/observable/fragment entries."
        )
    values: list[float] = []
    for observable_index in range(len(results.batch.observables)):
        total = 0.0
        for term_index, term in enumerate(results.batch.terms):
            product_value = 1.0
            for fragment in results.batch.problem.compiled.fragments:
                product_value *= local_values[
                    (term_index, observable_index, fragment.label)
                ]
            total += term.coefficient * product_value
        values.append(total)
    return Reconstruction(
        tuple(values),
        results.batch.problem.sampling_overhead,
        len(results.batch.terms),
    )


def evaluate_and_reconstruct(
    problem: WireCuttingProblem,
    observables: Iterable[PauliWord] | None = None,
    *,
    evaluator: ExperimentEvaluator | None = None,
) -> Reconstruction:
    """Convenience wrapper for generate -> execute -> reconstruct."""
    batch = generate_cutting_experiments(problem, observables)
    return reconstruct_expectation_values(
        execute_experiments(batch, evaluator)
    )


def restrict_to_causal_cone(
    circuit: Circuit, observables: Iterable[PauliWord]
) -> Circuit:
    """Remove gates unrelated to requested values before cutting."""
    return restrict_to_observable_causal_cone(circuit, observables)


def generate_tensor_network_experiments(
    cut_circuit: Circuit, observables: Iterable[PauliWord]
) -> LocalTensorExperimentBatch:
    """Generate local QPD responses instead of global ``8**cuts`` terms.

    This is the recommended exact path when there are several cuts.  The
    supplied circuit must already contain the desired wire-cut markers.
    """
    return _generate_local_tensor_experiments(cut_circuit, observables)


def execute_tensor_network_experiments(
    batch: LocalTensorExperimentBatch,
    evaluator: ExperimentEvaluator | None = None,
) -> LocalTensorExperimentResults:
    """Execute local tensor-network response experiments."""
    return execute_local_tensor_experiments(batch, evaluator)


def reconstruct_tensor_network(
    results: LocalTensorExperimentResults,
) -> Reconstruction:
    """Contract local responses into global expectation values."""
    result = contract_local_tensor_results(results)
    return Reconstruction(
        result.expectations, result.sampling_overhead, result.term_count
    )


def evaluate_and_reconstruct_tensor_network(
    cut_circuit: Circuit,
    observables: Iterable[PauliWord],
    *,
    evaluator: ExperimentEvaluator | None = None,
) -> Reconstruction:
    """Convenience wrapper for the optimized exact reconstruction path."""
    batch = generate_tensor_network_experiments(cut_circuit, observables)
    return reconstruct_tensor_network(
        execute_tensor_network_experiments(batch, evaluator)
    )


def _normalize_observables(
    observables: Iterable[PauliWord], num_qubits: int
) -> tuple[dict[int, str], ...]:
    normalized: list[dict[int, str]] = []
    for observable in observables:
        term: dict[int, str] = {}
        for qubit, pauli in observable.items():
            if qubit < 0 or qubit >= num_qubits or pauli not in _PAULIS:
                raise ValueError(
                    f"Invalid Pauli term {pauli!r} on qubit {qubit}."
                )
            if pauli != "I":
                term[qubit] = pauli
        normalized.append(term)
    if not normalized:
        raise ValueError("At least one observable is required.")
    return tuple(normalized)


def _fragment_by_wire(
    compiled: GeneratedWireCuttingExperiments,
) -> dict[int, tuple[int, int]]:
    return {
        wire: (fragment.label, local_qubit)
        for fragment in compiled.fragments
        for local_qubit, wire in enumerate(fragment.physical_wires)
    }
