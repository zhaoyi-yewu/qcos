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

import os
import pytest

from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.transpiler.cmss.common.qasm_converter import QasmConverter


class TestQasmConverter:
    @pytest.mark.smoke
    def test_single_qubit_gates(self):
        openqasm2_header = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[6];
creg c[6];
"""
        openqasm3_header = """OPENQASM 3.0;
include "stdgates.inc";
qubit[6] q;
bit[6] c;
"""
        body = """
h q[0];
x q[1];
y q[2];
z q[3];
s q[4];
sdg q[5];
t q[0];
tdg q[1];
sx q[2];
sxdg q[3];
p(1.57079632679) q[4];
u1(1.57079632679) q[5];
u2(1.57079632679, 3.14159265359) q[0];
u3(1.57079632679, 0.78539816339, 0.39269908169) q[1];"""
        openqasm2_data = openqasm2_header + body
        tree = get_abs_tree(openqasm2_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm2()
        assert qasm == openqasm2_data

        openqasm3_data = openqasm3_header + body
        tree = get_abs_tree(openqasm3_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm3()
        assert qasm == openqasm3_data

    def test_two_qubit_gates(self):
        openqasm2_header = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[7];
creg c[7];
"""
        openqasm3_header = """OPENQASM 3.0;
include "stdgates.inc";
qubit[7] q;
bit[7] c;
"""
        body = """
cx q[0], q[1];
cy q[1], q[2];
cz q[2], q[3];
ch q[3], q[4];
swap q[4], q[5];
crx(1.57079632679) q[5], q[6];
cry(1.57079632679) q[0], q[1];
crz(1.0471975512) q[1], q[2];
cu1(0.78539816339) q[2], q[3];
cp(0.62831853072) q[3], q[4];
cu3(1.57079632679, 0.78539816339, 0.39269908169) q[4], q[5];
csx q[5], q[6];
cu(1.57079632679, 0.78539816339, 0.39269908169, 0.19634954079) q[0], q[1];
rxx(1.57079632679) q[1], q[2];
rzz(1.0471975512) q[2], q[3];"""

        openqasm2_data = openqasm2_header + body
        tree = get_abs_tree(openqasm2_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm2()
        assert qasm == openqasm2_data

        openqasm3_data = openqasm3_header + body
        tree = get_abs_tree(openqasm3_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm3()
        assert qasm == openqasm3_data

    def test_three_qubit_gates(self):
        openqasm2_header = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
"""
        openqasm3_header = """OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
bit[3] c;
"""
        body = """
ccx q[0], q[1], q[2];
cswap q[0], q[1], q[2];
rccx q[0], q[1], q[2];"""

        openqasm2_data = openqasm2_header + body
        tree = get_abs_tree(openqasm2_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm2()
        assert qasm == openqasm2_data

        openqasm3_data = openqasm3_header + body
        tree = get_abs_tree(openqasm3_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm3()
        assert qasm == openqasm3_data

    def test_four_qubit_gates(self):
        openqasm2_header = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
"""
        openqasm3_header = """OPENQASM 3.0;
include "stdgates.inc";
qubit[4] q;
bit[4] c;
"""
        body = """
rc3x q[0], q[1], q[2], q[3];
c3x q[0], q[1], q[2], q[3];
c3sqrtx q[0], q[1], q[2], q[3];"""

        openqasm2_data = openqasm2_header + body
        tree = get_abs_tree(openqasm2_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm2()
        assert qasm == openqasm2_data

        openqasm3_data = openqasm3_header + body
        tree = get_abs_tree(openqasm3_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm3()
        assert qasm == openqasm3_data

    def test_five_qubit_gates(self):
        openqasm2_header = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
creg c[5];
"""
        openqasm3_header = """OPENQASM 3.0;
include "stdgates.inc";
qubit[5] q;
bit[5] c;
"""
        body = """
c4x q[0], q[1], q[2], q[3], q[4];"""

        openqasm2_data = openqasm2_header + body
        tree = get_abs_tree(openqasm2_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm2()
        assert qasm == openqasm2_data

        openqasm3_data = openqasm3_header + body
        tree = get_abs_tree(openqasm3_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm3()
        assert qasm == openqasm3_data

    def test_reset_measure(self):
        openqasm2_header = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
"""
        openqasm3_header = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
"""
        body = """
reset q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];"""

        openqasm2_data = openqasm2_header + body
        tree = get_abs_tree(openqasm2_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm2()
        assert qasm == openqasm2_data

        openqasm3_data = openqasm3_header + body
        tree = get_abs_tree(openqasm3_data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm3()
        assert qasm == openqasm3_data

    def test_parametric_for_loop(self):
        data = """OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
bit[3] c;

for int k in [0:3] {
    rz(0.1 * k) q[k];
}
"""
        expected_qasm = """OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
bit[3] c;

rz(0.0) q[0];
rz(0.1) q[1];
rz(0.2) q[2];"""

        tree = get_abs_tree(data)
        assert tree is not None
        ir = get_ir(tree)
        assert ir is not None
        converter = QasmConverter(ir)
        qasm = converter.to_qasm3()
        assert qasm == expected_qasm

        converter.save("test.qasm")
        os.remove("test.qasm")
