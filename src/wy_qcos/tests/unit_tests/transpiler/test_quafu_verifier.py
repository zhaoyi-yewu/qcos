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

import unittest

from wy_qcos.transpiler.high_performance import QuafuVerifier, VerifyParams


def _make_params(
    bits=8,
    basis_gates=None,
    coupling_list=None,
    edge_fidelities=None,
    single_qubit_fidelities=None,
    target_bits=None,
):
    """构造测试用 VerifyParams."""
    params = VerifyParams()
    params.bits = bits
    params.basis_gates = basis_gates or ["h", "rx", "ry", "rz", "cz"]
    params.coupling_list = coupling_list or [(0, 1), (1, 0), (1, 2), (2, 1)]
    params.edge_fidelities = edge_fidelities or [0.99, 0.99, 0.98, 0.98]
    params.single_qubit_fidelities = single_qubit_fidelities or [
        0.999,
        0.999,
        0.999,
        0.999,
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    params.target_bits = target_bits or []
    return params


def _make_verifier(**kwargs):
    return QuafuVerifier(_make_params(**kwargs))


class TestCheckQasmSyntax(unittest.TestCase):
    """QASM 语法校验测试."""

    def setUp(self):
        self.verifier = _make_verifier()

    def test_valid_qasm2(self):
        # 合法 QASM 2.0 → True
        qasm = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[2];\n"
            "creg c[2];\n"
            "h q[0];\n"
            "cz q[0],q[1];\n"
            "measure q[0] -> c[0];\n"
        )
        self.assertTrue(self.verifier.verify(qasm).passed)

    def test_qasm3_returns_false(self):
        # QASM 3.0 头部 → False
        self.assertFalse(
            self.verifier.verify("OPENQASM 3.0;\nqubit[2] q;\n").passed
        )

    def test_no_header_returns_false(self):
        # 缺少 OPENQASM 声明 → False
        self.assertFalse(self.verifier.verify("qreg q[2];\nh q[0];\n").passed)

    def test_invalid_gate_returns_false(self):
        # 含未知门名 → False
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nfoobar q[0];\n'
        )
        self.assertFalse(self.verifier.verify(qasm).passed)

    def test_comment_before_header(self):
        # 注释在 OPENQASM 前 → True
        qasm = (
            "// this is a comment\n"
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[2];\n"
            "h q[0];\n"
        )
        self.assertTrue(self.verifier.verify(qasm).passed)


