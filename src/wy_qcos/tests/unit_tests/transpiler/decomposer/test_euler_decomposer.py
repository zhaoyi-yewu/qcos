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

"""Tests for Euler decomposition of single-qubit unitary matrices."""

import numpy as np
import pytest

from wy_qcos.common.cmss.gate_operation import (
    H,
    X,
    Y,
    Z,
    S,
    SDG,
    T,
    P,
    R,
    TDG,
    RX,
    RY,
    RZ,
    SX,
    SXDG,
    U1,
    U2,
    U3,
    U,
)
from wy_qcos.transpiler.cmss.decomposer.euler_decomposer import EulerDecomposer

test_matrix = np.array(
    [
        [1, 0],
        [0, 1j],
    ],
    dtype=complex,
)
euler_decomposer = EulerDecomposer()


class TestEulerDecomposer:
    """Test Euler decomposition and matrix reconstruction."""

    @pytest.mark.smoke
    def test_set_matrix(self):
        """Test setting the matrix used by the decomposer."""
        euler_decomposer.set_matrix(test_matrix)
        result = np.allclose(test_matrix, euler_decomposer.matrix)
        assert result

    @pytest.mark.smoke
    def test_euler_zyz_decomposition(self):
        """Test ZYZ Euler angle extraction."""
        euler_decomposer.set_matrix(test_matrix)
        phase, theta, phi, lam = euler_decomposer.euler_zyz_decomposition()
        assert lam == pytest.approx(np.pi / 4)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 4)

    @pytest.mark.smoke
    def test_reconstruct_from_zyz(self):
        """Test matrix reconstruction from ZYZ Euler angles."""
        U_reconstructed = euler_decomposer.reconstruct_from_zyz(
            0, np.pi / 4, np.pi / 4
        )
        U_reconstructed = U_reconstructed / (
            np.sqrt(2) / 2 - 1j * np.sqrt(2) / 2
        )
        result = np.allclose(U_reconstructed, test_matrix)
        assert result

    @pytest.mark.smoke
    def test_euler_u3_decomposition(self):
        """Test U3 Euler angle extraction."""
        euler_decomposer.set_matrix(test_matrix)
        phase, theta, phi, lam = euler_decomposer.euler_u3_decomposition()
        assert lam == pytest.approx(np.pi / 4)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 4)

    @pytest.mark.smoke
    def test_reconstruct_from_u3(self):
        """Test matrix reconstruction from U3 Euler angles."""
        U_reconstructed = euler_decomposer.reconstruct_from_u3(
            0, np.pi / 4, np.pi / 4
        )
        result = np.allclose(U_reconstructed, test_matrix)
        assert result

    @pytest.mark.smoke
    def test_run(self):
        """Test the complete Euler decomposition workflow."""
        euler_decomposer.set_matrix(test_matrix)
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 4)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 4)

    def test_h(self):
        """Test Euler decomposition of the H gate."""
        euler_decomposer.set_matrix(H().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi)
        assert theta == pytest.approx(np.pi / 2)
        assert phi == pytest.approx(0)

    def test_x(self):
        """Test Euler decomposition of the X gate."""
        euler_decomposer.set_matrix(X().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(-np.pi / 2)
        assert theta == pytest.approx(np.pi)
        assert phi == pytest.approx(np.pi / 2)

    def test_y(self):
        """Test Euler decomposition of the Y gate."""
        euler_decomposer.set_matrix(Y().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(-np.pi)
        assert theta == pytest.approx(np.pi)
        assert phi == pytest.approx(np.pi)

    def test_z(self):
        """Test Euler decomposition of the Z gate."""
        euler_decomposer.set_matrix(Z().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 2)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 2)

    def test_s(self):
        """Test Euler decomposition of the S gate."""
        euler_decomposer.set_matrix(S().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 4)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 4)

    def test_sdg(self):
        """Test Euler decomposition of the SDG gate."""
        euler_decomposer.set_matrix(SDG().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(-np.pi / 4)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(-np.pi / 4)

    def test_t(self):
        """Test Euler decomposition of the T gate."""
        euler_decomposer.set_matrix(T().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 8)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 8)

    def test_tdg(self):
        """Test Euler decomposition of the TDG gate."""
        euler_decomposer.set_matrix(TDG().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(-np.pi / 8)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(-np.pi / 8)

    def test_p(self):
        """Test Euler decomposition of the P gate."""
        euler_decomposer.set_matrix(P(arg_value=np.pi).to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 2)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 2)

    def test_r(self):
        """Test Euler decomposition of the R gate."""
        euler_decomposer.set_matrix(R(arg_value=[np.pi, np.pi]).to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(-np.pi / 2)
        assert theta == pytest.approx(np.pi)
        assert phi == pytest.approx(np.pi / 2)

    def test_rx(self):
        """Test Euler decomposition of the RX gate."""
        euler_decomposer.set_matrix(RX(arg_value=np.pi / 2).to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 2)
        assert theta == pytest.approx(np.pi / 2)
        assert phi == pytest.approx(-np.pi / 2)

    def test_ry(self):
        """Test Euler decomposition of the RY gate."""
        euler_decomposer.set_matrix(RY(arg_value=np.pi / 2).to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(0)
        assert theta == pytest.approx(np.pi / 2)
        assert phi == pytest.approx(0)

    def test_rz(self):
        """Test Euler decomposition of the RZ gate."""
        euler_decomposer.set_matrix(RZ(arg_value=np.pi / 2).to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 4)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 4)

    def test_sx(self):
        """Test Euler decomposition of the SX gate."""
        euler_decomposer.set_matrix(SX().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 2)
        assert theta == pytest.approx(np.pi / 2)
        assert phi == pytest.approx(-np.pi / 2)

    def test_sxdg(self):
        """Test Euler decomposition of the SXDG gate."""
        euler_decomposer.set_matrix(SXDG().to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(-np.pi / 2)
        assert theta == pytest.approx(np.pi / 2)
        assert phi == pytest.approx(np.pi / 2)

    def test_u1(self):
        """Test Euler decomposition of the U1 gate."""
        euler_decomposer.set_matrix(U1(arg_value=[np.pi, np.pi]).to_matrix())
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 2)
        assert theta == pytest.approx(0)
        assert phi == pytest.approx(np.pi / 2)

    def test_u2(self):
        """Test Euler decomposition of the U2 gate."""
        euler_decomposer.set_matrix(
            U2(arg_value=[np.pi / 2, np.pi / 2]).to_matrix()
        )
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 2)
        assert theta == pytest.approx(np.pi / 2)
        assert phi == pytest.approx(np.pi / 2)

    def test_u3(self):
        """Test Euler decomposition of the U3 gate."""
        euler_decomposer.set_matrix(
            U3(arg_value=[np.pi / 2, np.pi / 2, np.pi / 2]).to_matrix()
        )
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 2)
        assert theta == pytest.approx(np.pi / 2)
        assert phi == pytest.approx(np.pi / 2)

    def test_u(self):
        """Test Euler decomposition of the U gate."""
        euler_decomposer.set_matrix(
            U(arg_value=[np.pi / 4, np.pi / 4, np.pi / 4]).to_matrix()
        )
        theta, phi, lam, phase = euler_decomposer.run()
        assert lam == pytest.approx(np.pi / 4)
        assert theta == pytest.approx(np.pi / 4)
        assert phi == pytest.approx(np.pi / 4)
