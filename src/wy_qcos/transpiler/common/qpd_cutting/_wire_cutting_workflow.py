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

"""Generic, Qiskit-free workflow for *wire* cutting only.

The public workflow is:

``find_wire_cuts`` -> ``apply_wire_cuts`` ->
``generate_wire_cutting_experiments`` -> ``reconstruct_expectation_values``.

The circuit is represented by :class:`.Circuit`; therefore no Qiskit circuit,
primitive, result type, or backend is required.  The automatic planner only
inserts cuts immediately before a multi-qubit operation.  It never cuts a
gate, and it works with any unitary arity supported by ``Circuit``.
"""

from __future__ import annotations

import heapq
from collections import Counter
from dataclasses import dataclass
from itertools import combinations, count, product
from collections.abc import Callable, Iterable, Mapping, Sequence

import numpy as np

from ._wire_cutting_core import (
    Circuit,
    Operation,
    PauliWord,
    WireCut,
    _PAULIS,
    _apply_unitary,
)


ComplexArray = np.ndarray


def _finite_or_infinite_power(base: float, exponent: int) -> float:
    """Return a non-negative floating power, saturating at infinity.

    Reporting a QPD overhead must not prevent a sampled large-circuit run
    from returning its hardware result merely because the *theoretical*
    variance bound exceeds IEEE-754's finite range.
    """
    limit = np.log(np.finfo(float).max)
    if exponent * np.log(base) > limit:
        return float("inf")
    return float(base**exponent)


@dataclass(frozen=True, order=True)
class CutLocation:
    """Cut the input wire just before a circuit instruction.

    ``instruction_index`` is an index in ``circuit.instructions`` and ``qubit``
    identifies one input of that operation.  Only multi-qubit operations are
    valid locations.
    """

    instruction_index: int
    qubit: int


@dataclass(frozen=True)
class CutPlan:
    """A wire-only partitioning plan returned by :func:`find_wire_cuts`."""

    locations: tuple[CutLocation, ...]
    subcircuit_widths: tuple[int, ...]
    optimal: bool
    strategy: str
    cut_graph_treewidth: int = 0

    @property
    def sampling_overhead(self) -> float:
        """The QPD sampling overhead, ``16 ** number_of_wire_cuts``."""
        return _finite_or_infinite_power(16.0, len(self.locations))


@dataclass(frozen=True)
class Fragment:
    """An independently executable partition, using local qubit indices."""

    label: int
    num_qubits: int
    operations: tuple[Operation, ...]
    physical_wires: tuple[int, ...]


@dataclass(frozen=True)
class QPDTerm:
    """One joint quasiprobability term across every wire cut."""

    coefficient: float
    source_measurements: tuple[str | None, ...]
    destination_states: tuple[ComplexArray, ...]


@dataclass(frozen=True)
class FragmentExperiment:
    """A fragment with preparations and terminal QPD measurements."""

    fragment: Fragment
    preparations: Mapping[int, ComplexArray]
    terminal_measurements: Mapping[int, str]


@dataclass(frozen=True)
class GeneratedWireCuttingExperiments:
    """Fragment/QPD data that an exact or external evaluator can execute."""

    fragments: tuple[Fragment, ...]
    terms: tuple[QPDTerm, ...]
    output_wires: Mapping[int, int]
    cut_sources: tuple[int, ...]
    cut_destinations: tuple[int, ...]

    @property
    def sampling_overhead(self) -> float:
        """Total quasiprobability sampling overhead."""
        total_weight = sum(abs(term.coefficient) for term in self.terms)
        if not np.isfinite(total_weight) or total_weight > np.sqrt(
            np.finfo(float).max
        ):
            return float("inf")
        return float(total_weight**2)

    def experiments_for_term(
        self, term: QPDTerm
    ) -> tuple[FragmentExperiment, ...]:
        """Materialize independently executable experiments for a QPD term."""
        by_wire = _fragment_by_wire(self.fragments)
        preparations: list[dict[int, ComplexArray]] = [
            dict() for _ in self.fragments
        ]
        measurements: list[dict[int, str]] = [dict() for _ in self.fragments]
        labels = {
            fragment.label: position
            for position, fragment in enumerate(self.fragments)
        }
        for source, destination, axis, state in zip(
            self.cut_sources,
            self.cut_destinations,
            term.source_measurements,
            term.destination_states,
            strict=True,
        ):
            source_fragment, source_local = by_wire[source]
            dest_fragment, dest_local = by_wire[destination]
            preparations[labels[dest_fragment.label]][dest_local] = state
            if axis is not None:
                measurements[labels[source_fragment.label]][source_local] = (
                    axis
                )
        return tuple(
            FragmentExperiment(
                fragment, preparations[index], measurements[index]
            )
            for index, fragment in enumerate(self.fragments)
        )


@dataclass(frozen=True)
class WireCuttingResult:
    """Expectation values reconstructed from evaluated wire-cut experiments."""

    expectations: tuple[float, ...]
    term_count: int
    sampling_overhead: float


@dataclass(frozen=True)
class AutoCutResult:
    """Result of the combined wire-cutting workflow."""

    plan: CutPlan
    cut_circuit: Circuit
    reconstruction: WireCuttingResult


@dataclass(frozen=True)
class LocalTensorExperiment:
    """One reusable local response in the wire-cut tensor network.

    ``cut_ids`` identifies the QPD indices on which this response depends;
    ``setting`` contains one of the eight wire-QPD maps for each such index.
    Unlike :class:`FragmentExperiment`, it is *not* tied to a full global
    QPD term, which allows results to be reused during contraction.
    """

    observable_index: int
    fragment_label: int
    cut_ids: tuple[int, ...]
    setting: tuple[int, ...]
    fragment_experiment: FragmentExperiment
    observable: Mapping[int, str]


