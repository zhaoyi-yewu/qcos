#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
import numpy as np

from qcos.transpiler.cmss.common.gate_operation import (
    H,
    X,
    Y,
    Z,
    S,
    SDG,
    T,
    P,
    TDG,
    RX,
    RY,
    RZ,
    SX,
    SXDG,
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
    CCX,
    RC3X,
    C3SQRTX,
    CSWAP,
    RCCX,
    U1,
    U2,
    U3,
    C4X,
)
from qcos.transpiler.cmss.circuit.operators.operator import Operator
from qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


class TestOperators:
    def test_gate_matrix(self):
        # test H gate matrix
        gate = H(targets=[0])
        res_gate_mat = np.asarray(
            [
                [0.70710678 + 0.0j, 0.70710678 + 0.0j],
                [0.70710678 + 0.0j, -0.70710678 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test X gate
        gate = X(targets=[0])
        res_gate_mat = np.asarray(
            [[0, 1], [1, 0]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test Y gate
        gate = Y(targets=[0])
        res_gate_mat = np.asarray(
            [[0, -1j], [1j, 0]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test Z gate
        gate = Z(targets=[0])
        res_gate_mat = np.asarray(
            [[1, 0], [0, -1]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test S gate
        gate = S(targets=[0])
        res_gate_mat = np.asarray(
            [[1, 0], [0, 1j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test SDG gate
        gate = SDG(targets=[0])
        res_gate_mat = np.asarray(
            [[1, 0], [0, -1j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test T gate
        gate = T(targets=[0])
        res_gate_mat = np.asarray(
            [[1 + 0.0j, 0.0 + 0.0j], [0 + 0.0j, 0.70710678 + 0.70710678j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test P gate
        gate = P(targets=[0], arg_value=[1])
        res_gate_mat = np.asarray(
            [[1 + 0.0j, 0 + 0.0j], [0 + 0.0j, 0.54030231 + 0.84147098j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test TDG gate
        gate = TDG(targets=[0])
        res_gate_mat = np.asarray(
            [[1 + 0.0j, 0 + 0.0j], [0 + 0.0j, 0.70710678 - 0.70710678j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test TDG gate
        gate = TDG(targets=[0])
        res_gate_mat = np.asarray(
            [[1 + 0.0j, 0 + 0.0j], [0 + 0.0j, 0.70710678 - 0.70710678j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test RX gate
        gate = RX(targets=[0], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [0.87758256 + 0.0j, 0 - 0.47942554j],
                [0 - 0.47942554j, 0.87758256 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test RY gate
        gate = RY(targets=[0], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [0.87758256 + 0.0j, -0.47942554 + 0.0j],
                [0.47942554 + 0.0j, 0.87758256 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test RZ gate
        gate = RZ(targets=[0], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [0.87758256 - 0.47942554j, 0 + 0.0j],
                [0 + 0.0j, 0.87758256 + 0.47942554j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test SX gate
        gate = SX(targets=[0])
        res_gate_mat = np.asarray(
            [[0.5 + 0.5j, 0.5 - 0.5j], [0.5 - 0.5j, 0.5 + 0.5j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test SXDG gate
        gate = SXDG(targets=[0])
        res_gate_mat = np.asarray(
            [[0.5 - 0.5j, 0.5 + 0.5j], [0.5 + 0.5j, 0.5 - 0.5j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CZ gate
        gate = CZ(targets=[0, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, -1.0 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CX gate
        gate = CX(targets=[0, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CY gate
        gate = CY(targets=[0, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 - 1.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 1.0j, 0.0 + 0.0j, 0.0 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test SWAP gate
        gate = SWAP(targets=[0, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CH gate
        gate = CH(targets=[0, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.70710678 + 0.0j, 0.0 + 0.0j, 0.70710678 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [
                    0.0 + 0.0j,
                    0.70710678 + 0.0j,
                    0.0 + 0.0j,
                    -0.70710678 + 0.0j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CRX gate
        gate = CRX(targets=[0, 1], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [
                    0.0 + 0.0j,
                    0.87758256 + 0.0j,
                    0.0 + 0.0j,
                    -0.0 - 0.47942554j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    -0.0 - 0.47942554j,
                    0.0 + 0.0j,
                    0.87758256 + 0.0j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CRY gate
        gate = CRY(targets=[0, 1], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [
                    0.0 + 0.0j,
                    0.87758256 + 0.0j,
                    0.0 + 0.0j,
                    -0.47942554 + 0.0j,
                ],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.47942554 + 0.0j, 0.0 + 0.0j, 0.87758256 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CRZ gate
        gate = CRZ(targets=[0, 1], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.87758256 - 0.47942554j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.87758256 + 0.47942554j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CU1 gate
        gate = CU1(targets=[0, 1], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.54030231 + 0.84147098j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CP gate
        gate = CP(targets=[0, 1], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.54030231 + 0.84147098j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CU3 gate
        gate = CU3(targets=[0, 1], arg_value=[1, 1, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [
                    0.0 + 0.0j,
                    0.87758256 + 0.0j,
                    0.0 + 0.0j,
                    -0.25903472 - 0.40342268j,
                ],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [
                    0.0 + 0.0j,
                    0.25903472 + 0.40342268j,
                    0.0 + 0.0j,
                    -0.36520321 + 0.79798357j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CSX gate
        gate = CSX(targets=[0, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.5 + 0.5j, 0.0 + 0.0j, 0.5 - 0.5j],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.5 - 0.5j, 0.0 + 0.0j, 0.5 + 0.5j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CU gate
        gate = CU(targets=[0, 1], arg_value=[1, 1, 1, 1])
        res_gate_mat = np.asarray(
            [
                [1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [
                    0.0 + 0.0j,
                    0.47415988 + 0.73846026j,
                    0.0 + 0.0j,
                    0.19951142 - 0.43594041j,
                ],
                [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j],
                [
                    0.0 + 0.0j,
                    -0.19951142 + 0.43594041j,
                    0.0 + 0.0j,
                    -0.86880015 + 0.12384446j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test RXX gate
        gate = RXX(targets=[0, 1], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [
                    0.87758256 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    -0.0 - 0.47942554j,
                ],
                [
                    0.0 + 0.0j,
                    0.87758256 + 0.0j,
                    -0.0 - 0.47942554j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    -0.0 - 0.47942554j,
                    0.87758256 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    -0.0 - 0.47942554j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.87758256 + 0.0j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test RZZ gate
        gate = RZZ(targets=[0, 1], arg_value=[1])
        res_gate_mat = np.asarray(
            [
                [0.87758256 - 0.47942554j, 0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.87758256 + 0.47942554j, 0.0 + 0.0j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.87758256 + 0.47942554j, 0.0 + 0.0j],
                [0.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j, 0.87758256 - 0.47942554j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CCX gate
        gate = CCX(targets=[0, 1, 2])
        res_gate_mat = np.asarray(
            [
                [
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test CSWAP gate
        gate = CSWAP(targets=[0, 1, 2])
        res_gate_mat = np.asarray(
            [
                [
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test RCCX gate
        gate = RCCX(targets=[0, 1, 2])
        res_gate_mat = np.asarray(
            [
                [1, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, -1j],
                [0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, -1, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 1j, 0, 0, 0, 0],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test RC3X gate
        gate = RC3X(targets=[0, 1, 2, 3])
        res_gate_mat = np.asarray(
            [
                [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 1j, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1j, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test C3X gate
        gate = RC3X(targets=[0, 1, 2, 3])
        res_gate_mat = np.asarray(
            [
                [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 1j, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1j, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test C3SQRTX gate
        gate = C3SQRTX(targets=[0, 1, 2, 3])
        res_gate_mat = np.asarray(
            [
                [
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.5 + 0.5j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.5 - 0.5j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    1.0 + 0.0j,
                    0.0 + 0.0j,
                ],
                [
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.5 - 0.5j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.0 + 0.0j,
                    0.5 + 0.5j,
                ],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test U1 gate
        gate = U1(targets=[0], arg_value=[1])
        res_gate_mat = np.asarray(
            [[1.0 + 0.0j, 0.0 + 0.0j], [0.0 + 0.0j, 0.54030231 + 0.84147098j]],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test U2 gate
        gate = U2(targets=[0], arg_value=[1, 1])
        res_gate_mat = np.asarray(
            [
                [0.70710678 + 0.0j, -0.38205142 - 0.59500984j],
                [0.38205142 + 0.59500984j, -0.29426025 + 0.64297038j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test U3 gate
        gate = U3(targets=[0], arg_value=[1, 1, 1])
        res_gate_mat = np.asarray(
            [
                [0.87758256 + 0.0j, -0.25903472 - 0.40342268j],
                [0.25903472 + 0.40342268j, -0.36520321 + 0.79798357j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(gate.to_matrix(), res_gate_mat))

        # test GateOperation
        gate = C4X(targets=[0, 1, 2, 3, 4])
        with pytest.raises(Exception) as e:
            gate.to_matrix()

        err_msg = str(e.value)
        assert "to_matrix not defined for this" in err_msg

    def test_operator(self):
        op = Operator(np.eye(4))
        assert op._data.shape == (4, 4)

        qc = QuantumCircuit(num_qubits=2, num_clbits=2)
        op = Operator(qc)
        assert op._data.shape == (4, 4)
