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

from networkx import Graph

from qcos.transpiler.cmss.mapping.dg import DG
from qcos.transpiler.cmss.mapping.subgraph_mapping import (
    subgraph_isomorphism_mapping,
    topgraph_mapping,
)


def get_initial_mapping(
    dependency_graph: DG, adjacency_graph: Graph, method="naive"
):
    """
    Get the initial mapping, providing 4 methods:
        naive: directly mapping logical qubits to physical qubits in order.
        simulated_annealing: heuristic mapping, based on simulated annealing,
            ref: "Quantum Circuit Transformation Based on Simulated Annealing
            and Heuristic Search."
        subgraph_isomorphism: Based on subgraph isomorphism, achieves precise
            allocation of qubits (this method may not always yield a solution).
        topgraph: Combines the above two methods. For the top part of the
            circuit topology graph, subgraph isomorphism is used. ref "Qubit
            Mapping Based on Subgraph Isomorphism and Filtered Depth-Limited
            Search."

    Args:
        dependency_graph (DG): dependency graph of the circuit
        adjacency_graph (Graph): adjacency graph of the quantum machine
        method (str, optional): mapping method. Defaults to 'naive'.

    Returns:
        list[int]: represents a mapping in which indices and values stand for
            logical and physical qubits.
    """
    if method == "naive":
        return list(range(len(adjacency_graph)))
    elif method == "simulated_annealing":
        # TODO
        return None
    elif method == "subgraph_isomorphism":
        return subgraph_isomorphism_mapping(dependency_graph, adjacency_graph)
    elif method == "topgraph":
        return topgraph_mapping(dependency_graph, adjacency_graph)
    else:
        raise ValueError(f"Unsupported method {method} for initial mapping")
