#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
from qcos.common.config import Config
from enum import Enum


DECOMPOSE_RULE = Config.DECOMPOSE_RULE


class GateType(Enum):
    """
    门类型
    1：单比特门，2：两比特门，3：三比特门，0：测量，-1：同步，-2：移动
    """
    SINGLE_QUBIT_GATE = 1
    DOUBLE_QUBIT_GATE = 2
    TRIPLE_QUBIT_GATE = 3
    MEASURE_GATE = 0
    SYNC_GATE = -1
    MOVE_GATE = -2


class Gate:
    """
    中间表示类
    """

    def __init__(
            self, name, targets=None, arg_value=None,
            gate_type=GateType.SINGLE_QUBIT_GATE.value,
            hermitian=True
    ) -> None:
        """
        Args:
            name (_type_): 门名称
            targets (_type_, optional): 目标量子比特. Defaults to None.
            arg_value (_type_, optional): 参数（旋转门所需）. Defaults to None.
            gate_type: 门类型
            hermitian: 是否是厄米
        """
        self.name = name
        self.targets = targets
        # pylint: disable=use-list-literal
        self.arg_value = arg_value if arg_value is not None else list()
        if not isinstance(self.arg_value, list):
            self.arg_value = [self.arg_value]
        self.type = gate_type
        self.hermitian = hermitian

    def decompose(self):
        """
        门对应的分解规则，如无指定规则，则调用默认的分解方法
        分解规则以字典的形式指定，配置在GlobalSetting的decomposition_rule中，
        其每个item的形式为
            gate_name: #门名称
            {
                "param": [str] #形式化的门参数，数量与门实际所需一致，如无参数，该项可不填
                "gates": [based_gates] #指定的分解形式，以based_gates列表表示
            }
        其中based_gates为一个三元组（name, targets, exps）,name表示门名称，targets为
        作用比特下标列表(从0开始)，exps为参数对应的表达式，以字符串的形式表示，表达式中的操
        作数可为param中定义的形式化参数以及常量，常量中π可用pi表示

        举例如下：
        decomposition_rule = {
            "u3":{
                "params": ["a", "b", "c"],
                "gates":[
                    ("rz", [0], ["c"]),
                    ("rx", [0], ["pi/2"]),
                    ("rz", [0], ["b+pi"]),
                    ("rx", [0], ["pi/2"]),
                    ("rz", [0], ["a+pi"]),
                ]
            }
            "h": {
                "gates": [
                    ("rx", [0], ["pi/2"])
                ]
            }
        }
        return:
            gates(list): 分解后的门列表
        """
        if DECOMPOSE_RULE is None:
            return self.default_decompose()

        custom_gate = DECOMPOSE_RULE.get(self.name, None)
        if custom_gate is None:
            return self.default_decompose()
        try:
            params_list = custom_gate.get("params", [])
            need_args = self.arg_value
            if len(params_list) != len(need_args):
                raise ValueError(f"{self.name} gate need {len(need_args)}"
                                 f"params but give {len(params_list)}")
            params = dict(zip(params_list, need_args))
            params["pi"] = np.pi
            decomposed_gates = custom_gate.get("gates", [])
            if len(decomposed_gates) == 0:
                return list([self])
            gates = []
            for name, qids, arg_value in decomposed_gates:
                qubits = [self.targets[qid] for qid in qids]
                # pylint: disable=eval-used
                args = [eval(arg, params) for arg in arg_value]
                gates.append(create_gate(name, qubits, args))
            return gates

        except Exception as e:
            raise RuntimeError(str(e)) from e

    def default_decompose(self):
        """
        默认的分解方法
        """
        raise RuntimeError("please specify the decomposition gates")

    def __repr__(self):
        return (f"{type(self).__name__}(targets={self.targets},"
                f"arg_value={self.arg_value})")


# 实例化门，需包含一个默认的分解方法
class H(Gate):
    """
    Hadamard门类, 将基态变为叠加态的量子逻辑门
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("h", targets, arg_value)

    def default_decompose(self):
        gates = []
        gates.append(RY(targets=self.targets, arg_value=np.pi / 2))
        gates.append(RX(targets=self.targets, arg_value=np.pi))
        return gates


class X(Gate):
    """
    Pauli-X门类, 将量子态绕Bloch球X轴旋转角度π进行翻转
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("x", targets, arg_value)

    def default_decompose(self):
        return list([RX(targets=self.targets, arg_value=np.pi)])


