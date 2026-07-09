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

import pytest
import numpy as np
import stim

from wy_qcos.qec.shor_code import (
    ShorStrategy,
    ShorStimStrategy,
    ShorQuantumCircuitStrategy,
    ShorCode,
)
from wy_qcos.qec.quantum_code_base import QuantumCodeBase
from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.common.cmss.gate_operation import H, X, Z


# ===========================================================================
# Test ShorStrategy (Base)
# ===========================================================================
class TestShorStrategy:
    """Test base ShorStrategy class."""

    def test_initialization(self):
        """Test ShorStrategy initialization."""
        strategy = ShorStrategy()
        assert strategy is not None

    def test_get_stabilizers(self):
        """Test get_stabilizers returns correct stabilizers."""
        strategy = ShorStrategy()
        stabilizers = strategy.get_stabilizers()
        assert "Z" in stabilizers
        assert "X" in stabilizers
        assert stabilizers["Z"] == [
            (0, 1),
            (1, 2),
            (3, 4),
            (4, 5),
            (6, 7),
            (7, 8),
        ]
        assert stabilizers["X"] == [(0, 3, 6), (1, 4, 7), (2, 5, 8)]

    def test_get_stabilizers_length(self):
        """Test stabilizer lengths."""
        strategy = ShorStrategy()
        stabilizers = strategy.get_stabilizers()
        # 6 Z stabilizers and 3 X stabilizers
        assert len(stabilizers["Z"]) == 6
        assert len(stabilizers["X"]) == 3

    def test_validate_and_format_circuit_raises_not_implemented(self):
        """Test validate_and_format_circuit raises NotImplementedError."""
        strategy = ShorStrategy()
        with pytest.raises(NotImplementedError):
            strategy.validate_and_format_circuit("circuit")

    def test_encode_raises_not_implemented(self):
        """Test that base encode raises NotImplementedError."""
        strategy = ShorStrategy()
        with pytest.raises(NotImplementedError):
            strategy.encode("circuit")

    def test_decode_raises_not_implemented(self):
        """Test that base decode raises NotImplementedError."""
        strategy = ShorStrategy()
        with pytest.raises(NotImplementedError):
            strategy.decode()

    def test_correct_raises_not_implemented(self):
        """Test that base correct raises NotImplementedError."""
        strategy = ShorStrategy()
        with pytest.raises(NotImplementedError):
            strategy.correct()

    def test_compute_samples_raises_not_implemented(self):
        """Test that base compute_samples raises NotImplementedError."""
        strategy = ShorStrategy()
        with pytest.raises(NotImplementedError):
            strategy.compute_samples([])