@dataclass(frozen=True)
class LocalTensorExperimentBatch:
    """All local responses required for exact tensor-network reconstruction."""

    fragments: tuple[Fragment, ...]
    output_wires: Mapping[int, int]
    cut_sources: tuple[int, ...]
    cut_destinations: tuple[int, ...]
    observables: tuple[dict[int, str], ...]
    experiments: tuple[LocalTensorExperiment, ...]
    contraction_order: tuple[int, ...]
    treewidth: int

    @property
    def number_of_cuts(self) -> int:
        """Number of wire-QPD indices in the tensor network."""
        return len(self.cut_sources)

    @property
    def exact_term_count(self) -> int:
        """Conceptual global QPD terms, which are never materialized here."""
        return 8**self.number_of_cuts

    @property
    def sampling_overhead(self) -> float:
        """The conventional wire-QPD sampling overhead, ``16**cuts``."""
        return _finite_or_infinite_power(16.0, self.number_of_cuts)


@dataclass(frozen=True)
class LocalTensorExperimentResults:
    """Local response values in :class:`LocalTensorExperimentBatch` order."""

    batch: LocalTensorExperimentBatch
    values: tuple[float, ...]


@dataclass(frozen=True)
class ShotAllocation:
    """Integer shot allocation for weighted QPD terms."""

    shots: tuple[int, ...]
    total_shots: int


FragmentEvaluator = Callable[[FragmentExperiment, Mapping[int, str]], float]

_ZERO = np.array([1, 0], dtype=complex)
_ONE = np.array([0, 1], dtype=complex)
_PLUS = np.array([1, 1], dtype=complex) / np.sqrt(2)
_MINUS = np.array([1, -1], dtype=complex) / np.sqrt(2)
_I_PLUS = np.array([1, 1j], dtype=complex) / np.sqrt(2)
_I_MINUS = np.array([1, -1j], dtype=complex) / np.sqrt(2)

_ONE_CUT_TERMS = (
    (None, _ZERO, 0.5),
    (None, _ONE, 0.5),
    ("X", _PLUS, 0.5),
    ("X", _MINUS, -0.5),
    ("Y", _I_PLUS, 0.5),
    ("Y", _I_MINUS, -0.5),
    ("Z", _ZERO, 0.5),
    ("Z", _ONE, -0.5),
)


def find_wire_cuts(
    circuit: Circuit,
    max_subcircuit_qubits: int,
    *,
    max_cuts: int | None = None,
    exhaustive_candidate_limit: int = 18,
    max_search_states: int = 50_000,
) -> CutPlan:
    """Automatically find a pure-wire-cut plan meeting a width constraint.

    Candidate cuts are each input of a multi-qubit operation.  When there are
    at most ``exhaustive_candidate_limit`` candidates, combinations are
    searched
    in increasing cut count, proving optimality.  Larger circuits use a
    deterministic greedy fallback; ``CutPlan.optimal`` reports which path was
    used.  ``max_cuts`` controls the allowed QPD cost explicitly.
    """
    if max_subcircuit_qubits < 1:
        raise ValueError("max_subcircuit_qubits must be positive.")
    _require_uncut(circuit)
    candidates = _candidate_locations(circuit)
    no_cut_widths = _component_widths(circuit, ())
    if max(no_cut_widths) <= max_subcircuit_qubits:
        return CutPlan((), no_cut_widths, True, "none", 0)
    if not candidates:
        raise ValueError(
            "No multi-qubit operation is available as a wire-cut location."
        )
    max_cuts = len(candidates) if max_cuts is None else max_cuts
    if max_cuts < 1:
        raise ValueError("max_cuts must be positive when cuts are needed.")

    if len(candidates) <= exhaustive_candidate_limit:
        visited = 0
        for number_of_cuts in range(1, min(max_cuts, len(candidates)) + 1):
            best: (
                tuple[tuple[int, int, int], tuple[CutLocation, ...]] | None
            ) = None
            for exhaustive_selected in combinations(
                candidates, number_of_cuts
            ):
                visited += 1
                if visited > max_search_states:
                    break
                widths = _component_widths(circuit, exhaustive_selected)
                if max(widths) <= max_subcircuit_qubits:
                    # Plans with the same cut count and width can have very
                    # different reconstruction cost.  Prefer a lower-treewidth
                    # fragment graph so the local-response tensor network can
                    # be contracted efficiently.
                    exhaustive_score = (
                        max(widths),
                        _cut_graph_treewidth(circuit, exhaustive_selected),
                        -min(widths),
                    )
                    if best is None or exhaustive_score < best[0]:
                        best = (exhaustive_score, exhaustive_selected)
            if best is not None:
                locations = best[1]
                return CutPlan(
                    locations,
                    _component_widths(circuit, locations),
                    True,
                    "exhaustive-treewidth",
                    _cut_graph_treewidth(circuit, locations),
                )
            if visited > max_search_states:
                break

    selected: tuple[CutLocation, ...] = ()
    remaining = set(candidates)
    for _ in range(max_cuts):
        ranked: list[
            tuple[tuple[int, int, int, tuple[CutLocation, ...]], CutLocation]
        ] = []
        for candidate in remaining:
            proposal = tuple(sorted((*selected, candidate)))
            widths = _component_widths(circuit, proposal)
            # First minimize violations, then the largest fragment, then use a
            # stable lexicographic tie-breaker.
            greedy_score = (
                sum(max(0, width - max_subcircuit_qubits) for width in widths),
                max(widths),
                _cut_graph_treewidth(circuit, proposal),
                proposal,
            )
            ranked.append((greedy_score, candidate))
        if not ranked:
            break
        _, chosen = min(ranked, key=lambda item: item[0])
        selected = tuple(sorted((*selected, chosen)))
        remaining.remove(chosen)
        widths = _component_widths(circuit, selected)
        if max(widths) <= max_subcircuit_qubits:
            return CutPlan(
                selected,
                widths,
                False,
                "greedy-treewidth",
                _cut_graph_treewidth(circuit, selected),
            )
    raise ValueError(
        "No wire-only plan meeting the requested width was found within "
        "max_cuts. "
        "Increase max_cuts or use a wider subcircuit constraint."
    )


