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

from functools import cached_property

from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.optimizer.template import (
    OptimizingTemplate,
    replace_all,
)
from wy_qcos.transpiler.cmss.common.gate_operation import (
    X,
    H,
    Z,
    RY,
)


class EquivalencePass:
    """Process equivalence templates."""

    def __init__(self) -> None:
        pass

    def param_transform(
        self, template: OptimizingTemplate, mapping: dict, new_nodes: dict
    ):
        """Process special equivalence templates, like x-ry-x.

        Args:
            template (OptimizingTemplate): equivalence template.
            mapping (dict): mapping nodes return by `template.compare()`.
            new_nodes (dict): replaced nodes return by
                `dag.substitute_node_with_dag`.
        """
        names = ""
        for node in template.template.topological_op_nodes():
            names += node.op.name
            names += "-"
        names = names[:-1]
        if names == "x-ry-x":
            new_ry = list(new_nodes.values())[0]
            old_ry = list(mapping.values())[1]
            new_ry.op.arg_value = [old_ry.op.arg_value[0] * -1]

    @cached_property
    def get_equivalence_circuits(self):
        # the last element is the `param_transform` function, process the
        # special template like x-ry-x
        tpl_list = [
            [1, 2, [H([0]), Z([0]), H([0])], [X([0])], None],
            [1, 2, [H([0]), X([0]), H([0])], [Z([0])], None],
            [1, 2, [X([0]), RY([0]), X([0])], [RY([0])], self.param_transform],
        ]
        ret = []
        for _, weight, tpl, rpl, transform in tpl_list:
            if (
                not isinstance(tpl, list)
                or not isinstance(rpl, list)
                or not isinstance(weight, int)
            ):
                raise ValueError(
                    "Template and replace must be list, weight must be int."
                )
            tpl_dag_graph = DAGCircuit.ir_to_dag(tpl)
            rpl_dag_graph = DAGCircuit.ir_to_dag(rpl)
            ret.append(
                OptimizingTemplate(
                    tpl_dag_graph,
                    rpl_dag_graph,
                    weight=weight,
                    param_transform=transform,
                )
            )
        return ret

    def replace_equivalence_circuits(
        self, dag: DAGCircuit, equivalence_circuits: list
    ):
        """Replace all equivalence circuits in dag.

        Args:
            dag (DAGCircuit): dag to be optimized.
            equivalence_circuits (list): equivalence circuits templates.

        Returns:
            int: the number of reduced gates.
        """
        cnt = 0
        for template in equivalence_circuits:
            cnt += replace_all(dag, template)
        return cnt

    def run(self, dag: DAGCircuit):
        """Optimize the dag with equivalence templates.

        Args:
            dag (DAGCircuit): dag to be optimized.

        Returns:
            int: the number of reduced gates.
        """
        templates = self.get_equivalence_circuits
        return self.replace_equivalence_circuits(dag, templates)
