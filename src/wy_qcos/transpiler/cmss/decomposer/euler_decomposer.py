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

from math import atan2, cos, sin

import numpy as np
from scipy import linalg


class EulerDecomposer:
    def __init__(self):
        self.matrix = None

    def set_matrix(self, matrix):
        self.matrix = matrix

    def euler_zyz_decomposition(self):
        """Decompose the unitary matrix into Rz(λ) Ry(θ) Rz(ϕ).

        Return:
            coe: global phase
            lam: λ
            theta: θ
            phi: ϕ
        """
        U = self.matrix.astype(np.complex128)
        coe = linalg.det(U) ** (-0.5)
        U = coe * U

        a = U[0, 0]
        c = U[1, 0]
        d = U[1, 1]

        theta = 2 * atan2(abs(c), abs(a))
        sum = np.angle(d)
        diff = np.angle(c)
        phi = sum + diff
        lam = sum - diff

        return coe, lam, theta, phi

    def euler_u3_decomposition(self):
        """Decompose the unitary matrix into U3(λ,θ,ϕ).

        Return:
            coe: global phase
            lam: λ
            theta: θ
            phi: ϕ
        """
        coe, lam, theta, phi = self.euler_zyz_decomposition()
        return coe, lam, theta, phi

    def reconstruct_from_zyz(self, lam, theta, phi):
        """Reconstruct matrix use Rz(λ) Ry(θ) Rz(ϕ).

        Args:
            lam: λ.
            theta: θ.
            phi: ϕ.

        Returns:
            the reconstructed Rz(λ) Ry(θ) Rz(ϕ) matrix.
        """
        Rz_lam = np.array([
            [np.exp(-1j * lam / 2), 0],
            [0, np.exp(1j * lam / 2)],
        ])
        Ry_theta = np.array([
            [np.cos(theta / 2), -np.sin(theta / 2)],
            [np.sin(theta / 2), np.cos(theta / 2)],
        ])
        Rz_phi = np.array([
            [np.exp(-1j * phi / 2), 0],
            [0, np.exp(1j * phi / 2)],
        ])

        return Rz_phi @ Ry_theta @ Rz_lam

    def reconstruct_from_u3(self, lam, theta, phi):
        """Reconstruct matrix use U3(λ,θ,ϕ).

        Args:
            lam:λ.
            theta: θ.
            phi: ϕ.

        Returns:
            the reconstructed U3(λ,θ,ϕ) matrix.
        """
        u3_cos = cos(theta / 2)
        u3_sin = sin(theta / 2)
        u3_matrix = np.array(
            [
                [u3_cos, -np.exp(1j * lam) * u3_sin],
                [np.exp(1j * phi) * u3_sin, np.exp(1j * (phi + lam)) * u3_cos],
            ],
            dtype=complex,
        )
        return u3_matrix

    def run(self, basis="zyz"):
        """Euler decompose ,decompose the unitary matrix into u3 or zyz gate.

        Args:
            basis: zyz or u3

        Returns:
            lam, theta, phi.
        """
        if basis == "zyz":
            coe, lam, theta, phi = self.euler_zyz_decomposition()
            U_reconstructed = self.reconstruct_from_zyz(lam, theta, phi)
            U_reconstructed = U_reconstructed / coe
            errors = np.linalg.norm(self.matrix - U_reconstructed)
            if errors > 1e-6:
                raise ValueError(
                    "decomposed matrix and original matrix is not the same"
                )
            return lam, theta, phi
        elif basis == "u3":
            coe, lam, theta, phi = self.euler_zyz_decomposition()
            U_reconstructed = self.reconstruct_from_u3(lam, theta, phi)
            U_reconstructed = U_reconstructed / coe
            errors = np.linalg.norm(self.matrix - U_reconstructed)
            if errors > 1e-6:
                raise ValueError(
                    "decomposed matrix and original matrix is not the same"
                )
            return lam, theta, phi
        return None