def find_width_limited_wire_cuts(
    circuit: Circuit,
    max_subcircuit_qubits: int,
    *,
    max_search_states: int | None = None,
) -> CutPlan:
    """Find a minimum-cut pure-LO wire-cut plan for two-qubit circuits.

    This is a native-model implementation of the pure-wire subset of
    Qiskit's ``LOCutsOptimizer``.  At every two-qubit gate it performs a
    Dijkstra best-first search over ``apply``, ``cut left``, ``cut right``,
    and ``cut both``.  Search states explicitly retain the current wire map,
    a union-find partition with fragment widths, and upstream-compatible
    ``no-merge`` constraints.  The latter prevent the two sides of a prior
    cut from being joined together by a later gate.

    Each LO wire cut multiplies QPD gamma by four.  Consequently minimizing
    gamma is exactly the same as minimizing the number of cuts (and the
    conventional sampling overhead ``16 ** cuts``).  With the default
    ``max_search_states=None``, the returned plan is globally minimum under
    this model and reports ``optimal=True``.  A positive state limit can stop
    the search before optimality is proved; a complete plan found before the
    limit is marked ``optimal=False``, while a limit reached before any plan
    is found raises :class:`RuntimeError`.

    The planner supports arbitrary one-qubit operations and two-qubit
    unitaries.  Use :func:`find_cuts` for the existing general-arity planner.
    """
    if max_subcircuit_qubits < 2:
        raise ValueError("max_subcircuit_qubits must be at least 2.")
    if max_search_states is not None and max_search_states < 1:
        raise ValueError("max_search_states must be positive.")
    _require_uncut(circuit)
    if any(
        isinstance(instruction, Operation) and len(instruction.qubits) > 2
        for instruction in circuit.instructions
    ):
        raise ValueError(
            "find_width_limited_wire_cuts supports only one- and "
            "two-qubit operations."
        )

    # A state mirrors upstream ``DisjointSubcircuitsState``.  ``parents`` and
    # ``widths`` form a union-find over wire segments; ``wiremap`` maps each
    # logical qubit to its currently live segment.  ``no_merge`` contains
    # pairs of segment IDs that must remain in different components.
    @dataclass(frozen=True)
    class State:
        wiremap: tuple[int, ...]
        parents: tuple[int, ...]
        widths: tuple[int, ...]
        no_merge: tuple[tuple[int, int], ...]
        gate_index: int

    two_qubit_gates = tuple(
        (instruction_index, instruction)
        for instruction_index, instruction in enumerate(circuit.instructions)
        if isinstance(instruction, Operation) and len(instruction.qubits) == 2
    )

    def find(state: State, wire: int) -> int:
        while wire != state.parents[wire]:
            wire = state.parents[wire]
        return wire

    def can_merge(state: State, left_root: int, right_root: int) -> bool:
        if left_root == right_root:
            return True
        if (
            state.widths[left_root] + state.widths[right_root]
            > max_subcircuit_qubits
        ):
            return False
        return not any(
            {find(state, first), find(state, second)}
            == {left_root, right_root}
            for first, second in state.no_merge
        )

    def merge(state: State, left_root: int, right_root: int) -> State:
        if left_root == right_root:
            return state
        # Match upstream's deterministic union: the lower wire ID is root.
        root, child = sorted((left_root, right_root))
        parents = list(state.parents)
        widths = list(state.widths)
        parents[child] = root
        widths[root] += widths[child]
        return State(
            state.wiremap,
            tuple(parents),
            tuple(widths),
            state.no_merge,
            state.gate_index,
        )

    def with_cut_wire(state: State, qubit: int) -> tuple[State, int]:
        new_wire = len(state.parents)
        return (
            State(
                state.wiremap[:qubit]
                + (new_wire,)
                + state.wiremap[qubit + 1 :],
                state.parents + (new_wire,),
                state.widths + (1,),
                state.no_merge,
                state.gate_index,
            ),
            new_wire,
        )

    def add_no_merge(state: State, first: int, second: int) -> State:
        if find(state, first) == find(state, second):
            raise AssertionError(
                "A no-merge constraint cannot join one component."
            )
        pair = (min(first, second), max(first, second))
        constraints = tuple(sorted(set((*state.no_merge, pair))))
        return State(
            state.wiremap,
            state.parents,
            state.widths,
            constraints,
            state.gate_index,
        )

    def advance(state: State) -> State:
        return State(
            state.wiremap,
            state.parents,
            state.widths,
            state.no_merge,
            state.gate_index + 1,
        )

    def successors(
        state: State,
    ) -> tuple[tuple[State, tuple[CutLocation, ...]], ...]:
        instruction_index, instruction = two_qubit_gates[state.gate_index]
        left, right = instruction.qubits
        left_root = find(state, state.wiremap[left])
        right_root = find(state, state.wiremap[right])
        outcomes: list[tuple[State, tuple[CutLocation, ...]]] = []

        # Apply the gate without cutting.
        if can_merge(state, left_root, right_root):
            outcomes.append((advance(merge(state, left_root, right_root)), ()))

        # These transitions are a direct native representation of upstream
        # ActionCutLeftWire and ActionCutRightWire.
        if (
            left_root != right_root
            and state.widths[right_root] + 1 <= max_subcircuit_qubits
        ):
            cut_state, new_wire = with_cut_wire(state, left)
            cut_state = merge(cut_state, new_wire, right_root)
            cut_state = add_no_merge(cut_state, left_root, right_root)
            outcomes.append((
                advance(cut_state),
                (CutLocation(instruction_index, left),),
            ))
        if (
            left_root != right_root
            and state.widths[left_root] + 1 <= max_subcircuit_qubits
        ):
            cut_state, new_wire = with_cut_wire(state, right)
            cut_state = merge(cut_state, left_root, new_wire)
            cut_state = add_no_merge(cut_state, left_root, right_root)
            outcomes.append((
                advance(cut_state),
                (CutLocation(instruction_index, right),),
            ))

        # ActionCutBothWires is also available when both inputs are already
        # in one component, exactly as in the upstream implementation.
        both_state, new_left = with_cut_wire(state, left)
        both_state, new_right = with_cut_wire(both_state, right)
        both_state = merge(both_state, new_left, new_right)
        both_state = add_no_merge(both_state, left_root, new_left)
        both_state = add_no_merge(both_state, right_root, new_right)
        outcomes.append((
            advance(both_state),
            (
                CutLocation(instruction_index, left),
                CutLocation(instruction_index, right),
            ),
        ))
        return tuple(outcomes)

    initial = State(
        tuple(range(circuit.num_qubits)),
        tuple(range(circuit.num_qubits)),
        (1,) * circuit.num_qubits,
        (),
        0,
    )
    queue: list[tuple[int, int, int, State, tuple[CutLocation, ...]]] = []
    sequence = count()
    heapq.heappush(queue, (0, 1, next(sequence), initial, ()))
    best_cost: dict[State, int] = {initial: 0}
    best_complete: tuple[int, State, tuple[CutLocation, ...]] | None = None
    expanded = 0
    limited = False

    while queue:
        cut_count, _, _, state, locations = heapq.heappop(queue)
        if best_cost.get(state) != cut_count:
            continue
        if state.gate_index == len(two_qubit_gates):
            best_complete = (cut_count, state, locations)
            break
        if max_search_states is not None and expanded >= max_search_states:
            limited = True
            break
        expanded += 1
        for next_state, new_locations in successors(state):
            next_cost = cut_count + len(new_locations)
            if next_cost >= best_cost.get(next_state, np.inf):
                continue
            best_cost[next_state] = next_cost
            next_locations = locations + new_locations
            if next_state.gate_index == len(two_qubit_gates) and (
                best_complete is None or next_cost < best_complete[0]
            ):
                # This gives a valid upper-bound plan if a caller explicitly
                # terminates the Dijkstra search with max_search_states.
                best_complete = (next_cost, next_state, next_locations)
            # The maximum component width is a deterministic secondary
            # tie-breaker only; the primary Dijkstra cost is cut count.
            max_width = max(
                next_state.widths[find(next_state, wire)]
                for wire in range(len(next_state.parents))
            )
            heapq.heappush(
                queue,
                (
                    next_cost,
                    max_width,
                    next(sequence),
                    next_state,
                    next_locations,
                ),
            )

    if best_complete is None:
        if limited:
            raise RuntimeError(
                "The wire-cut search reached max_search_states before "
                "finding a plan. Increase the limit or pass "
                "max_search_states=None for an exact search."
            )
        raise ValueError(
            "No wire-only plan meets the requested fragment-width limit."
        )

    _, _, locations = best_complete
    widths = _component_widths(circuit, locations)
    return CutPlan(
        locations,
        widths,
        not limited,
        "dijkstra-pure-lo-wire",
        _cut_graph_treewidth(circuit, locations),
    )


