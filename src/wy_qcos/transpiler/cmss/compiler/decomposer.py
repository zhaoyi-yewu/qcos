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

from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation


def decompose_gates(ir: list, supp_basis_gates: list):
    """将中间表示中的门分解到硬件脉冲直接支持的门上.

    Args:
        ir: 中间表示，类型为list
        supp_basis_gates: 支持的基础门列表，类型为list

    Returns:
        硬件支持的门，类型为list
    """
    gates = []
    for gate in ir:
        if (
            isinstance(gate, GateOperation)
            and gate.name not in supp_basis_gates
        ):
            gates += gate.decompose()
        else:
            gates += [gate]
    return gates
