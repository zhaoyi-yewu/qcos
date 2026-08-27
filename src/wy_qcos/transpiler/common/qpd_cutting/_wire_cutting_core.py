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

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import cos, sin

import numpy as np


ComplexArray = np.ndarray
PauliWord = Mapping[int, str]


@dataclass(frozen=True)
class WireCut:
    """Split marker for a logical wire's upstream and downstream parts."""

    qubit: int


@dataclass(frozen=True)
class Operation:
    """A unitary operation in the compact circuit representation."""

    matrix: ComplexArray
    qubits: tuple[int, ...]


class Circuit:
    """Minimal circuit used by the standalone cutting implementation."""

    def __init__(self, num_qubits: int) -> None:
        if num_qubits < 1:
            raise ValueError("A circuit must contain at least one qubit.")
        self.num_qubits = num_qubits
        self.instructions: list[Operation | WireCut] = []

    def unitary(self, matrix: ComplexArray, qubits: Sequence[int]) -> Circuit:
        """Append a unitary acting on ``qubits`` in the supplied order."""
        qubits = tuple(qubits)
        if not qubits or len(set(qubits)) != len(qubits):
            raise ValueError("An operation needs distinct target qubits.")
        if any(qubit < 0 or qubit >= self.num_qubits for qubit in qubits):
            raise ValueError("Operation target is outside the circuit.")
        matrix = np.asarray(matrix, dtype=complex)
        dimension = 1 << len(qubits)
        if matrix.shape != (dimension, dimension):
            raise ValueError(
                f"Matrix shape {matrix.shape} does not match "
                f"{len(qubits)} qubits."
            )
        if not np.allclose(
            matrix.conj().T @ matrix, np.eye(dimension), atol=1e-12
        ):
            raise ValueError("Operation matrix must be unitary.")
        self.instructions.append(Operation(matrix, qubits))
        return self

    def h(self, qubit: int) -> Circuit:
        """Append a Hadamard gate."""
        return self.unitary(np.array([[1, 1], [1, -1]]) / np.sqrt(2), [qubit])

    def x(self, qubit: int) -> Circuit:
        """Append a Pauli-X gate."""
        return self.unitary(_PAULIS["X"], [qubit])

    def y(self, qubit: int) -> Circuit:
        """Append a Pauli-Y gate."""
        return self.unitary(_PAULIS["Y"], [qubit])

    def z(self, qubit: int) -> Circuit:
        """Append a Pauli-Z gate."""
        return self.unitary(_PAULIS["Z"], [qubit])

    def ry(self, theta: float, qubit: int) -> Circuit:
        """Append a Y-axis rotation."""
        return self.unitary(
            np.array([
                [cos(theta / 2), -sin(theta / 2)],
                [sin(theta / 2), cos(theta / 2)],
            ]),
            [qubit],
        )

    def rz(self, theta: float, qubit: int) -> Circuit:
        """Append a Z-axis rotation."""
        return self.unitary(
            np.diag([np.exp(-0.5j * theta), np.exp(0.5j * theta)]), [qubit]
        )

    def cx(self, control: int, target: int) -> Circuit:
        """Append a controlled-X gate."""
        return self.unitary(
            np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]),
            [control, target],
        )

    def cz(self, control: int, target: int) -> Circuit:
        """Append a controlled-Z gate."""
        return self.unitary(np.diag([1, 1, 1, -1]), [control, target])

    def swap(self, left: int, right: int) -> Circuit:
        """Append a SWAP gate."""
        return self.unitary(
            np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]),
            [left, right],
        )

    def rx(self, theta: float, qubit: int) -> Circuit:
        """Append an X-axis rotation."""
        return self.unitary(
            np.array([
                [cos(theta / 2), -1j * sin(theta / 2)],
                [-1j * sin(theta / 2), cos(theta / 2)],
            ]),
            [qubit],
        )

    def rzz(self, theta: float, source: int, target: int) -> Circuit:
        """Append ``exp(-i theta Z⊗Z / 2)``."""
        phase = np.exp(-0.5j * theta)
        return self.unitary(
            np.diag([phase, phase.conjugate(), phase.conjugate(), phase]),
            [source, target],
        )

    def cut_wire(self, qubit: int) -> Circuit:
        """Mark the point at which ``qubit`` is cut."""
        if qubit < 0 or qubit >= self.num_qubits:
            raise ValueError("Cut target is outside the circuit.")
        self.instructions.append(WireCut(qubit))
        return self


@dataclass(frozen=True)
class ReconstructionResult:
    """Exact expectation values reconstructed from the eight cut terms."""

    expectations: tuple[float, ...]
    term_count: int
    sampling_overhead: float


@dataclass(frozen=True)
class _Fragment:
    num_qubits: int
    operations: tuple[Operation, ...]
    physical_wires: tuple[int, ...]
    source_qubit: int | None = None


@dataclass(frozen=True)
class _CutTerm:
    source_measurement: str | None
    downstream_state: ComplexArray
    coefficient: float


