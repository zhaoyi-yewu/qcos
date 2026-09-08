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

"""Compare quantum circuit optimization: C++ vs qiskit.

Both optimizers run at optimization_level=3 on the *same* input
circuit.

Pipeline (per QASM file):
  1. Parse QASM with qiskit.
  2. qiskit transpile to [h, rx, ry, rz, cx] with
     optimization_level=0 to produce the "base circuit".
  3. Convert base circuit to QASM2, then C++ qasm_to_ir to get
     IR + num_qubits.
  4. C++ optimize(IR, opt_level=3, basis={h,rx,ry,rz,cx}) then
     gate count + depth.
  5. qiskit transpile(base, opt_level=3, basis=[h,rx,ry,rz,cx])
     then gate count + depth.
  6. Report and compare.

The benchmark runner iterates over all benchpress QASM files
whose line count is below MAX_QASM_LINES (default 10 000).
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

import qiskit
import qiskit.qasm2

from wy_qcos.transpiler import high_performance as hp
from wy_qcos.transpiler.high_performance import (
    BaseOperation,
    OptimizeMetrics,
    QuantumCircuit,
)
from wy_qcos.tests.common.qasm_file_reader import QasmFileReader

# Basis gate set: used both for the opt_level=0 "base circuit"
# unroll and as the optimization target for both optimizers.
BASIS_GATES: list[str] = ["h", "rx", "ry", "rz", "cx"]
BASIS_GATE_SET: set[str] = set(BASIS_GATES)

# Only benchmark QASM files below this line count.
MAX_QASM_LINES: int = 10_000

# Optimization level for both optimizers.
OPT_LEVEL: int = 3

# All benchpress sub-directories, mirroring the decomposer benchmark.
BENCHPRESS_SUBDIRS: list[str] = [
    "bigint",
    "clifford",
    "dtc",
    "feynman",
    "qaoa",
    "qasmbench-large",
    "qasmbench-medium",
    "qasmbench-small",
    "qft",
    "qv",
    "square-heisenberg",
]

# Pass execution order (for column ordering in timing output).
_PASS_ORDER: list[str] = [
    "InverseCancellation",
    "AdjacentPhaseOpt",
    "EquivalencePass",
    "HadamardGateReduction",
    "RzCommuteOptimization",
    "CxCommuteOptimization",
    "PhasePolynomialMerging",
    "UnitarySynthesis",
]

# Type alias for a single comparison result dict.
ComparisonResult = dict[str, Any]


def _count_lines(path: Path) -> int:
    """Count lines in *path*, stopping at MAX_QASM_LINES."""
    count = 0
    with path.open(encoding="utf-8") as fh:
        for _ in fh:
            count += 1
            if count >= MAX_QASM_LINES:
                break
    return count


def _reduction_pct(optimized: int, base: int) -> float:
    """Return reduction percentage of *optimized* vs *base*."""
    return (1 - optimized / base) * 100 if base else 0.0


def _ordered_passes(all_passes: set[str]) -> list[str]:
    """Return pass names in execution order, remaining last."""
    ordered = [
        pass_name for pass_name in _PASS_ORDER if pass_name in all_passes
    ]
    remaining = sorted(all_passes - set(_PASS_ORDER))
    return ordered + remaining


def _qasm_to_base_circuit(
    qasm_source: str,
) -> qiskit.QuantumCircuit:
    """Parse QASM text and unroll to [h, rx, ry, rz, cx].

    Uses optimization_level=0 to produce the shared "base circuit"
    fed to both optimizers.
    """
    inst = qiskit.qasm2.LEGACY_CUSTOM_INSTRUCTIONS
    qc = qiskit.qasm2.loads(qasm_source, custom_instructions=inst)
    return qiskit.transpile(
        qc,
        basis_gates=BASIS_GATES,
        optimization_level=0,
    )


def _base_circuit_to_ir(
    base_circuit: qiskit.QuantumCircuit,
) -> tuple[list[BaseOperation], int]:
    """Convert a qiskit base circuit to C++ IR via QASM2 round-trip.

    Returns:
        (ir_ops, num_qubits).
    """
    base_qasm = qiskit.qasm2.dumps(base_circuit)
    return hp.qasm_to_ir(base_qasm)


def _ir_to_circuit(
    ir_ops: list[BaseOperation],
    num_qubits: int,
) -> QuantumCircuit:
    """Build a C++ QuantumCircuit from IR ops."""
    circ = hp.QuantumCircuit(num_qubits, 0, 0.0)
    circ.append_operations(ir_ops)
    return circ


def _cpp_optimize(
    ir_ops: list[BaseOperation],
    num_qubits: int,
) -> tuple[int, int, list[BaseOperation], OptimizeMetrics]:
    """Run C++ optimize at OPT_LEVEL with per-pass stats.

    Returns:
        (gate_count, depth, optimized_ops, metrics).
    """
    opt_ops, metrics = hp.optimize_with_analysis(
        ir_ops,
        opt_level=OPT_LEVEL,
        basis_gates=BASIS_GATE_SET,
    )
    circ = _ir_to_circuit(opt_ops, num_qubits)
    return circ.size(), circ.depth(), opt_ops, metrics


def _qiskit_optimize(
    base_circuit: qiskit.QuantumCircuit,
) -> tuple[int, int]:
    """Run qiskit transpile at OPT_LEVEL.

    Returns:
        (gate_count, depth).
    """
    opt = qiskit.transpile(
        base_circuit,
        basis_gates=BASIS_GATES,
        optimization_level=OPT_LEVEL,
    )
    return opt.size(), opt.depth()


def compare_single(
    qasm_path: Path,
) -> ComparisonResult:
    """Run the full comparison pipeline on one QASM file.

    Args:
        qasm_path: Path to a QASM benchmark file.

    Returns:
        A dict with keys: file, num_qubits, base_gate_count,
        base_depth, cpp_opt_gate_count, cpp_opt_depth, cpp_time,
        qiskit_opt_gate_count, qiskit_opt_depth, qiskit_time,
        pass_timings, pass_reduced.
    """
    qasm_source = qasm_path.read_text(encoding="utf-8")

    # Step 1-2: parse + unroll to basis at opt_level=0
    base_circuit = _qasm_to_base_circuit(qasm_source)

    # Step 3: convert base circuit to C++ IR (shared input)
    ir_ops, num_qubits = _base_circuit_to_ir(base_circuit)
    base_circ = _ir_to_circuit(ir_ops, num_qubits)
    base_gate_count = base_circ.size()
    base_depth = base_circ.depth()

    # Step 4: C++ optimize (with per-pass timing)
    start = time.perf_counter()
    cpp_gates, cpp_depth, _, metrics = _cpp_optimize(ir_ops, num_qubits)
    cpp_time = time.perf_counter() - start

    # Step 5: qiskit optimize
    start = time.perf_counter()
    qiskit_gates, qiskit_depth = _qiskit_optimize(base_circuit)
    qiskit_time = time.perf_counter() - start

    return {
        "file": str(qasm_path),
        "num_qubits": num_qubits,
        "base_gate_count": base_gate_count,
        "base_depth": base_depth,
        "cpp_opt_gate_count": cpp_gates,
        "cpp_opt_depth": cpp_depth,
        "cpp_time": cpp_time,
        "qiskit_opt_gate_count": qiskit_gates,
        "qiskit_opt_depth": qiskit_depth,
        "qiskit_time": qiskit_time,
        "pass_timings": dict(metrics.pass_time_ms),
        "pass_reduced": dict(metrics.pass_reduced),
    }


def _write_header(fh: TextIO) -> None:
    """Write a column header row for the per-file output."""
    print(
        f"  {'file':<38} | q={'n':<3}"
        f" | base  {'g':>5}/{'d':<5}"
        f" | cmss_cpp {'g':>5}/{'d':<5}"
        f" -{'g':>4}%/-{'d':>3}%"
        f" | qiskit {'g':>5}/{'d':<5}"
        f" -{'g':>4}%/-{'d':>3}%"
        f" | t(cmss_cpp) t(qiskit) ratio",
        file=fh,
    )
    print(
        f"  {'-' * 38} | {'-' * 5}"
        f" | {'-' * 6} {'-' * 11}"
        f" | {'-' * 9} {'-' * 11}"
        f" {'-' * 12}"
        f" | {'-' * 7} {'-' * 11}"
        f" {'-' * 12}"
        f" | {'-' * 30}",
        file=fh,
    )


def _write_result(result: ComparisonResult, fh: TextIO) -> None:
    """Write a single comparison result as a formatted line."""
    name = Path(result["file"]).name
    base_gates = result["base_gate_count"]
    base_depth = result["base_depth"]
    cmss_gates = result["cpp_opt_gate_count"]
    cmss_depth = result["cpp_opt_depth"]
    qiskit_gates = result["qiskit_opt_gate_count"]
    qiskit_depth = result["qiskit_opt_depth"]
    cmss_time = result["cpp_time"]
    qiskit_time = result["qiskit_time"]

    cmss_gate_pct = _reduction_pct(cmss_gates, base_gates)
    cmss_depth_pct = _reduction_pct(cmss_depth, base_depth)
    qiskit_gate_pct = _reduction_pct(qiskit_gates, base_gates)
    qiskit_depth_pct = _reduction_pct(qiskit_depth, base_depth)
    time_ratio = cmss_time / qiskit_time if qiskit_time > 0 else 0

    base_str = f"base  {base_gates:>5}/{base_depth:<5}"
    cmss_str = (
        f"cmss_cpp {cmss_gates:>5}/{cmss_depth:<5}"
        f" -{cmss_gate_pct:>4.0f}%/-{cmss_depth_pct:>3.0f}%"
    )
    qiskit_str = (
        f"qiskit {qiskit_gates:>5}/{qiskit_depth:<5}"
        f" -{qiskit_gate_pct:>4.0f}%/-{qiskit_depth_pct:>3.0f}%"
    )
    time_str = (
        f"t(cmss_cpp)={cmss_time:.2f}"
        f" t(qiskit)={qiskit_time:.2f}"
        f" ratio={time_ratio:.1f}x"
    )
    print(
        f"  {name:<38} | q={result['num_qubits']:<3}"
        f" | {base_str}"
        f" | {cmss_str}"
        f" | {qiskit_str}"
        f" | {time_str}",
        file=fh,
    )


def _write_summary(results: list[ComparisonResult], fh: TextIO) -> None:
    """Write aggregate statistics to *fh*.

    Shows base, optimized, absolute reduction, and percentage
    for both gate count and circuit depth.
    """
    if not results:
        print("  (no results)", file=fh)
        return

    num_files = len(results)
    total_base_gates = sum(res["base_gate_count"] for res in results)
    total_cmss_gates = sum(res["cpp_opt_gate_count"] for res in results)
    total_qiskit_gates = sum(res["qiskit_opt_gate_count"] for res in results)
    total_base_depth = sum(res["base_depth"] for res in results)
    total_cmss_depth = sum(res["cpp_opt_depth"] for res in results)
    total_qiskit_depth = sum(res["qiskit_opt_depth"] for res in results)

    cmss_better = sum(
        1
        for res in results
        if res["cpp_opt_gate_count"] < res["qiskit_opt_gate_count"]
    )
    qiskit_better = sum(
        1
        for res in results
        if res["qiskit_opt_gate_count"] < res["cpp_opt_gate_count"]
    )
    tied = sum(
        1
        for res in results
        if res["cpp_opt_gate_count"] == res["qiskit_opt_gate_count"]
    )

    col_width = 10

    def _summary_row(label: str, base: int, opt: int) -> str:
        """Format one summary table row."""
        reduced = base - opt
        pct = reduced / base * 100 if base else 0
        return (
            f"  {label:<16}| {base:>{col_width}}"
            f" | {opt:>{col_width}} | {reduced:>{col_width}}"
            f" | {pct:>6.2f}%"
        )

    print("", file=fh)
    print("=" * 78, file=fh)
    print(f"  Total files: {num_files}", file=fh)
    print(
        f"  {'':16}| {'base':>{col_width}}"
        f" | {'opt':>{col_width}} | {'reduced':>{col_width}}"
        f" | {'%':>7}",
        file=fh,
    )
    print(
        f"  {'-' * 16}+-{'-' * col_width}"
        f"-+-{'-' * col_width}-+-{'-' * col_width}"
        f"-+-{'-' * col_width}-+-{'-' * 7}",
        file=fh,
    )
    print(
        _summary_row("cmss_cpp gates", total_base_gates, total_cmss_gates),
        file=fh,
    )
    print(
        _summary_row("qiskit gates", total_base_gates, total_qiskit_gates),
        file=fh,
    )
    print(
        _summary_row("cmss_cpp depth", total_base_depth, total_cmss_depth),
        file=fh,
    )
    print(
        _summary_row("qiskit depth", total_base_depth, total_qiskit_depth),
        file=fh,
    )
    print(
        f"  cmss_cpp better: {cmss_better}"
        f" | qiskit better: {qiskit_better}"
        f" | tied: {tied}",
        file=fh,
    )
    print("=" * 78, file=fh)

    # per-circuit average method
    cmss_gate_avg = (
        sum(
            _reduction_pct(
                res["cpp_opt_gate_count"],
                res["base_gate_count"],
            )
            for res in results
        )
        / num_files
    )
    qiskit_gate_avg = (
        sum(
            _reduction_pct(
                res["qiskit_opt_gate_count"],
                res["base_gate_count"],
            )
            for res in results
        )
        / num_files
    )
    cmss_depth_avg = (
        sum(
            _reduction_pct(
                res["cpp_opt_depth"],
                res["base_depth"],
            )
            for res in results
        )
        / num_files
    )
    qiskit_depth_avg = (
        sum(
            _reduction_pct(
                res["qiskit_opt_depth"],
                res["base_depth"],
            )
            for res in results
        )
        / num_files
    )

    print("", file=fh)
    print(
        "  Per-circuit average reduction (each circuit weighted equally)",
        file=fh,
    )
    print(
        f"  {'':16}| {'gates':>12} | {'depth':>12}",
        file=fh,
    )
    print(
        f"  {'-' * 16}+-{'-' * 12}-+-{'-' * 12}",
        file=fh,
    )
    print(
        f"  {'cmss_cpp':16}|"
        f" {cmss_gate_avg:>11.2f}% | {cmss_depth_avg:>11.2f}%",
        file=fh,
    )
    print(
        f"  {'qiskit':16}|"
        f" {qiskit_gate_avg:>11.2f}% | {qiskit_depth_avg:>11.2f}%",
        file=fh,
    )
    print("=" * 78, file=fh)


def _write_pass_timings(results: list[ComparisonResult], fh: TextIO) -> None:
    """Write per-pass timing summary to *fh*."""
    all_passes: set[str] = set()
    for res in results:
        all_passes.update(res.get("pass_timings", {}))
    if not all_passes:
        return

    pass_names = _ordered_passes(all_passes)

    stats: dict[str, dict[str, float]] = {}
    for pname in pass_names:
        times = [
            res["pass_timings"][pname]
            for res in results
            if pname in res.get("pass_timings", {})
        ]
        stats[pname] = {
            "total_ms": sum(times),
            "avg_ms": sum(times) / len(times) if times else 0,
            "max_ms": max(times) if times else 0,
        }

    qiskit_total_ms = sum(res["qiskit_time"] * 1000 for res in results)
    cmss_total_ms = sum(res["cpp_time"] * 1000 for res in results)

    col_width = 14
    print("", file=fh)
    print("=" * 78, file=fh)
    print("  Per-Pass Timing Analysis (ms)", file=fh)
    print("=" * 78, file=fh)
    print(
        f"  {'pass name':<28}|"
        f" {'total':>{col_width}} | {'avg':>{col_width}}"
        f" | {'max':>{col_width}}",
        file=fh,
    )
    print(
        f"  {'-' * 28}-+-{'-' * col_width}"
        f"-+-{'-' * col_width}-+-{'-' * col_width}",
        file=fh,
    )
    for pname in pass_names:
        stat = stats[pname]
        print(
            f"  {pname:<28}|"
            f" {stat['total_ms']:>{col_width}.2f}"
            f" | {stat['avg_ms']:>{col_width}.4f}"
            f" | {stat['max_ms']:>{col_width}.2f}",
            file=fh,
        )
    print(
        f"  {'-' * 28}-+-{'-' * col_width}"
        f"-+-{'-' * col_width}-+-{'-' * col_width}",
        file=fh,
    )
    print(
        f"  {'cmss_cpp total':<28}| {cmss_total_ms:>{col_width}.2f}",
        file=fh,
    )
    print(
        f"  {'qiskit total':<28}| {qiskit_total_ms:>{col_width}.2f}",
        file=fh,
    )
    print("=" * 78, file=fh)


def _write_pass_timings_detail(
    results: list[ComparisonResult], fh: TextIO
) -> None:
    """Write per-circuit pass timing details to *fh*."""
    if not results:
        return

    all_passes: set[str] = set()
    for result in results:
        all_passes.update(result.get("pass_timings", {}))
    pass_names = _ordered_passes(all_passes)
    if not pass_names:
        return

    col_width = 14
    name_width = 28

    print("=" * 120, file=fh)
    print(
        "  Per-Circuit Detail: gates/depth + pass"
        " timing (ms) + qiskit time (ms)",
        file=fh,
    )
    print("=" * 120, file=fh)

    # Column header
    header = f"  {'file':<{name_width}} | {'q':>3} | {'base g/d':>11}"
    sep = f"  {'-' * name_width} | {'-' * 3} | {'-' * 11}"
    for pname in pass_names:
        header += f" | {pname[:col_width]:>{col_width}}"
        sep += f" | {'-' * col_width}"
    header += f" | {'cmss':>{col_width}}"
    sep += f" | {'-' * col_width}"
    header += f" | {'qiskit':>{col_width}}"
    sep += f" | {'-' * col_width}"
    print(header, file=fh)
    print(sep, file=fh)

    # Per-circuit rows
    for result in results:
        name = Path(result["file"]).name
        row = (
            f"  {name:<{name_width}}"
            f" | {result['num_qubits']:>3}"
            f" | {result['base_gate_count']:>5}"
            f"/{result['base_depth']:<5}"
        )
        pass_timings = result.get("pass_timings", {})
        cmss_total = sum(pass_timings.get(p, 0.0) for p in pass_names)
        for pname in pass_names:
            val = pass_timings.get(pname, 0.0)
            pct = val / cmss_total * 100 if cmss_total > 0 else 0
            row += f" | {f'{val:.2f}({pct:.0f}%)':>{col_width}}"
        row += f" | {cmss_total:>{col_width}.2f}"
        row += f" | {result['qiskit_time'] * 1000:>{col_width}.2f}"
        print(row, file=fh)

    print("=" * 120, file=fh)

    # Summary at the bottom
    print("", file=fh)
    _write_pass_timings(results, fh)


def _write_config(timestamp: str, fh: TextIO) -> None:
    """Write global benchmark configuration to *fh*."""
    print("=" * 78, file=fh)
    print("  Benchmark Configuration", file=fh)
    print("=" * 78, file=fh)
    print(f"  Timestamp       : {timestamp}", file=fh)
    print(f"  Basis gates     : {BASIS_GATES}", file=fh)
    print(f"  Optimization lvl: {OPT_LEVEL}", file=fh)
    print(f"  Max QASM lines  : {MAX_QASM_LINES}", file=fh)
    print("=" * 78, file=fh)


def run_benchmark(
    qasm_root: Path,
    max_lines: int = MAX_QASM_LINES,
    fh: TextIO = sys.stdout,
) -> tuple[list[ComparisonResult], list[tuple[str, str]]]:
    """Run the comparison on all benchpress QASM files.

    Only files with fewer than *max_lines* lines are processed.
    Results are written to *fh* (default: stdout).

    Args:
        qasm_root: Root directory containing QASM benchmark files.
        max_lines: Skip files with >= this many lines.
        fh: Output stream for per-file results and summary.

    Returns:
        (results, errors) where results is a list of result dicts
        and errors is a list of (file_path, error_message) tuples.
    """
    reader = QasmFileReader(qasm_root)
    results: list[ComparisonResult] = []
    errors: list[tuple[str, str]] = []

    _write_header(fh)

    for qasm_path in reader.iter_files():
        if _count_lines(qasm_path) >= max_lines:
            continue
        if "_transpiled" in qasm_path.name:
            continue

        try:
            result = compare_single(qasm_path)
            results.append(result)
            _write_result(result, fh)
        except Exception as exc:  # noqa: BLE001
            errors.append((str(qasm_path), repr(exc)))
            print(
                f"  SKIP {qasm_path.name}: {exc!r}",
                file=fh,
            )

    _write_summary(results, fh)

    if errors:
        print("", file=fh)
        print(
            f"  {len(errors)} file(s) skipped due to errors.",
            file=fh,
        )

    return results, errors


def main() -> None:
    """Entry point: run the comparison on all benchpress directories.

    Writes results to
    optimize_comparison_results_<timestamp>.txt in the project root.
    """
    project_root = Path(__file__).resolve().parents[5]
    bench_root = project_root / "samples" / "qasm" / "benchpress"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = project_root / f"optimize_comparison_results_{timestamp}.txt"

    all_results: list[ComparisonResult] = []
    all_errors: list[tuple[str, str]] = []

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(output_path, "w", encoding="utf-8") as fh:
        _write_config(timestamp_str, fh)
        start = time.perf_counter()

        for subdir in BENCHPRESS_SUBDIRS:
            qasm_dir = bench_root / subdir
            if not qasm_dir.is_dir():
                continue
            print(f"\n--- {subdir} ---", file=fh)
            results, errors = run_benchmark(qasm_dir, fh=fh)
            all_results.extend(results)
            all_errors.extend(errors)

        elapsed = time.perf_counter() - start

        # Global summary
        print("", file=fh)
        print("#" * 78, file=fh)
        print("  ALL DIRECTORIES SUMMARY", file=fh)
        print("#" * 78, file=fh)
        _write_summary(all_results, fh)

        print("", file=fh)
        print(
            f"  Test set path   : {bench_root}",
            file=fh,
        )
        print(
            f"  Elapsed time    : {elapsed:.2f}s",
            file=fh,
        )

    # Per-circuit pass timing detail to a separate file
    timings_path = project_root / f"optimize_pass_timings_{timestamp}.txt"
    with open(timings_path, "w", encoding="utf-8") as tfh:
        _write_pass_timings_detail(all_results, tfh)

    if all_errors:
        print(f"\nTotal skipped: {len(all_errors)} file(s).")

    print(f"Results written to {output_path}")
    print(f"Pass timings written to {timings_path}")


if __name__ == "__main__":
    main()
