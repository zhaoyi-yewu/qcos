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

"""Binding qcos transpiler cpp functions."""

from __future__ import annotations
import pybind11_stubgen.typing_ext
import typing

__all__: list[str] = [
    "BaseOperation",
    "C3SQRTX",
    "C3X",
    "C4X",
    "CCX",
    "CH",
    "CP",
    "CRX",
    "CRY",
    "CRZ",
    "CS",
    "CSDG",
    "CSWAP",
    "CSX",
    "CU",
    "CU1",
    "CU3",
    "CX",
    "CY",
    "CZ",
    "Control",
    "ControlType",
    "CppMCTSRouting",
    "DCX",
    "DOUBLE_QUBIT_OPERATION",
    "Decomposer",
    "ECR",
    "FIVE_QUBIT_OPERATION",
    "FOUR_QUBIT_OPERATION",
    "GateOperation",
    "GreedyRouting",
    "H",
    "ISWAP",
    "MEASURE",
    "MOVE",
    "Measure",
    "Move",
    "Neg",
    "OpType",
    "Operation",
    "OperationType",
    "P",
    "ParamGate",
    "Pos",
    "R",
    "RC3X",
    "RCCX",
    "RX",
    "RXX",
    "RY",
    "RYY",
    "RZ",
    "RZX",
    "RZZ",
    "Reset",
    "S",
    "SABRE",
    "SDG",
    "SINGLE_QUBIT_OPERATION",
    "SWAP",
    "SX",
    "SXDG",
    "SYNC",
    "Sync",
    "T",
    "TDG",
    "TRIPLE_QUBIT_OPERATION",
    "U",
    "U1",
    "U2",
    "U3",
    "X",
    "Y",
    "Z",
    "complex",
    "convert_qasm_string_to_operations",
    "convert_qasm_string_to_qcos_operations",
    "load_config_file",
    "load_qasm_to_gate_list",
    "otAFalse",
    "otATrue",
    "otBarrier",
    "otC3SQRTX",
    "otC3X",
    "otC4X",
    "otCCZ",
    "otCH",
    "otCNOT",
    "otCP",
    "otCRX",
    "otCRY",
    "otCRZ",
    "otCS",
    "otCSWAP",
    "otCSX",
    "otCSdg",
    "otCU",
    "otCU3",
    "otCY",
    "otCZ",
    "otClassicControlled",
    "otCompound",
    "otDCX",
    "otECR",
    "otGPhase",
    "otH",
    "otI",
    "otMeasure",
    "otMultiAFalse",
    "otMultiATrue",
    "otNone",
    "otOpCount",
    "otP",
    "otPeres",
    "otPeresdg",
    "otR",
    "otRC3X",
    "otRCCX",
    "otRX",
    "otRXX",
    "otRY",
    "otRYY",
    "otRZ",
    "otRZX",
    "otRZZ",
    "otReset",
    "otS",
    "otSWAP",
    "otSX",
    "otSXdg",
    "otSdg",
    "otT",
    "otTOFFOLI",
    "otTdg",
    "otTeleportation",
    "otU",
    "otU1",
    "otU2",
    "otU3",
    "otV",
    "otVdg",
    "otW",
    "otX",
    "otXXminusYY",
    "otXXplusYY",
    "otY",
    "otZ",
    "ot_iSWAP",
    "ot_iSWAPdg",
    "optimize",
    "sabre_initial_mapping",
    "sabre_routing",
]

class BaseOperation:
    arg_value: list[float]
    targets: list[int]
    def __deepcopy__(self, arg0: dict) -> BaseOperation: ...
    def __init__(
        self,
        name: str,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def arg_value_to_string(self) -> str: ...
    def targets_to_string(self) -> str: ...
    def to_openqasm(self, qubit_prefix: str = "q") -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def operation_type(self) -> OperationType: ...

class C3SQRTX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(256)
    ]: ...

class C3X(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(256)
    ]: ...

class C4X(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(1024)
    ]: ...

class CCX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(64)
    ]: ...

