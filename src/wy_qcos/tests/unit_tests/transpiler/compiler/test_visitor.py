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

from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree
from wy_qcos.transpiler.cmss.compiler.qtypes import RegType
from wy_qcos.transpiler.cmss.compiler.visitor import Visitor
from wy_qcos.transpiler.cmss.compiler.qtypes import Node


class TestVisitor:
    @classmethod
    def setup_class(cls):
        cls.data_0 = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[5];
        creg q[5];
        h q[0];
        x q[0];
        """

        cls.data_1 = """
        OPENQASM 2.0;
        include "qelib1.inc";
        creg q[5];
        creg c[5];
        h q[0];
        x q[0];
        """

        cls.data_2 = """
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

    def test_add_reg(self):
        vist = Visitor()
        vist.q_var = {"q"}
        with pytest.raises(SyntaxError) as context:
            vist.add_reg("q", 2, "qreg", 5)
        assert f"in line {5}, {'qreg'} redefined" in str(context.value)
        vist.q_var = {}

    def test_check_reg(self):
        vist = Visitor()
        with pytest.raises(NameError) as context:
            vist.check_reg(["q", 0], RegType.QREG, 5)
        assert f"in line {5}, qreg {'q'} is not defined" in str(context.value)

        vist.q_var = {"q": 0}
        with pytest.raises(IndexError) as context:
            vist.check_reg(["q", 0], RegType.QREG, 5)
        assert f"in line {5}, creg {'q'} out of bound" in str(context.value)
        vist.q_var = {}

    def test_check_in_gate_qubit(self):
        vist = Visitor()
        with pytest.raises(NameError) as context:
            vist.check_in_gate_qubit(["a", "b"], 8)
        assert f"in line {8}, qubit is not defined" in str(context.value)

        vist.defined_gate = {"current_gate": {"gate_q": ["q0", "q1", "q2"]}}
        vist.now_gate = "current_gate"
        with pytest.raises(NameError) as context:
            vist.check_in_gate_qubit(["a"], 8)
        assert f"in line {8}, qubit {'a'} is not defined" in str(context.value)

    def test_check_qlist(self):
        vist = Visitor()
        with pytest.raises(RuntimeError) as context:
            vist.check_qlist(["a", "b", "a"], 8)
        assert f"in line {8}, qubit reused" in str(context.value)

    def test_visit_program(self):
        vist = Visitor()
        tree = Node("empty", None, None, 1)
        with pytest.raises(RuntimeError) as context:
            vist.visit_program(tree)
        assert "OpenQASM version not specified" in str(context.value)

    def test_duplicate_qubit_name(self):
        vist = Visitor()
        tree = get_abs_tree(self.data_0)
        with pytest.raises(NameError) as context:
            vist.visit_program(tree)
        assert f"in line {5}, var {'q'} is existed" in str(context.value)

    def test_duplicate_bit_declare(self):
        vist = Visitor()
        tree = get_abs_tree(self.data_1)
        with pytest.raises(NameError) as context:
            vist.visit_program(tree)
        assert f"in line {6}, qreg {'q'} is not defined" in str(context.value)

    def test_function(self):
        vist = Visitor()
        tree = get_abs_tree(self.data_2)
        vist.visit_program(tree)

    def test_def_var3(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[3] q;

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 0
        assert q_num == 3

        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 0
        assert q_num == 1

    def test_def_gate(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[3] q;
        bit[3] c;

        gate my_gate q1, q2 {
            cx q1, q2;
            h q1;
        }

        gate my_gate q1 {
            x q1;
        }

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(SyntaxError) as context:
            vist.visit_program(tree)
        assert f"in line {12}, {'my_gate'} redefined" in str(context.value)

    def test_reset(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[3] q;
        bit[3] c;

        measure q[0] -> c[0];
        measure q[1] -> c[1];
        reset q[0];
        reset q[1];
        barrier q[0], q[1], q[2];

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 5
        assert q_num == 3

    def test_for(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[3] q;
        bit[3] c;
        int i;
        int j = 2;

        for int i in [0:1] {
            h q[i];
        }

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 1
        assert q_num == 3

    def test_assign_statement(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        bit[2] c;
        int x = 5;
        float y = 3.14;
        bool z = true;

        x = 10;
        y = 2.71;
        z = false;
        array[int[32], 2] arr = {1, 3};
        arr[0] = 2;
        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 0
        assert q_num == 2

    def test_qop(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[2];
        creg c[1];
        measure q -> c;

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(RuntimeError) as context:
            vist.visit_program(tree)
        assert f"in line {7},the len of qregs and cregs is different" in str(
            context.value
        )

        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[2];
        creg c[2];
        measure q[0] -> c[0];
        measure q[0] -> c[1];

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(RuntimeError) as context:
            vist.visit_program(tree)
        assert f"in line {8},multiple measurements" in str(context.value)

        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[2];
        creg c[2];
        if (undef == 1) x q[0];

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(NameError) as context:
            vist.visit_program(tree)
        assert f"in line {7}, creg {'undef'} is not defined" in str(
            context.value
        )

        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[2];
        creg c[2];
        if (c == 4) x q[0];

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(RuntimeError) as context:
            vist.visit_program(tree)
        assert (
            f"in line {7}, value {4} if always larger than creg {'c'}"
            in str(context.value)
        )

    def test_for_statement(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qreg q[3];
        for int i in 3 {
            x q[i];
        }

        int j=2;
        for int i in j {
            x q[i];
        }

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 5
        assert q_num == 3

        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qreg q[3];
        float j = 3.0;
        for int i in j {
            x q[i];
        }

        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(TypeError) as context:
            vist.visit_program(tree)
        assert (
            f"in line {6}, var {'i'} and var {'j'} should both be int type"
            in str(context.value)
        )

    def test_range_expression(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[5];
        for int i in [0:2:5] {
            x q[i];
        }
        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 3
        assert q_num == 5

    def test_uop_v3(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[1];
        foo q[0];
        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(NameError) as context:
            vist.visit_program(tree)
        assert f"in line {6}, gate {'foo'} is not defined" in str(
            context.value
        )
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[1];
        rx(1,2,3,4) q[0];
        """

        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(RuntimeError) as context:
            vist.visit_program(tree)
        assert "parameter error" in str(context.value)

        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        qreg q[2];
        cx q[0];
        """

        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(RuntimeError) as context:
            vist.visit_program(tree)
        assert "qubit error" in str(context.value)

    def test_exp(self):
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        int x = 1 + 1 * 3- 8 / 2;
        int y= -1;
        int z= 1 / 0;
        """
        vist = Visitor()
        tree = get_abs_tree(data)
        with pytest.raises(ZeroDivisionError) as context:
            vist.visit_program(tree)
        assert "divide by zero error" in str(context.value)

    def test_get_call_param_value(self):
        data = """
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
        test_single(1, 1.14+3*0.5-1.0/2) q[2];
        test_single(cos(0)+tan(1)+exp(1)+ln(3)+sqrt(4), 1.14+3*0.5-1.0/2) q[2];
        measure q[1] -> c[1];
        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 23
        assert q_num == 6

    def test_pi(self):
        data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[2];
        creg c[2];
        rx(pi) q[0];
        """
        vist = Visitor()
        tree = get_abs_tree(data)
        cir = vist.visit_program(tree)
        gates_list = cir.get_operations()
        q_num = cir.num_qubits
        assert len(gates_list) == 1
        assert q_num == 2
