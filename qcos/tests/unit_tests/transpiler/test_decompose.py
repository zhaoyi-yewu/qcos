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

import numpy as np

from qcos.transpiler.cmss.common.base_operation import OperationType
from qcos.transpiler.cmss.common.gate_operation import GateOperation
from qcos.transpiler.cmss.common.gate_operation import create_gate
from qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.tests.unit_tests.transpiler.comm import validate_gate_ir
from qcos.tests.unit_tests.transpiler.comm import validate_non_gate_ir


def validate_gate(actual: GateOperation, name: str, targets: list, arg: list):
    assert actual.name == name
    assert actual.targets == targets
    assert actual.arg_value == arg


class TestDecompose:
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

        cls.simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """

    def test_decompose(self):
        tree = get_abs_tree(self.data)
        assert tree is not None

        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 6
        assert len(ir) == 21

        decomposed_gates = decompose_gates(ir)
        assert len(decomposed_gates) == 85
        validate_gate_ir(decomposed_gates[0], "rx", ["2"], 1, False)
        validate_gate_ir(decomposed_gates[1], "ry", ["2"], 1, False)
        validate_gate_ir(decomposed_gates[4], "rz", ["2"], 1, False)
        validate_gate_ir(decomposed_gates[7], "ry", ["2"], 1, False)
        validate_gate_ir(decomposed_gates[21], "cx", ["2", "3"], 2, True)
        validate_gate_ir(decomposed_gates[24], "rx", ["3"], 1, False)
        validate_gate_ir(decomposed_gates[27], "cx", ["2", "3"], 2, True)
        validate_gate_ir(decomposed_gates[53], "rz", ["3"], 1, False)
        validate_gate_ir(decomposed_gates[62], "cx", ["2", "3"], 2, True)

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
        validate_gate_ir(opt_gates[0], "rx", ["2"], 1, False)
        validate_gate_ir(opt_gates[1], "ry", ["2"], 1, False)
        validate_gate_ir(opt_gates[4], "rz", ["2"], 1, False)
        validate_gate_ir(opt_gates[7], "rx", ["2"], 1, False)
        validate_gate_ir(opt_gates[22], "cx", ["2", "3"], 2, True)
        validate_gate_ir(opt_gates[24], "rx", ["3"], 1, False)
        validate_gate_ir(opt_gates[29], "cx", ["2", "3"], 2, True)
        validate_gate_ir(opt_gates[47], "rz", ["3"], 1, False)
        validate_gate_ir(opt_gates[52], "cx", ["2", "3"], 2, True)

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
        validate_gate_ir(opt_gates[0], "rx", ["0"], 1, False)
        validate_non_gate_ir(opt_gates[1], "measure", [0], 0)

    def test_optimizer_simple_with_reset(self):
        simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        reset q[0];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """

        tree = get_abs_tree(simple_data)
        assert tree is not None

        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 1
        assert len(ir) == 6
        validate_gate_ir(ir[0], "h", ["0"], 1, True)
        validate_non_gate_ir(ir[1], "reset", [0], -3)

        opt_gates = optimize_gate(ir)
        assert len(opt_gates) == 6
        validate_gate_ir(opt_gates[0], "h", ["0"], 1, True)
        validate_non_gate_ir(opt_gates[1], "reset", [0], -3)

        decomposed_gates = decompose_gates(opt_gates)
        assert len(decomposed_gates) == 8
        validate_gate_ir(decomposed_gates[0], "ry", ["0"], 1, False)
        validate_gate_ir(decomposed_gates[1], "rx", ["0"], 1, False)
        validate_non_gate_ir(decomposed_gates[2], "reset", [0], -3)
        opt_gates = optimize_gate(decomposed_gates)

        assert len(opt_gates) == 6
        validate_gate_ir(opt_gates[0], "ry", ["0"], 1, False)
        validate_gate_ir(opt_gates[1], "rx", ["0"], 1, False)
        validate_non_gate_ir(opt_gates[2], "reset", [0], -3)
        validate_non_gate_ir(opt_gates[5], "measure", [0], 0)

    def test_optimizer_defined_gate_with_reset(self):
        simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[6];
        creg c[6];
        gate test_single(theta) a{
            rx(theta) a;
            rx(theta) a;
            reset a;
        }
        gate test_two(x) a, b{
            test_single(x) a;
            test_single(x) b;
        }
        test_two(1.3) q[2], q[3];
        ccx q[0], q[1], q[4];
        barrier q;
        measure q[1] -> c[1];
        """

        tree = get_abs_tree(simple_data)
        assert tree is not None

        q_num, ir = get_ir(tree)
        assert ir is not None
        assert len(ir) == 9
        validate_gate_ir(ir[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(ir[2], "reset", ["2"], -3)
        validate_gate_ir(ir[3], "rx", ["3"], 1, False)
        validate_non_gate_ir(ir[5], "reset", ["3"], -3)
        validate_non_gate_ir(ir[7], "sync", [0, 1, 2, 3, 4, 5], -1)

        opt_gates = optimize_gate(ir)
        assert opt_gates is not None
        assert len(opt_gates) == 7
        validate_gate_ir(opt_gates[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(opt_gates[1], "reset", ["2"], -3)
        validate_gate_ir(opt_gates[2], "rx", ["3"], 1, False)
        validate_non_gate_ir(opt_gates[3], "reset", ["3"], -3)
        validate_non_gate_ir(opt_gates[5], "sync", [0, 1, 2, 3, 4, 5], -1)

        decomp_gates = decompose_gates(opt_gates)
        assert decomp_gates is not None
        assert len(decomp_gates) == 23
        validate_gate_ir(decomp_gates[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(decomp_gates[1], "reset", ["2"], -3)
        validate_gate_ir(decomp_gates[2], "rx", ["3"], 1, False)
        validate_non_gate_ir(decomp_gates[3], "reset", ["3"], -3)
        validate_gate_ir(decomp_gates[6], "cx", ["1", "4"], 2, True)
        validate_non_gate_ir(decomp_gates[21], "sync", [0, 1, 2, 3, 4, 5], -1)

        opt_gates = optimize_gate(decomp_gates)
        assert opt_gates is not None
        assert len(opt_gates) == 23
        validate_gate_ir(opt_gates[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(opt_gates[1], "reset", ["2"], -3)
        validate_gate_ir(opt_gates[2], "rx", ["3"], 1, False)
        validate_non_gate_ir(opt_gates[3], "reset", ["3"], -3)
        validate_gate_ir(opt_gates[6], "cx", ["1", "4"], 2, True)
        validate_non_gate_ir(opt_gates[21], "sync", [0, 1, 2, 3, 4, 5], -1)

    def test_optimizer_simple_with_barrier(self):
        simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        barrier q[0];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """

        tree = get_abs_tree(simple_data)
        assert tree is not None

        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 1
        assert len(ir) == 6
        validate_gate_ir(ir[0], "h", ["0"], 1, True)
        validate_non_gate_ir(ir[1], "sync", [0], -1)

        opt_gates = optimize_gate(ir)
        assert len(opt_gates) == 6
        validate_gate_ir(opt_gates[0], "h", ["0"], 1, True)
        validate_non_gate_ir(opt_gates[1], "sync", [0], -1)

        decomposed_gates = decompose_gates(opt_gates)
        assert len(decomposed_gates) == 8
        validate_gate_ir(decomposed_gates[0], "ry", ["0"], 1, False)
        validate_gate_ir(decomposed_gates[1], "rx", ["0"], 1, False)
        validate_non_gate_ir(decomposed_gates[2], "sync", [0], -1)

        opt_gates = optimize_gate(decomposed_gates)
        assert len(opt_gates) == 6
        validate_gate_ir(opt_gates[0], "ry", ["0"], 1, False)
        validate_gate_ir(opt_gates[1], "rx", ["0"], 1, False)
        validate_non_gate_ir(opt_gates[2], "sync", [0], -1)
        validate_non_gate_ir(opt_gates[5], "measure", [0], 0)

    def test_optimizer_defined_gate_with_barrier(self):
        simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[6];
        creg c[6];
        gate test_single(theta) a{
            rx(theta) a;
            rx(theta) a;
            barrier a;
        }

        gate test_two(x) a, b{
            test_single(x) a;
            test_single(x) b;
        }

        test_two(1.3) q[2], q[3];
        ccx q[0], q[1], q[4];
        barrier q;
        measure q[1] -> c[1];
        """

        tree = get_abs_tree(simple_data)
        assert tree is not None

        q_num, ir = get_ir(tree)
        assert ir is not None
        assert len(ir) == 9
        validate_gate_ir(ir[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(ir[2], "sync", ["2"], -1)
        validate_gate_ir(ir[3], "rx", ["3"], 1, False)
        validate_non_gate_ir(ir[5], "sync", ["3"], -1)
        validate_non_gate_ir(ir[7], "sync", [0, 1, 2, 3, 4, 5], -1)

        opt_gates = optimize_gate(ir)
        assert opt_gates is not None
        assert len(opt_gates) == 7
        validate_gate_ir(opt_gates[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(opt_gates[1], "sync", ["2"], -1)
        validate_gate_ir(opt_gates[2], "rx", ["3"], 1, False)
        validate_non_gate_ir(opt_gates[3], "sync", ["3"], -1)
        validate_non_gate_ir(opt_gates[5], "sync", [0, 1, 2, 3, 4, 5], -1)

        decomp_gates = decompose_gates(opt_gates)
        assert decomp_gates is not None
        assert len(decomp_gates) == 23
        validate_gate_ir(decomp_gates[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(decomp_gates[1], "sync", ["2"], -1)
        validate_gate_ir(decomp_gates[2], "rx", ["3"], 1, False)
        validate_non_gate_ir(decomp_gates[3], "sync", ["3"], -1)
        validate_gate_ir(decomp_gates[6], "cx", ["1", "4"], 2, True)
        validate_non_gate_ir(decomp_gates[21], "sync", [0, 1, 2, 3, 4, 5], -1)

        opt_gates = optimize_gate(decomp_gates)
        assert opt_gates is not None
        assert len(opt_gates) == 23
        validate_gate_ir(opt_gates[0], "rx", ["2"], 1, False)
        validate_non_gate_ir(opt_gates[1], "sync", ["2"], -1)
        validate_gate_ir(opt_gates[2], "rx", ["3"], 1, False)
        validate_non_gate_ir(opt_gates[3], "sync", ["3"], -1)
        validate_gate_ir(opt_gates[6], "cx", ["1", "4"], 2, True)
        validate_non_gate_ir(opt_gates[21], "sync", [0, 1, 2, 3, 4, 5], -1)

    def test_create_u1(self):
        u1 = create_gate("u1", [0], [1])
        assert u1.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value
        assert u1.name == "u1"
        assert u1.hermitian is False

        decom_gate = u1.default_decompose()
        assert len(decom_gate) == 1
        validate_gate(decom_gate[0], "rz", [0], [1])

    def test_create_u2(self):
        u2 = create_gate("u2", [0], [1, 2])
        assert u2.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value
        assert u2.name == "u2"
        assert u2.hermitian is False

        decom_gate = u2.default_decompose()
        assert len(decom_gate) == 3
        validate_gate(decom_gate[0], "rz", [0], [2 - np.pi / 2])
        validate_gate(decom_gate[1], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[2], "rz", [0], [1 + np.pi / 2])

    def test_create_u3(self):
        u3 = create_gate("u3", [0], [1, 2, 3])
        assert u3.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value
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
                ],
            }
        }

        trans_cfg_inst.set_decompose_rule(config)
        u3 = create_gate("u3", [0], [1, 2, 3])
        assert u3.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value
        assert u3.name == "u3"
        assert u3.hermitian is False

        decom_gate = u3.decompose()
        assert len(decom_gate) == 5
        validate_gate(decom_gate[0], "rz", [0], [3])
        validate_gate(decom_gate[1], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[2], "rz", [0], [2 + np.pi])
        validate_gate(decom_gate[3], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[4], "rz", [0], [1 + np.pi])

    def test_swap_decompose(self):
        swap = create_gate("swap", [0, 1], [])
        assert (
            swap.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        )
        assert swap.name == "swap"
        assert swap.hermitian is True
        decom_gate = swap.decompose()
        assert len(decom_gate) == 3
        validate_gate(decom_gate[0], "cx", [0, 1], [])
        validate_gate(decom_gate[1], "cx", [1, 0], [])
        validate_gate(decom_gate[2], "cx", [0, 1], [])

    def test_p_decompose(self):
        p = create_gate("p", [0], [np.pi])
        assert p.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value
        assert p.name == "p"
        assert p.hermitian is False
        decom_gate = p.decompose()
        assert len(decom_gate) == 1
        validate_gate(decom_gate[0], "rz", [0], [np.pi])

    def test_sx_decompose(self):
        sx = create_gate("sx", [0], [])
        assert sx.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value
        assert sx.name == "sx"
        assert sx.hermitian is False
        decom_gate = sx.decompose()
        assert len(decom_gate) == 8
        validate_gate(decom_gate[0], "rx", [0], [3 * np.pi / 2])
        validate_gate(decom_gate[1], "ry", [0], [3 * np.pi / 2])
        validate_gate(decom_gate[2], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[3], "ry", [0], [np.pi / 2])
        validate_gate(decom_gate[4], "rx", [0], [np.pi])
        validate_gate(decom_gate[5], "rx", [0], [3 * np.pi / 2])
        validate_gate(decom_gate[6], "ry", [0], [3 * np.pi / 2])
        validate_gate(decom_gate[7], "rx", [0], [np.pi / 2])

    def test_sxdg_decompose(self):
        sx = create_gate("sxdg", [0], [])
        assert sx.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value
        assert sx.name == "sxdg"
        assert sx.hermitian is False
        decom_gate = sx.decompose()
        assert len(decom_gate) == 8
        validate_gate(decom_gate[0], "rx", [0], [3 * np.pi / 2])
        validate_gate(decom_gate[1], "ry", [0], [np.pi / 2])
        validate_gate(decom_gate[2], "rx", [0], [np.pi / 2])
        validate_gate(decom_gate[3], "ry", [0], [np.pi / 2])
        validate_gate(decom_gate[4], "rx", [0], [np.pi])
        validate_gate(decom_gate[5], "rx", [0], [3 * np.pi / 2])
        validate_gate(decom_gate[6], "ry", [0], [np.pi / 2])
        validate_gate(decom_gate[7], "rx", [0], [np.pi / 2])

    def test_cswap_decompose(self):
        cswap = create_gate("cswap", [0, 1, 2], [])
        assert (
            cswap.operation_type == OperationType.TRIPLE_QUBIT_OPERATION.value
        )
        assert cswap.name == "cswap"
        assert cswap.hermitian is False
        decom_gate = cswap.decompose()
        assert len(decom_gate) == 19

    def test_cu1_decompose(self):
        cu1 = create_gate("cu1", [0, 1], [np.pi / 2])
        assert cu1.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        assert cu1.name == "cu1"
        assert cu1.hermitian is False
        decom_gate = cu1.decompose()
        assert len(decom_gate) == 5

    def test_cp_decompose(self):
        cp = create_gate("cp", [0, 1], [np.pi / 2])
        assert cp.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        assert cp.name == "cp"
        assert cp.hermitian is False
        decom_gate = cp.decompose()
        assert len(decom_gate) == 5

    def test_cu3_decompose(self):
        cu3 = create_gate("cu3", [0, 1], [1, 2, 3])
        assert cu3.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        assert cu3.name == "cu3"
        assert cu3.hermitian is False
        decom_gate = cu3.decompose()
        assert len(decom_gate) == 14

    def test_csx_decompose(self):
        csx = create_gate("csx", [0, 1], [])
        assert csx.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        assert csx.name == "csx"
        assert csx.hermitian is False
        decom_gate = csx.decompose()
        assert len(decom_gate) == 9

    def test_cu_decompose(self):
        cu = create_gate("cu", [0, 1], [np.pi, np.pi, np.pi, np.pi / 2])
        assert cu.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        assert cu.name == "cu"
        assert cu.hermitian is False
        decom_gate = cu.decompose()
        assert len(decom_gate) == 15

    def test_rxx_decompose(self):
        rxx = create_gate("rxx", [0, 1], [np.pi / 2])
        assert rxx.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        assert rxx.name == "rxx"
        assert rxx.hermitian is False
        decom_gate = rxx.decompose()
        assert len(decom_gate) == 15

    def test_rzz_decompose(self):
        rzz = create_gate("rzz", [0, 1], [np.pi / 2])
        assert rzz.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value
        assert rzz.name == "rzz"
        assert rzz.hermitian is False
        decom_gate = rzz.decompose()
        assert len(decom_gate) == 3

    def test_rccx_decompose(self):
        rccx = create_gate("rccx", [0, 1, 2])
        assert (
            rccx.operation_type == OperationType.TRIPLE_QUBIT_OPERATION.value
        )
        assert rccx.name == "rccx"
        assert rccx.hermitian is False
        decom_gate = rccx.decompose()
        assert len(decom_gate) == 13

    def test_rc3x_decompose(self):
        rc3x = create_gate("rc3x", [0, 1, 2, 3])
        assert rc3x.operation_type == OperationType.FOUR_QUBIT_OPERATION.value
        assert rc3x.name == "rc3x"
        assert rc3x.hermitian is False
        decom_gate = rc3x.decompose()
        assert len(decom_gate) == 26

    def test_c3x_decompose(self):
        c3x = create_gate("c3x", [0, 1, 2, 3])
        assert c3x.operation_type == OperationType.FOUR_QUBIT_OPERATION.value
        assert c3x.name == "c3x"
        assert c3x.hermitian is False
        decom_gate = c3x.decompose()
        assert len(decom_gate) == 33

    def test_c3sqrtx_decompose(self):
        c3sqrtx = create_gate("c3sqrtx", [0, 1, 2, 3])
        assert (
            c3sqrtx.operation_type == OperationType.FOUR_QUBIT_OPERATION.value
        )
        assert c3sqrtx.name == "c3sqrtx"
        assert c3sqrtx.hermitian is False
        decom_gate = c3sqrtx.decompose()
        assert len(decom_gate) == 69

    def test_c4x_decompose(self):
        c4x = create_gate("c4x", [0, 1, 2, 3, 4])
        assert c4x.operation_type == OperationType.FIVE_QUBIT_OPERATION.value
        assert c4x.name == "c4x"
        assert c4x.hermitian is False
        decom_gate = c4x.decompose()
        assert len(decom_gate) == 153

    def test_create_rx_exception(self):
        try:
            create_gate("rx", [0, 1], [1, 2, 3])
        except Exception as e:
            print(f"Exception: {e}")
