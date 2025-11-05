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
from networkx.algorithms import isomorphism

from qcos.transpiler.cmss.mapping.dg import DG


def subgraph_isomorphism_mapping(dependency_graph: DG, adjacency_graph: Graph):
    """
    Qubit precise allocation based on subgraph isomorphism.

    Args:
        dependency_graph (DG): Quantum circuit topology
        adjacency_graph (Graph): Hardware Topology

    Returns:
        list: mapping from logical qubits to physical qubits
    """
    subgraph = Graph()
    for node in dependency_graph.nodes:
        qubits = dependency_graph.get_node_qubits(node)
        if len(qubits) > 2:
            raise ValueError("Qubits number greater than 2 is not supported!")
        if len(qubits) == 1:
            continue
        for q in qubits:
            if q not in subgraph:
                subgraph.add_node(q)
        subgraph.add_edge(qubits[0], qubits[1])

    # subgraph isomorphism
    matcher = isomorphism.GraphMatcher(adjacency_graph, subgraph)
    log_to_phy = None
    # if an isomorphic subgraph is found
    if matcher.subgraph_is_isomorphic():
        # convert phy_to_log to log_to_phy
        num_qubits = len(subgraph)
        log_to_phy = [None] * num_qubits
        phy_to_log = matcher.mapping
        for q_phy, q_log in phy_to_log.items():
            if q_log < num_qubits:
                log_to_phy[q_log] = q_phy
    return log_to_phy
