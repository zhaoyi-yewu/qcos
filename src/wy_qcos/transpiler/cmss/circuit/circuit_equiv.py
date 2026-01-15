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

import os
from mqt import qcec

from wy_qcos.transpiler.common.errors import CircuitException
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator
from wy_qcos.transpiler.cmss.common.qasm_converter import QasmConverter
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


class CircuitEquivChecker:
    """CircuitEquivChecker scope for different methods.

    Description:
        Operator(Recommended scope for circuit): width of circuit in (1, 10],
        depth of circuit in (1, 50].
        QCEC(Recommended scope for circuit): width of circuit in (10, 50],
        depth of circuit in (50, 2000].

    """

    def __init__(self, qc1: QuantumCircuit, qc2: QuantumCircuit):
        """Initialize the CircuitEquivChecker.

        Args:
            qc1(QuantumCircuit): The first quantum circuit to be
            checked for equivalence.
            qc2(QuantumCircuit): The second quantum circuit to be
            checked for equivalence.
        """
        if not isinstance(qc1, QuantumCircuit) or not isinstance(
            qc2, QuantumCircuit
        ):
            raise CircuitException(
                "Invalid quantum circuit type."
                f"qc1: {type(qc1)}, qc2: {type(qc2)}"
            )
        self.qc1 = qc1
        self.qc2 = qc2

    @staticmethod
    def cicuit_equiv_by_qcec(
        qc1: str | os.PathLike[str], qc2: str | os.PathLike[str]
    ):
        """Return True if qc1 is equal to qc2 by qcec.

        Args:
            qc1(str | os.PathLike[str]): quantum circuit represented by
            qasm string or path.
            qc2(str | os.PathLike[str]): quantum circuit represented by
            qasm string or path.
        """
        if not isinstance(qc1, str) and not isinstance(qc1, os.PathLike):
            raise CircuitException(
                "The input circuit is not a string or a path-like object."
            )
        elif not isinstance(qc2, str) and not isinstance(qc2, os.PathLike):
            raise CircuitException(
                "The input circuit is not a string or a path-like object."
            )
        is_equivalent = False
        # check equivalence by qcec
        result = qcec.verify(qc1, qc2)
        # parse result
        status = str(result.equivalence).lower()
        if "equivalent" in status and "not_equivalent" not in status:
            is_equivalent = True
        elif "not_equivalent" in status:
            is_equivalent = False
        else:
            raise CircuitException(f"未知或超时: {status}.")

        return is_equivalent

    def algo_equiv(self, algo_no: int = 0) -> bool:
        """Compare the quantum circuits by selecting different algorithms.

        Args:
            algo_no(int): the algorithm number, default 0.
            If algo_no is 0, select Operator(OpenQASM) when num_qubit <= 10,
            otherwise QCEC.
            If algo_no is 1, verifying by Operator(Unitary Matrix).
            If algo_no is 2, verifying by MQT QCEC(Decision Diagrams and
            Alternating Equivalence Checking).
        """
        is_equivalent = False
        algo_selected = ""
        if algo_no == 0:
            qubit_num1 = self.qc1.num_qubits
            qubit_num2 = self.qc2.num_qubits
            if qubit_num1 != qubit_num2:
                return is_equivalent

            if qubit_num1 <= 10:
                algo_selected = "op"
            else:
                algo_selected = "qcec"

        if algo_no == 1 or algo_selected == "op":
            op1 = Operator(self.qc1)
            op2 = Operator(self.qc2)
            is_equivalent = op1.equiv(op2)
        elif algo_no == 2 or algo_selected == "qcec":
            # Convert qc1 to QASM 2.0
            qcv1 = QasmConverter(self.qc1)
            qc1_str = qcv1.to_qasm2()
            # Convert qc1 to QASM 2.0
            qcv1 = QasmConverter(self.qc1)
            qc2_str = qcv1.to_qasm2()
            is_equivalent = CircuitEquivChecker.cicuit_equiv_by_qcec(
                qc1_str, qc2_str
            )
        else:
            raise CircuitException(f"Invalid argument algo_num: {algo_no}.")

        return is_equivalent