class CH(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CP(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CRX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CRY(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CRZ(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CS(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CSDG(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CSWAP(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(64)
    ]: ...

class CSX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CU(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CU1(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CU3(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CY(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class CZ(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class ControlType:
    """Members.

    Pos

    Neg
    """

    Neg: typing.ClassVar[ControlType]  # value = <ControlType.Neg: 0>
    Pos: typing.ClassVar[ControlType]  # value = <ControlType.Pos: 1>
    __members__: typing.ClassVar[
        dict[str, ControlType]
    ]  # value = {'Pos': <ControlType.Pos: 1>, 'Neg': <ControlType.Neg: 0>}
    def __eq__(self, other: typing.Any) -> bool: ...
    def __getstate__(self) -> int: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __ne__(self, other: typing.Any) -> bool: ...
    def __repr__(self) -> str: ...
    def __setstate__(self, state: int) -> None: ...
    def __str__(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> int: ...

class Control:
    qubit: int
    type: ControlType
    def __init__(
        self, qubit: int = 0, type: ControlType = ControlType.Pos
    ) -> None: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...

class CppMCTSRouting:
    """C++ implementation of MCTS routing."""

    selec_times: int
    def __init__(self, selec_times: int = 5) -> None: ...
    def execute_routing(
        self,
        search_tree: typing.Any,
        ag: typing.Any,
        initial_layout: dict,
        num_q_vir: int,
        measure_ops: list,
    ) -> tuple: ...

class DCX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class Decomposer:
    def __init__(self) -> None: ...
    def apply_decompose_rules(
        self, arg0: list[BaseOperation], arg1: dict[ParamGate, list[ParamGate]]
    ) -> list: ...
    def get_decompose_rules(
        self, arg0: list[str], arg1: list[str]
    ) -> tuple: ...

class ECR(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class GateOperation(BaseOperation):
    def __deepcopy__(self, arg0: dict) -> GateOperation: ...
    def __init__(
        self,
        name: str,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
        hermitian: bool = False,
    ) -> None: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    @property
    def hermitian(self) -> bool: ...

class GreedyRouting:
    """Greedy blocked-gate routing: insert SWAP only when a gate is blocked."""

    def __init__(self, coupling_list: list[tuple[int, int]]) -> None: ...
    def execute(
        self, gates_list: list[GateOperation], initial_l2p: list[int] = []
    ) -> None: ...
    def get_physical_gates(self) -> list[GateOperation]: ...
    @property
    def logic2phy(self) -> list[int]: ...
    @property
    def phy2logic(self) -> list[int]: ...

class H(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class ISWAP(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class Measure(BaseOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...

class Move(BaseOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...

class OpType:
    """Members.

    otNone

    otGPhase

    otI

    otBarrier

    otH

    otX

    otY

    otZ

    otS

    otSdg

    otT

    otTdg

    otV

    otVdg

    otU

    otU2

    otP

    otSX

    otSXdg

    otRX

    otRY

    otRZ

    otSWAP

    ot_iSWAP

    ot_iSWAPdg

    otPeres

    otPeresdg

    otDCX

    otECR

    otRXX

    otRYY

    otRZZ

    otRZX

    otXXminusYY

    otXXplusYY

    otCompound

    otMeasure

    otReset

    otTeleportation

    otClassicControlled

    otATrue

    otAFalse

    otMultiATrue

    otMultiAFalse

    otOpCount

    otCNOT

    otTOFFOLI

    otCZ

    otU3

    otCU

    otU1

    otCH

    otCRX

    otCRY

    otCRZ

    otRCCX

    otRC3X

    otCP

    otCSWAP

    otC3X

    otCY

    otCSX

    otC3SQRTX

    otCU3

    otC4X

    otCS

    otCSdg

    otCCZ

    otR

    otW
    """

    __members__: typing.ClassVar[
        dict[str, OpType]
    ]  # value = {'otNone': <OpType.otNone: 0>,
    # 'otGPhase': <OpType.otGPhase: 1>, 'otI': <OpType.otI: 2>,
    # 'otBarrier': <OpType.otBarrier: 3>, 'otH': <OpType.otH: 4>,
    # 'otX': <OpType.otX: 5>, 'otY': <OpType.otY: 6>, 'otZ': <OpType.otZ: 7>,
    # 'otS': <OpType.otS: 8>, 'otSdg': <OpType.otSdg: 9>,
    # 'otT': <OpType.otT: 10>, 'otTdg': <OpType.otTdg: 11>,
    # 'otV': <OpType.otV: 12>, 'otVdg': <OpType.otVdg: 13>,
    # 'otU': <OpType.otU: 14>, 'otU2': <OpType.otU2: 15>,
    # 'otP': <OpType.otP: 16>, 'otSX': <OpType.otSX: 17>,
    # 'otSXdg': <OpType.otSXdg: 18>, 'otRX': <OpType.otRX: 19>,
    # 'otRY': <OpType.otRY: 20>, 'otRZ': <OpType.otRZ: 21>,
    # 'otSWAP': <OpType.otSWAP: 22>, 'ot_iSWAP': <OpType.ot_iSWAP: 23>,
    # 'ot_iSWAPdg': <OpType.ot_iSWAPdg: 24>, 'otPeres': <OpType.otPeres: 25>,
    # 'otPeresdg': <OpType.otPeresdg: 26>, 'otDCX': <OpType.otDCX: 27>,
    # 'otECR': <OpType.otECR: 28>, 'otRXX': <OpType.otRXX: 29>,
    # 'otRYY': <OpType.otRYY: 30>, 'otRZZ': <OpType.otRZZ: 31>,
    # 'otRZX': <OpType.otRZX: 32>, 'otXXminusYY': <OpType.otXXminusYY: 33>,
    # 'otXXplusYY': <OpType.otXXplusYY: 34>,
    # 'otCompound': <OpType.otCompound: 35>,
    # 'otMeasure': <OpType.otMeasure: 36>,
    # 'otReset': <OpType.otReset: 37>,
    # 'otTeleportation': <OpType.otTeleportation: 38>,
    # 'otClassicControlled': <OpType.otClassicControlled: 39>,
    # 'otATrue': <OpType.otATrue: 40>, 'otAFalse': <OpType.otAFalse: 41>,
    # 'otMultiATrue': <OpType.otMultiATrue: 42>,
    # 'otMultiAFalse': <OpType.otMultiAFalse: 43>,
    # 'otOpCount': <OpType.otOpCount: 44>,
    # 'otCNOT': <OpType.otCNOT: 45>, 'otTOFFOLI': <OpType.otTOFFOLI: 46>,
    # 'otCZ': <OpType.otCZ: 47>, 'otU3': <OpType.otU3: 48>,
    # 'otCU': <OpType.otCU: 49>, 'otU1': <OpType.otU1: 50>,
    # 'otCH': <OpType.otCH: 51>, 'otCRX': <OpType.otCRX: 52>,
    # 'otCRY': <OpType.otCRY: 53>, 'otCRZ': <OpType.otCRZ: 54>,
    # 'otRCCX': <OpType.otRCCX: 55>, 'otRC3X': <OpType.otRC3X: 56>,
    # 'otCP': <OpType.otCP: 57>, 'otCSWAP': <OpType.otCSWAP: 58>,
    # 'otC3X': <OpType.otC3X: 59>, 'otCY': <OpType.otCY: 60>,
    # 'otCSX': <OpType.otCSX: 61>, 'otC3SQRTX': <OpType.otC3SQRTX: 62>,
    # 'otCU3': <OpType.otCU3: 63>, 'otC4X': <OpType.otC4X: 64>,
    # 'otCS': <OpType.otCS: 65>, 'otCSdg': <OpType.otCSdg: 66>,
    # 'otCCZ': <OpType.otCCZ: 67>, 'otR': <OpType.otR: 68>,
    # 'otW': <OpType.otW: 69>}
    otAFalse: typing.ClassVar[OpType]  # value = <OpType.otAFalse: 41>
    otATrue: typing.ClassVar[OpType]  # value = <OpType.otATrue: 40>
    otBarrier: typing.ClassVar[OpType]  # value = <OpType.otBarrier: 3>
    otC3SQRTX: typing.ClassVar[OpType]  # value = <OpType.otC3SQRTX: 62>
    otC3X: typing.ClassVar[OpType]  # value = <OpType.otC3X: 59>
    otC4X: typing.ClassVar[OpType]  # value = <OpType.otC4X: 64>
    otCCZ: typing.ClassVar[OpType]  # value = <OpType.otCCZ: 67>
    otCH: typing.ClassVar[OpType]  # value = <OpType.otCH: 51>
    otCNOT: typing.ClassVar[OpType]  # value = <OpType.otCNOT: 45>
    otCP: typing.ClassVar[OpType]  # value = <OpType.otCP: 57>
    otCRX: typing.ClassVar[OpType]  # value = <OpType.otCRX: 52>
    otCRY: typing.ClassVar[OpType]  # value = <OpType.otCRY: 53>
    otCRZ: typing.ClassVar[OpType]  # value = <OpType.otCRZ: 54>
    otCS: typing.ClassVar[OpType]  # value = <OpType.otCS: 65>
    otCSWAP: typing.ClassVar[OpType]  # value = <OpType.otCSWAP: 58>
    otCSX: typing.ClassVar[OpType]  # value = <OpType.otCSX: 61>
    otCSdg: typing.ClassVar[OpType]  # value = <OpType.otCSdg: 66>
    otCU: typing.ClassVar[OpType]  # value = <OpType.otCU: 49>
    otCU3: typing.ClassVar[OpType]  # value = <OpType.otCU3: 63>
    otCY: typing.ClassVar[OpType]  # value = <OpType.otCY: 60>
    otCZ: typing.ClassVar[OpType]  # value = <OpType.otCZ: 47>
    otClassicControlled: typing.ClassVar[
        OpType
    ]  # value = <OpType.otClassicControlled: 39>
    otCompound: typing.ClassVar[OpType]  # value = <OpType.otCompound: 35>
    otDCX: typing.ClassVar[OpType]  # value = <OpType.otDCX: 27>
    otECR: typing.ClassVar[OpType]  # value = <OpType.otECR: 28>
    otGPhase: typing.ClassVar[OpType]  # value = <OpType.otGPhase: 1>
    otH: typing.ClassVar[OpType]  # value = <OpType.otH: 4>
    otI: typing.ClassVar[OpType]  # value = <OpType.otI: 2>
    otMeasure: typing.ClassVar[OpType]  # value = <OpType.otMeasure: 36>
    otMultiAFalse: typing.ClassVar[
        OpType
    ]  # value = <OpType.otMultiAFalse: 43>
    otMultiATrue: typing.ClassVar[OpType]  # value = <OpType.otMultiATrue: 42>
    otNone: typing.ClassVar[OpType]  # value = <OpType.otNone: 0>
    otOpCount: typing.ClassVar[OpType]  # value = <OpType.otOpCount: 44>
    otP: typing.ClassVar[OpType]  # value = <OpType.otP: 16>
    otPeres: typing.ClassVar[OpType]  # value = <OpType.otPeres: 25>
    otPeresdg: typing.ClassVar[OpType]  # value = <OpType.otPeresdg: 26>
    otR: typing.ClassVar[OpType]  # value = <OpType.otR: 68>
    otRC3X: typing.ClassVar[OpType]  # value = <OpType.otRC3X: 56>
    otRCCX: typing.ClassVar[OpType]  # value = <OpType.otRCCX: 55>
    otRX: typing.ClassVar[OpType]  # value = <OpType.otRX: 19>
    otRXX: typing.ClassVar[OpType]  # value = <OpType.otRXX: 29>
    otRY: typing.ClassVar[OpType]  # value = <OpType.otRY: 20>
    otRYY: typing.ClassVar[OpType]  # value = <OpType.otRYY: 30>
    otRZ: typing.ClassVar[OpType]  # value = <OpType.otRZ: 21>
    otRZX: typing.ClassVar[OpType]  # value = <OpType.otRZX: 32>
    otRZZ: typing.ClassVar[OpType]  # value = <OpType.otRZZ: 31>
    otReset: typing.ClassVar[OpType]  # value = <OpType.otReset: 37>
    otS: typing.ClassVar[OpType]  # value = <OpType.otS: 8>
    otSWAP: typing.ClassVar[OpType]  # value = <OpType.otSWAP: 22>
    otSX: typing.ClassVar[OpType]  # value = <OpType.otSX: 17>
    otSXdg: typing.ClassVar[OpType]  # value = <OpType.otSXdg: 18>
    otSdg: typing.ClassVar[OpType]  # value = <OpType.otSdg: 9>
    otT: typing.ClassVar[OpType]  # value = <OpType.otT: 10>
    otTOFFOLI: typing.ClassVar[OpType]  # value = <OpType.otTOFFOLI: 46>
    otTdg: typing.ClassVar[OpType]  # value = <OpType.otTdg: 11>
    otTeleportation: typing.ClassVar[
        OpType
    ]  # value = <OpType.otTeleportation: 38>
    otU: typing.ClassVar[OpType]  # value = <OpType.otU: 14>
    otU1: typing.ClassVar[OpType]  # value = <OpType.otU1: 50>
    otU2: typing.ClassVar[OpType]  # value = <OpType.otU2: 15>
    otU3: typing.ClassVar[OpType]  # value = <OpType.otU3: 48>
    otV: typing.ClassVar[OpType]  # value = <OpType.otV: 12>
    otVdg: typing.ClassVar[OpType]  # value = <OpType.otVdg: 13>
    otW: typing.ClassVar[OpType]  # value = <OpType.otW: 69>
    otX: typing.ClassVar[OpType]  # value = <OpType.otX: 5>
    otXXminusYY: typing.ClassVar[OpType]  # value = <OpType.otXXminusYY: 33>
    otXXplusYY: typing.ClassVar[OpType]  # value = <OpType.otXXplusYY: 34>
    otY: typing.ClassVar[OpType]  # value = <OpType.otY: 6>
    otZ: typing.ClassVar[OpType]  # value = <OpType.otZ: 7>
    ot_iSWAP: typing.ClassVar[OpType]  # value = <OpType.ot_iSWAP: 23>
    ot_iSWAPdg: typing.ClassVar[OpType]  # value = <OpType.ot_iSWAPdg: 24>
    def __eq__(self, other: typing.Any) -> bool: ...
    def __getstate__(self) -> int: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __ne__(self, other: typing.Any) -> bool: ...
    def __repr__(self) -> str: ...
    def __setstate__(self, state: int) -> None: ...
    def __str__(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> int: ...

class Operation:
    @property
    def controls(self) -> set[Control]: ...
    @property
    def name(self) -> str: ...
    @property
    def parameter(self) -> list[float]: ...
    @property
    def targets(self) -> list[int]: ...
    @property
    def type(self) -> OpType: ...

class OperationType:
    """Members.

    MEASURE

    SINGLE_QUBIT_OPERATION

    DOUBLE_QUBIT_OPERATION

    TRIPLE_QUBIT_OPERATION

    FOUR_QUBIT_OPERATION

    FIVE_QUBIT_OPERATION

    SYNC

    MOVE
    """

    DOUBLE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.DOUBLE_QUBIT_OPERATION: 2>
    FIVE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.FIVE_QUBIT_OPERATION: 5>
    FOUR_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.FOUR_QUBIT_OPERATION: 4>
    MEASURE: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.MEASURE: 0>
    MOVE: typing.ClassVar[OperationType]  # value = <OperationType.MOVE: -2>
    SINGLE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.SINGLE_QUBIT_OPERATION: 1>
    SYNC: typing.ClassVar[OperationType]  # value = <OperationType.SYNC: -1>
    TRIPLE_QUBIT_OPERATION: typing.ClassVar[
        OperationType
    ]  # value = <OperationType.TRIPLE_QUBIT_OPERATION: 3>
    __members__: typing.ClassVar[dict[str, OperationType]]
    def __eq__(self, other: typing.Any) -> bool: ...
    def __getstate__(self) -> int: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __ne__(self, other: typing.Any) -> bool: ...
    def __repr__(self) -> str: ...
    def __setstate__(self, state: int) -> None: ...
    def __str__(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> int: ...

class P(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class ParamGate:
    name: str
    params: list[str]
    qubits: list[str]
    def __init__(self) -> None: ...

class R(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class RC3X(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(256)
    ]: ...

class RCCX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def decompose_to_1q2q(self) -> list[BaseOperation]: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(64)
    ]: ...

class RX(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class RXX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class RY(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class RYY(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class RZ(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class RZX(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class RZZ(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class Reset(BaseOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...

class S(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class SABRE:
    """SABRE quantum routing algorithm."""

    def __init__(
        self,
        coupling_list: list[tuple[int, int]],
        extension_size: int = 20,
        weight: float = 0.5,
        decay: float = 0.001,
    ) -> None:
        """Construct a SABRE router.

        Args:
            coupling_list (list[tuple[int, int]]): Physical qubit connectivity
                graph.
            extension_size (int, optional): Size of the lookahead set.
                Defaults to 20.
            weight (float, optional): Weight between front layer and lookahead
                cost. Defaults to 0.5.
            decay (float, optional): SWAP decay coefficient. Defaults to 0.001.
        """

    def execute(
        self, gates_list: list[GateOperation], initial_l2p: list[int] = []
    ) -> None:
        """Execute SABRE routing.

        Args:
            gates_list (list[GateOperation]): Logical gate sequence.
            initial_l2p (list[int], optional): Initial logical-to-physical
                mapping. Defaults to empty.

        Returns:
            None
        """

    def get_logic2phy(self) -> list[int]:
        """Get the final logical-to-physical mapping after routing.

        Returns:
            list[int]: The index is logical qubit and value is physical qubit.
        """
    def get_physical_gates(self) -> list[GateOperation]:
        """Get the sequence of mapped physical gates after routing.

        Returns:
            list[GateOperation]: The physical gate sequence.
        """

class SDG(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class SWAP(GateOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(16)
    ]: ...

class SX(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class SXDG(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class Sync(BaseOperation):
    @typing.overload
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        targets: list[int],
        arg_value: list[float],
        operation_type: OperationType,
    ) -> None: ...
    def __repr__(self) -> str: ...

class T(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class TDG(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class U(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class U1(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class U2(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class U3(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class X(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class Y(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class Z(GateOperation):
    def __init__(
        self, targets: list[int], arg_value: list[float] = []
    ) -> None: ...
    def __repr__(self) -> str: ...
    def default_decompose(self) -> list[BaseOperation]: ...
    def to_matrix(
        self,
    ) -> typing.Annotated[
        list[complex], pybind11_stubgen.typing_ext.FixedSize(4)
    ]: ...

class complex:
    def __init__(self, arg0: float, arg1: float) -> None: ...
    @property
    def imag(self) -> float: ...
    @property
    def real(self) -> float: ...

def convert_qasm_string_to_operations(qasm_str: str) -> list[Operation]:
    """将QASM字符串转换为操作列表.

    Args:
        qasm_str: QASM格式的量子电路字符串

    Returns:
        返回解析得到的量子操作列表

    Example:
        >>> import high_performance
        >>> qasm = "OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0], q[1];"
        >>> ops = high_performance.convert_qasm_string_to_operations(qasm)
        >>> print(f"解析到 {len(ops)} 个操作")
    """

def convert_qasm_string_to_qcos_operations(
    qasm_str: str,
) -> tuple[list[BaseOperation], int]:
    """将QASM字符串转换为操作列表.

    Args:
        qasm_str: QASM格式的量子电路字符串

    Returns:
        返回解析得到的量子操作列表

    Example:
        >>> import high_performance
        >>> qasm = "OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0], q[1];"
        >>> ops, num_qubits = (
        ...     high_performance.convert_qasm_string_to_qcos_operations(qasm)
        ... )
        >>> print(f"解析到 {len(ops)} 个操作")
    """

def load_config_file(filename: str) -> list[tuple[int, int]]:
    """从配置文件中加载量子芯片耦合列表.

    Args:
        filename (str): 配置文件路径

    Returns:
        list[tuple[int,int]]: 耦合对列表
    """

def load_qasm_to_gate_list(filename: str) -> list[GateOperation]:
    """将QASM文件加载为门操作列表.

    Args:
        filename (str): QASM文件路径

    Returns:
        list[GateOperation]: 解析得到的门操作列表
    """

def create_gate(
    name: str,
    targets: list[int] = ...,
    arg_value: list[float] = ...,
    allow_undefined: bool = ...,
) -> BaseOperation:
    """根据名称创建门或操作对象."""

def optimize(
    ir: list[BaseOperation],
    opt_level: int = 1,
    verbose: bool = False,
    basis_gates: set[str] | None = None,
) -> list[BaseOperation]:
    """对 IR 执行优化.

    opt_level:
      0 - 不做优化
      1 - InverseCancellation + AdjacentPhaseOptPass
      2 - Level 1 + EquivalencePass
      3 - Level 2 + CliffordRzOptimization

    Args:
        ir (list[BaseOperation]): 待优化的操作序列
        opt_level (int, optional): 优化级别. Defaults to 1.
        verbose (bool, optional): 是否打印优化详情. Defaults to False.
        basis_gates (set[str] | None, optional): basis gate 过滤集合.

    Returns:
        list[BaseOperation]: 优化后的操作序列
    """

def sabre_initial_mapping(
    gates_list: list[GateOperation], coupling_list: list[tuple[int, int]]
) -> list[int]:
    """Get the initial mapping using the SABRE algorithm.

    Args:
        gates_list (list[GateOperation]): Logical gate sequence.
        coupling_list (list[tuple[int, int]]): Physical qubit coupling list.

    Returns:
        list[int]: The initial logical-to-physical mapping.
    """

def sabre_routing(
    gates_list: list[BaseOperation],
    coupling_list: list[tuple[int, int]],
    initial_l2p: list[int] = ...,
    extension_size: typing.SupportsInt = ...,
    weight: typing.SupportsFloat = ...,
    decay: typing.SupportsFloat = ...,
) -> list[BaseOperation]:
    """Execute SABRE routing for BaseOperation lists."""

DOUBLE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.DOUBLE_QUBIT_OPERATION: 2>
)
FIVE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.FIVE_QUBIT_OPERATION: 5>
)
FOUR_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.FOUR_QUBIT_OPERATION: 4>
)
MEASURE: OperationType  # value = <OperationType.MEASURE: 0>
MOVE: OperationType  # value = <OperationType.MOVE: -2>
Neg: ControlType  # value = <ControlType.Neg: 0>
Pos: ControlType  # value = <ControlType.Pos: 1>
SINGLE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.SINGLE_QUBIT_OPERATION: 1>
)
SYNC: OperationType  # value = <OperationType.SYNC: -1>
TRIPLE_QUBIT_OPERATION: (
    OperationType  # value = <OperationType.TRIPLE_QUBIT_OPERATION: 3>
)
otAFalse: OpType  # value = <OpType.otAFalse: 41>
otATrue: OpType  # value = <OpType.otATrue: 40>
otBarrier: OpType  # value = <OpType.otBarrier: 3>
otC3SQRTX: OpType  # value = <OpType.otC3SQRTX: 62>
otC3X: OpType  # value = <OpType.otC3X: 59>
otC4X: OpType  # value = <OpType.otC4X: 64>
otCCZ: OpType  # value = <OpType.otCCZ: 67>
otCH: OpType  # value = <OpType.otCH: 51>
otCNOT: OpType  # value = <OpType.otCNOT: 45>
otCP: OpType  # value = <OpType.otCP: 57>
otCRX: OpType  # value = <OpType.otCRX: 52>
otCRY: OpType  # value = <OpType.otCRY: 53>
otCRZ: OpType  # value = <OpType.otCRZ: 54>
otCS: OpType  # value = <OpType.otCS: 65>
otCSWAP: OpType  # value = <OpType.otCSWAP: 58>
otCSX: OpType  # value = <OpType.otCSX: 61>
otCSdg: OpType  # value = <OpType.otCSdg: 66>
otCU: OpType  # value = <OpType.otCU: 49>
otCU3: OpType  # value = <OpType.otCU3: 63>
otCY: OpType  # value = <OpType.otCY: 60>
otCZ: OpType  # value = <OpType.otCZ: 47>
otClassicControlled: OpType  # value = <OpType.otClassicControlled: 39>
otCompound: OpType  # value = <OpType.otCompound: 35>
otDCX: OpType  # value = <OpType.otDCX: 27>
otECR: OpType  # value = <OpType.otECR: 28>
otGPhase: OpType  # value = <OpType.otGPhase: 1>
otH: OpType  # value = <OpType.otH: 4>
otI: OpType  # value = <OpType.otI: 2>
otMeasure: OpType  # value = <OpType.otMeasure: 36>
otMultiAFalse: OpType  # value = <OpType.otMultiAFalse: 43>
otMultiATrue: OpType  # value = <OpType.otMultiATrue: 42>
otNone: OpType  # value = <OpType.otNone: 0>
otOpCount: OpType  # value = <OpType.otOpCount: 44>
otP: OpType  # value = <OpType.otP: 16>
otPeres: OpType  # value = <OpType.otPeres: 25>
otPeresdg: OpType  # value = <OpType.otPeresdg: 26>
otR: OpType  # value = <OpType.otR: 68>
otRC3X: OpType  # value = <OpType.otRC3X: 56>
otRCCX: OpType  # value = <OpType.otRCCX: 55>
otRX: OpType  # value = <OpType.otRX: 19>
otRXX: OpType  # value = <OpType.otRXX: 29>
otRY: OpType  # value = <OpType.otRY: 20>
otRYY: OpType  # value = <OpType.otRYY: 30>
otRZ: OpType  # value = <OpType.otRZ: 21>
otRZX: OpType  # value = <OpType.otRZX: 32>
otRZZ: OpType  # value = <OpType.otRZZ: 31>
otReset: OpType  # value = <OpType.otReset: 37>
otS: OpType  # value = <OpType.otS: 8>
otSWAP: OpType  # value = <OpType.otSWAP: 22>
otSX: OpType  # value = <OpType.otSX: 17>
otSXdg: OpType  # value = <OpType.otSXdg: 18>
otSdg: OpType  # value = <OpType.otSdg: 9>
otT: OpType  # value = <OpType.otT: 10>
otTOFFOLI: OpType  # value = <OpType.otTOFFOLI: 46>
otTdg: OpType  # value = <OpType.otTdg: 11>
otTeleportation: OpType  # value = <OpType.otTeleportation: 38>
otU: OpType  # value = <OpType.otU: 14>
otU1: OpType  # value = <OpType.otU1: 50>
otU2: OpType  # value = <OpType.otU2: 15>
otU3: OpType  # value = <OpType.otU3: 48>
otV: OpType  # value = <OpType.otV: 12>
otVdg: OpType  # value = <OpType.otVdg: 13>
otW: OpType  # value = <OpType.otW: 69>
otX: OpType  # value = <OpType.otX: 5>
otXXminusYY: OpType  # value = <OpType.otXXminusYY: 33>
otXXplusYY: OpType  # value = <OpType.otXXplusYY: 34>
otY: OpType  # value = <OpType.otY: 6>
otZ: OpType  # value = <OpType.otZ: 7>
ot_iSWAP: OpType  # value = <OpType.ot_iSWAP: 23>
ot_iSWAPdg: OpType  # value = <OpType.ot_iSWAPdg: 24>
