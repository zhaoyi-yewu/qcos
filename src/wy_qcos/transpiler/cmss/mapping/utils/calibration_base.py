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
"""Fidelity calibration base class.

Defines the full pipeline: parse calibration data -> graph scheduling ->
circuit construction -> batch submit -> collect results -> extract ->
write TOML. Subclasses implement platform-specific abstract methods.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EdgeResult:
    """Measured result for a single edge.

    qubit_a: Control qubit index.
    qubit_b: Target qubit index.
    measured_fid: Measured fidelity, None if unavailable.
    """

    qubit_a: int
    qubit_b: int
    measured_fid: float | None = None


@dataclass
class QubitResult:
    """Measured result for a single qubit.

    qubit: Qubit index.
    measured_fid: Measured fidelity ((P0+P1)/2), None if unavailable.
    """

    qubit: int
    measured_fid: float | None = None


@dataclass
class CircuitTask:
    """A circuit task ready for submission (QASM + measurement map).

    qasm: OPENQASM 2.0 circuit text.
    bit_map: {qubit_id: classical_bit_index} mapping.
    """

    qasm: str
    bit_map: dict[int, int]


def extract_prob(
    counts: dict,
    bit_positions: list[int],
    target: str,
    n_bits: int,
) -> float:
    """Extract probability of specific bit positions matching target.

    c[0] corresponds to the rightmost character of the state string
    (standard OPENQASM convention).

    Args:
        counts: Measurement result dict {state: count}.
        bit_positions: Classical bit positions to check, e.g. [0, 1].
        target: Expected value, e.g. "11" (order matches
            bit_positions).
        n_bits: Total number of bits, for zero-padding.

    Returns:
        Probability of the specified bits matching target.

    Raises:
        ValueError: If len(bit_positions) != len(target).

    Examples:
        >>> # Probability of bits 0 and 1 both being "1"
        >>> extract_prob(counts, [0, 1], "11", 4)
        >>> # Probability of bit 3 being "0"
        >>> extract_prob(counts, [3], "0", 4)
    """
    if len(bit_positions) != len(target):
        raise ValueError(
            f"bit_positions length ({len(bit_positions)}) "
            f"!= target length ({len(target)})"
        )
    total = sum(int(c) for c in counts.values()) or 1
    count_target = 0
    for state, count in counts.items():
        state = str(state).replace(" ", "").zfill(n_bits)
        bits = "".join(state[-(pos + 1)] for pos in bit_positions)
        if bits == target:
            count_target += int(count)
    return count_target / total


def _edge_qubits(edges: list[tuple[int, int]]) -> set[int]:
    """Extract all qubit indices involved in the edge list.

    Args:
        edges: Edge list [(u, v), ...].

    Returns:
        Set of all qubit indices appearing in any edge.
    """
    return {q for e in edges for q in e[:2]}


def _fmt_err(fid: float | None) -> float:
    """Format fidelity as error rate (1 - fid).

    None becomes 1.0 (fully broken).
    """
    return round(1 - fid, 4) if fid is not None else 1.0


def write_fidelity_toml(
    edge_results: list[EdgeResult],
    qubit_results: list[QubitResult],
    chip: str,
    qreg_size: int,
    driver: str,
    alias: str | None = None,
    output_dir: str = ".",
) -> str:
    """Write measured fidelities to a .toml file.

    Output format matches etc/topology/``*.toml``:
    - Inline dotted keys (coupler_map.CZ0_1 = ['Q0', 'Q1'])
    - Error rates (1 - fidelity), single quotes for strings
    - Directed edges merged into undirected couplers (avg)

    Args:
        edge_results: Edge measurement results.
        qubit_results: Qubit measurement results.
        chip: Chip name (used for section key and file name).
        qreg_size: Number of qubits.
        driver: Platform driver name (e.g. "DriverQuafu").
        alias: Display name for alias_name/description. Defaults to chip.
        output_dir: Output directory.

    Returns:
        Output file path.
    """
    if alias is None:
        alias = chip

    # Merge directed edges into undirected coupler pairs
    coupler_fids: dict[tuple[int, int], list[float]] = {}
    for r in edge_results:
        pair = (
            min(r.qubit_a, r.qubit_b),
            max(r.qubit_a, r.qubit_b),
        )
        if pair not in coupler_fids:
            coupler_fids[pair] = []
        if r.measured_fid is not None:
            coupler_fids[pair].append(r.measured_fid)

    chip_key = chip.lower()
    out: list[str] = []
    out.append(f"[{chip_key}]")
    out.append(f'alias_name = "{alias}"')
    out.append(f'driver = "{driver}"')
    out.append(f'description = "{alias}"')
    out.append("")

    section = f"{chip_key}.transpiler.qpu_configs"
    out.append(f"[{section}]")
    out.append("")
    out.append(f"qubits = {qreg_size}")
    out.append("")

    for u, v in sorted(coupler_fids):
        out.append(f"coupler_map.CZ{u}_{v} = ['Q{u}', 'Q{v}']")
    out.append("")

    for qr in sorted(qubit_results, key=lambda x: x.qubit):
        out.append(f"readout_error.Q{qr.qubit} = {_fmt_err(qr.measured_fid)}")
    out.append("")

    for (u, v), fids in sorted(coupler_fids.items()):
        avg_fid = sum(fids) / len(fids) if fids else None
        out.append(f"coupler_error.CZ{u}_{v} = {_fmt_err(avg_fid)}")
    out.append("")

    ts = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    output_path = f"{output_dir}/{chip}_fidelity_{ts}.toml"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"  Saved: {output_path}")
    return output_path


class FidelityCalibrator(ABC):
    """Fidelity calibration base class.

    Pipeline:
        1. Parse calibration data (load_calibration) -> edges,
           qubit_list, qreg_size.
        2. Schedule: group vertex-disjoint edges into batches
           (plan_edge_groups), plan measure / x+measure qubit
           groups (plan_qubit_groups).
        3. Build OPENQASM circuits for each group.
        4. Batch submit all circuits, non-blocking (submit).
        5. Collect results and extract per-edge ``P(|11>)`` and
           per-qubit P(0) / P(1) from counts (wait_result).
        6. Compute qubit fidelity = (P0 + P1) / 2.
        7. Write error rates (1 - fid) to a TOML file.

    Subclass implements:
        - load_calibration: parse platform calibration data.
        - submit: submit a circuit, return task_id.
        - wait_result: poll until task completes, return result.
    """

    chip: str
    driver: str
    submit_interval: float
    output_dir: str
    _calibration_cache: tuple | None

    @abstractmethod
    def load_calibration(
        self,
    ) -> tuple[
        list[tuple[int, int]],
        list[tuple[int, float]],
        int,
    ]:
        """Parse calibration data, return (edges, qubit_list, qreg_size).

        Called only once; the base class caches the result.

        Returns:
            (edges, qubit_list, qreg_size) tuple.
        """

    @property
    def calibration(
        self,
    ) -> tuple[
        list[tuple[int, int]],
        list[tuple[int, float]],
        int,
    ]:
        """Get cached calibration data.

        Lazy-loaded on first access.
        """
        if self._calibration_cache is None:
            self._calibration_cache = self.load_calibration()
        return self._calibration_cache

    @abstractmethod
    def submit(self, name: str, qasm: str) -> int:
        """Submit a circuit, return task_id immediately (non-blocking).

        Args:
            name: Task name.
            qasm: OPENQASM 2.0 circuit text.

        Returns:
            Platform-specific task identifier (task_id).
        """

    @abstractmethod
    def wait_result(self, task_id: int) -> dict:
        """Poll until task_id completes, return result dict.

        Args:
            task_id: Task identifier returned by submit().

        Returns:
            Result dict containing at least 'count' (measurement counts).

        Raises:
            RuntimeError: Task entered a failed terminal state.
            TimeoutError: Task did not complete within timeout.
        """

    def plan_edge_groups(
        self, edges: list[tuple[int, int]]
    ) -> list[list[tuple[int, int]]]:
        """Group edges by vertex-disjoint principle (greedy coloring).

        Edges in the same group share no physical qubits, so they
        can be tested simultaneously in a single circuit.

        Args:
            edges: All valid edges [(u, v), ...].

        Returns:
            List of groups, each being a list of vertex-disjoint edges.
        """
        groups: list[list[tuple[int, int]]] = []
        for edge in edges:
            u, v = edge
            placed = False
            for group in groups:
                used = {q for e in group for q in e[:2]}
                if u not in used and v not in used:
                    group.append(edge)
                    placed = True
                    break
            if not placed:
                groups.append([edge])
        return groups

    def plan_qubit_groups(
        self, qubit_list: list[tuple[int, float]]
    ) -> list[tuple[list[int], bool]]:
        """Group qubits into 2 batches: measure and x+measure.

        Dead qubits (old_fid <= 0) are filtered out here.

        Args:
            qubit_list: All qubits [(qid, fid), ...].

        Returns:
            List of (qubit_list, apply_x) tuples. apply_x=False
            means direct measurement, apply_x=True means X gate
            then measure. Empty list if no alive qubits.
        """
        alive_qubits = [qid for qid, fid in qubit_list if fid > 0]
        if not alive_qubits:
            return []
        return [
            (alive_qubits, False),
            (alive_qubits, True),
        ]

    def build_edge_circuit(
        self,
        edges: list[tuple[int, int]],
        qreg_size: int,
    ) -> CircuitTask:
        """Build a CX test circuit for a group of edges.

        Each edge: X(control) -> CX(control, target). All involved qubits are
        measured together. Edges must be vertex-disjoint (guaranteed by
        plan_edge_groups).

        Args:
            edges: List of vertex-disjoint edges [(u, v), ...].
            qreg_size: qreg size.

        Returns:
            CircuitTask (QASM + bit_map).
        """
        bits = sorted(_edge_qubits(edges))
        bit_map = {qubit: clbit for clbit, qubit in enumerate(bits)}
        n_bits = len(bits)
        lines = [
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            f"qreg q[{qreg_size}];",
            f"creg c[{n_bits}];",
        ]
        for u, v in edges:
            lines.append(f"x q[{u}];")
            lines.append(f"cx q[{u}],q[{v}];")
        for qubit in bits:
            lines.append(f"measure q[{qubit}] -> c[{bit_map[qubit]}];")
        return CircuitTask(qasm="\n".join(lines) + "\n", bit_map=bit_map)

    def build_qubit_circuit(
        self,
        qubit_list: list[int],
        apply_x: bool,
        qreg_size: int,
    ) -> CircuitTask:
        """Build a qubit measurement circuit (measure / x+measure).

        Args:
            qubit_list: Qubit indices to measure.
            apply_x: If True, apply X gate to each qubit before
                measure.
            qreg_size: qreg size.

        Returns:
            CircuitTask (QASM + bit_map).
        """
        bit_map = {qubit: clbit for clbit, qubit in enumerate(qubit_list)}
        n_bits = len(qubit_list)
        lines = [
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            f"qreg q[{qreg_size}];",
            f"creg c[{n_bits}];",
        ]
        if apply_x:
            for qubit in qubit_list:
                lines.append(f"x q[{qubit}];")
        for qubit in qubit_list:
            lines.append(f"measure q[{qubit}] -> c[{bit_map[qubit]}];")
        return CircuitTask(qasm="\n".join(lines) + "\n", bit_map=bit_map)

    def extract_edge_fids(
        self,
        edges: list[tuple[int, int]],
        circuit_task: CircuitTask,
        counts: dict,
    ) -> dict[tuple[int, int], float]:
        """Extract ``P(|11>)`` for each edge from combined counts.

        Args:
            edges: Edges contained in this circuit.
            circuit_task: Circuit task (with bit_map).
            counts: Measurement counts from the real machine.

        Returns:
            {(qubit_a, qubit_b): ``P(|11>)``} mapping.
        """
        result = {}
        n_bits = len(circuit_task.bit_map)
        for u, v in edges:
            clbit_u = circuit_task.bit_map[u]
            clbit_v = circuit_task.bit_map[v]
            result[(u, v)] = extract_prob(
                counts, [clbit_u, clbit_v], "11", n_bits
            )
        return result

    def extract_qubit_probs(
        self,
        qubit_list: list[int],
        apply_x: bool,
        circuit_task: CircuitTask,
        counts: dict,
    ) -> dict[int, float]:
        """Extract P(target) for each qubit from counts.

        target="1" when apply_x=True (X gate should produce ``|1>``),
        target="0" when apply_x=False (ground state should be ``|0>``).

        Args:
            qubit_list: Qubit indices in this circuit.
            apply_x: Whether X gate was applied.
            circuit_task: Circuit task (with bit_map).
            counts: Measurement counts from the real machine.

        Returns:
            {qubit_id: P(target)} mapping.
        """
        result = {}
        target = "1" if apply_x else "0"
        n_bits = len(circuit_task.bit_map)
        for qubit in qubit_list:
            clbit = circuit_task.bit_map[qubit]
            result[qubit] = extract_prob(counts, [clbit], target, n_bits)
        return result

    def _submit_all(
        self,
        edge_groups: list[list[tuple[int, int]]],
        qubit_groups: list[tuple[list[int], bool]],
        qreg_size: int,
    ) -> list[tuple]:
        """Phase 1: Build circuits + batch submit (non-blocking).

        Args:
            edge_groups: Edge groups from plan_edge_groups.
            qubit_groups: Qubit groups from plan_qubit_groups.
            qreg_size: qreg size.

        Returns:
            List of (kind, data, circuit_task, task_id).
        """
        pending: list[tuple] = []

        for idx, edge_list in enumerate(edge_groups):
            circuit_task = self.build_edge_circuit(edge_list, qreg_size)
            name = f"edge_{idx}"
            task_id = self.submit(name, circuit_task.qasm)
            pending.append(("edge", edge_list, circuit_task, task_id))
            time.sleep(self.submit_interval)

        for alive_qubits, apply_x in qubit_groups:
            circuit_task = self.build_qubit_circuit(
                alive_qubits, apply_x, qreg_size
            )
            name = "x_all" if apply_x else "measure_all"
            task_id = self.submit(name, circuit_task.qasm)
            pending.append((
                "qubit",
                (alive_qubits, apply_x),
                circuit_task,
                task_id,
            ))
            time.sleep(self.submit_interval)

        return pending

    def _collect_all(
        self, pending: list[tuple]
    ) -> tuple[list[EdgeResult], dict[int, float], dict[int, float]]:
        """Phase 2: Collect results + extract per-edge/qubit.

        Args:
            pending: List from _submit_all.

        Returns:
            (edge_results, measure_probs, x_probs).
        """
        edge_results: list[EdgeResult] = []
        measure_probs: dict[int, float] = {}
        x_probs: dict[int, float] = {}

        for i, (
            kind,
            data,
            circuit_task,
            task_id,
        ) in enumerate(pending, 1):
            try:
                raw = self.wait_result(task_id)
                counts = raw.get("count") or {}
            except Exception as exc:
                print(f"  [{i}/{len(pending)}] {kind} err: {exc}")
                counts = {}

            if kind == "edge":
                fids = self.extract_edge_fids(data, circuit_task, counts)
                for u, v in data:
                    fid = fids.get((u, v))
                    edge_results.append(EdgeResult(u, v, fid))
                    if fid is not None:
                        print(
                            f"  [{i}/{len(pending)}] "
                            f"Q[{u}]-Q[{v}] fid={fid:.4f}"
                        )
            else:
                alive_qubits, apply_x = data
                probs = self.extract_qubit_probs(
                    alive_qubits,
                    apply_x,
                    circuit_task,
                    counts,
                )
                if apply_x:
                    x_probs = probs
                else:
                    measure_probs = probs
                for qid in alive_qubits:
                    val = probs.get(qid, 0)
                    print(
                        f"  [{i}/{len(pending)}] {kind} Q[{qid}] P={val:.4f}"
                    )

        return edge_results, measure_probs, x_probs

    def _compute_qubit_fids(
        self,
        qubit_list: list[tuple[int, float]],
        measure_probs: dict[int, float],
        x_probs: dict[int, float],
    ) -> list[QubitResult]:
        """Compute qubit fidelities: fid = (P0 + P1) / 2.

        Dead qubits (old_fid <= 0) get fid=0.0.

        Args:
            qubit_list: All qubits [(qid, old_fid), ...].
            measure_probs: ``P(|0>)`` per qubit (no X gate).
            x_probs: ``P(|1>)`` per qubit (with X gate).

        Returns:
            List of QubitResult.
        """
        results: list[QubitResult] = []
        for qid, old_fid in qubit_list:
            if old_fid <= 0:
                results.append(QubitResult(qid, 0.0))
                continue
            fid = None
            if measure_probs or x_probs:
                fid = (measure_probs.get(qid, 0) + x_probs.get(qid, 0)) / 2
                print(
                    f"  Q[{qid}] "
                    f"P(0)={measure_probs.get(qid, 0):.4f} "
                    f"P(1)={x_probs.get(qid, 0):.4f} "
                    f"fid={fid:.4f}"
                )
            results.append(QubitResult(qid, fid))
        return results

    def run(self) -> str:
        """Entry point: parse -> schedule -> submit -> collect.

        Returns:
            TOML output file path.
        """
        edges, qubit_list, qreg_size = self.calibration
        print(
            f"Chip: {self.chip}, edges: {len(edges)}, "
            f"qubits: {len(qubit_list)}, qreg: {qreg_size}"
        )

        edge_groups = self.plan_edge_groups(edges)
        qubit_groups = self.plan_qubit_groups(qubit_list)
        print(f"Edge groups: {len(edges)} edges -> {len(edge_groups)} groups")

        pending = self._submit_all(edge_groups, qubit_groups, qreg_size)
        print(f"Submitted {len(pending)} tasks, collecting...")

        edge_results, measure_probs, x_probs = self._collect_all(pending)
        qubit_results = self._compute_qubit_fids(
            qubit_list, measure_probs, x_probs
        )

        return write_fidelity_toml(
            edge_results=edge_results,
            qubit_results=qubit_results,
            chip=self.chip,
            qreg_size=qreg_size,
            driver=self.driver,
            output_dir=self.output_dir,
        )
