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

import numpy as np
from math import sqrt, cos, sin, log2
from cmath import exp

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation
from wy_qcos.transpiler.cmss.common.base_operation import OperationType
from wy_qcos.transpiler.common.errors import (
    DecomposeException,
    CircuitException,
)
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.cmss.common.measure import Measure
from wy_qcos.transpiler.cmss.common.move import Move
from wy_qcos.transpiler.cmss.common.sync import Sync
from wy_qcos.transpiler.cmss.common.reset import Reset


class GateOperation(BaseOperation):
    """中间表示类."""

    def __init__(
        self,
        name,
        targets=None,
        arg_value=None,
        operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
        hermitian=True,
    ) -> None:
        """Init GateOperation.

        Args:
            name: 操作名称
            targets: 目标量子比特. Defaults to None.
            arg_value: 参数（旋转门所需）. Defaults to None.
            operation_type: 操作类型
            hermitian: 是否是厄米
        """
        super().__init__(name, targets, arg_value, operation_type)
        self.hermitian = hermitian
        if targets is not None:
            self.validate_params()

    def validate_params(self):
        """Validate gate's params.

        Operation type already indicated the number of qubits that gate needed.
        """
        if len(self.targets) != int(self.operation_type):
            raise DecomposeException("invalid targets num")

    def decompose(self):
        """门对应的分解规则，如无指定规则，则调用默认的分解方法.

        分解规则以字典的形式指定，配置在GlobalSetting的decomposition_rule中，
        其每个item的形式为::

            gate_name: #门名称
            {
                "param": [str] #形式化的门参数，数量与门实际所需一致，
                                如无参数，该项可不填
                "gates": [based_gates] #指定的分解形式，以based_gates列表表示
            }

        其中based_gates为一个三元组（name, targets, exps）,
        name表示门名称，targets为作用比特下标列表(从0开始),
        exps为参数对应的表达式，以字符串的形式表示，
        表达式中的操作数可为param中定义的形式化参数以及常量，常量中π可用pi表示

        示例::

            decomposition_rule = {
                "u3": {
                    "params": ["a", "b", "c"],
                    "gates": [
                        ("rz", [0], ["c"]),
                        ("rx", [0], ["pi/2"]),
                        ("rz", [0], ["b+pi"]),
                        ("rx", [0], ["pi/2"]),
                        ("rz", [0], ["a+pi"]),
                    ],
                },
                "h": {"gates": [("rx", [0], ["pi/2"])]},
            }
        """
        decompose_rule = trans_cfg_inst.get_decompose_rule()
        if decompose_rule is None:
            return self.default_decompose()

        custom_gate = decompose_rule.get(self.name, None)
        if custom_gate is None:
            return self.default_decompose()
        try:
            params_list = custom_gate.get("params", [])
            need_args = self.arg_value
            if len(params_list) != len(need_args):
                raise DecomposeException(
                    f"Gate: {self.name} requires arg: "
                    f"{need_args}, found {params_list}"
                )
            params = dict(zip(params_list, need_args))
            params["pi"] = np.pi
            decomposed_gates = custom_gate.get("gates", [])
            if len(decomposed_gates) == 0:
                return list([self])
            gates = []
            for name, qids, arg_value in decomposed_gates:
                qubits = [self.targets[qid] for qid in qids]
                # pylint: disable=eval-used
                args = [eval(arg, params) for arg in arg_value]  # noqa: S307
                gates.append(create_gate(name, qubits, args))
            return gates

        except Exception as e:
            raise DecomposeException(str(e)) from e

    def default_decompose(self):
        """默认的分解方法."""
        raise DecomposeException("please specify the decomposition gates")

    def __repr__(self):
        return (
            f"{type(self).__name__}(targets={self.targets},"
            f"arg_value={self.arg_value})"
        )

    @staticmethod
    def with_gate_array(base_array, dtype=None):
        """Return the complex matrix for the gate."""
        array_inter = np.array(base_array, dtype=np.complex128)
        array_inter.setflags(write=False)
        return np.asarray(array_inter, dtype=dtype)

    @staticmethod
    def _compute_control_matrix(base_mat, num_ctrl_qubits, ctrl_state=None):
        r"""Compute the controlled matrix of the input based matrix.

        Expression: V_n^j(U_{2^m}) = (U_{2^m} \otimes
            |j\rangle\!\langle j|) + (I_{2^m} \\otimes (I_{2^n} -
            |j\rangle\!\langle j|))

            where `|j\rangle \in \mathcal{H}^{2^n}` is the control state

        Args:
            base_mat (ndarray): unitary to be controlled
            num_ctrl_qubits (int): number of controls for new unitary
            ctrl_state (int or str or None): The control state in decimal or as
                a bitstring (e.g. '111'). If None, use 2**num_ctrl_qubits-1.

        Returns:
            ndarray: controlled version of base matrix.

        Raises:
            CircuitException: unrecognized mode or invalid ctrl_state
        """
        num_target = int(log2(base_mat.shape[0]))
        ctrl_dim = 2**num_ctrl_qubits
        ctrl_grnd = np.repeat([[1], [0]], [1, ctrl_dim - 1])
        if ctrl_state is None:
            ctrl_state = ctrl_dim - 1
        elif isinstance(ctrl_state, str):
            ctrl_state = int(ctrl_state, 2)
        if isinstance(ctrl_state, int):
            if not 0 <= ctrl_state < ctrl_dim:
                raise CircuitException(
                    "Invalid control state value specified."
                )
        else:
            raise CircuitException("Invalid control state type specified.")
        ctrl_proj = np.diag(np.roll(ctrl_grnd, ctrl_state))
        full_mat = np.kron(
            np.eye(2**num_target), np.eye(ctrl_dim) - ctrl_proj
        ) + np.kron(base_mat, ctrl_proj)
        return full_mat

    @staticmethod
    def with_controlled_gate_array(
        base_array, ctrl_state, num_ctrl_qubits, cached_states=None, dtype=None
    ):
        """Return the complex matrix.

        Description:
            If cached_states is not given, then all possible control states are
            precomputed.  If it is given, it should be an iterable of integers,
            and only these control states will be cached.
        """
        base = np.asarray(base_array, dtype=np.complex128)

        def matrix_for_control_state(state):
            out = np.asarray(
                GateOperation._compute_control_matrix(
                    base, num_ctrl_qubits, state
                ),
                dtype=np.complex128,
            )
            out.setflags(write=False)
            return out

        if cached_states is None:
            nonwritables = [
                matrix_for_control_state(state)
                for state in range(2**num_ctrl_qubits)
            ]
            return np.asarray(nonwritables[ctrl_state], dtype=dtype)
        else:
            nonwritables = {
                state: matrix_for_control_state(state)
                for state in cached_states
            }
            if (out := nonwritables.get(ctrl_state)) is not None:
                return np.asarray(out, dtype=dtype)
            return np.asarray(
                GateOperation._compute_control_matrix(
                    base, num_ctrl_qubits, ctrl_state
                ),
                dtype=dtype,
            )

    def to_matrix(self) -> np.ndarray:
        """Return a Numpy.ndarray for the gate unitary matrix.

        Returns:
            np.ndarray: a matrix array of the gate.

        Raises:
            CircuitException: If a Gate subclass does not implement this method
            an exception will be raised when this base class method is called.
        """
        if hasattr(self, "__array__"):
            return self.__array__(dtype=complex)
        raise CircuitException(f"to_matrix not defined for this {type(self)}")


