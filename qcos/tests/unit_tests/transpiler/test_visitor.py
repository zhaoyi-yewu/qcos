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

import os
import pytest

from qcos.transpiler.cmss.compiler.parser import get_abs_tree
from qcos.transpiler.cmss.compiler.qtypes import RegType
from qcos.transpiler.cmss.compiler.visitor import Visitor


vist = Visitor()


class TestVisitor:
    @classmethod
    def setup_class(cls):
        cls.data = """
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
        vist.q_var = {"q"}
        with pytest.raises(SyntaxError) as context:
            vist.add_reg("q", 2, "qreg", 5)
        assert f"in line {5}, {'qreg'} redefined" in str(context.value)
        vist.q_var = {}

    def test_check_reg(self):
        with pytest.raises(NameError) as context:
            vist.check_reg(["q", 0], RegType.QREG, 5)
        assert f"in line {5}, qreg {'q'} is not defined" in str(context.value)

        vist.q_var = {"q": 0}
        with pytest.raises(IndexError) as context:
            vist.check_reg(["q", 0], RegType.QREG, 5)
        assert f"in line {5}, creg {'q'} out of bound" in str(context.value)
        vist.q_var = {}

    def test_visit_program(self):
        tree = get_abs_tree(self.data_2)
        vist.visit_program(tree)
        os.remove("log_file")
