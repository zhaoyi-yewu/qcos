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


_PAULI_AXES = frozenset("IXYZ")


@dataclass(frozen=True, order=True)
class PauliTerm:
    """A hashable product-Pauli observable with implicit identity support."""

    factors: tuple[tuple[int, str], ...]

    def __post_init__(self) -> None:
        """Validate and canonicalize the immutable factor sequence."""
        indices = [qubit for qubit, _ in self.factors]
        if indices != sorted(indices) or len(indices) != len(set(indices)):
            raise ValueError(
                "Pauli factors must use unique, ascending qubit indices."
            )
        if any(
            qubit < 0 or pauli not in _PAULI_AXES - {"I"}
            for qubit, pauli in self.factors
        ):
            raise ValueError(
                "Factors must use non-negative qubits and X, Y, or Z axes."
            )

    @classmethod
    def from_mapping(cls, observable: Mapping[int, str]) -> PauliTerm:
        """Build a term from a sparse qubit-to-axis mapping."""
        normalized = []
        for qubit, pauli in observable.items():
            if (
                not isinstance(qubit, int)
                or qubit < 0
                or pauli not in _PAULI_AXES
            ):
                raise ValueError(
                    f"Invalid Pauli factor {pauli!r} on qubit {qubit!r}."
                )
            if pauli != "I":
                normalized.append((qubit, pauli))
        return cls(tuple(sorted(normalized)))

    @classmethod
    def from_label(cls, label: str) -> PauliTerm:
        """Build a term from a conventional big-endian Pauli label."""
        if not label or set(label) - _PAULI_AXES:
            raise ValueError(
                "A Pauli label must be a non-empty string over I, X, Y, Z."
            )
        return cls.from_mapping({
            qubit: axis
            for qubit, axis in enumerate(reversed(label))
            if axis != "I"
        })

    def as_dict(self) -> dict[int, str]:
        """Return the sparse mapping accepted by native circuit workflows."""
        return dict(self.factors)

    def label(self, num_qubits: int) -> str:
        """Return a big-endian label padded to ``num_qubits``."""
        if num_qubits < 0 or any(
            qubit >= num_qubits for qubit, _ in self.factors
        ):
            raise ValueError("num_qubits does not contain this Pauli term.")
        axes = ["I"] * num_qubits
        for qubit, axis in self.factors:
            axes[num_qubits - 1 - qubit] = axis
        return "".join(axes)


@dataclass(frozen=True)
class PauliSum:
    """A sparse linear combination of product-Pauli terms."""

    terms: tuple[tuple[complex, PauliTerm], ...]

    @classmethod
    def from_terms(
        cls,
        terms: Iterable[tuple[complex, PauliTerm | Mapping[int, str] | str]],
    ) -> PauliSum:
        """Normalize, combine, and order nonzero terms deterministically."""
        coefficients: dict[PauliTerm, complex] = {}
        for coefficient, observable in terms:
            term = coerce_pauli_term(observable)
            coefficients[term] = coefficients.get(term, 0.0j) + complex(
                coefficient
            )
        return cls(
            tuple(
                (coefficient, term)
                for term, coefficient in sorted(coefficients.items())
                if coefficient != 0
            )
        )


def coerce_pauli_term(
    observable: PauliTerm | Mapping[int, str] | str,
) -> PauliTerm:
    """Convert a native sparse mapping or label to :class:`PauliTerm`."""
    if isinstance(observable, PauliTerm):
        return observable
    if isinstance(observable, str):
        return PauliTerm.from_label(observable)
    return PauliTerm.from_mapping(observable)


def normalize_observables(
    observables: Iterable[PauliTerm | Mapping[int, str] | str], num_qubits: int
) -> tuple[dict[int, str], ...]:
    """Convert observables to native sparse maps and validate their widths."""
    normalized = tuple(
        coerce_pauli_term(observable) for observable in observables
    )
    if not normalized:
        raise ValueError("At least one observable is required.")
    for term in normalized:
        term.label(num_qubits)
    return tuple(term.as_dict() for term in normalized)


def qubitwise_commutes(left: PauliTerm, right: PauliTerm) -> bool:
    """Return whether every shared qubit has equal axes or an identity."""
    return all(
        right.as_dict().get(qubit, axis) == axis
        for qubit, axis in left.factors
    )


def group_qubitwise_commuting(
    observables: Sequence[PauliTerm | Mapping[int, str] | str],
) -> tuple[tuple[PauliTerm, ...], ...]:
    """Greedily group product Paulis that share one measurement basis."""
    groups: list[list[PauliTerm]] = []
    for observable in map(coerce_pauli_term, observables):
        for group in groups:
            if all(qubitwise_commutes(observable, member) for member in group):
                group.append(observable)
                break
        else:
            groups.append([observable])
    return tuple(tuple(group) for group in groups)


def gather_unique_observable_terms(
    observables: Iterable[PauliTerm | PauliSum | Mapping[int, str] | str],
) -> tuple[PauliTerm, ...]:
    """Return unique nonzero terms in first-occurrence order."""
    unique: dict[PauliTerm, None] = {}
    for observable in observables:
        source: Iterable[PauliTerm]
        if isinstance(observable, PauliSum):
            source = (
                term
                for coefficient, term in observable.terms
                if coefficient != 0
            )
        else:
            source = (coerce_pauli_term(observable),)
        for term in source:
            unique.setdefault(term, None)
    return tuple(unique)


def reconstruct_observable_expvals_from_terms(
    observables: Iterable[PauliTerm | PauliSum | Mapping[int, str] | str],
    term_expvals: Mapping[PauliTerm, complex],
) -> list[complex]:
    """Reconstruct observable expectations from product-Pauli expectations."""
    values: list[complex] = []
    for observable in observables:
        pauli_sum = (
            observable
            if isinstance(observable, PauliSum)
            else PauliSum.from_terms(((1.0, observable),))
        )
        value = 0.0j
        for coefficient, term in pauli_sum.terms:
            try:
                value += coefficient * term_expvals[term]
            except KeyError as error:
                raise ValueError(
                    f"Missing expectation value for Pauli term {term!r}."
                ) from error
        values.append(value)
    return values


__all__ = [
    "PauliTerm",
    "PauliSum",
    "coerce_pauli_term",
    "normalize_observables",
    "qubitwise_commutes",
    "group_qubitwise_commuting",
    "gather_unique_observable_terms",
    "reconstruct_observable_expvals_from_terms",
]