# 实例化门，需包含一个默认的分解方法
class H(GateOperation):
    """Hadamard门类, 将基态变为叠加态的量子逻辑门."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(Constant.SINGLE_QUBIT_GATE_H, targets, arg_value)

    def default_decompose(self):
        gates = [
            RY(targets=self.targets, arg_value=np.pi / 2),
            RX(targets=self.targets, arg_value=np.pi),
        ]
        return gates

    def __array__(self, dtype=None):
        h_array = (
            1 / sqrt(2) * np.array([[1, 1], [1, -1]], dtype=np.complex128)
        )
        return GateOperation.with_gate_array(h_array, dtype)


class X(GateOperation):
    """Pauli-X门类, 将量子态绕Bloch球X轴旋转角度π进行翻转."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(Constant.SINGLE_QUBIT_GATE_X, targets, arg_value)

    def default_decompose(self):
        return list([RX(targets=self.targets, arg_value=np.pi)])

    def __array__(self, dtype=None):
        x_array = [[0, 1], [1, 0]]
        return GateOperation.with_gate_array(x_array, dtype)


class Y(GateOperation):
    """Pauli-Y门类, 将量子态绕Bloch球Y轴旋转角度π进行翻转."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(Constant.SINGLE_QUBIT_GATE_Y, targets, arg_value)

    def default_decompose(self):
        return list([RY(targets=self.targets, arg_value=np.pi)])

    def __array__(self, dtype=None):
        y_array = [[0, -1j], [1j, 0]]
        return GateOperation.with_gate_array(y_array, dtype)


class Z(GateOperation):
    """Pauli-Z门类, 将量子态绕Bloch球Z轴旋转角度π进行翻转."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(Constant.SINGLE_QUBIT_GATE_Z, targets, arg_value)

    def default_decompose(self):
        gates = [
            RY(targets=self.targets, arg_value=np.pi),
            RX(targets=self.targets, arg_value=np.pi),
        ]
        return gates

    def __array__(self, dtype=None):
        z_array = [[1, 0], [0, -1]]
        return GateOperation.with_gate_array(z_array, dtype)


class S(GateOperation):
    """相位门类.

    对量子态的`|1⟩`分量施加一个相位变换，使得`|1⟩`变为`i∣1⟩`，而`|0⟩`分量保持不变
    S门在Bloch球中对应于绕Z轴旋转π/2的操作
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_S, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        gates = [
            RX(targets=self.targets, arg_value=3 * np.pi / 2),
            RY(targets=self.targets, arg_value=np.pi / 2),
            RX(targets=self.targets, arg_value=np.pi / 2),
        ]
        return gates

    def __array__(self, dtype=None):
        s_array = np.array([[1, 0], [0, 1j]])
        return GateOperation.with_gate_array(s_array, dtype)


class SDG(GateOperation):
    """反相位门类.

    是S门的共轭转置，对量子态的`|1⟩`分量施加一个相位变换，使得`|1⟩`变为`-i∣1⟩`，而`|0⟩`分量保持不变。
    SDG门在Bloch球中对应于绕Z轴旋转-π/2的操作。
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_SDG, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        gates = [
            RX(targets=self.targets, arg_value=3 * np.pi / 2),
            RY(targets=self.targets, arg_value=3 * np.pi / 2),
            RX(targets=self.targets, arg_value=np.pi / 2),
        ]
        return gates

    def __array__(self, dtype=None):
        sdg_array = np.array([[1, 0], [0, -1j]])
        return GateOperation.with_gate_array(sdg_array, dtype)


class T(GateOperation):
    """T门.

    用于实现较小的相位旋转。T门的作用是对量子态的`|1⟩`分量施加一个相位变换，
    使得`|1⟩`变为`e^iπ/4∣1⟩`，而`|0⟩`分量保持不变。
    T门在Bloch球中对应于绕Z轴旋转π/4的操作。
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_T, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        return list([RZ(targets=self.targets, arg_value=np.pi / 4)])

    def __array__(self, dtype=None):
        t_array = np.array([[1, 0], [0, (1 + 1j) / sqrt(2)]])
        return GateOperation.with_gate_array(t_array, dtype)


class P(GateOperation):
    """P门.

    P门是单量子比特的相位旋转门，用于在Bloch球上实现绕Z轴旋转λ角度的操作。
    它对量子态的`|1⟩`分量施加一个相位因子`e^{iλ}`，而`|0⟩`分量保持不变。
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_P, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        return list([RZ(targets=self.targets, arg_value=self.arg_value)])

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the Phase gate."""
        lam = float(self.arg_value[0])
        return np.array([[1, 0], [0, exp(1j * lam)]], dtype=dtype)


class R(GateOperation):
    """R门（XY平面旋转门）.

    R(θ, φ) = exp[-i θ/2 (cosφ X + sinφ Y)]
    表示绕 Bloch 球 XY 平面中、与 X 轴夹角为 φ 的轴旋转 θ。
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_R, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        theta, phi = self.arg_value
        return list([
            RZ(targets=self.targets, arg_value=phi),
            RX(targets=self.targets, arg_value=theta),
            RZ(targets=self.targets, arg_value=-phi),
        ])

    def __array__(self, dtype=None):
        theta, phi = self.arg_value

        c = np.cos(theta / 2)
        s = np.sin(theta / 2)

        r_array = np.array([
            [c, -1j * np.exp(-1j * phi) * s],
            [-1j * np.exp(1j * phi) * s, c],
        ])

        return GateOperation.with_gate_array(r_array, dtype)


