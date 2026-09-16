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

"""Unit tests for optimize_comparison benchmark utilities."""

import io
from pathlib import Path

from wy_qcos.transpiler.cmss.optimizer.optimize_comparison import (
    _write_pass_timings_detail,
    compare_single,
    run_benchmark,
)


class TestOptimizeComparison:
    """Unit tests for optimize_comparison benchmark utilities."""

    @classmethod
    def setup_class(cls):
        """Resolve the project root for locating sample QASM files."""
        cls.project_root = Path(__file__).resolve().parents[6]

    def test_compare_single(self):
        """Verify the full pipeline on qft_n4."""
        qasm_path = (
            self.project_root
            / "samples"
            / "qasm"
            / "benchpress"
            / "qasmbench-small"
            / "qft_n4"
            / "qft_n4.qasm"
        )
        assert qasm_path.is_file(), f"missing: {qasm_path}"
        result = compare_single(qasm_path)
        assert result["num_qubits"] > 0
        assert result["base_gate_count"] > 0
        assert result["cpp_opt_gate_count"] > 0
        assert result["qiskit_opt_gate_count"] > 0
        assert result["cpp_opt_gate_count"] <= result["base_gate_count"]
        assert result["qiskit_opt_gate_count"] <= result["base_gate_count"]

    def test_run_benchmark(self):
        """Verify run_benchmark on a small QASM directory."""
        qasm_dir = (
            self.project_root
            / "samples"
            / "qasm"
            / "benchpress"
            / "qasmbench-small"
        )
        assert qasm_dir.is_dir(), f"missing: {qasm_dir}"

        fh = io.StringIO()
        results, errors = run_benchmark(qasm_dir, max_lines=20, fh=fh)

        assert len(results) > 0
        assert len(errors) == 0
        output = fh.getvalue()
        assert "cmss_cpp" in output
        assert "qiskit" in output

        timings_fh = io.StringIO()
        _write_pass_timings_detail(results, timings_fh)
        assert "Per-Circuit" in timings_fh.getvalue()
