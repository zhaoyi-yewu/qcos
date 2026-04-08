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

from math import sqrt
import numpy as np
from scipy import linalg
from scipy.linalg import expm

from wy_qcos.transpiler.cmss.decomposer.euler_decomposer import EulerDecomposer


class KAKDecomposer:
    def __init__(self):
        self.matrix = None
        self.A0 = None
        self.A1 = None
        self.B0 = None
        self.B1 = None
        self.euler_decomposer = EulerDecomposer()

        self.M = np.array(
            [
                [1, 0, 0, 1j],
                [0, 1j, 1, 0],
                [0, 1j, -1, 0],
                [1, 0, 0, -1j],
            ],
            dtype=complex,
        ) / sqrt(2)
        self.M_DAG = self.M.conj().T

        self.A = np.array(
            [
                [1, 1, -1, 1],
                [1, 1, 1, -1],
                [1, -1, -1, -1],
                [1, -1, 1, 1],
            ],
            dtype=complex,
        )

        self.I = np.eye(2, dtype=complex)
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

    def set_matrix(self, matrix):
        """Set the matrix to be decomposed.

        Args:
            matrix: unitary matrix.
        """
        self.matrix = matrix

    def get_glob_phase(self, mat):
        """Remove the global phase of unitary matrix.

        Args:
            mat: unitary matrix.

        Returns:
            matrix without global phase.
        """
        exp_alpha = linalg.det(mat) ** (1 / 4)
        alpha = np.angle(exp_alpha)
        return mat * expm(-1j * alpha), alpha

    def decompose_matrix(self, mat):
        """Split a 4x4 matrix into two 2x2 matrices, and a global factor.

        Args:
            mat: 4x4 unitary matrix.

        Returns:
            a pair of 2x2 unit-determinant matrices.
        """
        max_val = -float("inf")
        a, b = 0, 0
        for i in range(4):
            for j in range(4):
                if abs(mat[i][j]) > max_val:
                    max_val = abs(mat[i][j])
                    a, b = i, j

        f1 = np.zeros((2, 2), dtype=np.complex128)
        f2 = np.zeros((2, 2), dtype=np.complex128)

        for i in range(2):
            for j in range(2):
                f1[(a >> 1) ^ i, (b >> 1) ^ j] = mat[
                    a ^ (i << 1), b ^ (j << 1)
                ]
                f2[(a & 1) ^ i, (b & 1) ^ j] = mat[a ^ i, b ^ j]

        f1 /= np.sqrt(np.linalg.det(f1)) or 1
        f2 /= np.sqrt(np.linalg.det(f2)) or 1

        denominator = f1[a >> 1, b >> 1] * f2[a & 1, b & 1]
        g = mat[a, b] / denominator
        if np.real(g) < 0:
            f1 *= -1

        return f1, f2

    def simu_svd(self):
        """Simultaneous SVD of two matrices, based on Eckart-Young theorem.

        Returns:
            q_left, q_right, ashn, phase.
        """
        mat, phase = self.get_glob_phase(self.matrix)
        u_su4 = self.M_DAG @ mat @ self.M
        mat1 = np.real(u_su4)
        mat2 = np.imag(u_su4)

        q_left, d, q_right_h = linalg.svd(mat1)
        q_left_h = q_left.conj().T
        q_right = q_right_h.conj().T

        g = q_left_h @ mat2 @ q_right
        dd, p = linalg.eigh(g)
        q_left = q_left @ p
        q_right = q_right @ p

        if linalg.det(q_left) < 0:
            q_left[:, 0] *= -1
        if linalg.det(q_right) < 0:
            q_right[:, 0] *= -1

        d1 = q_left.conj().T @ mat1 @ q_right
        d2 = q_left.conj().T @ mat2 @ q_right
        ashn = d1 + 1j * d2
        return q_left, q_right, ashn, phase

    def run(self):
        """KAK decomposition of an arbitrary two-qubit gate.

        Returns:
            including 1 ashn gate and 4 single-qubit gates.
        """
        q_left, q_right, ashn, phase = self.simu_svd()

        diag_elements = np.diag(ashn)
        thetas = np.angle(diag_elements)
        B = thetas
        res = np.linalg.solve(self.A, B)
        parms = res[1:]
        parms[np.abs(parms) < 1e-12] = 0

        a1, a0 = self.decompose_matrix(self.M @ q_left @ self.M_DAG)
        b1, b0 = self.decompose_matrix(self.M @ q_right.T @ self.M_DAG)

        self.A0 = self.euler_decompose(a0)
        self.A1 = self.euler_decompose(a1)
        self.B0 = self.euler_decompose(b0)
        self.B1 = self.euler_decompose(b1)

        for i in range(len(parms)):
            if parms[i] < 0:
                parms[i] += np.pi / 2
        sorted_parms = sorted(parms, reverse=True)

        if sorted_parms[0] + sorted_parms[1] >= np.pi / 2:
            sorted_parms[0] = np.pi / 2 - sorted_parms[1]
            sorted_parms[1] = np.pi / 2 - sorted_parms[0]
            sorted_parms = sorted(sorted_parms, reverse=True)

        if sorted_parms[2] == 0 and sorted_parms[0] > np.pi / 4:
            sorted_parms[0] = np.pi / 2 - sorted_parms[0]
            sorted_parms = sorted(sorted_parms, reverse=True)
        return sorted_parms

    def euler_decompose(self, mat):
        """Obtain the U3 parameters of a 2x2 unitary matrix.

        Args:
            mat: 2x2 unitary matrix

        Returns:
            lam, theta, phi.
        """
        self.euler_decomposer.set_matrix(mat)
        lam, theta, phi = self.euler_decomposer.run()
        U3_gate_parms = [lam, theta, phi]
        return U3_gate_parms
