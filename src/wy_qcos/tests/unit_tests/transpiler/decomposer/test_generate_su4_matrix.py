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
from scipy.linalg import expm

from wy_qcos.transpiler.cmss.decomposer.generate_su4_matrix import GenerateSU4

su4 = GenerateSU4()


class TestGenerateSU4:
    def test_random_unitary(self):
        U = su4.random_unitary(4)
        assert np.allclose(np.eye(4), U @ U.conj().T)

    def test_uniform(self):
        kx, ky, kz = su4.uniform()
        assert kx >= ky >= kz
        assert np.pi / 2 > kx >= 0
        assert np.pi / 2 > ky >= 0
        assert np.pi / 2 > kz >= 0

        cond1 = kx + ky <= np.pi / 2 + 1e-12
        assert cond1

        if np.isclose(kz, 0):
            cond2 = kx <= np.pi / 4 + 1e-12
            assert cond2

        U = expm(1j * (kx * su4.XX + ky * su4.YY + kz * su4.ZZ))
        assert np.allclose(np.eye(4), U @ U.conj().T)
