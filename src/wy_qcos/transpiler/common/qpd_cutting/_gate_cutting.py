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

"""Automatic, Qiskit-free gate-cutting workflow.

The workflow accepts :class:`.Circuit` objects with one- and two-qubit
unitaries.  It finds a width-constrained qubit partition, replaces every
cross-partition two-qubit gate by an exact local quasiprobability expansion,
evaluates every resulting fragment with density matrices, and reconstructs
Pauli expectation values.

The local decomposition is intentionally gate-agnostic: any numerical 4x4
unitary can be cut.  It uses a complete measure-and-prepare basis, so it is a
reference implementation rather than a low-overhead production sampler.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from typing import cast
from collections.abc import Iterable, Mapping, Sequence

import numpy as np

from ._wire_cutting_core import Circuit, Operation, PauliWord, _PAULIS


@dataclass(frozen=True)
class MeasurePrepare:
    """The physical map ``rho -> prepared * Tr(effect rho)`` on one qubit."""

    effect: np.ndarray
    prepared: np.ndarray


@dataclass(frozen=True)
class GateCutTerm:
    """One product-map term for a two-qubit gate cut."""

    left: MeasurePrepare
    right: MeasurePrepare
    coefficient: float


@dataclass(frozen=True)
class GateCut:
    """A cross-partition gate and its exact local decomposition."""

    instruction_index: int
    qubits: tuple[int, int]
    terms: tuple[GateCutTerm, ...]

    @property
    def gamma(self) -> float:
        """Return the quasiprobability 1-norm of this cut."""
        return float(sum(abs(term.coefficient) for term in self.terms))


@dataclass(frozen=True)
class Fragment:
    """A partition-local circuit with placeholders for local cut maps."""

    label: int
    qubits: tuple[int, ...]
    instructions: tuple[Operation | tuple[int, int], ...]


@dataclass(frozen=True)
class CuttingPlan:
    """Automatic partition and gate-cut plan for a circuit."""

    circuit: Circuit
    fragments: tuple[Fragment, ...]
    gate_cuts: tuple[GateCut, ...]
    partition: tuple[int, ...]

    @property
    def sampling_overhead(self) -> float:
        """Return the exact-sampling overhead induced by all selected cuts."""
        return float(
            np.prod([cut.gamma**2 for cut in self.gate_cuts], dtype=float)
        )


@dataclass(frozen=True)
class Reconstruction:
    """Values reconstructed from evaluated independent fragments."""

    expectations: tuple[float, ...]
    evaluated_term_combinations: int
    sampling_overhead: float


_BASIS_VECTORS = (
    np.array([1, 0], dtype=complex),
    np.array([0, 1], dtype=complex),
    np.array([1, 1], dtype=complex) / np.sqrt(2),
    np.array([1, 1j], dtype=complex) / np.sqrt(2),
)
_MP_BASIS = tuple(
    MeasurePrepare(
        np.outer(effect, effect.conj()), np.outer(prepared, prepared.conj())
    )
    for effect in _BASIS_VECTORS
    for prepared in _BASIS_VECTORS
)


def find_cuts(circuit: Circuit, *, max_qubits: int) -> CuttingPlan:
    """Find a width-constrained qubit partition and the required gate cuts.

    This uses a deterministic weighted graph partitioner followed by local
    improvement.  All cross-partition two-qubit gates are cut.  Gates with
    more than two inputs and explicit ``WireCut`` markers are rejected because
    the automatic workflow is deliberately a gate-cutting implementation.
    """
    if max_qubits < 1:
        raise ValueError("max_qubits must be positive.")
    if any(
        not isinstance(instruction, Operation)
        for instruction in circuit.instructions
    ):
        raise ValueError(
            "Automatic gate cutting does not accept explicit wire cuts."
        )
    if any(
        len(instruction.qubits) > 2 for instruction in circuit.instructions
    ):
        raise ValueError(
            "Decompose gates with more than two qubits before cut finding."
        )
    if circuit.num_qubits <= max_qubits:
        partition = tuple(0 for _ in range(circuit.num_qubits))
    else:
        partition = _partition_qubits(circuit, max_qubits)

    cuts: list[GateCut] = []
    cut_index_by_instruction: dict[int, int] = {}
    for index, instruction in enumerate(circuit.instructions):
        instruction = cast(Operation, instruction)
        if (
            len(instruction.qubits) == 2
            and partition[instruction.qubits[0]]
            != partition[instruction.qubits[1]]
        ):
            terms = _decompose_two_qubit_unitary(instruction.matrix)
            cut_index_by_instruction[index] = len(cuts)
            cuts.append(GateCut(index, instruction.qubits, terms))

    fragments = _build_fragments(circuit, partition, cut_index_by_instruction)
    return CuttingPlan(circuit, tuple(fragments), tuple(cuts), partition)


def reconstruct_expectation_values(
    plan: CuttingPlan,
    observables: Iterable[PauliWord],
    *,
    max_exact_terms: int = 250_000,
) -> Reconstruction:
    """Exactly evaluate fragments and reconstruct product-Pauli expectations.

    ``max_exact_terms`` prevents accidental exponential work.  For a larger
    plan, select fewer cuts, increase partition width, or implement importance
    sampling using the public :class:`GateCutTerm` data.
    """
    observables = tuple(
        _validate_observable(observable, plan.circuit.num_qubits)
        for observable in observables
    )
    term_count = int(
        np.prod([len(cut.terms) for cut in plan.gate_cuts], dtype=object)
    )
    if term_count > max_exact_terms:
        raise ValueError(
            f"Exact reconstruction needs {term_count} term combinations, "
            "exceeding "
            f"max_exact_terms={max_exact_terms}."
        )
    values = np.zeros(len(observables), dtype=float)
    choices: Sequence[range] = [
        range(len(cut.terms)) for cut in plan.gate_cuts
    ]
    for choice in product(*choices) if choices else [()]:
        coefficient = float(
            np.prod([
                plan.gate_cuts[index].terms[term].coefficient
                for index, term in enumerate(choice)
            ])
        )
        fragment_states = tuple(
            _evaluate_fragment(fragment, plan.gate_cuts, choice)
            for fragment in plan.fragments
        )
        for observable_index, observable in enumerate(observables):
            value = 1.0
            for fragment, state in zip(
                plan.fragments, fragment_states, strict=True
            ):
                local_word = {
                    local: observable[qubit]
                    for local, qubit in enumerate(fragment.qubits)
                    if qubit in observable
                }
                value *= _density_expectation(state, local_word)
            values[observable_index] += coefficient * value
    return Reconstruction(
        tuple(float(value) for value in values),
        term_count,
        plan.sampling_overhead,
    )


def exact_expectation_values(
    circuit: Circuit, observables: Iterable[PauliWord]
) -> tuple[float, ...]:
    """Evaluate the uncut circuit for verification or small circuits."""
    if any(
        not isinstance(instruction, Operation)
        for instruction in circuit.instructions
    ):
        raise ValueError(
            "Reference evaluation does not accept wire-cut markers."
        )
    density = _zero_density(circuit.num_qubits)
    for instruction in circuit.instructions:
        instruction = cast(Operation, instruction)
        density = _apply_unitary_density(
            density, instruction.matrix, instruction.qubits, circuit.num_qubits
        )
    return tuple(
        _density_expectation(
            density, _validate_observable(observable, circuit.num_qubits)
        )
        for observable in observables
    )


def _partition_qubits(circuit: Circuit, max_qubits: int) -> tuple[int, ...]:
    """Pack interacting qubits, then improve the result by relocation."""
    num_qubits = circuit.num_qubits
    num_parts = (num_qubits + max_qubits - 1) // max_qubits
    weights = np.zeros((num_qubits, num_qubits), dtype=float)
    for instruction in circuit.instructions:
        instruction = cast(Operation, instruction)
        if len(instruction.qubits) == 2:
            left, right = instruction.qubits
            weights[left, right] += 1.0
            weights[right, left] += 1.0
    # Process high-degree vertices first; place each next to its already
    # placed neighbours.
    order = sorted(
        range(num_qubits),
        key=lambda qubit: (-float(weights[qubit].sum()), qubit),
    )
    assignment = [-1] * num_qubits
    sizes = [0] * num_parts
    for qubit in order:
        candidates = [
            part for part in range(num_parts) if sizes[part] < max_qubits
        ]
        best = max(
            candidates,
            key=lambda part: (
                sum(
                    weights[qubit, other]
                    for other in range(num_qubits)
                    if assignment[other] == part
                ),
                -sizes[part],
                -part,
            ),
        )
        assignment[qubit] = best
        sizes[best] += 1
    # Improve the cut weight by moving vertices when capacity permits.
    improved = True
    while improved:
        improved = False
        for qubit in range(num_qubits):
            current = assignment[qubit]
            current_score = sum(
                weights[qubit, other]
                for other in range(num_qubits)
                if assignment[other] == current
            )
            for candidate in range(num_parts):
                if candidate == current or sizes[candidate] >= max_qubits:
                    continue
                candidate_score = sum(
                    weights[qubit, other]
                    for other in range(num_qubits)
                    if assignment[other] == candidate
                )
                if candidate_score > current_score + 1e-12:
                    assignment[qubit] = candidate
                    sizes[current] -= 1
                    sizes[candidate] += 1
                    improved = True
                    break
            if improved:
                break
    # A relocation cannot improve a completely full packing.  Try exchanges as
    # well; this is important for chains such as (0--1)--(2--3) with width 2.
    improved = True
    while improved:
        improved = False
        baseline = _internal_interaction_weight(assignment, weights)
        for left in range(num_qubits):
            for right in range(left + 1, num_qubits):
                if assignment[left] == assignment[right]:
                    continue
                assignment[left], assignment[right] = (
                    assignment[right],
                    assignment[left],
                )
                exchange_score = _internal_interaction_weight(
                    assignment, weights
                )
                if exchange_score > baseline + 1e-12:
                    improved = True
                    break
                assignment[left], assignment[right] = (
                    assignment[right],
                    assignment[left],
                )
            if improved:
                break
    # Compact labels, which makes plans stable and omits empty bins.
    labels = {old: new for new, old in enumerate(sorted(set(assignment)))}
    return tuple(labels[part] for part in assignment)


def _internal_interaction_weight(
    assignment: Sequence[int], weights: np.ndarray
) -> float:
    return float(
        sum(
            weights[left, right]
            for left in range(len(assignment))
            for right in range(left + 1, len(assignment))
            if assignment[left] == assignment[right]
        )
    )


def _build_fragments(
    circuit: Circuit, partition: Sequence[int], cut_indices: Mapping[int, int]
) -> list[Fragment]:
    per_fragment: dict[int, list[Operation | tuple[int, int]]] = {
        label: [] for label in sorted(set(partition))
    }
    qubits_by_fragment = {
        label: tuple(
            qubit
            for qubit, assigned in enumerate(partition)
            if assigned == label
        )
        for label in per_fragment
    }
    remaps = {
        label: {qubit: local for local, qubit in enumerate(qubits)}
        for label, qubits in qubits_by_fragment.items()
    }
    for index, instruction in enumerate(circuit.instructions):
        instruction = cast(Operation, instruction)
        labels = {partition[qubit] for qubit in instruction.qubits}
        if len(labels) == 1:
            label = labels.pop()
            per_fragment[label].append(
                Operation(
                    instruction.matrix,
                    tuple(
                        remaps[label][qubit] for qubit in instruction.qubits
                    ),
                )
            )
        elif index in cut_indices:
            cut_index = cut_indices[index]
            left, right = instruction.qubits
            per_fragment[partition[left]].append((
                cut_index,
                remaps[partition[left]][left],
            ))
            per_fragment[partition[right]].append((
                cut_index,
                remaps[partition[right]][right],
            ))
        else:  # pragma: no cover - only two-qubit cross gates reach this path
            raise AssertionError(
                "Cross-partition instruction was not marked as a cut."
            )
    return [
        Fragment(label, qubits_by_fragment[label], tuple(per_fragment[label]))
        for label in per_fragment
    ]


@lru_cache(maxsize=128)
def _decompose_two_qubit_unitary_from_bytes(
    matrix_bytes: bytes,
) -> tuple[GateCutTerm, ...]:
    matrix = cast(
        np.ndarray, np.frombuffer(matrix_bytes, dtype=np.complex128)
    ).reshape(4, 4)
    target = _two_qubit_channel_superoperator(matrix)
    basis = _product_map_superoperator_basis()
    coefficients = np.linalg.solve(basis, target.reshape(-1))
    terms: list[GateCutTerm] = []
    for index, coefficient in enumerate(coefficients):
        if abs(coefficient) > 1e-10:
            left, right = divmod(index, len(_MP_BASIS))
            if abs(coefficient.imag) > 1e-8:
                raise ValueError(
                    "Two-qubit channel decomposition unexpectedly has complex "
                    "coefficients."
                )
            terms.append(
                GateCutTerm(
                    _MP_BASIS[left], _MP_BASIS[right], float(coefficient.real)
                )
            )
    return tuple(terms)


def _decompose_two_qubit_unitary(
    matrix: np.ndarray,
) -> tuple[GateCutTerm, ...]:
    matrix = np.asarray(matrix, dtype=np.complex128)
    if matrix.shape != (4, 4):
        raise ValueError("Only two-qubit 4x4 unitaries can be gate-cut.")
    return _decompose_two_qubit_unitary_from_bytes(
        np.ascontiguousarray(matrix).tobytes()
    )


@lru_cache(maxsize=1)
def _product_map_superoperator_basis() -> np.ndarray:
    columns = []
    for left, right in product(_MP_BASIS, repeat=2):
        columns.append(
            _channel_superoperator(
                lambda rho: _apply_measure_prepare(
                    _apply_measure_prepare(rho, left, 0, 2), right, 1, 2
                )
            ).reshape(-1)
        )
    return np.column_stack(columns)


def _two_qubit_channel_superoperator(matrix: np.ndarray) -> np.ndarray:
    # The native circuit convention numbers q_0 as the least-significant
    # statevector bit, while a two-qubit gate matrix lists its first argument
    # as the most-significant local bit.  Embed the matrix before building the
    # channel so the measure-and-prepare basis uses the same wire ordering.
    embedded = _embed_operator(matrix, (0, 1), 2)
    return _channel_superoperator(
        lambda rho: embedded @ rho @ embedded.conj().T
    )


def _channel_superoperator(channel) -> np.ndarray:
    columns = []
    for row in range(4):
        for column in range(4):
            basis = np.zeros((4, 4), dtype=complex)
            basis[row, column] = 1.0
            columns.append(channel(basis).reshape(-1))
    return np.column_stack(columns)


def _evaluate_fragment(
    fragment: Fragment, cuts: Sequence[GateCut], choice: Sequence[int]
) -> np.ndarray:
    density = _zero_density(len(fragment.qubits))
    for instruction in fragment.instructions:
        if isinstance(instruction, Operation):
            density = _apply_unitary_density(
                density,
                instruction.matrix,
                instruction.qubits,
                len(fragment.qubits),
            )
        else:
            cut_index, qubit = instruction
            cut = cuts[cut_index]
            term = cut.terms[choice[cut_index]]
            local_map = (
                term.left
                if fragment.qubits[qubit] == cut.qubits[0]
                else term.right
            )
            density = _apply_measure_prepare(
                density, local_map, qubit, len(fragment.qubits)
            )
    return density


def _zero_density(num_qubits: int) -> np.ndarray:
    density = np.zeros((1 << num_qubits, 1 << num_qubits), dtype=complex)
    density[0, 0] = 1.0
    return density


def _apply_unitary_density(
    density: np.ndarray,
    matrix: np.ndarray,
    qubits: Sequence[int],
    num_qubits: int,
) -> np.ndarray:
    embedded = _embed_operator(matrix, qubits, num_qubits)
    return embedded @ density @ embedded.conj().T


def _embed_operator(
    matrix: np.ndarray, qubits: Sequence[int], num_qubits: int
) -> np.ndarray:
    dimension = 1 << num_qubits
    embedded = np.zeros((dimension, dimension), dtype=complex)
    for input_index in range(dimension):
        local_input = _local_bits(input_index, qubits)
        for local_output in range(1 << len(qubits)):
            output_index = input_index
            for position, qubit in enumerate(qubits):
                bit = (local_output >> (len(qubits) - 1 - position)) & 1
                output_index = (output_index & ~(1 << qubit)) | (bit << qubit)
            embedded[output_index, input_index] = matrix[
                local_output, local_input
            ]
    return embedded


def _local_bits(index: int, qubits: Sequence[int]) -> int:
    value = 0
    for qubit in qubits:
        value = (value << 1) | ((index >> qubit) & 1)
    return value


def _apply_measure_prepare(
    density: np.ndarray, operation: MeasurePrepare, qubit: int, num_qubits: int
) -> np.ndarray:
    """Apply a trace-nonincreasing local measure-and-prepare channel."""
    dimension = 1 << num_qubits
    output = np.zeros_like(density)
    mask = 1 << qubit
    for row in range(dimension):
        for column in range(dimension):
            row_rest = row & ~mask
            column_rest = column & ~mask
            out_row_bit = (row >> qubit) & 1
            out_column_bit = (column >> qubit) & 1
            weighted_input = 0.0j
            for in_row_bit in range(2):
                for in_column_bit in range(2):
                    in_row = row_rest | (in_row_bit << qubit)
                    in_column = column_rest | (in_column_bit << qubit)
                    weighted_input += (
                        operation.effect[in_column_bit, in_row_bit]
                        * density[in_row, in_column]
                    )
            output[row, column] = (
                operation.prepared[out_row_bit, out_column_bit]
                * weighted_input
            )
    return output


def _density_expectation(
    density: np.ndarray, observable: Mapping[int, str]
) -> float:
    num_qubits = int(np.log2(density.shape[0]))
    operator = np.eye(1 << num_qubits, dtype=complex)
    for qubit, pauli in observable.items():
        operator = (
            _embed_operator(_PAULIS[pauli], (qubit,), num_qubits) @ operator
        )
    value = np.trace(operator @ density)
    if abs(value.imag) > 1e-8:
        raise ValueError("A Pauli expectation must be real.")
    return float(value.real)


def _validate_observable(
    observable: PauliWord, num_qubits: int
) -> dict[int, str]:
    normalized: dict[int, str] = {}
    for qubit, pauli in observable.items():
        if qubit < 0 or qubit >= num_qubits or pauli not in _PAULIS:
            raise ValueError(f"Invalid Pauli term {pauli!r} on qubit {qubit}.")
        if pauli != "I":
            normalized[qubit] = pauli
    return normalized