def apply_wire_cuts(
    circuit: Circuit, plan: CutPlan | Sequence[CutLocation]
) -> Circuit:
    """Insert a plan's ``WireCut`` markers into a circuit copy."""
    _require_uncut(circuit)
    locations = tuple(plan.locations if isinstance(plan, CutPlan) else plan)
    by_instruction: dict[int, set[int]] = {}
    for location in locations:
        instruction = _operation_at(circuit, location.instruction_index)
        if (
            location.qubit not in instruction.qubits
            or len(instruction.qubits) < 2
        ):
            raise ValueError(f"Invalid wire-cut location: {location}.")
        by_instruction.setdefault(location.instruction_index, set()).add(
            location.qubit
        )
    out = Circuit(circuit.num_qubits)
    for index in range(len(circuit.instructions)):
        for qubit in sorted(by_instruction.get(index, ())):
            out.cut_wire(qubit)
        out.instructions.append(_operation_at(circuit, index))
    return out


def generate_wire_cutting_experiments(
    cut_circuit: Circuit,
    *,
    max_qpd_terms: int = 65_536,
    num_samples: int | None = None,
    seed: int | None = None,
) -> GeneratedWireCuttingExperiments:
    """Compile marked wire cuts into fragments and QPD terms.

    With ``num_samples=None`` (the default), every exact QPD term is
    materialized.  ``max_qpd_terms`` prevents accidental expansion of the
    exponential ``8 ** number_of_cuts`` term set.  With a positive finite
    ``num_samples``, terms are importance-sampled uniformly from the wire QPD
    distribution and repeated samples are combined.  This is an unbiased,
    non-exact estimator whose generated-term count is at most ``num_samples``.
    """
    fragments, output_wires, cut_sources, cut_destinations = (
        _compile_marked_circuit(cut_circuit)
    )
    number_of_cuts = len(cut_sources)
    term_count = 8**number_of_cuts
    if num_samples is not None and num_samples < 1:
        raise ValueError("num_samples must be positive when provided.")
    if num_samples is None and term_count > max_qpd_terms:
        raise ValueError(
            f"{number_of_cuts} wire cuts require {term_count} exact QPD "
            "terms; "
            f"this exceeds max_qpd_terms={max_qpd_terms}."
        )
    terms: tuple[QPDTerm, ...]
    if not number_of_cuts:
        terms = (QPDTerm(1.0, (), ()),)
    elif num_samples is not None:
        rng = np.random.default_rng(seed)
        samples = rng.integers(0, 8, size=(num_samples, number_of_cuts))
        counts = Counter(
            tuple(int(value) for value in sample) for sample in samples
        )
        scale = float(4**number_of_cuts / num_samples)
        terms = tuple(
            _qpd_term_from_map_ids(map_ids, coefficient=scale * count)
            for map_ids, count in sorted(counts.items())
        )
    else:
        terms = tuple(
            _qpd_term_from_map_ids(map_ids)
            for map_ids in product(range(8), repeat=number_of_cuts)
        )
    return GeneratedWireCuttingExperiments(
        fragments, terms, output_wires, cut_sources, cut_destinations
    )


