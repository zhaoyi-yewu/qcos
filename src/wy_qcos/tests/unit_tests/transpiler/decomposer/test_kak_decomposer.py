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

import numpy as np
import pytest

from wy_qcos.transpiler.cmss.common.gate_operation import (
    CZ,
    CX,
    CY,
    SWAP,
    CH,
    CRX,
    CRY,
    CRZ,
    CU1,
    CP,
    CU3,
    CSX,
    CU,
    RXX,
    RZZ,
)
from wy_qcos.transpiler.cmss.decomposer.kak_decomposer import KAKDecomposer

kak_decomposer = KAKDecomposer()
test_matrix = np.array(
    [
        [1, 0, 0, 0],
        [0, (1 + 1j) / 2, (1 - 1j) / 2, 0],
        [0, (1 - 1j) / 2, (1 + 1j) / 2, 0],
        [0, 0, 0, 1],
    ],
    dtype=complex,
)
glob_phase_matrix = np.array(
    [
        [0.9239 - 0.3827j, 0 + 0j, 0 + 0j, 0 + 0j],
        [0 + 0j, 0.6533 + 0.2706j, 0.2706 - 0.6533j, 0 + 0j],
        [0 + 0j, 0.2706 - 0.6533j, 0.6533 + 0.2706j, 0 + 0j],
        [0 + 0j, 0 + 0j, 0 + 0j, 0.9239 - 0.3827j],
    ],
    dtype=complex,
)
euler_matrix = np.array(
    [
        [0 + 0j, 1 + 0j, 0 + 0j, 0 + 0j],
        [0 - 1j, 0 + 0j, 0 + 0j, 0 + 0j],
        [0 + 0j, 0 + 0j, 0 + 0j, 0 - 1j],
        [0 + 0j, 0 + 0j, -1 + 0j, 0 + 0j],
    ],
    dtype=complex,
)

result_a1 = np.array(
    [
        [0.7071 + 0.7071j, 0 + 0j],
        [0 + 0j, 0.7071 - 0.7071j],
    ],
    dtype=complex,
)
result_a0 = np.array(
    [
        [0 + 0j, 0.7071 - 0.7071j],
        [-0.7071 - 0.7071j, 0 + 0j],
    ],
    dtype=complex,
)

result_q_left = np.array(
    [
        [0, 0, 1, 0],
        [-1, 0, 0, 0],
        [0, 0, 0, 1],
        [0, 1, 0, 0],
    ],
    dtype=complex,
)
result_q_right = np.array(
    [
        [0, 0, 1, 0],
        [-1, 0, 0, 0],
        [0, 0, 0, 1],
        [0, 1, 0, 0],
    ],
    dtype=complex,
)
result_ashn = np.array(
    [
        [0.9239 - 0.3827j, 0 + 0j, 0 + 0j, 0 + 0j],
        [0 + 0j, 0.9239 - 0.3827j, 0 + 0j, 0 + 0j],
        [0 + 0j, 0 + 0j, 0.9239 - 0.3827j, 0 + 0j],
        [0 + 0j, 0 + 0j, 0 + 0j, 0.3827 + 0.9239j],
    ],
    dtype=complex,
)

iswap_matrix = np.array(
    [
        [1, 0, 0, 0],
        [0, 0, 1j, 0],
        [0, 1j, 0, 0],
        [0, 0, 0, 1],
    ],
    dtype=complex,
)
cs_matrix = np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1j],
    ],
    dtype=complex,
)
csdg_matrix = np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, -1j],
    ],
    dtype=complex,
)
ryy_matrix = np.array(
    [
        [1, 0, 0, 1j],
        [0, 1, -1j, 0],
        [0, -1j, 1, 0],
        [1j, 0, 0, 1],
    ],
    dtype=complex,
) / np.sqrt(2)
rzx_matrix = np.array(
    [
        [1, -1j, 0, 0],
        [-1j, 1, 0, 0],
        [0, 0, 1, 1j],
        [0, 0, 1j, 1],
    ],
    dtype=complex,
) / np.sqrt(2)


