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


class GenerateSU4:
    def __init__(self):
        self.matrix = None
        self.X = np.array(
            [
                [0, 1],
                [1, 0],
            ],
            dtype=complex,
        )
        self.Y = np.array(
            [
                [0, -1j],
                [1j, 0],
            ],
            dtype=complex,
        )
        self.Z = np.array(
            [
                [1, 0],
                [0, -1],
            ],
            dtype=complex,
        )

        self.XX = np.kron(self.X, self.X)
        self.YY = np.kron(self.Y, self.Y)
        self.ZZ = np.kron(self.Z, self.Z)

    def random_unitary(self, N):
        """Generate random unitary matrix.

        Args:
            N: matrix order

        Returns:
            matrix
        """
        Z = np.random.randn(N, N) + 1j * np.random.randn(N, N)
        Q, R = np.linalg.qr(Z)
        D = np.diag(np.diag(R) / np.abs(np.diag(R)))
        self.matrix = Q @ D
        return Q @ D

    def uniform(self):
        """Generate (kx, ky, kz) that satisfy all constraints.

        Returns:
            kx, ky, kz
        """
        pi = np.pi
        half = pi / 2
        quarter = pi / 4

        r1, r2, r3 = np.random.uniform(0, 1, 3)
        c = -np.log(r1)
        b = c - np.log(r2)
        a = b - np.log(r3)
        s = a + b + c

        # Normalization
        a /= s
        b /= s
        c /= s

        # Scale to satisfy kx ky <= pi/2
        scale = half / (a + b)
        kx = a * scale
        ky = b * scale
        kz = c * scale

        # kx >= ky >= kz
        kx, ky, kz = np.sort([kx, ky, kz])[::-1]

        vol1 = (pi**3) / 192
        vol2 = (pi**2) / 32
        p = vol1 / (vol1 + vol2)

        if np.random.uniform() > p:
            # Enter kz = 0 region: uniform sampling
            kx = np.random.uniform(0, quarter)
            ky = np.random.uniform(0, kx)
            kz = 0.0
        self.matrix = expm(1j * (kx * self.XX + ky * self.YY + kz * self.ZZ))
        return kx, ky, kz
