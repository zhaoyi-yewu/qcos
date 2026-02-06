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

import math
import pytest

from wy_qcos.transpiler.cmss.decomposer.rule_applier import RuleApplier
from wy_qcos.transpiler.cmss.decomposer.equivalence_graph import (
    EquivalenceRule,
    EquivalenceGraph,
)
from wy_qcos.transpiler.cmss.common.gate_operation import create_gate
from wy_qcos.tests.unit_tests.transpiler.comm import (
    validate_gate_ir,
)


class TestRuleApplier:
    @classmethod
    def setup_class(cls):
        """Initialize shared test resources."""
        cls.graph = EquivalenceGraph()
        cls.applier = RuleApplier()

    @pytest.mark.smoke
    def test_apply_one_rule(self):
        # test rx equivalence rule
        rx_rule = EquivalenceRule(
            "rx(beta) q0 -> rx(pi) q0 | ry(beta) q0 | rx(3*pi/2) q0"
        )

        input_op = create_gate("rx", [5], [math.pi / 3])

        rule_applier = RuleApplier()
        result = rule_applier.apply_one_rule(input_op, rx_rule)

        validate_gate_ir(result[0], "rx", [5], 1, False)
        validate_gate_ir(result[1], "ry", [5], 1, False)
        validate_gate_ir(result[2], "rx", [5], 1, False)

        # test cx equivalence rule
        cnot_rule = EquivalenceRule(
            "cx() q0,q1 -> h() q1 | cz() q0,q1 | h() q1"
        )

        input_op = create_gate("cx", [3, 1], [])
        rule_applier = RuleApplier()
        result = rule_applier.apply_one_rule(input_op, cnot_rule)

        validate_gate_ir(result[0], "h", [1], 1, True)
        validate_gate_ir(result[1], "cz", [3, 1], 2, True)
        validate_gate_ir(result[2], "h", [1], 1, True)

        # test CRX equivalence rule
        crx_rule = EquivalenceRule(
            "crx(theta) q0,q1 -> "
            "u1(pi/2) q1 | "
            "cx() q0,q1 | "
            "u3(-theta/2,0,0) q1 | "
            "cx() q0,q1 | "
            "u3(theta/2,-pi/2,0) q1"
        )

        input_op = create_gate("crx", [0, 1], [math.pi / 3])

        rule_applier = RuleApplier()
        result = rule_applier.apply_one_rule(input_op, crx_rule)

        validate_gate_ir(result[0], "u1", [1], 1, False)
        validate_gate_ir(result[1], "cx", [0, 1], 2, True)
        validate_gate_ir(result[2], "u3", [1], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)
        validate_gate_ir(result[4], "u3", [1], 1, False)

        # test CU3 equivalence rule
        cu3_rule = EquivalenceRule(
            "cu3(theta,phi,lam) q0,q1 -> "
            "u1((lam+phi)/2) q0 | "
            "u1((lam-phi)/2) q1 | "
            "cx() q0,q1 | "
            "u3(-theta/2,0,-(phi+lam)/2) q1 | "
            "cx() q0,q1 | "
            "u3(theta/2,phi,0) q1"
        )

        input_op = create_gate("cu3", [0, 1], [0.1, 0.2, 0.3])

        rule_applier = RuleApplier()
        result = rule_applier.apply_one_rule(input_op, cu3_rule)

        validate_gate_ir(result[0], "u1", [0], 1, False)
        validate_gate_ir(result[1], "u1", [1], 1, False)
        validate_gate_ir(result[2], "cx", [0, 1], 2, True)
        validate_gate_ir(result[3], "u3", [1], 1, False)
        validate_gate_ir(result[4], "cx", [0, 1], 2, True)
        validate_gate_ir(result[5], "u3", [1], 1, False)

    def test_apply_path_simple_recursive(self):
        # A → B
        rule_A = EquivalenceRule("h() q0 -> x() q0")

        # B → C
        rule_B = EquivalenceRule("x() q0 -> y() q0")

        # C is target gate, so no rule needed
        rule_dict = {
            "h": rule_A,
            "x": rule_B,
        }

        target = ["y"]
        circuit = [create_gate("h", [0], [])]

        applier = RuleApplier()
        result = applier.apply_path(circuit, target, rule_dict)

        # Expect: A → B → C  → only C remains
        assert len(result) == 1
        validate_gate_ir(result[0], "y", [0], 1, True)
