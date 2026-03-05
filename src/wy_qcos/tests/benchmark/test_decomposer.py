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

"""Benchmark different quantum gate decomposition implementations.

This module is used to compare:
1. The baseline gate-level decomposer.
2. The equivalence-graph-based decomposer.

Both decomposers are applied to the same QASM benchmark circuits, and
their parsing and decomposition time are measured for performance analysis.
"""

import time
from pathlib import Path

from wy_qcos.transpiler.cmss.decomposer.decomposer import Decomposer
from wy_qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.tests.common.qasm_file_reader import QasmFileReader


class DecomposerBenchmark:
    """Provides benchmarking utilities for circuit decomposition.

    This class does NOT validate correctness or equivalence.
    Its sole purpose is to measure and compare the performance
    characteristics of different decomposition strategies.
    """

    @staticmethod
    def benchmark_new_equivalence_graph_decomposer(
        operations, target_gate_set: list
    ):
        """Benchmark the equivalence-graph-based decomposer.

        This decomposer performs gate rewriting based on equivalence
        relations and graph traversal, which typically trades higher
        preprocessing cost for better decomposition quality.

        Args:
            operations: Quantum operations extracted from the circuit IR.
            target_gate_set: Target hardware-supported gate set.

        Returns:
            Decomposed quantum operations.
        """
        decomposer = Decomposer()

        # Measure pure decomposition time (excluding parsing)
        start = time.perf_counter()
        gate_name_list = list({op.name for op in operations})
        rule_dict, _ = decomposer.get_decompose_rules(
            gate_name_list, target_gate_set
        )
        decomposed_gates = decomposer.apply_decompose_rules(
            operations, rule_dict
        )
        elapsed = time.perf_counter() - start

        print(f"[new Equivalence Graph Decomposer] time={elapsed:.6f}s")
        return decomposed_gates

    @staticmethod
    def benchmark_equivalence_graph_decomposer(
        operations, target_gate_set: list
    ):
        """Benchmark the equivalence-graph-based decomposer.

        This decomposer performs gate rewriting based on equivalence
        relations and graph traversal, which typically trades higher
        preprocessing cost for better decomposition quality.

        Args:
            operations: Quantum operations extracted from the circuit IR.
            target_gate_set: Target hardware-supported gate set.

        Returns:
            Decomposed quantum operations.
        """
        decomposer = Decomposer()

        # Measure pure decomposition time (excluding parsing)
        start = time.perf_counter()
        result = decomposer.decompose(operations, target_gate_set)
        elapsed = time.perf_counter() - start

        print(f"[Equivalence Graph Decomposer] time={elapsed:.6f}s")
        return result

    @staticmethod
    def benchmark_baseline_decomposer(operations, target_gate_set: list):
        """Benchmark the baseline decomposer.

        The baseline decomposer applies direct, rule-based gate expansion
        without using equivalence graph optimization. It serves as a
        performance and complexity baseline for comparison.

        Args:
            operations: Quantum operations extracted from the circuit IR.
            target_gate_set: Target hardware-supported gate set.

        Returns:
            Decomposed quantum operations.
        """
        start = time.perf_counter()
        result = decompose_gates(operations, target_gate_set)
        elapsed = time.perf_counter() - start

        print(f"[Baseline Decomposer] time={elapsed:.6f}s")
        return result

    @staticmethod
    def benchmark_qasm_directory(qasm_root, target_gate_set):
        """Run decomposition benchmarks on all QASM files in a directory.

        For each QASM file, this function performs the following steps:
        1. Parse QASM text into an abstract syntax tree (AST).
        2. Convert AST into circuit IR and extract quantum operations.
        3. Run baseline decomposer and record execution time.
        4. Run equivalence-graph-based decomposer and record execution time.

        This allows direct performance comparison under identical inputs.

        Args:
            qasm_root: Root directory containing QASM benchmark files.
            target_gate_set: Target hardware-supported gate set.
        """
        reader = QasmFileReader(qasm_root)

        for qasm_path, qasm_source in reader.iter_contents():
            print(f"[CASE] {qasm_path}")

            try:
                # Step 1–2: QASM parsing and IR construction
                start = time.perf_counter()
                tree = get_abs_tree(qasm_source)
                circuit_ir = get_ir(tree)
                operations = circuit_ir.get_operations()
                elapsed = time.perf_counter() - start

                print(f"[Parser] time={elapsed:.6f}s")

                # Step 3: baseline decomposition
                DecomposerBenchmark.benchmark_baseline_decomposer(
                    operations, target_gate_set
                )

                # Step 4: equivalence-graph-based decomposition
                DecomposerBenchmark.benchmark_equivalence_graph_decomposer(
                    operations, target_gate_set
                )

                DecomposerBenchmark.benchmark_new_equivalence_graph_decomposer(
                    operations, target_gate_set
                )

            except Exception:
                # Explicitly surface any failure to simplify debugging
                print("ERROR\n")
                raise


def main():
    """Entry point for decomposition performance benchmarking.

    This function benchmarks both decomposers on:
    - QASMBench small circuits
    - QASMBench medium circuits
    """
    target_gate_set = ["rx", "ry", "cz", "sync", "measure", "reset"]

    # Project root is resolved dynamically to avoid hard-coded paths
    project_root = Path(__file__).resolve().parents[4]
    # Benchmark: bigint
    bigint_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "bigint"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        bigint_benchmark_dir, target_gate_set
    )
    # Benchmark: clifford
    clifford_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "clifford"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        clifford_benchmark_dir, target_gate_set
    )
    # Benchmark: dtc
    dtc_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "dtc"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        dtc_benchmark_dir, target_gate_set
    )

    # Benchmark: feynman
    feynman_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "feynman"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        feynman_benchmark_dir, target_gate_set
    )

    # Benchmark: qaoa
    qaoa_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "qaoa"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        qaoa_benchmark_dir, target_gate_set
    )
    # Benchmark: qasmbench - large
    large_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "qasmbench-large"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        large_benchmark_dir, target_gate_set
    )

    # Benchmark: qasmbench-medium
    medium_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "qasmbench-medium"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        medium_benchmark_dir, target_gate_set
    )

    # Benchmark: qasmbench-small
    small_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "qasmbench-small"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        small_benchmark_dir, target_gate_set
    )

    # Benchmark: qft
    qft_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "qft"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        qft_benchmark_dir, target_gate_set
    )

    # Benchmark: qv
    qv_benchmark_dir = project_root / "samples" / "qasm" / "benchpress" / "qv"
    DecomposerBenchmark.benchmark_qasm_directory(
        qv_benchmark_dir, target_gate_set
    )

    # Benchmark: square-heisenberg
    square_heisenberg_benchmark_dir = (
        project_root / "samples" / "qasm" / "benchpress" / "square-heisenberg"
    )
    DecomposerBenchmark.benchmark_qasm_directory(
        square_heisenberg_benchmark_dir, target_gate_set
    )


if __name__ == "__main__":
    main()
