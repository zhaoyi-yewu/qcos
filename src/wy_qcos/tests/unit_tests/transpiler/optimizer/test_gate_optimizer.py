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

import pytest
import copy

from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import pass_merge_theta
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import (
    optimize_gate,
    optimize,
)
from wy_qcos.tests.unit_tests.transpiler.comm import (
    validate_gate_ir,
    validate_non_gate_ir,
)
from wy_qcos.common.cmss.gate_operation import H, CX, X, Y, Z, S, T, SDG
from wy_qcos.common.cmss.measure import Measure


class TestGateOptimizer:
    @classmethod
    def setup_class(cls):
        cls.data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[5];
        creg c[5];
        h q[0];
        h q[0];
        x q[0];
        ry(1) q[0];
        x q[0];
        h q[0];
        x q[0];
        h q[0];
        s q[0];
        sdg q[0];
        x q[0];
        x q[0];
        cx q[1], q[0];
        cx q[1], q[0];
        ccx q[2], q[1], q[0];
        ccx q[2], q[1], q[0];
        ry(1) q[3];
        ry(2.14) q[3];
        """

        cls.merge_theta_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        creg c[2];
        h q[0];
        cx q[0], q[1];
        measure q[0] -> c[0];
        measure q[1] -> c[1];
        if (c==1) x q[1];
        """

    @pytest.mark.smoke
    def test_pass_optimize_gate(self):
        tree = get_abs_tree(self.data)
        assert tree is not None
        cir = get_ir(tree)
        q_num, gates_list = cir.num_qubits, cir.get_operations()
        assert q_num == 5
        assert len(gates_list) == 18
        opt_gates = optimize_gate(gates_list)
        assert len(opt_gates) == 3
        validate_gate_ir(opt_gates[0], "ry", [0], 1, False)
        validate_gate_ir(opt_gates[1], "z", [0], 1, True)
        validate_gate_ir(opt_gates[2], "ry", [3], 1, False)

    def test_pass_merge_theta(self):
        tree = get_abs_tree(self.merge_theta_data)
        assert tree is not None
        cir = get_ir(tree)
        q_num, gates_list = cir.num_qubits, cir.get_operations()
        assert q_num == 2
        assert len(gates_list) == 4
        validate_gate_ir(gates_list[0], "h", [0], 1, True)
        validate_gate_ir(gates_list[1], "cx", [0, 1], 2, True)
        assert pass_merge_theta(gates_list) is False

    def test_optimize(self):
        tree = get_abs_tree(self.data)
        assert tree is not None
        cir = get_ir(tree)
        q_num, gates_list = cir.num_qubits, cir.get_operations()
        assert q_num == 5
        assert len(gates_list) == 18
        opt_gates = optimize(gates_list, opt_level=2)
        assert len(opt_gates) == 3
        validate_gate_ir(opt_gates[0], "ry", [0], 1, False)
        validate_gate_ir(opt_gates[1], "z", [0], 1, True)
        validate_gate_ir(opt_gates[2], "ry", [3], 1, False)

    def test_optimizer_with_multi_barrier(self):
        simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[6];
        creg c[6];
        ccx q[0], q[1], q[4];
        barrier q;
        barrier q;
        measure q[1] -> c[1];
        """

        tree = get_abs_tree(simple_data)
        assert tree is not None

        cir = get_ir(tree)
        gates_list = cir.get_operations()

        validate_gate_ir(gates_list[0], "ccx", [0, 1, 4], 3, True)
        validate_non_gate_ir(gates_list[1], "sync", [0, 1, 2, 3, 4, 5], -1)
        validate_non_gate_ir(gates_list[2], "sync", [0, 1, 2, 3, 4, 5], -1)

        opt_gates = optimize_gate(gates_list)
        validate_gate_ir(opt_gates[0], "ccx", [0, 1, 4], 3, True)
        validate_non_gate_ir(opt_gates[1], "sync", [0, 1, 2, 3, 4, 5], -1)
        validate_non_gate_ir(opt_gates[2], "sync", [0, 1, 2, 3, 4, 5], -1)


def _measure_indices(gates: list) -> list:
    """Return indices of measure gates in the list."""
    return [i for i, op in enumerate(gates) if op.name == "measure"]


def _has_measure_before_last_gate(gates: list) -> bool:
    """Check if any measure gate appears before the last non-measure gate."""
    measure_idx = _measure_indices(gates)
    if not measure_idx:
        return False
    first_measure = measure_idx[0]
    return any(
        op.name not in ("measure", "sync", "barrier")
        for op in gates[first_measure:]
    )


class TestOptimizeMeasurePlacement:
    """Verify optimize() does not move measure gates before other gates."""

    @pytest.mark.smoke
    def test_measure_at_end_opt1(self):
        """opt_level=1 should keep measure gates at the end."""
        gates = [
            H([0]),
            H([1]),
            CX([0, 1]),
            H([0]),
            H([1]),
            Measure([0]),
            Measure([1]),
        ]
        result = optimize(gates, opt_level=1)
        assert not _has_measure_before_last_gate(result)
        assert _measure_indices(result) == [len(result) - 2, len(result) - 1]

    def test_measure_at_end_opt2(self):
        """opt_level=2 should keep measure gates at the end."""
        gates = [
            H([0]),
            H([1]),
            CX([0, 1]),
            H([0]),
            H([1]),
            X([0]),
            X([0]),
            Measure([0]),
            Measure([1]),
        ]
        result = optimize(gates, opt_level=2)
        assert not _has_measure_before_last_gate(result)

    def test_measure_at_end_opt3(self):
        """opt_level=3 should keep measure gates at the end."""
        gates = [
            H([0]),
            H([1]),
            CX([0, 1]),
            H([0]),
            H([1]),
            S([0]),
            T([1]),
            SDG([0]),
            Measure([0]),
            Measure([1]),
        ]
        result = optimize(gates, opt_level=3)
        assert not _has_measure_before_last_gate(result)

    def test_measure_not_removed(self):
        """Measure gates should not be removed by optimization."""
        gates = [
            H([0]),
            H([1]),
            CX([0, 1]),
            H([0]),
            H([1]),
            Measure([0]),
            Measure([1]),
        ]
        result = optimize(gates, opt_level=1)
        assert len(_measure_indices(result)) == 2

    def test_measure_at_end_interleaved_qubits(self):
        """Check interleaved qubits do not cause measure to move ahead.

        Measure on q0 and q1 with gates on different qubits after measure
        in the original order should not cause measure to move ahead.
        """
        gates = [
            H([0]),
            H([1]),
            CX([0, 1]),
            H([0]),
            H([1]),
            X([0]),
            X([1]),
            H([0]),
            H([1]),
            Measure([0]),
            Measure([1]),
        ]
        result = optimize(gates, opt_level=1)
        assert not _has_measure_before_last_gate(result)

    def test_opt_level_0_unchanged(self):
        """opt_level=0 should return input unchanged."""
        gates = [
            H([0]),
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
        ]
        result = optimize(gates, opt_level=0)
        assert result is gates
        assert _measure_indices(result) == [2, 3]

    def test_measure_targets_preserved(self):
        """Measure gate targets should be preserved after optimization."""
        gates = [
            H([0]),
            H([1]),
            CX([0, 1]),
            H([0]),
            H([1]),
            Measure([0]),
            Measure([1]),
        ]
        result = optimize(gates, opt_level=1)
        measure_gates = [op for op in result if op.name == "measure"]
        assert len(measure_gates) == 2
        assert measure_gates[0].targets == [0]
        assert measure_gates[1].targets == [1]


class TestOptimizeBoundary:
    """Boundary tests for optimize() at level 1/2/3.

    Covers empty circuit, measure-only, full cancellation, idle qubits,
    single gate, non-contiguous qubits, mixed cancel/keep, and all-cancel
    without measure.
    """

    def test_empty_circuit(self):
        """No operations at all."""
        for level in range(1, 4):
            result = optimize([], opt_level=level)
            assert not result

    def test_measure_only(self):
        """Only measure, no gates to optimize."""
        ir = [Measure([1])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            assert len(result) == 1
            assert result[0].name == "measure"

    def test_all_cancel_with_measure(self):
        """H.H on same qubit cancels, measure remains."""
        ir = [H([0]), H([0]), Measure([0])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            assert len(result) == 1
            assert result[0].name == "measure"

    def test_all_cancel_no_measure(self):
        """All gates cancel, no measure left."""
        ir = [H([0]), H([0]), X([1]), X([1]), CX([0, 1]), CX([0, 1])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            assert len(result) == 0

    def test_idle_qubits(self):
        """Gates only on q0, q1/q2/q3 idle."""
        ir = [H([0]), H([0]), Measure([0])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            assert len(result) == 1
            assert result[0].name == "measure"

    def test_single_gate(self):
        """Single gate, nothing to cancel."""
        ir = [H([1])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            assert len(result) == 1
            assert result[0].name == "h"

    def test_non_contiguous_qubits(self):
        """CX on q0,q3 (q1,q2 idle), cancel pair."""
        ir = [CX([0, 3]), CX([0, 3]), Measure([0])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            assert len(result) == 1
            assert result[0].name == "measure"

    def test_mixed_cancel_keep(self):
        """H.H on q0 cancels, X on q1 stays."""
        ir = [H([0]), H([0]), X([1])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            names = [op.name for op in result]
            assert "h" not in names
            assert any(op.name == "x" for op in result)

    def test_multi_qubit_all_cancel(self):
        """Multiple qubit pairs all cancel."""
        ir = [
            H([0]),
            H([0]),
            X([1]),
            X([1]),
            Y([2]),
            Y([2]),
            Z([3]),
            Z([3]),
        ]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            assert len(result) == 0

    def test_measure_not_modified(self):
        """Measure targets preserved after optimization."""
        ir = [H([1]), H([1]), Measure([1])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            m = [op for op in result if op.name == "measure"]
            assert len(m) == 1
            assert m[0].targets == [1]

    def test_odd_count_self_inverse(self):
        """Three H gates on same qubit: cancel 2, keep 1."""
        ir = [H([1]), H([1]), H([1])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            h_count = sum(1 for op in result if op.name == "h")
            assert h_count == 1

    def test_different_qargs_no_cancel(self):
        """CX[0,1] and CX[1,0] do not cancel."""
        ir = [CX([0, 1]), CX([1, 0])]
        for level in range(1, 4):
            result = optimize(copy.deepcopy(ir), opt_level=level)
            cx_count = sum(1 for op in result if op.name == "cx")
            assert cx_count == 2