class TDG(GateOperation):
    """TDG门.

    T门的共轭转置, 作用是对量子态的`|1⟩`分量施加一个相位变换，
    使得`|1⟩`变为`e^-iπ/4∣1⟩`，而`|0⟩`分量保持不变。
    T门在Bloch球中对应于绕Z轴旋转-π/4的操作。
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_TDG, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        return list([RZ(targets=self.targets, arg_value=-np.pi / 4)])

    def __array__(self, dtype=None):
        t_array = np.array([[1, 0], [0, (1 - 1j) / sqrt(2)]])
        return GateOperation.with_gate_array(t_array, dtype)


class RX(GateOperation):
    """绕X轴旋转门.

    用来改变量子比特在X轴方向上的状态
    RX门在Bloch球中对应于绕X轴旋转一个指定的角度θ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_RX, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        return list([self])

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the RX gate."""
        rx_cos = cos(self.arg_value[0] / 2)
        rx_sin = sin(self.arg_value[0] / 2)
        return np.array(
            [[rx_cos, -1j * rx_sin], [-1j * rx_sin, rx_cos]], dtype=dtype
        )


class RY(GateOperation):
    """绕Y轴旋转门.

    用来改变量子比特在Y轴方向上的状态
    RY门在Bloch球中对应于绕Y轴旋转一个指定的角度θ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_RY, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        return list([self])

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the RY gate."""
        ry_cos = cos(self.arg_value[0] / 2)
        ry_sin = sin(self.arg_value[0] / 2)
        return np.array([[ry_cos, -ry_sin], [ry_sin, ry_cos]], dtype=dtype)


class RZ(GateOperation):
    """绕Z轴旋转门.

    用来改变量子比特在Z轴方向上的状态
    RZ门在Bloch球中对应于绕Z轴旋转一个指定的角度θ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_RZ, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        return list([self])

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the RY gate."""
        ilam2 = 0.5j * float(self.arg_value[0])
        return np.array([[exp(-ilam2), 0], [0, exp(ilam2)]], dtype=dtype)


class SX(GateOperation):
    """SX门（也称为 √X 门 或 square-root of NOT 门）.

    Pauli-X 门（即量子NOT门）的一半旋转，
    它在Bloch球上对应于 绕 X 轴旋转 π/2 的操作。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
    ) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_SX, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        gates = SDG(targets=self.targets).decompose()
        gates += H(targets=self.targets).decompose()
        gates += SDG(targets=self.targets).decompose()
        return gates

    def __array__(self, dtype=None):
        sx_array = [[0.5 + 0.5j, 0.5 - 0.5j], [0.5 - 0.5j, 0.5 + 0.5j]]
        return GateOperation.with_gate_array(sx_array, dtype)


