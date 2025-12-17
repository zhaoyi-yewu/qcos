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

from functools import cached_property

import numpy as np

from qcos.transpiler.cmss.optimizer.template import (
    OptimizingTemplate,
    generate_hadamard_gate_templates,
    replace_all,
    generate_single_qubit_gate_templates,
)
from qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from qcos.transpiler.cmss.circuit.dag_node import DAGOutNode, DAGOpNode


class CliffordRzOptimization:
    def __init__(self, level="light", verbose=False) -> None:
        self.level = level
        self.verbose = verbose

    @cached_property
    def hadamard_templates(self) -> list[OptimizingTemplate]:
        """Generate Hadamard gate optimization templates.

        Returns:
            list[OptimizingTemplate]: a list of h gate optimization templates.
        """
        return generate_hadamard_gate_templates()

    @cached_property
    def single_qubit_gate_templates(self):
        return generate_single_qubit_gate_templates()

    def reduce_hadamard_gates(self, dag: DAGCircuit) -> int:
        """Hadamard gate reduction algorithm.

        Args:
            dag (DAGCircuit): the DAG to be optimized.

        Returns:
            int: the count of reduced H gates.
        """
        cnt = 0
        for template in self.hadamard_templates:
            cnt += replace_all(dag, template)
        return cnt

    def cancel_single_qubit_gates(self, dag: DAGCircuit):
        """Merge Rz gates using commutation rules.

        Args:
            dag (DAGCircuit): the DAG to be optimized.

        Returns:
            int: the count of reduced Rz gates.
        """
        cnt = 0
        for node in list(dag.topological_op_nodes()):
            if node.name != "rz":
                continue

            # erase the gate if degree == 0
            if np.isclose(float(node.op.arg_value[0]), 0):
                dag.remove_op_node(node)
                cnt += 1
                continue

            c_node = node
            while True:
                # next node
                n_node: DAGOpNode = list(dag.successors(c_node))[0]
                if isinstance(n_node, DAGOutNode):
                    break
                # cx gate has multiple next nodes, we choose the one has the
                # same qargs with rz node, because the commutation rule will
                # not change the qargs
                if len(c_node.qargs) == 2:
                    successors = list(dag.successors(c_node))
                    for node_ in successors:
                        if isinstance(node_, DAGOutNode):
                            continue
                        if node_.qargs == node.qargs:
                            n_node = node_
                            break
                        if node.qargs[0] in node_.qargs:
                            n_node = node_

                if n_node.name == "rz":
                    n_node.op.arg_value[0] += node.op.arg_value[0]
                    dag.remove_op_node(node)
                    cnt += 1
                    break

                # template matching
                mapping = None
                for template in self.single_qubit_gate_templates:
                    mapping = template.compare(dag, n_node, node.qargs[0])
                    if mapping:
                        out_node = template.template.output_map[
                            template.anchor
                        ]
                        last_node = list(
                            template.template.predecessors(out_node)
                        )[0]
                        c_node = mapping[id(last_node)]
                        break
                if not mapping:
                    break
        return cnt
