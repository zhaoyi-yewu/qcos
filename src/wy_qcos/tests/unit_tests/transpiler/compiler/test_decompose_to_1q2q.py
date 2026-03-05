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

"""System tests for the 1-qubit and 2-qubit gate decomposer.

This module provides end-to-end tests for validating the quantum gate
decomposition workflow. The tests ensure that:

1. OpenQASM circuits are correctly parsed into an intermediate
   representation (IR).
2. The IR can be decomposed into a set of 1-qubit and 2-qubit gates.
3. The decomposed circuit contains only valid 1q/2q gates.
4. The decomposition preserves circuit semantics.
"""

import pytest
from pathlib import Path

from wy_qcos.transpiler.cmss.compiler.decomposer import (
    decompose_gates_to_1q2q,
)
from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.tests.common.qasm_file_reader import QasmFileReader
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.tests.unit_tests.transpiler.comm import (
    validate_ir_equals,
    validate_no_shared_reference_or_raise,
    validate_only_1q_2q_gates,
)


@pytest.mark.usefixtures("global_configs")
@pytest.mark.slow
class TestDecomposeTo1q2q:
    """System-level tests for 1q/2q gate decomposition."""

    samples_dir: Path

    @classmethod
    def setup_class(cls) -> None:
        """Initializes shared resources for the test suite."""
        cls.samples_dir = (
            Path(GLOBAL_CONFIGS["samples_dir"]).expanduser().resolve()
        )

    @staticmethod
    def _parse_qasm_to_gates(qasm_source: str) -> list:
        """Parses QASM source code into IR gate operations.

        Args:
            qasm_source: OpenQASM source code.

        Returns:
            A list of gate operations extracted from the IR.
        """
        tree = get_abs_tree(qasm_source)
        ir = get_ir(tree)
        return ir.get_operations()

    @staticmethod
    def _validate_decomposition(
        original_gates: list,
        decomposed_gates: list,
    ) -> None:
        """Validates correctness of a 1q/2q gate decomposition.

        Args:
            original_gates: Gate list before decomposition.
            decomposed_gates: Gate list after decomposition.

        Raises:
            ValueError: If semantic equivalence or structural constraints
                are violated.
        """
        validate_ir_equals(original_gates, decomposed_gates)
        validate_no_shared_reference_or_raise(original_gates, decomposed_gates)
        validate_only_1q_2q_gates(decomposed_gates)

    def _run_qasm_directory(self, qasm_dir: Path) -> None:
        """Runs decomposition tests for all QASM files in a directory.

        Args:
            qasm_dir: Directory containing QASM benchmark files.
        """
        qasm_reader = QasmFileReader(qasm_dir)

        for qasm_path, qasm_source in qasm_reader.iter_contents():
            print(f"\n[CASE] {qasm_path}")

            original_gates = self._parse_qasm_to_gates(qasm_source)
            decomposed_gates = decompose_gates_to_1q2q(original_gates)

            print(f"[IR] Gate count = {len(original_gates)}")
            print(
                f"[IR] Gate types = {sorted({g.name for g in original_gates})}"
            )

            self._validate_decomposition(original_gates, decomposed_gates)

            print("[OK] Decomposition validated")

    @pytest.mark.slow
    def test_qasmbench_small(self) -> None:
        """Runs system tests on QASMBench-small circuits."""
        qasm_dir = self.samples_dir / "qasm" / "benchpress" / "qasmbench-small"

        print("\n=== [ST] QASMBench Small Decomposer Test ===")
        print(f"[INFO] qasm_dir = {qasm_dir}")

        self._run_qasm_directory(qasm_dir)
