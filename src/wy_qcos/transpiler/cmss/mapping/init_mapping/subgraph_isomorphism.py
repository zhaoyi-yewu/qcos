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

import networkx as nx
import rustworkx as rx

from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.transpiler.cmss.mapping.init_mapping.simulated_annealing import (
    SimulatedAnnealingMapping,
)
from wy_qcos.transpiler.cmss.mapping.utils.mapping_utils import (
    IdRemap,
    build_id_remap,
    restore_physical_ids,
    validate_mapping_inputs,
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
        # handle remaining unallocated qubits that only have 1-qubit gates
        none_num = log_to_phy.count(None)
        if none_num > 0:
            phy_qubits = list(coupling_graph.nodes)
            remain_phy = [q for q in phy_qubits if q not in log_to_phy]
            idx_remain = 0
            for logic, phy in enumerate(log_to_phy):
                if phy is not None:
                    continue
                log_to_phy[logic] = remain_phy[idx_remain]
                idx_remain += 1
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
    sa_mapping = SimulatedAnnealingMapping()
    log_to_phy = sa_mapping.run(dependency_graph, coupling_graph, log_to_phy)
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

        if rx.graph_is_subgraph_isomorphic(
            coupling_graph, top_graph, call_limit=100000
        ):
            # find an isomorphism
            vf2 = rx.graph_vf2_mapping(
                coupling_graph, top_graph, subgraph=True, call_limit=100000
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


# ===============================================
# Fidelity-aware VF2 layout mapping
# ===============================================

# Maximum number of VF2 solutions to explore
_MAX_TRIALS = 10000


class _InteractionData:
    """Interaction graph extracted from two-qubit gates.

    Attributes:
        graph: rustworkx graph with dense logical node IDs.
        edge_counts: Mapping from (dense_a, dense_b) to
            the number of two-qubit gates on that pair.
        remap: Logical qubit ID densification mapping.
    """

    def __init__(self):
        self.graph = rx.PyGraph(multigraph=False)
        self.edge_counts: dict[tuple[int, int], int] = {}
        self.remap = IdRemap()


class _CouplingData:
    """Physical coupling graph with edge error rates.

    Attributes:
        graph: rustworkx graph with dense physical node IDs.
        edge_errors: Mapping from (dense_a, dense_b) to
            error rate (1 - fidelity).
        remap: Physical qubit ID densification mapping.
    """

    def __init__(self):
        self.graph = rx.PyGraph(multigraph=False)
        self.edge_errors: dict[tuple[int, int], float] = {}
        self.remap = IdRemap()


def _extract_interactions(
    gates_list: list,
) -> _InteractionData:
    """Extract the interaction graph from two-qubit gates.

    Collects all logical qubits participating in two-qubit
    gates, densifies their IDs, and builds an undirected graph
    where edges represent two-qubit interactions. Multiple gates
    on the same pair are merged into one edge with a higher
    count.

    Args:
        gates_list: Logical gate sequence.

    Returns:
        Interaction data with graph, edge counts, and remap.
    """
    coupled_logical: set[int] = set()
    pair_counts: dict[tuple[int, int], int] = {}

    for gate in gates_list:
        if gate.operation_type != OperationType.DOUBLE_QUBIT_OPERATION.value:
            continue
        q0 = gate.targets[0]
        q1 = gate.targets[1]
        coupled_logical.add(q0)
        coupled_logical.add(q1)
        key = (min(q0, q1), max(q0, q1))
        pair_counts[key] = pair_counts.get(key, 0) + 1

    data = _InteractionData()
    if not coupled_logical:
        return data

    data.remap = build_id_remap(coupled_logical)
    for orig_id in data.remap.dense_to_orig:
        data.graph.add_node(orig_id)

    for (log_a, log_b), count in pair_counts.items():
        dense_a = data.remap.orig_to_dense[log_a]
        dense_b = data.remap.orig_to_dense[log_b]
        data.graph.add_edge(dense_a, dense_b, count)
        edge_key = (min(dense_a, dense_b), max(dense_a, dense_b))
        data.edge_counts[edge_key] = count

    return data


def _build_coupling_graph(
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
) -> _CouplingData:
    """Build the physical coupling graph with error rates.

    Collects all physical qubits in coupling edges, densifies
    their IDs, and builds an undirected graph. When
    edge_fidelities is provided, edges with fidelity <= 0 are
    skipped, and error rates (1 - fidelity) are recorded.

    Args:
        coupling_list: Physical coupling edges as (u, v) pairs.
        edge_fidelities: Per-edge CZ fidelity, same order as
            coupling_list. Empty to disable fidelity scoring.

    Returns:
        Coupling data with graph, error rates, and remap.
    """
    physical_ids: set[int] = set()
    for u, v in coupling_list:
        physical_ids.add(u)
        physical_ids.add(v)

    data = _CouplingData()
    data.remap = build_id_remap(physical_ids)
    for orig_id in data.remap.dense_to_orig:
        data.graph.add_node(orig_id)

    use_fidelity = bool(edge_fidelities)
    added_edges: set[tuple[int, int]] = set()
    for i, (u, v) in enumerate(coupling_list):
        if use_fidelity and edge_fidelities[i] <= 0.0:
            continue
        dense_u = data.remap.orig_to_dense[u]
        dense_v = data.remap.orig_to_dense[v]
        edge_key = (
            min(dense_u, dense_v),
            max(dense_u, dense_v),
        )
        if edge_key not in added_edges:
            data.graph.add_edge(dense_u, dense_v, None)
            added_edges.add(edge_key)
        if use_fidelity and edge_fidelities[i] > 0.0:
            data.edge_errors[edge_key] = 1.0 - edge_fidelities[i]

    return data


def _run_vf2_search(
    interaction: _InteractionData,
    coupling: _CouplingData,
    num_logical: int,
) -> list[int]:
    """Run VF2 subgraph monomorphism search with scoring.

    Finds all embeddings of the interaction graph into the
    coupling graph, scores each by total error contribution
    (error_rate * gate_count), and returns the lowest-scoring
    mapping.

    Returns an empty list when no embedding is found.

    Args:
        interaction: Logical interaction graph and edge counts.
        coupling: Physical coupling graph with error rates.
        num_logical: Total number of logical qubits (including
            those not in two-qubit gates).

    Returns:
        Best-scoring logical-to-physical mapping, or empty
        list if no embedding was found.
    """
    best_score = float("inf")
    best_mapping: list[int] = []

    vf2_iter = rx.graph_vf2_mapping(
        coupling.graph,
        interaction.graph,
        subgraph=True,
        induced=False,
        call_limit=_MAX_TRIALS,
    )

    for mapping in vf2_iter:
        # mapping: {coupling_node -> interaction_node}
        # reverse to get interaction_node -> coupling_node
        int_to_coupling = {v: k for k, v in mapping.items()}

        score = 0.0
        for (int_a, int_b), count in interaction.edge_counts.items():
            p0 = int_to_coupling[int_a]
            p1 = int_to_coupling[int_b]
            edge_key = (min(p0, p1), max(p0, p1))
            error = coupling.edge_errors.get(edge_key, 0.0)
            score += error * count

        if score < best_score:
            best_score = score
            best_mapping = [-1] * num_logical
            for int_node in range(interaction.remap.dense_count):
                orig_logical = interaction.remap.dense_to_orig[int_node]
                physical = int_to_coupling[int_node]
                best_mapping[orig_logical] = physical

    return best_mapping


def _assign_remaining_qubits(
    mapping: list[int],
    coupling: _CouplingData,
    num_logical: int,
    single_qubit_fidelities: list[float],
) -> None:
    """Assign unmapped logical qubits to free physical qubits.

    Logical qubits not involved in two-qubit gates have no
    mapping from VF2. They are assigned to free physical qubits,
    preferring those with higher single-qubit fidelity.

    Args:
        mapping: Mutable logical-to-physical mapping (modified
            in place). Unmapped entries are -1.
        coupling: Physical coupling data with remap.
        num_logical: Total number of logical qubits.
        single_qubit_fidelities: Per-physical-qubit 1q fidelity,
            indexed by physical qubit ID.
    """
    num_physical = coupling.remap.dense_count

    used_physical: set[int] = set()
    for phy in mapping:
        if phy >= 0:
            used_physical.add(phy)

    candidates = [i for i in range(num_physical) if i not in used_physical]

    if single_qubit_fidelities:
        candidates.sort(
            key=lambda dense_id: _get_single_fid(
                coupling, single_qubit_fidelities, dense_id
            ),
            reverse=True,
        )

    candidate_idx = 0
    for logical_idx in range(num_logical):
        if mapping[logical_idx] >= 0:
            continue
        if candidate_idx >= len(candidates):
            break
        mapping[logical_idx] = candidates[candidate_idx]
        candidate_idx += 1


def _get_single_fid(
    coupling: _CouplingData,
    single_qubit_fidelities: list[float],
    dense_id: int,
) -> float:
    """Look up single-qubit fidelity for a dense physical ID.

    Args:
        coupling: Physical coupling data with remap.
        single_qubit_fidelities: Per-physical-qubit 1q fidelity.
        dense_id: Dense physical qubit ID.

    Returns:
        Fidelity value, or 0.0 if out of range.
    """
    orig_id = coupling.remap.dense_to_orig[dense_id]
    if 0 <= orig_id < len(single_qubit_fidelities):
        return single_qubit_fidelities[orig_id]
    return 0.0


def vf2_layout_mapping(
    gates_list: list,
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
    single_qubit_fidelities: list[float],
    num_logical: int,
) -> list[int]:
    """Compute initial mapping using VF2 subgraph monomorphism.

    Embeds the circuit's interaction graph into the coupling
    graph. A perfect embedding means all two-qubit gates can
    execute without any SWAP. When multiple embeddings exist,
    selects the one with the lowest total error rate.

    Args:
        gates_list: Logical gate sequence.
        coupling_list: Physical coupling edges as (u, v) pairs.
        edge_fidelities: Per-edge CZ fidelity, same order as
            coupling_list. Empty to disable fidelity scoring.
        single_qubit_fidelities: Per-physical-qubit 1q
            fidelity, indexed by physical qubit ID.
        num_logical: Number of logical qubits in the circuit.

    Returns:
        Logical-to-physical mapping list. Empty when no
        perfect embedding is found or when there are no
        two-qubit gates.
    """
    if num_logical <= 0:
        return []

    validate_mapping_inputs(coupling_list, edge_fidelities, num_logical)

    interaction = _extract_interactions(gates_list)
    if interaction.remap.dense_count == 0:
        return []

    coupling = _build_coupling_graph(coupling_list, edge_fidelities)
    num_physical = coupling.remap.dense_count
    if num_logical > num_physical:
        return []

    mapping = _run_vf2_search(interaction, coupling, num_logical)
    if not mapping:
        return []

    _assign_remaining_qubits(
        mapping,
        coupling,
        num_logical,
        single_qubit_fidelities,
    )
    restore_physical_ids(mapping, coupling.remap)

    return mapping
