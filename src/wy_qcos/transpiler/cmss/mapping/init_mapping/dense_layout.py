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

"""DenseLayout initial mapping algorithm.

Finds the most densely connected physical subgraph matching the
logical qubit count, then refines the arrangement via SABRE
forward-backward routing.

Subgraph scoring uses a weighted blend of density and fidelity:
    density_score  = edge_count / max_edge_count
    fidelity_score = average edge fidelity within the subgraph
    combined = w * fidelity_score + (1 - w) * density_score
"""

from collections import deque
from dataclasses import dataclass, field

from wy_qcos.transpiler.cmss.mapping.init_mapping.sabre_mapping import (
    sabre_initial_mapping,
)
from wy_qcos.transpiler.cmss.mapping.utils.mapping_utils import (
    select_best_single_qubits,
    validate_mapping_inputs,
)


@dataclass
class _SubgraphCandidate:
    """A BFS-collected subgraph candidate.

    Attributes:
        nodes: Physical qubit IDs collected by BFS.
        edge_count: Number of directed internal edges.
        fidelity_score: Average fidelity of internal edges,
            or 0.0 when no fidelity data.
    """

    nodes: list[int]
    edge_count: int
    fidelity_score: float


@dataclass
class _SubgraphEnumerationResult:
    """Result of enumerating all BFS subgraph candidates.

    Attributes:
        candidates: List of subgraph candidates.
        max_edge_count: Maximum edge_count across all
            candidates, used for density normalization.
    """

    candidates: list[_SubgraphCandidate] = field(default_factory=list)
    max_edge_count: int = 0


def _count_physical_qubits(
    coupling_list: list[tuple[int, int]],
) -> int:
    """Infer physical qubit count from coupling edges.

    Returns ``max(edge endpoints) + 1`` so arrays indexed by
    physical ID are large enough.
    """
    max_id = -1
    for u, v in coupling_list:
        max_id = max(max_id, u, v)
    return max_id + 1


def _build_adj_list(
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
    num_physical: int,
) -> list[list[int]]:
    """Build a bidirectional adjacency list.

    Converts directed coupling edges into undirected adjacency.
    When *edge_fidelities* is non-empty, edges with fidelity
    <= 0 are excluded (damaged / disabled links).
    """
    neighbors_set: list[set[int]] = [set() for _ in range(num_physical)]
    has_fidelity = bool(edge_fidelities)
    for i, (u, v) in enumerate(coupling_list):
        if has_fidelity and edge_fidelities[i] <= 0.0:
            continue
        neighbors_set[u].add(v)
        neighbors_set[v].add(u)
    return [sorted(s) for s in neighbors_set]


def _bfs_gather_subgraph(
    neighbors: list[list[int]],
    start: int,
    num_logical: int,
) -> list[int]:
    """BFS-collect *num_logical* connected nodes from *start*.

    Returns an empty list if the connected component is too
    small to hold *num_logical* nodes.
    """
    result: list[int] = []
    visited: set[int] = {start}
    queue = deque([start])
    while queue and len(result) < num_logical:
        current = queue.popleft()
        result.append(current)
        for neighbor in neighbors[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    if len(result) < num_logical:
        return []
    return result


def _enumerate_subgraph_candidates(
    neighbors: list[list[int]],
    num_logical: int,
    edge_fidelity_map: dict[tuple[int, int], float],
    num_physical: int,
) -> _SubgraphEnumerationResult:
    """Enumerate all BFS subgraph candidates with scoring.

    For each physical node as BFS start, collects *num_logical*
    connected nodes, then counts internal edges and computes
    average fidelity in a single pass.
    """
    use_fidelity = bool(edge_fidelity_map)
    result = _SubgraphEnumerationResult()

    for start in range(num_physical):
        subgraph = _bfs_gather_subgraph(neighbors, start, num_logical)
        if not subgraph:
            continue
        subgraph_set = set(subgraph)
        edge_count = 0
        fidelity_sum = 0.0
        fidelity_edge_count = 0
        for node in subgraph:
            for neighbor in neighbors[node]:
                if neighbor in subgraph_set:
                    edge_count += 1
                    if use_fidelity:
                        fid = edge_fidelity_map.get((node, neighbor))
                        if fid is not None:
                            fidelity_sum += fid
                            fidelity_edge_count += 1
        result.max_edge_count = max(result.max_edge_count, edge_count)
        fidelity_score = (
            fidelity_sum / fidelity_edge_count
            if fidelity_edge_count > 0
            else 0.0
        )
        result.candidates.append(
            _SubgraphCandidate(subgraph, edge_count, fidelity_score)
        )
    return result


def _make_identity_mapping(num_logical: int) -> list[int]:
    """Generate identity mapping [0, 1, ..., num_logical-1]."""
    return list(range(num_logical))


def dense_layout_mapping(
    gates_list: list,
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
    single_qubit_fidelities: list[float],
    num_logical: int,
    fidelity_weight: float = 0.5,
) -> list[int]:
    """Compute initial mapping using DenseLayout algorithm.

    Two-step process:
    1. Select the most densely connected physical subgraph of
       size *num_logical* (with optional fidelity weighting).
    2. Refine the arrangement via SABRE forward-backward routing.

    Args:
        gates_list: Logical gate sequence.
        coupling_list: Physical coupling edges as (u, v) pairs.
        edge_fidelities: Per-edge CZ fidelity, same order as
            coupling_list. Empty to disable fidelity scoring.
        single_qubit_fidelities: Per-physical-qubit 1q
            fidelity, indexed by physical qubit ID.
        num_logical: Number of logical qubits in the circuit.
        fidelity_weight: Weight for fidelity vs density [0, 1].
            0.0 = pure density, 1.0 = pure fidelity.

    Returns:
        Logical-to-physical mapping list. Empty on failure.
    """
    num_physical = _count_physical_qubits(coupling_list)
    validate_mapping_inputs(coupling_list, edge_fidelities, num_logical)
    if num_logical == 0:
        return []

    neighbors = _build_adj_list(coupling_list, edge_fidelities, num_physical)

    use_fidelity = bool(edge_fidelities) and fidelity_weight != 0.0

    edge_fidelity_map: dict[tuple[int, int], float] = {}
    if use_fidelity:
        for i, (u, v) in enumerate(coupling_list):
            if edge_fidelities[i] > 0.0:
                edge_fidelity_map[(u, v)] = edge_fidelities[i]

    enumeration = _enumerate_subgraph_candidates(
        neighbors,
        num_logical,
        edge_fidelity_map,
        num_physical,
    )

    density_denom = (
        float(enumeration.max_edge_count)
        if enumeration.max_edge_count > 0
        else 1.0
    )

    best_combined_score = -1.0
    best_subgraph: list[int] = []

    for candidate in enumeration.candidates:
        density_score = candidate.edge_count / density_denom
        combined_score = (
            fidelity_weight * candidate.fidelity_score
            + (1.0 - fidelity_weight) * density_score
        )
        if combined_score > best_combined_score:
            best_combined_score = combined_score
            best_subgraph = candidate.nodes

    if not best_subgraph:
        if not single_qubit_fidelities:
            return _make_identity_mapping(num_logical)
        best = select_best_single_qubits(
            single_qubit_fidelities, set(), num_logical
        )
        if len(best) < num_logical:
            return []
        return best

    return sabre_initial_mapping(gates_list, coupling_list, best_subgraph)