class TestCheckTopology(unittest.TestCase):
    """拓扑结构校验测试."""

    def test_all_single_qubit_fits(self):
        # 全单比特门，比特数在范围内 → True
        verifier = _make_verifier(bits=8)
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[4];\nh q[0];\nrx(1.570796) q[1];\n"
        )
        self.assertTrue(verifier.verify(qasm).passed)

    def test_all_single_qubit_exceeds_bits(self):
        # 实际操作使用 10 个不同比特，超过 bits=8 → False
        verifier = _make_verifier(bits=8)
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[10];\n' + "".join(
            f"h q[{i}];\n" for i in range(10)
        )
        self.assertFalse(verifier.verify(qasm).passed)

    def test_two_qubit_gate_fits_largest_component(self):
        # 含双比特门，比特数在最大连通分量内 → True
        verifier = _make_verifier(
            bits=8,
            coupling_list=[(0, 1), (1, 0), (1, 2), (2, 1), (5, 6), (6, 5)],
            edge_fidelities=[0.99, 0.99, 0.98, 0.98, 0.97, 0.97],
            single_qubit_fidelities=[
                0.999,
                0.999,
                0.999,
                0.0,
                0.0,
                0.999,
                0.999,
                0.0,
            ],
        )
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[3];\nh q[0];\ncz q[0],q[1];\n"
        )
        self.assertTrue(verifier.verify(qasm).passed)

    def test_two_qubit_gate_exceeds_largest_component(self):
        # 含双比特门，比特数超最大连通分量 → False
        verifier = _make_verifier(
            bits=8,
            coupling_list=[(0, 1), (1, 0), (1, 2), (2, 1), (5, 6), (6, 5)],
            edge_fidelities=[0.99, 0.99, 0.98, 0.98, 0.97, 0.97],
            single_qubit_fidelities=[
                0.999,
                0.999,
                0.999,
                0.0,
                0.0,
                0.999,
                0.999,
                0.0,
            ],
        )
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[5];\n"
            + "".join(f"h q[{i}];\n" for i in range(5))
            + "cz q[0],q[1];\n"
        )
        self.assertFalse(verifier.verify(qasm).passed)

    def test_target_bits_same_component(self):
        # target_bits 均在同一连通分量 → True
        verifier = _make_verifier(
            bits=8,
            coupling_list=[(0, 1), (1, 0), (1, 2), (2, 1), (5, 6), (6, 5)],
            edge_fidelities=[0.99, 0.99, 0.98, 0.98, 0.97, 0.97],
            single_qubit_fidelities=[
                0.999,
                0.999,
                0.999,
                0.0,
                0.0,
                0.999,
                0.999,
                0.0,
            ],
            target_bits=[0, 1, 2],
        )
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\n'
            "h q[2];\ncz q[0],q[1];\n"
        )
        self.assertTrue(verifier.verify(qasm).passed)

    def test_target_bits_different_components(self):
        # target_bits 跨两个连通分量 → False
        verifier = _make_verifier(
            bits=8,
            coupling_list=[(0, 1), (1, 0), (1, 2), (2, 1), (5, 6), (6, 5)],
            edge_fidelities=[0.99, 0.99, 0.98, 0.98, 0.97, 0.97],
            single_qubit_fidelities=[
                0.999,
                0.999,
                0.999,
                0.0,
                0.0,
                0.999,
                0.999,
                0.0,
            ],
            target_bits=[0, 5],
        )
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncz q[0],q[1];\n'
        )
        self.assertFalse(verifier.verify(qasm).passed)

    def test_target_bits_out_of_range_single_qubit(self):
        # target_bits 越界 + 全单比特门 → False
        verifier = _make_verifier(
            bits=8,
            coupling_list=[(0, 1), (1, 0)],
            edge_fidelities=[0.99, 0.99],
            single_qubit_fidelities=[
                0.999,
                0.999,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            target_bits=[0, 10],
        )
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\n'
        self.assertFalse(verifier.verify(qasm).passed)

    def test_target_bits_out_of_range_two_qubit(self):
        # target_bits 越界 + 含双比特门 → False
        verifier = _make_verifier(
            bits=8,
            coupling_list=[(0, 1), (1, 0)],
            edge_fidelities=[0.99, 0.99],
            single_qubit_fidelities=[
                0.999,
                0.999,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ],
            target_bits=[0, 10],
        )
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncz q[0],q[1];\n'
        )
        self.assertFalse(verifier.verify(qasm).passed)


class TestCheckDepthAndGateCount(unittest.TestCase):
    """门数量校验测试."""

    def setUp(self):
        self.verifier = _make_verifier()

    def test_200_cx_passes(self):
        # 200 个 cx 门（刚好在限制内）→ True
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
            + "cx q[0],q[1];\n" * 200
        )
        self.assertTrue(self.verifier.verify(qasm).passed)

    def test_201_cx_fails(self):
        # 201 个 cx 门（超出限制）→ False
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
            + "cx q[0],q[1];\n" * 201
        )
        self.assertFalse(self.verifier.verify(qasm).passed)

    def test_ccx_decompose_over_limit(self):
        # 40 个 ccx：多比特门数 40 <= 200，分解后约 240 个 cx > 200 → False
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\n'
            + "ccx q[0],q[1],q[2];\n" * 40
        )
        self.assertFalse(self.verifier.verify(qasm).passed)

    def test_depth_200_passes(self):
        # 200 个 h 门串行在同一比特上，深度 = 200 → True
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
            + "h q[0];\n" * 200
        )
        self.assertTrue(self.verifier.verify(qasm).passed)

    def test_depth_201_fails(self):
        # 201 个 h 门串行在同一比特上，深度 = 201 → False
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
            + "h q[0];\n" * 201
        )
        self.assertFalse(self.verifier.verify(qasm).passed)

    def test_depth_parallel_gates_passes(self):
        # 201 个 h 门分别在不同比特上（并行），深度 = 1 → True
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            f"qreg q[{201}];\n" + "".join(f"h q[{i}];\n" for i in range(201))
        )
        verifier = _make_verifier(bits=256)
        self.assertTrue(verifier.verify(qasm).passed)


if __name__ == "__main__":
    unittest.main()
