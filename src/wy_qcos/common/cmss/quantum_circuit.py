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

from wy_qcos.common.cmss.base_operation import (
    BaseOperation,
)
from wy_qcos.common.cmss.register import (
    Register,
    QuantumRegister,
    ClassicalRegister,
)
from wy_qcos.common.cmss.measure import Measure


class QuantumCircuit:
    def __init__(
        self, num_qubits: int = 0, num_clbits: int = 0, global_phase: float = 0
    ):
        """Initialize QuantumCircuit object.

        Args:
            num_qubits (int): number of qubits in the circuit.
            num_clbits (int): number of classical bits in the circuit.
            global_phase (float): global phase of the circuit.
        """
        if not isinstance(num_qubits, int) or not isinstance(num_clbits, int):
            raise ValueError("num_qubits and num_clbits must be integers.")
        if num_qubits < 0 or num_clbits < 0:
            raise ValueError(
                "Number of qubits and clbits must be non-negative."
            )
        self._num_qubits = num_qubits
        self._num_clbits = num_clbits
        # instructions by gate operations
        self._operations: list[BaseOperation] = []

        self.qregs: list[QuantumRegister] = []
        self.cregs: list[ClassicalRegister] = []
        self._global_phase: float = global_phase
        self._parameters = set()
        # pulse scheduler 所需接口（对齐 qiskit QuantumCircuit）
        self.instructions: list = []  # list[CircuitInstruction]
        self.calibrations: dict = {}
        # {gate_name: {((qubits,), params): Schedule}}
        self.metadata: dict = {}

    @classmethod
    def from_ir(cls, ir: list[BaseOperation], num_qubits: int = 0):
        """Create a quantum circuit from a list of gate operations.

        Args:
            ir (list[BaseOperation]): gate operations of ir.
            num_qubits (int): number of qubits in the circuit.

        Returns:
            QuantumCircuit: a quantum circuit corresponding to the ir.
        """
        if num_qubits > 0:
            circ = QuantumCircuit(num_qubits)
            # num_qubits already known -- skip per-op max() check
            circ._operations = list(ir)
        else:
            circ = QuantumCircuit()
            circ.append_operations(ir)
        return circ

    def append(self, operation: BaseOperation):
        """Append a gate operation to the quantum circuit.

        Args:
            operation (BaseOperation): The gate operation to append.
        """
        if isinstance(operation, BaseOperation):
            self._operations.append(operation)
            # Single max() call instead of two
            max_t = max(operation.targets) if operation.targets else -1
            if max_t >= self._num_qubits:
                self._num_qubits = max_t + 1
        else:
            raise TypeError("Invalid operation type!")

    def append_operations(self, operations: list[BaseOperation]):
        """Append multiple gate operations to the quantum circuit.

        Args:
            operations (list[BaseOperation]): The list of gate
            operations to append.
        """
        if isinstance(operations, list):
            ops = self._operations
            nq = self._num_qubits
            for op in operations:
                ops.append(op)
                max_t = max(op.targets) if op.targets else -1
                if max_t >= nq:
                    nq = max_t + 1
            self._num_qubits = nq
        else:
            raise TypeError("Invalid operation type!")

    def extend(self, operations: list[BaseOperation]):
        """Append multiple gate operations in a single batch.

        Alias for :meth:`append_operations` with a more Pythonic name.
        Avoids per-element method-call overhead compared to calling
        :meth:`append` in a loop.
        """
        self.append_operations(operations)

    def copy(self):
        """Create a lightweight copy of this circuit.

        Shares references to operation objects (treated as immutable).
        Much faster than ``deepcopy`` for circuits with many operations.
        """
        new_circ = QuantumCircuit(
            self._num_qubits, self._num_clbits, self._global_phase
        )
        new_circ._operations = list(self._operations)
        new_circ._parameters = set(self._parameters)
        return new_circ

    def compose(self, other):
        """Compose another circuit onto this one, returning a new circuit.

        Equivalent to ``self.copy()`` followed by appending all of
        ``other``'s operations, but more efficient than
        ``deepcopy`` + loop-``append``.
        """
        new_circ = self.copy()
        new_circ.append_operations(other.get_operations())
        return new_circ

    def get_operations(self):
        return self._operations

    @property
    def num_qubits(self):
        return self._num_qubits

    @property
    def num_clbits(self):
        return self._num_clbits

    @property
    def global_phase(self):
        return self._global_phase

    def set_global_phase(self, phase: float):
        """Set the global phase."""
        # If the phase is a Parameter or ParameterExpression,
        # convert it to a string
        if hasattr(phase, "expression"):
            self._global_phase = float(phase)
            if hasattr(phase, "parameters"):
                self._parameters.update(phase.parameters)
        elif hasattr(phase, "name"):
            self._global_phase = phase.name
            self._parameters.add(phase)
        else:
            self._global_phase = float(phase)

    def set_num_qubits(self, num_qubits: int):
        if not isinstance(num_qubits, int):
            raise TypeError("Input num_qubits must be an integer")
        if num_qubits < 0:
            raise ValueError("num_qubits must be non-negative")
        self._num_qubits = num_qubits

    def set_num_clbits(self, num_clbits: int):
        if not isinstance(num_clbits, int):
            raise TypeError("num_clbits must be an integer")
        if num_clbits < 0:
            raise ValueError("num_clbits must be non-negative")
        self._num_clbits = num_clbits

    def depth(self) -> int:
        """Calculate the depth of the quantum circuit.

        Returns:
            depth (int): depth of the quantum circuit
        """
        qubit_ops = [0] * (self._num_qubits + self._num_clbits)
        ignore_gates = ["sync", "reset", "move"]
        for op in self._operations:
            levels = []
            for q in op.targets:
                if op.name in ignore_gates:
                    levels.append(qubit_ops[q])
                else:
                    levels.append(qubit_ops[q] + 1)

            # max depth of every target qubit
            max_level = max(levels)
            for q in op.targets:
                qubit_ops[q] = max_level

        return max(qubit_ops)

    def width(self) -> int:
        """Calculate the width of the quantum circuit.

        Returns:
            width (int): number of bits in the quantum circuit
        """
        return self._num_qubits + self._num_clbits

    def size(self):
        """Returns total number of operations in circuit.

        Returns:
            int: Total number of gate operations.
        """
        return len(self._operations)

    def add_register(self, *regs: Register):
        """Add registers to the quantum circuit.

        Args:
            *regs (Register|QuantumRegister|ClassicalRegister): registers
            to be added
        """
        if not regs:
            return

        for reg in regs:
            if isinstance(reg, QuantumRegister):
                self.qregs.append(reg)
                self._num_qubits += reg.size
            elif isinstance(reg, ClassicalRegister):
                self.cregs.append(reg)
                self._num_clbits += reg.size
            else:
                raise TypeError("Invalid register type!")

    def measure(self, qubits: list):
        """Measure quantum bits.

        Args:
            qubits: qubit(s) to measure.
        """
        for qubit in qubits:
            self.append(Measure(targets=[qubit]))

    def measure_all(self):
        """Adds measurement to all qubits.

        By default, adds new classical bits in a :obj:`.ClassicalRegister`
        to store these measurements.

        """
        qubits = list(range(self._num_qubits))
        self.measure(qubits)
