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

import contextlib
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from collections.abc import Callable
from typing import TextIO

import qiskit
import qiskit.qasm2

from wy_qcos.transpiler import high_performance as hp
from wy_qcos.tests.common.qasm_file_reader import QasmFileReader

# Optional compiler packages.
try:
    from pyqpanda3.intermediate_compiler import convert_qasm_string_to_qprog
    from pyqpanda3.transpilation import Transpiler

    HAS_QPANDA3 = True
except ImportError:
    HAS_QPANDA3 = False

try:
    from cqlib.utils.qasm2 import loads as cqlib_loads_qasm
    from cqlib.utils.simplify import QCIS_Simplify
    from cqlib.circuits import Circuit

    HAS_CQLIB = True
except ImportError:
    HAS_CQLIB = False

# ---------------------------------------------------------------------------
# Configuration: modify these to customize a run.
# ---------------------------------------------------------------------------

BASIS_GATES: list[str] = ["h", "rx", "ry", "rz", "cx"]
BASIS_GATE_SET: set[str] = set(BASIS_GATES)
MAX_QASM_LINES: int = 10_000
BENCHMARK_SUBDIRS: list[str] = [
    "qasmbench-large",
    "qasmbench-medium",
    "qasmbench-small",
]

CMSS_OPT_LEVEL: int = 3
QISKIT_OPT_LEVEL: int = 3
QPANDA3_OPT_LEVEL: int = 2  # max level
QPANDA3_BASIS: list[str] = ["H", "RX", "RY", "RZ", "CNOT"]

SELECTED_COMPILERS: list[str] = ["qiskit", "cmss_cpp", "qpanda3", "cqlib"]

# Field widths for per-file table alignment.
GATE_WIDTH: int = 7
TWO_QUBIT_WIDTH: int = 5
DEPTH_WIDTH: int = 5

# Names of non-quantum operations to exclude from gate counts.
_NON_QUANTUM_OPS: set[str] = {"measure", "barrier", "reset"}


@dataclass
class OptimizationResult:
    """Optimization result for one compiler on one circuit."""

    gates: int
    two_qubit: int
    depth: int


# ---------------------------------------------------------------------------
# Backend optimization functions
# ---------------------------------------------------------------------------


def optimize_qiskit(base_circuit: qiskit.QuantumCircuit) -> OptimizationResult:
    """Run qiskit transpile at QISKIT_OPT_LEVEL and return gate/2q/depth."""
    opt = qiskit.transpile(
        base_circuit,
        basis_gates=BASIS_GATES,
        optimization_level=QISKIT_OPT_LEVEL,
    )
    # Exclude measure/barrier from gate count for fair comparison.
    ops = dict(opt.count_ops())
    quantum_gates = sum(v for k, v in ops.items() if k not in _NON_QUANTUM_OPS)
    return OptimizationResult(
        quantum_gates, opt.num_nonlocal_gates(), opt.depth()
    )


def optimize_cmss(ir_ops: list, num_qubits: int) -> OptimizationResult:
    """Run cmss_cpp optimization at CMSS_OPT_LEVEL and return gate/2q/depth."""
    opt_ops = hp.optimize(
        ir_ops, opt_level=CMSS_OPT_LEVEL, basis_gates=BASIS_GATE_SET
    )
    circ = hp.QuantumCircuit(num_qubits, 0, 0.0)
    circ.append_operations(opt_ops)
    # Exclude measure/barrier from gate count for fair comparison.
    quantum_ops = [op for op in opt_ops if op.name not in _NON_QUANTUM_OPS]
    return OptimizationResult(
        len(quantum_ops),
        sum(1 for op in quantum_ops if op.name == "cx"),
        circ.depth(),
    )


def optimize_qpanda3(
    base_circuit: qiskit.QuantumCircuit,
) -> OptimizationResult | None:
    """Run qpanda3 transpile at QPANDA3_OPT_LEVEL and return gate/2q/depth."""
    if not HAS_QPANDA3:
        return None
    base_qasm = qiskit.qasm2.dumps(base_circuit)
    try:
        prog = convert_qasm_string_to_qprog(base_qasm)
        opt = Transpiler().transpile(
            prog,
            optimization_level=QPANDA3_OPT_LEVEL,
            basic_gates=QPANDA3_BASIS,
        )
        co = opt.count_ops()
        return OptimizationResult(
            int(
                sum(
                    v
                    for k, v in co.items()
                    if k not in ("BARRIER", "MEASURE", "M")
                )
            ),
            int(sum(opt.count_ops(only_q2=True).values())),
            int(opt.depth()),
        )
    except Exception:
        return None


