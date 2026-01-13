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

from collections import deque
from collections.abc import Callable
import copy

import rustworkx as rx

from wy_qcos.transpiler.cmss.common.gate_operation import (
    X,
    RZ,
    H,
    CX,
    S,
    SDG,
    GateOperation,
)
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.dag_node import (
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
        param_transform: Callable | None = None,
    ):
        """Data structure for OptimizingTemplate.

        Each OptimizingTemplate is composed of a template circuit and
        a replacement circuit.

        Args:
            template (DAGCircuit): template circuit
            replacement (DAGCircuit): replacement circuit
            anchor (int): starting qubit of comparison with template.
            weight (int): reduced gate count.
            param_transform (Callable): a function to process the parameter
                transformation in equivalence pass, like `XRy(θ)X -> Ry(-θ)`.
        """
        self.template = template
        self.replacement = replacement
        self.anchor = anchor
        self.weight = weight
        self.param_transform = param_transform

    def compare(self, dag: DAGCircuit, start_node: DAGOpNode, anchor: int):
        """Compare template dag with circuit dag from start_node.

        Args:
            dag (DAGCircuit): the circuit to be compared.
            start_node (DAGOpNode): the node to start compare in dag.
            anchor (int): the anchor qubit in the circuit corresponding to
                the template.anchor.

        Returns:
            dict: mapping from node in template to node in dag.
        """
        template = self.template
        t_qubit = self.anchor
        # start compare from t_node, start_node
        t_node = list(template.successors(template.input_map[t_qubit]))[0]
        node = start_node

        # `qubit_mapping` is the bit mapping from the template to the DAG,
        # The DAG can know the sequential relationship between two nodes,
        # but it cannot determine the exact qubits on which they act.
        # ┌─────────┐
        # ┤ Rz(0.1) ├──■───  ─────────────■───
        # └─────────┘┌─┴─┐   ┌─────────┐┌─┴─┐
        # ───────────┤ X ├─  ┤ Rz(0.1) ├┤ X ├─
        #            └───┘   └─────────┘└───┘
        # For the two circuits mentioned above, they are the same from the DAG.
        # However, by maintaining the `qubit_mapping`, during the compare
        # process, it can be determined that the two circuits are not
        # equivalent, thus terminating the comparison, whereas this cannot be
        # determined solely from the DAG.
        qubit_mapping = {t_qubit: anchor}

        if node.name != t_node.name:
            return None

        for u_qubit, v_qubit in zip(t_node.qargs, node.qargs):
            # unmapped qubits, allocate them
            if u_qubit not in qubit_mapping.keys():
                qubit_mapping[u_qubit] = v_qubit
            # conflict with the previously established mapping, it indicates
            # that the circuit and the template are not equivalent.
            if qubit_mapping[u_qubit] != v_qubit:
                return None

        # the mapping from node in template to node in dag
        mapping = {id(t_node): node}
        queue = deque([(t_node, node)])
        while len(queue) > 0:
            u, v = queue.popleft()
            for neighbors in ["predecessors", "successors"]:
                u_nxts = list(getattr(template, neighbors)(u))
                v_nxts = list(getattr(dag, neighbors)(v))
                # compare circuit bit by bit
                for qubit in u.qargs:
                    u_nxt = None
                    v_nxt = None
                    for node in u_nxts:
                        if not isinstance(node, DAGOpNode):
                            continue
                        # next node must originate from current qubit
                        if qubit in node.qargs:
                            u_nxt = node
                            if len(node.qargs) == 1:
                                break

                    if not isinstance(u_nxt, DAGOpNode):
                        continue

                    for node in v_nxts:
                        if not isinstance(node, DAGOpNode):
                            continue
                        # like above, but convert qubit location
                        if qubit_mapping[qubit] in node.qargs:
                            v_nxt = node
                            if len(node.qargs) == 1:
                                break

                    if id(u_nxt) in mapping:
                        # conflict with the previously established mapping
                        if id(mapping[id(u_nxt)]) != id(v_nxt):
                            return None
                        continue

                    if (
                        not isinstance(v_nxt, DAGOpNode)
                        or u_nxt.name != v_nxt.name
                    ):
                        return None

                    # allocate mapping and check conflict
                    for u_qubit, v_qubit in zip(u_nxt.qargs, v_nxt.qargs):
                        if u_qubit not in qubit_mapping.keys():
                            qubit_mapping[u_qubit] = v_qubit
                        if qubit_mapping[u_qubit] != v_qubit:
                            return None

                    mapping[id(u_nxt)] = v_nxt
                    queue.append((u_nxt, v_nxt))

        return mapping


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


def generate_single_qubit_gate_templates() -> list[OptimizingTemplate]:
    tpl_list = [
        [2, 1, [H([1]), CX([0, 1]), H([1])]],
        [2, 1, [CX([0, 1]), RZ([1]), CX([0, 1])]],
        [2, 0, [CX([0, 1])]],
        [3, 0, [CX([1, 0]), CX([0, 2]), CX([1, 0])]],
        [1, 0, [H([0]), X([0]), H([0])]],
    ]
    ret = []
    for n_qubit, anchor, tpl in tpl_list:
        if not isinstance(tpl, list) or not isinstance(anchor, int):
            raise ValueError("Template must be list, anchor must be int.")
        tpl_dag = DAGCircuit.ir_to_dag(tpl)
        ret.append(OptimizingTemplate(tpl_dag, anchor=anchor))
    return ret


def generate_cnot_ctrl_templates() -> list[OptimizingTemplate]:
    tpl_list = [[2, 0, [CX([0, 1])]], [1, 0, [RZ([0])]]]
    ret = []
    for n_qubit, anchor, tpl in tpl_list:
        if not isinstance(tpl, list) or not isinstance(anchor, int):
            raise ValueError("Template must be list, anchor must be int.")
        tpl_dag = DAGCircuit.ir_to_dag(tpl)
        ret.append(OptimizingTemplate(tpl_dag, anchor=anchor))
    return ret


def generate_cnot_targ_templates() -> list[OptimizingTemplate]:
    tpl_list = [
        [2, 1, [CX([0, 1])]],
        [2, 0, [H([0]), CX([0, 1]), H([0])]],
        [1, 0, [X([0])]],
    ]
    ret = []
    for n_qubit, anchor, tpl in tpl_list:
        if not isinstance(tpl, list) or not isinstance(anchor, int):
            raise ValueError("Template must be list, anchor must be int.")
        tpl_dag = DAGCircuit.ir_to_dag(tpl)
        ret.append(OptimizingTemplate(tpl_dag, anchor=anchor))
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
        int: the number of reduced gates.
    """
    cnt = 0
    for node in dag.topological_op_nodes():
        mapping = template.compare(dag, node, node.qargs[0])
        if mapping:
            nodes = mapping.values()
            tmp_op = GateOperation(name="tmp")
            tmp_node = dag.replace_block_with_op(nodes, tmp_op)
            replacement = copy.deepcopy(template.replacement)
            # special case, symmetric template
            if template.weight == 4:
                start_compare_qubit = node.qargs[0]
                if tmp_node.qargs[1] == start_compare_qubit:
                    tmp_node.qargs = tmp_node.qargs[::-1]
            ret = dag.substitute_node_with_dag(tmp_node, replacement)
            # the qubits in op needs to be updated
            for new_node in ret.values():
                new_node.op.targets = list(new_node.qargs)
            if template.param_transform is not None:
                template.param_transform(template, mapping, ret)
            cnt += template.weight
    return cnt
