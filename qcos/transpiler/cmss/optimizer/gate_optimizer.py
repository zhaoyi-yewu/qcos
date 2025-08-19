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

from qcos.transpiler.cmss.common.gate_operation import create_gate
from qcos.transpiler.cmss.common.move import Move


def pass_hermitian(ir: list):
    """
    如果末尾的两个门相同，且都为hermitian，则消去

    param: ir (list): 中间表示
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
    """
    如果末尾的两个门是作用在同一比特上的同一类旋转门，则角度可以合并

    param: ir (list): 中间表示
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
    """
    如果末尾的两个门是作用在同一比特上的s和sdg或者t和tdg，则可以消去

    param: ir (list): 中间表示
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
    """
    HZH -> X, HXH -> Z, XRy(θ)X -> Ry(-θ)

    param: ir (list): 中间表示
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
    """
    一次执行pass，直到ir不发生变化

    param: ir (list): 中间表示
    """
    passed = True
    while passed:
        passed = False
        passed |= pass_hermitian(ir)
        passed |= pass_merge_theta(ir)
        passed |= pass_u_udg(ir)
        passed |= pass_three_gate_model(ir)


def optimize_gate(ir: list):
    """
    基础门优化
    优化策略主要包含如下几个：
        1. 连续的两个作用在相同比特上的厄米共轭门可以消除
        2. 连续两个相同的选择门，可以合并旋转角
        3. 旋转角->0的门等同于I，可以忽略
        4. HZH -> X, HXH -> Z
        5. XRy(θ)X -> -Ry(θ)

    param: ir (list): 中间表示
    return: optimize_gates(list): 优化后的门
    """
    optimize_gates = []
    for gate in ir:
        if isinstance(gate, Move):
            optimize_gates.append(gate)
            continue

        optimize_gates.append(gate)
        do_pass(optimize_gates)

    return optimize_gates
