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

    def decode(self, circuit):
        raise NotImplementedError("decode() must be implemented by subclass")


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

    def _detect_x_errors(self, data_bit: int, ancilla_bit: int, encoded_circuit: stim.Circuit):
        encoded_circuit.append("CX", [data_bit, ancilla_bit])
        encoded_circuit.append("CX", [data_bit + 1, ancilla_bit])
        encoded_circuit.append("M", [ancilla_bit])
        encoded_circuit.append("DETECTOR", [stim.target_rec(-1)])        

        encoded_circuit.append("CX", [data_bit + 1, ancilla_bit + 1])
        encoded_circuit.append("CX", [data_bit + 2, ancilla_bit + 1])
        encoded_circuit.append("M", [ancilla_bit + 1])
        encoded_circuit.append("DETECTOR", [stim.target_rec(-1)])    


    def _detect_z_errors(self, data_bit: int, ancilla_bit: int, encoded_circuit: stim.Circuit):
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
            0
        )
        return encoded_circuit

    def decode(self, circuit):
        raise NotImplementedError("decode() must be implemented by subclass")


class ShorQuantumCircuitStrategy(ShorStrategy):
    """ShorQuantumCircuitStrategy, usint Quantum circuit to process qec codes."""
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

    def decode(self, circuit):
        """Decode circuit.

        Args:
            circuit: quantum circuit.
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

    # 注册策略（装饰器写法）
    @classmethod
    def register(cls, circuit_type):
        def decorator(strategy_cls):
            cls.strategies[circuit_type] = strategy_cls()
            return strategy_cls

        return decorator

    # 自动根据 circuit 类型找到策略
    def _get_strategy(self, circuit):
        return ShorCode.strategies[type(circuit)]

    def validate_and_format_circuit(self, circuit, num_qubits: int):
        """Format the circuit data for Shor code.

        Args:
            circuit: quantum circuit.

        Returns:
            Formatted quantum circuit.
        """
        if num_qubits != 1:
            raise ValueError(
                f"Shor does not support {num_qubits} bits qec."
            )
        return self._get_strategy(circuit).validate_and_format_circuit(circuit)

    def encode(self, circuit):
        """Encode a logical state into 9 physical qubits.

        The Shor code encodes a single qubit state into 9 physical qubits
        using the concatenation of phase-flip and bit-flip codes.

        Args:
            circuit: representing the quantum circuit that prepares the logical state
                     to encode.

        Returns:
            encoded quantumm circuit.
        """
        # Create an encoded circuit
        return self._get_strategy(circuit).encode(circuit)

    def decode(self, circuit: list[BaseOperation]) -> list[BaseOperation]:
        """Decode the 9-qubit physical state back to logical state.

        Args:
            circuit: A list of BaseOperation objects representing
                     the 9-qubit physical state circuit.

        Returns:
            A list of BaseOperation objects representing the decoded logical
            single-qubit state circuit.
        """
        return self._get_strategy(circuit).decode(circuit)

    def correct(
        self, syndrome: list[int], circuit: list[BaseOperation]
    ) -> list[BaseOperation]:
        """Apply error correction based on the syndrome measurement.

        The Shor code uses 8 stabilizer generators (6 Z-type for bit-flip
        detection within each block of 3, and 2 X-type for phase-flip
        detection between blocks).

        Args:
            syndrome: The measured syndrome as a list of 8 integers (0 or 1).
                - syndrome[0:6]: Z-stabilizer meas for bit-flip detection
                - syndrome[6:8]: X-stabilizer meas for phase-flip detection
            circuit: A list of BaseOperation objects representing the current
            9-qubit physical state circuit.

        Returns:
            A list of BaseOperation objects representing the corrected 9-qubit
            physical state circuit.
        """
        if not syndrome or len(syndrome) < 8:
            return circuit

        corrected_circuit = list(circuit)
        corrected_circuit.append(
            GateOperation(
                name="_shor_corrected",
                targets=list(range(self._n_data)),
                arg_value=syndrome,
            )
        )
        return corrected_circuit

    def measure_syndrome(self, circuit: list[BaseOperation]) -> list[int]:
        """Measure the syndrome of the 9-qubit state.

        The Shor code has 8 stabilizer generators:
        - Z0Z1, Z1Z2 (first block bit-flip detection)
        - Z3Z4, Z4Z5 (second block bit-flip detection)
        - Z6Z7, Z7Z8 (third block bit-flip detection)
        - X0X3X6 (phase-flip detection between blocks 1 and 2)
        - X1X4X7 (phase-flip detection between blocks 2 and 3)

        Returns:
            A list of 8 integers (0 or 1) representing the syndrome meas.
        """
        # Default syndrome: no error detected
        syndrome = [0] * 8

        for op in circuit:
            if op.name in ("X", "Y", "Z") and op.targets:
                # Found an error gate, compute syndrome
                error_type = op.name
                error_qubit = op.targets[0]
                syndrome = self._compute_syndrome(error_type, error_qubit)
                break

        return syndrome

    def _compute_syndrome(
        self, error_type: str, qubit_index: int
    ) -> list[int]:
        """Compute the expected syndrome for a given error.

        This is a helper method that computes what syndrome would be measured
        if a specific error occurred on a specific qubit.

        Args:
            error_type: Type of Pauli error ('X', 'Y', or 'Z').
            qubit_index: Index of the qubit with the error (0-8).

        Returns:
            A list of 8 integers (0 or 1) representing the syndrome.
        """
        syndrome = [0] * 8

        # Determine which block the qubit belongs to (0, 1, or 2)
        block = qubit_index // 3
        # Position within the block (0, 1, or 2)
        pos_in_block = qubit_index % 3

        if error_type == "X":
            # X errors anticommute with Z stabilizers
            # Bit-flip syndrome within the block
            if pos_in_block == 0:
                # Z_i Z_{i+1} detects error on qubit i
                syndrome[2 * block] = 1
            elif pos_in_block == 1:
                syndrome[2 * block] = (
                    # Z_i Z_{i+1} detects error on qubit i+1
                    1
                )
                syndrome[2 * block + 1] = (
                    # Z_{i+1} Z_{i+2} detects error on qubit i+1
                    1
                )
            elif pos_in_block == 2:
                syndrome[2 * block + 1] = (
                    # Z_{i+1} Z_{i+2} detects error on qubit i+2
                    1
                )

        elif error_type == "Z":
            # Z errors anticommute with X stabilizers
            # Phase-flip syndrome between blocks
            if block == 0:
                syndrome[6] = 1  # X stabilizer between blocks 0 and 1
            elif block == 1:
                syndrome[6] = 1  # X stabilizer between blocks 0 and 1
                syndrome[7] = 1  # X stabilizer between blocks 1 and 2
            elif block == 2:
                syndrome[7] = 1  # X stabilizer between blocks 1 and 2

        elif error_type == "Y":
            # Y = iXZ, so it triggers both X and Z syndromes
            # Bit-flip syndrome within the block
            if pos_in_block == 0:
                syndrome[2 * block] = 1
            elif pos_in_block == 1:
                syndrome[2 * block] = 1
                syndrome[2 * block + 1] = 1
            elif pos_in_block == 2:
                syndrome[2 * block + 1] = 1

            # Phase-flip syndrome between blocks
            if block == 0:
                syndrome[6] = 1
            elif block == 1:
                syndrome[6] = 1
                syndrome[7] = 1
            elif block == 2:
                syndrome[7] = 1

        return syndrome




ShorCode.register(stim.Circuit)(ShorStimStrategy)
ShorCode.register(list[BaseOperation])(ShorQuantumCircuitStrategy)