def _qpd_term_from_map_ids(
    map_ids: Sequence[int], coefficient: float | None = None
) -> QPDTerm:
    """Construct a joint QPD term, optionally with a Monte-Carlo scale."""
    entries = tuple(_ONE_CUT_TERMS[map_id] for map_id in map_ids)
    sign = float(np.prod([entry[2] / abs(entry[2]) for entry in entries]))
    exact_coefficient = float(np.prod([entry[2] for entry in entries]))
    return QPDTerm(
        coefficient=exact_coefficient
        if coefficient is None
        else coefficient * sign,
        source_measurements=tuple(entry[0] for entry in entries),
        destination_states=tuple(entry[1] for entry in entries),
    )


def reconstruct_expectation_values(
    experiments: GeneratedWireCuttingExperiments,
    observables: Iterable[PauliWord],
    *,
    evaluator: FragmentEvaluator | None = None,
) -> WireCuttingResult:
    """Evaluate subcircuits and reconstruct global Pauli expectation values.

    The default evaluator is exact NumPy state-vector/density-matrix
    evaluation.
    An external evaluator receives a :class:`FragmentExperiment` and its local
    Pauli word, and must return the correlated expectation value.  When a
    fragment includes ``terminal_measurements``, the returned value must
    include
    the product of those measurement outcomes (the QPD sign).
    """
    evaluator = evaluate_exact_fragment if evaluator is None else evaluator
    normalized = tuple(
        _normalize_observable(word, experiments.output_wires)
        for word in observables
    )
    values = np.zeros(len(normalized), dtype=float)
    by_wire = _fragment_by_wire(experiments.fragments)
    for term in experiments.terms:
        fragment_experiments = experiments.experiments_for_term(term)
        for observable_index, observable in enumerate(normalized):
            product_value = 1.0
            for fragment_experiment in fragment_experiments:
                local_word = {
                    by_wire[wire][1]: pauli
                    for wire, pauli in observable.items()
                    if by_wire[wire][0].label
                    == fragment_experiment.fragment.label
                }
                product_value *= evaluator(fragment_experiment, local_word)
            values[observable_index] += term.coefficient * product_value
    return WireCuttingResult(
        tuple(float(value) for value in values),
        len(experiments.terms),
        experiments.sampling_overhead,
    )


def auto_wire_cut_and_reconstruct(
    circuit: Circuit,
    observables: Iterable[PauliWord],
    max_subcircuit_qubits: int,
    *,
    evaluator: FragmentEvaluator | None = None,
    max_cuts: int | None = None,
    max_qpd_terms: int = 65_536,
) -> AutoCutResult:
    """Run the complete automatic wire-cutting workflow."""
    plan = find_wire_cuts(circuit, max_subcircuit_qubits, max_cuts=max_cuts)
    cut_circuit = apply_wire_cuts(circuit, plan)
    experiments = generate_wire_cutting_experiments(
        cut_circuit, max_qpd_terms=max_qpd_terms
    )
    return AutoCutResult(
        plan,
        cut_circuit,
        reconstruct_expectation_values(
            experiments, observables, evaluator=evaluator
        ),
    )


def evaluate_exact_fragment(
    experiment: FragmentExperiment, observable: Mapping[int, str]
) -> float:
    """Exact default fragment evaluator, including QPD measurement parity."""
    state = _initial_state(
        experiment.fragment.num_qubits, experiment.preparations
    )
    for operation in experiment.fragment.operations:
        state = _apply_unitary(
            state,
            operation.matrix,
            operation.qubits,
            experiment.fragment.num_qubits,
        )
    density = np.outer(state, state.conj())
    for qubit, axis in experiment.terminal_measurements.items():
        pauli = _full_pauli(experiment.fragment.num_qubits, {qubit: axis})
        density = 0.5 * (pauli @ density + density @ pauli)
    return float(
        np.trace(
            _full_pauli(experiment.fragment.num_qubits, observable) @ density
        ).real
    )


def restrict_to_observable_causal_cone(
    circuit: Circuit, observables: Iterable[PauliWord]
) -> Circuit:
    """Drop operations and cut markers outside the backward Pauli causal cone.

    This transformation is exact for the requested product-Pauli expectation
    values.  It is useful before planning: gates outside the cone cannot
    influence the requested result, so preserving them would only increase
    fragment widths and the candidate-cut search space.  The returned circuit
    keeps the original logical wire numbering; unused wires are harmless.
    """
    active: set[int] = set()
    for observable in observables:
        normalized = _normalize_observable(
            observable, dict(enumerate(range(circuit.num_qubits)))
        )
        active.update(normalized)
    retained: list[Operation | WireCut] = []
    for instruction in reversed(circuit.instructions):
        if isinstance(instruction, WireCut):
            if instruction.qubit in active:
                retained.append(instruction)
            continue
        if active.intersection(instruction.qubits):
            retained.append(instruction)
            active.update(instruction.qubits)
    result = Circuit(circuit.num_qubits)
    result.instructions.extend(reversed(retained))
    return result