class Y(Gate):
    """
    Pauli-Y门类, 将量子态绕Bloch球Y轴旋转角度π进行翻转
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("y", targets, arg_value)

    def default_decompose(self):
        return list([RY(targets=self.targets, arg_value=np.pi)])


class Z(Gate):
    """
    Pauli-Z门类, 将量子态绕Bloch球Z轴旋转角度π进行翻转
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("z", targets, arg_value)

    def default_decompose(self):
        gates = []
        gates.append(RY(targets=self.targets, arg_value=np.pi))
        gates.append(RX(targets=self.targets, arg_value=np.pi))
        return gates


class S(Gate):
    """
    相位门类, 对量子态的|1⟩分量施加一个相位变换，使得|1⟩变为i∣1⟩，而|0⟩分量保持不变
    S门在Bloch球中对应于绕Z轴旋转π/2的操作
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("s", targets, arg_value, hermitian=False)

    def default_decompose(self):
        gates = []
        gates.append(RX(targets=self.targets, arg_value=3 * np.pi / 2))
        gates.append(RY(targets=self.targets, arg_value=np.pi / 2))
        gates.append(RX(targets=self.targets, arg_value=np.pi / 2))
        return gates


class SDG(Gate):
    """
    反相位门类, 是S门的共轭转置，对量子态的|1⟩分量施加一个相位变换，使得|1⟩变为-i∣1⟩
    而|0⟩分量保持不变。
    SDG门在Bloch球中对应于绕Z轴旋转-π/2的操作。
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("sdg", targets, arg_value, hermitian=False)

    def default_decompose(self):
        gates = []
        gates.append(RX(targets=self.targets, arg_value=3 * np.pi / 2))
        gates.append(RY(targets=self.targets, arg_value=3 * np.pi / 2))
        gates.append(RX(targets=self.targets, arg_value=np.pi / 2))
        return gates


class T(Gate):
    """
    T门，用于实现较小的相位旋转。T门的作用是对量子态的|1⟩分量施加一个相位变换，
    使得|1⟩变为e^iπ/4∣1⟩，而|0⟩分量保持不变。
    T门在Bloch球中对应于绕Z轴旋转π/4的操作。
    """
    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("t", targets, arg_value, hermitian=False)

    def default_decompose(self):
        return list([RZ(targets=self.targets, arg_value=np.pi / 4)])


class TDG(Gate):
    """
    TDG门，T门的共轭转置, 作用是对量子态的|1⟩分量施加一个相位变换，
    使得|1⟩变为e^-iπ/4∣1⟩，而|0⟩分量保持不变。
    T门在Bloch球中对应于绕Z轴旋转-π/4的操作。
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("tdg", targets, arg_value, hermitian=False)

    def default_decompose(self):
        return list([RZ(targets=self.targets, arg_value=-np.pi / 4)])


class RX(Gate):
    """
    绕X轴旋转门, 用来改变量子比特在X轴方向上的状态
    RX门在Bloch球中对应于绕X轴旋转一个指定的角度θ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("rx", targets, arg_value, hermitian=False)

    def default_decompose(self):
        return list([self])


class RY(Gate):
    """
    绕Y轴旋转门, 用来改变量子比特在Y轴方向上的状态
    RY门在Bloch球中对应于绕Y轴旋转一个指定的角度θ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("ry", targets, arg_value, hermitian=False)

    def default_decompose(self):
        return list([self])


class RZ(Gate):
    """
    绕Z轴旋转门, 用来改变量子比特在Z轴方向上的状态
    RZ门在Bloch球中对应于绕Z轴旋转一个指定的角度θ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("rz", targets, arg_value, hermitian=False)

    def default_decompose(self):
        return list([self])


