/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

 #include "decomposer/equivalence_graph.h"

 #include <sstream>
 #include <regex>
 #include <queue>
 #include <stdexcept>

using namespace std;
namespace qcos {
vector<string> EquivalenceLibary = {
   //reference from qiskit
     //https://github.com/wshanks/qiskit-terra/blob/main/qiskit/circuit/library/standard_gates/equivalence_library.py
     //HGate
     //
     //   ┌───┐        ┌─────────┐
     //q: ┤ H ├  ≡  q: ┤ U2(0,π) ├
     //   └───┘        └─────────┘
    "h() q0 -> u2(0, pi) q0",
     //CHGate
     //
     //q_0: ──■──     q_0: ─────────────────■─────────────────────
     //     ┌─┴─┐  ≡       ┌───┐┌───┐┌───┐┌─┴─┐┌─────┐┌───┐┌─────┐
     //q_1: ┤ H ├     q_1: ┤ S ├┤ H ├┤ T ├┤ X ├┤ Tdg ├┤ H ├┤ Sdg ├
     //     └───┘          └───┘└───┘└───┘└───┘└─────┘└───┘└─────┘
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
     //PhaseGate
     //
     //   ┌──────┐        ┌───────┐
     //q: ┤ P(ϴ) ├  ≡  q: ┤ U1(ϴ) ├
     //   └──────┘        └───────┘
    "p(theta) q0 -> u1(theta) q0",
    "p(theta) q0 -> u(0, 0, theta) q0",
     //CPhaseGate
     //                     ┌────────┐
     //q_0: ─■────     q_0: ┤ P(ϴ/2) ├──■───────────────■────────────
     //      │P(ϴ)  ≡       └────────┘┌─┴─┐┌─────────┐┌─┴─┐┌────────┐
     //q_1: ─■────     q_1: ──────────┤ X ├┤ P(-ϴ/2) ├┤ X ├┤ P(ϴ/2) ├
     //                               └───┘└─────────┘└───┘└────────┘
    (
        "cp(theta) q0,q1 -> "
        "p(theta/2) q0 | "
        "cx() q0,q1 | "
        "p(-theta/2) q1 | "
        "cx() q0,q1 | "
        "p(theta/2) q1"
    ),
     //CPhaseGate
     //
     //q_0: ─■────     q_0: ─■────
     //      │P(ϴ)  ≡        │U1(ϴ)
     //q_1: ─■────     q_1: ─■────
    "cp(theta) q0,q1 -> cu1(theta) q0,q1",
     //RGate
     //
     //   ┌────────┐        ┌───────────────────────┐
     //q: ┤ R(ϴ,φ) ├  ≡  q: ┤ U3(ϴ,φ - π/2,π/2 - φ) ├
     //   └────────┘        └───────────────────────┘
    "r(theta, phi) q0 -> u3(theta, phi - pi/2, -phi + pi/2) q0",
     //RCCXGate
     //
     //     ┌───────┐
     //q_0: ┤0      ├     q_0: ────────────────────────■────────────────────────
     //     │       │                                  │
     //q_1: ┤1 Rccx ├  ≡  q_1: ────────────■───────────┼─────────■──────────────
     //     │       │          ┌───┐┌───┐┌─┴─┐┌─────┐┌─┴─┐┌───┐┌─┴─┐┌─────┐┌───┐
     //q_2: ┤2      ├     q_2: ┤ H ├┤ T ├┤ X ├┤ Tdg ├┤ X ├┤ T ├┤ X ├┤ Tdg ├┤ H ├
     //     └───────┘          └───┘└───┘└───┘└─────┘└───┘└───┘└───┘└─────┘└───┘
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
     //RXGate
     //
     //   ┌───────┐        ┌────────┐
     //q: ┤ Rx(ϴ) ├  ≡  q: ┤ R(ϴ,0) ├
     //   └───────┘        └────────┘
    "rx(theta) q0 -> r(theta, 0) q0",
     //CRXGate
     //                                                             »
     //q_0: ────■────     q_0: ─────────────■────────────────────■──»
     //     ┌───┴───┐  ≡       ┌─────────┐┌─┴─┐┌──────────────┐┌─┴─┐»
     //q_1: ┤ Rx(ϴ) ├     q_1: ┤ U1(π/2) ├┤ X ├┤ U3(-ϴ/2,0,0) ├┤ X ├»
     //     └───────┘          └─────────┘└───┘└──────────────┘└───┘»
     // 
     // q_0: ─────────────────
     //      ┌────────────────┐
     // q_1: ┤ U3(ϴ/2,-π/2,0) ├
     //      └────────────────┘
    (
        "crx(theta) q0,q1 -> "
        "u1(pi/2) q1 | "
        "cx() q0,q1 | "
        "u3(-theta/2, 0, 0) q1 | "
        "cx() q0,q1 | "
        "u3(theta/2, -pi/2, 0) q1"
    ),
     //CRXGate
     //
     //q_0: ────■────     q_0: ───────■────────────────■────────────────────
     //     ┌───┴───┐  ≡       ┌───┐┌─┴─┐┌──────────┐┌─┴─┐┌─────────┐┌─────┐
     //q_1: ┤ Rx(ϴ) ├     q_1: ┤ S ├┤ X ├┤ Ry(-ϴ/2) ├┤ X ├┤ Ry(ϴ/2) ├┤ Sdg ├
     //     └───────┘          └───┘└───┘└──────────┘└───┘└─────────┘└─────┘
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
     //RZXGate
     //
     //     ┌─────────┐
     //q_0: ┤0        ├     q_0: ───────■─────────────■───────
     //     │  Rzx(ϴ) │  ≡       ┌───┐┌─┴─┐┌───────┐┌─┴─┐┌───┐
     //q_1: ┤1        ├     q_1: ┤ H ├┤ X ├┤ Rz(ϴ) ├┤ X ├┤ H ├
     //     └─────────┘          └───┘└───┘└───────┘└───┘└───┘
    (
        "rzx(theta) q0,q1 -> "
        "h() q1 | "
        "cx() q0,q1 | "
        "rz(theta) q1 | "
        "cx() q0,q1 | "
        "h() q1"
    ),
     //RYGate
     //
     //   ┌───────┐        ┌──────────┐
     //q: ┤ Ry(ϴ) ├  ≡  q: ┤ R(ϴ,π/2) ├
     //   └───────┘        └──────────┘
    "ry(theta) q0 -> r(theta, pi/2) q0",
     //CRYGate
     //
     //q_0: ────■────      q_0: ─────────────■────────────────■──
     //     ┌───┴───┐   ≡       ┌─────────┐┌─┴─┐┌──────────┐┌─┴─┐
     //q_1: ┤ Ry(ϴ) ├      q_1: ┤ Ry(ϴ/2) ├┤ X ├┤ Ry(-ϴ/2) ├┤ X ├
     //     └───────┘           └─────────┘└───┘└──────────┘└───┘
    (
        "cry(theta) q0,q1 -> "
        "ry(theta/2) q1 | "
        "cx() q0,q1 | "
        "ry(-theta/2) q1 | "
        "cx() q0,q1"
    ),
     //RYYGate
     //
     //     ┌─────────┐          ┌─────────┐                   ┌──────────┐
     //q_0: ┤0        ├     q_0: ┤ Rx(π/2) ├──■─────────────■──┤ Rx(-π/2) ├
     //     │  Ryy(ϴ) │  ≡       ├─────────┤┌─┴─┐┌───────┐┌─┴─┐├──────────┤
     //q_1: ┤1        ├     q_1: ┤ Rx(π/2) ├┤ X ├┤ Rz(ϴ) ├┤ X ├┤ Rx(-π/2) ├
     //     └─────────┘          └─────────┘└───┘└───────┘└───┘└──────────┘
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
     //RZGate
     //                 global phase: -ϴ/2
     //   ┌───────┐        ┌───────┐
     //q: ┤ Rz(ϴ) ├  ≡  q: ┤ U1(ϴ) ├
     //   └───────┘        └───────┘
    "rz(theta) q0 -> u1(theta) q0",
     //RZGate
     //
     //   ┌───────┐        ┌────┐┌────────┐┌──────┐
     //q: ┤ Rz(ϴ) ├  ≡  q: ┤ √X ├┤ Ry(-ϴ) ├┤ √Xdg ├
     //   └───────┘        └────┘└────────┘└──────┘
    "rz(theta) q0 -> sx() q0 | ry(-theta) q0 | sxdg() q0",
     //CRZGate
     //
     //q_0: ────■────     q_0: ─────────────■────────────────■──
     //     ┌───┴───┐  ≡       ┌─────────┐┌─┴─┐┌──────────┐┌─┴─┐
     //q_1: ┤ Rz(ϴ) ├     q_1: ┤ Rz(ϴ/2) ├┤ X ├┤ Rz(-ϴ/2) ├┤ X ├
     //     └───────┘          └─────────┘└───┘└──────────┘└───┘
    (
        "crz(theta) q0,q1 -> "
        "rz(theta/2) q1 | "
        "cx() q0,q1 | "
        "rz(-theta/2) q1 | "
        "cx() q0,q1"
    ),
     //RZZGate
     //
     //q_0: ─■─────     q_0: ──■─────────────■──
     //      │ZZ(ϴ)  ≡       ┌─┴─┐┌───────┐┌─┴─┐
     //q_1: ─■─────     q_1: ┤ X ├┤ Rz(ϴ) ├┤ X ├
     //                      └───┘└───────┘└───┘
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
     //RZXGate
     //
     //     ┌─────────┐
     //q_0: ┤0        ├     q_0: ───────■─────────────■───────
     //     │  Rzx(ϴ) │  ≡       ┌───┐┌─┴─┐┌───────┐┌─┴─┐┌───┐
     //q_1: ┤1        ├     q_1: ┤ H ├┤ X ├┤ Rz(ϴ) ├┤ X ├┤ H ├
     //     └─────────┘          └───┘└───┘└───────┘└───┘└───┘
    (
        "rzx(theta) q0,q1 -> "
        "h() q1 | "
        "cx() q0,q1 | "
        "rz(theta) q1 | "
        "cx() q0,q1 | "
        "h() q1"
    ),
     //ECRGate
     //
     //     ┌──────┐          ┌───────────┐┌───┐┌────────────┐
     //q_0: ┤0     ├     q_0: ┤0          ├┤ X ├┤0           ├
     //     │  Ecr │  ≡       │  Rzx(π/4) │└───┘│  Rzx(-π/4) │
     //q_1: ┤1     ├     q_1: ┤1          ├─────┤1           ├
     //     └──────┘          └───────────┘     └────────────┘
    "ecr() q0,q1 -> rzx(pi/4) q0,q1 | x() q0 | rzx(-pi/4) q0,q1",
     //SGate
     //
     //   ┌───┐        ┌─────────┐
     //q: ┤ S ├  ≡  q: ┤ U1(π/2) ├
     //   └───┘        └─────────┘
    "s() q0 -> u1(pi/2) q0",
     //SdgGate
     //
     //   ┌─────┐        ┌──────────┐
     //q: ┤ Sdg ├  ≡  q: ┤ U1(-π/2) ├
     //   └─────┘        └──────────┘
    "sdg() q0 -> u1(-pi/2) q0",
     //CSGate
     //
     //q_0: ──■──   q_0: ───────■────────
     //     ┌─┴─┐        ┌───┐┌─┴──┐┌───┐
     //q_1: ┤ S ├ = q_1: ┤ H ├┤ Sx ├┤ H ├
     //     └───┘        └───┘└────┘└───┘
    "cs() q0,q1 -> h() q1 | csx() q0,q1 | h() q1",
     //CSdgGate
     //
     //q_0: ───■───   q_0: ───────■────■────────
     //     ┌──┴──┐        ┌───┐┌─┴─┐┌─┴──┐┌───┐
     //q_1: ┤ Sdg ├ = q_1: ┤ H ├┤ X ├┤ Sx ├┤ H ├
     //     └─────┘        └───┘└───┘└────┘└───┘
    "csdg() q0,q1 -> h() q1 | cx() q0,q1 | csx() q0,q1 | h() q1",
     //SdgGate
     //
     //   ┌─────┐        ┌───┐┌───┐
     //q: ┤ Sdg ├  ≡  q: ┤ S ├┤ Z ├
     //   └─────┘        └───┘└───┘
    "sdg() q0 -> s() q0 | z() q0",
     //SdgGate
     //
     //   ┌─────┐        ┌───┐┌───┐
     //q: ┤ Sdg ├  ≡  q: ┤ Z ├┤ S ├
     //   └─────┘        └───┘└───┘
    "sdg() q0 -> z() q0 | s() q0",
     //SdgGate
     //
     //   ┌─────┐        ┌───┐┌───┐┌───┐
     //q: ┤ Sdg ├  ≡  q: ┤ S ├┤ S ├┤ S ├
     //   └─────┘        └───┘└───┘└───┘
    "sdg() q0 -> s() q0 | s() q0 | s() q0",
     //SwapGate
     //                       ┌───┐
     //q_0: ─X─     q_0: ──■──┤ X ├──■──
     //      │   ≡       ┌─┴─┐└─┬─┘┌─┴─┐
     //q_1: ─X─     q_1: ┤ X ├──■──┤ X ├
     //                  └───┘     └───┘
    "swap() q0,q1 -> cx() q0,q1 | cx() q1,q0 | cx() q0,q1",
     //iSwapGate
     //
     //     ┌────────┐          ┌───┐┌───┐     ┌───┐
     //q_0: ┤0       ├     q_0: ┤ S ├┤ H ├──■──┤ X ├─────
     //     │  Iswap │  ≡       ├───┤└───┘┌─┴─┐└─┬─┘┌───┐
     //q_1: ┤1       ├     q_1: ┤ S ├─────┤ X ├──■──┤ H ├
     //     └────────┘          └───┘     └───┘     └───┘
    (
        "iswap() q0,q1 -> "
        "s() q0 | "
        "s() q1 | "
        "h() q0 | "
        "cx() q0,q1 | "
        "cx() q1,q0 | "
        "h() q1"
    ),
     //SXGate
     //              global phase: π/4
     //   ┌────┐        ┌─────┐┌───┐┌─────┐
     //q: ┤ √X ├  ≡  q: ┤ Sdg ├┤ H ├┤ Sdg ├
     //   └────┘        └─────┘└───┘└─────┘
    "sx() q0 -> sdg() q0 | h() q0 | sdg() q0",
     //SXGate
     //              global phase: π/4
     //   ┌────┐        ┌─────────┐
     //q: ┤ √X ├  ≡  q: ┤ Rx(π/2) ├
     //   └────┘        └─────────┘
    "sx() q0 -> rx(pi/2) q0",
     //SXdgGate
     //                global phase: 7π/4
     //   ┌──────┐        ┌───┐┌───┐┌───┐
     //q: ┤ √Xdg ├  ≡  q: ┤ S ├┤ H ├┤ S ├
     //   └──────┘        └───┘└───┘└───┘
    "sxdg() q0 -> s() q0 | h() q0 | s() q0",
     //SXdgGate
     //                global phase: 7π/4
     //   ┌──────┐        ┌──────────┐
     //q: ┤ √Xdg ├  ≡  q: ┤ Rx(-π/2) ├
     //   └──────┘        └──────────┘
    "sxdg() q0 -> rx(-pi/2) q0",
     //CSXGate
     //
     //q_0: ──■───     q_0: ──────■─────────────
     //     ┌─┴──┐  ≡       ┌───┐ │U1(π/2) ┌───┐
     //q_1: ┤ Sx ├     q_1: ┤ H ├─■────────┤ H ├
     //     └────┘          └───┘          └───┘
    "csx() q0,q1 -> h() q1 | cu1(pi/2) q0,q1 | h() q1",
     //CSXGate
     //                global phase: π/8
     //                     ┌───┐┌───────────┐ ┌─────┐  ┌───┐
     //q_0: ──■───     q_0: ┤ X ├┤0          ├─┤ Tdg ├──┤ X ├
     //     ┌─┴──┐  ≡       └───┘│  Rzx(π/4) │┌┴─────┴─┐└───┘
     //q_1: ┤ Sx ├     q_1: ─────┤1          ├┤ sx^0.5 ├─────
     //     └────┘               └───────────┘└────────┘
    (
        "csx() q0,q1 -> "
        "x() q0 | "
        "rzx(pi/4) q0,q1 | "
        "tdg() q0 | "
        "x() q0 | "
        "rx(pi/4) q1"
    ),
     //DCXGate
     //
     //     ┌──────┐               ┌───┐
     //q_0: ┤0     ├     q_0: ──■──┤ X ├
     //     │  Dcx │  ≡       ┌─┴─┐└─┬─┘
     //q_1: ┤1     ├     q_1: ┤ X ├──■──
     //     └──────┘          └───┘
    "dcx() q0,q1 -> cx() q0,q1 | cx() q1,q0",
     //DCXGate
     //
     //     ┌──────┐           ┌───┐ ┌─────┐┌────────┐
     //q_0: ┤0     ├     q_0: ─┤ H ├─┤ Sdg ├┤0       ├─────
     //     │  Dcx │  ≡       ┌┴───┴┐└─────┘│  Iswap │┌───┐
     //q_1: ┤1     ├     q_1: ┤ Sdg ├───────┤1       ├┤ H ├
     //     └──────┘          └─────┘       └────────┘└───┘
    ("dcx() q0,q1 -> h() q0 | sdg() q0 | sdg() q1 | iswap() q0,q1 | h() q1"),
     //CSwapGate
     //
     //q_0: ─■─     q_0: ───────■───────
     //      │           ┌───┐  │  ┌───┐
     //q_1: ─X─  ≡  q_1: ┤ X ├──■──┤ X ├
     //      │           └─┬─┘┌─┴─┐└─┬─┘
     //q_2: ─X─     q_2: ──■──┤ X ├──■──
     //                       └───┘
    "cswap() q0,q1,q2 -> cx() q2,q1 | ccx() q0,q1,q2 | cx() q2,q1",
     //TGate
     //
     //   ┌───┐        ┌─────────┐
     //q: ┤ T ├  ≡  q: ┤ U1(π/4) ├
     //   └───┘        └─────────┘
    "t() q0 -> u1(pi/4) q0",
     //TdgGate
     //
     //   ┌─────┐        ┌──────────┐
     //q: ┤ Tdg ├  ≡  q: ┤ U1(-π/4) ├
     //   └─────┘        └──────────┘
    "tdg() q0 -> u1(-pi/4) q0",
     //UGate
     //
     //   ┌──────────┐        ┌───────────┐
     //q: ┤ U(θ,ϕ,λ) ├  ≡  q: ┤ U3(θ,ϕ,λ) ├
     //   └──────────┘        └───────────┘
    "u(theta,phi,lam) q0 -> u3(theta,phi,lam) q0",
     //CUGate
     //                                 ┌──────┐    ┌──────────────┐     »
     //q_0: ──────■───────     q_0: ────┤ P(γ) ├────┤ P(λ/2 + ϕ/2) ├──■──»
     //     ┌─────┴──────┐  ≡       ┌───┴──────┴───┐└──────────────┘┌─┴─┐»
     //q_1: ┤ U(θ,ϕ,λ,γ) ├     q_1: ┤ P(λ/2 - ϕ/2) ├────────────────┤ X ├»
     //     └────────────┘          └──────────────┘                └───┘»
     // 
     // q_0: ──────────────────────────■────────────────
     //      ┌──────────────────────┐┌─┴─┐┌────────────┐
     // q_1: ┤ U(-θ/2,ϕ,-λ/2 - ϕ/2) ├┤ X ├┤ U(θ/2,ϕ,0) ├
     //      └──────────────────────┘└───┘└────────────┘
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
     //CUGate
     //                             ┌──────┐
     //q_0: ──────■───────     q_0: ┤ P(γ) ├──────■──────
     //     ┌─────┴──────┐  ≡       └──────┘┌─────┴─────┐
     //q_1: ┤ U(θ,ϕ,λ,γ) ├     q_1: ────────┤ U3(θ,ϕ,λ) ├
     //     └────────────┘                  └───────────┘
    "cu(theta,phi,lam,gamma) q0,q1 -> p(gamma) q0 | cu3(theta,phi,lam) q0,q1",
     //U1Gate
     //
     //   ┌───────┐        ┌───────────┐
     //q: ┤ U1(θ) ├  ≡  q: ┤ U3(0,0,θ) ├
     //   └───────┘        └───────────┘
    "u1(theta) q0 -> u3(0,0,theta) q0",
     //U1Gate
     //
     //   ┌───────┐        ┌──────┐
     //q: ┤ U1(θ) ├  ≡  q: ┤ P(0) ├
     //   └───────┘        └──────┘
    "u1(theta) q0 -> p(theta) q0",
     //U1Gate
     //                 global phase: θ/2
     //   ┌───────┐        ┌───────┐
     //q: ┤ U1(θ) ├  ≡  q: ┤ Rz(θ) ├
     //   └───────┘        └───────┘
    "u1(theta) q0 -> rz(theta) q0",
     //CU1Gate
     //                      ┌─────────┐
     //q_0: ─■─────     q_0: ┤ U1(θ/2) ├──■────────────────■─────────────
     //      │U1(θ)  ≡       └─────────┘┌─┴─┐┌──────────┐┌─┴─┐┌─────────┐
     //q_1: ─■─────     q_1: ───────────┤ X ├┤ U1(-θ/2) ├┤ X ├┤ U1(θ/2) ├
     //                                 └───┘└──────────┘└───┘└─────────┘
    (
        "cu1(theta) q0,q1 -> "
        "u1(theta/2) q0 | "
        "cx() q0,q1 | "
        "u1(-theta/2) q1 | "
        "cx() q0,q1 | "
        "u1(theta/2) q1"
    ),
     //U2Gate
     //                   global phase: 7π/4
     //   ┌─────────┐        ┌─────────────┐┌────┐┌─────────────┐
     //q: ┤ U2(ϕ,λ) ├  ≡  q: ┤ U1(λ - π/2) ├┤ √X ├┤ U1(ϕ + π/2) ├
     //   └─────────┘        └─────────────┘└────┘└─────────────┘
    "u2(phi,lam) q0 -> u3(pi/2,phi,lam) q0",
     //U3Gate
     //                        global phase: λ/2 + ϕ/2 - π/2
     //   ┌───────────┐        ┌───────┐┌────┐┌───────────┐┌────┐┌────────────┐
     //q: ┤ U3(θ,ϕ,λ) ├  ≡  q: ┤ Rz(λ) ├┤ √X ├┤ Rz(θ + π) ├┤ √X ├┤ Rz(ϕ + 3π) ├
     //   └───────────┘        └───────┘└────┘└───────────┘└────┘└────────────┘
    (
        "u3(theta,phi,lam) q0 -> "
        "rz(lam) q0 | "
        "sx() q0 | "
        "rz(theta+pi) q0 | "
        "sx() q0 | "
        "rz(phi+3*pi) q0"
    ),
     //U3Gate
     //
     //   ┌───────────┐        ┌──────────┐
     //q: ┤ U3(θ,ϕ,λ) ├  ≡  q: ┤ U(θ,ϕ,λ) ├
     //   └───────────┘        └──────────┘
    "u3(theta,phi,lam) q0 -> u(theta,phi,lam) q0",
     //CU3Gate
     //                            ┌───────────────┐     »
     //q_0: ──────■──────     q_0: ┤ U1(λ/2 + ϕ/2) ├──■──»
     //     ┌─────┴─────┐  ≡       ├───────────────┤┌─┴─┐»
     //q_1: ┤ U3(θ,ϕ,λ) ├     q_1: ┤ U1(λ/2 - ϕ/2) ├┤ X ├»
     //     └───────────┘          └───────────────┘└───┘»
     // 
     // q_0: ──────────────────────────■─────────────────
     //     ┌───────────────────────┐┌─┴─┐┌─────────────┐
     // q_1:┤ U3(-θ/2,0,-λ/2 - ϕ/2) ├┤ X ├┤ U3(θ/2,ϕ,0) ├
     //     └───────────────────────┘└───┘└─────────────┘
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
     //XGate
     //
     //   ┌───┐        ┌───────────┐
     //q: ┤ X ├  ≡  q: ┤ U3(π,0,π) ├
     //   └───┘        └───────────┘
    "x() q0 -> u3(pi,0,pi) q0",
     //XGate
     //
     //   ┌───┐        ┌───┐┌───┐┌───┐┌───┐
     //q: ┤ X ├  ≡  q: ┤ H ├┤ S ├┤ S ├┤ H ├
     //   └───┘        └───┘└───┘└───┘└───┘
    "x() q0 -> h() q0 | s() q0 | s() q0 | h() q0",
     //CXGate
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
     //CXGate
     //
     //q_0: ──■──     q_0: ──────■──────
     //     ┌─┴─┐  ≡       ┌───┐ │ ┌───┐
     //q_1: ┤ X ├     q_1: ┤ H ├─■─┤ H ├
     //     └───┘          └───┘   └───┘
    "cx() q0,q1 -> h() q1 | cz() q0,q1 | h() q1",
     //CXGate
     //               global phase: 3π/4
     //                    ┌───┐     ┌────────┐┌───┐     ┌────────┐»
     //q_0: ──■──     q_0: ┤ H ├─────┤0       ├┤ X ├─────┤0       ├»
     //     ┌─┴─┐  ≡       ├───┤┌───┐│  Iswap │├───┤┌───┐│  Iswap │»
     //q_1: ┤ X ├     q_1: ┤ X ├┤ H ├┤1       ├┤ X ├┤ H ├┤1       ├»
     //     └───┘          └───┘└───┘└────────┘└───┘└───┘└────────┘»
     //      ┌───┐┌───┐
     // q_0: ┤ H ├┤ S ├─────
     //      ├───┤├───┤┌───┐
     // q_1: ┤ S ├┤ X ├┤ H ├
     //      └───┘└───┘└───┘
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
     //CXGate
     //               global phase: 7π/4
     //                    ┌──────────┐┌───────┐┌──────┐
     //q_0: ──■──     q_0: ┤ Rz(-π/2) ├┤ Ry(π) ├┤0     ├
     //     ┌─┴─┐  ≡       ├─────────┬┘└───────┘│  Ecr │
     //q_1: ┤ X ├     q_1: ┤ Rx(π/2) ├──────────┤1     ├
     //     └───┘          └─────────┘          └──────┘
    "cx() q0,q1 -> rz(-pi/2) q0 | ry(pi) q0 | rx(pi/2) q1 | ecr() q0,q1",
     //CXGate
     //q_0: ──■──     q_0: ───────────────■───────────────────
     //     ┌─┴─┐  ≡       ┌────────────┐ │P(π) ┌────────────┐
     //q_1: ┤ X ├     q_1: ┤ U(π/2,0,π) ├─■─────┤ U(π/2,0,π) ├
     //     └───┘          └────────────┘       └────────────┘
    "cx() q0,q1 -> u(pi/2,0,pi) q1 | cp(pi) q0,q1 | u(pi/2,0,pi) q1",
     //CXGate
     //                    ┌────────────┐
     //q_0: ──■──     q_0: ┤ U(0,0,π/2) ├────■──────────────────
     //     ┌─┴─┐  ≡       ├────────────┤┌───┴───┐┌────────────┐
     //q_1: ┤ X ├     q_1: ┤ U(π/2,0,π) ├┤ Rz(π) ├┤ U(π/2,0,π) ├
     //     └───┘          └────────────┘└───────┘└────────────┘
    (
        "cx() q0,q1 -> "
        "u(pi/2,0,pi) q1 | "
        "u(0,0,pi/2) q0 | "
        "crz(pi) q0,q1 | "
        "u(pi/2,0,pi) q1"
    ),
     //CXGate
     //               global phase: π/4
     //                    ┌───────────┐┌─────┐
     //q_0: ──■──     q_0: ┤0          ├┤ Sdg ├─
     //     ┌─┴─┐  ≡       │  Rzx(π/2) │├─────┴┐
     //q_1: ┤ X ├     q_1: ┤1          ├┤ √Xdg ├
     //     └───┘          └───────────┘└──────┘
    "cx() q0,q1 -> rzx(pi/2) q0,q1 | sdg() q0 | sxdg() q1",
     //CCXGate
     //
     //q_0: ──■──     q_0: ───────────────────■────────────
     //       │                               │
     //q_1: ──■──  ≡  q_1: ───────■───────────┼─────────■──
     //     ┌─┴─┐          ┌───┐┌─┴─┐┌─────┐┌─┴─┐┌───┐┌─┴─┐
     //q_2: ┤ X ├     q_2: ┤ H ├┤ X ├┤ Tdg ├┤ X ├┤ T ├┤ X ├
     //     └───┘          └───┘└───┘└─────┘└───┘└───┘└───┘
     //                        ┌───┐
     // q_0: ─────────■────■───┤ T ├───■──
     //       ┌───┐   │  ┌─┴─┐┌┴───┴┐┌─┴─┐
     // q_1: ─┤ T ├───┼──┤ X ├┤ Tdg ├┤ X ├
     //      ┌┴───┴┐┌─┴─┐├───┤└┬───┬┘└───┘
     // q_2  ┤ Tdg ├┤ X ├┤ T ├─┤ H ├──────
     //      └─────┘└───┘└───┘ └───┘
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
     //CCXGate
     //
     //q_0: ──■──     q_0: ────────■─────────────────■────■───
     //       │                  ┌─┴─┐┌─────┐      ┌─┴─┐  │
     //q_1: ──■──  ≡  q_1: ──■───┤ X ├┤ Sdg ├──■───┤ X ├──┼───
     //     ┌─┴─┐          ┌─┴──┐├───┤└─────┘┌─┴──┐├───┤┌─┴──┐
     //q_2: ┤ X ├     q_2: ┤ Sx ├┤ Z ├───────┤ Sx ├┤ Z ├┤ Sx ├
     //     └───┘          └────┘└───┘       └────┘└───┘└────┘
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
     //YGate
     //             global phase: 3π/2
     //   ┌───┐        ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐
     //q: ┤ Y ├  ≡  q: ┤ H ├┤ S ├┤ S ├┤ H ├┤ S ├┤ S ├
     //   └───┘        └───┘└───┘└───┘└───┘└───┘└───┘
    "y() q0 -> u3(pi,pi/2,pi/2) q0",
     //YGate
     //             global phase: π/2
     //   ┌───┐        ┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐
     //q: ┤ Y ├  ≡  q: ┤ S ├┤ S ├┤ H ├┤ S ├┤ S ├┤ H ├
     //   └───┘        └───┘└───┘└───┘└───┘└───┘└───┘
    "y() q0 -> s() q0 | s() q0 | h() q0 | s() q0 | s() q0 | h() q0",
     //CYGate
     //
     //q_0: ──■──     q_0: ─────────■───────
     //     ┌─┴─┐  ≡       ┌─────┐┌─┴─┐┌───┐
     //q_1: ┤ Y ├     q_1: ┤ Sdg ├┤ X ├┤ S ├
     //     └───┘          └─────┘└───┘└───┘
    "cy() q0,q1 -> sdg() q1 | cx() q0,q1 | s() q1",
     //ZGate
     //
     //   ┌───┐        ┌───────┐
     //q: ┤ Z ├  ≡  q: ┤ U1(π) ├
     //   └───┘        └───────┘
    "z() q0 -> u1(pi) q0",
     //ZGate
     //
     //   ┌───┐        ┌───┐┌───┐
     //q: ┤ Z ├  ≡  q: ┤ S ├┤ S ├
     //   └───┘        └───┘└───┘
    "z() q0 -> s() q0 | s() q0",
     //CZGate
     //
     //q_0: ─■─     q_0: ───────■───────
     //      │   ≡       ┌───┐┌─┴─┐┌───┐
     //q_1: ─■─     q_1: ┤ H ├┤ X ├┤ H ├
     //                  └───┘└───┘└───┘
    "cz() q0,q1 -> h() q1 | cx() q0,q1 | h() q1",
     //CCZGate
     //
     //q_0: ─■─   q_0: ───────■───────
     //      │                │
     //q_1: ─■─ = q_1: ───────■───────
     //      │         ┌───┐┌─┴─┐┌───┐
     //q_2: ─■─   q_2: ┤ H ├┤ X ├┤ H ├
     //                └───┘└───┘└───┘
    "ccz() q0,q1,q2 -> h() q2 | ccx() q0,q1,q2 | h() q2",
     //XGate
     //             global phase: π/2
     //   ┌───┐        ┌───────┐
     //q: ┤ X ├  ≡  q: ┤ Rx(π) ├
     //   └───┘        └───────┘
    "x() q0 -> rx(pi) q0",
     //YGate
     //             global phase: π/2
     //   ┌───┐        ┌───────┐
     //q: ┤ Y ├  ≡  q: ┤ Ry(π) ├
     //   └───┘        └───────┘
    "y() q0 -> ry(pi) q0",
     //HGate
     //             global phase: π/2
     //   ┌───┐        ┌─────────┐┌───────┐
     //q: ┤ H ├  ≡  q: ┤ Ry(π/2) ├┤ Rx(π) ├
     //   └───┘        └─────────┘└───────┘
    "h() q0 -> ry(pi/2) q0 | rx(pi) q0",
     //HGate
     //             global phase: π/2
     //   ┌───┐        ┌────────────┐┌────────┐
     //q: ┤ H ├  ≡  q: ┤ R(π/2,π/2) ├┤ R(π,0) ├
     //   └───┘        └────────────┘└────────┘
    "h() q0 -> r(pi/2, pi/2) q0 | r(pi, 0) q0",
     //below are some added rules
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
};

/* ============================================================
 * ParamGate
 * ============================================================ */

/**
 * @brief Compare two parameterized gates.
 *
 * Two ParamGate objects are considered equal if:
 * - gate names are identical
 * - qubit lists are identical
 * - parameter lists are identical
 *
 * @param other Another ParamGate object
 * @return true if fully identical
 * @return false otherwise
 */
bool ParamGate::operator==(const ParamGate& other) const {
    return name == other.name &&
           qubits == other.qubits &&
           params == other.params;
}

/**
 * @brief Compute hash value for ParamGate.
 *
 * Combines:
 * - gate name hash
 * - qubit hashes
 * - parameter hashes
 *
 * Enables ParamGate to be used in:
 * - std::unordered_map
 * - std::unordered_set
 *
 * @param g Input gate
 * @return Combined hash value
 */
size_t ParamGateHash::operator()(const ParamGate& g) const {

    std::hash<std::string> h;

    size_t res = h(g.name);

    for (auto& q : g.qubits) {
        res ^= h(q);
    }

    for (auto& p : g.params) {
        res ^= h(p);
    }

    return res;
}

/* ============================================================
 * EquivalenceRule
 * ============================================================ */

/**
 * @brief Construct equivalence rule from DSL string.
 *
 * Example:
 *   "cx(a,b)->h(b)|cz(a,b)|h(b)"
 *
 * The DSL is parsed into:
 * - target gate
 * - equivalent source gate sequence
 *
 * @param dsl DSL formatted equivalence rule
 */
EquivalenceRule::EquivalenceRule(const string& dsl) {

    auto parsed = parse_dsl(dsl);

    target = parsed.first;
    sources = parsed.second;
}

/**
 * @brief Parse an equivalence DSL rule.
 *
 * DSL format:
 *   target -> source1 | source2 | ...
 *
 * Example:
 *   cx(a,b)->h(b)|cz(a,b)|h(b)
 *
 * @param dsl Input DSL string
 * @return Parsed target gate and source sequence
 */
pair<ParamGate, vector<ParamGate>>
EquivalenceRule::parse_dsl(const string& dsl) {

    auto pos = dsl.find("->");

    string lhs = dsl.substr(0, pos);
    string rhs = dsl.substr(pos + 2);

    // Parse target gate
    ParamGate target = parse_gate_block(lhs);

    // Parse source gates
    vector<ParamGate> sources;

    stringstream ss(rhs);
    string token;

    while (getline(ss, token, '|')) {

        if (!token.empty()) {
            sources.push_back(
                parse_gate_block(token));
        }
    }

    return {target, sources};
}

/**
 * @brief Remove leading and trailing whitespace.
 *
 * Supported whitespace:
 * - space
 * - tab
 * - newline
 * - carriage return
 *
 * @param s Input string
 * @return Trimmed string
 */
static inline string trim(const string& s) {

    size_t start =
        s.find_first_not_of(" \t\n\r");

    if (start == string::npos) {
        return "";
    }

    size_t end =
        s.find_last_not_of(" \t\n\r");

    return s.substr(start, end - start + 1);
}

/**
 * @brief Parse a single gate block.
 *
 * Example:
 *   rx(theta)q0
 *
 * Parsed into:
 * - name   = "rx"
 * - params = {"theta"}
 * - qubits = {"q0"}
 *
 * Supports nested parameter expressions:
 *   u3(theta/2, sin(x), pi)
 *
 * @param block_raw Raw gate block string
 * @return Parsed ParamGate object
 *
 * @throws std::runtime_error
 * Thrown if:
 * - parsing fails
 * - parentheses mismatch
 */
ParamGate EquivalenceRule::parse_gate_block(
    const string& block_raw) {

    string block = trim(block_raw);

    auto i = block.find("(");

    if (i == string::npos) {
        throw runtime_error("parse error");
    }

    // ------------------------------------------------
    // Find matching closing parenthesis
    // ------------------------------------------------

    int depth = 0;
    size_t j = string::npos;

    for (size_t k = i; k < block.size(); ++k) {

        if (block[k] == '(') {

            depth++;

        } else if (block[k] == ')') {

            depth--;

            if (depth == 0) {
                j = k;
                break;
            }
        }
    }

    if (j == string::npos) {
        throw runtime_error(
            "unmatched parentheses");
    }

    string name =
        trim(block.substr(0, i));

    string params_str =
        block.substr(i + 1, j - i - 1);

    string qubits_str =
        block.substr(j + 1);

    vector<string> params;
    vector<string> qubits;

    string tmp;

    // ------------------------------------------------
    // Split parameters by commas
    //
    // Ignore commas inside nested parentheses.
    // ------------------------------------------------

    vector<string> param_tokens;

    depth = 0;
    string current;

    for (char c : params_str) {

        if (c == '(') {

            depth++;

        } else if (c == ')') {

            depth--;
        }

        if (c == ',' && depth == 0) {

            param_tokens.push_back(
                trim(current));

            current.clear();

        } else {

            current += c;
        }
    }

    if (!current.empty()) {
        param_tokens.push_back(
            trim(current));
    }

    // Remove empty parameters
    for (auto& p : param_tokens) {

        if (!p.empty()) {
            params.push_back(p);
        }
    }

    // ------------------------------------------------
    // Parse qubit list
    // ------------------------------------------------

    stringstream qs(qubits_str);

    while (getline(qs, tmp, ',')) {

        tmp = trim(tmp);

        if (!tmp.empty()) {
            qubits.push_back(tmp);
        }
    }

    return {name, qubits, params};
}

/* ============================================================
 * EquivalenceGraph
 * ============================================================ */

/**
 * @brief Construct equivalence graph.
 *
 * Loads all equivalence rules from the global
 * equivalence library and builds:
 * - forward decomposition index
 * - reverse dependency index
 */
EquivalenceGraph::EquivalenceGraph() {

    extern vector<string> EquivalenceLibary;

    // Load all rules from DSL library
    for (auto& dsl : EquivalenceLibary) {
        rules.emplace_back(dsl);
    }

    // Build graph indices
    for (auto& r : rules) {

        forward_index[r.target.name]
            .push_back(&r);

        for (auto& s : r.sources) {
            reverse_index[s.name]
                .push_back(&r);
        }
    }
}

/**
 * @brief Compute decomposition rule cost.
 *
 * Current cost model:
 *   cost = number of source gates
 *
 * Can later be extended to support:
 * - weighted two-qubit gate cost
 * - hardware-aware metrics
 * - depth-aware optimization
 *
 * @param rule Input equivalence rule
 * @return Rule cost
 */
double EquivalenceGraph::rule_cost(
    const EquivalenceRule& rule) {

    return (double)rule.sources.size();
}

/* ============================================================
 * Dijkstra-based Optimal Decomposition Search
 * ============================================================ */

/**
 * @brief Compute optimal decomposition rules.
 *
 * Uses reverse Dijkstra traversal starting from
 * target gates.
 *
 * The algorithm searches for the minimum-cost
 * decomposition path for each source gate.
 *
 * @param source Source gate set
 * @param target Target gate set
 *
 * @return Mapping:
 *   gate name -> optimal equivalence rule
 */
unordered_map<string, EquivalenceRule>
EquivalenceGraph::get_optimal_decomposition_rule_dictionary(
    const vector<string>& source,
    const vector<string>& target
) {

    unordered_set<string> visited;

    // Source gates still requiring decomposition
    unordered_set<string> left_source_gates;

    for (auto& s : source) {

        if (find(
                target.begin(),
                target.end(),
                s) == target.end()) {

            left_source_gates.insert(s);
        }
    }

    // Best known decomposition cost
    unordered_map<string, double> cost_map;

    // Best decomposition rule
    unordered_map<string, EquivalenceRule>
        optimal_rules;

    using Node =
        tuple<double, int, string>;

    priority_queue<
        Node,
        vector<Node>,
        greater<>
    > pq;

    int counter = 0;

    // ------------------------------------------------
    // Initialize target gates with zero cost
    // ------------------------------------------------

    for (auto& g : target) {

        pq.emplace(0.0, counter++, g);

        visited.insert(g);

        cost_map[g] = 0.0;
    }

    // ------------------------------------------------
    // Reverse Dijkstra traversal
    // ------------------------------------------------

    while (!pq.empty()) {

        auto [cost, _, gate] = pq.top();

        pq.pop();

        left_source_gates.erase(gate);

        // All source gates resolved
        if (left_source_gates.empty()) {
            return optimal_rules;
        }

        // Skip outdated queue entries
        if (cost_map.find(gate)
                != cost_map.end() &&
            cost_map[gate] < cost) {

            continue;
        }

        // No reverse dependency
        if (reverse_index.find(gate)
                == reverse_index.end()) {

            continue;
        }

        // Explore reverse rules
        for (auto* rule : reverse_index[gate]) {

            bool ok = true;

            double new_cost =
                rule_cost(*rule);

            // All source gates must already
            // have valid decomposition paths
            for (auto& s : rule->sources) {

                if (!visited.count(s.name)) {

                    ok = false;
                    break;
                }

                new_cost += cost_map[s.name];
            }

            if (!ok) {
                continue;
            }

            // Relaxation step
            if (cost_map.find(rule->target.name)
                    == cost_map.end() ||
                cost_map[rule->target.name]
                    > new_cost) {

                cost_map[rule->target.name] =
                    new_cost;

                optimal_rules[rule->target.name] =
                    *rule;

                pq.emplace(
                    new_cost,
                    counter++,
                    rule->target.name);

                visited.insert(
                    rule->target.name);
            }
        }
    }

    return optimal_rules;
}

/* ============================================================
 * Parameter Substitution
 * ============================================================ */

/**
 * @brief Escape regex special characters.
 *
 * Used when constructing regex replacement
 * patterns for symbolic parameter substitution.
 *
 * @param s Input string
 * @return Regex-safe escaped string
 */
static string regex_escape(const string& s) {

    static const regex re(
        R"([.^$|()\\[*+?{\]])");

    return regex_replace(
        s,
        re,
        R"(\$&)");
}

/**
 * @brief Rewrite symbolic parameter expressions.
 *
 * Example:
 *   theta -> pi / 2
 *
 * Parameters are substituted using regex-based
 * symbolic replacement.
 *
 * Keys are sorted by descending length to avoid
 * substring replacement conflicts.
 *
 * Example:
 *   t1 should be replaced before t
 *
 * @param exprs Original expressions
 * @param param_map Parameter substitution map
 *
 * @return Rewritten parameter expressions
 */
vector<string> EquivalenceGraph::rewrite_params(
    const vector<string>& exprs,
    const unordered_map<string, string>& param_map
) {

    vector<string> result;

    // ------------------------------------------------
    // Sort parameters by descending key length
    // ------------------------------------------------

    vector<pair<string, string>> ordered(
        param_map.begin(),
        param_map.end());

    sort(
        ordered.begin(),
        ordered.end(),
        [](const auto& a, const auto& b) {
            return a.first.size() >
                   b.first.size();
        });

    // ------------------------------------------------
    // Rewrite each expression
    // ------------------------------------------------

    for (const auto& expr : exprs) {

        string new_expr = expr;

        for (const auto& [k, v] : ordered) {

            string pattern =
                "\\b" +
                regex_escape(k) +
                "\\b";

            regex r(pattern);

            new_expr = regex_replace(
                new_expr,
                r,
                "(" + v + ")");
        }

        result.push_back(new_expr);
    }

    return result;
}

/* ============================================================
 * Recursive Gate Expansion
 * ============================================================ */

/**
 * @brief Recursively expand a gate decomposition.
 *
 * Expands a gate into target gates using:
 * - decomposition rules
 * - recursive traversal
 * - memoization cache
 *
 * Features:
 * - parameter substitution
 * - qubit remapping
 * - cycle detection
 *
 * @param gate Gate to expand
 * @param rule_map Optimal decomposition rules
 * @param target_set Allowed primitive gates
 * @param cache Expansion cache
 * @param path Current recursion path
 *
 * @return Fully expanded gate sequence
 *
 * @throws std::runtime_error
 * Thrown if:
 * - decomposition cycle detected
 * - decomposition rule missing
 * - parameter mismatch occurs
 * - qubit mapping fails
 */
vector<ParamGate>
EquivalenceGraph::expand_gate_recursive(
    const ParamGate& gate,
    const unordered_map<string, EquivalenceRule>& rule_map,
    const unordered_set<string>& target_set,
    unordered_map<
        ParamGate,
        vector<ParamGate>,
        ParamGateHash>& cache,
    unordered_set<
        ParamGate,
        ParamGateHash>& path
) {

    // ------------------------------------------------
    // Already primitive target gate
    // ------------------------------------------------

    if (target_set.count(gate.name)) {
        return {gate};
    }

    // ------------------------------------------------
    // Cache lookup
    // ------------------------------------------------

    auto cache_it = cache.find(gate);

    if (cache_it != cache.end()) {
        return cache_it->second;
    }

    // ------------------------------------------------
    // Cycle detection
    // ------------------------------------------------

    if (path.count(gate)) {

        throw runtime_error(
            "cycle detected at gate " +
            gate.name);
    }

    // ------------------------------------------------
    // Find decomposition rule
    // ------------------------------------------------

    auto it = rule_map.find(gate.name);

    if (it == rule_map.end()) {

        throw runtime_error(
            "no rule for gate " +
            gate.name);
    }

    const auto& rule = it->second;

    const ParamGate& template_gate =
        rule.target;

    // ------------------------------------------------
    // Build parameter mapping
    // ------------------------------------------------

    unordered_map<string, string> param_map;

    if (!template_gate.params.empty()) {

        if (gate.params.empty() ||
            gate.params.size() !=
                template_gate.params.size()) {

            throw runtime_error(
                "parameter mismatch for gate " +
                gate.name);
        }

        for (size_t i = 0;
             i < template_gate.params.size();
             ++i) {

            param_map[
                template_gate.params[i]] =
                gate.params[i];
        }
    }

    // ------------------------------------------------
    // Enter recursion
    // ------------------------------------------------

    path.insert(gate);

    vector<ParamGate> result;

    // ------------------------------------------------
    // Build qubit mapping
    // symbolic qubit -> physical qubit
    // ------------------------------------------------

    unordered_map<string, string> qubit_map;

    for (size_t i = 0;
         i < template_gate.qubits.size();
         ++i) {

        qubit_map[
            template_gate.qubits[i]] =
            gate.qubits[i];
    }

    // ------------------------------------------------
    // Expand source gates
    // ------------------------------------------------

    for (const auto& s : rule.sources) {

        // ---- Qubit remapping ----

        vector<string> mapped_qubits;

        mapped_qubits.reserve(
            s.qubits.size());

        for (const auto& q : s.qubits) {

            auto qit = qubit_map.find(q);

            if (qit == qubit_map.end()) {

                throw runtime_error(
                    "qubit mapping missing: " + q);
            }

            mapped_qubits.push_back(
                qit->second);
        }

        // ---- Rewrite parameters ----

        vector<string> rewritten_params =
            rewrite_params(
                s.params,
                param_map);

        // ---- Construct substituted gate ----

        ParamGate g2{
            s.name,
            mapped_qubits,
            rewritten_params
        };

        // ---- Recursive expansion ----

        auto sub = expand_gate_recursive(
            g2,
            rule_map,
            target_set,
            cache,
            path);

        result.insert(
            result.end(),
            sub.begin(),
            sub.end());
    }

    // ------------------------------------------------
    // Exit recursion
    // ------------------------------------------------

    path.erase(gate);

    // Cache result
    cache.emplace(gate, result);

    return result;
}

/* ============================================================
 * Build Full Decomposition Table
 * ============================================================ */

/**
 * @brief Build fully expanded decomposition table.
 *
 * Produces:
 * - complete decomposition lookup table
 * - decomposition complexity statistics
 *
 * Features:
 * - recursive gate expansion
 * - decomposition caching
 * - automatic excluded gate handling
 *
 * @param source Source gate set
 * @param target Target primitive gate set
 *
 * @return Pair containing:
 * - decomposition table
 * - gate count statistics
 */
pair<
    unordered_map<
        ParamGate,
        vector<ParamGate>,
        ParamGateHash>,
    unordered_map<string, int>
>
EquivalenceGraph::build_full_decomposition_table(
    const vector<string>& source,
    const vector<string>& target
) {

    // ------------------------------------------------
    // Extend source gate set
    // ------------------------------------------------

    vector<string> extended_source = source;

    extended_source.push_back("swap");

    // ------------------------------------------------
    // Extend target gate set
    // ------------------------------------------------

    vector<string> new_target = target;

    unordered_set<string> excluded_gates = {
        "measure",
        "reset",
        "sync",
        "move"
    };

    for (auto& g : excluded_gates) {

        if (find(
                new_target.begin(),
                new_target.end(),
                g) == new_target.end()) {

            new_target.push_back(g);
        }
    }

    // ------------------------------------------------
    // Compute optimal decomposition rules
    // ------------------------------------------------

    auto rule_map =
        get_optimal_decomposition_rule_dictionary(
            extended_source,
            new_target);

    unordered_set<string> target_set(
        new_target.begin(),
        new_target.end());

    // ------------------------------------------------
    // Build decomposition table
    // ------------------------------------------------

    unordered_map<
        ParamGate,
        vector<ParamGate>,
        ParamGateHash> table;

    unordered_map<string, int> count_map;

    unordered_map<
        ParamGate,
        vector<ParamGate>,
        ParamGateHash> cache;

    unordered_set<
        ParamGate,
        ParamGateHash> path;

    for (auto& name : extended_source) {

        // Already primitive target gate
        if (target_set.count(name)) {

            count_map[name] = 1;

            continue;
        }

        auto it = rule_map.find(name);

        if (it == rule_map.end()) {
            throw runtime_error("no rule");
        }

        ParamGate template_gate =
            it->second.target;

        // Skip duplicate entries
        if (table.count(template_gate)) {
            continue;
        }

        // Recursively expand decomposition
        auto expanded =
            expand_gate_recursive(
                template_gate,
                rule_map,
                target_set,
                cache,
                path);

        table[template_gate] = expanded;

        // Simple complexity metric
        count_map[template_gate.name] =
            expanded.size() + 1;
    }

    return {table, count_map};
}
}