# ===========================================================================
# Test ShorStimStrategy
# ===========================================================================
class TestShorStimStrategy:
    """Test ShorStimStrategy class."""

    def test_initialization(self):
        """Test ShorStimStrategy initialization."""
        strategy = ShorStimStrategy()
        assert strategy is not None
        assert strategy.syndrome == []
        assert strategy.raw_bits == []

    def test_validate_and_format_circuit_with_single_qubit_gate(self):
        """Test validate_and_format_circuit with a single-qubit gate."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        result = strategy.validate_and_format_circuit(circuit)
        assert isinstance(result, stim.Circuit)
        assert result == circuit

    def test_validate_and_format_circuit_with_empty_circuit(self):
        """Test validate_and_format_circuit with an empty circuit."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        result = strategy.validate_and_format_circuit(circuit)
        assert isinstance(result, stim.Circuit)

    def test_validate_and_format_circuit_with_multi_qubit_gate_raises_error(
        self,
    ):
        """Test that multi-qubit gate raises ValueError."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("CX", [0, 1])
        with pytest.raises(ValueError) as exc_info:
            strategy.validate_and_format_circuit(circuit)
        assert "multi-qubit" in str(exc_info.value).lower()

    def test_encode_returns_circuit(self):
        """Test encode returns a stim.Circuit."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)

    def test_encode_adds_operations(self):
        """Test encode adds operations to the circuit."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(circuit)
        # Encoded circuit should have more operations than input
        assert len(encoded) > len(circuit)

    def test_encode_with_x_gate(self):
        """Test encoding with logical X gate."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        # Should contain Z operations on logical qubits
        encoded_str = str(encoded)
        assert "Z" in encoded_str

    def test_encode_with_z_gate(self):
        """Test encoding with logical Z gate."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("Z", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        assert "X" in encoded_str

    def test_encode_with_y_gate(self):
        """Test encoding with logical Y gate."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("Y", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        assert "Z" in encoded_str
        assert "X" in encoded_str

    def test_encode_with_h_gate_raises_error(self):
        """Test that logical H gate raises ValueError."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("H", [0])
        with pytest.raises(ValueError) as exc_info:
            strategy.encode(circuit)
        assert "non-transversal" in str(exc_info.value).lower()

    def test_encode_with_s_gate(self):
        """Test encoding with logical S gate."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("S", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        assert "S" in encoded_str

    def test_encode_with_unsupported_gate_raises_error(self):
        """Test that unsupported gate raises ValueError."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("Z_ERROR", [0], 0.01)
        with pytest.raises(ValueError) as exc_info:
            strategy.encode(circuit)
        assert "unsupported" in str(exc_info.value).lower()

    def test_encode_with_x_error_inject(self):
        """Test encode with x_error injection type."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(
            circuit,
            error_inject={"error_type": "x_error", "noise_prob": 0.05},
        )
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        assert "X_ERROR" in encoded_str

    def test_encode_with_y_error_inject(self):
        """Test encode with y_error injection type."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(
            circuit,
            error_inject={"error_type": "y_error", "noise_prob": 0.02},
        )
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        assert "Y_ERROR" in encoded_str

    def test_encode_with_z_error_inject(self):
        """Test encode with z_error injection type."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(
            circuit,
            error_inject={"error_type": "z_error", "noise_prob": 0.03},
        )
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        assert "Z_ERROR" in encoded_str

    def test_encode_with_depolarize_error_inject(self):
        """Test encode with depolarize error_inject type."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(
            circuit,
            error_inject={"error_type": "depolarize", "noise_prob": 0.01},
        )
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        # depolarize should inject DEPOLARIZE1
        assert "DEPOLARIZE1" in encoded_str

    def test_encode_with_unsupported_error_inject_raises_error(self):
        """Test that unsupported error_inject type raises ValueError."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        with pytest.raises(ValueError) as exc_info:
            strategy.encode(
                circuit,
                error_inject={
                    "error_type": "unsupported_error",
                    "noise_prob": 0.01,
                },
            )
        assert "unsupported" in str(exc_info.value).lower()

    def test_encode_with_custom_noise_prob(self):
        """Test encode with custom noise_prob."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(
            circuit,
            error_inject={"error_type": "x_error", "noise_prob": 0.5},
        )
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        assert "X_ERROR" in encoded_str
        assert "0.5" in encoded_str

    def test_encode_without_error_inject(self):
        """Test encode without error_inject."""
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        encoded_str = str(encoded)
        # Default behavior: x_error with 0.01 probability
        assert "X_ERROR" in encoded_str
        assert "0.01" in encoded_str

    def test_correct_without_err_pos_returns_none(self):
        """Test correct with no err_pos returns None."""
        strategy = ShorStimStrategy()
        result = strategy.correct()
        assert result is None

    def test_correct_with_1d_raw_bits(self):
        """Test correct with 1D raw_bits."""
        strategy = ShorStimStrategy()
        strategy.raw_bits = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        err_pos = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.correct(err_pos=err_pos)
        expected = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        assert np.array_equal(result, expected)

    def test_correct_with_2d_raw_bits(self):
        """Test correct with 2D raw_bits."""
        strategy = ShorStimStrategy()
        strategy.raw_bits = [
            [1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0, 0],
        ]
        err_pos = [
            [1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0, 0],
        ]
        result = strategy.correct(err_pos=err_pos)
        expected = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        assert np.array_equal(result, expected)

    def test_correct_no_error(self):
        """Test correct when there is no error."""
        strategy = ShorStimStrategy()
        strategy.raw_bits = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        err_pos = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.correct(err_pos=err_pos)
        assert np.array_equal(result, [0, 0, 0, 0, 0, 0, 0, 0, 0])

    def test_decode_with_1d_syndrome(self):
        """Test decode with 1D syndrome (no errors)."""
        strategy = ShorStimStrategy()
        strategy.syndrome = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.decode()
        expected = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        assert np.array_equal(result, expected)

    def test_decode_with_1d_syndrome_and_error_block0(self):
        """Test decode with error in block 0."""
        strategy = ShorStimStrategy()
        # Z stabilizers: s0=1, s1=0 indicates error on qubit 0 in block 0
        strategy.syndrome = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.decode()
        assert result[0] == 1

    def test_decode_with_1d_syndrome_and_error_block0_pos1(self):
        """Test decode with error at position 1 in block 0."""
        strategy = ShorStimStrategy()
        # Z stabilizers: s0=1, s1=1 indicates error on qubit 1 in block 0
        strategy.syndrome = [1, 1, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.decode()
        assert result[1] == 1

    def test_decode_with_1d_syndrome_and_error_block0_pos2(self):
        """Test decode with error at position 2 in block 0."""
        strategy = ShorStimStrategy()
        # Z stabilizers: s0=0, s1=1 indicates error on qubit 2 in block 0
        strategy.syndrome = [0, 1, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.decode()
        assert result[2] == 1

    def test_decode_with_2d_syndrome(self):
        """Test decode with 2D syndrome."""
        strategy = ShorStimStrategy()
        strategy.syndrome = [
            [1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0, 0],
        ]
        result = strategy.decode()
        assert result.shape == (2, 9)

    def test_logical_measure_with_1d_bits(self):
        """Test logical_measure with 1D bits."""
        strategy = ShorStimStrategy()
        bits = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.logical_measure(bits)
        assert result == 1

    def test_logical_measure_with_2d_bits(self):
        """Test logical_measure with 2D bits."""
        strategy = ShorStimStrategy()
        bits = [
            [1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        result = strategy.logical_measure(bits)
        assert np.array_equal(result, [1, 0])

    def test_logical_measure_with_zero_bits(self):
        """Test logical_measure with all zero bits."""
        strategy = ShorStimStrategy()
        bits = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        result = strategy.logical_measure(bits)
        assert result == 0

    def test_compute_samples_with_1d_samples(self):
        """Test compute_samples with 1D samples."""
        strategy = ShorStimStrategy()
        samples = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        strategy.compute_samples(samples)
        # After np.atleast_2d, 1D samples become shape (1, 18)
        # syndrome is concatenated z_syn + x_syn with shape (1, 9)
        assert strategy.syndrome.shape == (1, 9)
        assert strategy.raw_bits.shape == (1, 9)

    def test_compute_samples_with_2d_samples(self):
        """Test compute_samples with 2D samples."""
        strategy = ShorStimStrategy()
        samples = [
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        strategy.compute_samples(samples)
        # syndrome should have shape (2, 9)
        assert isinstance(strategy.syndrome, np.ndarray)
        assert strategy.syndrome.shape == (2, 9)
        assert strategy.raw_bits.shape == (2, 9)

    def test_full_encode_decode_correct_cycle(self):
        """Test the full cycle: compute_samples -> decode -> correct."""
        strategy = ShorStimStrategy()
        # Simulate samples from encoding with a bit-flip on qubit 0
        # z_syn for block 0 (error on qubit 0): s0=1, s1=0
        # other syndromes all 0
        samples = [[1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]]
        strategy.compute_samples(samples)
        err_pos = strategy.decode()
        assert err_pos[0, 0] == 1  # qubit 0 has error
        corrected = strategy.correct(err_pos=err_pos)
        assert corrected[0, 0] == 0  # qubit 0 corrected to 0


# ===========================================================================
# Test ShorQuantumCircuitStrategy
# ===========================================================================
class TestShorQuantumCircuitStrategy:
    """Test ShorQuantumCircuitStrategy class."""

    def test_initialization(self):
        """Test ShorQuantumCircuitStrategy initialization."""
        strategy = ShorQuantumCircuitStrategy()
        assert strategy is not None

    def test_validate_and_format_circuit_with_single_qubit_gate(self):
        """Test validate_and_format_circuit with single-qubit GateOperation."""
        strategy = ShorQuantumCircuitStrategy()
        circuit = [H(targets=[0])]
        result = strategy.validate_and_format_circuit(circuit)
        assert len(result) == 1
        assert result[0].name == "h"

    def test_validate_and_format_circuit_with_multiple_gates(self):
        """Test validate_and_format_circuit with multiple gates."""
        strategy = ShorQuantumCircuitStrategy()
        circuit = [H(targets=[0]), X(targets=[1]), Z(targets=[2])]
        result = strategy.validate_and_format_circuit(circuit)
        assert len(result) == 3

    def test_validate_and_format_circuit_with_multi_qubit_gate_raises_error(
        self,
    ):
        """Test that multi-qubit gate raises ValueError."""
        strategy = ShorQuantumCircuitStrategy()
        from wy_qcos.common.cmss.gate_operation import CX

        circuit = [CX(targets=[0, 1])]
        with pytest.raises(ValueError) as exc_info:
            strategy.validate_and_format_circuit(circuit)
        assert "unexpected" in str(exc_info.value).lower()

    def test_validate_and_format_circuit_empty(self):
        """Test validate_and_format_circuit with empty list."""
        strategy = ShorQuantumCircuitStrategy()
        result = strategy.validate_and_format_circuit([])
        assert result == []

    def test_validate_and_format_circuit_filters_non_gate_operations(self):
        """Test that non-GateOperation objects are filtered out."""
        strategy = ShorQuantumCircuitStrategy()
        from wy_qcos.common.cmss.measure import Measure

        circuit = [H(targets=[0]), Measure(targets=[0])]
        result = strategy.validate_and_format_circuit(circuit)
        assert len(result) == 1
        assert result[0].name == "h"

    def test_encode_raises_not_implemented(self):
        """Test that encode raises NotImplementedError."""
        strategy = ShorQuantumCircuitStrategy()
        with pytest.raises(NotImplementedError):
            strategy.encode("circuit")

    def test_correct_raises_not_implemented(self):
        """Test that correct raises NotImplementedError."""
        strategy = ShorQuantumCircuitStrategy()
        with pytest.raises(NotImplementedError):
            strategy.correct()

    def test_decode_raises_not_implemented(self):
        """Test that decode raises NotImplementedError."""
        strategy = ShorQuantumCircuitStrategy()
        with pytest.raises(NotImplementedError):
            strategy.decode()

    def test_logical_measure_raises_not_implemented(self):
        """Test that logical_measure raises NotImplementedError."""
        strategy = ShorQuantumCircuitStrategy()
        with pytest.raises(NotImplementedError):
            strategy.logical_measure([])


# ===========================================================================
# Test ShorCode
# ===========================================================================
class TestShorCode:
    """Test ShorCode class."""

    def test_initialization(self):
        """Test ShorCode initialization."""
        code = ShorCode()
        assert isinstance(code, QuantumCodeBase)
        assert code._name == "ShorCode"

    def test_strategies_class_variable(self):
        """Test that strategies class variable exists and is a dict."""
        assert isinstance(ShorCode.strategies, dict)
        assert stim.Circuit in ShorCode.strategies
        assert list[BaseOperation] in ShorCode.strategies

    def test_strategies_are_correct_types(self):
        """Test that strategies map to correct types."""
        assert isinstance(ShorCode.strategies[stim.Circuit], ShorStimStrategy)
        assert isinstance(
            ShorCode.strategies[list[BaseOperation]],
            ShorQuantumCircuitStrategy,
        )

    def test_register_decorator(self):
        """Test the register decorator."""

        class MockStimStrategy(ShorStimStrategy):
            pass

        ShorCode.register(stim.Circuit)(MockStimStrategy)
        assert isinstance(ShorCode.strategies[stim.Circuit], MockStimStrategy)
        # Restore original
        ShorCode.strategies[stim.Circuit] = ShorStimStrategy()

    def test_validate_and_format_circuit_with_stim(self):
        """Test validate_and_format_circuit with stim circuit."""
        code = ShorCode()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        result = code.validate_and_format_circuit(circuit, num_qubits=1)
        assert isinstance(result, stim.Circuit)

    def test_validate_and_format_circuit_with_list(self):
        """Test validate_and_format_circuit with list of GateOperation.

        Note: type([]) returns 'list' which differs from list[BaseOperation],
        so this will raise KeyError.
        """
        code = ShorCode()
        circuit = [H(targets=[0])]
        with pytest.raises(KeyError):
            code.validate_and_format_circuit(circuit, num_qubits=1)

    def test_validate_and_format_circuit_invalid_num_qubits(self):
        """Test that num_qubits != 1 raises ValueError."""
        code = ShorCode()
        circuit = stim.Circuit()
        with pytest.raises(ValueError) as exc_info:
            code.validate_and_format_circuit(circuit, num_qubits=2)
        assert "not support" in str(exc_info.value)

    def test_validate_and_format_circuit_with_unsupported_type(self):
        """Test that unsupported circuit type raises KeyError."""
        code = ShorCode()
        with pytest.raises(KeyError):
            code.validate_and_format_circuit("invalid_type", num_qubits=1)

    def test_encode_with_stim_circuit(self):
        """Test encode with stim circuit."""
        code = ShorCode()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        result = code.encode(circuit)
        assert isinstance(result, stim.Circuit)

    def test_encode_with_list_circuit(self):
        """Test encode with list of GateOperation.

        Note: type([]) returns 'list' which differs from list[BaseOperation],
        so this will raise KeyError.
        """
        code = ShorCode()
        circuit = [H(targets=[0])]
        with pytest.raises(KeyError):
            code.encode(circuit)

    def test_decode(self):
        """Test decode method."""
        code = ShorCode()
        strategy = ShorCode.strategies[stim.Circuit]
        strategy.syndrome = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        result = code.decode(stim.Circuit())
        assert result[0] == 1

    def test_correct(self):
        """Test correct method."""
        code = ShorCode()
        strategy = ShorCode.strategies[stim.Circuit]
        strategy.raw_bits = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        err_pos = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        result = code.correct(stim.Circuit(), err_pos=err_pos)
        assert np.array_equal(result, [0, 0, 0, 0, 0, 0, 0, 0, 0])

    def test_correct_without_err_pos(self):
        """Test correct without err_pos."""
        code = ShorCode()
        result = code.correct(stim.Circuit())
        assert result is None

    def test_logical_measure(self):
        """Test logical_measure method."""
        code = ShorCode()
        bits = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        result = code.logical_measure(stim.Circuit(), bits)
        assert result == 1

    def test_compute_samples(self):
        """Test compute_samples method."""
        code = ShorCode()
        samples = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        code.compute_samples(stim.Circuit(), samples)
        strategy = ShorCode.strategies[stim.Circuit]
        assert strategy.syndrome.shape == (1, 9)

    def test_get_strategy_with_stim(self):
        """Test _get_strategy with stim circuit."""
        code = ShorCode()
        strategy = code._get_strategy(stim.Circuit())
        assert isinstance(strategy, ShorStimStrategy)

    def test_get_strategy_with_list(self):
        """Test _get_strategy with list.

        Note: type([]) returns 'list' which differs from list[BaseOperation],
        so this will raise KeyError.
        """
        code = ShorCode()
        with pytest.raises(KeyError):
            code._get_strategy([])

    def test_register_and_get_new_strategy(self):
        """Test registering a new strategy and retrieving it."""

        class CustomStrategy(ShorStimStrategy):
            pass

        custom_strategy = CustomStrategy()
        ShorCode.strategies["custom"] = custom_strategy
        assert "custom" in ShorCode.strategies
        # Clean up
        del ShorCode.strategies["custom"]

    def test_valid_strategies_after_instance_creation(self):
        """Test that strategies dict is properly populated."""
        ShorCode()
        assert len(ShorCode.strategies) >= 2
        assert stim.Circuit in ShorCode.strategies
        assert list[BaseOperation] in ShorCode.strategies
