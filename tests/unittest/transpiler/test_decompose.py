#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.transpiler.cmss.compiler import get_abs_tree, get_ir, decomposer
from qcos.transpiler.cmss.compiler import optimizer
from qcos.transpiler.cmss.compiler import Gate


def validate_ir(actual: Gate, name: str, targets: list, q_type: int,
                q_hermitian: bool):
    assert actual.hermitian == q_hermitian
    assert actual.name == name
    assert actual.targets == targets
    assert actual.type == q_type


class TestDecompose:
    @classmethod
    def setup_class(cls):
        cls.data = '''
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
        '''

        cls.simple_data = '''
          OPENQASM 2.0;
          include "qelib1.inc";
          qreg q[1];
          creg c[1];
          h q[0];
          h q[0];
          x q[0];
          rx(1) q[0];
          measure q->c;
        '''

    def test_decompose(self):
        tree = get_abs_tree(self.data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 6
        assert len(ir) == 21
        decomposed_gates = decomposer(ir)
        assert len(decomposed_gates) == 85
        validate_ir(decomposed_gates[0], "rx", ["2"], 1, False)
        validate_ir(decomposed_gates[1], "ry", ["2"], 1, False)
        validate_ir(decomposed_gates[4], "rz", ["2"],1, False)
        validate_ir(decomposed_gates[7], "ry", ["2"], 1, False)
        validate_ir(decomposed_gates[21], "cx", ["2", "3"], 2, True)
        validate_ir(decomposed_gates[24], "rx", ["3"], 1, False)
        validate_ir(decomposed_gates[27], "cx", ["2", "3"], 2, True)
        validate_ir(decomposed_gates[53], "rz", ["3"], 1, False)
        validate_ir(decomposed_gates[62], "cx", ["2", "3"], 2, True)

    def test_optimizer(self):
        tree = get_abs_tree(self.data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 6
        assert len(ir) == 21
        decomposed_gates = decomposer(ir)
        assert len(decomposed_gates) == 85
        opt_gates = optimizer(decomposed_gates)
        assert len(opt_gates) == 77
        validate_ir(opt_gates[0], "rx", ["2"], 1, False)
        validate_ir(opt_gates[1], "ry", ["2"], 1, False)
        validate_ir(opt_gates[4], "rz", ["2"],1, False)
        validate_ir(opt_gates[7], "rx", ["2"], 1, False)
        validate_ir(opt_gates[22], "cx", ["2", "3"], 2, True)
        validate_ir(opt_gates[24], "rx", ["3"], 1, False)
        validate_ir(opt_gates[29], "cx", ["2", "3"], 2, True)
        validate_ir(opt_gates[47], "rz", ["3"], 1, False)
        validate_ir(opt_gates[52], "cx", ["2", "3"], 2, True)

    def test_optimizer_simple(self):
        tree = get_abs_tree(self.simple_data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 1
        assert len(ir) == 5
        opt_gates = optimizer(ir)
        assert len(opt_gates) == 3
        decomposed_gates = decomposer(opt_gates)
        assert len(decomposed_gates) == 3
        opt_gates = optimizer(decomposed_gates)
        assert len(opt_gates) == 2
        validate_ir(opt_gates[0], "rx", ["0"], 1, False)
        validate_ir(opt_gates[1], "measure", [0], 0, False)
