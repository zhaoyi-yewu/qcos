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

import rustworkx as rx

from qcos.transpiler.cmss.common.gate_operation import (
    H,
    CX,
    S,
    SDG,
    GateOperation,
)
from qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from qcos.transpiler.cmss.circuit.dag_node import (
    DAGOpNode,
    DAGNode,
)


class OptimizingTemplate:
    def __init__(
        self,
        template: DAGCircuit,
        replacement: DAGCircuit | None = None,
        anchor: int = 0,
        weight: int = 1,
    ):
        """Data structure for OptimizingTemplate.

        Each OptimizingTemplate is composed of a template circuit and
        a replacement circuit.

        Args:
            template (DAGCircuit): template circuit
            replacement (DAGCircuit): replacement circuit
            anchor (int): starting qubit of comparison with template.
            weight (int): reduced gate count.
        """
        self.template = template
        self.replacement = replacement
        self.anchor = anchor
        self.weight = weight


def generate_hadamard_gate_templates() -> list[OptimizingTemplate]:
    """Generate Hadamard gate optimization templates.

    Each template is composed of qubit count, reduction count, template
        circuit, and replacement circuit.

    Returns:
        list[OptimizingTemplate]: a list of OptimizingTemplate.
    """
    tpl_list = [
        [1, 1, [H([0]), S([0]), H([0])], [SDG([0]), H([0]), SDG([0])]],
        [1, 1, [H([0]), SDG([0]), H([0])], [S([0]), H([0]), S([0])]],
        [2, 4, [H([0]), H([1]), CX([0, 1]), H([0]), H([1])], [CX([1, 0])]],
        [
            2,
            2,
            [H([1]), S([1]), CX([0, 1]), SDG([1]), H([1])],
            [SDG([1]), CX([0, 1]), S([1])],
        ],
        [
            2,
            2,
            [H([1]), SDG([1]), CX([0, 1]), S([1]), H([1])],
            [S([1]), CX([0, 1]), SDG([1])],
        ],
    ]
    ret = []
    for n_qubit, weight, tpl, rpl in tpl_list:
        if (
            not isinstance(tpl, list)
            or not isinstance(rpl, list)
            or not isinstance(weight, int)
        ):
            raise ValueError(
                "Template and replacement must be list, weight must be int."
            )
        tpl_dag_graph = DAGCircuit.ir_to_dag(tpl)
        rpl_dag_graph = DAGCircuit.ir_to_dag(rpl)
        ret.append(
            OptimizingTemplate(tpl_dag_graph, rpl_dag_graph, weight=weight)
        )
    return ret


def search_template(graph: rx.PyDAG | DAGCircuit, template: rx.PyDAG):
    """Search template DAG in another DAG.

    Args:
        graph (rx.PyDAG | DAGCircuit): the DAG to search in.
        template (rx.PyDAG): the DAG to search for.

    Returns:
        tuple(dict, list): dict is the mapping from graph to template,
            list is the matched nodes in graph.
    """
    if isinstance(graph, DAGCircuit):
        graph = graph._multi_graph

    if not isinstance(graph, rx.PyDAG):
        raise ValueError("Graph must be DAGCircuit or rx.PyDAG.")

    # node_matcher for subgraph isomorphic
    def node_matcher(node1: DAGNode, node2: DAGNode):
        if not isinstance(node1, DAGOpNode) or not isinstance(
            node2, DAGOpNode
        ):
            return True
        return node1.name == node2.name

    # mapping dict from graph to template
    ret_mapping = {}
    # matched nodes in graph
    graph_match_nodes = []
    if rx.digraph_is_subgraph_isomorphic(
        graph, template, node_matcher=node_matcher
    ):
        vf2 = rx.digraph_vf2_mapping(
            graph, template, subgraph=True, node_matcher=node_matcher
        )
        mapping = next(vf2)
        graph_nodes = graph.nodes()
        template_nodes = template.nodes()
        for idx1, idx2 in mapping.items():
            node1 = graph_nodes[idx1]
            node2 = template_nodes[idx2]
            if isinstance(node1, DAGOpNode) and isinstance(node2, DAGOpNode):
                ret_mapping[idx1] = idx2
                graph_match_nodes.append(node1)
    return ret_mapping, graph_match_nodes


def replace_all(dag: DAGCircuit, template: OptimizingTemplate):
    """Replace all subcircuit in dag with template.

    Args:
        dag (DAGCircuit): the dag to be modified.
        template (OptimizingTemplate): search for template.template in dag,
            and replace it with template.replacement.

    Returns:
        int: the number of reduced H gates.
    """
    cnt = 0
    while True:
        # the template(rx.PyDAG) to search
        tpl_graph = template.template._multi_graph
        ret_mapping, nodes = search_template(dag, tpl_graph)
        # already replaced all
        if len(ret_mapping) == 0:
            break
        # tmp operation, will be replaced with template.replacement
        tmp_op = GateOperation(name="tmp", validate=False)
        tmp_node = dag.replace_block_with_op(nodes, tmp_op)
        dag.substitute_node_with_dag(tmp_node, template.replacement)
        cnt += template.weight
    return cnt
