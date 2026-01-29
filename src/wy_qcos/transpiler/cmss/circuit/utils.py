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

import random
import numpy as np
from pathlib import Path

from wy_qcos.transpiler.common.errors import CircuitException
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import (
    QuantumCircuit,
    ClassicalRegister,
)
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator
from wy_qcos.transpiler.cmss.common.gate_operation import create_gate
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.common.measure import Measure
from wy_qcos.transpiler.cmss.common.qasm_converter import QasmConverter


class RandomCircuitGen:
    """Random circuit generator.

    Description:
        Generate random circuit with depth or number of gates.
    """

    def __init__(self):
        self.qc: QuantumCircuit = None
        # number of qubits of quantum circuit
        self.num_qubits = 0
        # depth of quantum circuit
        self.depth = 0
        # number of gates
        self.size = 0

    def random_circuit_with_depth(
        self,
        num_qubits: int,
        depth: int,
        max_operands: int = 2,
        measure: bool = False,
        reset: bool = False,
        seed: None | int = None,
        gate_type: int = 1,
        outfile: None | str = None,
    ):
        """Generate random circuit of arbitrary size and form.

        Args:
            num_qubits (int): number of qubits.
            depth (int): depth of circuit.
            max_operands (int, optional): max qubits of the gates operation.
            Defaults to 2.
            measure (bool): whether to measure the qubits. Defaults to False.
            reset (bool): whether to reset the qubits. Defaults to False.
            seed (int, optional): random seed. Defaults to None.
            gate_type (int): type of gates. 0 for random gates,
            1 for Clifford + T.
            outfile (str, optional): output file path. Defaults to None.

        Returns:
            list: random ir list.
        """
        if num_qubits == 0 or depth == 0:
            self.qc = QuantumCircuit()
            return []
        if max_operands < 1 or max_operands > 4:
            raise CircuitException(
                "Invalid max_operands, max_operands must be between 1 and 4."
            )
        if gate_type != 0 and gate_type != 1:
            raise CircuitException(
                f"Invalid gate_type. gate_type must be 0 or 1: {gate_type}."
            )

        self.num_qubits = num_qubits
        self.depth = depth
        max_operands = (
            max_operands if num_qubits > max_operands else num_qubits
        )
        if gate_type == 0:
            gates_1q = [
                # 3 elements in tuple, represants
                # (gate_name, num_qubits, num_parameters)
                (Constant.SINGLE_QUBIT_GATE_X, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_Y, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_Z, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_H, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_S, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_T, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_P, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_U, 1, 3),
                (Constant.SINGLE_QUBIT_GATE_R, 1, 2),
                (Constant.SINGLE_QUBIT_GATE_RX, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_RY, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_RZ, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_SX, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_SXDG, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_SDG, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_TDG, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_U1, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_U2, 1, 2),
                (Constant.SINGLE_QUBIT_GATE_U3, 1, 3),
            ]

            gates_2q = [
                (Constant.TWO_QUBIT_GATE_CH, 2, 0),
                (Constant.TWO_QUBIT_GATE_CRX, 2, 1),
                (Constant.TWO_QUBIT_GATE_CRY, 2, 1),
                (Constant.TWO_QUBIT_GATE_CRZ, 2, 1),
                (Constant.TWO_QUBIT_GATE_CX, 2, 0),
                (Constant.TWO_QUBIT_GATE_CY, 2, 0),
                (Constant.TWO_QUBIT_GATE_CZ, 2, 0),
                (Constant.TWO_QUBIT_GATE_SWAP, 2, 0),
                (Constant.TWO_QUBIT_GATE_CU1, 2, 1),
                (Constant.TWO_QUBIT_GATE_CP, 2, 1),
                (Constant.TWO_QUBIT_GATE_CU3, 2, 3),
                (Constant.TWO_QUBIT_GATE_CSX, 2, 0),
                (Constant.TWO_QUBIT_GATE_CU, 2, 4),
                (Constant.TWO_QUBIT_GATE_RXX, 2, 1),
                (Constant.TWO_QUBIT_GATE_RZZ, 2, 1),
            ]

            gates_3q = [
                (Constant.THREE_QUBIT_GATE_CCX, 3, 0),
                (Constant.THREE_QUBIT_GATE_CSWAP, 3, 0),
                (Constant.THREE_QUBIT_GATE_RCCX, 3, 0),
            ]

            gates_4q = [
                (Constant.FOUR_QUBIT_GATE_RC3X, 4, 0),
                (Constant.FOUR_QUBIT_GATE_C3X, 4, 0),
                (Constant.FOUR_QUBIT_GATE_C3SQRTX, 4, 0),
            ]
        else:
            # Clifford + T
            gates_1q = [
                (Constant.SINGLE_QUBIT_GATE_X, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_H, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_S, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_T, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_SDG, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_TDG, 1, 0),
            ]

            gates_2q = [
                (Constant.TWO_QUBIT_GATE_CX, 2, 0),
                (Constant.TWO_QUBIT_GATE_CZ, 2, 0),
            ]
            gates_3q = []
            gates_4q = []

        if reset:
            gates_1q.append((Constant.SINGLE_QUBIT_GATE_RESET, 1, 0))

        gates = gates_1q.copy()
        if max_operands >= 2:
            gates.extend(gates_2q)
        if max_operands >= 3:
            gates.extend(gates_3q)
        if max_operands >= 4:
            gates.extend(gates_4q)
        gates_arr = np.array(
            gates,
            dtype=[
                ("class", object),
                ("num_qubits", np.int64),
                ("num_params", np.int64),
            ],
        )
        gates_1q_arr = np.array(gates_1q, dtype=gates_arr.dtype)

        qc = QuantumCircuit(num_qubits)

        if measure:
            cr = ClassicalRegister(num_qubits, "c")
            qc.add_register(cr)

        if seed is None:
            seed = np.random.randint(0, np.iinfo(np.int32).max)
        rng = np.random.default_rng(seed)

        qubits = [i for i in range(num_qubits)]
        # Apply arbitrary random operations in layers across all qubits.
        for _ in range(depth):
            # Select num_qubits gates randomly.
            gate_specs = rng.choice(gates_arr, size=len(qubits))
            # Get the cumulative number of qubits used by each gate.
            cumulative_qubits = np.cumsum(
                gate_specs["num_qubits"], dtype=np.int64
            )

            # Sort the cumulative number of qubits. The numbers arrange
            # in ascending order and split the gate_specs into two parts:
            # lower than the max number of qubits, and greater than the max.
            # Then get the lack of qubits for the last gate and
            # the total qubits.
            max_index = np.searchsorted(
                cumulative_qubits, num_qubits, side="right"
            )
            gate_specs = gate_specs[:max_index]
            slack = num_qubits - cumulative_qubits[max_index - 1]
            if slack:
                gate_specs = np.hstack((
                    gate_specs,
                    rng.choice(gates_1q_arr, size=slack),
                ))

            # qubits list
            q_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
            # paramenters list
            p_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
            q_indices[0] = p_indices[0] = 0
            np.cumsum(gate_specs["num_qubits"], out=q_indices[1:])
            np.cumsum(gate_specs["num_params"], out=p_indices[1:])
            parameters = rng.uniform(0, 2 * np.pi, size=p_indices[-1])
            rng.shuffle(qubits)

            for gate, q_start, q_end, p_start, p_end in zip(
                gate_specs["class"],
                q_indices[:-1],
                q_indices[1:],
                p_indices[:-1],
                p_indices[1:],
            ):
                targets = qubits[q_start:q_end]
                arg_value = parameters[p_start:p_end]
                qc.append(
                    create_gate(
                        name=gate, targets=targets, arg_value=arg_value
                    )
                )

        if measure:
            mea_qubits = [i for i in range(len(qubits))]
            qc.append(Measure(targets=mea_qubits, arg_value=[]))
        self.qc = qc
        self.size = qc.size()

        if outfile is not None:
            file_path = Path(outfile).resolve()
            if file_path.exists():
                raise CircuitException(
                    f"Output file has existed. outfile: {file_path}!"
                )
            qcv = QasmConverter(self.qc)
            qcv.save(path=file_path, version="2.0")

        return qc.get_operations()

    def random_circuit_with_gates(
        self,
        num_qubits: int,
        num_gates: int,
        basis_gates: tuple = (
            "x",
            "s",
            "sdg",
            "t",
            "tdg",
            "z",
            "h",
            "rz",
            "cx",
        ),
        seed: None | int = None,
        outfile: None | str = None,
    ):
        """Generate a random ir.

        Args:
            num_qubits (int): number of qubits.
            num_gates (int): number of gates.
            basis_gates (tuple, optional): basis gates. Defaults to ("x", "s",
                "sdg", "t", "tdg", "z", "h", "rz", "cx").
            seed (int): random seed.
            outfile (str, optional): output file path. Defaults to None.

        Returns:
            list: random ir list.
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        ir = []
        if num_gates == 0:
            return ir

        self.qc = QuantumCircuit(num_qubits=num_qubits)
        self.num_qubits = num_qubits
        self.size = num_gates
        for _ in range(num_gates):
            gate_name = random.choice(basis_gates)
            if gate_name in Constant.SINGLE_QUBIT_GATE_LIST:
                qubit = random.randint(0, num_qubits - 1)
                gate = create_gate(gate_name, targets=[qubit])
            elif gate_name in Constant.TWO_QUBIT_GATE_LIST:
                if num_qubits < 2:
                    raise ValueError(
                        f"{gate_name} gate need at least 2 qubits"
                    )
                qubits = random.sample(range(num_qubits), 2)
                gate = create_gate(gate_name, targets=qubits)
            elif gate_name in Constant.THREE_QUBIT_GATE_LIST:
                if num_qubits < 3:
                    raise ValueError(
                        f"{gate_name} gate need at least 3 qubits"
                    )
                qubits = random.sample(range(num_qubits), 3)
                gate = create_gate(gate_name, targets=qubits)
            else:
                raise NotImplementedError(
                    f"{gate_name} gate is not implemented"
                )

            if gate_name in ("rz", "rx", "ry"):
                angle = np.random.uniform(0, 2 * np.pi)
                gate.arg_value = [angle]

            ir.append(gate)

        self.qc.append_operations(ir)
        self.depth = self.qc.depth()

        if outfile is not None:
            file_path = Path(outfile).resolve()
            if file_path.exists():
                raise CircuitException(
                    f"Output file has existed. outfile: {file_path}!"
                )
            qcv = QasmConverter(self.qc)
            qcv.save(path=file_path, version="2.0")
        return ir


def is_equal(circ1: QuantumCircuit, circ2: QuantumCircuit) -> bool:
    """Compare two quantum circuits.

    Args:
        circ1 (QuantumCircuit): the first quantum circuit.
        circ2 (QuantumCircuit): the second quantum circuit.

    Returns:
        bool: equal or not.
    """
    op1 = Operator(circ1)
    op2 = Operator(circ2)
    return op1.equiv(op2)
