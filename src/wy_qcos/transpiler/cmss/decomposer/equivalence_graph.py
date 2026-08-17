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

import heapq
import re
from dataclasses import dataclass

EquivalenceLibary: list[str] = [
    # reference from qiskit
    # https://github.com/wshanks/qiskit-terra/blob/main/qiskit/circuit/library/standard_gates/equivalence_library.py
    # HGate
    #
    #    ┌───┐        ┌─────────┐
    # q: ┤ H ├  ≡  q: ┤ U2(0,π) ├
    #    └───┘        └─────────┘
    "h() q0 -> u2(0, pi) q0",
    # CHGate
    #
    # q_0: ──■──     q_0: ─────────────────■─────────────────────
    #      ┌─┴─┐  ≡       ┌───┐┌───┐┌───┐┌─┴─┐┌─────┐┌───┐┌─────┐
    # q_1: ┤ H ├     q_1: ┤ S ├┤ H ├┤ T ├┤ X ├┤ Tdg ├┤ H ├┤ Sdg ├
    #      └───┘          └───┘└───┘└───┘└───┘└─────┘└───┘└─────┘
    (
        "ch() q0,q1 -> "
        "s() q1 | "
        "h() q1 | "
        "t() q1 | "
        "cx() q0,q1 | "
        "tdg() q1 | "
        "h() q1 | "
        "sdg() q1"
    ),
    # PhaseGate
    #
    #    ┌──────┐        ┌───────┐
    # q: ┤ P(ϴ) ├  ≡  q: ┤ U1(ϴ) ├
    #    └──────┘        └───────┘
    "p(theta) q0 -> u1(theta) q0",
    "p(theta) q0 -> u(0, 0, theta) q0",
    "p(theta) q0 -> u3(0, 0, theta) q0",
    "p(theta) q0 -> rz(theta) q0",
    # CPhaseGate
    #                      ┌────────┐
    # q_0: ─■────     q_0: ┤ P(ϴ/2) ├──■───────────────■────────────
    #       │P(ϴ)  ≡       └────────┘┌─┴─┐┌─────────┐┌─┴─┐┌────────┐
    # q_1: ─■────     q_1: ──────────┤ X ├┤ P(-ϴ/2) ├┤ X ├┤ P(ϴ/2) ├
    #                                └───┘└─────────┘└───┘└────────┘
    (
        "cp(theta) q0,q1 -> "
        "p(theta/2) q0 | "
        "cx() q0,q1 | "
        "p(-theta/2) q1 | "
        "cx() q0,q1 | "
        "p(theta/2) q1"
    ),
    # CPhaseGate
    #
    # q_0: ─■────     q_0: ─■────
    #       │P(ϴ)  ≡        │U1(ϴ)
    # q_1: ─■────     q_1: ─■────
    "cp(theta) q0,q1 -> cu1(theta) q0,q1",
    # RGate
    #
    #    ┌────────┐        ┌───────────────────────┐
    # q: ┤ R(ϴ,φ) ├  ≡  q: ┤ U3(ϴ,φ - π/2,π/2 - φ) ├
    #    └────────┘        └───────────────────────┘
    "r(theta, phi) q0 -> u3(theta, phi - pi/2, -phi + pi/2) q0",
    # RCCXGate
    #
    #      ┌───────┐
    # q_0: ┤0      ├     q_0: ────────────────────────■────────────────────────
    #      │       │                                  │
    # q_1: ┤1 Rccx ├  ≡  q_1: ────────────■───────────┼─────────■──────────────
    #      │       │          ┌───┐┌───┐┌─┴─┐┌─────┐┌─┴─┐┌───┐┌─┴─┐┌─────┐┌───┐
    # q_2: ┤2      ├     q_2: ┤ H ├┤ T ├┤ X ├┤ Tdg ├┤ X ├┤ T ├┤ X ├┤ Tdg ├┤ H ├
    #      └───────┘          └───┘└───┘└───┘└─────┘└───┘└───┘└───┘└─────┘└───┘
    (
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
    ),
    # RXGate
    #
    #    ┌───────┐        ┌────────┐
    # q: ┤ Rx(ϴ) ├  ≡  q: ┤ R(ϴ,0) ├
    #    └───────┘        └────────┘
    "rx(theta) q0 -> r(theta, 0) q0",
    # CRXGate
    #                                                              »
    # q_0: ────■────     q_0: ─────────────■────────────────────■──»
    #      ┌───┴───┐  ≡       ┌─────────┐┌─┴─┐┌──────────────┐┌─┴─┐»
    # q_1: ┤ Rx(ϴ) ├     q_1: ┤ U1(π/2) ├┤ X ├┤ U3(-ϴ/2,0,0) ├┤ X ├»
    #      └───────┘          └─────────┘└───┘└──────────────┘└───┘»
    # «
    # «q_0: ─────────────────
    # «     ┌────────────────┐
    # «q_1: ┤ U3(ϴ/2,-π/2,0) ├
    # «     └────────────────┘
    (
        "crx(theta) q0,q1 -> "
        "u1(pi/2) q1 | "
        "cx() q0,q1 | "
        "u3(-theta/2, 0, 0) q1 | "
        "cx() q0,q1 | "
        "u3(theta/2, -pi/2, 0) q1"
    ),
    # CRXGate
    #
    # q_0: ────■────     q_0: ───────■────────────────■────────────────────
    #      ┌───┴───┐  ≡       ┌───┐┌─┴─┐┌──────────┐┌─┴─┐┌─────────┐┌─────┐
    # q_1: ┤ Rx(ϴ) ├     q_1: ┤ S ├┤ X ├┤ Ry(-ϴ/2) ├┤ X ├┤ Ry(ϴ/2) ├┤ Sdg ├
    #      └───────┘          └───┘└───┘└──────────┘└───┘└─────────┘└─────┘
    (
        "crx(theta) q0,q1 -> "
        "s() q1 | "
        "cx() q0,q1 | "
        "ry(-theta/2) q1 | "
        "cx() q0,q1 | "
        "ry(theta/2) q1 | "
        "sdg() q1"
    ),
    (
        "rxx(theta) q0,q1 -> "
        "h() q0 | "
        "h() q1 | "
        "rzz(theta) q0,q1 | "
        "h() q0 | "
        "h() q1"
    ),
    # RZXGate
    #
    #      ┌─────────┐
    # q_0: ┤0        ├     q_0: ───────■─────────────■───────
    #      │  Rzx(ϴ) │  ≡       ┌───┐┌─┴─┐┌───────┐┌─┴─┐┌───┐
    # q_1: ┤1        ├     q_1: ┤ H ├┤ X ├┤ Rz(ϴ) ├┤ X ├┤ H ├
    #      └─────────┘          └───┘└───┘└───────┘└───┘└───┘
    (
        "rzx(theta) q0,q1 -> "
        "h() q1 | "
        "cx() q0,q1 | "
        "rz(theta) q1 | "
        "cx() q0,q1 | "
        "h() q1"
    ),
    # RYGate
    #
    #    ┌───────┐        ┌──────────┐
    # q: ┤ Ry(ϴ) ├  ≡  q: ┤ R(ϴ,π/2) ├
    #    └───────┘        └──────────┘
    "ry(theta) q0 -> r(theta, pi/2) q0",
    # CRYGate
    #
    # q_0: ────■────      q_0: ─────────────■────────────────■──
    #      ┌───┴───┐   ≡       ┌─────────┐┌─┴─┐┌──────────┐┌─┴─┐
    # q_1: ┤ Ry(ϴ) ├      q_1: ┤ Ry(ϴ/2) ├┤ X ├┤ Ry(-ϴ/2) ├┤ X ├
    #      └───────┘           └─────────┘└───┘└──────────┘└───┘
    (
        "cry(theta) q0,q1 -> "
        "ry(theta/2) q1 | "
        "cx() q0,q1 | "
        "ry(-theta/2) q1 | "
        "cx() q0,q1"
    ),
    # RYYGate
    #
    #      ┌─────────┐          ┌─────────┐                   ┌──────────┐
    # q_0: ┤0        ├     q_0: ┤ Rx(π/2) ├──■─────────────■──┤ Rx(-π/2) ├
    #      │  Ryy(ϴ) │  ≡       ├─────────┤┌─┴─┐┌───────┐┌─┴─┐├──────────┤
    # q_1: ┤1        ├     q_1: ┤ Rx(π/2) ├┤ X ├┤ Rz(ϴ) ├┤ X ├┤ Rx(-π/2) ├
    #      └─────────┘          └─────────┘└───┘└───────┘└───┘└──────────┘
    (
        "ryy(theta) q0,q1 -> "
        "rx(pi/2) q0 | "
        "rx(pi/2) q1 | "
        "cx() q0,q1 | "
        "rz(theta) q1 | "
        "cx() q0,q1 | "
        "rx(-pi/2) q0 | "
        "rx(-pi/2) q1"
    ),
    (
        "ryy(theta) q0,q1 -> "
        "rx(pi/2) q0 | "
        "rx(pi/2) q1 | "
        "rzz(theta) q0,q1 | "
        "rx(-pi/2) q0 | "
        "rx(-pi/2) q1"
    ),
    # RZGate
    #                  global phase: -ϴ/2
    #    ┌───────┐        ┌───────┐
    # q: ┤ Rz(ϴ) ├  ≡  q: ┤ U1(ϴ) ├
    #    └───────┘        └───────┘
    "rz(theta) q0 -> u1(theta) q0",
    "rz(theta) q0 -> h() q0 | rx(theta) q0 | h() q0",
    # RZGate
    #
    #    ┌───────┐        ┌────┐┌────────┐┌──────┐
    # q: ┤ Rz(ϴ) ├  ≡  q: ┤ √X ├┤ Ry(-ϴ) ├┤ √Xdg ├
    #    └───────┘        └────┘└────────┘└──────┘
    "rz(theta) q0 -> sx() q0 | ry(-theta) q0 | sxdg() q0",
    # CRZGate
    #
    # q_0: ────■────     q_0: ─────────────■────────────────■──
    #      ┌───┴───┐  ≡       ┌─────────┐┌─┴─┐┌──────────┐┌─┴─┐
    # q_1: ┤ Rz(ϴ) ├     q_1: ┤ Rz(ϴ/2) ├┤ X ├┤ Rz(-ϴ/2) ├┤ X ├
    #      └───────┘          └─────────┘└───┘└──────────┘└───┘
    (
        "crz(theta) q0,q1 -> "
        "rz(theta/2) q1 | "
        "cx() q0,q1 | "
        "rz(-theta/2) q1 | "
        "cx() q0,q1"
    ),
    # RZZGate
    #
    # q_0: ─■─────     q_0: ──■─────────────■──
    #       │ZZ(ϴ)  ≡       ┌─┴─┐┌───────┐┌─┴─┐
    # q_1: ─■─────     q_1: ┤ X ├┤ Rz(ϴ) ├┤ X ├
    #                       └───┘└───────┘└───┘
    "rzz(theta) q0,q1 -> cx() q0,q1 | rz(theta) q1 | cx() q0,q1",
    (
        "rzz(theta) q0,q1 -> "
        "h() q0 | "
        "h() q1 | "
        "rxx(theta) q0,q1 | "
        "h() q0 | "
        "h() q1"
    ),
    (
        "rzz(theta) q0,q1 -> "
        "rx(-pi/2) q0 | "
        "rx(-pi/2) q1 | "
        "ryy(theta) q0,q1 | "
        "rx(pi/2) q0 | "
        "rx(pi/2) q1"
    ),
    # RZXGate
    #
    #      ┌─────────┐
    # q_0: ┤0        ├     q_0: ───────■─────────────■───────
    #      │  Rzx(ϴ) │  ≡       ┌───┐┌─┴─┐┌───────┐┌─┴─┐┌───┐
    # q_1: ┤1        ├     q_1: ┤ H ├┤ X ├┤ Rz(ϴ) ├┤ X ├┤ H ├
    #      └─────────┘          └───┘└───┘└───────┘└───┘└───┘
    (
        "rzx(theta) q0,q1 -> "
        "h() q1 | "
        "cx() q0,q1 | "
        "rz(theta) q1 | "
        "cx() q0,q1 | "
        "h() q1"
    ),
    # ECRGate
    #
    #      ┌──────┐          ┌───────────┐┌───┐┌────────────┐
    # q_0: ┤0     ├     q_0: ┤0          ├┤ X ├┤0           ├
    #      │  Ecr │  ≡       │  Rzx(π/4) │└───┘│  Rzx(-π/4) │
    # q_1: ┤1     ├     q_1: ┤1          ├─────┤1           ├
    #      └──────┘          └───────────┘     └────────────┘
    "ecr() q0,q1 -> rzx(pi/4) q0,q1 | x() q0 | rzx(-pi/4) q0,q1",
    # SGate
    #
    #    ┌───┐        ┌─────────┐
    # q: ┤ S ├  ≡  q: ┤ U1(π/2) ├
    #    └───┘        └─────────┘
    "s() q0 -> u1(pi/2) q0",
    # SdgGate
    #
    #    ┌─────┐        ┌──────────┐
    # q: ┤ Sdg ├  ≡  q: ┤ U1(-π/2) ├
    #    └─────┘        └──────────┘
    "sdg() q0 -> u1(-pi/2) q0",
    # CSGate
    #
    # q_0: ──■──   q_0: ───────■────────
    #      ┌─┴─┐        ┌───┐┌─┴──┐┌───┐
    # q_1: ┤ S ├ = q_1: ┤ H ├┤ Sx ├┤ H ├
    #      └───┘        └───┘└────┘└───┘
    "cs() q0,q1 -> h() q1 | csx() q0,q1 | h() q1",
    # CSdgGate
    #
    # q_0: ───■───   q_0: ───────■────■────────
    #      ┌──┴──┐        ┌───┐┌─┴─┐┌─┴──┐┌───┐
    # q_1: ┤ Sdg ├ = q_1: ┤ H ├┤ X ├┤ Sx ├┤ H ├
    #      └─────┘        └───┘└───┘└────┘└───┘
    "csdg() q0,q1 -> h() q1 | cx() q0,q1 | csx() q0,q1 | h() q1",
    # SdgGate
    #
    #    ┌─────┐        ┌───┐┌───┐
    # q: ┤ Sdg ├  ≡  q: ┤ S ├┤ Z ├
    #    └─────┘        └───┘└───┘
    "sdg() q0 -> s() q0 | z() q0",
    # SdgGate
    #
    #    ┌─────┐        ┌───┐┌───┐
    # q: ┤ Sdg ├  ≡  q: ┤ Z ├┤ S ├
    #    └─────┘        └───┘└───┘
    "sdg() q0 -> z() q0 | s() q0",
    # SdgGate
    #
    #    ┌─────┐        ┌───┐┌───┐┌───┐
    # q: ┤ Sdg ├  ≡  q: ┤ S ├┤ S ├┤ S ├
    #    └─────┘        └───┘└───┘└───┘
    "sdg() q0 -> s() q0 | s() q0 | s() q0",
    # SwapGate
    #                        ┌───┐
    # q_0: ─X─     q_0: ──■──┤ X ├──■──
    #       │   ≡       ┌─┴─┐└─┬─┘┌─┴─┐
    # q_1: ─X─     q_1: ┤ X ├──■──┤ X ├
    #                   └───┘     └───┘
    "swap() q0,q1 -> cx() q0,q1 | cx() q1,q0 | cx() q0,q1",
    # iSwapGate
    #
    #      ┌────────┐          ┌───┐┌───┐     ┌───┐
    # q_0: ┤0       ├     q_0: ┤ S ├┤ H ├──■──┤ X ├─────
    #      │  Iswap │  ≡       ├───┤└───┘┌─┴─┐└─┬─┘┌───┐
    # q_1: ┤1       ├     q_1: ┤ S ├─────┤ X ├──■──┤ H ├
    #      └────────┘          └───┘     └───┘     └───┘
    (
        "iswap() q0,q1 -> "
        "s() q0 | "
        "s() q1 | "
        "h() q0 | "
        "cx() q0,q1 | "
        "cx() q1,q0 | "
        "h() q1"
    ),
    # SXGate
    #               global phase: π/4
    #    ┌────┐        ┌─────┐┌───┐┌─────┐
    # q: ┤ √X ├  ≡  q: ┤ Sdg ├┤ H ├┤ Sdg ├
    #    └────┘        └─────┘└───┘└─────┘
    "sx() q0 -> sdg() q0 | h() q0 | sdg() q0",
    # SXGate
    #               global phase: π/4
    #    ┌────┐        ┌─────────┐
    # q: ┤ √X ├  ≡  q: ┤ Rx(π/2) ├
    #    └────┘        └─────────┘
    "sx() q0 -> rx(pi/2) q0",
    # SXdgGate
    #                 global phase: 7π/4
    #    ┌──────┐        ┌───┐┌───┐┌───┐
    # q: ┤ √Xdg ├  ≡  q: ┤ S ├┤ H ├┤ S ├
    #    └──────┘        └───┘└───┘└───┘
    "sxdg() q0 -> s() q0 | h() q0 | s() q0",
    # SXdgGate
    #                 global phase: 7π/4
    #    ┌──────┐        ┌──────────┐
    # q: ┤ √Xdg ├  ≡  q: ┤ Rx(-π/2) ├
    #    └──────┘        └──────────┘
    "sxdg() q0 -> rx(-pi/2) q0",
    # IGate (Identity)
    #    ┌───┐        ┌───────────┐
    # q: ┤ I ├  ≡  q: ┤ U3(0,0,0) ├
    #    └───┘        └───────────┘
    "id() q0 -> u3(0,0,0) q0",
    # CSXGate
    #
    # q_0: ──■───     q_0: ──────■─────────────
    #      ┌─┴──┐  ≡       ┌───┐ │U1(π/2) ┌───┐
    # q_1: ┤ Sx ├     q_1: ┤ H ├─■────────┤ H ├
    #      └────┘          └───┘          └───┘
    "csx() q0,q1 -> h() q1 | cu1(pi/2) q0,q1 | h() q1",
    # CSXGate
    #                 global phase: π/8
    #                      ┌───┐┌───────────┐ ┌─────┐  ┌───┐
    # q_0: ──■───     q_0: ┤ X ├┤0          ├─┤ Tdg ├──┤ X ├
    #      ┌─┴──┐  ≡       └───┘│  Rzx(π/4) │┌┴─────┴─┐└───┘
    # q_1: ┤ Sx ├     q_1: ─────┤1          ├┤ sx^0.5 ├─────
    #      └────┘               └───────────┘└────────┘
    (
        "csx() q0,q1 -> "
        "x() q0 | "
        "rzx(pi/4) q0,q1 | "
        "tdg() q0 | "
        "x() q0 | "
        "rx(pi/4) q1"
    ),
    # DCXGate
    #
    #      ┌──────┐               ┌───┐
    # q_0: ┤0     ├     q_0: ──■──┤ X ├
    #      │  Dcx │  ≡       ┌─┴─┐└─┬─┘
    # q_1: ┤1     ├     q_1: ┤ X ├──■──
    #      └──────┘          └───┘
    "dcx() q0,q1 -> cx() q0,q1 | cx() q1,q0",
    # DCXGate
    #
    #      ┌──────┐           ┌───┐ ┌─────┐┌────────┐
    # q_0: ┤0     ├     q_0: ─┤ H ├─┤ Sdg ├┤0       ├─────
    #      │  Dcx │  ≡       ┌┴───┴┐└─────┘│  Iswap │┌───┐
    # q_1: ┤1     ├     q_1: ┤ Sdg ├───────┤1       ├┤ H ├
    #      └──────┘          └─────┘       └────────┘└───┘
    ("dcx() q0,q1 -> h() q0 | sdg() q0 | sdg() q1 | iswap() q0,q1 | h() q1"),
    # CSwapGate
    #
    # q_0: ─■─     q_0: ───────■───────
    #       │           ┌───┐  │  ┌───┐
    # q_1: ─X─  ≡  q_1: ┤ X ├──■──┤ X ├
    #       │           └─┬─┘┌─┴─┐└─┬─┘
    # q_2: ─X─     q_2: ──■──┤ X ├──■──
    #                        └───┘
    "cswap() q0,q1,q2 -> cx() q2,q1 | ccx() q0,q1,q2 | cx() q2,q1",
    # TGate
    #
    #    ┌───┐        ┌─────────┐
    # q: ┤ T ├  ≡  q: ┤ U1(π/4) ├
    #    └───┘        └─────────┘
    "t() q0 -> u1(pi/4) q0",
    # TdgGate
    #
    #    ┌─────┐        ┌──────────┐
    # q: ┤ Tdg ├  ≡  q: ┤ U1(-π/4) ├
    #    └─────┘        └──────────┘
    "tdg() q0 -> u1(-pi/4) q0",
    # UGate
    #
    #    ┌──────────┐        ┌───────────┐
    # q: ┤ U(θ,ϕ,λ) ├  ≡  q: ┤ U3(θ,ϕ,λ) ├
    #    └──────────┘        └───────────┘
    "u(theta,phi,lam) q0 -> u3(theta,phi,lam) q0",
    # CUGate
    #                                  ┌──────┐    ┌──────────────┐     »
    # q_0: ──────■───────     q_0: ────┤ P(γ) ├────┤ P(λ/2 + ϕ/2) ├──■──»
    #      ┌─────┴──────┐  ≡       ┌───┴──────┴───┐└──────────────┘┌─┴─┐»
    # q_1: ┤ U(θ,ϕ,λ,γ) ├     q_1: ┤ P(λ/2 - ϕ/2) ├────────────────┤ X ├»
    #      └────────────┘          └──────────────┘                └───┘»
    # «
    # «q_0: ──────────────────────────■────────────────
    # «     ┌──────────────────────┐┌─┴─┐┌────────────┐
    # «q_1: ┤ U(-θ/2,ϕ,-λ/2 - ϕ/2) ├┤ X ├┤ U(θ/2,ϕ,0) ├
    # «     └──────────────────────┘└───┘└────────────┘
    (
        "cu(theta,phi,lam,gamma) q0,q1 -> "
        "p(gamma) q0 | "
        "p((lam + phi)/2) q0 | "
        "p((lam - phi)/2) q1 | "
        "cx() q0,q1 | "
        "u(-theta/2,0,-(phi + lam)/2) q1 | "
        "cx() q0,q1 | "
        "u(theta/2,phi,0) q1"
    ),
    # CUGate
    #                              ┌──────┐
    # q_0: ──────■───────     q_0: ┤ P(γ) ├──────■──────
    #      ┌─────┴──────┐  ≡       └──────┘┌─────┴─────┐
    # q_1: ┤ U(θ,ϕ,λ,γ) ├     q_1: ────────┤ U3(θ,ϕ,λ) ├
    #      └────────────┘                  └───────────┘
    "cu(theta,phi,lam,gamma) q0,q1 -> p(gamma) q0 | cu3(theta,phi,lam) q0,q1",
    # U1Gate
    #
    #    ┌───────┐        ┌───────────┐
    # q: ┤ U1(θ) ├  ≡  q: ┤ U3(0,0,θ) ├
    #    └───────┘        └───────────┘
    "u1(theta) q0 -> u3(0,0,theta) q0",
    # U1Gate
    #
    #    ┌───────┐        ┌──────┐
    # q: ┤ U1(θ) ├  ≡  q: ┤ P(0) ├
    #    └───────┘        └──────┘
    "u1(theta) q0 -> p(theta) q0",
    # U1Gate
    #                  global phase: θ/2
    #    ┌───────┐        ┌───────┐
    # q: ┤ U1(θ) ├  ≡  q: ┤ Rz(θ) ├
    #    └───────┘        └───────┘
    "u1(theta) q0 -> rz(theta) q0",
    # CU1Gate
    #                       ┌─────────┐
    # q_0: ─■─────     q_0: ┤ U1(θ/2) ├──■────────────────■─────────────
    #       │U1(θ)  ≡       └─────────┘┌─┴─┐┌──────────┐┌─┴─┐┌─────────┐
    # q_1: ─■─────     q_1: ───────────┤ X ├┤ U1(-θ/2) ├┤ X ├┤ U1(θ/2) ├
    #                                  └───┘└──────────┘└───┘└─────────┘
    (
        "cu1(theta) q0,q1 -> "
        "u1(theta/2) q0 | "
        "cx() q0,q1 | "
        "u1(-theta/2) q1 | "
        "cx() q0,q1 | "
        "u1(theta/2) q1"
    ),
    # U2Gate
    #                    global phase: 7π/4
    #    ┌─────────┐        ┌─────────────┐┌────┐┌─────────────┐
    # q: ┤ U2(ϕ,λ) ├  ≡  q: ┤ U1(λ - π/2) ├┤ √X ├┤ U1(ϕ + π/2) ├
    #    └─────────┘        └─────────────┘└────┘└─────────────┘
    "u2(phi,lam) q0 -> u3(pi/2,phi,lam) q0",
    # U3Gate
    #                         global phase: λ/2 + ϕ/2 - π/2
    #    ┌───────────┐        ┌───────┐┌────┐┌───────────┐┌────┐┌────────────┐
    # q: ┤ U3(θ,ϕ,λ) ├  ≡  q: ┤ Rz(λ) ├┤ √X ├┤ Rz(θ + π) ├┤ √X ├┤ Rz(ϕ + 3π) ├
    #    └───────────┘        └───────┘└────┘└───────────┘└────┘└────────────┘
    (
        "u3(theta,phi,lam) q0 -> "
        "rz(lam) q0 | "
        "sx() q0 | "
        "rz(theta+pi) q0 | "
        "sx() q0 | "
        "rz(phi+3*pi) q0"
    ),
    # U3Gate
    #
    #    ┌───────────┐        ┌──────────┐
    # q: ┤ U3(θ,ϕ,λ) ├  ≡  q: ┤ U(θ,ϕ,λ) ├
    #    └───────────┘        └──────────┘
    "u3(theta,phi,lam) q0 -> u(theta,phi,lam) q0",
    # CU3Gate
    #                             ┌───────────────┐     »
    # q_0: ──────■──────     q_0: ┤ U1(λ/2 + ϕ/2) ├──■──»
    #      ┌─────┴─────┐  ≡       ├───────────────┤┌─┴─┐»
    # q_1: ┤ U3(θ,ϕ,λ) ├     q_1: ┤ U1(λ/2 - ϕ/2) ├┤ X ├»
    #      └───────────┘          └───────────────┘└───┘»
    # «
    # «q_0: ──────────────────────────■─────────────────
    # «    ┌───────────────────────┐┌─┴─┐┌─────────────┐
    # «q_1:┤ U3(-θ/2,0,-λ/2 - ϕ/2) ├┤ X ├┤ U3(θ/2,ϕ,0) ├
    # «    └───────────────────────┘└───┘└─────────────┘
    (
        "cu3(theta,phi,lam) q0,q1 -> "
        "u1((lam+phi)/2) q0 | "
        "u1((lam-phi)/2) q1 | "
        "cx() q0,q1 | "
        "u3(-theta/2,0,-(phi+lam)/2) q1 | "
        "cx() q0,q1 | "
        "u3(theta/2,phi,0) q1"
    ),
    "cu3(theta,phi,lam) q0,q1 -> cu(theta,phi,lam) q0,q1",
    # XGate
    #
    #    ┌───┐        ┌───────────┐
    # q: ┤ X ├  ≡  q: ┤ U3(π,0,π) ├
    #    └───┘        └───────────┘
    "x() q0 -> u3(pi,0,pi) q0",
    # XGate
    #
    #    ┌───┐        ┌───┐┌───┐┌───┐┌───┐
    # q: ┤ X ├  ≡  q: ┤ H ├┤ S ├┤ S ├┤ H ├
    #    └───┘        └───┘└───┘└───┘└───┘
    "x() q0 -> h() q0 | s() q0 | s() q0 | h() q0",
    # CXGate
    (
        "cx() q0,q1 -> "
        "ry(pi/2) q0 | "
        "rxx(pi/2) q0,q1 | "
        "rx(-pi/2) q0 | "
        "rx(-pi/2) q1 | "
        "ry(-pi/2) q0"
    ),
    (
        "cx() q0,q1 -> "
        "ry(pi/2) q0 | "
        "rxx(-pi/2) q0,q1 | "
        "rx(pi/2) q0 | "
        "rx(pi/2) q1 | "
        "ry(-pi/2) q0"
    ),
    (
        "cx() q0,q1 -> "
        "ry(-pi/2) q0 | "
        "rxx(pi/2) q0,q1 | "
        "rx(-pi/2) q0 | "
        "rx(pi/2) q1 | "
        "ry(pi/2) q0"
    ),
    (
        "cx() q0,q1 -> "
        "ry(-pi/2) q0 | "
        "rxx(-pi/2) q0,q1 | "
        "rx(pi/2) q0 | "
        "rx(-pi/2) q1 | "
        "ry(pi/2) q0"
    ),
    # CXGate
    #
    # q_0: ──■──     q_0: ──────■──────
    #      ┌─┴─┐  ≡       ┌───┐ │ ┌───┐
    # q_1: ┤ X ├     q_1: ┤ H ├─■─┤ H ├
    #      └───┘          └───┘   └───┘
    "cx() q0,q1 -> h() q1 | cz() q0,q1 | h() q1",
    # CXGate
    #                global phase: 3π/4
    #                     ┌───┐     ┌────────┐┌───┐     ┌────────┐»
    # q_0: ──■──     q_0: ┤ H ├─────┤0       ├┤ X ├─────┤0       ├»
    #      ┌─┴─┐  ≡       ├───┤┌───┐│  Iswap │├───┤┌───┐│  Iswap │»
    # q_1: ┤ X ├     q_1: ┤ X ├┤ H ├┤1       ├┤ X ├┤ H ├┤1       ├»
    #      └───┘          └───┘└───┘└────────┘└───┘└───┘└────────┘»
    # «     ┌───┐┌───┐
    # «q_0: ┤ H ├┤ S ├─────
    # «     ├───┤├───┤┌───┐
    # «q_1: ┤ S ├┤ X ├┤ H ├
    # «     └───┘└───┘└───┘
    (
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
    ),
    # CXGate
    #                global phase: 7π/4
    #                     ┌──────────┐┌───────┐┌──────┐
    # q_0: ──■──     q_0: ┤ Rz(-π/2) ├┤ Ry(π) ├┤0     ├
    #      ┌─┴─┐  ≡       ├─────────┬┘└───────┘│  Ecr │
    # q_1: ┤ X ├     q_1: ┤ Rx(π/2) ├──────────┤1     ├
    #      └───┘          └─────────┘          └──────┘
    "cx() q0,q1 -> rz(-pi/2) q0 | ry(pi) q0 | rx(pi/2) q1 | ecr() q0,q1",
    # CXGate
    # q_0: ──■──     q_0: ───────────────■───────────────────
    #      ┌─┴─┐  ≡       ┌────────────┐ │P(π) ┌────────────┐
    # q_1: ┤ X ├     q_1: ┤ U(π/2,0,π) ├─■─────┤ U(π/2,0,π) ├
    #      └───┘          └────────────┘       └────────────┘
    "cx() q0,q1 -> u(pi/2,0,pi) q1 | cp(pi) q0,q1 | u(pi/2,0,pi) q1",
    # CXGate
    #                     ┌────────────┐
    # q_0: ──■──     q_0: ┤ U(0,0,π/2) ├────■──────────────────
    #      ┌─┴─┐  ≡       ├────────────┤┌───┴───┐┌────────────┐
    # q_1: ┤ X ├     q_1: ┤ U(π/2,0,π) ├┤ Rz(π) ├┤ U(π/2,0,π) ├
    #      └───┘          └────────────┘└───────┘└────────────┘
    (
        "cx() q0,q1 -> "
        "u(pi/2,0,pi) q1 | "
        "u(0,0,pi/2) q0 | "
        "crz(pi) q0,q1 | "
        "u(pi/2,0,pi) q1"
    ),
    # CXGate
    #                global phase: π/4
    #                     ┌───────────┐┌─────┐
    # q_0: ──■──     q_0: ┤0          ├┤ Sdg ├─
    #      ┌─┴─┐  ≡       │  Rzx(π/2) │├─────┴┐
    # q_1: ┤ X ├     q_1: ┤1          ├┤ √Xdg ├
    #      └───┘          └───────────┘└──────┘
    "cx() q0,q1 -> rzx(pi/2) q0,q1 | sdg() q0 | sxdg() q1",
    # CCXGate
    #
    # q_0: ──■──     q_0: ───────────────────■────────────
    #        │                               │
    # q_1: ──■──  ≡  q_1: ───────■───────────┼─────────■──
    #      ┌─┴─┐          ┌───┐┌─┴─┐┌─────┐┌─┴─┐┌───┐┌─┴─┐
    # q_2: ┤ X ├     q_2: ┤ H ├┤ X ├┤ Tdg ├┤ X ├┤ T ├┤ X ├
    #      └───┘          └───┘└───┘└─────┘└───┘└───┘└───┘
    # «                       ┌───┐
    # «q_0: ─────────■────■───┤ T ├───■──
    # «      ┌───┐   │  ┌─┴─┐┌┴───┴┐┌─┴─┐
    # «q_1: ─┤ T ├───┼──┤ X ├┤ Tdg ├┤ X ├
    # «     ┌┴───┴┐┌─┴─┐├───┤└┬───┬┘└───┘
    # «q_2  ┤ Tdg ├┤ X ├┤ T ├─┤ H ├──────
    # «     └─────┘└───┘└───┘ └───┘
    (
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
    ),
    # CCXGate
    #
    # q_0: ──■──     q_0: ────────■─────────────────■────■───
    #        │                  ┌─┴─┐┌─────┐      ┌─┴─┐  │
    # q_1: ──■──  ≡  q_1: ──■───┤ X ├┤ Sdg ├──■───┤ X ├──┼───
    #      ┌─┴─┐          ┌─┴──┐├───┤└─────┘┌─┴──┐├───┤┌─┴──┐
    # q_2: ┤ X ├     q_2: ┤ Sx ├┤ Z ├───────┤ Sx ├┤ Z ├┤ Sx ├
    #      └───┘          └────┘└───┘       └────┘└───┘└────┘
    (
        "ccx() q0,q1,q2 -> "
        "csx() q1,q2 | "
        "cx() q0,q1 | "
        "z() q2 | "
        "sdg() q1 | "
        "csx() q1,q2 | "
        "z() q2 | "
        "cx() q0,q1 | "
        "csx() q0,q2"
    ),
    # YGate
    #              global phase: 3π/2
    #    ┌───┐        ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐
    # q: ┤ Y ├  ≡  q: ┤ H ├┤ S ├┤ S ├┤ H ├┤ S ├┤ S ├
    #    └───┘        └───┘└───┘└───┘└───┘└───┘└───┘
    "y() q0 -> u3(pi,pi/2,pi/2) q0",
    # YGate
    #              global phase: π/2
    #    ┌───┐        ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐
    # q: ┤ Y ├  ≡  q: ┤ S ├┤ S ├┤ H ├┤ S ├┤ S ├┤ H ├
    #    └───┘        └───┘└───┘└───┘└───┘└───┘└───┘
    "y() q0 -> s() q0 | s() q0 | h() q0 | s() q0 | s() q0 | h() q0",
    # CYGate
    #
    # q_0: ──■──     q_0: ─────────■───────
    #      ┌─┴─┐  ≡       ┌─────┐┌─┴─┐┌───┐
    # q_1: ┤ Y ├     q_1: ┤ Sdg ├┤ X ├┤ S ├
    #      └───┘          └─────┘└───┘└───┘
    "cy() q0,q1 -> sdg() q1 | cx() q0,q1 | s() q1",
    # ZGate
    #
    #    ┌───┐        ┌───────┐
    # q: ┤ Z ├  ≡  q: ┤ U1(π) ├
    #    └───┘        └───────┘
    "z() q0 -> u1(pi) q0",
    # ZGate
    #
    #    ┌───┐        ┌───┐┌───┐
    # q: ┤ Z ├  ≡  q: ┤ S ├┤ S ├
    #    └───┘        └───┘└───┘
    "z() q0 -> s() q0 | s() q0",
    # CZGate
    #
    # q_0: ─■─     q_0: ───────■───────
    #       │   ≡       ┌───┐┌─┴─┐┌───┐
    # q_1: ─■─     q_1: ┤ H ├┤ X ├┤ H ├
    #                   └───┘└───┘└───┘
    "cz() q0,q1 -> h() q1 | cx() q0,q1 | h() q1",
    # CCZGate
    #
    # q_0: ─■─   q_0: ───────■───────
    #       │                │
    # q_1: ─■─ = q_1: ───────■───────
    #       │         ┌───┐┌─┴─┐┌───┐
    # q_2: ─■─   q_2: ┤ H ├┤ X ├┤ H ├
    #                 └───┘└───┘└───┘
    "ccz() q0,q1,q2 -> h() q2 | ccx() q0,q1,q2 | h() q2",
    # XGate
    #              global phase: π/2
    #    ┌───┐        ┌───────┐
    # q: ┤ X ├  ≡  q: ┤ Rx(π) ├
    #    └───┘        └───────┘
    "x() q0 -> rx(pi) q0",
    # YGate
    #              global phase: π/2
    #    ┌───┐        ┌───────┐
    # q: ┤ Y ├  ≡  q: ┤ Ry(π) ├
    #    └───┘        └───────┘
    "y() q0 -> ry(pi) q0",
    # HGate
    #              global phase: π/2
    #    ┌───┐        ┌─────────┐┌───────┐
    # q: ┤ H ├  ≡  q: ┤ Ry(π/2) ├┤ Rx(π) ├
    #    └───┘        └─────────┘└───────┘
    "h() q0 -> ry(pi/2) q0 | rx(pi) q0",
    # HGate
    #              global phase: π/2
    #    ┌───┐        ┌────────────┐┌────────┐
    # q: ┤ H ├  ≡  q: ┤ R(π/2,π/2) ├┤ R(π,0) ├
    #    └───┘        └────────────┘└────────┘
    "h() q0 -> r(pi/2, pi/2) q0 | r(pi, 0) q0",
    # below are some added rules
    (
        "rc3x() q0,q1,q2,q3 -> "
        "u2(0,pi) q3 | "
        "u1(pi/4) q3 | "
        "cx() q2,q3 | "
        "u1(-pi/4) q3 | "
        "u2(0,pi) q3 | "
        "cx() q0,q3 | "
        "u1(pi/4) q3 | "
        "cx() q1,q3 | "
        "u1(-pi/4) q3 | "
        "cx() q0,q3 | "
        "u1(pi/4) q3 | "
        "cx() q1,q3 | "
        "u1(-pi/4) q3 | "
        "u2(0,pi) q3 | "
        "u1(pi/4) q3 | "
        "cx() q2,q3 | "
        "u1(-pi/4) q3 | "
        "u2(0,pi) q3"
    ),
    (
        "c3x() q0,q1,q2,q3 -> "
        "h() q3 | "
        "p(pi/8) q0 | "
        "p(pi/8) q1 | "
        "p(pi/8) q2 | "
        "p(pi/8) q3 | "
        "cx() q0,q1 | "
        "p(-pi/8) q1 | "
        "cx() q0,q1 | "
        "cx() q1,q2 | "
        "p(-pi/8) q2 | "
        "cx() q0,q2 | "
        "p(pi/8) q2 | "
        "cx() q1,q2 | "
        "p(-pi/8) q2 | "
        "cx() q0,q2 | "
        "cx() q2,q3 | "
        "p(-pi/8) q3 | "
        "cx() q1,q3 | "
        "p(pi/8) q3 | "
        "cx() q2,q3 | "
        "p(-pi/8) q3 | "
        "cx() q0,q3 | "
        "p(pi/8) q3 | "
        "cx() q2,q3 | "
        "p(-pi/8) q3 | "
        "cx() q1,q3 | "
        "p(pi/8) q3 | "
        "cx() q2,q3 | "
        "p(-pi/8) q3 | "
        "cx() q0,q3 | "
        "h() q3"
    ),
    (
        "c3sqrtx() q0,q1,q2,q3 -> "
        "h() q3 | cu1(pi/8) q0,q3 | h() q3 | "
        "cx() q0,q1 | "
        "h() q3 | cu1(-pi/8) q1,q3 | h() q3 | "
        "cx() q0,q1 | "
        "h() q3 | cu1(pi/8) q1,q3 | h() q3 | "
        "cx() q1,q2 | "
        "h() q3 | cu1(-pi/8) q2,q3 | h() q3 | "
        "cx() q0,q2 | "
        "h() q3 | cu1(pi/8) q2,q3 | h() q3 | "
        "cx() q1,q2 | "
        "h() q3 | cu1(-pi/8) q2,q3 | h() q3 | "
        "cx() q0,q2 | "
        "h() q3 | cu1(pi/8) q2,q3 | h() q3"
    ),
    (
        "c4x() q0,q1,q2,q3,q4 -> "
        "h() q4 | cu1(pi/2) q3,q4 | h() q4 | "
        "c3x() q0,q1,q2,q3 | "
        "h() q4 | cu1(-pi/2) q3,q4 | h() q4 | "
        "c3x() q0,q1,q2,q3 | "
        "c3sqrtx() q0,q1,q2,q4"
    ),
]


