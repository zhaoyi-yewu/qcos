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

from wy_qcos.transpiler.cmss.decomposer.equivalence_graph import (
    EquivalenceRule,
    EquivalenceGraph,
)
from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation


class TestEquivalenceRule:
    @pytest.mark.smoke
    def test_h_equivalence_u2(self):
        dsl = "h() q0 -> u2(0, pi) q0"
        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "h"
        assert target.qubits == ["q0"]
        assert target.params == []

        # check sources
        assert len(rule.sources) == 1
        src = rule.sources[0]

        assert src.name == "u2"
        assert src.qubits == ["q0"]

        # check params：0, pi
        assert src.params == ["0", "pi"]

    def test_ch_equivalence(self):
        dsl = (
            "ch() q0,q1 -> "
            "s() q1 | "
            "h() q1 | "
            "t() q1 | "
            "cx() q0,q1 | "
            "tdg() q1 | "
            "h() q1 | "
            "sdg() q1"
        )
        rule = EquivalenceRule(dsl)

        # target
        target = rule.target
        assert target.name == "ch"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        # sources
        src = rule.sources
        assert len(src) == 7

        expected = [
            ("s", ["q1"], []),
            ("h", ["q1"], []),
            ("t", ["q1"], []),
            ("cx", ["q0", "q1"], []),
            ("tdg", ["q1"], []),
            ("h", ["q1"], []),
            ("sdg", ["q1"], []),
        ]

        for i, (name, qubits, params) in enumerate(expected):
            assert src[i].name == name
            assert src[i].qubits == qubits
            assert src[i].params == params

    def test_p_equivalence(self):
        dsl = "p(theta) q0 -> u1(theta) q0"
        rule = EquivalenceRule(dsl)

        # target
        target = rule.target
        assert target.name == "p"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        # source
        assert len(rule.sources) == 1
        src = rule.sources[0]
        assert src.name == "u1"
        assert src.qubits == ["q0"]
        assert src.params == ["theta"]

        dsl = "p(theta) q0 -> u(0, 0, theta) q0"
        rule = EquivalenceRule(dsl)

        # target
        target = rule.target
        assert target.name == "p"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        # source
        assert len(rule.sources) == 1
        src = rule.sources[0]
        assert src.name == "u"
        assert src.qubits == ["q0"]

        assert src.params[0] == "0"
        assert src.params[1] == "0"
        assert src.params[2] == "theta"

    def test_cphase_equivalence(self):
        # rule 1
        dsl = (
            "cp(theta) q0,q1 -> "
            "p(theta/2) q0 | "
            "cx() q0,q1 | "
            "p(-theta/2) q1 | "
            "cx() q0,q1 | "
            "p(theta/2) q1"
        )

        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cp"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        src = rule.sources
        assert len(src) == 5

        expected = [
            ("p", ["q0"], ["theta/2"]),
            ("cx", ["q0", "q1"], []),
            ("p", ["q1"], ["-theta/2"]),
            ("cx", ["q0", "q1"], []),
            ("p", ["q1"], ["theta/2"]),
        ]

        for i, (name, qubits, params) in enumerate(expected):
            assert src[i].name == name
            assert src[i].qubits == qubits
            assert src[i].params == params

        # rule 2
        dsl = "cp(theta) q0,q1 -> cu1(theta) q0,q1"

        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cp"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        src = rule.sources
        assert len(src) == 1

        assert src[0].name == "cu1"
        assert src[0].qubits == ["q0", "q1"]
        assert src[0].params == ["theta"]

    def test_r_equivalence(self):
        dsl = "r(theta, phi) q0 -> u3(theta, phi - pi/2, -phi + pi/2) q0"

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "r"
        assert target.qubits == ["q0"]
        assert target.params == ["theta", "phi"]

        # check sources
        src = rule.sources
        assert len(src) == 1

        gate = src[0]
        assert gate.name == "u3"
        assert gate.qubits == ["q0"]
        assert gate.params == [
            "theta",
            "phi - pi/2",
            "-phi + pi/2",
        ]

    def test_rccx_equivalence(self):
        dsl = (
            "rccx() q0,q1,q2 -> "
            "h() q2 | "
            "t() q2 | "
            "cx() q1,q2 | "
            "tdg() q2 | "
            "cx() q0,q2 | "
            "t() q2 | "
            "cx() q1,q2 | "
            "tdg() q2 | "
            "h() q2"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rccx"
        assert target.qubits == ["q0", "q1", "q2"]
        assert target.params == []

        # check sources
        src = rule.sources
        assert len(src) == 9

        # h q2
        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q2"]
        assert g0.params == []

        # t q2
        g1 = src[1]
        assert g1.name == "t"
        assert g1.qubits == ["q2"]
        assert g1.params == []

        # cx q1,q2
        g2 = src[2]
        assert g2.name == "cx"
        assert g2.qubits == ["q1", "q2"]
        assert g2.params == []

        # tdg q2
        g3 = src[3]
        assert g3.name == "tdg"
        assert g3.qubits == ["q2"]
        assert g3.params == []

        # cx q0,q2
        g4 = src[4]
        assert g4.name == "cx"
        assert g4.qubits == ["q0", "q2"]
        assert g4.params == []

        # t q2
        g5 = src[5]
        assert g5.name == "t"
        assert g5.qubits == ["q2"]
        assert g5.params == []

        # cx q1,q2
        g6 = src[6]
        assert g6.name == "cx"
        assert g6.qubits == ["q1", "q2"]
        assert g6.params == []

        # tdg q2
        g7 = src[7]
        assert g7.name == "tdg"
        assert g7.qubits == ["q2"]
        assert g7.params == []

        # h q2
        g8 = src[8]
        assert g8.name == "h"
        assert g8.qubits == ["q2"]
        assert g8.params == []

    def test_rx_equivalence(self):
        dsl = "rx(theta) q0 -> r(theta, 0) q0"

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rx"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 1

        gate = src[0]
        assert gate.name == "r"
        assert gate.qubits == ["q0"]
        assert gate.params == ["theta", "0"]

    def test_crx_equivalence(self):
        dsl = (
            "crx(theta) q0,q1 -> "
            "u1(pi/2) q1 | "
            "cx() q0,q1 | "
            "u3(-theta/2, 0, 0) q1 | "
            "cx() q0,q1 | "
            "u3(theta/2, -pi/2, 0) q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "crx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q1"]
        assert g0.params == ["pi/2"]

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "u3"
        assert g2.qubits == ["q1"]
        assert g2.params == ["-theta/2", "0", "0"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "u3"
        assert g4.qubits == ["q1"]
        assert g4.params == ["theta/2", "-pi/2", "0"]

        dsl = (
            "crx(theta) q0,q1 -> "
            "s() q1 | "
            "cx() q0,q1 | "
            "ry(-theta/2) q1 | "
            "cx() q0,q1 | "
            "ry(theta/2) q1 | "
            "sdg() q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "crx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 6

        g0 = src[0]
        assert g0.name == "s"
        assert g0.qubits == ["q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "ry"
        assert g2.qubits == ["q1"]
        assert g2.params == ["-theta/2"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "ry"
        assert g4.qubits == ["q1"]
        assert g4.params == ["theta/2"]

        g5 = src[5]
        assert g5.name == "sdg"
        assert g5.qubits == ["q1"]
        assert g5.params == []

    def test_rxx_equivalence(self):
        dsl = (
            "rxx(theta) q0,q1 -> "
            "h() q0 | "
            "h() q1 | "
            "rzz(theta) q0,q1 | "
            "h() q0 | "
            "h() q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rxx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "h"
        assert g1.qubits == ["q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "rzz"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == ["theta"]

        g3 = src[3]
        assert g3.name == "h"
        assert g3.qubits == ["q0"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "h"
        assert g4.qubits == ["q1"]
        assert g4.params == []

    def test_rzx_equivalence(self):
        dsl = (
            "rzx(theta) q0,q1 -> "
            "h() q1 | "
            "cx() q0,q1 | "
            "rz(theta) q1 | "
            "cx() q0,q1 | "
            "h() q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rzx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "rz"
        assert g2.qubits == ["q1"]
        assert g2.params == ["theta"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "h"
        assert g4.qubits == ["q1"]
        assert g4.params == []

        dsl = (
            "rzx(theta) q0,q1 -> "
            "h() q1 | "
            "cx() q0,q1 | "
            "rz(theta) q1 | "
            "cx() q0,q1 | "
            "h() q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rzx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "rz"
        assert g2.qubits == ["q1"]
        assert g2.params == ["theta"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "h"

    def test_ry_equivalence(self):
        dsl = "ry(theta) q0 -> r(theta, pi/2) q0"

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "ry"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "r"
        assert g0.qubits == ["q0"]
        assert g0.params == ["theta", "pi/2"]

    def test_cry_equivalence(self):
        dsl = (
            "cry(theta) q0,q1 -> "
            "ry(theta/2) q1 | "
            "cx() q0,q1 | "
            "ry(-theta/2) q1 | "
            "cx() q0,q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "cry"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 4

        g0 = src[0]
        assert g0.name == "ry"
        assert g0.qubits == ["q1"]
        assert g0.params == ["theta/2"]

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "ry"
        assert g2.qubits == ["q1"]
        assert g2.params == ["-theta/2"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

    def test_ryy_equivalence(self):
        dsl = (
            "ryy(theta) q0,q1 -> "
            "rx(pi/2) q0 | "
            "rx(pi/2) q1 | "
            "cx() q0,q1 | "
            "rz(theta) q1 | "
            "cx() q0,q1 | "
            "rx(-pi/2) q0 | "
            "rx(-pi/2) q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "ryy"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 7

        g0 = src[0]
        assert g0.name == "rx"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi/2"]

        g1 = src[1]
        assert g1.name == "rx"
        assert g1.qubits == ["q1"]
        assert g1.params == ["pi/2"]

        g2 = src[2]
        assert g2.name == "cx"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == []

        g3 = src[3]
        assert g3.name == "rz"
        assert g3.qubits == ["q1"]
        assert g3.params == ["theta"]

        g4 = src[4]
        assert g4.name == "cx"
        assert g4.qubits == ["q0", "q1"]
        assert g4.params == []

        g5 = src[5]
        assert g5.name == "rx"
        assert g5.qubits == ["q0"]
        assert g5.params == ["-pi/2"]

        g6 = src[6]
        assert g6.name == "rx"
        assert g6.qubits == ["q1"]
        assert g6.params == ["-pi/2"]

        dsl = (
            "ryy(theta) q0,q1 -> "
            "rx(pi/2) q0 | "
            "rx(pi/2) q1 | "
            "rzz(theta) q0,q1 | "
            "rx(-pi/2) q0 | "
            "rx(-pi/2) q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "ryy"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "rx"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi/2"]

        g1 = src[1]
        assert g1.name == "rx"
        assert g1.qubits == ["q1"]
        assert g1.params == ["pi/2"]

        g2 = src[2]
        assert g2.name == "rzz"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == ["theta"]

        g3 = src[3]
        assert g3.name == "rx"
        assert g3.qubits == ["q0"]
        assert g3.params == ["-pi/2"]

        g4 = src[4]
        assert g4.name == "rx"
        assert g4.qubits == ["q1"]
        assert g4.params == ["-pi/2"]

    def test_rz_equivalence(self):
        dsl = "rz(theta) q0 -> u1(theta) q0"

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rz"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q0"]
        assert g0.params == ["theta"]

        dsl = "rz(theta) q0 -> sx() q0 | ry(-theta) q0 | sxdg() q0"

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rz"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "sx"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "ry"
        assert g1.qubits == ["q0"]
        assert g1.params == ["-theta"]

        g2 = src[2]
        assert g2.name == "sxdg"
        assert g2.qubits == ["q0"]
        assert g2.params == []

    def test_crz_equivalence(self):
        dsl = (
            "crz(theta) q0,q1 -> "
            "rz(theta/2) q1 | "
            "cx() q0,q1 | "
            "rz(-theta/2) q1 | "
            "cx() q0,q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "crz"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 4

        g0 = src[0]
        assert g0.name == "rz"
        assert g0.qubits == ["q1"]
        assert g0.params == ["theta/2"]

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "rz"
        assert g2.qubits == ["q1"]
        assert g2.params == ["-theta/2"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

    def test_rzz_equivalence(self):
        dsl = "rzz(theta) q0,q1 -> cx() q0,q1 | rz(theta) q1 | cx() q0,q1"

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rzz"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "cx"
        assert g0.qubits == ["q0", "q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "rz"
        assert g1.qubits == ["q1"]
        assert g1.params == ["theta"]

        g2 = src[2]
        assert g2.name == "cx"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == []

        dsl = (
            "rzz(theta) q0,q1 -> "
            "h() q0 | "
            "h() q1 | "
            "rxx(theta) q0,q1 | "
            "h() q0 | "
            "h() q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rzz"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "h"
        assert g1.qubits == ["q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "rxx"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == ["theta"]

        g3 = src[3]
        assert g3.name == "h"
        assert g3.qubits == ["q0"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "h"
        assert g4.qubits == ["q1"]
        assert g4.params == []

        dsl = (
            "rzz(theta) q0,q1 -> "
            "rx(-pi/2) q0 | "
            "rx(-pi/2) q1 | "
            "ryy(theta) q0,q1 | "
            "rx(pi/2) q0 | "
            "rx(pi/2) q1"
        )

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "rzz"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        # check sources
        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "rx"
        assert g0.qubits == ["q0"]
        assert g0.params == ["-pi/2"]

        g1 = src[1]
        assert g1.name == "rx"
        assert g1.qubits == ["q1"]
        assert g1.params == ["-pi/2"]

        g2 = src[2]
        assert g2.name == "ryy"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == ["theta"]

        g3 = src[3]
        assert g3.name == "rx"
        assert g3.qubits == ["q0"]
        assert g3.params == ["pi/2"]

        g4 = src[4]
        assert g4.name == "rx"
        assert g4.qubits == ["q1"]
        assert g4.params == ["pi/2"]

    def test_ecr_equivalence(self):
        dsl = "ecr() q0,q1 -> rzx(pi/4) q0,q1 | x() q0 | rzx(-pi/4) q0,q1"

        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "ecr"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        # check sources
        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "rzx"
        assert g0.qubits == ["q0", "q1"]
        assert g0.params == ["pi/4"]

        g1 = src[1]
        assert g1.name == "x"
        assert g1.qubits == ["q0"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "rzx"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == ["-pi/4"]

    def test_s_equivalence(self):
        dsl = "s() q0 -> u1(pi/2) q0"
        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "s"
        assert target.qubits == ["q0"]
        assert target.params == []

        # check sources
        src = rule.sources
        assert len(src) == 1
        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi/2"]

    def test_sdg_equivalence(self):
        dsl = "sdg() q0 -> u1(-pi/2) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sdg"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 1
        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q0"]
        assert g0.params == ["-pi/2"]

        dsl = "sdg() q0 -> s() q0 | z() q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sdg"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 2

        g0 = src[0]
        assert g0.name == "s"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "z"
        assert g1.qubits == ["q0"]
        assert g1.params == []

        dsl = "sdg() q0 -> z() q0 | s() q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sdg"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 2

        g0 = src[0]
        assert g0.name == "z"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "s"
        assert g1.qubits == ["q0"]
        assert g1.params == []

        dsl = "sdg() q0 -> s() q0 | s() q0 | s() q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sdg"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "s"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "s"
        assert g1.qubits == ["q0"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "s"
        assert g2.qubits == ["q0"]
        assert g2.params == []

    def test_cs_equivalence(self):
        dsl = "cs() q0,q1 -> h() q1 | csx() q0,q1 | h() q1"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cs"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "csx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "h"
        assert g2.qubits == ["q1"]
        assert g2.params == []

    def test_csdg_equivalence(self):
        dsl = "csdg() q0,q1 -> h() q1 | cx() q0,q1 | csx() q0,q1 | h() q1"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "csdg"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 4

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "csx"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == []

        g3 = src[3]
        assert g3.name == "h"
        assert g3.qubits == ["q1"]
        assert g3.params == []

    def test_swap_equivalence(self):
        dsl = "swap() q0,q1 -> cx() q0,q1 | cx() q1,q0 | cx() q0,q1"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "swap"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "cx"
        assert g0.qubits == ["q0", "q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q1", "q0"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "cx"
        assert g2.qubits == ["q0", "q1"]
        assert g2.params == []

    def test_iswap_equivalence(self):
        dsl = (
            "iswap() q0,q1 -> "
            "s() q0 | "
            "s() q1 | "
            "h() q0 | "
            "cx() q0,q1 | "
            "cx() q1,q0 | "
            "h() q1"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "iswap"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 6

        g0 = src[0]
        assert g0.name == "s"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "s"
        assert g1.qubits == ["q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "h"
        assert g2.qubits == ["q0"]
        assert g2.params == []

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "cx"
        assert g4.qubits == ["q1", "q0"]
        assert g4.params == []

        g5 = src[5]
        assert g5.name == "h"
        assert g5.qubits == ["q1"]
        assert g5.params == []

    def test_sx_equivalence(self):
        dsl = "sx() q0 -> sdg() q0 | h() q0 | sdg() q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sx"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "sdg"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "h"
        assert g1.qubits == ["q0"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "sdg"
        assert g2.qubits == ["q0"]
        assert g2.params == []

        dsl = "sx() q0 -> rx(pi/2) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sx"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "rx"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi/2"]

    def test_sxdg_equivalence(self):
        dsl = "sxdg() q0 -> s() q0 | h() q0 | s() q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sxdg"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "s"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "h"
        assert g1.qubits == ["q0"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "s"
        assert g2.qubits == ["q0"]
        assert g2.params == []

        dsl = "sxdg() q0 -> rx(-pi/2) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "sxdg"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "rx"
        assert g0.qubits == ["q0"]
        assert g0.params == ["-pi/2"]

    def test_csx_equivalence(self):
        dsl = "csx() q0,q1 -> h() q1 | cu1(pi/2) q0,q1 | h() q1"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "csx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "cu1"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == ["pi/2"]

        g2 = src[2]
        assert g2.name == "h"
        assert g2.qubits == ["q1"]
        assert g2.params == []

        dsl = (
            "csx() q0,q1 -> "
            "x() q0 | "
            "rzx(pi/4) q0,q1 | "
            "tdg() q0 | "
            "x() q0 | "
            "rx(pi/4) q1"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "csx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "x"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "rzx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == ["pi/4"]

        g2 = src[2]
        assert g2.name == "tdg"
        assert g2.qubits == ["q0"]
        assert g2.params == []

        g3 = src[3]
        assert g3.name == "x"
        assert g3.qubits == ["q0"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "rx"
        assert g4.qubits == ["q1"]
        assert g4.params == ["pi/4"]

    def test_dcx_equivalence(self):
        dsl = "dcx() q0,q1 -> cx() q0,q1 | cx() q1,q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "dcx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 2

        g0 = src[0]
        assert g0.name == "cx"
        assert g0.qubits == ["q0", "q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q1", "q0"]
        assert g1.params == []

        dsl = (
            "dcx() q0,q1 -> "
            "h() q0 | "
            "sdg() q0 | "
            "sdg() q1 | "
            "iswap() q0,q1 | "
            "h() q1"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "dcx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "h"
        assert g0.qubits == ["q0"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "sdg"
        assert g1.qubits == ["q0"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "sdg"
        assert g2.qubits == ["q1"]
        assert g2.params == []

        g3 = src[3]
        assert g3.name == "iswap"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "h"
        assert g4.qubits == ["q1"]
        assert g4.params == []

    def test_cswap_equivalence(self):
        dsl = "cswap() q0,q1,q2 -> cx() q2,q1 | ccx() q0,q1,q2 | cx() q2,q1"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cswap"
        assert target.qubits == ["q0", "q1", "q2"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3

        g0 = src[0]
        assert g0.name == "cx"
        assert g0.qubits == ["q2", "q1"]
        assert g0.params == []

        g1 = src[1]
        assert g1.name == "ccx"
        assert g1.qubits == ["q0", "q1", "q2"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "cx"
        assert g2.qubits == ["q2", "q1"]
        assert g2.params == []

    def test_t_equivalence(self):
        dsl = "t() q0 -> u1(pi/4) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "t"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi/4"]

    def test_tdg_equivalence(self):
        dsl = "tdg() q0 -> u1(-pi/4) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "tdg"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q0"]
        assert g0.params == ["-pi/4"]

    def test_u_equivalence(self):
        dsl = "u(theta,phi,lam) q0 -> u3(theta,phi,lam) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "u"
        assert target.qubits == ["q0"]
        assert target.params == ["theta", "phi", "lam"]

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "u3"
        assert g0.qubits == ["q0"]
        assert g0.params == ["theta", "phi", "lam"]

    def test_cu_equivalence(self):
        dsl = (
            "cu(theta,phi,lam,gamma) q0,q1 -> "
            "p(gamma) q0 | "
            "p((lam + phi)/2) q0 | "
            "p((lam - phi)/2) q1 | "
            "cx() q0,q1 | "
            "u(-theta/2,0,-(phi + lam)/2) q1 | "
            "cx() q0,q1 | "
            "u(theta/2,phi,0) q1"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cu"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta", "phi", "lam", "gamma"]

        src = rule.sources
        assert len(src) == 7

        g0 = src[0]
        assert g0.name == "p"
        assert g0.qubits == ["q0"]
        assert g0.params == ["gamma"]

        g1 = src[1]
        assert g1.name == "p"
        assert g1.qubits == ["q0"]
        assert g1.params == ["(lam + phi)/2"]

        g2 = src[2]
        assert g2.name == "p"
        assert g2.qubits == ["q1"]
        assert g2.params == ["(lam - phi)/2"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "u"
        assert g4.qubits == ["q1"]
        assert g4.params == ["-theta/2", "0", "-(phi + lam)/2"]

        g5 = src[5]
        assert g5.name == "cx"
        assert g5.qubits == ["q0", "q1"]
        assert g5.params == []

        g6 = src[6]
        assert g6.name == "u"
        assert g6.qubits == ["q1"]
        assert g6.params == ["theta/2", "phi", "0"]

        dsl = (
            "cu(theta,phi,lam,gamma) q0,q1 -> "
            "p(gamma) q0 | "
            "cu3(theta,phi,lam) q0,q1"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cu"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta", "phi", "lam", "gamma"]

        src = rule.sources
        assert len(src) == 2

        g0 = src[0]
        assert g0.name == "p"
        assert g0.qubits == ["q0"]
        assert g0.params == ["gamma"]

        g1 = src[1]
        assert g1.name == "cu3"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == ["theta", "phi", "lam"]

    def test_u1_equivalence(self):
        dsl = "u1(theta) q0 -> u3(0,0,theta) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "u1"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "u3"
        assert g0.qubits == ["q0"]
        assert g0.params == ["0", "0", "theta"]

        dsl = "u1(theta) q0 -> p(theta) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "u1"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "p"
        assert g0.qubits == ["q0"]
        assert g0.params == ["theta"]

        dsl = "u1(theta) q0 -> rz(theta) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "u1"
        assert target.qubits == ["q0"]
        assert target.params == ["theta"]

        src = rule.sources
        assert len(src) == 1

        g0 = src[0]
        assert g0.name == "rz"
        assert g0.qubits == ["q0"]
        assert g0.params == ["theta"]

    def test_cu1_equivalence(self):
        dsl = (
            "cu1(theta) q0,q1 -> "
            "u1(theta/2) q0 | "
            "cx() q0,q1 | "
            "u1(-theta/2) q1 | "
            "cx() q0,q1 | "
            "u1(theta/2) q1"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cu1"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta"]

        src = rule.sources
        assert len(src) == 5

        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q0"]
        assert g0.params == ["theta/2"]

        g1 = src[1]
        assert g1.name == "cx"
        assert g1.qubits == ["q0", "q1"]
        assert g1.params == []

        g2 = src[2]
        assert g2.name == "u1"
        assert g2.qubits == ["q1"]
        assert g2.params == ["-theta/2"]

        g3 = src[3]
        assert g3.name == "cx"
        assert g3.qubits == ["q0", "q1"]
        assert g3.params == []

        g4 = src[4]
        assert g4.name == "u1"
        assert g4.qubits == ["q1"]
        assert g4.params == ["theta/2"]

    def test_u2_equivalence(self):
        dsl = "u2(phi,lam) q0 -> u3(pi/2,phi,lam) q0"
        rule = EquivalenceRule(dsl)

        # check target
        target = rule.target
        assert target.name == "u2"
        assert target.qubits == ["q0"]
        assert target.params == ["phi", "lam"]

        # check sources
        src = rule.sources
        assert len(src) == 1
        g0 = src[0]
        assert g0.name == "u3"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi/2", "phi", "lam"]

    def test_u3_equivalence(self):
        dsl = (
            "u3(theta,phi,lam) q0 -> "
            "rz(lam) q0 | "
            "sx() q0 | "
            "rz(theta+pi) q0 | "
            "sx() q0 | "
            "rz(phi+3*pi) q0"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "u3"
        assert target.qubits == ["q0"]
        assert target.params == ["theta", "phi", "lam"]

        src = rule.sources
        assert len(src) == 5
        g0, g1, g2, g3, g4 = src
        assert g0.name == "rz" and g0.qubits == ["q0"] and g0.params == ["lam"]
        assert g1.name == "sx" and g1.qubits == ["q0"] and g1.params == []
        assert (
            g2.name == "rz"
            and g2.qubits == ["q0"]
            and g2.params == ["theta+pi"]
        )
        assert g3.name == "sx" and g3.qubits == ["q0"] and g3.params == []
        assert (
            g4.name == "rz"
            and g4.qubits == ["q0"]
            and g4.params == ["phi+3*pi"]
        )

        dsl = "u3(theta,phi,lam) q0 -> u(theta,phi,lam) q0"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "u3"
        assert target.qubits == ["q0"]
        assert target.params == ["theta", "phi", "lam"]

        src = rule.sources
        assert len(src) == 1
        g0 = src[0]
        assert g0.name == "u"
        assert g0.qubits == ["q0"]
        assert g0.params == ["theta", "phi", "lam"]

    def test_cu3_equivalence(self):
        dsl = (
            "cu3(theta,phi,lam) q0,q1 -> "
            "u1((lam+phi)/2) q0 | "
            "u1((lam-phi)/2) q1 | "
            "cx() q0,q1 | "
            "u3(-theta/2,0,-(phi+lam)/2) q1 | "
            "cx() q0,q1 | "
            "u3(theta/2,phi,0) q1"
        )
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cu3"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta", "phi", "lam"]

        src = rule.sources
        assert len(src) == 6
        g0, g1, g2, g3, g4, g5 = src
        assert (
            g0.name == "u1"
            and g0.qubits == ["q0"]
            and g0.params == ["(lam+phi)/2"]
        )
        assert (
            g1.name == "u1"
            and g1.qubits == ["q1"]
            and g1.params == ["(lam-phi)/2"]
        )
        assert (
            g2.name == "cx" and g2.qubits == ["q0", "q1"] and g2.params == []
        )
        assert (
            g3.name == "u3"
            and g3.qubits == ["q1"]
            and g3.params == ["-theta/2", "0", "-(phi+lam)/2"]
        )
        assert (
            g4.name == "cx" and g4.qubits == ["q0", "q1"] and g4.params == []
        )
        assert (
            g5.name == "u3"
            and g5.qubits == ["q1"]
            and g5.params == ["theta/2", "phi", "0"]
        )
        dsl = "cu3(theta,phi,lam) q0,q1 -> cu(theta,phi,lam) q0,q1"
        rule = EquivalenceRule(dsl)

        target = rule.target
        assert target.name == "cu3"
        assert target.qubits == ["q0", "q1"]
        assert target.params == ["theta", "phi", "lam"]

        src = rule.sources
        assert len(src) == 1
        g0 = src[0]
        assert g0.name == "cu"
        assert g0.qubits == ["q0", "q1"]
        assert g0.params == ["theta", "phi", "lam"]

    def test_x_equivalences(self):
        # x() -> u3(pi,0,pi)
        dsl = "x() q0 -> u3(pi,0,pi) q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "x"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 1
        g0 = src[0]
        assert g0.name == "u3"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi", "0", "pi"]

        # x() -> h() s() s() h()
        dsl = "x() q0 -> h() q0 | s() q0 | s() q0 | h() q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "x"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 4
        g0, g1, g2, g3 = src
        assert g0.name == "h" and g0.qubits == ["q0"] and g0.params == []
        assert g1.name == "s" and g1.qubits == ["q0"] and g1.params == []
        assert g2.name == "s" and g2.qubits == ["q0"] and g2.params == []
        assert g3.name == "h" and g3.qubits == ["q0"] and g3.params == []

        # x() q0 -> rx(pi) q0
        dsl = "x() q0 -> rx(pi) q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "x"
        assert target.qubits == ["q0"]
        assert target.params == []
        src = rule.sources
        g0 = src[0]
        assert g0.name == "rx"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi"]

    def test_cx_equivalences(self):
        dsl = (
            "cx() q0,q1 -> "
            "ry(pi/2) q0 | "
            "rxx(pi/2) q0,q1 | "
            "rx(-pi/2) q0 | "
            "rx(-pi/2) q1 | "
            "ry(-pi/2) q0"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 5
        g0, g1, g2, g3, g4 = src
        assert (
            g0.name == "ry" and g0.qubits == ["q0"] and g0.params == ["pi/2"]
        )
        assert (
            g1.name == "rxx"
            and g1.qubits == ["q0", "q1"]
            and g1.params == ["pi/2"]
        )
        assert (
            g2.name == "rx" and g2.qubits == ["q0"] and g2.params == ["-pi/2"]
        )
        assert (
            g3.name == "rx" and g3.qubits == ["q1"] and g3.params == ["-pi/2"]
        )
        assert (
            g4.name == "ry" and g4.qubits == ["q0"] and g4.params == ["-pi/2"]
        )

        dsl = (
            "cx() q0,q1 -> "
            "ry(pi/2) q0 | "
            "rxx(-pi/2) q0,q1 | "
            "rx(pi/2) q0 | "
            "rx(pi/2) q1 | "
            "ry(-pi/2) q0"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        g0, g1, g2, g3, g4 = src
        assert (
            g0.name == "ry" and g0.qubits == ["q0"] and g0.params == ["pi/2"]
        )
        assert (
            g1.name == "rxx"
            and g1.qubits == ["q0", "q1"]
            and g1.params == ["-pi/2"]
        )
        assert (
            g2.name == "rx" and g2.qubits == ["q0"] and g2.params == ["pi/2"]
        )
        assert (
            g3.name == "rx" and g3.qubits == ["q1"] and g3.params == ["pi/2"]
        )
        assert (
            g4.name == "ry" and g4.qubits == ["q0"] and g4.params == ["-pi/2"]
        )

        dsl = (
            "cx() q0,q1 -> "
            "ry(-pi/2) q0 | "
            "rxx(pi/2) q0,q1 | "
            "rx(-pi/2) q0 | "
            "rx(pi/2) q1 | "
            "ry(pi/2) q0"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        g0, g1, g2, g3, g4 = src
        assert (
            g0.name == "ry" and g0.qubits == ["q0"] and g0.params == ["-pi/2"]
        )
        assert (
            g1.name == "rxx"
            and g1.qubits == ["q0", "q1"]
            and g1.params == ["pi/2"]
        )
        assert (
            g2.name == "rx" and g2.qubits == ["q0"] and g2.params == ["-pi/2"]
        )
        assert (
            g3.name == "rx" and g3.qubits == ["q1"] and g3.params == ["pi/2"]
        )
        assert (
            g4.name == "ry" and g4.qubits == ["q0"] and g4.params == ["pi/2"]
        )

        dsl = (
            "cx() q0,q1 -> "
            "ry(-pi/2) q0 | "
            "rxx(-pi/2) q0,q1 | "
            "rx(pi/2) q0 | "
            "rx(-pi/2) q1 | "
            "ry(pi/2) q0"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        g0, g1, g2, g3, g4 = src
        assert (
            g0.name == "ry" and g0.qubits == ["q0"] and g0.params == ["-pi/2"]
        )
        assert (
            g1.name == "rxx"
            and g1.qubits == ["q0", "q1"]
            and g1.params == ["-pi/2"]
        )
        assert (
            g2.name == "rx" and g2.qubits == ["q0"] and g2.params == ["pi/2"]
        )
        assert (
            g3.name == "rx" and g3.qubits == ["q1"] and g3.params == ["-pi/2"]
        )
        assert (
            g4.name == "ry" and g4.qubits == ["q0"] and g4.params == ["pi/2"]
        )

        # cx() -> h() cz() h()
        dsl = "cx() q0,q1 -> h() q1 | cz() q0,q1 | h() q1"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        assert len(src) == 3
        g0, g1, g2 = src
        assert g0.name == "h" and g0.qubits == ["q1"] and g0.params == []
        assert (
            g1.name == "cz" and g1.qubits == ["q0", "q1"] and g1.params == []
        )
        assert g2.name == "h" and g2.qubits == ["q1"] and g2.params == []

        # cx() -> h() x() h() iswap() ...
        dsl = (
            "cx() q0,q1 -> "
            "h() q0 | "
            "x() q1 | "
            "h() q1 | "
            "iswap() q0,q1 | "
            "x() q0 | "
            "x() q1 | "
            "h() q1 | "
            "iswap() q0,q1 | "
            "h() q0 | "
            "s() q0 | "
            "s() q1 | "
            "x() q1 | "
            "h() q1"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        expected_names = [
            "h",
            "x",
            "h",
            "iswap",
            "x",
            "x",
            "h",
            "iswap",
            "h",
            "s",
            "s",
            "x",
            "h",
        ]
        expected_qubits = [
            ["q0"],
            ["q1"],
            ["q1"],
            ["q0", "q1"],
            ["q0"],
            ["q1"],
            ["q1"],
            ["q0", "q1"],
            ["q0"],
            ["q0"],
            ["q1"],
            ["q1"],
            ["q1"],
        ]
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

        # cx() -> rz(-pi/2) ry(pi) rx(pi/2) ecr()
        dsl = (
            "cx() q0,q1 -> "
            "rz(-pi/2) q0 | "
            "ry(pi) q0 | "
            "rx(pi/2) q1 | "
            "ecr() q0,q1"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        expected_names = ["rz", "ry", "rx", "ecr"]
        expected_qubits = [["q0"], ["q0"], ["q1"], ["q0", "q1"]]
        expected_params = ["-pi/2", "pi", "pi/2", ""]
        for g, name, qubits, params in zip(
            src, expected_names, expected_qubits, expected_params
        ):
            assert g.name == name
            assert g.qubits == qubits
            if params:
                assert g.params == [params]
            else:
                assert g.params == []

        # cx() -> u(pi/2,0,pi) cphase(pi) u(pi/2,0,pi)
        dsl = (
            "cx() q0,q1 -> "
            "u(pi/2,0,pi) q1 | "
            "cphase(pi) q0,q1 | "
            "u(pi/2,0,pi) q1"
        )

        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        expected_names = ["u", "cphase", "u"]
        expected_qubits = [["q1"], ["q0", "q1"], ["q1"]]
        expected_params = [["pi/2", "0", "pi"], ["pi"], ["pi/2", "0", "pi"]]
        for g, name, qubits, params in zip(
            src, expected_names, expected_qubits, expected_params
        ):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == params

        # cx() -> u(pi/2,0,pi) u(0,0,pi/2) crz(pi)
        dsl = (
            "cx() q0,q1 -> "
            "u(pi/2,0,pi) q1 | "
            "u(0,0,pi/2) q0 | "
            "crz(pi) q0,q1 | "
            "u(pi/2,0,pi) q1"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        expected_names = ["u", "u", "crz", "u"]
        expected_qubits = [["q1"], ["q0"], ["q0", "q1"], ["q1"]]
        expected_params = [
            ["pi/2", "0", "pi"],
            ["0", "0", "pi/2"],
            ["pi"],
            ["pi/2", "0", "pi"],
        ]
        for g, name, qubits, params in zip(
            src, expected_names, expected_qubits, expected_params
        ):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == params

        # cx() -> rzx(pi/2) sdg() sxdg()
        dsl = "cx() q0,q1 -> rzx(pi/2) q0,q1 | sdg() q0 | sxdg() q1"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cx"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        expected_names = ["rzx", "sdg", "sxdg"]
        expected_qubits = [["q0", "q1"], ["q0"], ["q1"]]
        expected_params = [["pi/2"], [], []]
        for g, name, qubits, params in zip(
            src, expected_names, expected_qubits, expected_params
        ):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == params

    def test_ccx_equivalences(self):
        # ccx() q0,q1,q2 -> h() q2 | cx() q1,q2 | tdg() q2 | ...
        dsl = (
            "ccx() q0,q1,q2 -> "
            "h() q2 | "
            "cx() q1,q2 | "
            "tdg() q2 | "
            "cx() q0,q2 | "
            "t() q2 | "
            "cx() q1,q2 | "
            "tdg() q2 | "
            "cx() q0,q2 | "
            "t() q1 | "
            "t() q2 | "
            "h() q2 | "
            "cx() q0,q1 | "
            "t() q0 | "
            "tdg() q1 | "
            "cx() q0,q1"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "ccx"
        assert target.qubits == ["q0", "q1", "q2"]
        assert target.params == []

        src = rule.sources
        expected_names = [
            "h",
            "cx",
            "tdg",
            "cx",
            "t",
            "cx",
            "tdg",
            "cx",
            "t",
            "t",
            "h",
            "cx",
            "t",
            "tdg",
            "cx",
        ]
        expected_qubits = [
            ["q2"],
            ["q1", "q2"],
            ["q2"],
            ["q0", "q2"],
            ["q2"],
            ["q1", "q2"],
            ["q2"],
            ["q0", "q2"],
            ["q1"],
            ["q2"],
            ["q2"],
            ["q0", "q1"],
            ["q0"],
            ["q1"],
            ["q0", "q1"],
        ]
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

        # ccx() q0,q1,q2 -> csx() q1,q2 | cx() q0,q1 | z() q2 ...
        dsl = (
            "ccx() q0,q1,q2 -> "
            "csx() q1,q2 | "
            "cx() q0,q1 | "
            "z() q2 | "
            "sdg() q1 | "
            "csx() q1,q2 | "
            "z() q2 | "
            "cx() q0,q1 | "
            "csx() q0,q2"
        )
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "ccx"
        assert target.qubits == ["q0", "q1", "q2"]
        assert target.params == []

        src = rule.sources
        expected_names = ["csx", "cx", "z", "sdg", "csx", "z", "cx", "csx"]
        expected_qubits = [
            ["q1", "q2"],
            ["q0", "q1"],
            ["q2"],
            ["q1"],
            ["q1", "q2"],
            ["q2"],
            ["q0", "q1"],
            ["q0", "q2"],
        ]
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

    def test_y_equivalences(self):
        # y() q0 -> u3(pi,pi/2,pi/2) q0
        dsl = "y() q0 -> u3(pi,pi/2,pi/2) q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "y"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        g0 = src[0]
        assert g0.name == "u3"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi", "pi/2", "pi/2"]

        # y() q0 -> s() q0 | s() q0 | h() q0 | s() q0 | s() q0 | h() q0
        dsl = "y() q0 -> s() q0 | s() q0 | h() q0 | s() q0 | s() q0 | h() q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "y"
        assert target.qubits == ["q0"]
        assert target.params == []

        src = rule.sources
        expected_names = ["s", "s", "h", "s", "s", "h"]
        expected_qubits = [["q0"]] * 6
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

        # y() q0 -> ry(pi) q0
        dsl = "y() q0 -> ry(pi) q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "y"
        assert target.qubits == ["q0"]
        assert target.params == []
        src = rule.sources
        g0 = src[0]
        assert g0.name == "ry"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi"]

    def test_cy_equivalences(self):
        # cy() q0,q1 -> sdg() q1 | cx() q0,q1 | s() q1
        dsl = "cy() q0,q1 -> sdg() q1 | cx() q0,q1 | s() q1"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cy"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []

        src = rule.sources
        expected_names = ["sdg", "cx", "s"]
        expected_qubits = [["q1"], ["q0", "q1"], ["q1"]]
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

    def test_z_equivalences(self):
        # z() q0 -> u1(pi) q0
        dsl = "z() q0 -> u1(pi) q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "z"
        assert target.qubits == ["q0"]
        assert target.params == []
        src = rule.sources
        g0 = src[0]
        assert g0.name == "u1"
        assert g0.qubits == ["q0"]
        assert g0.params == ["pi"]

        # z() q0 -> s() q0 | s() q0
        dsl = "z() q0 -> s() q0 | s() q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "z"
        assert target.qubits == ["q0"]
        assert target.params == []
        src = rule.sources
        expected_names = ["s", "s"]
        expected_qubits = [["q0"], ["q0"]]
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

    def test_cz_equivalences(self):
        # cz() q0,q1 -> h() q1 | cx() q0,q1 | h() q1
        dsl = "cz() q0,q1 -> h() q1 | cx() q0,q1 | h() q1"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "cz"
        assert target.qubits == ["q0", "q1"]
        assert target.params == []
        src = rule.sources
        expected_names = ["h", "cx", "h"]
        expected_qubits = [["q1"], ["q0", "q1"], ["q1"]]
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

    def test_ccz_equivalences(self):
        # ccz() q0,q1,q2 -> h() q2 | ccx() q0,q1,q2 | h() q2
        dsl = "ccz() q0,q1,q2 -> h() q2 | ccx() q0,q1,q2 | h() q2"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "ccz"
        assert target.qubits == ["q0", "q1", "q2"]
        assert target.params == []
        src = rule.sources
        expected_names = ["h", "ccx", "h"]
        expected_qubits = [["q2"], ["q0", "q1", "q2"], ["q2"]]
        for g, name, qubits in zip(src, expected_names, expected_qubits):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == []

    def test_h_equivalences(self):
        # h() q0 -> ry(pi/2) q0 | rx(pi) q0
        dsl = "h() q0 -> ry(pi/2) q0 | rx(pi) q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "h"
        assert target.qubits == ["q0"]
        assert target.params == []
        src = rule.sources
        expected_names = ["ry", "rx"]
        expected_qubits = [["q0"], ["q0"]]
        expected_params = ["pi/2", "pi"]
        for g, name, qubits, param in zip(
            src, expected_names, expected_qubits, expected_params
        ):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == [param]

        # h() q0 -> r(pi/2, pi/2) q0 | r(pi, 0) q0
        dsl = "h() q0 -> r(pi/2, pi/2) q0 | r(pi, 0) q0"
        rule = EquivalenceRule(dsl)
        target = rule.target
        assert target.name == "h"
        assert target.qubits == ["q0"]
        assert target.params == []
        src = rule.sources
        expected_names = ["r", "r"]
        expected_qubits = [["q0"], ["q0"]]
        expected_params = [["pi/2", "pi/2"], ["pi", "0"]]
        for g, name, qubits, params in zip(
            src, expected_names, expected_qubits, expected_params
        ):
            assert g.name == name
            assert g.qubits == qubits
            assert g.params == params


class TestEquivalenceGraph:
    def test_no_decomposition_needed(self):
        g = EquivalenceGraph()
        source = [
            BaseOperation("rx"),
            BaseOperation("ry"),
            BaseOperation("rz"),
            BaseOperation("cx"),
        ]
        target = ["rx", "ry", "rz", "cx"]

        rules = g.get_optimal_decomposition_rule_dictionary(source, target)
        assert not rules

    def test_h_gates(self):
        g = EquivalenceGraph()
        source = [
            BaseOperation("h"),
        ]
        target = ["rx", "ry", "rz", "cx"]

        rules = g.get_optimal_decomposition_rule_dictionary(source, target)

        for gate in source:
            assert gate.name in rules

    def test_single_qubit_gates(self):
        g = EquivalenceGraph()
        target = ["rx", "ry", "rz", "cx"]

        single_qubit_gates = [
            "h",
            "x",
            "y",
            "z",
            "s",
            "p",
            "sdg",
            "t",
            "tdg",
            "sx",
            "sxdg",
            "u1",
            "u2",
            "u3",
            "u",
        ]
        for gate_name in single_qubit_gates:
            source = [BaseOperation(gate_name)]
            rules = g.get_optimal_decomposition_rule_dictionary(source, target)
            assert gate_name in rules

    def test_two_qubits_gates(self):
        g = EquivalenceGraph()
        target = ["rx", "ry", "rz", "cx"]

        two_qubit_gates = [
            "cy",
            "cz",
            "ch",
            "swap",
            "crx",
            "cry",
            "crz",
            "cu1",
            "cp",
            "cu3",
            "csx",
            "cu",
            "rxx",
            "rzz",
        ]
        for gate_name in two_qubit_gates:
            source = [BaseOperation(gate_name)]
            rules = g.get_optimal_decomposition_rule_dictionary(source, target)
            assert gate_name in rules

    def test_three_or_more_qubits_gates(self):
        g = EquivalenceGraph()
        target = ["rx", "ry", "rz", "cx"]

        three_or_more_qubit_gates = [
            "ccx",
            "cswap",
            "rccx",
            "rc3x",
            "c3x",
            "c3sqrtx",
            "c4x",
        ]
        for gate_name in three_or_more_qubit_gates:
            source = [BaseOperation(gate_name)]
            rules = g.get_optimal_decomposition_rule_dictionary(source, target)
            assert gate_name in rules
