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

"""Explicit conversion from the existing circuit model to the upstream API.

Logical qubit numbers and Pauli-label ordering are unchanged.  Native
multi-qubit operation matrices have their first target as the most significant
matrix bit; Qiskit instead treats its first target as the least significant
matrix bit.  Conversion reverses each operation's target list to account for
that difference without modifying its matrix or global phase.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from numbers import Integral

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList

from ._wire_cutting_core import Circuit, Operation, WireCut
from .instructions import CutWire
from .observables import PauliTerm, coerce_pauli_term


def to_qiskit(circuit: Circuit) -> QuantumCircuit:
    """Return a Qiskit circuit with the native circuit's operations.

    Each static unitary, including arbitrary matrices on three or more
    qubits, is copied without synthesis, approximation, or phase removal.
    Native targets ``(a, b)`` become Qiskit unitary targets ``[b, a]``;
    logical qubit ``q`` still refers to Qiskit qubit ``q``.  Every
    :class:`WireCut` becomes a :class:`CutWire` at its original position.
    Neither the native circuit nor its matrices are modified or shared with
    the result.

    This converts the circuit representation only.  After conversion, use
    ``cut_wires`` to expand markers, ``expand_observables`` to map the final
    observables, and the upstream partition/experiment/reconstruction APIs.
    The upstream automatic cut finder still requires operations on at most
    two qubits; any larger unitary must be transpiled before automatic search.

    Args:
        circuit: A circuit built with this project's :class:`Circuit`.

    Raises:
        TypeError: The input is not a native circuit, or an instruction has
            a type outside the native static-unitary model, or a width or
            target index is not an integer.
        ValueError: A width or target index is out of range.  Instructions
            appended directly to the native circuit are validated as well.
    """
    if not isinstance(circuit, Circuit):
        raise TypeError("to_qiskit expects a qpd_cutting.Circuit instance.")
    if isinstance(circuit.num_qubits, bool) or not isinstance(
        circuit.num_qubits, Integral
    ):
        raise TypeError("The circuit width must be a positive integer.")
    num_qubits = int(circuit.num_qubits)
    if num_qubits < 1:
        raise ValueError("The circuit width must be a positive integer.")
    converted = QuantumCircuit(num_qubits)
    for instruction in circuit.instructions:
        if isinstance(instruction, WireCut):
            converted.append(
                CutWire(), [_qubit_index(instruction.qubit, num_qubits)]
            )
        elif isinstance(instruction, Operation):
            targets = [
                _qubit_index(qubit, num_qubits)
                for qubit in reversed(instruction.qubits)
            ]
            if not targets or len(set(targets)) != len(targets):
                raise ValueError("An operation needs distinct target qubits.")
            matrix = np.array(instruction.matrix, dtype=complex, copy=True)
            dimension = 1 << len(targets)
            if matrix.shape != (dimension, dimension):
                raise ValueError(
                    "Operation matrix shape does not match its targets."
                )
            converted.unitary(matrix, targets)
        else:
            raise TypeError(
                "Unsupported native instruction type: "
                f"{type(instruction).__name__}."
            )
    return converted


def to_pauli_list(
    observables: Iterable[PauliTerm | Mapping[int, str] | str] | PauliList,
    num_qubits: int,
) -> PauliList:
    """Convert product-Pauli observables without changing qubit order or signs.

    Native :class:`PauliTerm` objects, sparse mappings such as ``{0: "Y"}``,
    and unsigned strings such as ``"IZY"`` are accepted in an iterable.
    Qubit zero is the rightmost label character, as in both native observables
    and Qiskit.  Short labels are padded on the left with identity operators;
    explicit labels wider than ``num_qubits`` are rejected.  Ordering and
    duplicate observables are preserved.  Supply a collection (for example,
    ``["IZY"]``), including when there is only one observable.  Qubit indices
    and widths may be Python or NumPy integers, but not booleans or floats;
    every explicit index must be in range, including identity factors.

    An existing :class:`PauliList` is copied with its phases unchanged and
    must have exactly ``num_qubits`` qubits.  Weighted :class:`PauliSum`
    objects are not product Paulis: first extract their unique terms using
    ``gather_unique_observable_terms`` and later combine reconstructed values
    using ``reconstruct_observable_expvals_from_terms``.

    Raises:
        TypeError: The width is not an integer, or a native observable is
            neither a Pauli term, mapping, nor label.
        ValueError: The width is negative, the list is empty, or an observable
            is invalid or does not fit the requested width.
    """
    if isinstance(num_qubits, bool) or not isinstance(num_qubits, Integral):
        raise TypeError("num_qubits must be a non-negative integer.")
    num_qubits = int(num_qubits)
    if num_qubits < 0:
        raise ValueError("num_qubits must be a non-negative integer.")
    if isinstance(observables, PauliList):
        if observables.num_qubits != num_qubits:
            raise ValueError("The PauliList width does not match num_qubits.")
        if len(observables) == 0:
            raise ValueError("At least one observable is required.")
        return observables.copy()
    if isinstance(observables, (str, Mapping, PauliTerm)):
        raise TypeError(
            "observables must be a collection; wrap one observable in a list."
        )

    labels: list[str] = []
    for observable in observables:
        if not isinstance(observable, (PauliTerm, Mapping, str)):
            raise TypeError(
                "Expected a PauliTerm, qubit-to-axis mapping, or Pauli label; "
                "expand weighted observables into product-Pauli terms."
            )
        if isinstance(observable, str) and len(observable) > num_qubits:
            raise ValueError("A Pauli label is wider than num_qubits.")
        if isinstance(observable, Mapping):
            observable = {
                _qubit_index(qubit, num_qubits): axis
                for qubit, axis in observable.items()
            }
        elif isinstance(observable, PauliTerm):
            observable = PauliTerm(
                tuple(
                    (_qubit_index(qubit, num_qubits), axis)
                    for qubit, axis in observable.factors
                )
            )
        labels.append(coerce_pauli_term(observable).label(num_qubits))
    if not labels:
        raise ValueError("At least one observable is required.")
    return PauliList(labels)


def _qubit_index(qubit: int, num_qubits: int) -> int:
    """Normalize integer scalars without wrapping or truncating them."""
    if isinstance(qubit, bool) or not isinstance(qubit, Integral):
        raise TypeError(
            "A qubit index must be an integer, excluding booleans."
        )
    qubit = int(qubit)
    if not 0 <= qubit < num_qubits:
        raise ValueError(
            "A qubit index is outside the requested circuit width."
        )
    return qubit


__all__ = ["to_qiskit", "to_pauli_list"]
