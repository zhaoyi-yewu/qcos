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

import pymatching
import stim

from wy_qcos.qec.quantum_code_base import QuantumCodeBase
from wy_qcos.common.cmss.base_operation import (
    BaseOperation,
    OperationType,
)
from wy_qcos.common.cmss.gate_operation import (
    GateOperation,
)


class ShorStrategy:
    def __init__(self):
        """Initialize the Shor Strategy."""
        # 9 bits for correcting
        self._n_data = 9
        # 6 bits for ancilla
        self._n_ancilla = 6
        # Shor can only correct 1 logical bit
        self._n_logical = 1

    def get_stabilizers(self) -> dict:
        """Get the stabilizer generators of the Shor code.

        Returns:
            A list of strings representing the 8 stabilizer generators.
        """
        return {
            "Z": [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8)],
            "X": [(0, 3, 6), (1, 4, 7)],
        }

    def format_circuit(self, circuit):
        raise NotImplementedError

    def encode(self, circuit):
        """Encode circuit.

        Args:
            circuit: quantum circuit.
        """
        raise NotImplementedError("encode() must be implemented by subclass")

    def decode(self, **kwargs):
        raise NotImplementedError("decode() must be implemented by subclass")

    def correct(self, **kwargs):
        raise NotImplementedError("correct() must be implemented by subclass")


class ShorStimStrategy(ShorStrategy):
    """ShorStimStrategy, usint Stim circuit to process qec codes."""

    def __init__(self):
        """Initialize the Shor Stim Strategy."""
        super.__init__()

    def format_circuit(self, circuit):
        """Validate the circuit data for Shor code.

        This method filters the stim.Circuit to keep only single-qubit gates

        Args:
            circuit: stim.Circuit

        Returns:
            stim.Circuit
        """
        formatted_circuit = stim.Circuit()
        for gate in circuit:
            if stim.gate_data(gate).is_annotation:
                continue
            if not stim.gate_data(gate).is_single_qubit_gate():
                raise ValueError("Unexpected circuit input.")
            formatted_circuit.append(gate)
        return formatted_circuit

    def _detect_x_errors(
        self, data_bit: int, ancilla_bit: int, encoded_circuit: stim.Circuit
    ):
        encoded_circuit.append("CX", [data_bit, ancilla_bit])
        encoded_circuit.append("CX", [data_bit + 1, ancilla_bit])
        encoded_circuit.append("M", [ancilla_bit])
        encoded_circuit.append("DETECTOR", [stim.target_rec(-1)])

        encoded_circuit.append("CX", [data_bit + 1, ancilla_bit + 1])
        encoded_circuit.append("CX", [data_bit + 2, ancilla_bit + 1])
        encoded_circuit.append("M", [ancilla_bit + 1])
        encoded_circuit.append("DETECTOR", [stim.target_rec(-1)])

    def _detect_z_errors(
        self, data_bit: int, ancilla_bit: int, encoded_circuit: stim.Circuit
    ):
        encoded_circuit.append("H", [ancilla_bit])
        for q in range(data_bit, data_bit + 6):
            encoded_circuit.append("CX", [ancilla_bit, q])
        encoded_circuit.append("H", [ancilla_bit])
        encoded_circuit.append("M", [ancilla_bit])
        encoded_circuit.append("DETECTOR", [stim.target_rec(-1)])

    def encode(self, circuit: stim.Circuit):
        """Encode circuit.

        Args:
            circuit: quantum circuit.

        Returns:
            encoded circuit.
        """
        # init
        encoded_circuit = stim.Circuit()
        data_qbits = list(range(self._n_data))
        anc_qubits = list(range(self._n_data, self._n_data + self._n_ancilla))
        encoded_circuit.append("R", data_qbits)
        encoded_circuit.append("R", anc_qubits)

        # phase repetition
        for qbit in [0, 1, 2]:
            encoded_circuit.append("H", qbit)
            encoded_circuit.append("CX", [qbit, qbit + 3])
            encoded_circuit.append("CX", [qbit, qbit + 6])

        # bit repetition
        for qbit in [0, 3, 6]:
            encoded_circuit.append("CX", [qbit, qbit + 1])
            encoded_circuit.append("CX", [qbit, qbit + 2])

        stabilizers = self.get_stabilizers()
        z_stabilizers = stabilizers.get("Z", [])
        for block in z_stabilizers:
            pair1 = block[0]
            pair2 = block[1]
            ctrl = pair1[0]
            target1 = pair1[1]
            target2 = pair2[1]
            encoded_circuit.append("CX", [ctrl, target1])
            encoded_circuit.append("CX", [ctrl, target2])

        # apply logical gate
        for gate in circuit:
            encoded_circuit.append(gate.name, [0, 3, 6])

        # add noise
        encoded_circuit.append("DEPOLARIZE1", range(self._n_logical), 0.001)
        encoded_circuit.append("DEPOLARIZE2", range(self._n_logical), 0.003)

        # detect X errors
        self._detect_x_errors(0, 9, encoded_circuit)
        self._detect_x_errors(3, 11, encoded_circuit)
        self._detect_x_errors(6, 13, encoded_circuit)

        # detect Z errors
        self._detect_z_errors(0, 15, encoded_circuit)
        self._detect_z_errors(3, 16, encoded_circuit)

        encoded_circuit.append("M", range(self._n_data))
        # logical observable
        encoded_circuit.append(
            "OBSERVABLE_INCLUDE",
            [
                stim.target_rec(-9),
                stim.target_rec(-6),
                stim.target_rec(-3),
            ],
            0,
        )
        return encoded_circuit

    def correct(self, **kwargs):
        obs = kwargs.get("obs", None)
        pred = kwargs.get("pred", None)
        if obs is None or pred is None:
            return None
        corrected_result = obs ^ pred
        raise corrected_result

    def decode(self, **kwargs):
        dem = kwargs.get("dem", None)
        syndrome = kwargs.get("syndrome", None)
        if dem is None or syndrome is None:
            return None
        matching = pymatching.Matching.from_detector_error_model(dem)
        pred = matching.decode_batch(syndrome)
        return pred