class SXDG(GateOperation):
    """SXDG 门（也写作 √X† 或 SX⁻¹）.

    SXDG 门是 SX 门的共轭转置（逆操作），也称为 inverse square-root of X gate.
    它在 Bloch 球上对应于 绕 X 轴旋转 -π/2 的操作。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
    ) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_SXDG,
            targets,
            arg_value,
            hermitian=False,
        )

    def default_decompose(self):
        gates = S(targets=self.targets).decompose()
        gates += H(targets=self.targets).decompose()
        gates += S(targets=self.targets).decompose()
        return gates

    def __array__(self, dtype=None):
        sdg_array = [[0.5 - 0.5j, 0.5 + 0.5j], [0.5 + 0.5j, 0.5 - 0.5j]]
        return GateOperation.with_gate_array(sdg_array, dtype)


class CZ(GateOperation):
    """受控Z门或Controlled-Z门.

    在控制量子比特为`|1⟩`时，对目标量子比特应用一个Z门（Pauli-Z门）
    将目标量子比特的相位翻转。
    CZ门在Bloch球中对应于绕Z轴旋转π角度, 仅当控制量子比特为`|1⟩`时。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CZ, targets, arg_value, gate_type
        )

    def default_decompose(self):
        gates = H(targets=[self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates += H(targets=[self.targets[1]]).decompose()
        return gates

    def __array__(self, dtype=None):
        z_array = [[1, 0], [0, -1]]
        return GateOperation.with_controlled_gate_array(
            base_array=z_array,
            ctrl_state=int("1", 2),
            num_ctrl_qubits=1,
            dtype=dtype,
        )


class CX(GateOperation):
    """受控非门或Controlled-X门.

    当控制位处于`|1⟩`状态时，将目标位翻转
    （即`|0⟩`变为`|1⟩`，`|1⟩`变为`|0⟩`）。如果控制位处于`|0⟩`状态，则目标位保持不变。
    对应于经典比特的XOR（异或）操作
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CX, targets, arg_value, gate_type
        )

    def default_decompose(self):
        gates = H(targets=[self.targets[1]]).decompose()
        gates.append(CZ(self.targets))
        gates += H(targets=[self.targets[1]]).decompose()
        return gates

    def __array__(self, dtype=None):
        x_array = [[0, 1], [1, 0]]
        return GateOperation.with_controlled_gate_array(
            base_array=x_array,
            ctrl_state=int("1", 2),
            num_ctrl_qubits=1,
            dtype=dtype,
        )


class CY(GateOperation):
    """受控Y门或Controlled-Y门.

    在控制量子比特为`|1⟩`时，
    对目标量子比特应用一个Y门（Pauli-Y门）将目标量子比特绕Y轴旋转π角度。
    CY门在Bloch球中对应于绕Y轴旋转π角度, 仅当控制量子比特为`|1⟩`时。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CY, targets, arg_value, gate_type
        )

    def default_decompose(self):
        gates = []
        gates += SDG([self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates += S([self.targets[1]]).decompose()
        return gates

    def __array__(self, dtype=None):
        y_array = [[0, -1j], [1j, 0]]
        return GateOperation.with_controlled_gate_array(
            base_array=y_array,
            ctrl_state=int("1", 2),
            num_ctrl_qubits=1,
            dtype=dtype,
        )


class SWAP(GateOperation):
    """交换门，交换两个量子比特。."""

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_SWAP, targets, arg_value, gate_type
        )

    def default_decompose(self):
        gates = []
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates.append(CX([self.targets[1], self.targets[0]]))
        gates.append(CX([self.targets[0], self.targets[1]]))
        return gates

    def __array__(self, dtype=None):
        swap_array = [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]
        return GateOperation.with_gate_array(swap_array, dtype)


class CH(GateOperation):
    """受控Hadamard门，当控制量子比特为`|1⟩`时，对目标量子比特应用Hadamard门（H门）."""

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CH, targets, arg_value, gate_type
        )

    def default_decompose(self):
        gates = []
        gates += H([self.targets[1]]).decompose()
        gates += SDG([self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates += H([self.targets[1]]).decompose()
        gates += T([self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates += T([self.targets[1]]).decompose()
        gates += H([self.targets[1]]).decompose()
        gates += S([self.targets[1]]).decompose()
        gates += X([self.targets[1]]).decompose()
        gates += S([self.targets[0]]).decompose()
        return gates

    def __array__(self, dtype=None):
        h_array = (
            1 / sqrt(2) * np.array([[1, 1], [1, -1]], dtype=np.complex128)
        )
        return GateOperation.with_controlled_gate_array(
            base_array=h_array,
            ctrl_state=int("1", 2),
            num_ctrl_qubits=1,
            dtype=dtype,
        )


class CRX(GateOperation):
    """受控单量子比特旋转门，当控制量子比特为`|1⟩`时，对目标量子比特沿X轴旋转θ角度."""

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CRX,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += H([self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates.append(
            RZ(targets=[self.targets[1]], arg_value=-self.arg_value[0] / 2)
        )
        gates.append(CX(self.targets))
        gates.append(
            RZ(targets=[self.targets[1]], arg_value=self.arg_value[0] / 2)
        )
        gates += H([self.targets[1]]).decompose()
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the CRX gate."""
        half_theta = float(self.arg_value[0]) / 2
        crx_cos = cos(half_theta)
        crx_isin = 1j * sin(half_theta)
        return np.array(
            [
                [1, 0, 0, 0],
                [0, crx_cos, 0, -crx_isin],
                [0, 0, 1, 0],
                [0, -crx_isin, 0, crx_cos],
            ],
            dtype=dtype,
        )


class CRY(GateOperation):
    """受控的单量子比特旋转门，当控制量子比特为`|1⟩`时，对目标量子比特沿Y轴旋转θ角度."""

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CRY,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = [
            CX(self.targets),
            RY(targets=[self.targets[1]], arg_value=-self.arg_value[0] / 2),
            CX(self.targets),
            RY(targets=[self.targets[1]], arg_value=self.arg_value[0] / 2),
        ]
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the CRY gate."""
        half_theta = float(self.arg_value[0]) / 2
        cry_cos = cos(half_theta)
        cry_sin = sin(half_theta)
        return np.array(
            [
                [1, 0, 0, 0],
                [0, cry_cos, 0, -cry_sin],
                [0, 0, 1, 0],
                [0, cry_sin, 0, cry_cos],
            ],
            dtype=dtype,
        )


class CRZ(GateOperation):
    """受控的单量子比特旋转门，当控制量子比特为`|1⟩`时，对目标量子比特沿Z轴旋转θ角度."""

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CRZ,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = [
            CX(self.targets),
            RZ(targets=[self.targets[1]], arg_value=-self.arg_value[0] / 2),
            CX(self.targets),
            RZ(targets=[self.targets[1]], arg_value=self.arg_value[0] / 2),
        ]
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the CRZ gate."""
        arg = 1j * float(self.arg_value[0]) / 2
        return np.array(
            [
                [1, 0, 0, 0],
                [0, exp(-arg), 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, exp(arg)],
            ],
            dtype=dtype,
        )


class CU1(GateOperation):
    """受控U1门.

    CU1 门是一个 **受控相位旋转门**，是单量子比特 U1(λ) 门的受控版本。
    当控制量子比特为`|1⟩`时，目标量子比特执行一个绕 Z 轴旋转角度 λ 的 U1 门；
    当控制量子比特为`|0⟩`时，不进行任何操作。.
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CU1,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += U1(
            targets=[self.targets[0]], arg_value=self.arg_value[0] / 2
        ).decompose()
        gates.append(CX(self.targets))
        gates += U1(
            targets=[self.targets[1]], arg_value=-self.arg_value[0] / 2
        ).decompose()
        gates.append(CX(self.targets))
        gates += U1(
            targets=[self.targets[1]], arg_value=self.arg_value[0] / 2
        ).decompose()
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the CU1 gate."""
        eith = exp(1j * float(self.arg_value[0]))
        return np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, eith]],
            dtype=dtype,
        )


class CP(GateOperation):
    """CP门（Controlled-Phase 门）.

    CP 门（Controlled-Phase Gate）是一个 **受控相位旋转门**，
    对目标量子比特施加受控的 Z 轴旋转操作。
    当控制量子比特为`|1⟩`时，目标量子比特执行绕 Z 轴旋转角度 λ 的相位门 P(λ)；
    当控制量子比特为`|0⟩`时，目标量子比特保持不变。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CP,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += P(
            targets=[self.targets[0]], arg_value=self.arg_value[0] / 2
        ).decompose()
        gates.append(CX(self.targets))
        gates += P(
            targets=[self.targets[1]], arg_value=-self.arg_value[0] / 2
        ).decompose()
        gates.append(CX(self.targets))
        gates += P(
            targets=[self.targets[1]], arg_value=self.arg_value[0] / 2
        ).decompose()
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the CPhase gate."""
        eith = exp(1j * float(self.arg_value[0]))
        return np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, eith]],
            dtype=dtype,
        )


class CU3(GateOperation):
    """CU3门（受控U3门）.

    CU3 门是一种两量子比特门，用于在控制比特为`|1⟩`时，
    对目标比特施加 U3(θ, φ, λ) 操作；当控制比特为`|0⟩`时，
    目标比特保持不变。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CU3,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += U1(
            targets=[self.targets[0]],
            arg_value=(self.arg_value[2] + self.arg_value[1]) / 2,
        ).decompose()
        gates += U1(
            targets=[self.targets[1]],
            arg_value=(self.arg_value[2] - self.arg_value[1]) / 2,
        ).decompose()
        gates.append(CX(self.targets))
        gates += U3(
            targets=[self.targets[1]],
            arg_value=[
                -self.arg_value[0] / 2,
                0,
                -(self.arg_value[1] + self.arg_value[2]) / 2,
            ],
        ).decompose()
        gates.append(CX(self.targets))
        gates += U3(
            targets=[self.targets[1]],
            arg_value=[
                self.arg_value[0] / 2,
                self.arg_value[1],
                0,
            ],
        ).decompose()
        return gates

    def __array__(self, dtype=complex):
        """Return a Numpy.ndarray for the CU3 gate."""
        theta, phi, lam = self.arg_value
        theta, phi, lam = float(theta), float(phi), float(lam)
        u3_cos = cos(theta / 2)
        u3_sin = sin(theta / 2)
        return np.array(
            [
                [1, 0, 0, 0],
                [0, u3_cos, 0, -exp(1j * lam) * u3_sin],
                [0, 0, 1, 0],
                [0, exp(1j * phi) * u3_sin, 0, exp(1j * (phi + lam)) * u3_cos],
            ],
            dtype=dtype,
        )


class CSX(GateOperation):
    """CSX门（受控SX门）.

    CSX 门是一种两量子比特受控门，
    当控制比特处于`|1⟩`状态时，对目标比特施加 SX 门（√X 门）；
    当控制比特为`|0⟩`时，目标比特保持不变。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CSX,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += H([self.targets[1]]).decompose()
        gates += CU1(self.targets, [np.pi / 2]).decompose()
        gates += H([self.targets[1]]).decompose()
        return gates

    def __array__(self, dtype=None):
        sx_array = [[0.5 + 0.5j, 0.5 - 0.5j], [0.5 - 0.5j, 0.5 + 0.5j]]
        return GateOperation.with_controlled_gate_array(
            base_array=sx_array,
            ctrl_state=int("1", 2),
            num_ctrl_qubits=1,
            dtype=dtype,
        )


class CU(GateOperation):
    """CU门（受控U门）.

    CU 门是一种通用的两量子比特受控门，
    当控制比特处于`|1⟩`状态时，对目标比特施加一个任意的单量子比特酉变换 U；
    当控制比特为`|0⟩`时，目标比特保持不变。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_CU,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += P([self.targets[0]], [self.arg_value[3]]).decompose()
        gates += P(
            [self.targets[0]], [(self.arg_value[2] + self.arg_value[1]) / 2]
        ).decompose()
        gates += P(
            [self.targets[1]], [(self.arg_value[2] - self.arg_value[1]) / 2]
        ).decompose()
        gates.append(CX(self.targets))
        gates += U3(
            [self.targets[1]],
            [
                -self.arg_value[0] / 2,
                0,
                -(self.arg_value[1] + self.arg_value[2]) / 2,
            ],
        ).decompose()
        gates.append(CX(self.targets))
        gates += U3(
            [self.targets[1]],
            [
                self.arg_value[0] / 2,
                self.arg_value[1],
                0,
            ],
        ).decompose()
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the CU gate."""
        theta, phi, lam, gamma = (float(param) for param in self.arg_value)
        cu_cos = cos(theta / 2)
        cu_sin = sin(theta / 2)
        cu_a = exp(1j * gamma) * cu_cos
        cu_b = -exp(1j * (gamma + lam)) * cu_sin
        cu_c = exp(1j * (gamma + phi)) * cu_sin
        cu_d = exp(1j * (gamma + phi + lam)) * cu_cos
        return np.array(
            [
                [1, 0, 0, 0],
                [0, cu_a, 0, cu_b],
                [0, 0, 1, 0],
                [0, cu_c, 0, cu_d],
            ],
            dtype=dtype,
        )


class RXX(GateOperation):
    """RXX门（双量子比特 X-X 旋转门）.

    RXX 门是一种双量子比特旋转门，
    用于在两个量子比特的 X 方向上进行相互耦合的旋转操作。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_RXX,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += U3(
            [self.targets[0]], [np.pi / 2, self.arg_value[0], 0]
        ).decompose()
        gates += H([self.targets[1]]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates += U1([self.targets[1]], -self.arg_value[0]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates += H([self.targets[1]]).decompose()
        gates += U2(
            [self.targets[0]], [-np.pi, np.pi - self.arg_value[0]]
        ).decompose()
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the RXX gate."""
        theta2 = float(self.arg_value[0]) / 2
        rxx_cos = cos(theta2)
        rxx_isin = 1j * sin(theta2)
        return np.array(
            [
                [rxx_cos, 0, 0, -rxx_isin],
                [0, rxx_cos, -rxx_isin, 0],
                [0, -rxx_isin, rxx_cos, 0],
                [-rxx_isin, 0, 0, rxx_cos],
            ],
            dtype=dtype,
        )


class RZZ(GateOperation):
    """RZZ门（双量子比特 Z-Z 旋转门）.

    RZZ 门是一种双量子比特旋转门，
    用于在两个量子比特的 Z 方向上进行相互耦合的旋转操作。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.TWO_QUBIT_GATE_RZZ,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates.append(CX(self.targets))
        gates += U1([self.targets[1]], [self.arg_value[0]]).decompose()
        gates.append(CX(self.targets))
        return gates

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the RZZ gate."""
        itheta2 = 1j * float(self.arg_value[0]) / 2
        return np.array(
            [
                [exp(-itheta2), 0, 0, 0],
                [0, exp(itheta2), 0, 0],
                [0, 0, exp(itheta2), 0],
                [0, 0, 0, exp(-itheta2)],
            ],
            dtype=dtype,
        )


class CCX(GateOperation):
    """Toffoli门，如果两个控制量子比特都处于`|1⟩`状态，则对目标量子比特应用X门（Pauli-X门）."""

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.TRIPLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.THREE_QUBIT_GATE_CCX, targets, arg_value, gate_type
        )

    def default_decompose(self):
        gates = []
        gates += H([self.targets[2]]).decompose()
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += TDG([self.targets[2]]).decompose()
        gates.append(CX([self.targets[0], self.targets[2]]))
        gates += T([self.targets[2]]).decompose()
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += TDG([self.targets[2]]).decompose()
        gates.append(CX([self.targets[0], self.targets[2]]))
        gates += T([self.targets[2]]).decompose()
        gates += T([self.targets[1]]).decompose()
        gates += H([self.targets[2]]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates += T([self.targets[0]]).decompose()
        gates += TDG([self.targets[1]]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        return gates

    def __array__(self, dtype=None):
        x_array = [[0, 1], [1, 0]]
        return GateOperation.with_controlled_gate_array(
            base_array=x_array,
            ctrl_state=int("11", 2),
            num_ctrl_qubits=2,
            cached_states=(3,),
            dtype=dtype,
        )


class CSWAP(GateOperation):
    """CSWAP 门（也称 Fredkin 门）是一种 三比特受控交换门，.

    它根据第一个比特（控制比特）的状态，决定是否交换后两个比特（目标比特）的状态。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.TRIPLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.THREE_QUBIT_GATE_CSWAP,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates.append(CX([self.targets[2], self.targets[1]]))
        gates += CCX(self.targets).decompose()
        gates.append(CX([self.targets[2], self.targets[1]]))
        return gates

    def __array__(self, dtype=None):
        swap_array = [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]
        return GateOperation.with_controlled_gate_array(
            base_array=swap_array,
            ctrl_state=int("1", 2),
            num_ctrl_qubits=1,
            dtype=dtype,
        )


class RCCX(GateOperation):
    """RCCX门（相对相位受控受控X门 / Relative-Phase Toffoli Gate）.

    RCCX 门是一种三量子比特逻辑门，
    是 Toffoli 门（CCX）的一个相对相位版本，
    即在实现相同控制逻辑的同时，引入了相位差，
    从而在物理实现上更简洁、资源消耗更低。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.TRIPLE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.THREE_QUBIT_GATE_RCCX,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += U2([self.targets[2]], [0, np.pi]).decompose()
        gates += U1([self.targets[2]], [np.pi / 4]).decompose()
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += U1([self.targets[2]], [-np.pi / 4]).decompose()
        gates.append(CX([self.targets[0], self.targets[2]]))
        gates += U1([self.targets[2]], [np.pi / 4]).decompose()
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += U1([self.targets[2]], [-np.pi / 4]).decompose()
        gates += U2([self.targets[2]], [0, np.pi]).decompose()
        return gates

    def __array__(self, dtype=None):
        init_array = [
            [1, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, -1j],
            [0, 0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, -1, 0, 0],
            [0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 1j, 0, 0, 0, 0],
        ]
        return GateOperation.with_gate_array(init_array, dtype)


class RC3X(GateOperation):
    """RC3X门（Relative-phase Toffoli 门）.

    RC3X 门是 Toffoli（CCX）门的相对相位版本，
    当两个控制量子比特均为`|1⟩`时，对目标量子比特施加 X 操作，
    但在部分叠加态上引入相对相位差。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.FOUR_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.FOUR_QUBIT_GATE_RC3X,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += U2([self.targets[3]], [0, np.pi]).decompose()
        gates += U1([self.targets[3]], [np.pi / 4]).decompose()
        gates.append(CX([self.targets[2], self.targets[3]]))
        gates += U1([self.targets[3]], [-np.pi / 4]).decompose()
        gates += U2([self.targets[3]], [0, np.pi]).decompose()
        gates.append(CX([self.targets[0], self.targets[3]]))
        gates += U1([self.targets[3]], [np.pi / 4]).decompose()
        gates.append(CX([self.targets[1], self.targets[3]]))
        gates += U1([self.targets[3]], [-np.pi / 4]).decompose()
        gates.append(CX([self.targets[0], self.targets[3]]))
        gates += U1([self.targets[3]], [np.pi / 4]).decompose()
        gates.append(CX([self.targets[1], self.targets[3]]))
        gates += U1([self.targets[3]], [-np.pi / 4]).decompose()
        gates += U2([self.targets[3]], [0, np.pi]).decompose()
        gates += U1([self.targets[3]], [np.pi / 4]).decompose()
        gates.append(CX([self.targets[2], self.targets[3]]))
        gates += U1([self.targets[3]], [-np.pi / 4]).decompose()
        gates += U2([self.targets[3]], [0, np.pi]).decompose()
        return gates

    def __array__(self, dtype=None):
        init_array = [
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 1j, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1j, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        return GateOperation.with_gate_array(init_array, dtype)


class C3X(GateOperation):
    """C3X门（三控制X门 / 三重受控非门）.

    C3X 门是多控制量子门的一种，具有三个控制量子比特和一个目标量子比特。
    当且仅当三个控制量子比特均为`|1⟩`时，C3X 门对目标量子比特施加 X（非）操作；
    否则，目标量子比特保持不变。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.FOUR_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.FOUR_QUBIT_GATE_C3X,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += H([self.targets[3]]).decompose()
        gates += P([self.targets[0]], [np.pi / 8]).decompose()
        gates += P([self.targets[1]], [np.pi / 8]).decompose()
        gates += P([self.targets[2]], [np.pi / 8]).decompose()
        gates += P([self.targets[3]], [np.pi / 8]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates += P([self.targets[1]], [-np.pi / 8]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += P([self.targets[2]], [-np.pi / 8]).decompose()
        gates.append(CX([self.targets[0], self.targets[2]]))
        gates += P([self.targets[2]], [np.pi / 8]).decompose()
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += P([self.targets[2]], [-np.pi / 8]).decompose()
        gates.append(CX([self.targets[0], self.targets[2]]))
        gates.append(CX([self.targets[2], self.targets[3]]))
        gates += P([self.targets[3]], [-np.pi / 8]).decompose()
        gates.append(CX([self.targets[1], self.targets[3]]))
        gates += P([self.targets[3]], [np.pi / 8]).decompose()
        gates.append(CX([self.targets[2], self.targets[3]]))
        gates += P([self.targets[3]], [-np.pi / 8]).decompose()
        gates.append(CX([self.targets[0], self.targets[3]]))
        gates += P([self.targets[3]], [np.pi / 8]).decompose()
        gates.append(CX([self.targets[2], self.targets[3]]))
        gates += P([self.targets[3]], [-np.pi / 8]).decompose()
        gates.append(CX([self.targets[1], self.targets[3]]))
        gates += P([self.targets[3]], [np.pi / 8]).decompose()
        gates.append(CX([self.targets[2], self.targets[3]]))
        gates += P([self.targets[3]], [-np.pi / 8]).decompose()
        gates.append(CX([self.targets[0], self.targets[3]]))
        gates += H([self.targets[3]]).decompose()
        return gates

    def __array__(self, dtype=None):
        x_array = [[0, 1], [1, 0]]
        return GateOperation.with_controlled_gate_array(
            base_array=x_array,
            ctrl_state=int("111", 2),
            num_ctrl_qubits=3,
            cached_states=(7,),
            dtype=dtype,
        )


class C3SQRTX(GateOperation):
    """C3√X门（三控制√X门 / 三重受控平方根X门）.

    C3√X门是具有三个控制量子比特的受控平方根X门（Controlled-Square-Root-of-X）
    当且仅当三个控制量子比特均处于 `|1⟩` 状态时，
    它对目标量子比特施加 √X 操作（即 X 门的平方根）；
    否则，目标量子比特保持不变。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.FOUR_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.FOUR_QUBIT_GATE_C3SQRTX,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += H([self.targets[3]]).decompose()
        gates += CU1(
            [self.targets[0], self.targets[3]], [np.pi / 8]
        ).decompose()
        gates += H([self.targets[3]]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates += H([self.targets[3]]).decompose()
        gates += CU1(
            [self.targets[1], self.targets[3]], [-np.pi / 8]
        ).decompose()
        gates += H([self.targets[3]]).decompose()
        gates.append(CX([self.targets[0], self.targets[1]]))
        gates += H([self.targets[3]]).decompose()
        gates += CU1(
            [self.targets[1], self.targets[3]], [np.pi / 8]
        ).decompose()
        gates += H([self.targets[3]]).decompose()
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += H([self.targets[3]]).decompose()
        gates += CU1(
            [self.targets[2], self.targets[3]], [-np.pi / 8]
        ).decompose()
        gates += H([self.targets[3]]).decompose()
        gates.append(CX([self.targets[0], self.targets[2]]))
        gates += H([self.targets[3]]).decompose()
        gates += CU1(
            [self.targets[2], self.targets[3]], [np.pi / 8]
        ).decompose()
        gates += H([self.targets[3]]).decompose()
        gates.append(CX([self.targets[1], self.targets[2]]))
        gates += H([self.targets[3]]).decompose()
        gates += CU1(
            [self.targets[2], self.targets[3]], [-np.pi / 8]
        ).decompose()
        gates += H([self.targets[3]]).decompose()
        gates.append(CX([self.targets[0], self.targets[2]]))
        gates += H([self.targets[3]]).decompose()
        gates += CU1(
            [self.targets[2], self.targets[3]], [np.pi / 8]
        ).decompose()
        gates += H([self.targets[3]]).decompose()

        return gates

    def __array__(self, dtype=None):
        sx_array = [[0.5 + 0.5j, 0.5 - 0.5j], [0.5 - 0.5j, 0.5 + 0.5j]]
        return GateOperation.with_controlled_gate_array(
            sx_array,
            ctrl_state=int("111", 2),
            num_ctrl_qubits=3,
            cached_states=(7,),
            dtype=dtype,
        )


class C4X(GateOperation):
    """C4X门（四控制X门 / 四重受控非门）.

    C4X 门是具有四个控制量子比特的多控制X门（Multi-Controlled X Gate），
    也称为四重受控非门（Four-Controlled-NOT Gate）。

    当且仅当四个控制量子比特全部处于 `|1⟩` 状态时，
    C4X 门对目标量子比特施加 X 操作（即翻转其量子态：`|0⟩` ↔ `|1⟩`）；
    否则，目标量子比特保持不变。
    """

    def __init__(
        self,
        targets=None,
        arg_value=None,
        gate_type=OperationType.FIVE_QUBIT_OPERATION.value,
    ) -> None:
        super().__init__(
            Constant.FIVE_QUBIT_GATE_C4X,
            targets,
            arg_value,
            gate_type,
            hermitian=False,
        )

    def default_decompose(self):
        gates = []
        gates += H([self.targets[4]]).decompose()
        gates += CU1(
            [self.targets[3], self.targets[4]], [np.pi / 2]
        ).decompose()
        gates += H([self.targets[4]]).decompose()
        gates += C3X([
            self.targets[0],
            self.targets[1],
            self.targets[2],
            self.targets[3],
        ]).decompose()
        gates += H([self.targets[4]]).decompose()
        gates += CU1(
            [self.targets[3], self.targets[4]], [-np.pi / 2]
        ).decompose()
        gates += H([self.targets[4]]).decompose()
        gates += C3X([
            self.targets[0],
            self.targets[1],
            self.targets[2],
            self.targets[3],
        ]).decompose()
        gates += C3SQRTX([
            self.targets[0],
            self.targets[1],
            self.targets[2],
            self.targets[4],
        ]).decompose()

        return gates

    def __array__(self, dtype=None):
        x_array = [[0, 1], [1, 0]]
        return GateOperation.with_controlled_gate_array(
            base_array=x_array,
            ctrl_state=int("1111", 2),
            num_ctrl_qubits=4,
            cached_states=(15,),
            dtype=dtype,
        )


class U1(GateOperation):
    """U1门，对应于绕Z轴的相位旋转，参数为λ."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_U1, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        return list([RZ(self.targets, self.arg_value)])

    def __array__(self, dtype=None):
        """Return a Numpy.ndarray for the U1 gate."""
        lam = float(self.arg_value[0])
        return np.array([[1, 0], [0, np.exp(1j * lam)]], dtype=dtype)


class U2(GateOperation):
    """U2门，对应于 π/2 角度的极坐标旋转，参数为ϕ和λ."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_U2, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        gates = [
            RZ(self.targets, self.arg_value[0] + np.pi / 2),
            RX(self.targets, np.pi / 2),
            RZ(self.targets, self.arg_value[1] - np.pi / 2),
        ]
        return gates[::-1]

    def __array__(self, dtype=complex):
        """Return a Numpy.ndarray for the U2 gate."""
        isqrt2 = 1 / sqrt(2)
        phi, lam = self.arg_value
        phi, lam = float(phi), float(lam)
        return np.array(
            [
                [isqrt2, -exp(1j * lam) * isqrt2],
                [exp(1j * phi) * isqrt2, exp(1j * (phi + lam)) * isqrt2],
            ],
            dtype=dtype,
        )


class U3(GateOperation):
    """U3门，对应于任意角度的极坐标旋转，参数为θ、ϕ和λ."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_U3, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        gates = [
            RZ(self.targets, self.arg_value[1] + np.pi * 3),
            RX(self.targets, np.pi / 2),
            RZ(self.targets, self.arg_value[0] + np.pi),
            RX(self.targets, np.pi / 2),
            RZ(self.targets, self.arg_value[2]),
        ]
        return gates[::-1]

    def __array__(self, dtype=complex):
        """Return a Numpy.ndarray for the U3 gate."""
        theta, phi, lam = self.arg_value
        theta, phi, lam = float(theta), float(phi), float(lam)
        u3_cos = cos(theta / 2)
        u3_sin = sin(theta / 2)
        return np.array(
            [
                [u3_cos, -exp(1j * lam) * u3_sin],
                [exp(1j * phi) * u3_sin, exp(1j * (phi + lam)) * u3_cos],
            ],
            dtype=dtype,
        )


class U(GateOperation):
    """U门，对应于任意角度的极坐标旋转，参数为θ、ϕ和λ."""

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__(
            Constant.SINGLE_QUBIT_GATE_U, targets, arg_value, hermitian=False
        )

    def default_decompose(self):
        gates = [
            RZ(self.targets, self.arg_value[1] + np.pi * 3),
            RX(self.targets, np.pi / 2),
            RZ(self.targets, self.arg_value[0] + np.pi),
            RX(self.targets, np.pi / 2),
            RZ(self.targets, self.arg_value[2]),
        ]
        return gates[::-1]

    def __array__(self, dtype=complex):
        """Return a Numpy.ndarray for the U3 gate."""
        theta, phi, lam = self.arg_value
        theta, phi, lam = float(theta), float(phi), float(lam)
        u3_cos = cos(theta / 2)
        u3_sin = sin(theta / 2)
        return np.array(
            [
                [u3_cos, -exp(1j * lam) * u3_sin],
                [exp(1j * phi) * u3_sin, exp(1j * (phi + lam)) * u3_cos],
            ],
            dtype=dtype,
        )


def create_gate(
    name: str,
    targets: list = [],
    arg_value: list = [],
    allow_undefined: bool = False,
):
    """Create gate object.

    Args:
        name: name of gate
        targets: targets to bit list
        arg_value: arg list
        allow_undefined: allow undefined

    Returns:
        gate instance
    """
    if name == Constant.SINGLE_QUBIT_GATE_H:
        return H(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_X:
        return X(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_Y:
        return Y(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_Z:
        return Z(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_R:
        return R(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_RX:
        return RX(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_RY:
        return RY(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_RZ:
        return RZ(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_SX:
        return SX(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_SXDG:
        return SXDG(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_S:
        return S(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_T:
        return T(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_P:
        return P(targets, arg_value)
    elif name in (
        Constant.SINGLE_QUBIT_GATE_U,
        Constant.SINGLE_QUBIT_GATE_U_UPPERCASE,
    ):
        return U(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_SDG:
        return SDG(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_TDG:
        return TDG(targets, arg_value)
    elif name in (
        Constant.TWO_QUBIT_GATE_CX,
        Constant.TWO_QUBIT_GATE_CX_UPPERCASE,
    ):
        return CX(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CY:
        return CY(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CZ:
        return CZ(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CH:
        return CH(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_SWAP:
        return SWAP(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CRX:
        return CRX(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CRY:
        return CRY(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CRZ:
        return CRZ(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CU1:
        return CU1(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CP:
        return CP(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CU3:
        return CU3(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CSX:
        return CSX(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_CU:
        return CU(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_RXX:
        return RXX(targets, arg_value)
    elif name == Constant.TWO_QUBIT_GATE_RZZ:
        return RZZ(targets, arg_value)
    elif name == Constant.THREE_QUBIT_GATE_CCX:
        return CCX(targets, arg_value)
    elif name == Constant.THREE_QUBIT_GATE_CSWAP:
        return CSWAP(targets, arg_value)
    elif name == Constant.THREE_QUBIT_GATE_RCCX:
        return RCCX(targets, arg_value)
    elif name == Constant.FOUR_QUBIT_GATE_RC3X:
        return RC3X(targets, arg_value)
    elif name == Constant.FOUR_QUBIT_GATE_C3X:
        return C3X(targets, arg_value)
    elif name == Constant.FOUR_QUBIT_GATE_C3SQRTX:
        return C3SQRTX(targets, arg_value)
    elif name == Constant.FIVE_QUBIT_GATE_C4X:
        return C4X(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_U1:
        return U1(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_U2:
        return U2(targets, arg_value)
    elif name == Constant.SINGLE_QUBIT_GATE_U3:
        return U3(targets, arg_value)
    elif name == "sync":
        return Sync(targets, arg_value)
    elif name == "measure":
        return Measure(targets, arg_value)
    elif name == "move":
        return Move(targets, arg_value)
    elif name == "reset":
        return Reset(targets, arg_value)
    else:
        if allow_undefined:
            return GateOperation(name, targets=targets, arg_value=arg_value)
        raise DecomposeException(f"{name} is not support")
