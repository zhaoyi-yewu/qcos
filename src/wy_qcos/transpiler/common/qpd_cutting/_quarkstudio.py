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

"""Optional QuarkStudio execution adapter for native wire-QPD fragments.

The QuarkStudio SDK is imported only when a
:class:`QuarkStudioFragmentEvaluator` is created, so using the exact NumPy
evaluator requires neither a QPU dependency nor Qiskit.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ._wire_cutting_workflow import FragmentExperiment


class QuarkStudioFragmentEvaluator:
    """Execute :class:`FragmentExperiment` objects through QuarkStudio.

    Instances implement the evaluator callable accepted by the wire-cutting
    execution functions.  The returned value includes both the product-Pauli
    observable and the terminal QPD measurement parity.
    """

    _task_manager: Any
    _chip: str
    _shots: int
    _poll_interval: float
    _submitted: int
    _total_submissions: int | None

    def __init__(
        self,
        token: str,
        chip: str,
        shots: int,
        *,
        poll_interval: float = 2.0,
        total_submissions: int | None = None,
    ) -> None:
        """Configure a QuarkStudio task manager for one chip and shot count.

        Args:
            token: Authentication token used to access QuarkStudio.
            chip: Name of the QuarkStudio chip used to run fragments.
            shots: Number of shots per fragment. It must be a positive
                multiple of 1024.
            poll_interval: Number of seconds between task status queries.
            total_submissions: Expected total number of submitted tasks,
                used only to report execution progress when provided.
        """
        if sys.version_info < (3, 12):
            raise RuntimeError(
                "QuarkStudio requires Python 3.12+; "
                f"this interpreter is Python {sys.version.split()[0]}."
            )
        if shots < 1024 or shots % 1024:
            raise ValueError(
                "QuarkStudio shots must be a positive multiple of 1024."
            )
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive.")
        if total_submissions is not None and total_submissions < 0:
            raise ValueError(
                "total_submissions must be non-negative when provided."
            )
        try:
            from quark import Task
        except ImportError as error:
            raise RuntimeError(
                "Install the QuarkStudio SDK with "
                "`pip install -U quarkstudio`."
            ) from error

        self._task_manager = Task(token)
        self._chip = chip
        self._shots = shots
        self._poll_interval = poll_interval
        self._submitted = 0
        self._total_submissions = total_submissions

    @property
    def submitted_tasks(self) -> int:
        """Return the submitted QuarkStudio task count."""
        return self._submitted

    def __call__(
        self, experiment: FragmentExperiment, observable: Mapping[int, str]
    ) -> float:
        """Measure one fragment response, including its terminal QPD parity."""
        no_qpu_response = self.non_qpu_response(experiment, observable)
        if no_qpu_response is not None:
            return no_qpu_response

        qasm, cbit_by_qubit = self._fragment_to_openqasm2(
            experiment, observable
        )
        self._submitted += 1
        counts = self._submit_and_wait(
            qasm, f"qpd-wire-fragment-{self._submitted}"
        )
        terminal_axes = dict(experiment.terminal_measurements)
        return self._correlated_expectation(
            counts, terminal_axes, observable, cbit_by_qubit
        )

    @staticmethod
    def non_qpu_response(
        experiment: FragmentExperiment, observable: Mapping[int, str]
    ) -> float | None:
        """Return a known response or ``None`` when a QPU is needed."""
        terminal_axes = dict(experiment.terminal_measurements)
        for qubit, pauli in observable.items():
            qpd_axis = terminal_axes.get(qubit)
            if qpd_axis is not None and qpd_axis != pauli:
                # The core evaluator evaluates (PQ + QP) / 2.  Different
                # one-qubit Paulis anticommute, so this response is zero.
                return 0.0
        if not terminal_axes and not observable:
            return 1.0
        return None

    @staticmethod
    def requires_submission(
        experiment: FragmentExperiment, observable: Mapping[int, str]
    ) -> bool:
        """Return whether this local response requires a real QPU task."""
        return (
            QuarkStudioFragmentEvaluator.non_qpu_response(
                experiment, observable
            )
            is None
        )

    def _submit_and_wait(self, qasm: str, name: str) -> Mapping[str, int]:
        """Submit an OpenQASM 2 fragment and wait for its counts."""
        task_started_at = time.perf_counter()
        progress = (
            str(self._total_submissions)
            if self._total_submissions is not None
            else "?"
        )
        print(
            f"[QuarkStudio] submitting task {self._submitted}/{progress}: "
            f"{name} "
            f"(chip={self._chip}, shots={self._shots})"
        )
        task_id = self._task_manager.run({
            "chip": self._chip,
            "name": name,
            "circuit": qasm,
            "shots": self._shots,
            "options": {"compiler": "quarkcircuit", "correct": False},
        })
        print(
            f"[QuarkStudio] task {self._submitted}/{progress} "
            f"submitted: id={task_id}"
        )
        while True:
            result = self._task_manager.result(task_id)
            status = result.get("status")
            if status == "Finished":
                counts = result["count"]
                print(
                    f"[QuarkStudio] task {self._submitted}/"
                    f"{progress} finished: "
                    f"{sum(counts.values())} returned shots, "
                    f"elapsed={time.perf_counter() - task_started_at:.2f}s"
                )
                return counts
            if status == "Failed":
                raise RuntimeError(
                    f"QuarkStudio task {task_id} failed: {result}"
                )
            time.sleep(self._poll_interval)

    @staticmethod
    def _fragment_to_openqasm2(
        experiment: FragmentExperiment, observable: Mapping[int, str]
    ) -> tuple[str, dict[int, int]]:
        """Serialize a QPD fragment and terminal measurements to QASM 2."""
        fragment = experiment.fragment
        lines = [
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            f"qreg q[{fragment.num_qubits}];",
        ]
        for qubit, state in sorted(experiment.preparations.items()):
            lines.extend(_qpd_preparation_qasm(qubit, state))
        for operation in fragment.operations:
            lines.extend(
                _operation_to_qasm(operation.matrix, operation.qubits)
            )

        axes = dict(experiment.terminal_measurements)
        axes.update(observable)
        measured_qubits = sorted(axes)
        lines.append(f"creg c[{len(measured_qubits)}];")
        for cbit, qubit in enumerate(measured_qubits):
            lines.extend(_pauli_measurement_qasm(qubit, axes[qubit], cbit))
        return "\n".join(lines), {
            qubit: cbit for cbit, qubit in enumerate(measured_qubits)
        }

    @staticmethod
    def _correlated_expectation(
        counts: Mapping[str, int],
        terminal_axes: Mapping[int, str],
        observable: Mapping[int, str],
        cbit_by_qubit: Mapping[int, int],
    ) -> float:
        """Convert OpenQASM big-endian counts to a correlated expectation."""
        total_shots = sum(counts.values())
        if total_shots <= 0:
            raise ValueError("QuarkStudio returned no measurement shots.")
        value = 0.0
        for bitstring, count in counts.items():
            bits = bitstring.replace(" ", "")
            # OpenQASM count strings put the highest classical bit on the
            # left.  Reverse them so outcomes[cbit] addresses c[cbit].
            if len(bits) != len(cbit_by_qubit) or set(bits) - {"0", "1"}:
                raise ValueError(
                    f"Unexpected QuarkStudio count key: {bitstring!r}."
                )
            outcomes = tuple(int(bit) for bit in reversed(bits))
            qpd_sign = np.prod([
                1 - 2 * outcomes[cbit_by_qubit[qubit]]
                for qubit in terminal_axes
            ])
            observable_sign = np.prod([
                1 - 2 * outcomes[cbit_by_qubit[qubit]] for qubit in observable
            ])
            value += count * qpd_sign * observable_sign / total_shots
        return float(value)


def _qpd_preparation_qasm(qubit: int, state: np.ndarray) -> list[str]:
    """Prepare one of the six standard wire-QPD states in OpenQASM 2."""
    known_states = {
        "zero": np.array([1, 0], dtype=complex),
        "one": np.array([0, 1], dtype=complex),
        "plus": np.array([1, 1], dtype=complex) / np.sqrt(2),
        "minus": np.array([1, -1], dtype=complex) / np.sqrt(2),
        "iplus": np.array([1, 1j], dtype=complex) / np.sqrt(2),
        "iminus": np.array([1, -1j], dtype=complex) / np.sqrt(2),
    }
    name = next(
        (
            name
            for name, known in known_states.items()
            if np.allclose(state, known)
        ),
        None,
    )
    operations = {
        "zero": (),
        "one": ("x",),
        "plus": ("h",),
        "minus": ("x", "h"),
        "iplus": ("h", "s"),
        "iminus": ("x", "h", "s"),
    }
    if name is None:
        raise ValueError(
            "The QPD state is not a supported wire-QPD basis state."
        )
    return [f"{operation} q[{qubit}];" for operation in operations[name]]


def _pauli_measurement_qasm(qubit: int, pauli: str, cbit: int) -> list[str]:
    """Rotate a Pauli measurement into OpenQASM's computational basis."""
    basis_change = {"X": ("h",), "Y": ("sdg", "h"), "Z": ()}
    if pauli not in basis_change:
        raise ValueError(f"Unsupported Pauli measurement axis: {pauli!r}.")
    return [
        *(f"{operation} q[{qubit}];" for operation in basis_change[pauli]),
        f"measure q[{qubit}] -> c[{cbit}];",
    ]