def generate_local_tensor_experiments(
    cut_circuit: Circuit, observables: Iterable[PauliWord]
) -> LocalTensorExperimentBatch:
    """Generate reusable local responses for exact tensor-network cutting.

    No global ``8**c`` QPD list is built.  A fragment incident on ``d`` cuts
    contributes only ``8**d`` local configurations per observable.  The
    resulting response tensors are contracted by
    :func:`contract_local_tensor_results`.
    """
    fragments, output_wires, cut_sources, cut_destinations = (
        _compile_marked_circuit(cut_circuit)
    )
    normalized = tuple(
        _normalize_observable(word, output_wires) for word in observables
    )
    if not normalized:
        raise ValueError("At least one observable is required.")
    by_wire = _fragment_by_wire(fragments)
    incident: dict[int, set[int]] = {
        fragment.label: set() for fragment in fragments
    }
    for cut_id, (source, destination) in enumerate(
        zip(cut_sources, cut_destinations, strict=True)
    ):
        incident[by_wire[source][0].label].add(cut_id)
        incident[by_wire[destination][0].label].add(cut_id)

    experiments: list[LocalTensorExperiment] = []
    for observable_index, observable in enumerate(normalized):
        for fragment in fragments:
            cut_ids = tuple(sorted(incident[fragment.label]))
            local_observable = {
                by_wire[wire][1]: pauli
                for wire, pauli in observable.items()
                if by_wire[wire][0].label == fragment.label
            }
            for setting in product(range(8), repeat=len(cut_ids)):
                fragment_experiment = _fragment_experiment_for_local_setting(
                    fragment,
                    cut_ids,
                    setting,
                    cut_sources,
                    cut_destinations,
                    by_wire,
                )
                experiments.append(
                    LocalTensorExperiment(
                        observable_index,
                        fragment.label,
                        cut_ids,
                        tuple(setting),
                        fragment_experiment,
                        local_observable,
                    )
                )
    order, treewidth = _min_fill_order(
        tuple(tuple(sorted(values)) for values in incident.values()),
        len(cut_sources),
    )
    return LocalTensorExperimentBatch(
        fragments,
        output_wires,
        cut_sources,
        cut_destinations,
        normalized,
        tuple(experiments),
        order,
        treewidth,
    )


def execute_local_tensor_experiments(
    batch: LocalTensorExperimentBatch,
    evaluator: FragmentEvaluator | None = None,
) -> LocalTensorExperimentResults:
    """Evaluate local response tensors with a selected evaluator."""
    evaluator = evaluate_exact_fragment if evaluator is None else evaluator
    return LocalTensorExperimentResults(
        batch,
        tuple(
            float(evaluator(item.fragment_experiment, item.observable))
            for item in batch.experiments
        ),
    )


def contract_local_tensor_results(
    results: LocalTensorExperimentResults,
) -> WireCuttingResult:
    """Contract cached responses without enumerating global QPD terms."""
    batch = results.batch
    if len(results.values) != len(batch.experiments):
        raise ValueError(
            "Result count does not match the local tensor experiment batch."
        )
    response_lookup = {
        (item.observable_index, item.fragment_label, item.setting): value
        for item, value in zip(batch.experiments, results.values, strict=True)
    }
    if len(response_lookup) != len(batch.experiments):
        raise ValueError(
            "Local tensor experiment batch contains duplicate response "
            "coordinates."
        )
    items_by_response_tensor: dict[
        tuple[int, int], list[LocalTensorExperiment]
    ] = {}
    for item in batch.experiments:
        items_by_response_tensor.setdefault(
            (item.observable_index, item.fragment_label), []
        ).append(item)

    expectations: list[float] = []
    for observable_index in range(len(batch.observables)):
        factors: list[tuple[tuple[int, ...], ComplexArray]] = []
        for fragment in batch.fragments:
            fragment_items = items_by_response_tensor[
                (observable_index, fragment.label)
            ]
            cut_ids = fragment_items[0].cut_ids
            tensor = np.empty((8,) * len(cut_ids), dtype=float)
            for item in fragment_items:
                tensor[item.setting] = response_lookup[
                    (observable_index, fragment.label, item.setting)
                ]
            factors.append((cut_ids, tensor))
        for cut_id in range(batch.number_of_cuts):
            coefficients = np.asarray(
                [entry[2] for entry in _ONE_CUT_TERMS], dtype=float
            )
            factors.append(((cut_id,), coefficients))
        expectations.append(
            float(_contract_factors(factors, batch.contraction_order))
        )
    return WireCuttingResult(
        tuple(expectations), batch.exact_term_count, batch.sampling_overhead
    )


def evaluate_and_contract_local_tensors(
    cut_circuit: Circuit,
    observables: Iterable[PauliWord],
    *,
    evaluator: FragmentEvaluator | None = None,
) -> WireCuttingResult:
    """Generate, evaluate, and contract local responses."""
    batch = generate_local_tensor_experiments(cut_circuit, observables)
    return contract_local_tensor_results(
        execute_local_tensor_experiments(batch, evaluator)
    )


