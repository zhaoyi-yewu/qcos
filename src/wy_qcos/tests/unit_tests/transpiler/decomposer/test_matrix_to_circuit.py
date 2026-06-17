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

import itertools
import numpy as np
import pytest

from wy_qcos.common.cmss.gate_operation import (
    CZ,
    CX,
    H,
    SWAP,
    RXX,
    RYY,
    RZZ,
)
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator
from wy_qcos.transpiler.cmss.decomposer.generate_su4_matrix import GenerateSU4
from wy_qcos.transpiler.cmss.decomposer.matrix_to_circuit import (
    MatrixDecomposer,
    matrix_to_circuit,
)

decomposer = MatrixDecomposer()
generate_su4 = GenerateSU4()


def _random_unitary(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((size, size)) + 1j * rng.standard_normal(
        (size, size)
    )
    q, _ = np.linalg.qr(z)
    return q


def _assert_equiv(matrix: np.ndarray, gates, num_qubits: int):
    circuit = QuantumCircuit.from_ir(gates, num_qubits)
    operator = Operator(circuit)
    assert operator.equiv(Operator(matrix))


class TestMatrixToCircuit:
    @pytest.mark.smoke
    def test_one_qubit_h(self):
        matrix = H().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    @pytest.mark.smoke
    def test_two_qubit_cz(self):
        matrix = CZ().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_two_qubit_common_gates(self):
        for gate in (CX(), SWAP(), RXX([0, 1], [np.pi / 3]), RZZ([0, 1], [0.4])):
            matrix = gate.to_matrix()
            gates, _ = matrix_to_circuit(matrix, [0, 1])
            _assert_equiv(matrix, gates, 2)

    def test_two_qubit_random(self):
        generate_su4.uniform()
        matrix = generate_su4.matrix
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_three_qubit_random(self):
        matrix = _random_unitary(8, seed=7)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_invalid_matrix_raises(self):
        with pytest.raises(ValueError):
            matrix_to_circuit(np.eye(3))

    def test_ryy_gate_matrix(self):
        matrix = RYY([0, 1], [np.pi / 2]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)
    
    def test_cz_control_reversal_symmetry(self):
        matrix = CZ().to_matrix()

        gates1, _ = matrix_to_circuit(matrix, [0, 1])
        gates2, _ = matrix_to_circuit(matrix, [1, 0])

        _assert_equiv(matrix, gates1, 2)
        _assert_equiv(matrix, gates2, 2)
    
    def test_cx_cz_structure_consistency(self):
        cx_matrix = CX().to_matrix()
        cz_matrix = CZ().to_matrix()

        gates1, _ = matrix_to_circuit(cx_matrix, [0, 1])
        gates2, _ = matrix_to_circuit(cz_matrix, [0, 1])

        _assert_equiv(cx_matrix, gates1, 2)
        _assert_equiv(cz_matrix, gates2, 2)
        
    def test_recursion_stack_safety(self):
        matrix = np.eye(4, dtype=complex)

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

        # 再跑一遍（防 internal state leak）
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)
        
    def test_diagonal_unitary(self):
        diag = np.diag([1, -1, 1, -1]).astype(complex)

        gates, _ = matrix_to_circuit(diag, [0, 1])
        _assert_equiv(diag, gates, 2)

    
    def test_zero_angle_rxx(self):
        matrix = RXX([0, 1], [0.0]).to_matrix()

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)
    
    def test_four_qubit_random_smoke(self):
        matrix = _random_unitary(16, seed=123)

        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)
    
    def test_gate_decompose_stability(self):
        gate = SWAP()
        matrix = gate.to_matrix()

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

        # 再跑一次 decomposition
        gates2, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates2, 2)
    
    def test_qubit_aliasing_bug(self):
        matrix = CX().to_matrix()

        # intentionally reversed + reused indices
        gates, _ = matrix_to_circuit(matrix, [2, 2])

        # 应该要抛错或失败
        with pytest.raises(Exception):
            _assert_equiv(matrix, gates, 2)
        
    def test_identity_repeatability(self):
        I = np.eye(4, dtype=complex)

        g1, _ = matrix_to_circuit(I, [0, 1])
        g2, _ = matrix_to_circuit(I, [0, 1])

        _assert_equiv(I, g1, 2)
        _assert_equiv(I, g2, 2)
    
    def test_su4_repeatability(self):
        for seed in range(5):
            generate_su4.uniform()
            matrix = generate_su4.matrix

            gates, _ = matrix_to_circuit(matrix, [0, 1])
            _assert_equiv(matrix, gates, 2)
    
    def test_global_phase_equivalence(self):
        matrix = CZ().to_matrix()

        phase = np.exp(1j * np.pi / 3)
        matrix2 = phase * matrix

        gates, _ = matrix_to_circuit(matrix2, [0, 1])

        _assert_equiv(matrix2, gates, 2)
    
    def test_global_phase_only(self):
        matrix = np.exp(1j * np.pi / 4) * np.eye(4)

        gates, _ = matrix_to_circuit(matrix, [0, 1])

        _assert_equiv(matrix, gates, 2)
    
    def test_near_identity(self):
        eps = 1e-12

        matrix = np.array(
            [
                [1, eps],
                [-eps, 1]
            ],
            dtype=complex
        )

        q, _ = np.linalg.qr(matrix)

        gates, _ = matrix_to_circuit(q, [0])

        _assert_equiv(q, gates, 1)
    
    @pytest.mark.parametrize("seed", range(50))
    def test_su4_stress(self, seed):
        rng = np.random.default_rng(seed)

        z = rng.normal(size=(4,4)) + 1j*rng.normal(size=(4,4))
        q, _ = np.linalg.qr(z)

        gates, _ = matrix_to_circuit(q, [0,1])

        _assert_equiv(q, gates, 2)
    
    paulis = [
        np.array([[1, 0], [0, 1]], dtype=complex),   # I
        np.array([[0, 1], [1, 0]], dtype=complex),   # X
        np.array([[0, -1j], [1j, 0]], dtype=complex),# Y
        np.array([[1, 0], [0, -1]], dtype=complex),   # Z
    ]
    @pytest.mark.parametrize(
        "a,b",
        itertools.product(paulis, repeat=2)
    )
    def test_pauli_tensor(self, a, b):
        matrix = np.kron(a, b)

        gates, _ = matrix_to_circuit(matrix, [0,1])

        _assert_equiv(matrix, gates, 2)
    
    
    def test_bell_transform(self):
        matrix = CX().to_matrix() @ np.kron(H().to_matrix(), np.eye(2))

        gates, _ = matrix_to_circuit(matrix, [0,1])

        _assert_equiv(matrix, gates, 2)
    
    def test_random_diagonal_unitary(self):
        rng = np.random.default_rng(0)

        phases = np.exp(
            1j * rng.uniform(0, 2*np.pi, size=4)
        )

        matrix = np.diag(phases)

        gates, _ = matrix_to_circuit(matrix, [0,1])

        _assert_equiv(matrix, gates, 2)
    
    @pytest.mark.parametrize(
        "matrix",
        [
            CX().to_matrix(),
            CZ().to_matrix(),
            SWAP().to_matrix(),
        ]
    )
    def test_hermitian_unitaries(self, matrix):
        gates, _ = matrix_to_circuit(matrix, [0,1])

        _assert_equiv(matrix, gates, 2)
    
    
    def test_non_unitary_rejected(self):
        matrix = np.array(
            [
                [1,0],
                [0,2]
            ],
            dtype=complex
        )

        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])
    
    def test_singular_matrix_rejected(self):
        matrix = np.array(
            [
                [1,0],
                [0,0]
            ],
            dtype=complex
        )

        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])
    
    def test_nan_matrix(self):
        matrix = np.eye(2, dtype=complex)

        matrix[0,0] = np.nan

        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])
    
    def test_inf_matrix(self):
        matrix = np.eye(2, dtype=complex)

        matrix[0,0] = np.inf

        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])
    
    def test_qubit_count_mismatch(self):
        matrix = CZ().to_matrix()

        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])
    
    def test_empty_qubits(self):
        matrix = np.eye(2)

        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [])
    
    @pytest.mark.parametrize("seed", range(100))
    def test_random_two_qubit_regression(self, seed):
        matrix = _random_unitary(4, seed)

        gates, _ = matrix_to_circuit(matrix, [0,1])

        _assert_equiv(matrix, gates, 2)
    
    def test_redecompose_result(self):
        matrix = _random_unitary(4, 42)

        gates, _ = matrix_to_circuit(matrix, [0,1])

        circuit = QuantumCircuit.from_ir(gates, 2)

        recovered = Operator(circuit).data

        gates2, _ = matrix_to_circuit(recovered, [0,1])

        _assert_equiv(recovered, gates2, 2)
    
    def test_five_qubit_random(self):
        matrix = _random_unitary(32, seed=999)

        gates, _ = matrix_to_circuit(matrix, [0,1,2,3,4])

        _assert_equiv(matrix, gates, 5)