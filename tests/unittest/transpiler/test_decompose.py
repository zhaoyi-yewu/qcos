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

import numpy as np

from qcos.common.config import Config
from qcos.transpiler.cmss.common.gate import Gate, GateType, create_gate
from qcos.transpiler.cmss.common.gate import U1, U2, U3
from qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate


def validate_ir(actual: Gate, name: str, targets: list, q_type: int,
                q_hermitian: bool):
    assert actual.hermitian == q_hermitian
    assert actual.name == name
    assert actual.targets == targets
    assert actual.type == q_type


def validate_gate(actual: Gate, name: str, targets: list, arg: list):
    assert actual.name == name
    assert actual.targets == targets
    assert actual.arg_value == arg


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
        decomposed_gates = decompose_gates(ir)
        assert len(decomposed_gates) == 85
        validate_ir(decomposed_gates[0], "rx", ["2"], 1, False)
        validate_ir(decomposed_gates[1], "ry", ["2"], 1, False)
        validate_ir(decomposed_gates[4], "rz", ["2"], 1, False)
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
        decomposed_gates = decompose_gates(ir)
        assert len(decomposed_gates) == 85
        opt_gates = optimize_gate(decomposed_gates)
        assert len(opt_gates) == 77
        validate_ir(opt_gates[0], "rx", ["2"], 1, False)
        validate_ir(opt_gates[1], "ry", ["2"], 1, False)
        validate_ir(opt_gates[4], "rz", ["2"], 1, False)
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
        opt_gates = optimize_gate(ir)
        assert len(opt_gates) == 3
        decomposed_gates = decompose_gates(opt_gates)
        assert len(decomposed_gates) == 3
        opt_gates = optimize_gate(decomposed_gates)
        assert len(opt_gates) == 2
        validate_ir(opt_gates[0], "rx", ["0"], 1, False)
        validate_ir(opt_gates[1], "measure", [0], 0, False)

    def test_create_u1(self):
        u1 = create_gate("u1", [0], [1])
        assert u1.type == GateType.SINGLE_QUBIT_GATE.value
        assert u1.name == "u1"
        assert u1.hermitian is False

        decom_gate = u1.default_decompose()
        assert len(decom_gate) == 1
        validate_gate(decom_gate[0], "rz", [0], [1])

    def test_create_u2(self):
        u2 = create_gate("u2", [0], [1, 2])
        assert u2.type == GateType.SINGLE_QUBIT_GATE.value
        assert u2.name == "u2"
        assert u2.hermitian is False

        decom_gate = u2.default_decompose()
        assert len(decom_gate) == 3
        validate_gate(decom_gate[0], "rz", [0], [2 - np.pi / 2])
        validate_gate(decom_gate[1], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[2], "rz", [0], [1 + np.pi / 2])

    def test_create_u3(self):
        u3 = create_gate("u3", [0], [1, 2, 3])
        assert u3.type == GateType.SINGLE_QUBIT_GATE.value
        assert u3.name == "u3"
        assert u3.hermitian is False

        decom_gate = u3.default_decompose()
        assert len(decom_gate) == 5
        validate_gate(decom_gate[0], "rz", [0], [3])
        validate_gate(decom_gate[1], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[2], "rz", [0], [1 + np.pi])
        validate_gate(decom_gate[3], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[4], "rz", [0], [2 + 3 * np.pi])

    def test_u3_decompose(self):
        config = {
            "u3": {
                "params": ["a", "b", "c"],
                "gates": [
                    ("rz", [0], ["c"]),
                    ("rx", [0], ["pi/2"]),
                    ("rz", [0], ["b+pi"]),
                    ("rx", [0], ["pi/2"]),
                    ("rz", [0], ["a+pi"]),
                ]
            }
        }

        Config.DECOMPOSE_RULE = config
        u3 = create_gate("u3", [0], [1, 2, 3])
        assert u3.type == GateType.SINGLE_QUBIT_GATE.value
        assert u3.name == "u3"
        assert u3.hermitian is False

        decom_gate = u3.decompose()
        assert len(decom_gate) == 5
        validate_gate(decom_gate[0], "rz", [0], [3])
        validate_gate(decom_gate[1], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[2], "rz", [0], [2 + np.pi])
        validate_gate(decom_gate[3], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[4], "rz", [0], [1 + np.pi])
