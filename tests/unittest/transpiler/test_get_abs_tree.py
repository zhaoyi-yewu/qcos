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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from qcos.transpiler.cmss.compiler.parser import get_abs_tree
from qcos.transpiler.cmss.compiler.qtypes import Node


class TestGetAbsTree:
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

    def test_get_abs_tree(self):
        tree = get_abs_tree(self.data)
        assert tree is not None
        assert isinstance(tree, Node)
        assert tree.type == "top"
        assert len(tree.children) == 8

    def test_qreg_declaration(self):
        tree = get_abs_tree(self.data)
        qreg_found = False
        for child in tree.children:
            if child.type == "defvar" and child.leaf == "qreg":
                qreg_found = True
                assert child.pos == 4
                assert child.children == ["q", 6]
                assert len(child.children) == 2
                break
        assert qreg_found is True

    def test_creg_declaration(self):
        tree = get_abs_tree(self.data)
        creg_found = False
        for child in tree.children:
            if child.type == "defvar" and child.leaf == "creg":
                creg_found = True
                assert child.pos == 5
                assert child.children == ["c", 6]
                assert len(child.children) == 2
                break
        assert creg_found is True

    def test_custom_single_gate(self):
        tree = get_abs_tree(self.data)
        custom_gate_found = False
        for child in tree.children:
            if child.type == "defgate" and child.leaf[0] == "test_single":
                custom_gate_found = True
                assert child.pos == 6
                assert child.leaf == ["test_single", ["a"], ["theta", "phi"]]
                assert len(child.children) == 11
                break
        assert custom_gate_found is True

    def test_custom_multi_gate(self):
        tree = get_abs_tree(self.data)
        custom_gate_found = False
        for child in tree.children:
            if child.type == "defgate" and child.leaf[0] == "test_two":
                custom_gate_found = True
                assert child.pos == 20
                assert child.leaf == ["test_two", ["a", "b"], ["x", "y"]]
                assert len(child.children) == 8
                break
        assert custom_gate_found is True

    def test_register_usage(self):
        tree = get_abs_tree(self.data)
        register_usage_found = False
        for child in tree.children:
            if child.type == "uop" and child.leaf == [['q', 2], ['q', 3]]:
                register_usage_found = True
                assert child.pos == 31
                assert len(child.children) == 2
                break
        assert register_usage_found is True

    def test_barrier_statement(self):
        tree = get_abs_tree(self.data)
        barrier_found = False
        for child in tree.children:
            if child.type == "barrier":
                barrier_found = True
                assert child.pos == 33
                assert len(child.children) == 1
                break
        assert barrier_found is True

    def test_measure_statement(self):
        tree = get_abs_tree(self.data)
        measure_found = False
        for child in tree.children:
            if child.type == "measure":
                measure_found = True
                assert child.pos == 34
                assert child.leaf == ["c", 1]
                assert len(child.children) == 2
                break
        assert measure_found is True