class ShorQuantumCircuitStrategy(ShorStrategy):
    """ShorQuantumCircuitStrategy, use Quantum circuit to process qec codes."""

    def __init__(self):
        """Initialize the Shor Stim Strategy."""
        super.__init__()

    def format_circuit(self, circuit):
        """Validate the circuit data for Shor code.

        This method filters the BaseOperation list to keep only GateOperation
        objects, and further filters to keep only single-qubit gates
        (operation_type == 1).

        Args:
            circuit: A list of BaseOperation objects representing
            the quantum circuit.

        Returns:
            A list of BaseOperation objects containing only single-qubit
            GateOperation instances.
        """
        # Filter to keep only single-qubit GateOperation instances
        formatted_circuit = []
        for op in circuit:
            if isinstance(op, GateOperation):
                # Check if it's a single-qubit gate (operation_type == 1)
                if (
                    op.operation_type
                    != OperationType.SINGLE_QUBIT_OPERATION.value
                ):
                    raise ValueError("Unexpected circuit input.")
                formatted_circuit.append(op)
        return formatted_circuit

    def encode(self, circuit):
        """Encode circuit.

        Args:
            circuit: quantum circuit.
        """
        raise NotImplementedError("this class need implement this func")

    def correct(self, **kwargs):
        """Correct quantum circuit.

        Args:
            kwargs: optional args
        """
        raise NotImplementedError("correct() must be implemented by subclass")

    def decode(self, **kwargs):
        """Decode circuit.

        Args:
            kwargs: optional args
        """
        raise NotImplementedError("decode() must be implemented by subclass")


class ShorCode(QuantumCodeBase):
    """Implementation of the 9-qubit Shor error correction code.

    The Shor code encodes 1 logical qubit into 9 physical qubits
    and can correct any single-qubit error. It combines a 3-qubit
    phase flip code with a 3-qubit bit flip code.

    Attributes:
        name: Name of the code ("ShorCode").
        n_physical: Number of physical qubits (9).
        n_logical: Number of logical qubits (1).
        distance: Code distance (3).
    """

    strategies = {}

    def __init__(self):
        """Initialize the Shor code."""
        super().__init__(name="ShorCode")
        # 9 bits for correcting
        self._n_data = 9
        # 6 bits for ancilla
        self._n_ancilla = 6
        # Shor can only correct 1 logical bit
        self._n_logical = 1
        self._distance = 3

    @classmethod
    def register(cls, circuit_type):
        def decorator(strategy_cls):
            cls.strategies[circuit_type] = strategy_cls()
            return strategy_cls

        return decorator

    def _get_strategy(self, circuit):
        return ShorCode.strategies[type(circuit)]

    def validate_and_format_circuit(self, circuit, num_qubits: int):
        """Format the circuit data for Shor code.

        Args:
            circuit: quantum circuit.
            num_qubits: num of qubits

        Returns:
            Formatted quantum circuit.
        """
        if num_qubits != 1:
            raise ValueError(f"Shor does not support {num_qubits} bits qec.")
        return self._get_strategy(circuit).validate_and_format_circuit(circuit)

    def encode(self, circuit):
        """Encode a logical state into 9 physical qubits.

        The Shor code encodes a single qubit state into 9 physical qubits
        using the concatenation of phase-flip and bit-flip codes.

        Args:
            circuit: representing the quantum circuit.

        Returns:
            encoded quantumm circuit.
        """
        # Create an encoded circuit
        return self._get_strategy(circuit).encode(circuit)

    def decode(self, circuit, **kwargs):
        """Decode the syndrome.

        Args:
            circuit: quantum circuit
            kwargs: optional args
        """
        return self._get_strategy(circuit).decode(kwargs)

    def correct(self, circuit, **kwargs):
        """Apply error correction based on the syndrome measurement.

        Args:
            circuit: quantum circuit
            kwargs: optional args

        Returns:
            Correctted results
        """
        return self._get_strategy(circuit).correct(kwargs)


ShorCode.register(stim.Circuit)(ShorStimStrategy)
ShorCode.register(list[BaseOperation])(ShorQuantumCircuitStrategy)
