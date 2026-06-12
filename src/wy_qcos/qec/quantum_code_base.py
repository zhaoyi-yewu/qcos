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
            circuit: representing the quantum circuit

        Returns:
            encoded quantum circuit.
        """
        raise NotImplementedError("encode() must be implemented by subclass")

    @abstractmethod
    def decode(self, circuit, **kwargs):
        """Decode the syndrome.

        Args:
            circuit: quantum circuit
            kwargs: optional args
        """
        raise NotImplementedError("decode() must be implemented by subclass")

    @abstractmethod
    def correct(self, circuit, **kwargs):
        """Apply error correction based on the syndrome measurement.

        Args:
            circuit: quantum circuit
            kwargs: optional args

        Returns:
            corrected result
        """
        raise NotImplementedError("correct() must be implemented by subclass")

    def validate_and_format_circuit(self, circuit, num_qubits: int):
        """Validate and formatcircuit data.

        Args:
            circuit: quantum circuit.
            num_qubits: qubits num

        Returns:
            quantum circuit
        """
        raise NotImplementedError(
            "validate_and_format_circuit() must be implemented by subclass"
        )

    def compute_samples(self, circuit, samples: list):
        """compute samles to get raw bits and syndrome

        Args:
            circuit: quantum circuit.
            samples: samples data
        """

        raise NotImplementedError(
            "compute_samples() must be implemented by subclass"
        )