def _operation_to_qasm(matrix: np.ndarray, qubits: Sequence[int]) -> list[str]:
    """Serialize the native :class:`~.Circuit` gate set to OpenQASM 2."""
    matrix = np.asarray(matrix, dtype=complex)
    if len(qubits) == 1:
        qubit = qubits[0]
        known_gates = {
            "h": np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2),
            "x": np.array([[0, 1], [1, 0]], dtype=complex),
            "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
            "z": np.array([[1, 0], [0, -1]], dtype=complex),
        }
        for operation, expected in known_gates.items():
            if np.allclose(matrix, expected):
                return [f"{operation} q[{qubit}];"]
        for finder, operation in (
            (_rx_angle, "rx"),
            (_ry_angle, "ry"),
            (_rz_angle, "rz"),
        ):
            theta = finder(matrix)
            if theta is not None:
                return [f"{operation}({_number(theta)}) q[{qubit}];"]
    elif len(qubits) == 2:
        left, right = qubits
        known_gates = {
            "cx": np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 1],
                [0, 0, 1, 0],
            ]),
            "cz": np.diag([1, 1, 1, -1]),
            "swap": np.array([
                [1, 0, 0, 0],
                [0, 0, 1, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 1],
            ]),
        }
        for operation, expected in known_gates.items():
            if np.allclose(matrix, expected):
                return [f"{operation} q[{left}],q[{right}];"]
        theta = _rzz_angle(matrix)
        if theta is not None:
            # OpenQASM 2 qelib1 has no RZZ primitive; CX-RZ-CX implements
            # exp(-i theta Z⊗Z / 2) exactly.
            return [
                f"cx q[{left}],q[{right}];",
                f"rz({_number(theta)}) q[{right}];",
                f"cx q[{left}],q[{right}];",
            ]
    raise ValueError(
        "The QuarkStudio adapter supports Circuit's "
        "H/X/Y/Z/RX/RY/RZ/CX/CZ/SWAP/RZZ gates."
    )