def allocate_shots_by_variance(
    coefficients: Sequence[float],
    total_shots: int,
    *,
    variances: Sequence[float] | None = None,
    minimum_shots: int = 1,
) -> ShotAllocation:
    """Allocate shots proportionally to ``|coefficient| * sqrt(variance)``.

    This is the Neyman allocation used after a pilot run.  When variances are
    omitted, it reduces to importance allocation by coefficient magnitude.
    Zero-weight terms receive no shots.  The function is backend-neutral and
    returns a schedule that an adapter may apply to its QPU submissions.
    """
    if total_shots < 1 or minimum_shots < 0:
        raise ValueError(
            "total_shots must be positive and minimum_shots non-negative."
        )
    if variances is not None and len(variances) != len(coefficients):
        raise ValueError(
            "variances and coefficients must have the same length."
        )
    weights = np.abs(np.asarray(coefficients, dtype=float))
    if variances is not None:
        variance_values = np.asarray(variances, dtype=float)
        if np.any(variance_values < 0):
            raise ValueError("variances must be non-negative.")
        weights *= np.sqrt(variance_values)
    nonzero = np.flatnonzero(weights > 0)
    if not len(nonzero):
        raise ValueError("At least one coefficient must be non-zero.")
    required = minimum_shots * len(nonzero)
    if required > total_shots:
        raise ValueError(
            "total_shots is below the requested minimum allocation."
        )
    remaining = total_shots - required
    raw = weights / weights.sum() * remaining
    shots = np.zeros(len(coefficients), dtype=int)
    shots[nonzero] = minimum_shots + np.floor(raw[nonzero]).astype(int)
    remainder = total_shots - int(shots.sum())
    if remainder:
        fractional = raw - np.floor(raw)
        order = sorted(nonzero, key=lambda index: (-fractional[index], index))
        for index in order[:remainder]:
            shots[index] += 1
    return ShotAllocation(tuple(int(value) for value in shots), total_shots)


def _candidate_locations(circuit: Circuit) -> tuple[CutLocation, ...]:
    return tuple(
        CutLocation(index, qubit)
        for index, instruction in enumerate(circuit.instructions)
        if isinstance(instruction, Operation) and len(instruction.qubits) > 1
        for qubit in instruction.qubits
    )


def _component_widths(
    circuit: Circuit, locations: Sequence[CutLocation]
) -> tuple[int, ...]:
    widths = tuple(
        fragment.num_qubits
        for fragment in _compile_marked_circuit(
            apply_wire_cuts(circuit, locations)
        )[0]
    )
    return tuple(sorted(widths, reverse=True))


def _compile_marked_circuit(
    circuit: Circuit,
) -> tuple[
    tuple[Fragment, ...], dict[int, int], tuple[int, ...], tuple[int, ...]
]:
    current_wire = list(range(circuit.num_qubits))
    next_wire = circuit.num_qubits
    transformed: list[Operation] = []
    cut_sources: list[int] = []
    cut_destinations: list[int] = []
    for instruction in circuit.instructions:
        if isinstance(instruction, WireCut):
            source = current_wire[instruction.qubit]
            destination = next_wire
            next_wire += 1
            current_wire[instruction.qubit] = destination
            cut_sources.append(source)
            cut_destinations.append(destination)
        else:
            transformed.append(
                Operation(
                    instruction.matrix,
                    tuple(current_wire[qubit] for qubit in instruction.qubits),
                )
            )
    adjacency = {wire: {wire} for wire in range(next_wire)}
    for operation in transformed:
        for left in operation.qubits:
            adjacency[left].update(operation.qubits)
    components = _components(adjacency)
    fragments: list[Fragment] = []
    for label, wires in enumerate(
        sorted(components, key=lambda item: min(item))
    ):
        ordered = tuple(sorted(wires))
        local = {wire: index for index, wire in enumerate(ordered)}
        operations = tuple(
            Operation(
                operation.matrix,
                tuple(local[qubit] for qubit in operation.qubits),
            )
            for operation in transformed
            if set(operation.qubits) <= wires
        )
        fragments.append(Fragment(label, len(ordered), operations, ordered))
    return (
        tuple(fragments),
        dict(enumerate(current_wire)),
        tuple(cut_sources),
        tuple(cut_destinations),
    )


def _components(adjacency: Mapping[int, set[int]]) -> list[set[int]]:
    undiscovered = set(adjacency)
    result: list[set[int]] = []
    while undiscovered:
        start = undiscovered.pop()
        component = {start}
        pending = [start]
        while pending:
            wire = pending.pop()
            for neighbour in adjacency[wire]:
                if neighbour not in component:
                    component.add(neighbour)
                    undiscovered.discard(neighbour)
                    pending.append(neighbour)
        result.append(component)
    return result


def _fragment_by_wire(
    fragments: Sequence[Fragment],
) -> dict[int, tuple[Fragment, int]]:
    return {
        wire: (fragment, local)
        for fragment in fragments
        for local, wire in enumerate(fragment.physical_wires)
    }


def _normalize_observable(
    observable: PauliWord, output_wires: Mapping[int, int]
) -> dict[int, str]:
    normalized: dict[int, str] = {}
    for logical_qubit, pauli in observable.items():
        if logical_qubit not in output_wires or pauli not in _PAULIS:
            raise ValueError(
                f"Invalid Pauli term {pauli!r} on qubit {logical_qubit}."
            )
        if pauli != "I":
            normalized[output_wires[logical_qubit]] = pauli
    return normalized


def _initial_state(
    num_qubits: int, preparations: Mapping[int, ComplexArray]
) -> ComplexArray:
    state = np.zeros(1 << num_qubits, dtype=complex)
    state[0] = 1.0
    for qubit, prepared_state in preparations.items():
        prepared_state = np.asarray(prepared_state, dtype=complex)
        if prepared_state.shape != (2,) or not np.isclose(
            np.vdot(prepared_state, prepared_state), 1.0
        ):
            raise ValueError(
                "Prepared states must be normalized one-qubit statevectors."
            )
        state = _apply_unitary(
            state, np.outer(prepared_state, _ZERO), (qubit,), num_qubits
        )
    return state


