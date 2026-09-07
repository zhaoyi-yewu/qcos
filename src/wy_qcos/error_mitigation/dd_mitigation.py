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

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.common.cmss.base_operation import BaseOperation, OperationType
from wy_qcos.common.cmss.delay import Delay
from wy_qcos.error_mitigation.mitigation_base import MitigationBase

logger = logging.getLogger(__name__)

XY4_PULSES = ["x", "y", "x", "y"]
CPMG_PULSES = ["x", "x"]


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
) -> Dict[int, List[Dict[str, float]]]:
    """Detect idle windows for each qubit.

    Analyzes the circuit to find periods where each qubit has no gate
    applied, based on gate timing information.

    Args:
        operations: List of gate operations in the circuit.
        num_qubits: Number of qubits.
        gate_times: Mapping from gate name to duration in microseconds.

    Returns:
        Dict mapping qubit index to list of idle windows, each with
        "start" and "duration" keys.
    """
    current_time = [0.0] * num_qubits
    idle_windows: Dict[int, List[Dict[str, float]]] = {
        q: [] for q in range(num_qubits)
    }

    for op in operations:
        if op.name in ("sync", "barrier", "measure", "reset"):
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

    return idle_windows


def generate_dd_sequence(
    idle_duration: float,
    sequence: str,
    gate_times: Dict[str, float],
    qubit: int,
) -> List[BaseOperation]:
    """Generate DD pulse sequence for an idle window.

    Args:
        idle_duration: Duration of the idle window in microseconds.
        sequence: "XY4" or "CPMG".
        gate_times: Gate duration mapping.
        qubit: Target qubit index.

    Returns:
        List of operations forming the DD sequence.
    """
    if sequence == "XY4":
        pulses = XY4_PULSES
    elif sequence == "CPMG":
        pulses = CPMG_PULSES
    else:
        logger.warning("Unknown DD sequence '%s', using XY4", sequence)
        pulses = XY4_PULSES

    pulse_duration = gate_times.get("x", gate_times.get("default", 0.02))
    total_pulse_time = len(pulses) * pulse_duration

    if idle_duration <= total_pulse_time:
        return []

    num_delays = len(pulses) + 1
    delay_each = (idle_duration - total_pulse_time) / num_delays

    ops: List[BaseOperation] = []
    for gate_name in pulses:
        if delay_each > 0:
            d = Delay(duration=delay_each)
            d.targets = [qubit]
            ops.append(d)
        ops.append(_make_gate(gate_name, qubit))

    if delay_each > 0:
        d = Delay(duration=delay_each)
        d.targets = [qubit]
        ops.append(d)

    return ops


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
        if op.name in ("sync", "barrier", "measure", "reset"):
            new_ops.append(op)
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