def optimize_cqlib(
    base_circuit: qiskit.QuantumCircuit,
) -> OptimizationResult | None:
    """Run cqlib simplify and return gate/2q/depth.

    Note: cqlib uses CZ basis internally (not CX), so gate counts may differ
    from other compilers using CX basis. 2-qubit gates counted are CZ, not CX.
    """
    if not HAS_CQLIB:
        return None
    circuit = cqlib_loads_qasm(qiskit.qasm2.dumps(base_circuit))
    opt = Circuit.load(QCIS_Simplify().simplify(circuit.qcis))
    seq = opt.instruction_sequence
    try:
        depth = opt.depth()
    except ValueError:
        return None
    # Filter out measure and barrier for fair comparison.
    quantum_instrs = [
        e
        for e in seq
        if str(e.instruction).split("(", maxsplit=1)[0]
        not in ("M", "B", "BARRIER")
    ]
    return OptimizationResult(
        len(quantum_instrs),
        sum(1 for e in quantum_instrs if len(e.qubits) == 2),
        depth,
    )


# Compiler registry: name -> (display_label, optimize_fn, needs_ir).
# needs_ir=True means the fn takes (ir_ops, num_qubits) instead of the
# qiskit base circuit (cmss reuses the hp IR from the baseline).
_OptFn = Callable[..., OptimizationResult | None]

COMPILER_REGISTRY: dict[str, tuple[str, _OptFn, bool]] = {
    "qiskit": ("qiskit", optimize_qiskit, False),
    "cmss_cpp": ("cmss_cpp", optimize_cmss, True),
    "qpanda3": ("qpanda3", optimize_qpanda3, False),
    "cqlib": ("cqlib", optimize_cqlib, False),
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def load_base_circuit(qasm_source: str) -> qiskit.QuantumCircuit:
    """Parse QASM and unroll to basis gates with optimization_level=0."""
    instructions = qiskit.qasm2.LEGACY_CUSTOM_INSTRUCTIONS
    qc = qiskit.qasm2.loads(qasm_source, custom_instructions=instructions)
    return qiskit.transpile(qc, basis_gates=BASIS_GATES, optimization_level=0)


def compute_base_stats(
    base_circuit: qiskit.QuantumCircuit,
) -> tuple[OptimizationResult, list, int]:
    """Compute baseline stats via high_performance IR."""
    ir, num_qubits = hp.qasm_to_ir(qiskit.qasm2.dumps(base_circuit))
    circ = hp.QuantumCircuit(num_qubits, 0, 0.0)
    circ.append_operations(ir)
    # Exclude measure/barrier for fair comparison with optimized results.
    quantum_ir = [op for op in ir if op.name not in _NON_QUANTUM_OPS]
    return (
        OptimizationResult(
            len(quantum_ir),
            sum(1 for op in quantum_ir if op.name == "cx"),
            circ.depth(),
        ),
        ir,
        num_qubits,
    )


def reduction_percentage(optimized: int, base: int) -> float:
    """Return reduction percentage: (base - optimized) / base * 100."""
    return (1 - optimized / base) * 100 if base else 0.0


def format_percentage(pct: float, width: int = 4) -> str:
    """Format percentage with sign: '-X%' for reduction, '+X%' for increase."""
    sign = "-" if pct >= 0 else "+"
    return f"{sign}{abs(pct):>{width}.0f}%"


def count_lines(path: Path) -> int:
    """Count lines in a file, capped at MAX_QASM_LINES."""
    with path.open(encoding="utf-8") as fh:
        return sum(1 for _ in zip(range(MAX_QASM_LINES), fh))


@contextlib.contextmanager
def suppress_stderr():
    """Redirect fd 2 to /dev/null to suppress C++ library warnings."""
    saved_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 2)
    try:
        yield
    finally:
        os.dup2(saved_fd, 2)
        os.close(devnull_fd)
        os.close(saved_fd)


# ---------------------------------------------------------------------------
# Core comparison logic
# ---------------------------------------------------------------------------


