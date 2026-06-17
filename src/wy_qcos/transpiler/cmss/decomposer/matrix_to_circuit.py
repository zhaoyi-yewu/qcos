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

"""Synthesize quantum circuits from arbitrary unitary matrices."""

from __future__ import annotations

from math import log2

import numpy as np
from scipy.linalg import cossin, schur

from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.common.cmss.gate_operation import (
    CX,
    CRZ,
    CRY,
    P,
    RY,
    RZ,
    U3,
    X,
    create_gate,
)
from wy_qcos.transpiler.cmss.decomposer.euler_decomposer import EulerDecomposer

_ATOL = 1e-12
_ELEMENTARY_GATES = {
    "x",
    "y",
    "z",
    "h",
    "rx",
    "ry",
    "rz",
    "p",
    "u",
    "u1",
    "u2",
    "u3",
    "cx",
    "cy",
    "cz",
    "swap",
}

_CONTROLLED_GATE_MAP = {
    "x": "cx",
    "y": "cy",
    "z": "cz",
    "h": "ch",
    "rx": "crx",
    "ry": "cry",
    "rz": "crz",
    "p": "cp",
    "u3": "cu3",
    "u": "cu",
    "cx": "ccx",
    "cz": "ccz",
    "swap": "cswap",
}


class MatrixDecomposer:
    """Convert unitary matrices into equivalent quantum gate sequences."""

    def __init__(self):
        self._euler = EulerDecomposer()

    def decompose(
        self,
        matrix: np.ndarray,
        qubits: list[int] | None = None,
    ) -> tuple[list[BaseOperation], float]:
        """Decompose a unitary matrix into a quantum circuit.

        Args:
            matrix: Unitary matrix of shape (2^n, 2^n).
            qubits: Target qubit indices. When omitted, ``[0, ..., n-1]``
                is used.

        Returns:
            A tuple of:
                - gate list implementing the unitary up to global phase
                - accumulated global phase in radians

        Raises:
            ValueError: If the input is not a square unitary matrix.
        """
        mat = self._validate_unitary(matrix)
        num_qubits = self._num_qubits(mat.shape[0])
        if qubits is None:
            qubits = list(range(num_qubits))
        if len(qubits) != num_qubits:
            raise ValueError(
                f"Expected {num_qubits} qubits, got {len(qubits)}."
            )
        gates, phase = self._decompose_recursive(mat, qubits)
        return gates, phase

    @staticmethod
    def _num_qubits(dimension: int) -> int:
        num_qubits = int(round(log2(dimension)))
        if 2**num_qubits != dimension:
            raise ValueError(
                f"Matrix dimension {dimension} is not a power of two."
            )
        return num_qubits

    @staticmethod
    def _validate_unitary(matrix: np.ndarray) -> np.ndarray:
        mat = np.asarray(matrix, dtype=np.complex128)
        if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
            raise ValueError("Matrix must be a square 2D array.")
        if not np.allclose(mat @ mat.conj().T, np.eye(mat.shape[0]), atol=1e-8):
            raise ValueError("Matrix must be unitary.")
        return mat

    def _decompose_recursive(
        self,
        matrix: np.ndarray,
        qubits: list[int],
    ) -> tuple[list[BaseOperation], float]:
        num_qubits = len(qubits)
        if num_qubits == 1:
            return self._decompose_one_qubit(matrix, qubits[0])
        return self._decompose_csd(matrix, qubits)

    def _decompose_one_qubit(
        self,
        matrix: np.ndarray,
        qubit: int,
    ) -> tuple[list[BaseOperation], float]:
        self._euler.set_matrix(matrix)
        coe, theta, phi, lam = self._euler.euler_zyz_decomposition()
        gates = [
            RZ([qubit], [float(lam)]),
            RY([qubit], [float(theta)]),
            RZ([qubit], [float(phi)]),
        ]
        return gates, float(-np.angle(coe))

    def _single_qubit_u3_params(
        self,
        matrix: np.ndarray,
    ) -> tuple[list[float], float]:
        self._euler.set_matrix(matrix)
        coe, theta, phi, lam = self._euler.euler_u3_decomposition()
        return [float(theta), float(phi), float(lam)], float(-np.angle(coe))

    def _decompose_csd(
        self,
        matrix: np.ndarray,
        qubits: list[int],
    ) -> tuple[list[BaseOperation], float]:
        num_qubits = len(qubits)
        half = 2 ** (num_qubits - 1)
        sub_qubits = qubits[:-1]
        msb = qubits[-1]

        (left_u1, left_u2), theta, (vh1, vh2) = cossin(
            matrix,
            p=half,
            q=half,
            separate=True,
        )

        gates: list[BaseOperation] = []
        phase = 0.0

        v_gates, v_phase = self._decompose_multiplex(
            vh1,
            vh2,
            sub_qubits,
            msb,
        )
        gates.extend(v_gates)
        phase += v_phase

        cs_gates, cs_phase = self._decompose_cosine_sine(
            theta,
            sub_qubits,
            msb,
        )
        gates.extend(cs_gates)
        phase += cs_phase

        u_gates, u_phase = self._decompose_multiplex(
            left_u1,
            left_u2,
            sub_qubits,
            msb,
        )
        gates.extend(u_gates)
        phase += u_phase

        return gates, phase

    def _decompose_multiplex(
        self,
        unitary0: np.ndarray,
        unitary1: np.ndarray,
        sub_qubits: list[int],
        msb: int,
    ) -> tuple[list[BaseOperation], float]:
        if len(sub_qubits) == 1:
            target = sub_qubits[0]
            controlled0 = self._controlled_unitary(
                msb,
                target,
                unitary0,
                ctrl_state=0,
            )
            controlled1 = self._controlled_unitary(
                msb,
                target,
                unitary1,
                ctrl_state=1,
            )
            return controlled0 + controlled1, 0.0

        return self._demultiplex(unitary0, unitary1, sub_qubits, msb)

    def _demultiplex(
        self,
        unitary0: np.ndarray,
        unitary1: np.ndarray,
        sub_qubits: list[int],
        msb: int,
    ) -> tuple[list[BaseOperation], float]:
        u0 = np.asarray(unitary0, dtype=np.complex128)
        u1 = np.asarray(unitary1, dtype=np.complex128)

        if u0.shape[0] == 1:
            return self._demultiplex_diagonal_2x2(
                np.diag([u0[0, 0], u1[0, 0]]),
                msb,
            )

        schur_matrix = u0 @ u1.conj().T
        t_matrix, z_matrix = schur(schur_matrix, output="complex")
        v_matrix = z_matrix
        diag_values = np.sqrt(np.diagonal(t_matrix))
        w_matrix = np.diag(diag_values) @ v_matrix.conj().T @ u1

        gates_v, phase_v = self._decompose_recursive(v_matrix, sub_qubits)
        gates_w, phase_w = self._decompose_recursive(w_matrix, sub_qubits)
        gates_d, phase_d = self._demultiplex_diagonal(
            diag_values,
            sub_qubits,
            msb,
        )
        return gates_w + gates_d + gates_v, phase_v + phase_w + phase_d

    def _demultiplex_diagonal(
        self,
        diag_values: np.ndarray,
        sub_qubits: list[int],
        msb: int,
    ) -> tuple[list[BaseOperation], float]:
        angles = [2.0 * 1j * np.log(value) for value in diag_values]
        control_bits = list(reversed(sub_qubits))
        real_angles = [float(np.real(angle)) for angle in angles]
        return self._uniformly_controlled_rk(real_angles, control_bits, msb, "rz"), 0.0

    def _demultiplex_diagonal_2x2(
        self,
        matrix: np.ndarray,
        msb: int,
    ) -> tuple[list[BaseOperation], float]:
        p_value, q_value = matrix[0, 0], matrix[1, 1]
        log_p = 1j * np.log(p_value)
        log_q = 1j * np.log(q_value)
        global_phase = float(-np.real((log_p + log_q) / 2.0))
        rz_angle = float(np.real((log_q - log_p) / 2.0))
        gates: list[BaseOperation] = []
        if abs(rz_angle) > _ATOL:
            gates.append(RZ([msb], [rz_angle]))
        return gates, global_phase

    @staticmethod
    def _binary_code(num_controls: int) -> np.ndarray:
        length = 2**num_controls
        width = num_controls
        codes = [
            [int(bit) for bit in format(index, f"0{width}b")]
            for index in range(length)
        ]
        return np.asarray(codes, dtype=int)

    @staticmethod
    def _gray_code(num_controls: int) -> np.ndarray:
        length = 2**num_controls
        codes = np.zeros((length, num_controls), dtype=int)
        for index in range(length):
            value = index ^ (index >> 1)
            for bit in range(num_controls):
                codes[index, num_controls - 1 - bit] = (value >> bit) & 1
        return codes

    def _controlled_unitary(
        self,
        control: int,
        target: int,
        unitary: np.ndarray,
        ctrl_state: int,
    ) -> list[BaseOperation]:
        sub_gates, sub_phase = self._decompose_one_qubit(
            np.asarray(unitary, dtype=np.complex128),
            target,
        )
        lam, theta, phi = (gate.arg_value[0] for gate in sub_gates)
        gates: list[BaseOperation] = []
        if abs(lam) > _ATOL:
            gates.extend(CRZ([control, target], [float(lam)]).decompose())
        if abs(theta) > _ATOL:
            gates.extend(CRY([control, target], [float(theta)]).decompose())
        if abs(phi) > _ATOL:
            gates.extend(CRZ([control, target], [float(phi)]).decompose())
        if abs(sub_phase) > _ATOL:
            gates.extend(P([control], [float(sub_phase)]).decompose())
        if ctrl_state == 0:
            return [X([control])] + gates + [X([control])]
        return gates

    def _decompose_cosine_sine(
        self,
        theta: np.ndarray,
        sub_qubits: list[int],
        msb: int,
    ) -> tuple[list[BaseOperation], float]:
        angles = [2.0 * float(angle) for angle in theta]
        if all(abs(angle) <= _ATOL for angle in angles):
            return [], 0.0
        control_bits = list(reversed(sub_qubits))
        return self._uniformly_controlled_rk(angles, control_bits, msb, "ry"), 0.0

    def _uniformly_controlled_rk(
        self,
        angles: list[float],
        control_bits: list[int],
        target: int,
        axis: str,
    ) -> list[BaseOperation]:
        if len(angles) <= 1:
            if len(angles) == 1 and abs(angles[0]) > _ATOL:
                gate = RY if axis == "ry" else RZ
                return [gate([target], [float(angles[0])])]
            return []

        num_controls = len(control_bits)
        binary = self._binary_code(num_controls)
        gray = self._gray_code(num_controls)
        size = len(angles)
        mix = np.zeros((size, size), dtype=float)
        for row in range(size):
            for col in range(size):
                mix[row, col] = (1.0 / size) * (-1) ** int(
                    np.dot(binary[col], gray[row])
                )
        thetas = mix @ np.asarray(angles, dtype=float)
        rotation = RY if axis == "ry" else RZ

        gates: list[BaseOperation] = []
        for index, angle in enumerate(thetas):
            gates.append(rotation([target], [float(angle)]))
            next_index = index + 1 if index + 1 < len(gray) else 0
            diff = np.abs(gray[next_index] - gray[index])
            control_index = int(np.where(diff == 1)[0][0])
            gates.append(CX([control_bits[control_index], target]))
        return gates

    def _uniformly_controlled_ry(
        self,
        target: int,
        controls: list[int],
        control_state: int,
        angle: float,
    ) -> list[BaseOperation]:
        prep: list[BaseOperation] = []
        for bit_index, control in enumerate(controls):
            if not (control_state >> bit_index) & 1:
                prep.append(X([control]))

        gates = prep + self._multi_controlled_ry(controls, target, angle) + prep
        return gates

    def _multi_controlled_ry(
        self,
        controls: list[int],
        target: int,
        angle: float,
    ) -> list[BaseOperation]:
        if len(controls) == 0:
            return [RY([target], [angle])]
        if len(controls) == 1:
            return CRY([controls[0], target], [float(angle)]).decompose()
        if len(controls) == 2:
            control0, control1 = controls
            half = angle / 2
            return [
                CX([control1, target]),
                *self._controlled_one_qubit(
                    control0,
                    target,
                    [float(half), 0.0, 0.0],
                    ctrl_state=1,
                ),
                CX([control1, target]),
                *self._controlled_one_qubit(
                    control0,
                    target,
                    [float(-half), 0.0, 0.0],
                    ctrl_state=1,
                ),
                CX([control1, target]),
                *self._controlled_one_qubit(
                    control0,
                    target,
                    [float(half), 0.0, 0.0],
                    ctrl_state=1,
                ),
                CX([control1, target]),
            ]

        raise NotImplementedError(
            "Uniformly controlled rotations with more than two control "
            "qubits are not supported yet."
        )

    def _single_qubit_subcircuit_matrix(
        self,
        gates: list[BaseOperation],
    ) -> np.ndarray | None:
        if not gates:
            return np.eye(2, dtype=np.complex128)
        targets = {target for gate in gates for target in gate.targets}
        if len(targets) != 1 or any(len(gate.targets) != 1 for gate in gates):
            return None
        mat = np.eye(2, dtype=np.complex128)
        for gate in reversed(gates):
            mat = np.asarray(gate, dtype=np.complex128) @ mat
        return mat

    def _control_subcircuit(
        self,
        gates: list[BaseOperation],
        control: int,
        ctrl_state: int,
    ) -> list[BaseOperation]:
        if (
            len(gates) == 1
            and gates[0].name.lower() == "u3"
            and len(gates[0].targets) == 1
        ):
            return self._controlled_one_qubit(
                control,
                gates[0].targets[0],
                [float(v) for v in gates[0].arg_value[:3]],
                ctrl_state=ctrl_state,
            )

        unitary = self._single_qubit_subcircuit_matrix(gates)
        if unitary is not None:
            target = gates[0].targets[0]
            return self._controlled_unitary(
                control,
                target,
                unitary,
                ctrl_state=ctrl_state,
            )

        if ctrl_state == 0:
            return (
                [X([control])]
                + self._control_subcircuit(gates, control, 1)
                + [X([control])]
            )

        controlled: list[BaseOperation] = []
        for gate in self._expand_to_elementary(gates):
            controlled.extend(self._add_single_control(gate, control))
        return controlled

    def _expand_to_elementary(
        self,
        gates: list[BaseOperation],
    ) -> list[BaseOperation]:
        elementary: list[BaseOperation] = []
        for gate in gates:
            if gate.name.lower() in _ELEMENTARY_GATES:
                elementary.append(gate)
                continue
            try:
                expanded = gate.decompose()
            except ValueError:
                expanded = [gate]
            if len(expanded) == 1 and expanded[0] is gate:
                elementary.append(gate)
            else:
                elementary.extend(self._expand_to_elementary(expanded))
        return elementary

    def _add_single_control(
        self,
        gate: BaseOperation,
        control: int,
    ) -> list[BaseOperation]:
        name = gate.name.lower()
        targets = gate.targets
        args = gate.arg_value

        if name in {"rz", "u1", "p", "ry", "rx", "u3", "u"}:
            return self._controlled_unitary(
                control,
                targets[0],
                np.asarray(gate, dtype=np.complex128),
                ctrl_state=1,
            )
        if name in _CONTROLLED_GATE_MAP:
            controlled_name = _CONTROLLED_GATE_MAP[name]
            controlled = create_gate(
                controlled_name,
                [control] + targets,
                args,
            )
            return controlled.decompose()

        if name in {"rxx", "ryy", "rzz", "rzx"}:
            return self._control_subcircuit(gate.decompose(), control, 1)

        raise NotImplementedError(
            f"Controlled synthesis is not implemented for gate '{gate.name}'."
        )

    def _controlled_one_qubit(
        self,
        control: int,
        target: int,
        u3_params: list[float],
        ctrl_state: int,
    ) -> list[BaseOperation]:
        unitary = U3([target], [float(v) for v in u3_params[:3]]).to_matrix()
        return self._controlled_unitary(
            control,
            target,
            unitary,
            ctrl_state=ctrl_state,
        )


def matrix_to_circuit(
    matrix: np.ndarray,
    qubits: list[int] | None = None,
) -> tuple[list[BaseOperation], float]:
    """Convert a unitary matrix into a quantum circuit.

    This is a convenience wrapper around :class:`MatrixDecomposer`.

    Args:
        matrix: Unitary matrix of shape (2^n, 2^n).
        qubits: Optional qubit indices. Defaults to ``[0, ..., n-1]``.

    Returns:
        A tuple of gate list and global phase.
    """
    return MatrixDecomposer().decompose(matrix, qubits)