class TestKAKDecomposer:
    def test_set_matrix(self):
        kak_decomposer.set_matrix(test_matrix)
        result = np.allclose(test_matrix, kak_decomposer.matrix)
        assert result

    def test_get_glob_phase(self):
        mat, phase = kak_decomposer.get_glob_phase(test_matrix)
        result = np.allclose(np.round(mat, 4), glob_phase_matrix)
        assert result
        assert np.round(phase, 4) == 0.3927

    def test_decompose_matric(self):
        a1, a0 = kak_decomposer.decompose_matrix(euler_matrix)
        assert np.allclose(a1, result_a1)
        assert np.allclose(a0, result_a0)

    def test_simu_svd(self):
        kak_decomposer.set_matrix(test_matrix)
        q_left, q_right, ashn, phase = kak_decomposer.simu_svd()
        assert np.round(phase, 4) == 0.3927

    def test_run(self):
        kak_decomposer.set_matrix(test_matrix)
        parms = kak_decomposer.run()
        assert parms[0] == (np.pi / 8) * 3
        assert parms[1] - np.pi / 8 < 1e-12
        assert parms[2] == np.pi / 8

    def test_cz_gate(self):
        kak_decomposer.set_matrix(CZ().to_matrix())
        cz_result = kak_decomposer.run()
        assert cz_result[0] == np.pi / 4
        assert cz_result[1] == 0
        assert cz_result[2] == 0

    def test_cx_gate(self):
        kak_decomposer.set_matrix(CX().to_matrix())
        cx_result = kak_decomposer.run()
        assert cx_result[0] == pytest.approx(np.pi / 4)
        assert cx_result[1] == 0
        assert cx_result[2] == 0

    def test_cy_gate(self):
        kak_decomposer.set_matrix(CY().to_matrix())
        cy_result = kak_decomposer.run()
        assert cy_result[0] == np.pi / 4
        assert cy_result[1] == 0
        assert cy_result[2] == 0

    def test_swap_gate(self):
        kak_decomposer.set_matrix(SWAP().to_matrix())
        swap_result = kak_decomposer.run()
        assert swap_result[0] == np.pi / 4
        assert swap_result[1] == np.pi / 4
        assert swap_result[2] == np.pi / 4

    def test_iswap_gate(self):
        kak_decomposer.set_matrix(iswap_matrix)
        iswap_result = kak_decomposer.run()
        assert iswap_result[0] == pytest.approx(np.pi / 4)
        assert iswap_result[1] == pytest.approx(np.pi / 4)

    def test_ch_gate(self):
        kak_decomposer.set_matrix(CH().to_matrix())
        ch_result = kak_decomposer.run()
        assert ch_result[0] == np.pi / 4
        assert ch_result[1] == 0
        assert ch_result[2] == 0

    def test_cs_gate(self):
        kak_decomposer.set_matrix(cs_matrix)
        cs_result = kak_decomposer.run()
        assert cs_result[0] == np.pi / 8
        assert cs_result[1] == 0
        assert cs_result[2] == 0

    def test_csdg_gate(self):
        kak_decomposer.set_matrix(csdg_matrix)
        csdg_result = kak_decomposer.run()
        assert csdg_result[0] == np.pi / 8
        assert csdg_result[1] == 0
        assert csdg_result[2] == 0

    def test_crx_gate(self):
        kak_decomposer.set_matrix(CRX(arg_value=np.pi / 2).to_matrix())
        crx_result = kak_decomposer.run()
        assert crx_result[0] == np.pi / 8
        assert crx_result[1] == 0
        assert crx_result[2] == 0

    def test_cry_gate(self):
        kak_decomposer.set_matrix(CRY(arg_value=np.pi / 2).to_matrix())
        cry_result = kak_decomposer.run()
        assert cry_result[0] == np.pi / 8
        assert cry_result[1] == 0
        assert cry_result[2] == 0

    def test_crz_gate(self):
        kak_decomposer.set_matrix(CRZ(arg_value=np.pi / 2).to_matrix())
        crz_result = kak_decomposer.run()
        assert crz_result[0] == np.pi / 8
        assert crz_result[1] == 0
        assert crz_result[2] == 0

    def test_cu1_gate(self):
        kak_decomposer.set_matrix(CU1(arg_value=np.pi / 2).to_matrix())
        cu1_result = kak_decomposer.run()
        assert cu1_result[0] == np.pi / 8
        assert cu1_result[1] == 0
        assert cu1_result[2] == 0

    def test_cp_gate(self):
        kak_decomposer.set_matrix(CP(arg_value=np.pi / 2).to_matrix())
        cp_result = kak_decomposer.run()
        assert cp_result[0] == np.pi / 8
        assert cp_result[1] == 0
        assert cp_result[2] == 0

    def test_cu3_gate(self):
        arg_value = [np.pi / 2, np.pi / 2, np.pi / 2]
        kak_decomposer.set_matrix(CU3(arg_value=arg_value).to_matrix())
        cu3_result = kak_decomposer.run()
        assert cu3_result[0] == np.pi / 4
        assert cu3_result[1] == 0
        assert cu3_result[2] == 0

    def test_csx_gate(self):
        kak_decomposer.set_matrix(CSX().to_matrix())
        csx_result = kak_decomposer.run()
        assert csx_result[0] == np.pi / 8
        assert csx_result[1] == 0
        assert csx_result[2] == 0

    def test_cu_gate(self):
        arg_value = [np.pi / 2, np.pi / 2, np.pi / 2, np.pi / 2]
        kak_decomposer.set_matrix(CU(arg_value=arg_value).to_matrix())
        cu_result = kak_decomposer.run()
        assert cu_result[0] == np.pi / 4
        assert cu_result[1] == 0
        assert cu_result[2] == 0

    def test_rxx_gate(self):
        kak_decomposer.set_matrix(RXX(arg_value=np.pi / 2).to_matrix())
        rxx_result = kak_decomposer.run()
        assert rxx_result[0] == np.pi / 4
        assert rxx_result[1] == 0
        assert rxx_result[2] == 0

    def test_ryy_gate(self):
        kak_decomposer.set_matrix(ryy_matrix)
        ryy_result = kak_decomposer.run()
        assert ryy_result[0] == np.pi / 4
        assert ryy_result[1] == 0
        assert ryy_result[2] == 0

    def test_rzz_gate(self):
        kak_decomposer.set_matrix(RZZ(arg_value=np.pi / 2).to_matrix())
        rzz_result = kak_decomposer.run()
        assert rzz_result[0] == np.pi / 4
        assert rzz_result[1] == 0
        assert rzz_result[2] == 0

    def test_rzx_gate(self):
        kak_decomposer.set_matrix(rzx_matrix)
        rzx_result = kak_decomposer.run()
        assert rzx_result[0] == np.pi / 4
        assert rzx_result[1] == 0
        assert rzx_result[2] == 0

    def test_random_matrix(self):
        random_matrix = np.random.randn(4, 4) + 1j * np.random.randn(4, 4)
        q, r = np.linalg.qr(random_matrix)
        kak_decomposer.set_matrix(q)
        result = kak_decomposer.run()
        assert result[0] > 0
        assert result[1] > 0
        assert result[2] > 0
