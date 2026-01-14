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
import math as m

from wy_qcos.transpiler.cmss.common.gate_operation import (
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
from wy_qcos.transpiler.cmss.common.sync import Sync
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


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

        # test C4X gate
        gate = C4X(targets=[0, 1, 2, 3, 4])
        gate_matrix = gate.to_matrix()
        mat_shape = gate_matrix.shape
        close1 = m.isclose(
            gate_matrix[mat_shape[0] - 1][mat_shape[1] // 2 - 1], 1
        )
        close2 = m.isclose(
            gate_matrix[mat_shape[0] // 2 - 1][mat_shape[1] - 1], 1
        )
        assert close1 and close2

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

    def test_operator(self):
        op1 = Operator(np.eye(4))
        assert op1.data.shape == (4, 4)

        qc = QuantumCircuit(num_qubits=2, num_clbits=2)
        op2 = Operator(qc)
        assert op2.data.shape == (4, 4)

        op3 = Operator._init_instruction(H([0]))
        res_gate_mat = np.asarray(
            [
                [0.70710678 + 0.0j, 0.70710678 + 0.0j],
                [0.70710678 + 0.0j, -0.70710678 + 0.0j],
            ],
            dtype=complex,
        )
        assert np.all(np.isclose(op3.data, res_gate_mat))

    def test_operator_equiv(self):
        qc1 = QuantumCircuit(num_qubits=1)
        gate_list = [H([0]), Z([0]), H([0])]
        qc1.append_operations(gate_list)
        op1 = Operator(qc1)

        qc2 = QuantumCircuit(num_qubits=1)
        qc2.append(X([0]))
        op2 = Operator(qc2)
        assert op1.equiv(op2) is True
        assert op1.equiv("invalid data") is False
        assert op1.equiv(Operator(np.eye(3))) is False

    def test_operator_dot(self):
        op1 = Operator(np.eye(4))
        op2 = Operator(np.eye(4))
        op1.compose(op2, front=False)
        assert op1.data.shape == (4, 4)
        assert np.all(np.isclose(op1.data, np.eye(4)))

        op1.compose(op2, front=True)
        assert np.all(np.isclose(op1.data, np.eye(4)))

    def test_operater_exception(self):
        with pytest.raises(Exception) as e1:
            Operator("invalid input")

        err_msg = str(e1.value)
        assert "Invalid input data format for Operator." in err_msg

        with pytest.raises(Exception) as e2:
            Operator(np.eye(2))._append_instruction("invalid instruction")

        err_msg = str(e2.value)
        assert "Input object isnot QuantumCircuit." in err_msg

        sync = Sync([0])
        qc = QuantumCircuit(num_qubits=2)
        qc.append(sync)
        op = Operator(np.eye(4))
        op._append_instruction(qc)
        assert op.data.shape == (4, 4)

    def test_operator_global_phase(self):
        """Test equivalence of operators with global phase.

        The Hadamard gate is equivalent to RY and RX gates with
        angles π and π/2, respectively.

        example::

            global phase: π/2
            ┌───┐        ┌─────────┐┌───────┐
         q: ┤ H ├  ≡  q: ┤ Ry(π/2) ├┤ Rx(π) ├
            └───┘        └─────────┘└───────┘
        """
        qc1 = QuantumCircuit(num_qubits=1)
        qc1.append(H([0]))
        op1 = Operator(qc1)

        qc2 = QuantumCircuit(num_qubits=1, global_phase=np.pi / 2)
        qc2.append_operations([
            RY(targets=[0], arg_value=[np.pi / 2]),
            RX(targets=[0], arg_value=[np.pi]),
        ])
        op2 = Operator(qc2)
        assert op1.equiv(op2) is True