def compare_single(qasm_path: Path, compilers: list[str]) -> dict:
    """Run all selected compilers on one QASM file and return results dict."""
    qasm_source = qasm_path.read_text(encoding="utf-8")
    base_circuit = load_base_circuit(qasm_source)
    base_result, ir_ops, num_qubits = compute_base_stats(base_circuit)

    # Always compute cmss_cpp as the reference baseline.
    compute_list = list(compilers)
    if "cmss_cpp" not in compute_list:
        compute_list.append("cmss_cpp")

    opt_results: dict[str, OptimizationResult | None] = {}
    for name in compute_list:
        _, optimize_fn, needs_ir = COMPILER_REGISTRY[name]
        try:
            opt_results[name] = (
                optimize_fn(ir_ops, num_qubits)
                if needs_ir
                else optimize_fn(base_circuit)
            )
        except Exception:
            opt_results[name] = None

    return {
        "file": str(qasm_path),
        "num_qubits": num_qubits,
        "base": base_result,
        "opt": opt_results,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_compiler_cell(
    label: str, result: OptimizationResult | None, base: OptimizationResult
) -> str:
    """Format compiler row: label G/2Q/D with reduction pct vs base."""
    if result is None:
        na = (
            f"{'n/a':>{GATE_WIDTH}}"
            f"/{'n/a':>{TWO_QUBIT_WIDTH}}"
            f"/{'n/a':>{DEPTH_WIDTH}}"
        )
        return f"{label:<8} {na} n/a /n/a /n/a"
    gate_pct = format_percentage(
        reduction_percentage(result.gates, base.gates), 4
    )
    two_qubit_pct = format_percentage(
        reduction_percentage(result.two_qubit, base.two_qubit), 4
    )
    depth_pct = format_percentage(
        reduction_percentage(result.depth, base.depth), 4
    )
    nums = (
        f"{result.gates:>{GATE_WIDTH}}"
        f"/{result.two_qubit:>{TWO_QUBIT_WIDTH}}"
        f"/{result.depth:>{DEPTH_WIDTH}}"
    )
    return f"{label:<8} {nums} {gate_pct}/{two_qubit_pct}/{depth_pct}"


def write_table_header(fh: TextIO, compilers: list[str]) -> None:
    """Write the per-file table header to *fh*."""
    base_hdr = (
        f"{'base':<8} {'g':>{GATE_WIDTH}}"
        f"/{'2q':>{TWO_QUBIT_WIDTH}}"
        f"/{'d':>{DEPTH_WIDTH}}"
    )
    cols = [base_hdr]
    for c in compilers:
        pcts = f"{'%':>6}/{'%':>6}/{'%':>6}"
        cols.append(
            f"{COMPILER_REGISTRY[c][0]:<8} {'g':>{GATE_WIDTH}}"
            f"/{'2q':>{TWO_QUBIT_WIDTH}}"
            f"/{'d':>{DEPTH_WIDTH}} {pcts}"
        )
    print(f"  {'file':<32} | q={'n':<3}  | " + " | ".join(cols), file=fh)
    sep_width = 2 + 32 + 3 + 5 + 3 + len(" | ".join(cols))
    print("-" * sep_width, file=fh)


def write_table_row(result: dict, compilers: list[str], fh: TextIO) -> None:
    """Write one per-file data row to *fh*."""
    name = Path(result["file"]).name
    base = result["base"]
    base_str = (
        f"{'base':<8} {base.gates:>{GATE_WIDTH}}"
        f"/{base.two_qubit:>{TWO_QUBIT_WIDTH}}"
        f"/{base.depth:>{DEPTH_WIDTH}}"
    )
    parts = [base_str]
    for c in compilers:
        parts.append(
            format_compiler_cell(
                COMPILER_REGISTRY[c][0], result["opt"].get(c), base
            )
        )
    print(
        f"  {name:<32} | q={result['num_qubits']:<3}  | " + " | ".join(parts),
        file=fh,
    )


def write_summary(
    results: list[dict], compilers: list[str], fh: TextIO
) -> None:
    """Write summary blocks: one per compiler comparing against cmss.

    Each block uses its own common-files set (only that compiler and
    cmss_cpp must succeed), so a failure in one compiler does not shrink
    the comparison set for unrelated compilers.
    """
    if not results:
        print("  (no results)", file=fh)
        return

    display = [c for c in compilers if c != "cmss_cpp"]

    for c in display:
        label = COMPILER_REGISTRY[c][0]
        pair = [c, "cmss_cpp"]
        common = [
            r
            for r in results
            if all(r["opt"].get(k) is not None for k in pair)
        ]
        if not common:
            print(f"  No common files for {label} vs cmss.", file=fh)
            continue

        base_totals = {
            attr: sum(getattr(r["base"], attr) for r in common)
            for attr in ("gates", "two_qubit", "depth")
        }
        compiler_totals = {
            attr: sum(getattr(r["opt"][c], attr) for r in common)
            for attr in ("gates", "two_qubit", "depth")
        }
        cmss_totals = {
            attr: sum(getattr(r["opt"]["cmss_cpp"], attr) for r in common)
            for attr in ("gates", "two_qubit", "depth")
        }

        print("", file=fh)
        print("=" * 78, file=fh)
        print(
            f"  Improvement over {label}: ({label} - cmss) / {label}", file=fh
        )
        print(
            f"  (positive = cmss better, negative = {label} better)", file=fh
        )
        col_width = 12
        hdr = f"  {'':18}" + "".join(
            f"| {d:>{col_width}}" for d in ("gates", "2q", "depth")
        )
        print(hdr, file=fh)
        print(
            f"  {'-' * 18}"
            + "".join(f"+-{'-' * col_width}" for _ in range(3)),
            file=fh,
        )
        for row_label, totals in [
            ("base", base_totals),
            (f"{label} optimized", compiler_totals),
            ("cmss optimized", cmss_totals),
        ]:
            row = f"  {row_label:<18}"
            for attr in ("gates", "two_qubit", "depth"):
                row += f"| {totals[attr]:>{col_width}}"
            print(row, file=fh)
        diff_row = f"  {'diff':<18}"
        pct_row = f"  {'%':<18}"
        for attr in ("gates", "two_qubit", "depth"):
            diff = compiler_totals[attr] - cmss_totals[attr]
            pct = (
                diff / compiler_totals[attr] * 100
                if compiler_totals[attr]
                else 0.0
            )
            diff_row += f"| {diff:>{col_width}}"
            pct_row += f"| {pct:>{col_width - 1}.2f}%"
        print(diff_row, file=fh)
        print(pct_row, file=fh)
        print("=" * 78, file=fh)


def run_benchmark(
    qasm_root: Path,
    compilers: list[str],
    fh: TextIO = sys.stdout,
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Run benchmark on one directory and write per-file + summary to *fh*.

    Returns:
        (results, errors) where errors is a list of (path, message) tuples.
    """
    reader = QasmFileReader(qasm_root)
    results: list[dict] = []
    errors: list[tuple[str, str]] = []

    write_table_header(fh, compilers)

    for qasm_path in reader.iter_files():
        if count_lines(qasm_path) >= MAX_QASM_LINES:
            continue
        if "_transpiled" in qasm_path.name:
            continue
        try:
            with suppress_stderr():
                result = compare_single(qasm_path, compilers)
            results.append(result)
            write_table_row(result, compilers, fh)
        except Exception as exc:
            errors.append((str(qasm_path), repr(exc)))

    write_summary(results, compilers, fh)

    return results, errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full benchmark and write results to a timestamped file."""
    selected = [c for c in SELECTED_COMPILERS if c in COMPILER_REGISTRY]
    if not selected:
        print("No valid compilers selected.", file=sys.stderr)
        sys.exit(1)

    project_root = Path(__file__).resolve().parents[5]
    bench_root = project_root / "samples" / "qasm" / "benchpress"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = (
        project_root / f"multi_optimizer_comparison_results_{timestamp}.txt"
    )

    all_results: list[dict] = []
    all_errors: list[tuple[str, str]] = []

    with open(output_path, "w", encoding="utf-8") as fh:
        print("=" * 78, file=fh)
        print("  Multi-Compiler Optimization Comparison", file=fh)
        print("=" * 78, file=fh)
        print(
            f"  Timestamp       : "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            file=fh,
        )
        print(
            f"  Compilers       : "
            f"{', '.join(COMPILER_REGISTRY[c][0] for c in selected)}",
            file=fh,
        )
        print(f"  Basis gates     : {BASIS_GATES}", file=fh)
        print(f"  cmss/qiskit opt : level {CMSS_OPT_LEVEL}", file=fh)
        print(
            f"  qpanda3 opt     : level {QPANDA3_OPT_LEVEL} (max=2)",
            file=fh,
        )
        print("  cqlib           : (no level)", file=fh)
        print(f"  Max QASM lines  : {MAX_QASM_LINES}", file=fh)
        print("=" * 78, file=fh)

        start = time.perf_counter()
        for subdir in BENCHMARK_SUBDIRS:
            qasm_dir = bench_root / subdir
            if not qasm_dir.is_dir():
                continue
            print(f"\n--- {subdir} ---", file=fh)
            results, errors = run_benchmark(qasm_dir, selected, fh)
            all_results.extend(results)
            all_errors.extend(errors)

        elapsed = time.perf_counter() - start
        print("", file=fh)
        print("#" * 78, file=fh)
        print("  ALL DIRECTORIES SUMMARY", file=fh)
        print("#" * 78, file=fh)
        write_summary(all_results, selected, fh)

        print("", file=fh)
        print(f"  Test set path   : {bench_root}", file=fh)
        print(f"  Elapsed time    : {elapsed:.2f}s", file=fh)

    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()
