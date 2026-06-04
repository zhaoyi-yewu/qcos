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

"""System tests for the Decomposer component.

This module contains system-level tests for validating the quantum gate
decomposition workflow. The tests ensure that:

1. OpenQASM circuits can be correctly parsed into an intermediate
   representation (IR).
2. The IR can be decomposed into multiple backend-specific instruction sets.
3. The decomposed circuits only contain gates supported by the target backend.
4. The decomposition process preserves circuit equivalence.

These tests operate on benchmark QASM circuits and serve as an end-to-end
verification of the decomposer's correctness.
"""

import pytest
from pathlib import Path

from wy_qcos.transpiler.high_performance import (
    convert_qasm_string_to_qcos_operations,
    Decomposer,
)
from wy_qcos.transpiler.cmss.circuit.cpp_utils import (
    convert_ir_py2cpp,
    convert_ir_cpp2py,
)

from wy_qcos.tests.unit_tests.transpiler.comm import (
    validate_ir_equals,
    validate_gates_in_targets,
)

from wy_qcos.tests.common.qasm_file_reader import QasmFileReader
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
@pytest.mark.slow
class TestDecomposer:
    """System-level tests for quantum circuit decomposition.

    This test suite verifies the correctness of the Decomposer component
    across multiple quantum backends. It focuses on validating functional
    correctness rather than performance.

    The following aspects are covered:
    - Correct parsing of QASM input into IR.
    - Successful decomposition into backend-supported gate sets.
    - Semantic equivalence between original and decomposed circuits.
    """

    @classmethod
    def setup_class(cls):
        """Initializes shared resources for the test suite.

        This method is executed once before all test cases in this class.
        It prepares:
        - The root directory containing QASM benchmark samples.
        - A shared Decomposer instance to avoid repeated initialization.
        - Backend-specific quantum instruction sets used for validation.
        """
        cls.samples_dir = (
            Path(GLOBAL_CONFIGS["samples_dir"]).expanduser().resolve()
        )
        cls.decomposer = Decomposer()
        cls.backend_instruction_sets = {
            "Hanyuan": ["rx", "ry", "cz", "sync", "measure", "reset"],
            "Spinq": [
                "h",
                "i",
                "x",
                "y",
                "z",
                "rx",
                "ry",
                "rz",
                "p",
                "s",
                "t",
                "tdg",
                "u",
                "cx",
                "cy",
                "cz",
                "swap",
                "ccx",
                "ccz",
                "sync",
                "measure",
                "reset",
            ],
            "Uqc": ["rx", "ry", "rzz", "sync", "measure", "reset"],
            "IBM Q": ["rz", "sx", "x", "cx", "sync", "measure", "reset"],
            "IonQ": ["rxx", "rx", "ry", "rz", "sync", "measure", "reset"],
            "Nam": ["cx", "h", "rz", "sync", "measure", "reset"],
            "Origin": ["cz", "u3", "sync", "measure", "reset"],
            "Quafu": [
                "cx",
                "rx",
                "ry",
                "rz",
                "h",
                "sync",
                "measure",
                "reset",
            ],
            "USTC": [
                "cx",
                "rx",
                "ry",
                "rz",
                "h",
                "x",
                "sync",
                "measure",
                "reset",
            ],
        }

    def _parse_qasm_to_gates(self, qasm_source):
        """Parses QASM source code into a list of IR gate operations.

        Args:
            qasm_source: A string containing the OpenQASM source code.

        Returns:
            A list of gate operations extracted from the intermediate
            representation of the circuit.
        """
        parse_result, _ = convert_qasm_string_to_qcos_operations(qasm_source)
        parse_result = convert_ir_cpp2py(parse_result)
        return parse_result

    def _validate_decomposition(
        self, original_gates, target_basis, backend_name
    ):
        """Validates decomposition correctness for a specific backend.

        This method decomposes the given circuit into the target instruction
        set and performs the following checks:
        1. All gates in the decomposed circuit are supported by the backend.
        2. The decomposed circuit is semantically equivalent to the original.

        Args:
            original_gates: List of gate operations from the original circuit.
            target_basis: List of gate names supported by the target backend.
            backend_name: Human-readable name of the backend, used for logging.
        """
        source = convert_ir_py2cpp(original_gates)
        gate_name_list = list({op.name for op in original_gates})
        dict, _ = self.decomposer.get_decompose_rules(
            gate_name_list, target_basis
        )
        decomposed_gates = self.decomposer.apply_decompose_rules(source, dict)
        result = convert_ir_cpp2py(decomposed_gates)
        validate_gates_in_targets(result, target_basis)
        validate_ir_equals(original_gates, result)

        print(f"[OK] {backend_name} decomposition validated")

    def run_directory_tests(self, qasm_dir):
        """Runs decomposition tests for all QASM files in a directory.

        For each QASM file, this method:
        - Parses the circuit into IR.
        - Extracts the list of gate operations.
        - Decomposes the circuit for each supported backend.
        - Validates correctness and equivalence of the results.

        Args:
            qasm_dir: Path to a directory containing QASM benchmark files.
        """
        qasm_reader = QasmFileReader(qasm_dir)

        for qasm_path, qasm_source in qasm_reader.iter_contents():
            print(f"\n[CASE] {qasm_path}")

            original_gates = self._parse_qasm_to_gates(qasm_source)

            print(f"[IR] Gate count = {len(original_gates)}")
            print(
                f"[IR] Gate types = {sorted({g.name for g in original_gates})}"
            )

            for (
                backend_name,
                target_basis,
            ) in self.backend_instruction_sets.items():
                self._validate_decomposition(
                    original_gates,
                    target_basis,
                    backend_name,
                )

    @pytest.mark.slow
    def test_qasmbench_small_decompose(self):
        """System test for QASMBench-small circuits."""
        qasm_dir = self.samples_dir / "qasm" / "benchpress" / "qasmbench-small"

        print("\n=== [ST] QASMBench Small Decomposer Test ===")
        print(f"[INFO] qasm_dir = {qasm_dir}")

        self.run_directory_tests(qasm_dir)
