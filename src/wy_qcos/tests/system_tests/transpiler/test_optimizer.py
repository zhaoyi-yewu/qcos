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


import copy
from pathlib import Path

import pytest

from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import (
    optimize_gate,
    optimize,
)
from wy_qcos.tests.common.qasm_file_reader import QasmFileReader
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.tests.unit_tests.transpiler.comm import validate_ir_equals
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


@pytest.mark.usefixtures("global_configs")
class TestOptimizer:
    """System-level tests for quantum gate optimization.

    This test suite verifies the correctness of the gate optimizer by
    running optimization passes on real QASM benchmark circuits.

    The focus of these tests is **semantic correctness**, ensuring that:
    - QASM programs are correctly parsed into IR.
    - Gate-level optimization preserves circuit semantics.
    - Optimized IR is equivalent to the original IR.
    """

    @classmethod
    def setup_class(cls):
        """Initialize shared test resources.

        This method runs once before all tests in this class.
        It resolves the root directory containing QASM benchmark samples.
        """
        cls.samples_dir = (
            Path(GLOBAL_CONFIGS["samples_dir"]).expanduser().resolve()
        )

    def _parse_qasm_to_gates(self, qasm_source):
        """Parse OpenQASM source into a list of IR gate operations.

        Args:
            qasm_source (str): OpenQASM source code.

        Returns:
            list: A list of IR gate operations representing the circuit.
        """
        tree = get_abs_tree(qasm_source)
        ir = get_ir(tree)
        return ir.get_operations()

    def _validate_optimization(self, original_gates):
        """Validate semantic equivalence after gate optimization.

        This method verifies that different optimization paths preserve
        the semantics of the original gate sequence.

        Args:
            original_gates (list): Gate operations before optimization.
        """
        reference = copy.deepcopy(original_gates)

        for optimizer_fn in (optimize_gate, optimize):
            gates = copy.deepcopy(reference)
            optimized = optimizer_fn(gates)
            circuit = QuantumCircuit.from_ir(optimized)
            validate_ir_equals(reference, optimized)
            print(
                f"[OPT] {optimizer_fn.__name__:<15}| "
                f"Width = {circuit.width()},"
                f"Gate count = {len(optimized)},"
                f"Depth ={circuit.depth()}"
            )

        print("[OK] Optimization semantic equivalence validated")

    def run_directory_tests(self, qasm_dir):
        """Run optimization tests for all QASM files in a directory.

        For each QASM file, this method:
        - Parses the QASM source into IR.
        - Extracts gate operations.
        - Applies gate optimization.
        - Verifies semantic equivalence.

        Args:
            qasm_dir (Path): Directory containing QASM benchmark files.
        """
        qasm_reader = QasmFileReader(qasm_dir)

        for qasm_path, qasm_source in qasm_reader.iter_contents():
            print(f"\n[CASE] {qasm_path}")

            gates = self._parse_qasm_to_gates(qasm_source)
            circuit = QuantumCircuit.from_ir(gates)

            print(
                f"[IR]  origin gate    | "
                f"Width = {circuit.width()},"
                f"Gate count = {len(gates)},"
                f"Depth = {circuit.depth()}"
            )
            self._validate_optimization(gates)

    def test_qasmbench_small_optimization(self):
        """System test for QASMBench-small circuits."""
        qasm_dir = self.samples_dir / "qasm" / "benchpress" / "qasmbench-small"

        print("\n=== [ST] QASMBench Small Optimization Test ===")
        print(f"[INFO] qasm_dir = {qasm_dir}")

        self.run_directory_tests(qasm_dir)
