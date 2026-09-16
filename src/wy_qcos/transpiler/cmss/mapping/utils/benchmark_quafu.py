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
"""Quafu circuit benchmark.

Batch-tests circuit fidelity on a Quafu chip: verify -> compile ->
batch submit -> collect -> compute classical fidelity.  Uses a TOML
file (from calibration_quafu.py) as the chip data source.
"""

from __future__ import annotations

import math
import os
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from quark import Task
from qiskit.qasm2 import (
    loads as qasm2_loads,
    LEGACY_CUSTOM_INSTRUCTIONS,
)
from qiskit.quantum_info import Statevector

from wy_qcos.transpiler.high_performance import (  # type: ignore[attr-defined]
    QuafuVerifier,
    VerifyParams,
    qasm_to_ir,
    to_qasm2,
    transpile_from_qasm,
)

BASIS_GATES = ["u", "cz"]


def _parse_opt_level(compiler: str) -> int | None:
    """Return opt_level if compiler is a local compiler, else None.

    Local compiler names use the format ``level{N}``,
    e.g. ``level0`` or ``level3``.

    Args:
        compiler: Compiler name from the compilers list.

    Returns:
        Optimization level (0-3), or None for server-side compilers.
    """
    prefix = "level"
    if compiler.startswith(prefix):
        try:
            return int(compiler[len(prefix) :])
        except ValueError:
            return None
    return None


@dataclass
class ChipData:
    """Parsed chip data from TOML file."""

    coupling_list: list[tuple[int, int]]
    edge_fidelities: list[float]
    single_qubit_fidelities: list[float]


def load_toml_chip(toml_path: str) -> ChipData:
    """Parse a TOML calibration file into ChipData.

    The TOML format (from calibration_quafu.py) stores
    error rates (1 - fidelity), converted back to fidelities here.

    Args:
        toml_path: Path to the TOML file.

    Returns:
        ChipData with coupling_list, edge_fidelities, and
        single_qubit_fidelities.
    """
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    chip_key = next(iter(data))
    configs = data[chip_key]["transpiler"]["qpu_configs"]
    qreg_size = configs["qubits"]

    coupler_map = configs.get("coupler_map", {})
    coupler_error = configs.get("coupler_error", {})
    readout_error = configs.get("readout_error", {})

    coupling_list: list[tuple[int, int]] = []
    edge_fidelities: list[float] = []
    for key, qubits in sorted(coupler_map.items()):
        u = int(qubits[0][1:])
        v = int(qubits[1][1:])
        coupling_list.append((u, v))
        err = coupler_error.get(key, 1)
        edge_fidelities.append(float(1 - err))

    single_qubit_fidelities = [0.0] * qreg_size
    for key, err in readout_error.items():
        qid = int(key[1:])
        if qid < qreg_size:
            single_qubit_fidelities[qid] = float(1 - err)

    return ChipData(
        coupling_list=coupling_list,
        edge_fidelities=edge_fidelities,
        single_qubit_fidelities=single_qubit_fidelities,
    )


@dataclass
class RunResult:
    """Result of running a circuit on the hardware."""

    fidelity: float | None = None
    error: str | None = None
    gate_count: int | None = None
    depth: int | None = None
    two_qubit_count: int | None = None


