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

from wy_qcos.transpiler.high_performance import (
    GateOperation as GateOperation_cpp,
    OperationType as OperationType_cpp,
    create_gate as create_gate_cpp,
    load_qasm_to_gate_list,
)
from wy_qcos.common.cmss.gate_operation import (
    OperationType,
    GateOperation,
    create_gate,
)


def load_qasm_to_ir(file_path: str, code_type: str = "cpp"):
    """Load qasm file to gate list.

    Args:
        file_path (str): qasm file path.
        code_type (str, optional): GateOperation type, can be 'cpp' or 'py'.
            Defaults to "cpp".

    Returns:
        list[GateOperation]: gate list.
    """
    if code_type == "cpp":
        return load_qasm_to_gate_list(file_path)
    elif code_type == "py":
        ir_cpp = load_qasm_to_gate_list(file_path)
        ir_py = []
        for gate in ir_cpp:
            if gate.operation_type == OperationType_cpp.SINGLE_QUBIT_OPERATION:
                op_type = OperationType.SINGLE_QUBIT_OPERATION
            elif (
                gate.operation_type == OperationType_cpp.DOUBLE_QUBIT_OPERATION
            ):
                op_type = OperationType.DOUBLE_QUBIT_OPERATION
            else:
                raise ValueError("not support more than two qubits.")
            gate_py = GateOperation(
                gate.name, gate.targets, gate.arg_value, op_type.value
            )
            ir_py.append(gate_py)
        return ir_py
    else:
        raise NotImplementedError("Code type must be 'cpp' or 'py'")


def convert_ir_py2cpp(ir_py: list[GateOperation]):
    ir_cpp = []
    for gate in ir_py:
        # use cpp version `create_gate` function.
        gate_cpp = create_gate_cpp(
            gate.name,
            [int(t) for t in gate.targets],
            [float(a) for a in gate.arg_value],
        )
        ir_cpp.append(gate_cpp)
    return ir_cpp


def convert_ir_cpp2py(ir_cpp: list[GateOperation_cpp]):
    ir_py = []
    for gate in ir_cpp:
        # use py version `create_gate` function.
        gate_py = create_gate(
            gate.name,
            gate.targets,
            gate.arg_value,
        )
        ir_py.append(gate_py)
    return ir_py
