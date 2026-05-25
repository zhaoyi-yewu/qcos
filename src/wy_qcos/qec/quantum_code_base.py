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

from abc import ABC, abstractmethod


class QuantumCodeBase(ABC):
    """Abstract base class for quantum error correction codes.

    This class provides the interface and default implementations for
    quantum error correction operations including encoding, error injection,
    syndrome measurement, error correction, and decoding.

    Attributes:
        name: Name of the quantum error correction code.
        n_physical: Number of physical qubits.
        n_logical: Number of logical qubits.
        distance: Code distance.
    """

    def __init__(self, name: str = "QuantumCodeBase"):
        """Initialize the quantum error correction code.

        Args:
            name: Name of the code.
        """
        self._name = name
        self._n_physical: int = 0
        self._n_logical: int = 0
        self._distance: int = 1

    @property
    def name(self) -> str:
        """Get the name of the code."""
        return self._name

    @property
    def n_physical(self) -> int:
        """Get the number of physical qubits."""
        return self._n_physical

    @property
    def n_logical(self) -> int:
        """Get the number of logical qubits."""
        return self._n_logical

    @property
    def distance(self) -> int:
        """Get the code distance."""
        return self._distance

    @abstractmethod
    def encode(self, circuit):
        """Encode a logical state into the physical qubit state.

        Args:
            circuit: representing the quantum circuit that prepares the logical state
                     to encode.

        Returns:
            encoded quantum circuit.
        """
        raise NotImplementedError("encode() must be implemented by subclass")

    @abstractmethod
    def decode(self, circuit: list) -> list:
        """Decode the physical qubit state back to logical state.

        Args:
            circuit: A list of objects representing
                     the physical state circuit.

        Returns:
            A list of objects representing the decoded
            logical state circuit.
        """
        raise NotImplementedError("decode() must be implemented by subclass")

    @abstractmethod
    def correct(self, syndrome: list[int], circuit: list) -> list:
        """Apply error correction based on the syndrome measurement.

        Args:
            syndrome: The measured syndrome as a list of integers.
            circuit: A list of objects representing
                     the current physical state circuit.

        Returns:
            A list of objects representing the corrected
            physical state circuit.
        """
        raise NotImplementedError("correct() must be implemented by subclass")

    def measure_syndrome(self, circuit: list) -> list[int]:
        """Measure the syndrome of the physical qubit state.

        This is a default implementation that can be overridden by subclasses.

        Args:
            circuit: A list of objects representing
                     the physical state circuit.

        Returns:
            The measured syndrome as a list of integers.
        """
        # Default implementation returns empty syndrome
        raise NotImplementedError(
            "measure_syndrome() must be implemented by subclass"
        )

    def validate_and_format_circuit(self, circuit, num_qubits: int):
        """Validate and formatcircuit data.

        Args:
            circuit: quantum circuit.
            num_qubits: qubits num

        Returns:

        """
        raise NotImplementedError(
            "validate_and_format_circuit() must be implemented by subclass"
        )

    def run(
        self,
        gate_list: list,
        inject_errors: list[dict] | None = None,
    ) -> list:
        """Run the complete error correction cycle.

        This method performs encoding, optional error injection,
        syndrome measurement, error correction, and decoding in sequence.

        Args:
            gate_list: A list of objects representing
                       the quantum circuit that prepares the initial
                       logical state.
            inject_errors: inject_errors

        Returns:
            A list of objects representing the final
            decoded logical state circuit.
        """
        # Step 0: Format and filter the input circuit
        circuit = self.format_data(gate_list)

        # Step 1: Encode the initial state
        circuit = self.encode(circuit)

        # Step 2: Inject errors if specified
        if inject_errors:
            for error_spec in inject_errors:
                error_type = error_spec.get("error_type", "X")
                qubit_index = error_spec.get("qubit_index", 0)
                circuit = self.inject_error(
                    circuit=circuit,
                    qubit_index=qubit_index,
                    error_type=error_type,
                )

        # Step 3: Measure syndrome
        syndrome = self.measure_syndrome(circuit)

        # Step 4: Apply error correction
        circuit = self.correct(syndrome, circuit)

        # Step 5: Decode the circuit
        final_circuit = self.decode(circuit)

        return final_circuit
