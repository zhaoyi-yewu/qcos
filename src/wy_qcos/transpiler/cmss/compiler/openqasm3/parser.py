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

import openqasm3

from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.compiler.openqasm3.convertor import ConvertVisitor


def convert(node: openqasm3.ast.Program) -> QuantumCircuit:
    """Convert a parsed OpenQASM 3 program in AST form, into a QuantumCircuit.

    Args:
        node: The root node of the AST.

    Returns:
        QuantumCircuit: The converted circuit.
    """
    return ConvertVisitor().convert(node)


def parse(
    input_: str,
) -> QuantumCircuit:
    """Parses the OpenQASM 3 program into AST form.

    And then converts the output to QuantumCircuit form.

    Args:
        input_: The OpenQASM 3 program to parse and convert.

    Returns:
        QuantumCircuit: The converted circuit.
    """
    return convert(openqasm3.parse(input_))
