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

import logging
import numpy as np
import stim

from numpy.typing import NDArray

from wy_qcos.qec.quantum_code_base import QuantumCodeBase
from wy_qcos.common.cmss.base_operation import (
    BaseOperation,
    OperationType,
)
from wy_qcos.common.cmss.gate_operation import (
    GateOperation,
)

logger = logging.getLogger(__name__)


class ShorStrategy:
    def __init__(self):
        """Initialize the Shor Strategy."""

    def get_stabilizers(self) -> dict:
        """Get the stabilizer generators of the Shor code.

        Returns:
            A list of strings representing the 8 stabilizer generators.
        """
        return {
            "Z": [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8)],
            "X": [(0, 1, 2, 3, 4, 5), (3, 4, 5, 6, 7, 8)],
        }

    @staticmethod
    def _validate_error_inject(error_inject: dict):
        """Validate error_inject configuration.

        Args:
            error_inject: error injection configuration dict.

        Raises:
            ValueError: If error_inject configuration is invalid.
        """
        VALID_ERROR_TYPES = {"x_error", "y_error", "z_error", "depolarize"}

        if not isinstance(error_inject, dict):
            raise ValueError(
                f"error_inject type error, got {type(error_inject).__name__}"
            )

        error_type = error_inject.get("error_type", None)
        if error_type is not None and error_type not in VALID_ERROR_TYPES:
            raise ValueError(
                f"Invalid error_type '{error_type}', "
                f"must be one of: {', '.join(sorted(VALID_ERROR_TYPES))}"
            )

        noise_prob = error_inject.get("noise_prob", None)
        if noise_prob is not None and not isinstance(noise_prob, (int, float)):
            raise ValueError(
                f"noise_prob type error,  {type(noise_prob).__name__}"
            )

    def validate_and_format_circuit(self, circuit):
        """Validate and formate raw circuit.

        Args:
            circuit: raw circuit.
        """
        raise NotImplementedError(
            "validate_and_format_circuit() must be implemented by subclass"
        )

    def encode(self, circuit, **kwargs):
        """Encode circuit.

        Args:
            circuit: quantum circuit.
            kwargs: optional keyword arguments (error_inject, noise_prob, etc.)
        """
        raise NotImplementedError("encode() must be implemented by subclass")

    def decode(self):
        """Decode syndrome.

        Returns:
            err_pos.
        """
        raise NotImplementedError("decode() must be implemented by subclass")

    def correct(self, **kwargs):
        """Correct raw_bits.

        Args:
            kwargs: kwargs.

        Returns:
            corrected bits.
        """
        raise NotImplementedError("correct() must be implemented by subclass")

    def compute_samples(self, samples: NDArray[np.int_]):
        """Compute samles to get raw bits and syndrome.

        Args:
            samples: samples data
        """
        raise NotImplementedError(
            "compute_samples() must be implemented by subclass"
        )