@dataclass(frozen=True)
class ParamGate:
    """Represents a parameterized quantum gate.

    This class contains:
        - name (str): The name of the gate (e.g., 'u3', 'cx').
        - qubits (list[str]): list of qubit identifiers this gate acts on.
        - params (list[str], optional):
          list of parameter expressions for the gate.
    """

    name: str
    qubits: tuple[str, ...]
    params: tuple[str, ...] = ()


class EquivalenceRule:
    """Represents an equivalence rule for decomposing gates.

    The rule is specified in a DSL string, for example:
        "cx() q0,q1 -> u(pi/2,0,pi) q1 | cp(pi) q0,q1 | u(pi/2,0,pi) q1"
    """

    def __init__(self, dsl: str):
        """Initializes an EquivalenceRule from a DSL string.

        Args:
            dsl (str): The equivalence rule DSL string.
        """
        self.target, self.sources = self._parse_dsl(dsl)

    def _parse_dsl(self, dsl: str) -> tuple[ParamGate, list[ParamGate]]:
        """Parses a DSL string into target and source gates.

        Args:
            dsl (str): The equivalence rule DSL string.

        Returns:
            tuple[ParamGate, list[ParamGate]]: The target gate and
                list of source gates.

        Raises:
            ValueError: If the DSL cannot be parsed.
        """
        lhs, rhs = dsl.split("->", 1)
        target = self._parse_gate_block(lhs.strip())
        sources = [
            self._parse_gate_block(x.strip())
            for x in rhs.split("|")
            if x.strip()
        ]
        return target, sources

    def _parse_gate_block(self, block: str) -> ParamGate:
        """Parses a single gate block into a ParamGate.

        Args:
            block (str): Gate block string, e.g., 'u3(theta,phi,lam) q0,q1'.

        Returns:
            ParamGate: The parsed ParamGate object.

        Raises:
            ValueError: If parsing fails or qubits are missing.
        """
        block = block.strip()
        i = block.find("(")
        j = block.rfind(")", i)
        if i < 0 or j < 0:
            raise ValueError(f"can't parse gate block: {block}")

        name = block[:i].strip()
        params_str = block[i + 1 : j].strip()
        qubit_str = block[j + 1 :].strip()

        if not qubit_str:
            raise ValueError(f"no qubit list: {block}")

        qubits = tuple([q.strip() for q in qubit_str.split(",")])  # pylint: disable=consider-using-generator
        params = (
            tuple([p.strip() for p in params_str.split(",")])  # pylint: disable=consider-using-generator
            if params_str
            else ()
        )

        return ParamGate(name=name, params=params, qubits=qubits)


