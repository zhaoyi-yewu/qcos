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
from qcos.tests.unit_tests.transpiler.comm import validate_gate_ir
from qcos.tests.unit_tests.transpiler.comm import validate_non_gate_ir


class TestGetIr:
    @classmethod
    def setup_class(cls):
        cls.data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[6];
        creg c[6];
        gate test_single(theta, phi) a{
            rx(theta) a;
            h a;
            ry(-phi) a;
            rz(theta + phi) a;
            x a;
            y a;
            z a;
            s a;
            sdg a;
            tdg a;
            t a;
        }
        gate test_two(x, y) a, b{
            test_single(x, y) a;
            cx a, b;
            cy a, b;
            cz a, b;
            ch a, b;
            crx(x) a, b;
            cry(y) a, b;
            crz(x+y) a, b;
        }
        test_two(sin(1.2), 1.3) q[2], q[3];
        ccx q[0], q[1], q[4];
        barrier q;
        measure q[1] -> c[1];
        """

    def test_get_ir(self):
        tree = get_abs_tree(self.data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 6
        assert len(ir) == 21
        validate_gate_ir(ir[0], "rx", ["2"], 1, False)
        validate_gate_ir(ir[1], "h", ["2"], 1, True)
        validate_gate_ir(ir[2], "ry", ["2"], 1, False)
        validate_gate_ir(ir[3], "rz", ["2"], 1, False)
        validate_gate_ir(ir[4], "x", ["2"], 1, True)
        validate_gate_ir(ir[5], "y", ["2"], 1, True)
        validate_gate_ir(ir[6], "z", ["2"], 1, True)
        validate_gate_ir(ir[7], "s", ["2"], 1, False)
        validate_gate_ir(ir[8], "sdg", ["2"], 1, False)
        validate_gate_ir(ir[9], "tdg", ["2"], 1, False)
        validate_gate_ir(ir[10], "t", ["2"], 1, False)
        validate_gate_ir(ir[11], "cx", ["2", "3"], 2, True)
        validate_gate_ir(ir[12], "cy", ["2", "3"], 2, True)
        validate_gate_ir(ir[13], "cz", ["2", "3"], 2, True)
        validate_gate_ir(ir[14], "ch", ["2", "3"], 2, True)
        validate_gate_ir(ir[15], "crx", ["2", "3"], 2, False)
        validate_gate_ir(ir[16], "cry", ["2", "3"], 2, False)
        validate_gate_ir(ir[17], "crz", ["2", "3"], 2, False)
        validate_gate_ir(ir[18], "ccx", ["0", "1", "4"], 3, True)
        validate_non_gate_ir(ir[19], "sync", [0, 1, 2, 3, 4, 5], -1)
        validate_non_gate_ir(ir[20], "measure", [1], 0)

    def test_swap_gate(self):
        data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        creg c[2];
        x q[0];
        swap q[0], q[1];
        measure q[0] -> c[0];
        measure q[1] -> c[1];
        """
        tree = get_abs_tree(data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 2
        assert len(ir) == 4
        validate_gate_ir(ir[0], "x", ["0"], 1, True)
        validate_gate_ir(ir[1], "swap", ["0", "1"], 2, True)
        validate_non_gate_ir(ir[2], "measure", [0], 0)
        validate_non_gate_ir(ir[3], "measure", [1], 0)

    def test_for_empty(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        for int i in [0:5] {
        }
        """
        tree = get_abs_tree(data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 0
        assert len(ir) == 0

    def test_for_gates(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qreg q[2];
        creg c[2];
        for int i in [0:2] {
            x q[1];
            h q[0];
        }
        """
        tree = get_abs_tree(data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 2
        assert len(ir) == 4
        validate_gate_ir(ir[0], "x", ["1"], 1, True)
        validate_gate_ir(ir[1], "h", ["0"], 1, True)
        validate_gate_ir(ir[2], "x", ["1"], 1, True)
        validate_gate_ir(ir[3], "h", ["0"], 1, True)

    def test_for_gates_idx(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qreg q[2];
        creg c[2];
        for int i in [0:2] {
            x q[i];
            h q[i];
        }
        """
        tree = get_abs_tree(data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 2
        assert len(ir) == 4
        validate_gate_ir(ir[0], "x", ["0"], 1, True)
        validate_gate_ir(ir[1], "h", ["0"], 1, True)
        validate_gate_ir(ir[2], "x", ["1"], 1, True)
        validate_gate_ir(ir[3], "h", ["1"], 1, True)

    def test_bracket_reg(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        int i = 0;
        qreg q[2];
        creg c[2];
        h q[i];
        h q[i+1];
        """
        tree = get_abs_tree(data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 2
        assert len(ir) == 2
        validate_gate_ir(ir[0], "h", ["0"], 1, True)
        validate_gate_ir(ir[1], "h", ["1"], 1, True)

    def test_for_array(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qreg q[5];
        creg c[5];
        array[int[32], 2] arr = {1, 3};
        for int i in arr {
           h q[i];
        }

        for int i in {2, 4} {
            h q[i];
        }
        """
        tree = get_abs_tree(data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 5
        assert len(ir) == 4
        validate_gate_ir(ir[0], "h", ["1"], 1, True)
        validate_gate_ir(ir[1], "h", ["3"], 1, True)
        validate_gate_ir(ir[2], "h", ["2"], 1, True)
        validate_gate_ir(ir[3], "h", ["4"], 1, True)

    def test_gate(self):
        data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[5];
        creg c[5];
        p(pi) q[0];
        sx q[0];
        sxdg q[1];
        cswap q[0], q[1], q[2];
        cu1(pi/2) q[0], q[1];
        cp (pi/2) q[1], q[2];
        cu3(pi/2, pi/2, pi/2) q[0], q[1];
        csx q[1], q[2];
        cu(pi/2, pi/2, pi/2,pi) q[0], q[2];
        rxx(pi/2) q[0],q[1];
        rzz(pi/2) q[0],q[1];
        rccx q[0], q[1], q[2];
        rc3x q[0], q[1], q[2], q[3];
        c3x q[0], q[1], q[2], q[3];
        c3sqrtx q[0], q[1], q[2], q[3];
        c4x q[0], q[1], q[2], q[3], q[4];
        """
        tree = get_abs_tree(data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 5
        assert len(ir) == 16
        validate_gate_ir(ir[0], "p", ["0"], 1, False)
        validate_gate_ir(ir[1], "sx", ["0"], 1, False)
        validate_gate_ir(ir[2], "sxdg", ["1"], 1, False)
        validate_gate_ir(ir[3], "cswap", ["0", "1", "2"], 3, False)
        validate_gate_ir(ir[4], "cu1", ["0", "1"], 2, False)
        validate_gate_ir(ir[5], "cp", ["1", "2"], 2, False)
        validate_gate_ir(ir[6], "cu3", ["0", "1"], 2, False)
        validate_gate_ir(ir[7], "csx", ["1", "2"], 2, False)
        validate_gate_ir(ir[8], "cu", ["0", "2"], 2, False)
        validate_gate_ir(ir[9], "rxx", ["0", "1"], 2, False)
        validate_gate_ir(ir[10], "rzz", ["0", "1"], 2, False)
        validate_gate_ir(ir[11], "rccx", ["0", "1", "2"], 3, False)
        validate_gate_ir(ir[12], "rc3x", ["0", "1", "2", "3"], 4, False)
        validate_gate_ir(ir[13], "c3x", ["0", "1", "2", "3"], 4, False)
        validate_gate_ir(ir[14], "c3sqrtx", ["0", "1", "2", "3"], 4, False)
        validate_gate_ir(ir[15], "c4x", ["0", "1", "2", "3", "4"], 5, False)