class ShorStimStrategy(ShorStrategy):
    """ShorStimStrategy, using Stim circuit to process qec codes."""

    def __init__(self):
        """Initialize the Shor Stim Strategy."""
        super().__init__()
        self.syndrome = []
        self.raw_bits = []

    def validate_and_format_circuit(self, circuit):
        """Validate and formate raw circuit.

        Args:
            circuit: raw circuit.

        Returns:
            formatted_circuit.
        """
        formatted_circuit = stim.Circuit()
        for gate in circuit:
            gate_name = gate.name
            gate_info = stim.gate_data(gate_name)
            if not gate_info.is_single_qubit_gate:
                raise ValueError(
                    f"Unexpected multi-qubit gate input: {gate_name},"
                    "Only single-qubit gates allowed."
                )
            formatted_circuit.append(gate)
        return formatted_circuit

    def encode(self, circuit: stim.Circuit, **kwargs) -> stim.Circuit:
        """Encode 1 logical qubit into 9 physical qubits.

        Args:
            circuit: raw stim circuit.
            kwargs: optional keyword arguments:

        Returns:
            encoded stim circuit.
        """
        error_inject = kwargs.get("error_inject", None)
        if error_inject is None:
            error_inject = {"error_type": "x_error", "noise_prob": 0.01}
        else:
            self._validate_error_inject(error_inject)

        encoded_circuit = stim.Circuit()

        # init
        data = list(range(9))
        anc_z = list(range(9, 15))
        anc_x = list(range(15, 17))
        all_q = data + anc_z + anc_x

        encoded_circuit.append("R", all_q)
        encoded_circuit.append("TICK")

        encoded_circuit.append("H", [0, 3, 6])
        encoded_circuit.append("TICK")
        encoded_circuit.append("CX", [0, 1, 0, 2])  # block0
        encoded_circuit.append("CX", [3, 4, 3, 5])  # block1
        encoded_circuit.append("CX", [6, 7, 6, 8])  # block2
        encoded_circuit.append("TICK")

        # apply logical gate
        for gate in circuit:
            gate_name = gate.name
            if gate_name == "X":
                encoded_circuit.append("Z", [0, 3, 6])
            elif gate_name == "Z":
                encoded_circuit.append("X", data)
            elif gate_name == "Y":
                encoded_circuit.append("Z", [0, 3, 6])
                encoded_circuit.append("X", data)
            elif gate_name == "H":
                raise ValueError(
                    "Logical H gate requires non-transversal implementation"
                )
            elif gate_name == "S":
                encoded_circuit.append("S", [0, 3, 6])
            else:
                raise ValueError(f"Unsupported logical gate: {gate_name}")
        encoded_circuit.append("TICK")

        # apply noise based on error_inject dict config
        if error_inject is not None:
            error_type = error_inject.get("error_type", "x_error")
            noise_prob = error_inject.get("noise_prob", 0.01)
            if error_type == "depolarize":
                stim_gate_name = "DEPOLARIZE1"
            else:
                stim_gate_name = error_type.upper()
            encoded_circuit.append(stim_gate_name, data, noise_prob)
        encoded_circuit.append("TICK")

        # Z stablizers: Z₀Z₁, Z₁Z₂, Z₃Z₄, Z₄Z₅, Z₆Z₇, Z₇Z₈
        for (q1, q2), anc in zip(self.get_stabilizers()["Z"], anc_z):
            encoded_circuit.append("CX", [q1, anc, q2, anc])
            encoded_circuit.append("M", [anc])
            encoded_circuit.append("R", [anc])
            encoded_circuit.append("TICK")

        # X stablizers
        for qs, anc in zip(self.get_stabilizers()["X"], anc_x):
            encoded_circuit.append("H", [anc])
            for q in qs:
                encoded_circuit.append("CX", [anc, q])
            encoded_circuit.append("H", [anc])
            encoded_circuit.append("M", [anc])
            encoded_circuit.append("R", [anc])
            encoded_circuit.append("TICK")

        # reverse
        encoded_circuit.append("CX", [6, 7, 6, 8])
        encoded_circuit.append("CX", [3, 4, 3, 5])
        encoded_circuit.append("CX", [0, 1, 0, 2])
        encoded_circuit.append("TICK")
        encoded_circuit.append("H", [0, 3, 6])
        encoded_circuit.append("TICK")

        # measure
        encoded_circuit.append("M", data)
        return encoded_circuit

    def correct(self, **kwargs):
        """Correct raw_bits.

        Args:
            kwargs: kwargs.

        Returns:
            corrected bits.
        """
        if not len(self.raw_bits):
            raise RuntimeError("Need to call compute_samples before correct")

        err_pos = kwargs.get("err_pos", None)
        if err_pos is None:
            return self.raw_bits

        raw_bits = np.atleast_2d(self.raw_bits).astype(np.int8)
        err_pos = np.atleast_2d(err_pos).astype(np.int8)

        corr = raw_bits.copy()
        corr[err_pos == 1] ^= 1
        return corr[0] if raw_bits.shape[0] == 1 else corr

    def decode(self):
        """Decode syndrome.

        Returns:
            err_pos.
        """
        if len(self.syndrome) == 0:
            raise RuntimeError("decode() called before compute_samples()")

        syndrome = np.asarray(self.syndrome, dtype=np.int8)
        orig_ndim = syndrome.ndim

        if orig_ndim == 1:
            syn = syndrome[np.newaxis, :]
        else:
            syn = syndrome

        n = syn.shape[0]
        err_pos = np.zeros((n, 9), dtype=np.int8)

        z_syn = syn[:, :6]

        def block_x_decode(s0, s1):
            res = np.full_like(s0, -1, dtype=np.int8)
            res[(s0 == 1) & (s1 == 0)] = 0
            res[(s0 == 1) & (s1 == 1)] = 1
            res[(s0 == 0) & (s1 == 1)] = 2
            return res

        off0 = block_x_decode(z_syn[:, 0], z_syn[:, 1])
        mask0 = off0 != -1
        err_pos[mask0, 0 + off0[mask0]] = 1

        off1 = block_x_decode(z_syn[:, 2], z_syn[:, 3])
        mask1 = off1 != -1
        err_pos[mask1, 3 + off1[mask1]] = 1

        off2 = block_x_decode(z_syn[:, 4], z_syn[:, 5])
        mask2 = off2 != -1
        err_pos[mask2, 6 + off2[mask2]] = 1

        x_syn = syn[:, 6:8]
        block0_z = (x_syn[:, 0] == 1) & (x_syn[:, 1] == 0)
        err_pos[block0_z, 0] ^= 1

        return err_pos[0] if orig_ndim == 1 else err_pos

    def logical_measure(self, bits):
        """Get logical value.

        Args:
            bits: corrected bits

        Returns:
            logical measure
        """
        bits = np.atleast_1d(bits).astype(np.int8)
        return int(bits[0]) if bits.ndim == 1 else bits[:, 0]

    def compute_samples(self, samples: NDArray[np.int_]):
        """Compute samles to get raw bits and syndrome.

        Args:
            samples: samples data
        """
        s = np.atleast_2d(samples)
        self.syndrome = s[:, :8]
        self.raw_bits = s[:, 8:17]


