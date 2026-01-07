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

from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


class QasmConverter:
    """Convert a list of Operations into OpenQASM 2.0 or 3.0 code."""

    def __init__(self, circuit: QuantumCircuit):
        """Initialize the QasmConverter.

        Args:
            circuit: quantum circuit to be converted.
        """
        self.operations = circuit.get_operations()
        qubit_num = circuit.num_qubits
        if qubit_num == 0:
            # Extract integer indices from targets
            max_idx = max(
                max(int(t) for t in op.targets)
                for op in self.operations
                if op.targets
            )
            qubit_num = max_idx + 1
        self.qubit_num = qubit_num

    def to_qasm2(self) -> str:
        """Generate OpenQASM 2.0 source code."""
        header = [
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            f"qreg q[{self.qubit_num}];",
            f"creg c[{self.qubit_num}];",
            "",
        ]

        body = []
        for op in self.operations:
            body.append(self._convert_op_to_qasm2(op))

        return "\n".join(header + body)

    def _convert_op_to_qasm2(self, op: BaseOperation) -> str:
        """Convert a single operation into QASM2 format."""
        name = op.name.lower()
        if name in ("measure", "reset"):
            return self._handle_special_qasm2(op)
        else:
            return op.to_openqasm("q")

    def _handle_special_qasm2(self, op: BaseOperation) -> str:
        """Handle measurement and reset operations in QASM2."""
        t = op.targets
        if op.name.lower() == "measure":
            return f"measure q[{t[0]}] -> c[{t[0]}];"
        elif op.name.lower() == "reset":
            return f"reset q[{t[0]}];"
        else:
            raise ValueError(f"Unknown special operation: {op.name}")

    def to_qasm3(self) -> str:
        """Generate OpenQASM 3.0 source code."""
        header = [
            "OPENQASM 3.0;",
            'include "stdgates.inc";',
            f"qubit[{self.qubit_num}] q;",
            f"bit[{self.qubit_num}] c;",
            "",
        ]

        body = []
        for op in self.operations:
            body.append(self._convert_op_to_qasm3(op))

        return "\n".join(header + body)

    def _convert_op_to_qasm3(self, op: BaseOperation) -> str:
        """Convert a single operation into QASM3 format."""
        name = op.name.lower()
        t = op.targets
        if name == "measure":
            return f"measure q[{t[0]}] -> c[{t[0]}];"
        elif name == "reset":
            return f"reset q[{t[0]}];"
        else:
            return op.to_openqasm("q")

    def save(self, path: str, version: str = "2.0"):
        """Save the generated QASM code to a .qasm file."""
        if version.startswith("2"):
            text = self.to_qasm2()
        elif version.startswith("3"):
            text = self.to_qasm3()
        else:
            raise ValueError(f"Unknown QASM version: {version}")

        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
