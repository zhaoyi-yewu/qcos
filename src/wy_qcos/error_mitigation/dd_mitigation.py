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

"""Dynamical decoupling (DD).

Inserts echo pulse sequences (XY4 or CPMG) into idle windows between
gates on qubits, suppressing decoherence during idle periods.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.common.cmss.base_operation import BaseOperation, OperationType
from wy_qcos.common.cmss.delay import Delay
from wy_qcos.error_mitigation.mitigation_base import MitigationBase

logger = logging.getLogger(__name__)

# Canonical dynamical-decoupling pulse sequences (axis labels).  These
# match the sequences offered by mitiq (mitiq/dd/dd_sequences.py) so that
# results are directly comparable.  "x"/"y" are echoed as single-qubit
# pi-pulses; an even-length sequence is a net identity (XY4, XY8) which
# refocuses dephasing without changing the logical state.
XY4_PULSES = ["x", "y", "x", "y"]
CPMG_PULSES = ["x", "x"]
XX_PULSES = ["x", "x"]
XY8_PULSES = ["x", "y", "x", "y", "y", "x", "y", "x"]
XXYX_PULSES = ["x", "x", "y", "x"]

# Supported named sequences (alias -> canonical pulse list).
_DD_SEQUENCES: dict[str, list[str]] = {
    "XX": XX_PULSES,
    "CPMG": CPMG_PULSES,
    "XY4": XY4_PULSES,
    "XY8": XY8_PULSES,
    "XXYX": XXYX_PULSES,
}


def udd_pulses(n: int) -> list[str]:
    """Build the n-th-order Uhrig DD pulse-axis sequence.

    The Uhrig sequence places n pulses at times ``t_k = t * sin^2(k*pi /
    (2*(n+1)))`` for ``k = 1..n``.  The *axis* pattern alternates y/x to
    suppress dephasing to n-th order; this implementation follows the
    convention used by mitiq (y-axis for odd n, x/y alternation otherwise).

    Args:
        n: Order of the UDD sequence (number of pulses), ``n >= 1``.

    Returns:
        List of ``n`` pulse-axis labels ("x"/"y").

    Raises:
        ValueError: If ``n < 1``.
    """
    if n < 1:
        raise ValueError(f"UDD order must be >= 1, got {n}")
    # mitiq uses Y for odd n, X/Y alternating for even n; we follow the same
    # axis choice so the timing (set by generate_dd_sequence below) is the
    # distinguishing feature.
    if n % 2 == 1:
        return ["y"] * n
    return [("y" if i % 2 == 0 else "x") for i in range(n)]


def _make_gate(name: str, qubit: int) -> GateOperation:
    """Create a single-qubit gate operation."""
    return GateOperation(
        name,
        targets=[qubit],
        operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
    )


def detect_idle_windows(
    operations: List[BaseOperation],
    num_qubits: int,
    gate_times: Dict[str, float],
    include_trailing: bool = False,
) -> Dict[int, List[Dict[str, float]]]:
    """Detect idle windows for each qubit.

    Walks the circuit building a per-qubit timeline (mitiq's approach):
    each qubit's clock advances when one of its gates runs; the gap
    between the previous gate's end and the next gate's start is an idle
    window.  ``barrier``/``sync`` act as global alignment points (all
    clocks jump to the latest), matching how hardware schedules them.

    Args:
        operations: List of gate operations in the circuit.
        num_qubits: Number of qubits.
        gate_times: Mapping from gate name to duration in microseconds.
        include_trailing: Also emit the idle window from each qubit's
            last gate up to the circuit end (max clock).  mitiq only
            fills idle time *before* a measurement, so the default is
            ``False`` for backwards compatibility.

    Returns:
        Dict mapping qubit index to list of idle windows, each with
        "start" and "duration" keys.
    """
    current_time = [0.0] * num_qubits
    idle_windows: Dict[int, List[Dict[str, float]]] = {
        q: [] for q in range(num_qubits)
    }

    for op in operations:
        if op.name in ("measure", "reset"):
            continue
        # barrier/sync align all qubit clocks to the latest, a global
        # scheduling point (no idle window recorded across the barrier).
        if op.name in ("sync", "barrier"):
            if op.targets:
                latest = max(current_time[q] for q in op.targets)
                for q in op.targets:
                    current_time[q] = latest
            else:
                latest = max(current_time)
                current_time = [latest] * num_qubits
            continue
        if not op.targets:
            continue

        gate_duration = gate_times.get(op.name, gate_times.get("default", 0.0))
        start = max(current_time[q] for q in op.targets)

        for q in op.targets:
            gap = start - current_time[q]
            if gap > 0:
                idle_windows[q].append({
                    "start": current_time[q],
                    "duration": gap,
                })
            current_time[q] = start + gate_duration

    if include_trailing:
        end = max(current_time)
        for q in range(num_qubits):
            trailing = end - current_time[q]
            if trailing > 1e-9:
                idle_windows[q].append({
                    "start": current_time[q],
                    "duration": trailing,
                })

    return idle_windows


def generate_dd_sequence(
    idle_duration: float,
    sequence: str,
    gate_times: Dict[str, float],
    qubit: int,
) -> List[BaseOperation]:
    """Generate a DD pulse sequence filling an idle window.

    The window is bookended by free-evolution delays, with the pulse axes
    determined by the chosen ``sequence``.  Named sequences (XX, CPMG,
    XY4, XY8, XXYX) distribute their pulses at *equal* spacing (CPMG
    convention); ``UDDn`` uses the Uhrig non-uniform spacing
    ``t_k = sin^2(k*pi/(2*(n+1)))``, which suppresses dephasing to n-th
    order.

    Args:
        idle_duration: Duration of the idle window in microseconds.
        sequence: One of "XX", "CPMG", "XY4", "XY8", "XXYX", or
            "UDD<n>" (e.g. "UDD8") for n-th-order Uhrig DD.
        gate_times: Gate duration mapping; uses "x" or "default".
        qubit: Target qubit index.

    Returns:
        List of operations (Delay + pi-pulses) spanning the window, or an
        empty list if the window is too short to hold the pulses.
    """
    pulses = _resolve_sequence(sequence)
    n = len(pulses)
    pulse_duration = gate_times.get("x", gate_times.get("default", 0.02))
    total_pulse_time = n * pulse_duration

    if idle_duration <= total_pulse_time:
        return []

    free_time = idle_duration - total_pulse_time

    # Pulse *centres* relative to window start, as a fraction of the
    # total window.  Equal spacing for named sequences; Uhrig spacing for
    # UDD.  mitiq places the k-th pulse centre at the k-th fraction.
    if sequence.upper().startswith("UDD"):
        order = n
        centres_frac = [
            (np.sin(np.pi * k / (2 * (order + 1)))) ** 2
            for k in range(1, order + 1)
        ]
    else:
        centres_frac = [(k + 0.5) / n for k in range(n)]

    # Convert centre fractions to absolute times within the window, then
    # interleave Delay + pulse so the emitted op stream reproduces them.
    centres = [c * idle_duration for c in centres_frac]
    ops: List[BaseOperation] = []
    prev_edge = 0.0
    for k, gate_name in enumerate(pulses):
        pulse_start = centres[k] - pulse_duration / 2.0
        pre_delay = pulse_start - prev_edge
        if pre_delay > 0:
            ops.append(_make_delay(pre_delay, qubit))
        ops.append(_make_gate(gate_name, qubit))
        prev_edge = pulse_start + pulse_duration
    # trailing free evolution
    trailing = idle_duration - prev_edge
    if trailing > 1e-12:
        ops.append(_make_delay(trailing, qubit))
    return ops


def _resolve_sequence(sequence: str) -> list[str]:
    """Map a sequence name (incl. ``UDD<n>``) to a pulse-axis list."""
    name = sequence.upper()
    if name.startswith("UDD"):
        try:
            order = int(name[3:])
        except ValueError as exc:
            raise ValueError(
                f"Invalid UDD sequence '{sequence}', expected UDD<n>"
            ) from exc
        return udd_pulses(order)
    if name in _DD_SEQUENCES:
        return list(_DD_SEQUENCES[name])
    logger.warning("Unknown DD sequence '%s', using XY4", sequence)
    return list(XY4_PULSES)


def _make_delay(duration: float, qubit: int) -> Delay:
    """Create a Delay instruction targeted on ``qubit``."""
    d = Delay(duration=duration)
    d.targets = [qubit]
    return d


def insert_dd_into_circuit(
    circuit: QuantumCircuit,
    sequence: str = "XY4",
    gate_times: Optional[Dict[str, float]] = None,
) -> Tuple[QuantumCircuit, Dict[str, Any]]:
    """Insert DD sequences into idle windows of a circuit.

    Args:
        circuit: The transpiled quantum circuit.
        sequence: "XY4" or "CPMG".
        gate_times: Gate duration mapping. If None, DD is skipped.

    Returns:
        Tuple of (new_circuit_with_dd, metadata).
    """
    if gate_times is None:
        logger.warning("No gate timing data, skipping DD")
        return circuit, {"dd_applied": False, "reason": "no_gate_times"}

    operations = circuit.get_operations()
    num_qubits = circuit.num_qubits
    idle_windows = detect_idle_windows(operations, num_qubits, gate_times)

    min_pulse_time = gate_times.get("x", gate_times.get("default", 0.02))
    min_idle = 4 * min_pulse_time

    dd_insertions: Dict[int, List[Tuple[float, List[BaseOperation]]]] = {
        q: [] for q in range(num_qubits)
    }
    windows_filled = 0

    for q, windows in idle_windows.items():
        for window in windows:
            if window["duration"] >= min_idle:
                dd_ops = generate_dd_sequence(
                    window["duration"], sequence, gate_times, q
                )
                if dd_ops:
                    dd_insertions[q].append((window["start"], dd_ops))
                    windows_filled += 1

    if windows_filled == 0:
        return circuit, {
            "dd_applied": False,
            "reason": "no_suitable_idle_windows",
            "windows_detected": sum(len(w) for w in idle_windows.values()),
        }

    new_ops: List[BaseOperation] = []
    current_time = [0.0] * num_qubits
    inserted_at: Dict[int, set] = {q: set() for q in range(num_qubits)}

    for op in operations:
        if op.name in ("measure", "reset"):
            new_ops.append(op)
            continue
        # barrier/sync align clocks (must match detect_idle_windows so the
        # DD insertion times line up with the detected windows).
        if op.name in ("sync", "barrier"):
            new_ops.append(op)
            if op.targets:
                latest = max(current_time[q] for q in op.targets)
                for q in op.targets:
                    current_time[q] = latest
            else:
                latest = max(current_time)
                current_time = [latest] * num_qubits
            continue
        if not op.targets:
            new_ops.append(op)
            continue

        gate_duration = gate_times.get(op.name, gate_times.get("default", 0.0))
        op_start = max(current_time[q] for q in op.targets)

        for q in op.targets:
            gap_start = current_time[q]
            for ins_start, ins_ops in dd_insertions[q]:
                ins_key = ins_start
                if (
                    ins_key not in inserted_at[q]
                    and ins_start >= gap_start - 1e-9
                    and ins_start < op_start - 1e-9
                ):
                    new_ops.extend(ins_ops)
                    inserted_at[q].add(ins_key)

            current_time[q] = op_start + gate_duration

        new_ops.append(op)

    for q in range(num_qubits):
        for ins_start, ins_ops in dd_insertions[q]:
            if ins_start not in inserted_at[q]:
                new_ops.extend(ins_ops)

    new_circuit = QuantumCircuit.from_ir(new_ops, num_qubits)
    metadata = {
        "dd_applied": True,
        "sequence": sequence,
        "windows_filled": windows_filled,
        "depth_original": circuit.depth(),
        "depth_new": new_circuit.depth(),
    }
    return new_circuit, metadata


class DDMitigation(MitigationBase):
    """Dynamical decoupling mitigation technique.

    Inserts echo pulse sequences into idle windows to suppress
    decoherence.
    """

    def __init__(
        self,
        sequence: str = "XY4",
        gate_times: Optional[Dict[str, float]] = None,
    ):
        """Initialize DD mitigation.

        Args:
            sequence: "XY4" or "CPMG".
            gate_times: Gate duration mapping in microseconds.
        """
        super().__init__("dd")
        self._sequence = sequence
        self._gate_times = gate_times

    def set_config(self, config: Dict[str, Any]) -> None:
        super().set_config(config)
        self._sequence = config.get("sequence", self._sequence)

    def validate_device(self, device_config: Dict[str, Any]) -> tuple:
        gate_times = device_config.get("gate_times")
        if not gate_times:
            em_config = device_config.get("error_mitigation", {})
            dd_config = em_config.get("dd", {})
            gate_times = dd_config.get("gate_times")
        if not gate_times:
            return (
                False,
                "DD requires gate timing configuration for device. "
                "Add [error_mitigation.dd] gate_times to device config.",
            )
        return (True, None)

    def transform_circuit(
        self, circuit: QuantumCircuit
    ) -> List[Dict[str, Any]]:
        """Insert DD sequences into the circuit.

        DD is applied at the circuit level (before execution).
        The result is a single modified circuit.

        Args:
            circuit: The transpiled quantum circuit.

        Returns:
            List with one circuit variant containing DD sequences.
        """
        gate_times = self._gate_times or self._config.get("gate_times")
        new_circuit, dd_metadata = insert_dd_into_circuit(
            circuit, self._sequence, gate_times
        )
        return [
            {
                "label": "original",
                "circuit": new_circuit,
                "scale_factor": 1,
                "dd_metadata": dd_metadata,
            }
        ]

    def postprocess(
        self,
        results: Dict[str, Dict[str, int]],
        calibration: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """DD post-processing (passthrough).

        DD modifies the circuit before execution, so no result
        post-processing is needed.

        Args:
            results: Measurement counts.
            calibration: Not used.

        Returns:
            Results unchanged.
        """
        return {
            "results": results,
            "metadata": {
                "technique": "dd",
                "applied": True,
                "note": "DD applied at circuit level, no post-processing",
            },
        }