def _full_pauli(
    num_qubits: int, observable: Mapping[int, str]
) -> ComplexArray:
    operator = np.array([[1]], dtype=complex)
    for qubit in range(num_qubits - 1, -1, -1):
        operator = np.kron(operator, _PAULIS[observable.get(qubit, "I")])
    return operator


def _operation_at(circuit: Circuit, index: int) -> Operation:
    try:
        operation = circuit.instructions[index]
    except IndexError as error:
        raise ValueError(
            f"Instruction index {index} is outside the circuit."
        ) from error
    if not isinstance(operation, Operation):
        raise ValueError(f"Instruction {index} is not a unitary operation.")
    return operation


def _require_uncut(circuit: Circuit) -> None:
    if any(
        isinstance(instruction, WireCut)
        for instruction in circuit.instructions
    ):
        raise ValueError(
            "Automatic planning expects a circuit without pre-existing "
            "WireCut markers."
        )


def _fragment_experiment_for_local_setting(
    fragment: Fragment,
    cut_ids: Sequence[int],
    setting: Sequence[int],
    cut_sources: Sequence[int],
    cut_destinations: Sequence[int],
    by_wire: Mapping[int, tuple[Fragment, int]],
) -> FragmentExperiment:
    preparations: dict[int, ComplexArray] = {}
    measurements: dict[int, str] = {}
    for cut_id, map_id in zip(cut_ids, setting, strict=True):
        axis, state, _ = _ONE_CUT_TERMS[map_id]
        source_fragment, source_local = by_wire[cut_sources[cut_id]]
        destination_fragment, destination_local = by_wire[
            cut_destinations[cut_id]
        ]
        if source_fragment.label == fragment.label and axis is not None:
            measurements[source_local] = axis
        if destination_fragment.label == fragment.label:
            preparations[destination_local] = state
    return FragmentExperiment(fragment, preparations, measurements)


def _cut_graph_treewidth(
    circuit: Circuit, locations: Sequence[CutLocation]
) -> int:
    """Return a deterministic min-fill upper bound for a proposed cut graph."""
    fragments, _, sources, destinations = _compile_marked_circuit(
        apply_wire_cuts(circuit, locations)
    )
    by_wire = _fragment_by_wire(fragments)
    incident: dict[int, set[int]] = {
        fragment.label: set() for fragment in fragments
    }
    for cut_id, (source, destination) in enumerate(
        zip(sources, destinations, strict=True)
    ):
        incident[by_wire[source][0].label].add(cut_id)
        incident[by_wire[destination][0].label].add(cut_id)
    _, treewidth = _min_fill_order(
        tuple(tuple(values) for values in incident.values()), len(sources)
    )
    return treewidth


def _min_fill_order(
    factor_axes: Sequence[Sequence[int]], number_of_cuts: int
) -> tuple[tuple[int, ...], int]:
    """Compute a min-fill variable-elimination order and its induced width."""
    adjacency: dict[int, set[int]] = {
        cut_id: set() for cut_id in range(number_of_cuts)
    }
    for axes in factor_axes:
        for left in axes:
            adjacency[left].update(right for right in axes if right != left)
    remaining = set(adjacency)
    order: list[int] = []
    width = 0
    while remaining:

        def score(variable: int) -> tuple[int, int, int]:
            neighbours = adjacency[variable] & remaining
            missing = sum(
                right not in adjacency[left]
                for left, right in combinations(sorted(neighbours), 2)
            )
            return missing, len(neighbours), variable

        variable = min(remaining, key=score)
        neighbours = adjacency[variable] & remaining
        width = max(width, len(neighbours))
        for left, right in combinations(neighbours, 2):
            adjacency[left].add(right)
            adjacency[right].add(left)
        remaining.remove(variable)
        order.append(variable)
    return tuple(order), width


def _contract_factors(
    factors: Sequence[tuple[tuple[int, ...], ComplexArray]],
    order: Sequence[int],
) -> float:
    """Contract small labelled tensors by variable elimination.

    The implementation deliberately avoids an einsum-label limit and makes
    peak memory depend on the induced treewidth rather than the total number
    of cuts.
    """
    working = [
        (tuple(axes), np.asarray(values, dtype=float))
        for axes, values in factors
    ]
    for variable in order:
        involved = [factor for factor in working if variable in factor[0]]
        if not involved:
            continue
        working = [factor for factor in working if variable not in factor[0]]
        union_axes = tuple(
            sorted({axis for axes, _ in involved for axis in axes})
        )
        product_tensor = np.ones((8,) * len(union_axes), dtype=float)
        for axes, values in involved:
            positions = [union_axes.index(axis) for axis in axes]
            permutation = np.argsort(positions)
            ordered_positions = [positions[index] for index in permutation]
            ordered_values = (
                np.transpose(values, permutation) if len(axes) > 1 else values
            )
            shape = [1] * len(union_axes)
            for axis_position in ordered_positions:
                shape[axis_position] = 8
            product_tensor *= ordered_values.reshape(shape)
        variable_axis = union_axes.index(variable)
        remaining_axes = tuple(axis for axis in union_axes if axis != variable)
        working.append((
            remaining_axes,
            product_tensor.sum(axis=variable_axis),
        ))
    if not working:
        return 1.0
    union_axes = tuple(sorted({axis for axes, _ in working for axis in axes}))
    if union_axes:
        raise ValueError(
            "Contraction order did not eliminate every cut index."
        )
    value = 1.0
    for axes, tensor in working:
        if axes:
            raise ValueError("Non-scalar tensor remains after contraction.")
        value *= float(np.asarray(tensor).reshape(()))
    return value
