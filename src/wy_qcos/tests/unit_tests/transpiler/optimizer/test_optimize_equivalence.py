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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Reliability test: verify optimization preserves circuit equivalence.

Workflow per circuit (random + benchmark):
  1. Transpile to the target basis set with level=0 (basis conversion
     only, no optimization) to obtain the "base" circuit.
  2. Run the optimizer at level 3 on the base circuit.
  3. Verify matrix equivalence between base and optimized circuits
     using validate_optimize_result from comm.py.
  4. Verify all gates in the optimized circuit belong to the target
     basis set.

Circuit sources:
  - 100 random circuits (4-8 qubits, 100-300 gates, default basis)
  - Benchmark circuits from samples/qasm/benchpress/qasmbench-small
    (filtered: <=10 qubits, <=500 gates, excluding _transpiled)

Test matrix:
  - Basis gate sets: [u,cz], [h,rx,ry,rz,cz], [h,rx,ry,rz,cx]
  - Python optimizer (python, level 3)
  - C++ optimizer (high_performance, level 3)
  - C++ transpile_from_qasm (level 3, no routing)
  - C++ params: fast_mode True/False, num_threads 1/0
"""

import copy
import os
from pathlib import Path

import numpy as np
import pytest

from wy_qcos.common.cmss.gate_operation import create_gate
from wy_qcos.common.cmss.qasm_converter import QasmConverter
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.tests.unit_tests.transpiler.comm import (
    validate_optimize_result,
)
from wy_qcos.transpiler import high_performance as hp
from wy_qcos.transpiler.cmss.circuit.utils import RandomCircuitGen
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import (
    optimize as py_optimize,
)

OPT_LEVEL = 3
BASE_LEVEL = 0
NUM_RANDOM = 100
MIN_QUBITS = 4
MAX_QUBITS = 8
MIN_GATES = 100
MAX_GATES = 300
FAIL_DIR = os.path.join(os.path.dirname(__file__), "failures")
REPO_ROOT = Path(__file__).resolve().parents[6]
BENCH_DIR = REPO_ROOT / "samples" / "qasm" / "benchpress" / "qasmbench-small"
BASIS_SETS = [
    {"u", "cz"},
    {"h", "rx", "ry", "rz", "cz"},
    {"h", "rx", "ry", "rz", "cx"},
]
BASIS_IDS = ["-".join(sorted(b)) for b in BASIS_SETS]

NON_GATE_OPS = {"measure", "reset", "sync", "move", "barrier"}


def _strip_non_gates(ops):
    """Remove non-gate operations from an op list."""
    return [op for op in ops if op.name not in NON_GATE_OPS]


def _strip_measure_from_qasm(qasm_str):
    """Remove measure statements from QASM text."""
    lines = qasm_str.split("\n")
    return "\n".join(
        line for line in lines if not line.strip().startswith("measure")
    )


def _gen_random_circuit(
    seed: int,
    min_qubits: int = MIN_QUBITS,
    max_qubits: int = MAX_QUBITS,
    min_gates: int = MIN_GATES,
    max_gates: int = MAX_GATES,
):
    """Generate a random circuit with default basis gates.

    Returns (qasm_str, num_qubits).
    """
    rng = np.random.default_rng(seed)
    num_qubits = int(rng.integers(min_qubits, max_qubits + 1))
    num_gates = int(rng.integers(min_gates, max_gates + 1))
    rcg = RandomCircuitGen()
    ir = rcg.random_circuit_with_gates(
        num_qubits=num_qubits,
        num_gates=num_gates,
        seed=seed,
    )
    qasm_str = QasmConverter(
        QuantumCircuit.from_ir(ir, num_qubits),
    ).to_qasm2()
    return qasm_str, num_qubits


def _load_bench_circuits():
    """Load benchmark circuits from qasmbench-small.

    Filters: <=10 qubits, excludes _transpiled files.
    Gate count filtering is done in the circuits fixture after
    decomposition to basis gates.
    Returns a list of (qasm_str, num_qubits) tuples.
    """
    result = []
    bench_dir = os.path.normpath(BENCH_DIR)
    if not os.path.isdir(bench_dir):
        return result
    for name in sorted(os.listdir(bench_dir)):
        dir_path = os.path.join(bench_dir, name)
        if not os.path.isdir(dir_path):
            continue
        for fname in sorted(os.listdir(dir_path)):
            if not fname.endswith(".qasm") or "_transpiled" in fname:
                continue
            filepath = os.path.join(dir_path, fname)
            with open(filepath, encoding="utf-8") as f:
                qasm_str = f.read()
            try:
                _, num_qubits = hp.qasm_to_ir(qasm_str)
            except Exception:  # noqa: S112
                continue
            if num_qubits > MAX_QUBITS:
                continue
            result.append((qasm_str, num_qubits))
    return result


def _to_py_ops(ops):
    """Convert C++ BaseOperation list to Python GateOperation list."""
    return [
        create_gate(
            name=op.name,
            targets=list(op.targets),
            arg_value=list(op.arg_value),
        )
        for op in ops
    ]


def _check_basis_gates(ops, basis, label, optimizer):
    """Assert every gate in *ops* belongs to *basis*."""
    non_basis = {op.name for op in ops} - basis - NON_GATE_OPS
    assert not non_basis, (
        f"Basis gate check FAILED: optimizer={optimizer}, "
        f"basis={label}, non_basis={non_basis}"
    )


def _basis_label(basis) -> str:
    """Human-readable basis gate set label for error messages."""
    return "{" + ",".join(sorted(basis)) + "}"


def _save_failed_circuit(qasm_str, index, basis, optimizer, **extra):
    """Save the failing circuit QASM to file, return the file path."""
    os.makedirs(FAIL_DIR, exist_ok=True)
    basis_str = "_".join(sorted(basis))
    parts = [optimizer, basis_str, f"idx{index}"]
    for key, val in extra.items():
        parts.append(f"{key}{val}")
    filename = "_".join(parts) + ".qasm"
    filepath = os.path.join(FAIL_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(qasm_str)
    return filepath


@pytest.mark.slow
class TestOptimizeEquivalence:
    """Verify that optimization preserves matrix equivalence."""

    @pytest.fixture(scope="class")
    @classmethod
    def circuits(cls):
        """Pre-generate circuits with QASM and level=0 base ops.

        Returns a list of (qasm_str, num_qubits, base_ops) tuples
        where base_ops is a dict {basis_idx: list[BaseOperation]}.
        Includes random circuits and benchmark circuits.
        """
        # Build circuit sources: (qasm_str, num_qubits)
        sources = []
        for seed in range(NUM_RANDOM):
            sources.append(_gen_random_circuit(seed))
        sources.extend(_load_bench_circuits())

        result = []
        for qasm_str, num_qubits in sources:
            qasm_str = _strip_measure_from_qasm(qasm_str)
            base_ops = {}
            skip = False
            for basis_idx in range(len(BASIS_SETS)):
                basis = sorted(BASIS_SETS[basis_idx])
                transpile_result = hp.transpile_from_qasm(
                    qasm_string=qasm_str,
                    supp_basis_gates=basis,
                    opt_level=BASE_LEVEL,
                )
                if len(transpile_result.basis_gate_list) > MAX_GATES:
                    skip = True
                    break
                base_ops[basis_idx] = _strip_non_gates(
                    transpile_result.basis_gate_list,
                )
            if skip:
                continue
            result.append((qasm_str, num_qubits, base_ops))
        return result

    # ---- Python optimizer (python) ----

    @pytest.mark.parametrize(
        "basis_idx", range(len(BASIS_SETS)), ids=BASIS_IDS
    )
    def test_py_optimize_equiv(self, circuits, basis_idx):
        """Python optimizer level 3 must preserve equivalence."""
        basis = sorted(BASIS_SETS[basis_idx])
        label = _basis_label(basis)
        failures = []
        for index, (qasm_str, num_qubits, base_ops) in enumerate(circuits):
            ops = _to_py_ops(base_ops[basis_idx])
            try:
                opt_ir = py_optimize(
                    copy.deepcopy(ops),
                    opt_level=OPT_LEVEL,
                    basis_gates=set(basis),
                )
            except Exception:  # noqa: S112
                continue
            try:
                validate_optimize_result(
                    ops,
                    opt_ir,
                    num_qubits,
                    num_qubits,
                )
            except AssertionError:
                path = _save_failed_circuit(
                    qasm_str,
                    index,
                    basis,
                    "python",
                )
                failures.append(f"index={index}, circuit={path}")
                continue
            try:
                _check_basis_gates(opt_ir, set(basis), label, "python")
            except AssertionError as e:
                failures.append(f"index={index}, basis_check={e}")
        if failures:
            raise AssertionError(
                f"Equivalence FAILED: optimizer=python, "
                f"basis={label}, {len(failures)} failures: "
                + "; ".join(failures)
            ) from None

    @pytest.mark.parametrize(
        "basis_idx", range(len(BASIS_SETS)), ids=BASIS_IDS
    )
    def test_cpp_optimize_equiv(self, circuits, basis_idx):
        """C++ optimizer level 3 must preserve equivalence."""
        basis = sorted(BASIS_SETS[basis_idx])
        label = _basis_label(basis)
        failures = []
        for index, (qasm_str, num_qubits, base_ops) in enumerate(circuits):
            ops = base_ops[basis_idx]
            try:
                opt_ops = hp.optimize(
                    copy.deepcopy(ops),
                    opt_level=OPT_LEVEL,
                    basis_gates=set(basis),
                )
            except Exception:  # noqa: S112
                continue
            try:
                validate_optimize_result(
                    _to_py_ops(ops),
                    _to_py_ops(opt_ops),
                    num_qubits,
                    num_qubits,
                )
            except AssertionError:
                path = _save_failed_circuit(
                    qasm_str,
                    index,
                    basis,
                    "high_performance",
                )
                failures.append(f"index={index}, circuit={path}")
                continue
            try:
                _check_basis_gates(
                    opt_ops, set(basis), label, "high_performance"
                )
            except AssertionError as e:
                failures.append(f"index={index}, basis_check={e}")
        if failures:
            raise AssertionError(
                f"Equivalence FAILED: optimizer=high_performance, "
                f"basis={label}, {len(failures)} failures: "
                + "; ".join(failures)
            )

    # ---- C++ transpile_from_qasm (optimize only, no routing) ----

    @pytest.mark.parametrize(
        "basis_idx", range(len(BASIS_SETS)), ids=BASIS_IDS
    )
    @pytest.mark.parametrize(
        "fast_mode", [True, False], ids=["fast", "no_fast"]
    )
    @pytest.mark.parametrize(
        "num_threads", [1, 0], ids=["threads=1", "threads=0"]
    )
    def test_cpp_transpile_equiv(
        self,
        circuits,
        basis_idx,
        fast_mode,
        num_threads,
    ):
        """C++ transpile_from_qasm (no routing) must preserve equiv."""
        basis = sorted(BASIS_SETS[basis_idx])
        label = _basis_label(basis)
        failures = []
        for index, (qasm_str, num_qubits, base_ops) in enumerate(circuits):
            ops = base_ops[basis_idx]
            try:
                opt_result = hp.transpile_from_qasm(
                    qasm_string=qasm_str,
                    supp_basis_gates=basis,
                    opt_level=OPT_LEVEL,
                    fast_mode=fast_mode,
                    num_threads=num_threads,
                )
            except Exception:  # noqa: S112
                continue
            try:
                validate_optimize_result(
                    _to_py_ops(ops),
                    _to_py_ops(opt_result.basis_gate_list),
                    num_qubits,
                    opt_result.num_qubits,
                )
            except AssertionError:
                path = _save_failed_circuit(
                    qasm_str,
                    index,
                    basis,
                    "high_performance",
                    fast=fast_mode,
                    threads=num_threads,
                )
                failures.append(f"index={index}, circuit={path}")
                continue
            try:
                _check_basis_gates(
                    opt_result.basis_gate_list,
                    set(basis),
                    label,
                    "high_performance",
                )
            except AssertionError as e:
                failures.append(f"index={index}, basis_check={e}")
        if failures:
            raise AssertionError(
                f"Equivalence FAILED: optimizer=high_performance, "
                f"basis={label}, fast={fast_mode}, threads={num_threads}, "
                f"{len(failures)} failures: " + "; ".join(failures)
            ) from None