class CZ(Gate):
    """
    受控Z门或Controlled-Z门, 在控制量子比特为|1⟩时，对目标量子比特应用一个Z门（Pauli-Z门）
    将目标量子比特的相位翻转。
    CZ门在Bloch球中对应于绕Z轴旋转π角度, 仅当控制量子比特为|1⟩时。
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.DOUBLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("cz", targets, arg_value, gate_type)

    def default_decompose(self):
        gates = H(targets=[self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates += H(targets=[self.targets[1]]).decompose()
        return gates


class CX(Gate):
    """
    受控非门或Controlled-X门, 当控制位处于|1⟩状态时，将目标位翻转
    （即|0⟩变为|1⟩，|1⟩变为|0⟩）。如果控制位处于|0⟩状态，则目标位保持不变。
    对应于经典比特的XOR（异或）操作
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.DOUBLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("cx", targets, arg_value, gate_type)

    def default_decompose(self):
        return list([self])


class CY(Gate):
    """
    受控Y门或Controlled-Y门, 在控制量子比特为|1⟩时，
    对目标量子比特应用一个Y门（Pauli-Y门）将目标量子比特绕Y轴旋转π角度。
    CY门在Bloch球中对应于绕Y轴旋转π角度, 仅当控制量子比特为|1⟩时。
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.DOUBLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("cy", targets, arg_value, gate_type)

    def default_decompose(self):
        gates = []
        gates += SDG([self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates += S([self.targets[1]]).decompose()
        return gates


class CH(Gate):
    """
    受控Hadamard门，当控制量子比特为|1⟩时，对目标量子比特应用Hadamard门（H门）
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.DOUBLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("ch", targets, arg_value, gate_type)

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


class CRX(Gate):
    """
    受控单量子比特旋转门，当控制量子比特为|1⟩时，对目标量子比特沿X轴旋转θ角度
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.DOUBLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("crx", targets, arg_value, gate_type,
                         hermitian=False)

    def default_decompose(self):
        gates = []
        gates += H([self.targets[1]]).decompose()
        gates.append(CX(self.targets))
        gates.append(RZ(targets=[self.targets[1]],
                        arg_value=-self.arg_value[0] / 2))
        gates.append(CX(self.targets))
        gates.append(RZ(targets=[self.targets[1]],
                        arg_value=self.arg_value[0] / 2))
        gates += H([self.targets[1]]).decompose()
        return gates


class CRY(Gate):
    """
    受控的单量子比特旋转门，当控制量子比特为|1⟩时，对目标量子比特沿Y轴旋转θ角度
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.DOUBLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("cry", targets, arg_value, gate_type,
                         hermitian=False)

    def default_decompose(self):
        gates = []
        gates.append(CX(self.targets))
        gates.append(RY(targets=[self.targets[1]],
                        arg_value=-self.arg_value[0] / 2))
        gates.append(CX(self.targets))
        gates.append(RY(targets=[self.targets[1]],
                        arg_value=self.arg_value[0] / 2))
        return gates


class CRZ(Gate):
    """
    受控的单量子比特旋转门，当控制量子比特为|1⟩时，对目标量子比特沿Z轴旋转θ角度
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.DOUBLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("crz", targets, arg_value, gate_type,
                         hermitian=False)

    def default_decompose(self):
        gates = []
        gates.append(CX(self.targets))
        gates.append(RZ(targets=[self.targets[1]],
                        arg_value=-self.arg_value[0] / 2))
        gates.append(CX(self.targets))
        gates.append(RZ(targets=[self.targets[1]],
                        arg_value=self.arg_value[0] / 2))
        return gates


class CCX(Gate):
    """
    Toffoli门，如果两个控制量子比特都处于|1⟩状态，则对目标量子比特应用X门（Pauli-X门）
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.TRIPLE_QUBIT_GATE.value
    ) -> None:
        super().__init__("ccx", targets, arg_value, gate_type)

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


class U1(Gate):
    """
    U1门，对应于绕Z轴的相位旋转，参数为λ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("u1", targets, arg_value, hermitian=False)

    def default_decompose(self):
        return list([RZ(self.targets, self.arg_value)])


class U2(Gate):
    """
    U2门，对应于 π/2 角度的极坐标旋转，参数为ϕ和λ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("u2", targets, arg_value, hermitian=False)

    def default_decompose(self):
        gates = []
        gates.append(RZ(self.targets, self.arg_value[0] + np.pi / 2))
        gates.append(RX(self.targets, np.pi / 2))
        gates.append(RZ(self.targets, self.arg_value[1] - np.pi / 2))
        return gates[::-1]


