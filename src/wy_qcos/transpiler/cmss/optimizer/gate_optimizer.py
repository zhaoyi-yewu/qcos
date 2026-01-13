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

from typing import Any
import numpy as np

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.common.gate_operation import (
    create_gate,
    H,
    CX,
    S,
    SDG,
    X,
    Y,
    Z,
    SWAP,
    T,
    TDG,
    CZ,
    CCX,
)
from wy_qcos.transpiler.cmss.common.move import Move
from wy_qcos.transpiler.cmss.common.reset import Reset
from wy_qcos.transpiler.cmss.optimizer.inverse_cancellation import (
    InverseCancellation,
)
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.optimizer.clifford_rz_optimization import (
    CliffordRzOptimization,
)
from wy_qcos.transpiler.cmss.optimizer.subcircuit_rewrite import (
    EquivalencePass,
)
from wy_qcos.transpiler.cmss.optimizer.adjacent_optimization import (
    AdjacentPhaseOptPass,
)


def pass_hermitian(ir: list):
    """如果末尾的两个门相同，且都为hermitian，则消去.

    Args:
        ir (list): 中间表示

    Returns:
        passed
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
    """如果末尾的两个门是作用在同一比特上的同一类旋转门，则角度可以合并.

    Args:
        ir (list): 中间表示

    Returns:
        passed
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
            ir[-2].arg_value[0] %= 4 * np.pi
            ir.pop(-1)
            if abs(ir[-1].arg_value[0]) < 1e-5:
                ir.pop(-1)
            passed = True
            continue
        break
    return passed


def pass_u_udg(ir: list):
    """如果末尾的两个门是作用在同一比特上的s和sdg或者t和tdg，则可以消去.

    Args:
      ir (list): 中间表示

    Returns:
        passes
    """
    passed = False
    while True:
        if len(ir) < 2:
            break
        if ir[-1].targets != ir[-2].targets:
            break
        # pylint: disable=too-many-boolean-expressions
        if (
            (ir[-1].name == "s" and ir[-2].name == "sdg")
            or (ir[-1].name == "sdg" and ir[-2].name == "s")
            or (ir[-1].name == "t" and ir[-2].name == "tdg")
            or (ir[-1].name == "tdg" and ir[-2].name == "t")
        ):
            ir.pop(-1)
            ir.pop(-1)
            passed = True
            continue
        break
    return passed


def pass_three_gate_model(ir: list):
    """HZH -> X, HXH -> Z, XRy(θ)X -> Ry(-θ).

    Args:
        ir (list): 中间表示

    Returns:
        passes
    """
    passed = False
    while True:
        if len(ir) < 3:
            break
        if (ir[-1].targets != ir[-2].targets) or (
            ir[-1].targets != ir[-3].targets
        ):
            break
        if ir[-1].name == "h" and ir[-3].name == "h":
            if ir[-2].name in ("x", "z"):
                ir.pop(-1)
                ori_gate = ir.pop(-1)
                ir.pop(-1)
                new_name = "z" if ori_gate.name == "x" else "x"
                ir.append(
                    create_gate(new_name, ori_gate.targets, ori_gate.arg_value)
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
                        -1.0 * ori_gate.arg_value[0],
                    )
                )
                passed = True
                continue
        break
    return passed


def do_pass(ir: list):
    """一次执行pass，直到ir不发生变化.

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


def optimize_gate(
    ir: list, opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL
):
    """基础门优化.

    优化策略主要包含如下几个：
        1. 连续的两个作用在相同比特上的厄米共轭门可以消除
        2. 连续两个相同的选择门，可以合并旋转角
        3. 旋转角->0的门等同于I，可以忽略
        4. HZH -> X, HXH -> Z
        5. XRy(θ)X -> -Ry(θ)

    Args:
        ir (list): ir
        opt_level (int): optimization level

    Returns:
        optimized gates
    """
    if opt_level < Constant.DEFAULT_OPTIMIZATION_LEVEL:
        return ir
    optimize_gates = []
    for gate in ir:
        if isinstance(gate, Move) or isinstance(gate, Reset):
            optimize_gates.append(gate)
            continue

        optimize_gates.append(gate)
        do_pass(optimize_gates)

    return optimize_gates


def do_optimize_pass(dag: DAGCircuit, pass_list: list):
    """Iteratively apply optimization passes.

    Iteratively apply a sequence of optimization passes to a DAGCircuit
    until no further reduction in circuit size is observed.

    Args:
        dag (DAGCircuit): The DAGCircuit to be optimized.
        pass_list (list): A list of optimization passes.
    """
    while True:
        init_size = dag.size()
        for pass_ in pass_list:
            pass_.run(dag)
        new_size = dag.size()
        if new_size >= init_size:
            break


def optimize(
    ir: list,
    opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
    verbose=False,
):
    """Optimize the input ir.

    Args:
        ir (list): the ir to be optimized.
        opt_level (int, optional): optimization level. Defaults to 1.
        verbose (bool, optional): whether print optimization information.
            Defaults to False.

    Returns:
        list: optimized ir.
    """
    if opt_level == 0:
        return ir
    elif opt_level > 3 or opt_level < 0:
        raise ValueError(f"Optimization level {opt_level} is not supported.")

    dag = DAGCircuit.ir_to_dag(ir)

    inverse_optimizer = InverseCancellation([
        H(),
        CX(),
        (S(), SDG()),
        (T(), TDG()),
        X(),
        Y(),
        Z(),
        SWAP(),
        CZ(),
        CCX(),
    ])
    equivalence_optimizer = EquivalencePass()
    adjacent_phase_optimizer = AdjacentPhaseOptPass()
    commutative_optimizer = CliffordRzOptimization(verbose=verbose)

    # The passes in the current optimization levels are not the final versions.
    # For example, in the future, single-qubit synthesis optimization will be
    # added to Level 1 and Level 2, and two-qubit gate synthesis optimization
    # will be added to Level 3.
    _opt: list[Any] = []
    if opt_level == 1:
        _opt = [
            inverse_optimizer,
            adjacent_phase_optimizer,
            equivalence_optimizer,
        ]
    elif opt_level == 2:
        _opt = [
            inverse_optimizer,
            adjacent_phase_optimizer,
            equivalence_optimizer,
            commutative_optimizer,
        ]
    elif opt_level == 3:
        _opt = [
            inverse_optimizer,
            adjacent_phase_optimizer,
            equivalence_optimizer,
            commutative_optimizer,
        ]
    else:
        raise ValueError(f"Optimization level {opt_level} is not supported.")

    do_optimize_pass(dag, _opt)

    ir = []
    for node in dag.topological_op_nodes():
        ir.append(node.op)
    return ir