@dataclass(frozen=True)
class RuleEdge:
    src: str  # gate name
    dst: str  # gate name
    rule: EquivalenceRule
    kind: str  # "require" | "produce"


class EquivalenceGraph:
    """Graph of equivalence rules for quantum gate decomposition."""

    def __init__(self) -> None:
        """Initializes an empty EquivalenceGraph."""
        self.rules: list[EquivalenceRule] = [
            EquivalenceRule(rule) for rule in EquivalenceLibary
        ]

        # target_gate → list of rules
        self.forward_index = {}  # str -> list[EquivalenceRule]

        # source_gate → list of rules whose target contains this source
        self.reverse_index = {}  # str -> list[EquivalenceRule]

        for r in self.rules:
            self.forward_index.setdefault(r.target.name, []).append(r)
            for src in r.sources:
                self.reverse_index.setdefault(src.name, []).append(r)

    def _rule_cost(self, rule: EquivalenceRule) -> float:
        """Cost = number of gates in decomposition."""
        return float(len(rule.sources))

    def get_optimal_decomposition_rule_dictionary(
        self, source: list[str], target: list[str]
    ) -> dict[str, EquivalenceRule]:
        """Generate optimal decomposition rules.

        Generates a dictionary of optimal decomposition rules for given
        source and target operations.

        Args:
            source (list[str]): List of source gate names to be decomposed.
            target (list[str]): List of target operations to achieve.

        Returns:
            dict[str, EquivalenceRule]: A mapping from operation name to
            equivalence rule.
        """
        EXCLUDED_GATES = {"measure", "reset", "sync", "move"}

        for gate in EXCLUDED_GATES:
            if gate not in target:
                target.append(gate)

        visited_gates: set[str] = set()
        left_source_gates: set[str] = set(x for x in source if x not in target)

        cost_map: dict[str, float] = {}
        optimal_rules: dict[str, EquivalenceRule] = {}
        priority_queue = []
        counter = 0

        for gate_name in target:
            heapq.heappush(priority_queue, (0.0, counter, gate_name))
            counter += 1
            visited_gates.add(gate_name)
            cost_map[gate_name] = 0.0

        while priority_queue:
            cost, _, gate_name = heapq.heappop(priority_queue)
            left_source_gates.discard(gate_name)
            if not left_source_gates:
                return optimal_rules
            # this gate has optimal rules
            if cost_map.get(gate_name, float("inf")) < cost:
                continue

            # this gate has no reverse rules
            if gate_name not in self.reverse_index:
                continue

            for rule in self.reverse_index[gate_name]:
                rule_cost = self._rule_cost(rule)
                if all(s.name in visited_gates for s in rule.sources):
                    new_cost = (
                        sum(cost_map[s.name] for s in rule.sources) + rule_cost
                    )
                    if (
                        rule.target.name not in cost_map
                        or cost_map[rule.target.name] > new_cost
                    ):
                        heapq.heappush(
                            priority_queue,
                            (new_cost, counter, rule.target.name),
                        )
                        counter += 1
                        visited_gates.add(rule.target.name)
                        cost_map[rule.target.name] = new_cost
                        optimal_rules[rule.target.name] = rule

        return {}

    def rule_edges(self) -> list[RuleEdge]:
        """Return all edges in the equivalence rule graph.

        Each edge represents a transformation relationship derived from a rule.
        An edge goes from a source gate to a target gate and carries the rule
        that produces the target from the source.

        Returns:
            list[RuleEdge]: A list of RuleEdge objects representing all
            producer edges in the equivalence rule graph.
        """
        edges: list[RuleEdge] = []

        for rule in self.rules:
            target = rule.target.name

            for src in rule.sources:
                edges.append(
                    RuleEdge(
                        src=src.name,
                        dst=target,
                        rule=rule,
                        kind="produce",
                    )
                )

        return edges

    def to_dot(self) -> str:
        """Generate a Graphviz DOT representation of the rule graph.

        This visualization shows:

        - Gate nodes as ellipses.
        - Rule nodes as boxes.
        - Directed edges from source gates to rule nodes,
          and from rule nodes to target gates.

        Returns:
            str: A DOT-format string that can be rendered by Graphviz to
            visualize the equivalence rule graph.
        """
        lines = [
            "digraph EquivalenceRuleGraph {",
            "  rankdir=LR;",
            "  node [fontname=Helvetica];",
        ]

        # Gate nodes
        gate_names = set()
        for r in self.rules:
            gate_names.add(r.target.name)
            for s in r.sources:
                gate_names.add(s.name)

        for g in gate_names:
            lines.append(
                f'  "{g}" [shape=ellipse, style=filled, fillcolor=lightblue];'
            )

        # Rule nodes
        rule_ids = {}
        for idx, r in enumerate(self.rules):
            rule_ids[r] = f"rule_{idx}"
            label = f"{r.target.name} <- " + ",".join(
                s.name for s in r.sources
            )
            lines.append(f'  "{rule_ids[r]}" [shape=box, label="{label}"];')

        # Edges
        for r in self.rules:
            rule_node = rule_ids[r]

            for s in r.sources:
                lines.append(f'  "{s.name}" -> "{rule_node}";')

            lines.append(f'  "{rule_node}" -> "{r.target.name}";')

        lines.append("}")
        return "\n".join(lines)

    def _rewrite_params(
        self,
        exprs: tuple[str, ...],
        param_map: dict[str, str],
    ) -> tuple[str, ...]:
        """Rewrite parameter expressions using a parameter map.

        Each parameter token is replaced only when it appears as a full token.

        Args:
            exprs: Original parameter expression tuple.
            param_map: Mapping from symbolic parameter to expression string.

        Returns:
            Rewritten parameter tuple, or None if no parameters.
        """
        rewritten: list[str] = []

        for expr in exprs:
            new_expr = expr

            for key, value in param_map.items():
                pattern = rf"\b{re.escape(key)}\b"
                replacement = f"({value})"
                new_expr = re.sub(pattern, replacement, new_expr)

            rewritten.append(new_expr)

        return tuple(rewritten)

    def _expand_gate_recursive(
        self,
        gate: ParamGate,
        rule_map: dict[str, EquivalenceRule],
        target_set: set[str],
        cache: dict[ParamGate, list[ParamGate]],
        path: set[ParamGate],
    ) -> list[ParamGate]:
        """Recursively expand a ParamGate into target-gate sequence.

        Args:
            gate: Gate to expand.
            rule_map: Gate name -> decomposition rule.
            target_set: Names of target gates.
            cache: Memoization cache.
            path: Current recursion stack for cycle detection.

        Returns:
            Fully expanded ParamGate sequence.

        Raises:
            ValueError: If rule missing, parameter mismatch, or cycle detected.
        """
        # -------- Target gate reached --------
        if gate.name in target_set:
            return [gate]

        # -------- Cache --------
        cached = cache.get(gate)
        if cached is not None:
            return cached

        # -------- Cycle detection --------
        if gate in path:
            raise ValueError(f"Cycle detected at gate {gate}")

        rule = rule_map.get(gate.name)
        if rule is None:
            raise ValueError(f"No rule for gate {gate.name}")

        # -------- Parameter binding --------
        param_map: dict[str, str] = {}

        template = rule.target

        if template.params:
            if not gate.params or len(gate.params) != len(template.params):
                raise ValueError(
                    "Parameter mismatch for gate "
                    f"{gate.name}: expected {template.params}, "
                    f"got {gate.params}"
                )

            param_map = dict(zip(template.params, gate.params))

        # -------- Enter recursion path --------
        path.add(gate)

        result: list[ParamGate] = []

        for source_gate in rule.sources:
            # ---- Qubit mapping ----
            qubit_map = dict(zip(template.qubits, gate.qubits))
            mapped_qubits = tuple(qubit_map[q] for q in source_gate.qubits)

            # ---- Parameter rewrite ----
            rewritten_params = self._rewrite_params(
                source_gate.params,
                param_map,
            )

            rewritten_gate = ParamGate(
                name=source_gate.name,
                qubits=mapped_qubits,
                params=rewritten_params,
            )

            sub_expanded = self._expand_gate_recursive(
                gate=rewritten_gate,
                rule_map=rule_map,
                target_set=target_set,
                cache=cache,
                path=path,
            )

            result.extend(sub_expanded)

        # -------- Exit recursion path --------
        path.remove(gate)

        cache[gate] = result
        return result

    def build_full_decomposition_table(
        self,
        source: list[str],
        target: list[str],
        enable_mapping: bool = True,
        is_neutral_atom: bool = False,
    ) -> tuple[
        dict[ParamGate, list[ParamGate]],
        dict[str, int],
    ]:
        """Build full decomposition table for all non-target gates.

        Args:
            source: Source gate names that may require decomposition.
            target: Target gate name set (basis gates).
            enable_mapping: Whether mapping (routing) is enabled. Only when
                mapping is enabled is the SWAP gate added to the source set,
                since its decomposition depth is used by the mapping module.
            is_neutral_atom: Whether the target device is a neutral-atom
                system. Neutral-atom routing does not rely on SWAP insertion
                and its basis gate set may lack a two-qubit gate to decompose
                SWAP, so SWAP is skipped to avoid spurious "No rule for gate
                swap" errors. SWAP is only added when mapping is enabled AND
                the device is not a neutral-atom system.

        Returns:
            tuple[dict[ParamGate, list[ParamGate]], dict[str, int]]:
                Decomposition table and gate expansion count map.

        Raises:
            ValueError: If decomposition rule missing.
        """
        # Only require SWAP decomposition when mapping is enabled and the
        # device is not a neutral-atom system. Neutral-atom routing does not
        # insert SWAPs, and the basis gate set may lack a two-qubit gate to
        # decompose SWAP (swap -> cx -> cz).
        require_swap = enable_mapping and not is_neutral_atom
        effective_source = source + ["swap"] if require_swap else source

        # Compute additional SWAP depth for the mapping module
        rule_map = self.get_optimal_decomposition_rule_dictionary(
            effective_source,
            target,
        )

        target_set = set(target)

        cache: dict[ParamGate, list[ParamGate]] = {}
        table: dict[ParamGate, list[ParamGate]] = {}
        count_map: dict[str, int] = {}

        for name in effective_source:
            if name in target_set:
                count_map[name] = 1
                continue

            rule = rule_map.get(name)
            if rule is None:
                raise ValueError(f"No rule for gate {name}")

            template_gate = rule.target

            if template_gate in table:
                continue

            expanded = self._expand_gate_recursive(
                gate=template_gate,
                rule_map=rule_map,
                target_set=target_set,
                cache=cache,
                path=set(),
            )

            table[template_gate] = expanded
            count_map[template_gate.name] = len(expanded) + 1

        return table, count_map