class U3(Gate):
    """
    U3门，对应于任意角度的极坐标旋转，参数为θ、ϕ和λ
    """

    def __init__(self, targets=None, arg_value=None) -> None:
        super().__init__("u3", targets, arg_value, hermitian=False)

    def default_decompose(self):
        gates = []
        gates.append(RZ(self.targets, self.arg_value[1] + np.pi * 3))
        gates.append(RX(self.targets, np.pi / 2))
        gates.append(RZ(self.targets, self.arg_value[0] + np.pi))
        gates.append(RX(self.targets, np.pi / 2))
        gates.append(RZ(self.targets, self.arg_value[2]))
        return gates[::-1]


class SYNC(Gate):
    """
    同步门，用于在量子电路中同步操作，确保某些操作在特定的时间点同时发生
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.SYNC_GATE.value
    ) -> None:
        super().__init__("sync", targets, arg_value, gate_type,
                         hermitian=False)

    def default_decompose(self):
        return list([self])


class MEASURE(Gate):
    """
    测量门，用于测量量子比特的状态，将其从量子态转换为经典态
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.MEASURE_GATE.value
    ) -> None:
        super().__init__("measure", targets, arg_value, gate_type,
                         hermitian=False)

    def default_decompose(self):
        return list([self])


class MOV(Gate):
    """
    移动门, 用于执行量子比特在存储区和操纵区之间的移动操作
    """

    def __init__(
            self, targets=None, arg_value=None,
            gate_type=GateType.MOVE_GATE.value
    ) -> None:
        super().__init__("mov", targets, arg_value, gate_type,
                         hermitian=False)

    def default_decompose(self):
        return list([self])


def create_gate(name, targets=None, arg_value=None, allow_undefined=False):
    """
    创建Gate对象

    Args:
        name (_type_): 门名称
        targets (_type_, optional): 作用比特列表. Defaults to None.
        arg_value (_type_, optional): 参数列表. Defaults to None.
        allow_undefined (bool, optional): 是否允许自定义的门
    return:
        Gate: 门名称对应的量子比特门实例
    """
    if name == "h":
        return H(targets, arg_value)
    elif name == "x":
        return X(targets, arg_value)
    elif name == "y":
        return Y(targets, arg_value)
    elif name == "z":
        return Z(targets, arg_value)
    elif name == "rx":
        return RX(targets, arg_value)
    elif name == "ry":
        return RY(targets, arg_value)
    elif name == "rz":
        return RZ(targets, arg_value)
    elif name == "s":
        return S(targets, arg_value)
    elif name == "t":
        return T(targets, arg_value)
    elif name == "sdg":
        return SDG(targets, arg_value)
    elif name == "tdg":
        return TDG(targets, arg_value)
    elif name == "cx":
        return CX(targets, arg_value)
    elif name == "cy":
        return CY(targets, arg_value)
    elif name == "cz":
        return CZ(targets, arg_value)
    elif name == "ch":
        return CH(targets, arg_value)
    elif name == "crx":
        return CRX(targets, arg_value)
    elif name == "cry":
        return CRY(targets, arg_value)
    elif name == "crz":
        return CRZ(targets, arg_value)
    elif name == "ccx":
        return CCX(targets, arg_value)
    elif name == "u1":
        return U1(targets, arg_value)
    elif name == "u2":
        return U2(targets, arg_value)
    elif name == "u3":
        return U3(targets, arg_value)
    elif name == "sync":
        return SYNC(targets, arg_value)
    elif name == "measure":
        return MEASURE(targets, arg_value)
    else:
        if allow_undefined:
            return Gate(name, targets=targets, arg_value=arg_value)
        raise RuntimeError(f"{name} is not support")


def decomposer(ir: list):
    """
    将中间表示中的门分解到硬件脉冲直接支持的门上

    Args:
        ir (list): 中间表示
    return:
        gates(list): 硬件支持的门
    """
    gates = []
    for gate in ir:
        gates += gate.decompose()
    return gates