def _rx_angle(matrix: np.ndarray) -> float | None:
    """Return the RX angle if ``matrix`` is RX, otherwise ``None``."""
    theta = 2 * np.arctan2(-matrix[0, 1].imag, matrix[0, 0].real)
    expected = np.array([
        [np.cos(theta / 2), -1j * np.sin(theta / 2)],
        [-1j * np.sin(theta / 2), np.cos(theta / 2)],
    ])
    return float(theta) if np.allclose(matrix, expected) else None


def _ry_angle(matrix: np.ndarray) -> float | None:
    """Return the RY angle if ``matrix`` is RY, otherwise ``None``."""
    theta = 2 * np.arctan2(matrix[1, 0].real, matrix[0, 0].real)
    expected = np.array([
        [np.cos(theta / 2), -np.sin(theta / 2)],
        [np.sin(theta / 2), np.cos(theta / 2)],
    ])
    return float(theta) if np.allclose(matrix, expected) else None


def _rz_angle(matrix: np.ndarray) -> float | None:
    """Return the RZ angle if ``matrix`` is RZ, otherwise ``None``."""
    if matrix.shape != (2, 2) or not np.allclose(
        matrix, np.diag(np.diag(matrix))
    ):
        return None
    theta = np.angle(matrix[1, 1] / matrix[0, 0])
    expected = np.diag([np.exp(-0.5j * theta), np.exp(0.5j * theta)])
    return float(theta) if np.allclose(matrix, expected) else None


def _rzz_angle(matrix: np.ndarray) -> float | None:
    """Return the RZZ angle if ``matrix`` is RZZ, otherwise ``None``."""
    if matrix.shape != (4, 4) or not np.allclose(
        matrix, np.diag(np.diag(matrix))
    ):
        return None
    theta = -2 * np.angle(matrix[0, 0])
    expected = np.diag([
        np.exp(-0.5j * theta),
        np.exp(0.5j * theta),
        np.exp(0.5j * theta),
        np.exp(-0.5j * theta),
    ])
    return float(theta) if np.allclose(matrix, expected) else None


def _number(value: float) -> str:
    """Format an angle without losing useful precision in OpenQASM text."""
    return format(value, ".16g")


__all__ = ["QuarkStudioFragmentEvaluator"]
