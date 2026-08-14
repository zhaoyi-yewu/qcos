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
from wy_qcos.common.cmss.quantum_circuit import (
    QuantumCircuit,
    ClassicalRegister,
)
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator
from wy_qcos.common.cmss.gate_operation import create_gate
from wy_qcos.common.constant import Constant
from wy_qcos.common.cmss.measure import Measure
from wy_qcos.common.cmss.qasm_converter import QasmConverter


class RandomCircuitGen:
    """Random circuit generator.

    Description:
        Generate random circuit with depth or number of gates.
    """

    def __init__(self) -> None:
        self.qc: QuantumCircuit | None = None
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
        gate_type: int = 0,
        density: float = 0.05,
        two_qubits_rate: float = 0.1,
        outfile: None | str = None,
    ):
        """Generate random circuit of arbitrary size and form.

        Args:
            num_qubits (int): number of qubits.
            depth (int): depth of circuit.
            max_operands (int, optional): max qubits of the gates operation.
            Only takes effect when gate_type=2; for gate_type 0 or 1 it is
            forced to 2. Defaults to 2.
            measure (bool): whether to measure the qubits. Defaults to False.
            reset (bool): whether to reset the qubits. Defaults to False.
            seed (int, optional): random seed. Defaults to None.
            gate_type (int): type of gates. 0 for basic gates (x, rx, ry, h,
            cx, cz), 1 for Clifford gates, 2 for all gates.
            density (float): the number of qubits that would be used to filled
            with gates, representing density of gates in the circuit.
            Defaults to 0.3.
            two_qubits_rate (float): max ratio of two-qubit gates (soft limit,
            can be exceeded to satisfy depth). Defaults to 0.5.
            outfile (str, optional): output file path. Must end with .qasm.
            Defaults to None.

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
        if gate_type not in (0, 1, 2):
            raise CircuitException(
                f"Invalid gate_type. "
                f"gate_type must be 0, 1, or 2: {gate_type}."
            )
        if gate_type in (0, 1) and max_operands != 2:
            max_operands = 2
        if density <= 0 or density > 1:
            raise CircuitException(
                f"Invalid density, density must be in (0, 1]: {density}."
            )
        if outfile is not None and not outfile.endswith(".qasm"):
            raise CircuitException(
                f"Invalid outfile suffix. "
                f"outfile must end with '.qasm': {outfile}"
            )

        self.num_qubits = num_qubits
        max_operands = (
            max_operands if num_qubits > max_operands else num_qubits
        )
        if gate_type == 0:
            gates_1q = [
                (Constant.SINGLE_QUBIT_GATE_X, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_RX, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_RY, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_H, 1, 0),
            ]
            gates_2q = [
                (Constant.TWO_QUBIT_GATE_CX, 2, 0),
                (Constant.TWO_QUBIT_GATE_CZ, 2, 0),
            ]
            gates_3q = []
            gates_4q = []
        elif gate_type == 1:
            gates_1q = [
                (Constant.SINGLE_QUBIT_GATE_X, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_Y, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_Z, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_H, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_S, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_SDG, 1, 0),
            ]
            gates_2q = [
                (Constant.TWO_QUBIT_GATE_CX, 2, 0),
                (Constant.TWO_QUBIT_GATE_CZ, 2, 0),
            ]
            gates_3q = []
            gates_4q = []
        else:
            gates_1q = [
                (Constant.SINGLE_QUBIT_GATE_X, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_Y, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_Z, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_H, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_S, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_T, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_P, 1, 1),
                (Constant.SINGLE_QUBIT_GATE_U, 1, 3),
                (Constant.SINGLE_QUBIT_GATE_U_UPPERCASE, 1, 0),
                (Constant.SINGLE_QUBIT_GATE_R, 1, 0),
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
                (Constant.TWO_QUBIT_GATE_RYY, 2, 1),
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

        if reset:
            gates_1q.append((Constant.SINGLE_QUBIT_GATE_RESET, 1, 0))

        gates_1q_only = gates_1q.copy()
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
        gates_1q_arr = np.array(
            gates_1q_only,
            dtype=[
                ("class", object),
                ("num_qubits", np.int64),
                ("num_params", np.int64),
            ],
        )

        qc = QuantumCircuit(num_qubits)

        if measure:
            cr = ClassicalRegister(num_qubits, "c")
            qc.add_register(cr)

        if seed is None:
            seed = np.random.randint(0, np.iinfo(np.int32).max)
        rng = np.random.default_rng(seed)

        all_qubits = [i for i in range(num_qubits)]
        used_num = max(max_operands, int(num_qubits * density))
        used_qubits = random.sample(all_qubits, k=used_num)

        total_gates_count = 0
        two_qubit_gates_count = 0
        target_depth = depth

        def _generate_layer(use_gates_arr, used_qubits, rng, qc):
            gate_specs = rng.choice(use_gates_arr, size=len(used_qubits))
            cumulative_qubits = np.cumsum(
                gate_specs["num_qubits"], dtype=np.int64
            )
            max_index = np.searchsorted(
                cumulative_qubits, used_num, side="right"
            )
            gate_specs = gate_specs[:max_index]
            return gate_specs

        for layer_idx in range(target_depth):
            use_gates_arr = gates_arr
            if (
                layer_idx > 0
                and total_gates_count > 0
                and two_qubit_gates_count / total_gates_count
                >= two_qubits_rate
            ):
                use_gates_arr = gates_1q_arr

            gate_specs = _generate_layer(use_gates_arr, used_qubits, rng, qc)

            for g in gate_specs:
                total_gates_count += 1
                if g["num_qubits"] >= 2:
                    two_qubit_gates_count += 1

            q_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
            p_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
            q_indices[0] = p_indices[0] = 0
            np.cumsum(gate_specs["num_qubits"], out=q_indices[1:])
            np.cumsum(gate_specs["num_params"], out=p_indices[1:])
            parameters = rng.uniform(0, 2 * np.pi, size=p_indices[-1])
            rng.shuffle(used_qubits)

            for gate, q_start, q_end, p_start, p_end in zip(
                gate_specs["class"],
                q_indices[:-1],
                q_indices[1:],
                p_indices[:-1],
                p_indices[1:],
            ):
                targets = used_qubits[q_start:q_end]
                arg_value = parameters[p_start:p_end]
                qc.append(
                    create_gate(
                        name=gate,
                        targets=targets,
                        arg_value=arg_value.tolist(),
                    )
                )

        while qc.depth() < target_depth:
            gate_specs = _generate_layer(gates_1q_arr, used_qubits, rng, qc)
            q_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
            p_indices = np.empty(len(gate_specs) + 1, dtype=np.int64)
            q_indices[0] = p_indices[0] = 0
            np.cumsum(gate_specs["num_qubits"], out=q_indices[1:])
            np.cumsum(gate_specs["num_params"], out=p_indices[1:])
            parameters = rng.uniform(0, 2 * np.pi, size=p_indices[-1])
            rng.shuffle(used_qubits)
            for gate, q_start, q_end, p_start, p_end in zip(
                gate_specs["class"],
                q_indices[:-1],
                q_indices[1:],
                p_indices[:-1],
                p_indices[1:],
            ):
                targets = used_qubits[q_start:q_end]
                arg_value = parameters[p_start:p_end]
                qc.append(
                    create_gate(
                        name=gate,
                        targets=targets,
                        arg_value=arg_value.tolist(),
                    )
                )

        if measure:
            mea_qubits = [i for i in range(num_qubits)]
            for qubit in mea_qubits:
                qc.append(Measure(targets=[qubit], arg_value=[]))
        self.qc = qc
        self.depth = qc.depth()
        self.size = qc.size()

        print(
            f"Random circuit generated: num_qubits={num_qubits}, "
            f"depth={self.depth}, size={self.size}, seed={seed}"
        )

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
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_SDG,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_TDG,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
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

            if gate_name in (
                Constant.SINGLE_QUBIT_GATE_RZ,
                Constant.SINGLE_QUBIT_GATE_RX,
                Constant.SINGLE_QUBIT_GATE_RY,
            ):
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


if __name__ == "__main__":
    rcg = RandomCircuitGen()
    rcg.random_circuit_with_depth(
        num_qubits=100,
        depth=50000,
        max_operands=2,
        measure=False,
        reset=False,
        seed=42,
        gate_type=0,
        density=0.04,
        two_qubits_rate=0.2,
        outfile="random_circuit.qasm",
    )