def pass_hermitian(ir: list):
    """如果末尾的两个门相同，且都为hermitian，则消去

    Args:
        ir (list): 中间表示
    """
    passed = False
    while True:
        if len(ir) < 2:
            break
        if ir[-1].name != ir[-2].name:
            break
        if ir[-1].targets != ir[-2].targets:
            break
        if ir[-1].hermitian:
            ir.pop(-1)
            ir.pop(-1)
            passed = True
            continue
        break
    return passed


def pass_merge_theta(ir: list):
    """如果末尾的两个门是作用在同一比特上的同一类旋转门，则角度可以合并

    Args:
        ir (list): 中间表示
    """
    passed = False
    while True:
        if len(ir) < 2:
            break
        if ir[-1].name != ir[-2].name:
            break
        if ir[-1].targets != ir[-2].targets:
            break
        if ir[-1].name in ["rx", "ry", "rz", "crx", "cry", "crz", "u1"]:
            ir[-2].arg_value[0] += ir[-1].arg_value[0]
            ir[-2].arg_value[0] %= (4 * np.pi)
            ir.pop(-1)
            if abs(ir[-1].arg_value[0]) < 1e-5:
                ir.pop(-1)
            passed = True
            continue
        break
    return passed


def pass_u_udg(ir: list):
    """如果末尾的两个门是作用在同一比特上的s和sdg或者t和tdg，则可以消去

    Args:
        ir (list): 中间表示
    """
    passed = False
    while True:
        if len(ir) < 2:
            break
        if ir[-1].targets != ir[-2].targets:
            break
        # pylint: disable=too-many-boolean-expressions
        if (ir[-1].name == "s" and ir[-2].name == "sdg") or (
                ir[-1].name == "sdg" and ir[-2].name == "s") or (
                ir[-1].name == "t" and ir[-2].name == "tdg") or (
                ir[-1].name == "tdg" and ir[-2].name == "t"):
            ir.pop(-1)
            ir.pop(-1)
            passed = True
            continue
        break
    return passed


def pass_three_gate_model(ir: list):
    """HZH -> X, HXH -> Z, XRy(θ)X -> Ry(-θ)

    Args:
        ir (list): 中间表示
    """
    passed = False
    while True:
        if len(ir) < 3:
            break
        if (ir[-1].targets != ir[-2].targets) or (
                ir[-1].targets != ir[-3].targets):
            break
        if ir[-1].name == "h" and ir[-3].name == "h":
            if ir[-2].name in ("x", "z"):
                ir.pop(-1)
                ori_gate = ir.pop(-1)
                ir.pop(-1)
                new_name = "z" if ori_gate.name == "x" else "x"
                ir.append(
                    create_gate(
                        new_name,
                        ori_gate.targets,
                        ori_gate.arg_value
                    )
                )
                passed = True
                continue
        if ir[-1].name == "x" and ir[-3].name == "x":
            if ir[-2].name == "ry":
                ir.pop(-1)
                ori_gate = ir.pop(-1)
                ir.pop(-1)
                ir.append(
                    create_gate(
                        ori_gate.name,
                        ori_gate.targets,
                        -1.0 * ori_gate.arg_value[0]
                    )
                )
                passed = True
                continue
        break
    return passed


def do_pass(ir: list):
    """一次执行pass，直到ir不发生变化

    Args:
        ir (list): 中间表示
    """
    passed = True
    while passed:
        passed = False
        passed |= pass_hermitian(ir)
        passed |= pass_merge_theta(ir)
        passed |= pass_u_udg(ir)
        passed |= pass_three_gate_model(ir)


def optimizer(ir: list):
    """基础门优化
    优化策略主要包含如下几个：
        1. 连续的两个作用在相同比特上的厄米共轭门可以消除
        2. 连续两个相同的选择门，可以合并旋转角
        3. 旋转角->0的门等同于I，可以忽略
        4. HZH -> X, HXH -> Z
        5. XRy(θ)X -> -Ry(θ)
    Args:
        ir (list): 中间表示

    return:
        optimize_gates(list): 优化后的门
    """
    optimize_gates = []
    for gate in ir:
        if isinstance(gate, MOV):
            optimize_gates.append(gate)
            continue

        optimize_gates.append(gate)
        do_pass(optimize_gates)

    return optimize_gates
