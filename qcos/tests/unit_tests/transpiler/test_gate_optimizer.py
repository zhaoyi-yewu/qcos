#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.optimizer.gate_optimizer import pass_merge_theta
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from qcos.tests.unit_tests.transpiler.comm import validate_gate_ir


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

    def test_pass_optimize_gate(self):
        tree = get_abs_tree(self.data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 5
        assert len(ir) == 18
        opt_gates = optimize_gate(ir)
        assert len(opt_gates) == 3
        validate_gate_ir(opt_gates[0], "ry", ["0"], 1, False)
        validate_gate_ir(opt_gates[1], "z", ["0"], 1, True)
        validate_gate_ir(opt_gates[2], "ry", ["3"], 1, False)

    def test_pass_merge_theta(self):
        tree = get_abs_tree(self.merge_theta_data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 2
        assert len(ir) == 4
        validate_gate_ir(ir[0], "h", ["0"], 1, True)
        validate_gate_ir(ir[1], "cx", ["0", "1"], 2, True)
        assert pass_merge_theta(ir) is False
