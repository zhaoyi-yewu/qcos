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

import networkx as nx
import rustworkx as rx

from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.transpiler.cmss.mapping.init_mapping.simulated_annealing import (
    sa_initial_mapping,
)


def subgraph_isomorphism_mapping(
    dependency_graph: DG, coupling_graph: nx.Graph
):
    """Qubit precise allocation based on subgraph isomorphism.

    Args:
        dependency_graph (DG): Quantum circuit topology
        coupling_graph (Graph): Hardware Topology

    Returns:
        list: mapping from logical qubits to physical qubits
    """
    coupling_graph = nx_to_rx(coupling_graph)
    sub_graph = rx.PyGraph(multigraph=False)
    for node in dependency_graph.nodes:
        qubits = dependency_graph.get_node_qubits(node)
        if len(qubits) > 2:
            raise ValueError("Qubits number greater than 2 is not supported!")
        if len(qubits) == 1:
            continue
        node_idx = []
        for q in qubits:
            if q not in sub_graph.nodes():
                sub_graph.add_node(q)
            node_idx.append(list(sub_graph.nodes()).index(q))
        sub_graph.add_edge(node_idx[0], node_idx[1], None)

    # subgraph isomorphism
    log_to_phy = None
    # if an isomorphic subgraph is found
    if rx.graph_is_subgraph_isomorphic(coupling_graph, sub_graph):
        # convert phy_to_log to log_to_phy
        num_qubits = dependency_graph.num_q
        log_to_phy = [None] * num_qubits
        vf2 = rx.graph_vf2_mapping(coupling_graph, sub_graph, subgraph=True)
        phy_to_log = next(vf2)
        # convert idx to node
        coupling_graph_nodes = coupling_graph.nodes()
        sub_graph_nodes = sub_graph.nodes()
        for q_phy_idx, q_log_idx in phy_to_log.items():
            q_phy = coupling_graph_nodes[q_phy_idx]
            q_log = sub_graph_nodes[q_log_idx]
            if q_log < num_qubits:
                log_to_phy[q_log] = q_phy
    return log_to_phy


def topgraph_mapping(dependency_graph: DG, coupling_graph: nx.Graph):
    """Find the largest subcircuit that is isomorphic to the hardware topology.

    And assign the remaining unallocated logical qubits sequentially.

    Args:
        dependency_graph (DG): dependency graph of the whole circuit.
        coupling_graph (nx.Graph): adjacency graph of the hardware.

    Returns:
        list: return the mapping from logical qubits to physical qubits.
    """
    # the graph of circuit is isomorphic to the hardware
    log_to_phy = subgraph_isomorphism_mapping(dependency_graph, coupling_graph)
    if log_to_phy is not None:
        return log_to_phy

    # all cnot gates
    cx_list = []
    for node in dependency_graph.nodes:
        for gate in dependency_graph.get_node_gates(node):
            targets = gate[1]
            if len(targets) == 2:
                cx_list.append(targets)

    # search the max front circuit isomorphic to the hardware
    _, phy_to_log = topgraph_search(
        cx_list, coupling_graph, 0, len(cx_list) - 1
    )

    # convert phy_to_log to log_to_phy
    num_qubits = dependency_graph.num_q
    log_to_phy = [None] * num_qubits
    for q_phy, q_log in phy_to_log.items():
        if q_log < num_qubits:
            log_to_phy[q_log] = q_phy

    # use simulated annealing to assign the remaining unallocated qubits
    log_to_phy = sa_initial_mapping(
        dependency_graph, coupling_graph, log_to_phy
    )
    return log_to_phy


def topgraph_search(
    cx_list: list, coupling_graph: nx.Graph, left: int, right: int
):
    """Use binary search to find the largest subcircuit that is isomorphic.

    Args:
        cx_list (list): list of all cnot gates
        coupling_graph (nx.Graph): adjacency graph of the hardware.
        left (int): left boundary of the search range
        right (int): right boundary of the search range

    Returns:
        tuple(int, list): the count of cx gates in the cx_list that can
            isomorphic to the hardware, and the mapping from physical to
            logical.
    """
    best_idx = 0
    best_mapping = rx.NodeMap()
    sub_graph = rx.PyGraph(multigraph=False)
    coupling_graph = nx_to_rx(coupling_graph)
    while left <= right:
        # try the middle of the search range
        mid = (left + right) // 2
        top_graph = rx.PyGraph(multigraph=False)
        # add node
        for i in range(mid):
            q1, q2 = cx_list[i]
            if q1 not in top_graph.nodes():
                top_graph.add_node(q1)
            if q2 not in top_graph.nodes():
                top_graph.add_node(q2)
        # add edge
        all_nodes = list(top_graph.nodes())
        for i in range(mid):
            q1, q2 = cx_list[i]
            q1_idx = all_nodes.index(q1)
            q2_idx = all_nodes.index(q2)
            top_graph.add_edge(q1_idx, q2_idx, None)

        if rx.graph_is_subgraph_isomorphic(coupling_graph, top_graph):
            # find an isomorphism
            vf2 = rx.graph_vf2_mapping(
                coupling_graph, top_graph, subgraph=True
            )
            mapping = next(vf2)
            best_idx = mid
            best_mapping = mapping
            sub_graph = top_graph
            left = mid + 1
        else:
            # no isomorphism found, narrow the search range.
            right = mid - 1

    # convert the idx to node in mapping
    ret_map = {}
    coupling_graph_nodes = coupling_graph.nodes()
    sub_graph_nodes = sub_graph.nodes()
    for q_phy_idx, q_log_idx in best_mapping.items():
        # current key value is idx of node
        q_phy = coupling_graph_nodes[q_phy_idx]
        q_log = sub_graph_nodes[q_log_idx]
        ret_map[q_phy] = q_log
    return best_idx, ret_map


def nx_to_rx(nx_graph: nx.Graph) -> rx.PyGraph:
    """Convert nx.Graph to rx.PyGraph."""
    rx_graph = rx.PyGraph(multigraph=False)
    # add nodes to rx_graph
    for node in nx_graph.nodes:
        rx_graph.add_node(node)
    all_nodes = list(rx_graph.nodes())
    # add edges to rx_graph
    for edge in nx_graph.edges:
        u, v = edge[0], edge[1]
        u_idx = all_nodes.index(u)
        v_idx = all_nodes.index(v)
        rx_graph.add_edge(u_idx, v_idx, None)
    return rx_graph