class ShorQuantumCircuitStrategy(ShorStrategy):
    """ShorQuantumCircuitStrategy, use Quantum circuit to process qec codes."""

    def __init__(self):
        """Initialize the Shor Stim Strategy."""
        super().__init__()

    def validate_and_format_circuit(self, circuit):
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

    def encode(self, circuit, **kwargs):
        """Encode circuit.

        Args:
            circuit: quantum circuit.
            kwargs: optional keyword arguments (error_inject, noise_prob, etc.)
        """
        raise NotImplementedError("this class need implement this func")

    def correct(self, **kwargs):
        """Correct quantum circuit.

        Args:
            kwargs: optional args
        """
        raise NotImplementedError("correct() must be implemented by subclass")

    def decode(self):
        """Decode circuit."""
        raise NotImplementedError("decode() must be implemented by subclass")

    def logical_measure(self, bits):
        """Get logical value.

        Args:
            bits: quantum bits value
        """
        raise NotImplementedError("decode() must be implemented by subclass")


class ShorCode(QuantumCodeBase):
    """Implementation of the 9-qubit Shor error correction code.

    The Shor code encodes 1 logical qubit into 9 physical qubits
    and can correct any single-qubit error. It combines a 3-qubit
    phase flip code with a 3-qubit bit flip code.
    """

    strategies = {}

    def __init__(self):
        """Initialize the Shor code."""
        super().__init__(name="ShorCode")

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

    def encode(self, circuit, **kwargs):
        """Encode a logical state into 9 physical qubits.

        The Shor code encodes a single qubit state into 9 physical qubits
        using the concatenation of phase-flip and bit-flip codes.

        Args:
            circuit: representing the quantum circuit.
            kwargs: optional keyword arguments (error_inject, noise_prob, etc.)

        Returns:
            encoded quantumm circuit.
        """
        # Create an encoded circuit
        return self._get_strategy(circuit).encode(circuit, **kwargs)

    def decode(self, circuit):
        """Decode the syndrome.

        Args:
            circuit: quantum circuit
            kwargs: optional args
        """
        return self._get_strategy(circuit).decode()

    def correct(self, circuit, **kwargs):
        """Apply error correction based on the syndrome measurement.

        Args:
            circuit: quantum circuit
            kwargs: optional args

        Returns:
            Correctted results
        """
        return self._get_strategy(circuit).correct(**kwargs)

    def logical_measure(self, circuit, bits):
        """Get logical value.

        Args:
            circuit: quantum circuit
            bits: corrected bits

        Returns:
            logical measure
        """
        return self._get_strategy(circuit).logical_measure(bits)

    def compute_samples(self, circuit, samples: NDArray[np.int_]):
        """Compute samles to get raw bits and syndrome.

        Args:
            circuit: quantum circuit
            samples: samples data
        """
        return self._get_strategy(circuit).compute_samples(samples)


ShorCode.register(stim.Circuit)(ShorStimStrategy)
ShorCode.register(list[BaseOperation])(ShorQuantumCircuitStrategy)
