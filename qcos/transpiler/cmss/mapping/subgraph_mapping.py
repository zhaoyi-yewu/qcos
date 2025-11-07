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
        num_qubits = dependency_graph.get_dg_num_q()
        log_to_phy = [None] * num_qubits
        phy_to_log = matcher.mapping
        for q_phy, q_log in phy_to_log.items():
            if q_log < num_qubits:
                log_to_phy[q_log] = q_phy
    return log_to_phy


def topgraph_mapping(dependency_graph: DG, adjacency_graph: Graph):
    """
    Find the largest subcircuit that is isomorphic to the hardware topology.
    And assign the remaining unallocated logical qubits sequentially.

    Args:
        dependency_graph (DG): dependency graph of the whole circuit.
        adjacency_graph (Graph): adjacency graph of the hardware.

    Returns:
        tuple(int, list): return the count of cx gates in the largest
            subcircuit, and the mapping from logical qubits to physical qubits.
    """
    # the graph of circuit is isomorphic to the hardware
    log_to_phy = subgraph_isomorphism_mapping(
        dependency_graph, adjacency_graph
    )
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
    front_gate_num, phy_to_log = topgraph_search(
        cx_list, adjacency_graph, 0, len(cx_list) - 1
    )

    # convert phy_to_log to log_to_phy
    num_qubits = dependency_graph.get_dg_num_q()
    log_to_phy = [None] * num_qubits
    for q_phy, q_log in phy_to_log.items():
        if q_log < num_qubits:
            log_to_phy[q_log] = q_phy

    # assign the unallocated qubits in order.
    assigned_physical = list(filter(lambda x: x is not None, log_to_phy))
    # all physical bits
    physical_bits = adjacency_graph.nodes
    unassigned_physical = sorted(list(physical_bits - assigned_physical))
    unassigned_index = 0
    for i in range(len(log_to_phy)):
        if log_to_phy[i] is None:
            log_to_phy[i] = unassigned_physical[unassigned_index]
            unassigned_index += 1
    return front_gate_num, log_to_phy


def topgraph_search(
    cx_list: list, adjacency_graph: Graph, left: int, right: int
):
    """Use binary search to find the largest subcircuit that is isomorphic.

    Args:
        cx_list (list): list of all cnot gates
        adjacency_graph (Graph): adjacency graph of the hardware.
        left (int): left boundary of the search range
        right (int): right boundary of the search range

    Returns:
        tuple(int, list): the count of cx gates in the cx_list that can
            isomorphic to the hardware, and the mapping from physical to
            logical.
    """
    best_idx = 0
    best_mapping = None
    while left <= right:
        # try the middle of the search range
        mid = (left + right) // 2
        top_graph = Graph()
        for i in range(mid):
            q1, q2 = cx_list[i]
            top_graph.add_edge(q1, q2)

        matcher = isomorphism.GraphMatcher(adjacency_graph, top_graph)
        match = matcher.subgraph_is_isomorphic()
        if match:
            # find an isomorphism, try to expand the range.
            best_idx = mid
            best_mapping = matcher.mapping
            left = mid + 1
        else:
            # no isomorphism found, narrow the search range.
            right = mid - 1

    return best_idx, best_mapping