@dataclass
class CircuitEntry:
    """Test status and results for a single circuit.

    Example: for circuit file "grover.qasm" tested with
    compilers ["level0", "level3"], a fully-passed entry looks
    like::

        CircuitEntry(
            circuit="grover",
            qasm_path=Path("/data/grover.qasm"),
            verify_error=None,
            ideal_error=None,
            run_results={
                "level0": RunResult(fidelity=0.95),
                "level3": RunResult(fidelity=0.98),
            },
        )
    """

    circuit: str
    qasm_path: Path
    verify_error: str | None = None
    ideal_error: str | None = None
    run_results: dict[str, RunResult] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Whether the circuit passed pre-verification."""
        return self.verify_error is None


def compute_ideal(qasm: str) -> dict[str, float]:
    """Compute ideal probability distribution.

    Uses Qiskit Statevector to simulate the circuit without measurement.
    If only a subset of qubits is measured (creg < qreg), the
    distribution is marginalized to the measured qubits so that
    state strings match the hardware measurement results.

    Args:
        qasm: OPENQASM 2.0 circuit text.

    Returns:
        Dict {state: probability}.
    """
    circ = qasm2_loads(
        qasm,
        custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS,
    )
    # Parse measurement instructions to find which qubits map to
    # which classical bits, sorted by classical bit index.
    measured_pairs: list[tuple[int, int]] = []
    for inst in circ.data:
        if inst.operation.name == "measure":
            q_idx = circ.qubits.index(inst.qubits[0])
            c_idx = circ.clbits.index(inst.clbits[0])
            measured_pairs.append((q_idx, c_idx))
    measured_pairs.sort(key=lambda x: x[1])
    measured_qubits = [q for q, _ in measured_pairs]

    try:
        circ.remove_final_measurements(inplace=True)
    except Exception:  # noqa: S110
        pass
    # Use qargs to marginalize to measured qubits directly.
    # measured_qubits is sorted by classical bit index, so the
    # output bit ordering matches the server's counts format
    # (rightmost = clbit 0 = first measured qubit).
    statevector = Statevector(circ)
    qargs = measured_qubits if measured_qubits else None
    return {
        str(k): float(v)
        for k, v in statevector.probabilities_dict(qargs=qargs).items()
    }


def classical_fidelity(
    counts: dict[str, int],
    ideal: dict[str, float],
) -> float:
    """Compute classical fidelity.

    F = (sum sqrt(p_ideal * p_actual))^2 (Bhattacharyya coefficient squared).

    Args:
        counts: Measurement counts {state: count}.
        ideal: Ideal probabilities {state: prob}.

    Returns:
        Classical fidelity in [0, 1].
    """
    if not counts or not ideal:
        return 0.0
    total = sum(counts.values())
    p_actual = {state: count / total for state, count in counts.items()}
    all_states = set(ideal) | set(p_actual)
    coef = sum(
        math.sqrt(ideal.get(state, 0) * p_actual.get(state, 0))
        for state in all_states
    )
    return coef * coef


class QuafuCircuitBenchmark:
    """Batch circuit fidelity benchmark on a Quafu chip.

    Pipeline:
        1. Parse TOML chip data (load_toml_chip).
        2. Pre-verify all circuits against chip topology (_verify_circuit).
        3. Compile + batch submit, non-blocking (_compile_and_submit / submit).
        4. Collect results + compute classical fidelity
           (_collect_results / wait_result).
        5. Print results table (_print_results).
    """

    def __init__(
        self,
        toml_path: str,
        circuits_dir: str,
        chip: str,
        compilers: list[str] | None = None,
        shots: int = 1024,
        timeout: int = 300,
        submit_interval: float = 0.25,
    ):
        """Initialize the benchmark.

        Args:
            toml_path: Path to the TOML calibration file.
            circuits_dir: Directory containing .qasm files.
            chip: Quafu chip name.
            compilers: Compiler names to test. Local compilers use
                ``level{N}`` format (e.g. ``level0``,
                ``level3``). Server compilers use their server name.
                Defaults to ["level0", "level3"].
            shots: Measurement shots per circuit.
            timeout: Per-task timeout in seconds.
            submit_interval: Interval between submissions.
        """
        token = os.environ.get("QUARK_TOKEN", "")
        if not token:
            raise SystemExit("Please set QUARK_TOKEN environment variable")
        self._task_manager = Task(token)
        self.chip_data = load_toml_chip(toml_path)
        self.circuits_dir = circuits_dir
        self.chip = chip
        self.compilers = compilers or ["level0", "level3"]
        self.shots = shots
        self.timeout = timeout
        self.submit_interval = submit_interval

    def submit(
        self,
        name: str,
        qasm: str,
        server_compiler: str | None = None,
    ) -> int:
        """Submit a circuit to the Quafu cloud (non-blocking).

        Args:
            name: Task name.
            qasm: OPENQASM 2.0 circuit text.
            server_compiler: Server-side compiler name. None means the
                circuit is already compiled locally.

        Returns:
            Quafu task id (tid).
        """
        return self._task_manager.run({
            "chip": self.chip,
            "name": name,
            "circuit": qasm,
            "shots": self.shots,
            "options": {
                "compiler": server_compiler,
                "correct": False,
                "open_dd": None,
            },
        })

    def wait_result(self, task_id: int) -> dict:
        """Poll the Quafu server until the task completes.

        Args:
            task_id: Quafu task id returned by submit().

        Returns:
            Result dict containing at least 'count'.

        Raises:
            RuntimeError: Task failed.
            TimeoutError: Task did not complete within timeout.
        """
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            status = self._task_manager.status(task_id)
            if status == "Finished":
                return self._task_manager.result(task_id)
            if status == "Failed":
                raise RuntimeError(f"task {task_id} failed")
            time.sleep(2.0)
        raise TimeoutError(f"task {task_id} timeout ({self.timeout}s)")

    def _verify_circuit(self, qasm: str) -> tuple[bool, str | None]:
        """Verify a circuit can run on the chip.

        Uses QuafuVerifier with the chip's coupling list and fidelities.
        Dead edges (fid <= 0) are excluded.
        single_qubit_fidelities is passed unfiltered so the verifier
        knows which qubits are dead (fid=0).

        Args:
            qasm: OPENQASM 2.0 circuit text.

        Returns:
            (passed, error_message).

        Raises:
            ValueError: If chip has no usable edges.
        """
        chip = self.chip_data
        usable = [
            (edge, fid)
            for edge, fid in zip(chip.coupling_list, chip.edge_fidelities)
            if fid > 0
        ]
        if not usable:
            raise ValueError("No usable edges on chip")
        coupling_list, edge_fids = map(list, zip(*usable))
        bits = sum(1 for fid in chip.single_qubit_fidelities if fid > 0)
        params = VerifyParams()
        params.bits = bits
        params.basis_gates = BASIS_GATES
        params.coupling_list = coupling_list
        params.edge_fidelities = edge_fids
        params.single_qubit_fidelities = chip.single_qubit_fidelities
        params.target_bits = []
        result = QuafuVerifier(params).verify(qasm)
        if result.passed:
            return True, None
        return False, result.message

    @staticmethod
    def _compute_circuit_stats(ops: list) -> dict[str, int]:
        """Compute gate count, depth, and two-qubit gate count.

        Skips measurement operations. Depth is computed as the
        longest path of dependent gates on shared qubits.

        Args:
            ops: List of BaseOperation from TranspileResult.

        Returns:
            Dict with gate_count, depth, two_qubit_count.
        """
        gate_count = 0
        two_qubit = 0
        qubit_depth: dict[int, int] = {}
        for op in ops:
            if op.name == "measure":
                continue
            gate_count += 1
            targets = op.targets
            if len(targets) == 2:
                two_qubit += 1
            max_d = max((qubit_depth.get(t, 0) for t in targets), default=0)
            for t in targets:
                qubit_depth[t] = max_d + 1
        depth = max(qubit_depth.values(), default=0)
        return {
            "gate_count": gate_count,
            "depth": depth,
            "two_qubit_count": two_qubit,
        }

    def _compile_local(
        self, qasm_text: str, opt_level: int = 3
    ) -> tuple[str, dict[str, int]]:
        """Compile locally and return QASM text + circuit stats.

        Uses the C++ transpiler with the chip's coupling list and
        fidelities at the given optimization level.

        Args:
            qasm_text: Source QASM circuit text.
            opt_level: Optimization level (0-3).

        Returns:
            (compiled QASM text, stats dict).
        """
        chip = self.chip_data
        result = transpile_from_qasm(
            qasm_text,
            BASIS_GATES,
            opt_level,
            coupling_list=chip.coupling_list,
            edge_fidelities=chip.edge_fidelities,
            single_qubit_fidelities=chip.single_qubit_fidelities,
            fidelity_threshold=0.1,
        )
        stats = self._compute_circuit_stats(result.basis_gate_list)
        return to_qasm2(result.basis_gate_list), stats

    def _discover_circuits(self) -> list[CircuitEntry]:
        """Find all .qasm circuit files in the circuits dir.

        Skips already-compiled or transpiled files.

        Returns:
            List of CircuitEntry, sorted by path.
        """
        paths = sorted(
            p
            for p in Path(self.circuits_dir).rglob("*.qasm")
            if ".compiled." not in p.name and "transpiled" not in p.name
        )
        return [CircuitEntry(circuit=p.stem, qasm_path=p) for p in paths]

    def _pre_verify(
        self, entries: list[CircuitEntry]
    ) -> tuple[list[CircuitEntry], dict]:
        """Phase 0: Pre-verify all circuits against topology.

        Args:
            entries: All circuit entries.

        Returns:
            (active_entries, failures_dict).
        """
        print(f"[Phase 0] Pre-verify {len(entries)} circuits")
        for entry in entries:
            qasm = entry.qasm_path.read_text(encoding="utf-8")
            passed, error = self._verify_circuit(qasm)
            entry.verify_error = error
            if not passed:
                print(f"  SKIP {entry.circuit}: {error}")
        active = [e for e in entries if e.passed]
        failures = {e.circuit: e.verify_error for e in entries if not e.passed}
        print(f"  Passed {len(active)}/{len(entries)}")
        return active, failures

    def _compile_and_submit(self, active: list[CircuitEntry]) -> list[tuple]:
        """Phase 1: Compile + batch submit (non-blocking).

        For each circuit, computes ideal distribution, then
        compiles and submits per-compiler tasks.

        Args:
            active: Circuits that passed pre-verification.

        Returns:
            List of (entry, result, task_id, ideal_probs, compiler).
        """
        print("[Phase 1] Compile + submit")
        pending: list[tuple] = []
        start = time.time()
        for entry in active:
            qasm = entry.qasm_path.read_text(encoding="utf-8")
            try:
                ideal = compute_ideal(qasm)
            except Exception as exc:
                entry.ideal_error = str(exc)
                print(f"  {entry.circuit}: compute ideal failed")
                continue
            for compiler in self.compilers:
                result = RunResult()
                entry.run_results[compiler] = result
                try:
                    opt_level = _parse_opt_level(compiler)
                    if opt_level is not None:
                        submit_qasm, stats = self._compile_local(
                            qasm, opt_level
                        )
                        result.gate_count = stats["gate_count"]
                        result.depth = stats["depth"]
                        result.two_qubit_count = stats["two_qubit_count"]
                        server_compiler = None
                    else:
                        submit_qasm = qasm
                        server_compiler = compiler
                    name = f"{entry.circuit}_{compiler}"
                    task_id = self.submit(name, submit_qasm, server_compiler)
                    pending.append((entry, result, task_id, ideal, compiler))
                except Exception as exc:
                    result.error = str(exc)
                    print(f"  {entry.circuit}/{compiler}: ERR {str(exc)[:60]}")
                time.sleep(self.submit_interval)
        print(f"  Submitted {len(pending)} tasks, {time.time() - start:.1f}s")
        return pending

    @staticmethod
    def _parse_counts(result: dict) -> dict[str, int]:
        """Parse and normalize measurement counts.

        Args:
            result: Raw result dict from wait_result.

        Returns:
            Normalized counts {state_str: int}.
        """
        raw_counts = result.get("count") or {}
        counts: dict[str, int] = {}
        for state, count in raw_counts.items():
            key = str(state).replace(" ", "")
            counts[key] = int(count)
        return counts

    def _collect_results(self, pending: list[tuple]) -> None:
        """Phase 2: Collect results + compute fidelity.

        Args:
            pending: List from _compile_and_submit.
        """
        print("[Phase 2] Collect results")
        start = time.time()
        for i, (
            entry,
            result,
            task_id,
            ideal,
            compiler,
        ) in enumerate(pending, 1):
            try:
                raw = self.wait_result(task_id)
                counts = self._parse_counts(raw)
                if not counts:
                    result.error = str(raw.get("error") or "no counts")
                    continue
                result.fidelity = round(classical_fidelity(counts, ideal), 4)
                # For server-side compilers, extract stats from the
                # "transpiled" QASM returned by the server.
                if result.gate_count is None:
                    transpiled = raw.get("transpiled") or ""
                    if isinstance(transpiled, str) and transpiled.strip():
                        try:
                            ops, _ = qasm_to_ir(transpiled)
                            srv = self._compute_circuit_stats(ops)
                            result.gate_count = srv["gate_count"]
                            result.depth = srv["depth"]
                            result.two_qubit_count = srv["two_qubit_count"]
                        except Exception:  # noqa: S110  stats are optional
                            pass
                print(
                    f"  [{i}/{len(pending)}] "
                    f"{entry.circuit}/{compiler}: "
                    f"F={result.fidelity:.4f}"
                )
            except Exception as exc:
                result.error = str(exc)
                print(
                    f"  [{i}/{len(pending)}] "
                    f"{entry.circuit}/{compiler}: "
                    f"ERR {str(exc)[:50]}"
                )
        print(f"  Collect time {time.time() - start:.1f}s")

    @staticmethod
    def _print_results(
        entries: list[CircuitEntry],
        failures: dict,
        compilers: list[str],
    ):
        """Print stats + fidelity table and summary.

        One row per (circuit, compiler) showing gate count, depth,
        two-qubit gate count, and fidelity.  Followed by per-compiler
        averages for all metrics.

        Args:
            entries: All circuit entries.
            failures: Pre-verification failures.
            compilers: Compiler names for column headers.
        """
        active = [e for e in entries if e.passed]
        compiler_w = max(len(c) for c in compilers) + 2

        print("\n" + "=" * 79)
        header = (
            f"{'circuit':<22}"
            f" {'compiler':<{compiler_w}}"
            f" {'gates':>6}"
            f" {'depth':>6}"
            f" {'2q':>6}"
            f" {'fidelity':>10}"
        )
        print(header)
        print("-" * 79)
        for idx, entry in enumerate(active):
            for compiler in compilers:
                result = entry.run_results.get(compiler)
                if result is None:
                    continue
                gc = (
                    str(result.gate_count)
                    if result.gate_count is not None
                    else "-"
                )
                dp = str(result.depth) if result.depth is not None else "-"
                tq = (
                    str(result.two_qubit_count)
                    if result.two_qubit_count is not None
                    else "-"
                )
                if result.fidelity is not None:
                    fid = f"{result.fidelity:.4f}"
                elif entry.ideal_error:
                    fid = "IDEAL_ERR"
                else:
                    fid = "ERR"
                print(
                    f"{entry.circuit:<22}"
                    f" {compiler:<{compiler_w}}"
                    f" {gc:>6}"
                    f" {dp:>6}"
                    f" {tq:>6}"
                    f" {fid:>10}"
                )
            if idx < len(active) - 1:
                print("-" * 79)

        print("-" * 79)
        for compiler in compilers:
            results = [
                r
                for r in (
                    e.run_results[compiler]
                    for e in active
                    if compiler in e.run_results
                )
                if r is not None
            ]
            n = len(results)
            fids = [r.fidelity for r in results if r.fidelity is not None]
            gcs = [r.gate_count for r in results if r.gate_count is not None]
            dps = [r.depth for r in results if r.depth is not None]
            tqs = [
                r.two_qubit_count
                for r in results
                if r.two_qubit_count is not None
            ]
            if n:
                gc_str = f"{sum(gcs) / len(gcs):.0f}" if gcs else "-"
                dp_str = f"{sum(dps) / len(dps):.0f}" if dps else "-"
                tq_str = f"{sum(tqs) / len(tqs):.0f}" if tqs else "-"
                avg_f = sum(fids) / n if fids else 0.0
                min_f = min(fids) if fids else 0.0
                max_f = max(fids) if fids else 0.0
                fail = n - len(fids)
                print(
                    f"  {compiler:<{compiler_w}} "
                    f"avg gates={gc_str:>6}  "
                    f"depth={dp_str:>6}  "
                    f"2q={tq_str:>6}  "
                    f"F={avg_f:.4f}  "
                    f"(n={n}, fail={fail}, "
                    f"min={min_f:.4f}, "
                    f"max={max_f:.4f})"
                )
                if fail > 0 and fids:
                    avg_ok = sum(fids) / len(fids)
                    print(
                        f"  {'':<{compiler_w}} "
                        f"avg gates={'':>6}  "
                        f"depth={'':>6}  "
                        f"2q={'':>6}  "
                        f"F={avg_ok:.4f}  "
                        f"(n={len(fids)}, "
                        f"min={min_f:.4f}, "
                        f"max={max_f:.4f})"
                    )

        if failures:
            print(f"\n  Pre-verify skipped: {len(failures)}")
        ideal_errs = [e for e in active if e.ideal_error]
        if ideal_errs:
            print(f"  Ideal failed: {len(ideal_errs)}")

    def run(self) -> None:
        """Run the three-phase benchmark pipeline.

        Phase 0: Pre-verify all circuits.
        Phase 1: Compile + batch submit (non-blocking).
        Phase 2: Collect results + compute fidelity.
        """
        entries = self._discover_circuits()
        print(
            f"Chip: {self.chip}, shots: {self.shots}, "
            f"compilers: {self.compilers}, "
            f"circuits: {len(entries)}"
        )
        print("=" * 79)
        active, failures = self._pre_verify(entries)
        pending = self._compile_and_submit(active)
        self._collect_results(pending)
        self._print_results(entries, failures, self.compilers)


def benchmark(
    toml_path: str,
    circuits_dir: str,
    chip: str = "Dongling",
    compilers: list[str] | None = None,
    shots: int = 1024,
    timeout: int = 300,
    submit_interval: float = 0.25,
) -> None:
    """Run circuit benchmark on a Quafu chip.

    Args:
        toml_path: Path to the TOML calibration file.
        circuits_dir: Directory containing .qasm files.
        chip: Quafu chip name.
        compilers: Compiler names to test.
        shots: Measurement shots per circuit.
        timeout: Per-task timeout in seconds.
        submit_interval: Interval between submissions.
    """
    bench = QuafuCircuitBenchmark(
        toml_path=toml_path,
        circuits_dir=circuits_dir,
        chip=chip,
        compilers=compilers,
        shots=shots,
        timeout=timeout,
        submit_interval=submit_interval,
    )
    bench.run()


if __name__ == "__main__":
    benchmark(
        # 先通过calibration_quafu.py生成.toml文件
        toml_path=("xxx.toml"),
        circuits_dir=("samples/qasm/benchpress/qasmbench-small"),
        chip="Shenglian",
        compilers=["level0", "level3", "quarkcircuit"],
    )
