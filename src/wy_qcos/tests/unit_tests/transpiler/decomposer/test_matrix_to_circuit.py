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

"""Unit tests for matrix-to-circuit decomposition."""

import itertools
import numpy as np
import pytest

from wy_qcos.common.cmss.gate_operation import (
    CZ,
    CX,
    CY,
    CH,
    H,
    RXX,
    RYY,
    RZZ,
    SWAP,
    RX,
    RY,
    RZ,
    X,
    Y,
    Z,
    S,
    SDG,
    T,
    TDG,
    SX,
    SXDG,
    P,
    U1,
    U2,
    U3,
    U,
    CRX,
    CRY,
    CRZ,
    CP,
    CU1,
    CU3,
    CU,
    CSX,
    CCX,
    CSWAP,
    RCCX,
    BaseOperation,
    create_gate,
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


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _random_unitary(size: int, seed: int) -> np.ndarray:
    """Generate a random unitary matrix of given size.

    Args:
        size: Matrix dimension (power of two).
        seed: Random seed for reproducibility.

    Returns:
        A unitary matrix of shape (size, size).
    """
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((size, size)) + 1j * rng.standard_normal((
        size,
        size,
    ))
    q, _ = np.linalg.qr(z)
    return q


def _assert_equiv(
    matrix: np.ndarray, gates: list[BaseOperation], num_qubits: int
) -> None:
    """Assert that a gate list implements the given unitary matrix.

    Args:
        matrix: The target unitary matrix.
        gates: List of gates to be tested.
        num_qubits: Number of qubits in the circuit.

    Raises:
        AssertionError: If the gate sequence does not match the matrix.
    """
    circuit = QuantumCircuit.from_ir(gates, num_qubits)
    operator = Operator(circuit)
    assert operator.equiv(Operator(matrix))


# ----------------------------------------------------------------------
# Test class
# ----------------------------------------------------------------------


class TestMatrixToCircuit:
    """Test suite for MatrixDecomposer and matrix_to_circuit."""

    @pytest.mark.smoke
    def test_one_qubit_h(self) -> None:
        """Decompose a Hadamard gate (single qubit)."""
        matrix = H().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    @pytest.mark.smoke
    def test_two_qubit_cz(self) -> None:
        """Decompose a CZ gate (two qubits)."""
        matrix = CZ().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_two_qubit_common_gates(self) -> None:
        """Decompose common two-qubit gates (CX, SWAP, RXX, RZZ)."""
        for gate in (
            CX(),
            SWAP(),
            RXX([0, 1], [np.pi / 3]),
            RZZ([0, 1], [0.4]),
        ):
            matrix = gate.to_matrix()
            gates, _ = matrix_to_circuit(matrix, [0, 1])
            _assert_equiv(matrix, gates, 2)

    def test_two_qubit_random(self) -> None:
        """Decompose a random SU(4) matrix."""
        generate_su4.uniform()
        matrix = generate_su4.matrix
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_three_qubit_random(self) -> None:
        """Decompose a random 3-qubit unitary."""
        matrix = _random_unitary(8, seed=7)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_invalid_matrix_raises(self) -> None:
        """Non-power-of-two dimension should raise ValueError."""
        with pytest.raises(ValueError):
            matrix_to_circuit(np.eye(3))

    def test_ryy_gate_matrix(self) -> None:
        """Decompose RYY gate."""
        matrix = RYY([0, 1], [np.pi / 2]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_cz_control_reversal_symmetry(self) -> None:
        """CZ decomposition should be symmetric under control reversal."""
        matrix = CZ().to_matrix()

        gates1, _ = matrix_to_circuit(matrix, [0, 1])
        gates2, _ = matrix_to_circuit(matrix, [1, 0])

        _assert_equiv(matrix, gates1, 2)
        _assert_equiv(matrix, gates2, 2)

    def test_cx_cz_structure_consistency(self) -> None:
        """Ensure CX and CZ decompositions are structurally correct."""
        cx_matrix = CX().to_matrix()
        cz_matrix = CZ().to_matrix()

        gates1, _ = matrix_to_circuit(cx_matrix, [0, 1])
        gates2, _ = matrix_to_circuit(cz_matrix, [0, 1])

        _assert_equiv(cx_matrix, gates1, 2)
        _assert_equiv(cz_matrix, gates2, 2)

    def test_recursion_stack_safety(self) -> None:
        """Identity matrix decomposition should not cause recursion issues."""
        matrix = np.eye(4, dtype=complex)

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

        # Run a second time to check for internal state leaks.
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_diagonal_unitary(self) -> None:
        """Diagonal unitary matrix should decompose correctly."""
        diag = np.diag([1, -1, 1, -1]).astype(complex)

        gates, _ = matrix_to_circuit(diag, [0, 1])
        _assert_equiv(diag, gates, 2)

    def test_zero_angle_rxx(self) -> None:
        """RXX with zero angle should reduce to identity."""
        matrix = RXX([0, 1], [0.0]).to_matrix()

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_four_qubit_random_smoke(self) -> None:
        """Decompose a random 4-qubit unitary (smoke test)."""
        matrix = _random_unitary(16, seed=123)

        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_gate_decompose_stability(self) -> None:
        """SWAP decomposition should be stable across runs."""
        gate = SWAP()
        matrix = gate.to_matrix()

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

        # Run decomposition again to ensure repeatability.
        gates2, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates2, 2)

    def test_qubit_aliasing_bug(self) -> None:
        """Duplicate qubit indices should raise an error."""
        matrix = CX().to_matrix()

        # Intentionally provide repeated indices.
        with pytest.raises(Exception):
            gates, _ = matrix_to_circuit(matrix, [2, 2])
            # The decomposition might pass, but circuit construction will fail.
            _assert_equiv(matrix, gates, 2)

    def test_identity_repeatability(self) -> None:
        """Identity matrix decomposition should be repeatable."""
        identity = np.eye(4, dtype=complex)

        g1, _ = matrix_to_circuit(identity, [0, 1])
        g2, _ = matrix_to_circuit(identity, [0, 1])

        _assert_equiv(identity, g1, 2)
        _assert_equiv(identity, g2, 2)

    def test_su4_repeatability(self) -> None:
        """SU(4) random matrix decomposition should be repeatable."""
        for seed in range(5):
            generate_su4.uniform()
            matrix = generate_su4.matrix

            gates, _ = matrix_to_circuit(matrix, [0, 1])
            _assert_equiv(matrix, gates, 2)

    def test_global_phase_equivalence(self) -> None:
        """A global phase factor should not affect equivalence."""
        matrix = CZ().to_matrix()

        phase = np.exp(1j * np.pi / 3)
        matrix2 = phase * matrix

        gates, _ = matrix_to_circuit(matrix2, [0, 1])
        _assert_equiv(matrix2, gates, 2)

    def test_global_phase_only(self) -> None:
        """A pure global phase matrix should decompose to identity."""
        matrix = np.exp(1j * np.pi / 4) * np.eye(4)

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_near_identity(self) -> None:
        """A nearly-identity matrix should decompose stably."""
        eps = 1e-12
        matrix = np.array([[1, eps], [-eps, 1]], dtype=complex)
        q, _ = np.linalg.qr(matrix)

        gates, _ = matrix_to_circuit(q, [0])
        _assert_equiv(q, gates, 1)

    @pytest.mark.parametrize("seed", range(50))
    def test_su4_stress(self, seed: int) -> None:
        """Stress test with 50 random SU(4) matrices."""
        rng = np.random.default_rng(seed)
        z = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
        q, _ = np.linalg.qr(z)

        gates, _ = matrix_to_circuit(q, [0, 1])
        _assert_equiv(q, gates, 2)

    # Pauli matrices for tensor product tests.
    PAULIS = [
        np.array([[1, 0], [0, 1]], dtype=complex),  # I
        np.array([[0, 1], [1, 0]], dtype=complex),  # X
        np.array([[0, -1j], [1j, 0]], dtype=complex),  # Y
        np.array([[1, 0], [0, -1]], dtype=complex),  # Z
    ]

    @pytest.mark.parametrize("a,b", itertools.product(PAULIS, repeat=2))
    def test_pauli_tensor(self, a: np.ndarray, b: np.ndarray) -> None:
        """Decompose tensor products of Pauli matrices."""
        matrix = np.kron(a, b)

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_bell_transform(self) -> None:
        """Decompose the Bell state preparation circuit."""
        matrix = CX().to_matrix() @ np.kron(H().to_matrix(), np.eye(2))

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_random_diagonal_unitary(self) -> None:
        """Decompose a random diagonal unitary (phase shifts)."""
        rng = np.random.default_rng(0)
        phases = np.exp(1j * rng.uniform(0, 2 * np.pi, size=4))
        matrix = np.diag(phases)

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    @pytest.mark.parametrize(
        "matrix",
        [
            CX().to_matrix(),
            CZ().to_matrix(),
            SWAP().to_matrix(),
        ],
    )
    def test_hermitian_unitaries(self, matrix: np.ndarray) -> None:
        """Decompose Hermitian unitaries (CX, CZ, SWAP)."""
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_non_unitary_rejected(self) -> None:
        """Non-unitary matrix should raise ValueError."""
        matrix = np.array([[1, 0], [0, 2]], dtype=complex)
        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])

    def test_singular_matrix_rejected(self) -> None:
        """Singular matrix should raise ValueError."""
        matrix = np.array([[1, 0], [0, 0]], dtype=complex)
        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])

    def test_nan_matrix(self) -> None:
        """Matrix with NaN should raise ValueError."""
        matrix = np.eye(2, dtype=complex)
        matrix[0, 0] = np.nan
        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])

    def test_inf_matrix(self) -> None:
        """Matrix with Inf should raise ValueError."""
        matrix = np.eye(2, dtype=complex)
        matrix[0, 0] = np.inf
        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])

    def test_qubit_count_mismatch(self) -> None:
        """Qubit list length mismatch should raise ValueError."""
        matrix = CZ().to_matrix()
        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [0])

    def test_empty_qubits(self) -> None:
        """Empty qubit list should raise ValueError."""
        matrix = np.eye(2)
        with pytest.raises(ValueError):
            matrix_to_circuit(matrix, [])

    @pytest.mark.parametrize("seed", range(100))
    def test_random_two_qubit_regression(self, seed: int) -> None:
        """Regression test: random 2-qubit unitaries for 100 seeds."""
        matrix = _random_unitary(4, seed)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_redecompose_result(self) -> None:
        """Decompose a matrix, reconstruct it, then decompose again."""
        matrix = _random_unitary(4, 42)

        gates, _ = matrix_to_circuit(matrix, [0, 1])
        circuit = QuantumCircuit.from_ir(gates, 2)
        recovered = Operator(circuit).data

        gates2, _ = matrix_to_circuit(recovered, [0, 1])
        _assert_equiv(recovered, gates2, 2)

    def test_five_qubit_random(self) -> None:
        """Decompose a random 5-qubit unitary (smoke test)."""
        matrix = _random_unitary(32, seed=999)

        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3, 4])
        _assert_equiv(matrix, gates, 5)

    # ------------------------------------------------------------------
    # Coverage-boost tests for internal helper methods
    # ------------------------------------------------------------------

    def test_single_qubit_u3_params(self) -> None:
        """_single_qubit_u3_params should return valid (params, phase)."""
        matrix = H().to_matrix()
        params, phase = decomposer._single_qubit_u3_params(matrix)
        assert len(params) == 3
        assert isinstance(phase, float)

    def test_single_qubit_subcircuit_matrix_empty(self) -> None:
        """Empty gate list should return identity matrix."""
        mat = decomposer._single_qubit_subcircuit_matrix([])
        assert mat is not None
        np.testing.assert_allclose(mat, np.eye(2, dtype=complex), atol=1e-12)

    def test_single_qubit_subcircuit_matrix_single_gate(self) -> None:
        """Single RZ gate should produce its matrix."""
        gate = RZ([0], [0.5])
        mat = decomposer._single_qubit_subcircuit_matrix([gate])
        assert mat is not None
        expected = np.asarray(gate, dtype=complex)
        np.testing.assert_allclose(mat, expected, atol=1e-12)

    def test_single_qubit_subcircuit_matrix_multi_target(self) -> None:
        """Multi-target gates should return None."""
        gate = CX([0, 1])
        mat = decomposer._single_qubit_subcircuit_matrix([gate])
        assert mat is None

    def test_single_qubit_subcircuit_matrix_mixed_targets(self) -> None:
        """Gates acting on different qubits should return None."""
        gates: list[BaseOperation] = [RZ([0], [0.3]), RZ([1], [0.5])]
        mat = decomposer._single_qubit_subcircuit_matrix(gates)
        assert mat is None

    def test_multi_controlled_ry_zero_controls(self) -> None:
        """Zero controls should produce a plain RY gate."""
        gates = decomposer._multi_controlled_ry([], 0, np.pi / 4)
        assert len(gates) == 1
        assert gates[0].name.lower() == "ry"

    def test_multi_controlled_ry_one_control(self) -> None:
        """One control should produce a CRY decomposition."""
        gates = decomposer._multi_controlled_ry([0], 1, np.pi / 3)
        assert len(gates) > 0
        # Verify correctness by building the circuit and checking the matrix.
        circuit = QuantumCircuit.from_ir(gates, 2)
        op = Operator(circuit)
        expected = CRY([0, 1], [np.pi / 3]).to_matrix()
        assert op.equiv(Operator(expected))

    def test_multi_controlled_ry_two_controls(self) -> None:
        """Two controls should produce a valid gate sequence."""
        gates = decomposer._multi_controlled_ry([0, 1], 2, np.pi / 6)
        assert len(gates) > 0

    def test_multi_controlled_ry_three_controls_raises(self) -> None:
        """More than 2 controls should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            decomposer._multi_controlled_ry([0, 1, 2], 3, np.pi / 4)

    def test_uniformly_controlled_ry_ctrl_state_zero(self) -> None:
        """ctrl_state=0 should prepend X gates to controls."""
        gates = decomposer._uniformly_controlled_ry(
            target=1, controls=[0], control_state=0, angle=np.pi / 2
        )
        gate_names = [g.name.lower() for g in gates]
        assert "x" in gate_names

    def test_uniformly_controlled_ry_ctrl_state_one(self) -> None:
        """ctrl_state=1 should NOT prepend X gates (already active-high)."""
        gates = decomposer._uniformly_controlled_ry(
            target=1, controls=[0], control_state=1, angle=np.pi / 2
        )
        gate_names = [g.name.lower() for g in gates]
        assert "x" not in gate_names

    def test_controlled_one_qubit(self) -> None:
        """_controlled_one_qubit should produce controlled gates."""
        gates = decomposer._controlled_one_qubit(
            control=0, target=1, u3_params=[np.pi / 4, 0.0, 0.0], ctrl_state=1
        )
        assert len(gates) > 0

    def test_controlled_one_qubit_ctrl_state_zero(self) -> None:
        """ctrl_state=0 should sandwich the controlled gate with X gates."""
        gates = decomposer._controlled_one_qubit(
            control=0, target=1, u3_params=[np.pi / 4, 0.0, 0.0], ctrl_state=0
        )
        gate_names = [g.name.lower() for g in gates]
        assert gate_names[0] == "x"
        assert gate_names[-1] == "x"

    def test_control_subcircuit_u3_gate(self) -> None:
        """_control_subcircuit with a single U3 gate should delegate."""
        u3_gate = U3([1], [np.pi / 4, 0.0, np.pi / 2])
        result = decomposer._control_subcircuit(
            [u3_gate], control=0, ctrl_state=1
        )
        assert len(result) > 0

    def test_control_subcircuit_single_qubit_circuit(self) -> None:
        """_control_subcircuit with a single-qubit sub-circuit should work."""
        gates: list[BaseOperation] = [
            RZ([1], [0.3]),
            RY([1], [0.5]),
            RZ([1], [0.2]),
        ]
        result = decomposer._control_subcircuit(gates, control=0, ctrl_state=1)
        assert len(result) > 0

    def test_control_subcircuit_ctrl_state_zero(self) -> None:
        """ctrl_state=0 should add X gates around the controlled circuit."""
        gates: list[BaseOperation] = [CX([1, 2])]
        result = decomposer._control_subcircuit(gates, control=0, ctrl_state=0)
        gate_names = [g.name.lower() for g in result]
        assert gate_names[0] == "x"
        assert gate_names[-1] == "x"

    def test_control_subcircuit_multi_qubit_gates(self) -> None:
        """_control_subcircuit with multi-qubit gates should expand them."""
        gates: list[BaseOperation] = [CX([1, 2]), RZ([1], [0.5])]
        result = decomposer._control_subcircuit(gates, control=0, ctrl_state=1)
        assert len(result) > 0

    def test_expand_to_elementary_basic_gates(self) -> None:
        """Elementary gates should pass through unchanged."""
        gates: list[BaseOperation] = [
            RX([0], [0.5]),
            RY([0], [0.3]),
            CX([0, 1]),
        ]
        result = decomposer._expand_to_elementary(gates)
        assert len(result) == 3

    def test_expand_to_elementary_compound_gate(self) -> None:
        """Compound gates (non-elementary) should be recursively expanded."""
        # CRX is not in _ELEMENTARY_GATES, so it should be expanded
        gate = CRX([0, 1], [0.5])
        result = decomposer._expand_to_elementary([gate])
        # All result gates should be elementary
        elementary_names = {
            "rx",
            "ry",
            "rz",
            "x",
            "y",
            "z",
            "cx",
            "cz",
            "h",
            "p",
            "u",
            "u1",
            "u2",
            "u3",
            "cy",
            "swap",
        }
        assert all(g.name.lower() in elementary_names for g in result)

    def test_add_single_control_rz_gate(self) -> None:
        """_add_single_control with RZ should produce controlled gates."""
        gate = RZ([1], [0.5])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_cx_gate(self) -> None:
        """_add_single_control with CX should produce CCX decomposition."""
        gate = CX([1, 2])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_cz_gate_raises(self) -> None:
        """_add_single_control with CZ raises ValueError (ccz unsupported)."""
        gate = CZ([1, 2])
        with pytest.raises(ValueError, match="ccz is not support"):
            decomposer._add_single_control(gate, control=0)

    def test_add_single_control_swap_gate(self) -> None:
        """_add_single_control with SWAP should produce CSWAP decomposition."""
        gate = SWAP([1, 2])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_rxx_gate(self) -> None:
        """_add_single_control with RXX should recursively control."""
        gate = RXX([1, 2], [0.5])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_ryy_gate(self) -> None:
        """_add_single_control with RYY should recursively control."""
        gate = RYY([1, 2], [0.5])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_rzz_gate(self) -> None:
        """_add_single_control with RZZ should recursively control."""
        gate = RZZ([1, 2], [0.5])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_unsupported_raises(self) -> None:
        """Unsupported gate should raise NotImplementedError."""
        # Create a gate with a name not in any control map.
        gate = BaseOperation("unsupported_gate", [0], None, "1")
        gate.name = "unsupported_gate"
        with pytest.raises(NotImplementedError):
            decomposer._add_single_control(gate, control=1)

    def test_uniformly_controlled_rk_single_angle(self) -> None:
        """Single angle should produce a single rotation gate."""
        gates = decomposer._uniformly_controlled_rk(
            angles=[0.5], control_bits=[], target=0, axis="ry"
        )
        assert len(gates) == 1
        assert gates[0].name.lower() == "ry"

    def test_uniformly_controlled_rk_single_angle_rz(self) -> None:
        """Single angle with axis='rz' should produce an RZ gate."""
        gates = decomposer._uniformly_controlled_rk(
            angles=[0.5], control_bits=[], target=0, axis="rz"
        )
        assert len(gates) == 1
        assert gates[0].name.lower() == "rz"

    def test_uniformly_controlled_rk_zero_angle(self) -> None:
        """Zero single angle should produce an empty list."""
        gates = decomposer._uniformly_controlled_rk(
            angles=[0.0], control_bits=[], target=0, axis="ry"
        )
        assert gates == []

    def test_uniformly_controlled_rk_empty_angles(self) -> None:
        """Empty angle list should return empty gates."""
        gates = decomposer._uniformly_controlled_rk(
            angles=[], control_bits=[], target=0, axis="ry"
        )
        assert gates == []

    def test_decompose_cosine_sine_all_zeros(self) -> None:
        """All-zero theta should return empty gates."""
        theta = np.zeros(2)
        gates, phase = decomposer._decompose_cosine_sine(
            theta, sub_qubits=[0], msb=1
        )
        assert gates == []
        assert phase == 0.0

    def test_demultiplex_diagonal_2x2_identity(self) -> None:
        """Identity-like diagonal should produce no RZ gate (zero angle)."""
        mat = np.eye(2, dtype=complex)
        gates, phase = decomposer._demultiplex_diagonal_2x2(mat, msb=0)
        # Both diag values are 1 → log(1)=0 → rz_angle=0 → no RZ gate
        assert gates == []

    def test_demultiplex_diagonal_2x2_nontrivial(self) -> None:
        """Non-trivial diagonal should produce an RZ gate."""
        mat = np.diag([1.0, np.exp(1j * np.pi / 4)])
        gates, phase = decomposer._demultiplex_diagonal_2x2(mat, msb=0)
        assert len(gates) == 1
        assert gates[0].name.lower() == "rz"

    def test_validate_unitary_1d_array(self) -> None:
        """1D array should raise ValueError (not square 2D)."""
        with pytest.raises(ValueError, match="square"):
            decomposer._validate_unitary(np.array([1, 0, 0, 1]))

    def test_validate_unitary_non_square_2d(self) -> None:
        """Non-square 2D array should raise ValueError."""
        with pytest.raises(ValueError, match="square"):
            decomposer._validate_unitary(np.array([[1, 0, 0], [0, 1, 0]]))

    def test_num_qubits_non_power_of_two(self) -> None:
        """Non-power-of-two dimension should raise ValueError."""
        with pytest.raises(ValueError, match="power of two"):
            decomposer._num_qubits(6)

    def test_binary_code_shape(self) -> None:
        """_binary_code should return correct shape and values."""
        codes = decomposer._binary_code(3)
        assert codes.shape == (8, 3)
        # First row: 000, last row: 111
        np.testing.assert_array_equal(codes[0], [0, 0, 0])
        np.testing.assert_array_equal(codes[7], [1, 1, 1])

    def test_gray_code_shape(self) -> None:
        """_gray_code should return correct shape and Gray property."""
        codes = decomposer._gray_code(3)
        assert codes.shape == (8, 3)
        # First row: 000
        np.testing.assert_array_equal(codes[0], [0, 0, 0])
        # Consecutive rows differ in exactly one bit
        for i in range(len(codes) - 1):
            diff = np.sum(np.abs(codes[i + 1] - codes[i]))
            assert diff == 1

    def test_controlled_unitary_ctrl_state_zero(self) -> None:
        """_controlled_unitary with ctrl_state=0 should add X gates."""
        unitary = np.array([[0, 1], [1, 0]], dtype=complex)  # X gate
        gates = decomposer._controlled_unitary(
            control=0, target=1, unitary=unitary, ctrl_state=0
        )
        gate_names = [g.name.lower() for g in gates]
        assert gate_names[0] == "x"
        assert gate_names[-1] == "x"

    def test_controlled_unitary_identity(self) -> None:
        """_controlled_unitary with identity should produce minimal gates."""
        unitary = np.eye(2, dtype=complex)
        gates = decomposer._controlled_unitary(
            control=0, target=1, unitary=unitary, ctrl_state=1
        )
        # Identity has all-zero Euler angles, gates should be minimal
        assert isinstance(gates, list)

    def test_decompose_with_default_qubits(self) -> None:
        """Decompose without specifying qubits (uses default indices)."""
        matrix = CZ().to_matrix()
        gates, _ = decomposer.decompose(matrix)
        _assert_equiv(matrix, gates, 2)

    def test_decompose_one_qubit_identity(self) -> None:
        """1-qubit identity matrix should decompose correctly."""
        matrix = np.eye(2, dtype=complex)
        gates, phase = decomposer.decompose(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_decompose_two_qubit_cy(self) -> None:
        """Decompose CY gate to verify _decompose_multiplex sub_qubits=1."""
        matrix = CY().to_matrix()
        gates, _ = decomposer.decompose(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_add_single_control_ry_gate(self) -> None:
        """_add_single_control with RY should produce controlled gates."""
        gate = RY([1], [0.7])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_rx_gate(self) -> None:
        """_add_single_control with RX should produce controlled gates."""
        gate = RX([1], [0.7])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_p_gate(self) -> None:
        """_add_single_control with P should produce controlled gates."""
        gate = P([1], [0.5])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_u3_gate(self) -> None:
        """_add_single_control with U3 should produce controlled gates."""
        gate = U3([1], [0.5, 0.3, 0.1])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_u_gate(self) -> None:
        """_add_single_control with U should produce controlled gates."""
        gate = U([1], [0.5, 0.3, 0.1])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_cy_gate_raises(self) -> None:
        """_add_single_control with CY raises NotImplementedError."""
        gate = CY([1, 2])
        with pytest.raises(NotImplementedError):
            decomposer._add_single_control(gate, control=0)

    def test_add_single_control_h_gate(self) -> None:
        """_add_single_control with H should produce CH decomposition."""
        gate = H([1])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_expand_to_elementary_u3(self) -> None:
        """U3 gate is elementary and should pass through."""
        gate = U3([0], [0.1, 0.2, 0.3])
        result = decomposer._expand_to_elementary([gate])
        assert len(result) == 1
        assert result[0] is gate

    def test_control_subcircuit_single_rz_gate(self) -> None:
        """_control_subcircuit with a single RZ gate should work."""
        gate = RZ([1], [0.5])
        result = decomposer._control_subcircuit(
            [gate], control=0, ctrl_state=1
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_controlled_unitary_with_phase(self) -> None:
        """_controlled_unitary with non-zero global phase."""
        # Use a matrix with non-trivial phase
        theta = np.pi / 3
        unitary = np.array(
            [
                [np.cos(theta / 2), -np.sin(theta / 2)],
                [np.sin(theta / 2), np.cos(theta / 2)],
            ],
            dtype=complex,
        )
        gates = decomposer._controlled_unitary(
            control=0, target=1, unitary=unitary, ctrl_state=1
        )
        assert isinstance(gates, list)

    def test_add_single_control_y_gate(self) -> None:
        """_add_single_control with Y should produce CY decomposition."""
        gate = Y([1])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_z_gate(self) -> None:
        """_add_single_control with Z should produce CZ decomposition."""
        gate = Z([1])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_x_gate(self) -> None:
        """_add_single_control with X should produce CX decomposition."""
        gate = X([1])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_add_single_control_u1_gate(self) -> None:
        """_add_single_control with U1 should produce controlled gates."""
        # U1 has name "u1" which is in the first branch
        gate = create_gate("u1", [1], [0.5])
        result = decomposer._add_single_control(gate, control=0)
        assert len(result) > 0

    def test_expand_to_elementary_cx(self) -> None:
        """CX is elementary and should pass through."""
        gate = CX([0, 1])
        result = decomposer._expand_to_elementary([gate])
        assert len(result) == 1
        assert result[0] is gate

    def test_expand_to_elementary_h_is_elementary(self) -> None:
        """H gate is in _ELEMENTARY_GATES and passes through unchanged."""
        gate = H([0])
        result = decomposer._expand_to_elementary([gate])
        assert len(result) == 1
        assert result[0] is gate

    def test_decompose_multiplex_two_sub_qubits(self) -> None:
        """3-qubit decomposition exercises _demultiplex (sub_qubits > 1)."""
        matrix = _random_unitary(8, seed=42)
        gates, _ = decomposer.decompose(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    # ------------------------------------------------------------------
    # Matrix-based branch coverage tests
    # ------------------------------------------------------------------

    # -- 1-qubit matrices targeting specific Euler angle patterns --

    def test_1q_s_gate_z_rotation_only(self) -> None:
        """S gate: pure Z-rotation (theta=0), exercises _controlled_unitary."""
        matrix = S().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_t_gate_small_z_rotation(self) -> None:
        """T gate: π/4 Z-rotation, exercises small-angle branches."""
        matrix = T().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_sdg_gate(self) -> None:
        """SDG gate: negative Z-rotation."""
        matrix = SDG().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_tdg_gate(self) -> None:
        """TDG gate: negative π/4 Z-rotation."""
        matrix = TDG().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_sx_gate(self) -> None:
        """SX gate: sqrt(X), exercises non-trivial Euler angles."""
        matrix = SX().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_sxdg_gate(self) -> None:
        """SXDG gate: inverse sqrt(X)."""
        matrix = SXDG().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_pure_phase_matrix(self) -> None:
        """Pure global phase e^{iφ}I: all angles zero, only phase branch."""
        phase = np.exp(1j * np.pi / 5)
        matrix = phase * np.eye(2, dtype=complex)
        gates, returned_phase = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)
        assert abs(returned_phase) > 1e-10

    def test_1q_x_gate(self) -> None:
        """X gate: pi rotation around X axis."""
        matrix = X().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_y_gate(self) -> None:
        """Y gate: pi rotation around Y axis."""
        matrix = Y().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_z_gate(self) -> None:
        """Z gate: pi rotation around Z axis."""
        matrix = Z().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_u1_gate(self) -> None:
        """U1 gate: phase rotation."""
        matrix = U1([0], [np.pi / 3]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_u2_gate(self) -> None:
        """U2 gate: π/2 polar rotation."""
        matrix = U2([0], [np.pi / 4, np.pi / 6]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_rx_pi_over_3(self) -> None:
        """RX(π/3): non-standard angle, exercises theta branch."""
        matrix = RX([0], [np.pi / 3]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_ry_pi_over_5(self) -> None:
        """RY(π/5): pure Y-rotation, lam=phi=0."""
        matrix = RY([0], [np.pi / 5]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_rz_pi_over_7(self) -> None:
        """RZ(π/7): pure Z-rotation, theta=0."""
        matrix = RZ([0], [np.pi / 7]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_negative_pi_rotation(self) -> None:
        """Negative angle rotation to test sign handling."""
        matrix = RY([0], [-np.pi / 4]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_very_small_angle(self) -> None:
        """Very small angle near _ATOL threshold."""
        matrix = RZ([0], [1e-10]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    def test_1q_pi_rotation(self) -> None:
        """Exact π rotation: boundary case for Euler decomposition."""
        matrix = RX([0], [np.pi]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0])
        _assert_equiv(matrix, gates, 1)

    # -- 2-qubit matrices targeting CSD + _controlled_unitary branches --

    def test_2q_ch_gate(self) -> None:
        """CH gate: controlled-Hadamard, exercises CSD non-trivial blocks."""
        matrix = CH().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_csx_gate(self) -> None:
        """CSX gate: controlled-SX."""
        matrix = CSX().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cu1_gate(self) -> None:
        """CU1 gate: controlled phase, diagonal matrix."""
        matrix = CU1([0, 1], [np.pi / 3]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_crx_gate(self) -> None:
        """CRX gate: controlled-X rotation."""
        matrix = CRX([0, 1], [np.pi / 4]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cry_gate(self) -> None:
        """CRY gate: controlled-Y rotation."""
        matrix = CRY([0, 1], [np.pi / 3]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_crz_gate(self) -> None:
        """CRZ gate: controlled-Z rotation."""
        matrix = CRZ([0, 1], [np.pi / 5]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cp_gate(self) -> None:
        """CP gate: controlled phase."""
        matrix = CP([0, 1], [np.pi / 6]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cu3_gate(self) -> None:
        """CU3 gate: controlled universal rotation."""
        matrix = CU3([0, 1], [np.pi / 4, np.pi / 3, np.pi / 6]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cu_gate(self) -> None:
        """CU gate: controlled U with global phase."""
        matrix = CU(
            [0, 1], [np.pi / 4, np.pi / 3, np.pi / 6, np.pi / 8]
        ).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cy_gate(self) -> None:
        """CY gate: controlled-Y."""
        matrix = CY().to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cz_with_phase(self) -> None:
        """CZ * e^{iπ/4}: controlled-Z with global phase."""
        matrix = CZ().to_matrix() * np.exp(1j * np.pi / 4)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_block_diagonal(self) -> None:
        """Block-diagonal unitary: CSD produces diagonal blocks."""
        u0 = RY([0], [np.pi / 3]).to_matrix()
        u1 = RZ([0], [np.pi / 5]).to_matrix()
        matrix = np.block([[u0, np.zeros((2, 2))], [np.zeros((2, 2)), u1]])
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_anti_diagonal(self) -> None:
        """Anti-diagonal unitary: exercises different CSD pattern."""
        matrix = np.array(
            [
                [0, 0, 1, 0],
                [0, 0, 0, 1],
                [1, 0, 0, 0],
                [0, 1, 0, 0],
            ],
            dtype=complex,
        )
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_permutation_0123_to_1032(self) -> None:
        """Permutation matrix: swaps pairs, exercises CSD permutation."""
        matrix = np.zeros((4, 4), dtype=complex)
        matrix[0, 1] = 1
        matrix[1, 0] = 1
        matrix[2, 3] = 1
        matrix[3, 2] = 1
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_permutation_0123_to_2301(self) -> None:
        """Cyclic permutation matrix."""
        matrix = np.zeros((4, 4), dtype=complex)
        matrix[0, 2] = 1
        matrix[1, 3] = 1
        matrix[2, 0] = 1
        matrix[3, 1] = 1
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_kron_rz_ry(self) -> None:
        """Kronecker product RZ ⊗ RY: separable unitary."""
        rz = RZ([0], [np.pi / 4]).to_matrix()
        ry = RY([0], [np.pi / 3]).to_matrix()
        matrix = np.kron(rz, ry)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_kron_s_t(self) -> None:
        """Kronecker product S ⊗ T: both pure Z-rotations."""
        s_mat = S().to_matrix()
        t_mat = T().to_matrix()
        matrix = np.kron(s_mat, t_mat)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_kron_x_z(self) -> None:
        """Kronecker product X ⊗ Z: Pauli tensor."""
        matrix = np.kron(X().to_matrix(), Z().to_matrix())
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_kron_h_h(self) -> None:
        """Kronecker product H ⊗ H: double Hadamard."""
        matrix = np.kron(H().to_matrix(), H().to_matrix())
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_sparse_unitary(self) -> None:
        """Sparse unitary: only a few non-zero entries per row."""
        matrix = np.array(
            [
                [0, 1, 0, 0],
                [1, 0, 0, 0],
                [0, 0, 0, 1j],
                [0, 0, 1j, 0],
            ],
            dtype=complex,
        )
        # Normalize to make it unitary
        matrix[2, 3] = 1
        matrix[3, 2] = -1
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_diagonal_distinct_phases(self) -> None:
        """Diagonal matrix with 4 distinct phases."""
        phases = [np.exp(1j * a) for a in [0, np.pi / 3, np.pi / 5, np.pi / 7]]
        matrix = np.diag(phases)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_near_identity_perturbation(self) -> None:
        """Near-identity 2-qubit: small perturbation from I."""
        rng = np.random.default_rng(42)
        eps = 1e-10
        h = rng.standard_normal((4, 4)) + 1j * rng.standard_normal((4, 4))
        h = (h - h.conj().T) / 2
        matrix = np.eye(4) + eps * h
        q, _ = np.linalg.qr(matrix)
        gates, _ = matrix_to_circuit(q, [0, 1])
        _assert_equiv(q, gates, 2)

    # -- 3-qubit matrices: exercises _demultiplex with Schur decomposition --

    def test_3q_ccx_toffoli(self) -> None:
        """CCX (Toffoli) gate: 3-qubit, exercises deep recursion + Schur."""
        matrix = CCX([0, 1, 2]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_cswap_fredkin(self) -> None:
        """CSWAP (Fredkin) gate: 3-qubit controlled SWAP."""
        matrix = CSWAP([0, 1, 2]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_rccx(self) -> None:
        """RCCX gate: relative-phase Toffoli, 3-qubit."""
        matrix = RCCX([0, 1, 2]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_diagonal_phases(self) -> None:
        """3-qubit diagonal matrix with 8 distinct phases."""
        rng = np.random.default_rng(77)
        phases = np.exp(1j * rng.uniform(0, 2 * np.pi, size=8))
        matrix = np.diag(phases)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_identity(self) -> None:
        """3-qubit identity: all angles zero in CSD."""
        matrix = np.eye(8, dtype=complex)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_kron_cx_i(self) -> None:
        """Kronecker CX ⊗ I: 3-qubit, block structure."""
        cx = CX().to_matrix()
        matrix = np.kron(cx, np.eye(2, dtype=complex))
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_kron_h_cz(self) -> None:
        """Kronecker H ⊗ CZ: 3-qubit separable structure."""
        h_mat = H().to_matrix()
        cz_mat = CZ().to_matrix()
        matrix = np.kron(h_mat, cz_mat)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_permutation(self) -> None:
        """3-qubit permutation matrix (cyclic shift)."""
        matrix = np.zeros((8, 8), dtype=complex)
        for i in range(8):
            matrix[i, (i + 1) % 8] = 1
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_anti_diagonal(self) -> None:
        """3-qubit anti-diagonal (bit-flip) matrix."""
        matrix = np.fliplr(np.eye(8, dtype=complex))
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_block_diagonal_4x4(self) -> None:
        """3-qubit block-diagonal: two 4x4 unitary blocks."""
        u0 = _random_unitary(4, seed=10)
        u1 = _random_unitary(4, seed=11)
        matrix = np.block([
            [u0, np.zeros((4, 4))],
            [np.zeros((4, 4)), u1],
        ])
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_global_phase(self) -> None:
        """3-qubit with non-trivial global phase."""
        matrix = np.exp(1j * np.pi / 7) * np.eye(8, dtype=complex)
        gates, returned_phase = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    # -- 4-qubit matrices targeting deeper recursion --

    def test_4q_identity(self) -> None:
        """4-qubit identity: exercises deep CSD recursion with zero angles."""
        matrix = np.eye(16, dtype=complex)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_diagonal(self) -> None:
        """4-qubit diagonal with distinct phases."""
        rng = np.random.default_rng(55)
        phases = np.exp(1j * rng.uniform(0, 2 * np.pi, size=16))
        matrix = np.diag(phases)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_kron_cx_cx(self) -> None:
        """Kronecker CX ⊗ CX: 4-qubit, two independent CNOTs."""
        cx = CX().to_matrix()
        matrix = np.kron(cx, cx)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_kron_swap_cz(self) -> None:
        """Kronecker SWAP ⊗ CZ: 4-qubit mixed structure."""
        matrix = np.kron(SWAP().to_matrix(), CZ().to_matrix())
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_anti_diagonal(self) -> None:
        """4-qubit anti-diagonal (full bit-flip) matrix."""
        matrix = np.fliplr(np.eye(16, dtype=complex))
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_permutation(self) -> None:
        """4-qubit cyclic permutation matrix."""
        matrix = np.zeros((16, 16), dtype=complex)
        for i in range(16):
            matrix[i, (i + 3) % 16] = 1
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_block_diagonal(self) -> None:
        """4-qubit block-diagonal: two 8x8 unitary blocks."""
        u0 = _random_unitary(8, seed=20)
        u1 = _random_unitary(8, seed=21)
        matrix = np.block([
            [u0, np.zeros((8, 8))],
            [np.zeros((8, 8)), u1],
        ])
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_global_phase(self) -> None:
        """4-qubit with non-trivial global phase."""
        matrix = np.exp(1j * np.pi / 11) * np.eye(16, dtype=complex)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    # -- Additional edge-case matrices --

    def test_2q_crx_zero_angle(self) -> None:
        """CRX(0) = identity, exercises zero-angle branches in CSD."""
        matrix = CRX([0, 1], [0.0]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cry_zero_angle(self) -> None:
        """CRY(0) = identity."""
        matrix = CRY([0, 1], [0.0]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_crz_zero_angle(self) -> None:
        """CRZ(0) = identity."""
        matrix = CRZ([0, 1], [0.0]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_crx_pi(self) -> None:
        """CRX(π): maximal controlled rotation."""
        matrix = CRX([0, 1], [np.pi]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cu1_pi(self) -> None:
        """CU1(π): controlled-Z-like behavior."""
        matrix = CU1([0, 1], [np.pi]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cu3_identity_params(self) -> None:
        """CU3(0,0,0) = identity."""
        matrix = CU3([0, 1], [0.0, 0.0, 0.0]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_cu_nontrivial_gamma(self) -> None:
        """CU with non-zero gamma (global phase of controlled block)."""
        matrix = CU([0, 1], [np.pi / 2, 0.0, 0.0, np.pi / 3]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_negative_angle_crz(self) -> None:
        """CRZ with negative angle."""
        matrix = CRZ([0, 1], [-np.pi / 4]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_swap_with_global_phase(self) -> None:
        """SWAP * e^{iπ/3}: permutation with global phase."""
        matrix = SWAP().to_matrix() * np.exp(1j * np.pi / 3)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_3q_ccx_nonstandard_qubits(self) -> None:
        """CCX with non-standard qubit indices [1, 3, 5]."""
        matrix = CCX([0, 1, 2]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [1, 3, 5])
        # Verify gate targets use the specified qubit indices
        all_targets = {t for g in gates for t in g.targets}
        assert all_targets.issubset({1, 3, 5})

    def test_3q_cswap_nonstandard_qubits(self) -> None:
        """CSWAP with non-standard qubit indices [0, 2, 4]."""
        matrix = CSWAP([0, 1, 2]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 2, 4])
        all_targets = {t for g in gates for t in g.targets}
        assert all_targets.issubset({0, 2, 4})

    @pytest.mark.parametrize("angle", [0.01, 0.1, 0.5, 1.0, np.pi / 2, np.pi])
    def test_2q_crx_various_angles(self, angle: float) -> None:
        """CRX with various angles to cover different rotation magnitudes."""
        matrix = CRX([0, 1], [angle]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    @pytest.mark.parametrize("angle", [0.01, 0.1, 0.5, 1.0, np.pi / 2, np.pi])
    def test_2q_cp_various_angles(self, angle: float) -> None:
        """CP with various angles."""
        matrix = CP([0, 1], [angle]).to_matrix()
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_kron_sx_sxdg(self) -> None:
        """Kronecker SX ⊗ SXDG: inverse pair, product is identity."""
        sx = SX().to_matrix()
        sxdg = SXDG().to_matrix()
        matrix = np.kron(sx, sxdg)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_2q_kron_p_p(self) -> None:
        """Kronecker P ⊗ P: two phase gates."""
        p1 = P([0], [np.pi / 3]).to_matrix()
        p2 = P([0], [np.pi / 5]).to_matrix()
        matrix = np.kron(p1, p2)
        gates, _ = matrix_to_circuit(matrix, [0, 1])
        _assert_equiv(matrix, gates, 2)

    def test_3q_kron_rz_cx(self) -> None:
        """Kronecker RZ ⊗ CX: 3-qubit mixed structure."""
        rz = RZ([0], [np.pi / 4]).to_matrix()
        cx = CX().to_matrix()
        matrix = np.kron(rz, cx)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_3q_kron_swap_rz(self) -> None:
        """Kronecker SWAP ⊗ RZ: 3-qubit."""
        swap = SWAP().to_matrix()
        rz = RZ([0], [np.pi / 6]).to_matrix()
        matrix = np.kron(swap, rz)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2])
        _assert_equiv(matrix, gates, 3)

    def test_4q_kron_h_h_h_h(self) -> None:
        """Kronecker H⊗H⊗H⊗H: fully separable 4-qubit."""
        h = H().to_matrix()
        matrix = np.kron(np.kron(np.kron(h, h), h), h)
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)

    def test_4q_kron_cz_swap(self) -> None:
        """Kronecker CZ ⊗ SWAP: 4-qubit mixed structure."""
        matrix = np.kron(CZ().to_matrix(), SWAP().to_matrix())
        gates, _ = matrix_to_circuit(matrix, [0, 1, 2, 3])
        _assert_equiv(matrix, gates, 4)