_ZERO = np.array([1, 0], dtype=complex)
_ONE = np.array([0, 1], dtype=complex)
_PLUS = np.array([1, 1], dtype=complex) / np.sqrt(2)
_MINUS = np.array([1, -1], dtype=complex) / np.sqrt(2)
_I_PLUS = np.array([1, 1j], dtype=complex) / np.sqrt(2)
_I_MINUS = np.array([1, -1j], dtype=complex) / np.sqrt(2)

_CUT_TERMS = (
    _CutTerm(None, _ZERO, 0.5),
    _CutTerm(None, _ONE, 0.5),
    _CutTerm("X", _PLUS, 0.5),
    _CutTerm("X", _MINUS, -0.5),
    _CutTerm("Y", _I_PLUS, 0.5),
    _CutTerm("Y", _I_MINUS, -0.5),
    _CutTerm("Z", _ZERO, 0.5),
    _CutTerm("Z", _ONE, -0.5),
)

_PAULIS = {
    "I": np.eye(2, dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}


def reconstruct_single_wire_cut(
    circuit: Circuit, observables: Iterable[PauliWord]
) -> ReconstructionResult:
    """Reconstruct Pauli expectation values after exactly one marked wire cut.

    ``observables`` maps logical qubit indices to ``"X"``, ``"Y"`` or ``"Z"``.
    Omitted qubits are identities.  The cut logical qubit is interpreted on
    the downstream side, matching the state-transfer semantics of a wire cut.
    """
    upstream, downstream, final_wire_ids = _split_single_wire_cut(circuit)
    normalized = tuple(
        _normalize_pauli_word(observable, circuit.num_qubits)
        for observable in observables
    )
    upstream_states = _simulate(upstream)
    reconstructed = np.zeros(len(normalized), dtype=float)

    for term in _CUT_TERMS:
        downstream_states = _simulate(
            downstream, {downstream.source_qubit: term.downstream_state}
        )
        for index, observable in enumerate(normalized):
            up_word, down_word = _partition_observable(
                observable, final_wire_ids, upstream, downstream
            )
            upstream_value = _measured_expectation(
                upstream_states,
                up_word,
                upstream.source_qubit,
                term.source_measurement,
            )
            downstream_value = _expectation(downstream_states, down_word)
            reconstructed[index] += (
                term.coefficient * upstream_value * downstream_value
            )

    return ReconstructionResult(
        expectations=tuple(float(value) for value in reconstructed),
        term_count=len(_CUT_TERMS),
        sampling_overhead=float(
            sum(abs(term.coefficient) for term in _CUT_TERMS) ** 2
        ),
    )


def exact_expectations_without_cut(
    circuit: Circuit, observables: Iterable[PauliWord]
) -> tuple[float, ...]:
    """Return reference expectations by treating the cut marker as identity."""
    operations = tuple(
        instruction
        for instruction in circuit.instructions
        if isinstance(instruction, Operation)
    )
    state = _simulate(
        _Fragment(
            circuit.num_qubits, operations, tuple(range(circuit.num_qubits))
        )
    )
    return tuple(
        float(
            _expectation(
                state, _normalize_pauli_word(observable, circuit.num_qubits)
            )
        )
        for observable in observables
    )


def _split_single_wire_cut(
    circuit: Circuit,
) -> tuple[_Fragment, _Fragment, dict[int, int]]:
    cuts = [
        instruction
        for instruction in circuit.instructions
        if isinstance(instruction, WireCut)
    ]
    if len(cuts) != 1:
        raise ValueError(
            "This standalone implementation supports exactly one WireCut."
        )
    cut = cuts[0]
    virtual_cut_wire = circuit.num_qubits
    current_wire_ids = list(range(circuit.num_qubits))
    transformed: list[Operation] = []
    for instruction in circuit.instructions:
        if isinstance(instruction, WireCut):
            current_wire_ids[instruction.qubit] = virtual_cut_wire
        else:
            transformed.append(
                Operation(
                    instruction.matrix,
                    tuple(current_wire_ids[q] for q in instruction.qubits),
                )
            )

    # There must be no gate joining the two independently executable fragments.
    adjacency = {wire: set() for wire in range(circuit.num_qubits + 1)}
    for operation in transformed:
        for left in operation.qubits:
            for right in operation.qubits:
                adjacency[left].add(right)
    upstream_wires = _connected_component(adjacency, cut.qubit)
    downstream_wires = _connected_component(adjacency, virtual_cut_wire)
    if upstream_wires & downstream_wires:
        raise ValueError(
            "The cut does not separate the circuit into two fragments."
        )
    if upstream_wires | downstream_wires != set(adjacency):
        raise ValueError(
            "The circuit has an idle component unrelated to the wire cut."
        )

    def build_fragment(wires: set[int], source_wire: int | None) -> _Fragment:
        ordered_wires = sorted(wires)
        remap = {wire: index for index, wire in enumerate(ordered_wires)}
        operations = tuple(
            Operation(
                operation.matrix, tuple(remap[q] for q in operation.qubits)
            )
            for operation in transformed
            if set(operation.qubits) <= wires
        )
        return _Fragment(
            len(ordered_wires),
            operations,
            tuple(ordered_wires),
            None if source_wire is None else remap[source_wire],
        )

    return (
        build_fragment(upstream_wires, cut.qubit),
        build_fragment(downstream_wires, virtual_cut_wire),
        {
            logical: current_wire_ids[logical]
            for logical in range(circuit.num_qubits)
        },
    )


def _connected_component(
    adjacency: Mapping[int, set[int]], start: int
) -> set[int]:
    found = {start}
    pending = [start]
    while pending:
        wire = pending.pop()
        for neighbour in adjacency[wire]:
            if neighbour not in found:
                found.add(neighbour)
                pending.append(neighbour)
    return found


def _normalize_pauli_word(
    observable: PauliWord, num_qubits: int
) -> dict[int, str]:
    normalized: dict[int, str] = {}
    for qubit, pauli in observable.items():
        if qubit < 0 or qubit >= num_qubits or pauli not in _PAULIS:
            raise ValueError(f"Invalid Pauli term {pauli!r} on qubit {qubit}.")
        if pauli != "I":
            normalized[qubit] = pauli
    return normalized


def _partition_observable(
    observable: Mapping[int, str],
    final_wire_ids: Mapping[int, int],
    upstream: _Fragment,
    downstream: _Fragment,
) -> tuple[dict[int, str], dict[int, str]]:
    up_local = {
        wire: index for index, wire in enumerate(upstream.physical_wires)
    }
    down_local = {
        wire: index for index, wire in enumerate(downstream.physical_wires)
    }
    up_word: dict[int, str] = {}
    down_word: dict[int, str] = {}
    for logical_qubit, pauli in observable.items():
        final_wire = final_wire_ids[logical_qubit]
        if final_wire in up_local:
            up_word[up_local[final_wire]] = pauli
        elif final_wire in down_local:
            down_word[down_local[final_wire]] = pauli
        else:  # pragma: no cover
            # All logical wires must belong to one fragment.
            raise ValueError(
                f"Observable qubit {logical_qubit} is not in a fragment."
            )
    return up_word, down_word


def _simulate(
    fragment: _Fragment,
    initial_states: Mapping[int | None, ComplexArray] | None = None,
) -> ComplexArray:
    state = np.zeros(1 << fragment.num_qubits, dtype=complex)
    state[0] = 1.0
    if initial_states:
        for qubit, vector in initial_states.items():
            if qubit is None:
                continue
            vector = np.asarray(vector, dtype=complex)
            if vector.shape != (2,) or not np.isclose(
                np.vdot(vector, vector), 1.0
            ):
                raise ValueError(
                    "Prepared states must be normalized one-qubit vectors."
                )
            state = _apply_unitary(
                state,
                vector.reshape(2, 1) @ np.array([[1, 0]]),
                (qubit,),
                fragment.num_qubits,
            )
    for operation in fragment.operations:
        state = _apply_unitary(
            state, operation.matrix, operation.qubits, fragment.num_qubits
        )
    return state


def _apply_unitary(
    state: ComplexArray,
    matrix: ComplexArray,
    qubits: Sequence[int],
    num_qubits: int,
) -> ComplexArray:
    axes = [num_qubits - 1 - qubit for qubit in qubits]
    tensor = state.reshape((2,) * num_qubits)
    moved = np.moveaxis(tensor, axes, range(len(axes)))
    rest_shape = moved.shape[len(axes) :]
    updated = matrix @ moved.reshape(1 << len(axes), -1)
    return np.moveaxis(
        updated.reshape((2,) * len(axes) + rest_shape), range(len(axes)), axes
    ).reshape(-1)


def _expectation(state: ComplexArray, observable: Mapping[int, str]) -> float:
    transformed = state
    num_qubits = int(np.log2(state.size))
    for qubit, pauli in observable.items():
        transformed = _apply_unitary(
            transformed, _PAULIS[pauli], (qubit,), num_qubits
        )
    return float(np.vdot(state, transformed).real)


def _measured_expectation(
    state: ComplexArray,
    observable: Mapping[int, str],
    source_qubit: int | None,
    measurement: str | None,
) -> float:
    if measurement is None:
        return _expectation(state, observable)
    if source_qubit is None:
        raise ValueError("A measured cut term requires a source qubit.")
    num_qubits = int(np.log2(state.size))
    measured = _apply_unitary(
        state, _PAULIS[measurement], (source_qubit,), num_qubits
    )
    # Tr[O (P+ rho P+ - P- rho P-)] = Re <psi|O sigma|psi>.
    transformed = measured
    for qubit, pauli in observable.items():
        transformed = _apply_unitary(
            transformed, _PAULIS[pauli], (qubit,), num_qubits
        )
    return float(np.vdot(state, transformed).real)
