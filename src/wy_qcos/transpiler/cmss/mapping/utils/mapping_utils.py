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

"""Mapping utility functions.

Stateless helpers shared by SABRE and other mapping algorithms:
- fidelity threshold computation
- low-fidelity edge / qubit filtering
- connected-component selection
- target_bits induced subgraph
- logical qubit ID densification
- qubit selection by fidelity
"""

import math
from dataclasses import dataclass, field
from collections import deque

# Adaptive fidelity threshold clamp range
FIDELITY_THRESHOLD_UPPER = 0.9
FIDELITY_THRESHOLD_LOWER = 0.3


@dataclass
class IdRemap:
    """Logical or physical ID densification mapping.

    Attributes:
        orig_to_dense: mapping from original ID to dense ID.
        dense_to_orig: sorted list of original IDs in dense order.
        dense_count: number of dense IDs (== len(dense_to_orig)).
    """

    orig_to_dense: dict[int, int] = field(default_factory=dict)
    dense_to_orig: list[int] = field(default_factory=list)
    dense_count: int = 0


def compute_adaptive_fidelity_threshold(
    edge_fidelities: list[float],
) -> float:
    """Compute adaptive fidelity threshold from edge statistics.

    Calculates ``mean - std`` of all positive edge fidelities, then clamps
    the result to ``[FIDELITY_THRESHOLD_LOWER, FIDELITY_THRESHOLD_UPPER]``.

    Args:
        edge_fidelities (list[float]): Per-edge CZ fidelities.  Zero or
            negative values are treated as missing and excluded from the
            statistics.

    Returns:
        float: Adaptive threshold clamped to [0.3, 0.9].  Returns ``0.0``
            when no valid (positive) edges exist, meaning "don't filter".
    """
    # only count valid edges (fidelity > 0), skip damaged/missing data
    valid = [fid for fid in edge_fidelities if fid > 0.0]
    if not valid:
        return 0.0
    mean = sum(valid) / len(valid)
    variance = sum((fid - mean) ** 2 for fid in valid) / len(valid)
    std = math.sqrt(variance)
    threshold = mean - std
    return max(
        FIDELITY_THRESHOLD_LOWER,
        min(FIDELITY_THRESHOLD_UPPER, threshold),
    )


def filter_low_fidelity(
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
    single_qubit_fidelities: list[float],
    threshold: float,
) -> tuple[list[tuple[int, int]], list[float]]:
    """Remove edges and qubits below the fidelity threshold.

    Performs two passes:

    1. Zeros out ``single_qubit_fidelities[i]`` in-place for any qubit whose
       fidelity is at or below *threshold*.
    2. Filters *coupling_list* to keep only edges where the edge fidelity
       **and** both endpoint single-qubit fidelities exceed *threshold*.

    Args:
        coupling_list (list[tuple[int, int]]): Coupling graph edges as
            ``(u, v)`` pairs.
        edge_fidelities (list[float]): Per-edge fidelity, same order as
            *coupling_list*.
        single_qubit_fidelities (list[float]): Per-qubit 1-q gate fidelity,
            indexed by physical qubit ID.  Modified **in-place**: entries
            at or below *threshold* are zeroed.
        threshold (float): Fidelity cutoff.  Edges / qubits with fidelity
            ``<= threshold`` are removed.

    Returns:
        tuple[list[tuple[int, int]], list[float]]: Filtered
            ``(coupling_list, edge_fidelities)`` — new lists, not views.
    """
    if not edge_fidelities:
        raise ValueError(
            "edge_fidelities must not be empty for filter_low_fidelity"
        )
    if len(edge_fidelities) != len(coupling_list):
        raise ValueError(
            f"edge_fidelities size ({len(edge_fidelities)}) "
            f"!= coupling_list size ({len(coupling_list)})"
        )

    # step 1: zero out single-qubit fidelities below threshold
    for i in range(len(single_qubit_fidelities)):
        if single_qubit_fidelities[i] <= threshold:
            single_qubit_fidelities[i] = 0.0

    new_edges: list[tuple[int, int]] = []
    new_fids: list[float] = []
    # step 2: remove edges where edge or endpoint fidelity is below threshold
    for i, (u, v) in enumerate(coupling_list):
        edge_fid = edge_fidelities[i]
        u_fid = (
            single_qubit_fidelities[u]
            if u < len(single_qubit_fidelities)
            else 0.0
        )
        v_fid = (
            single_qubit_fidelities[v]
            if v < len(single_qubit_fidelities)
            else 0.0
        )
        if edge_fid > threshold and u_fid > threshold and v_fid > threshold:
            new_edges.append((u, v))
            new_fids.append(edge_fidelities[i])

    return new_edges, new_fids


def select_largest_component(
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
) -> tuple[list[tuple[int, int]], list[float]]:
    """Keep only the largest connected component of the coupling graph.

    Uses union-find to identify connected components, then filters both
    the edge list and fidelity list to retain only edges whose endpoints
    belong to the largest component.

    Args:
        coupling_list (list[tuple[int, int]]): Coupling graph edges as
            ``(u, v)`` pairs.
        edge_fidelities (list[float]): Per-edge fidelity, same order as
            *coupling_list*.

    Returns:
        tuple[list[tuple[int, int]], list[float]]: Filtered
            ``(coupling_list, edge_fidelities)`` containing only edges
            within the largest connected component.  Returns the original
            lists unchanged when *coupling_list* is empty.
    """
    if not coupling_list:
        return coupling_list, edge_fidelities

    # build undirected adjacency list for BFS
    adjacency: dict[int, list[int]] = {}
    for u, v in coupling_list:
        adjacency.setdefault(u, []).append(v)
        adjacency.setdefault(v, []).append(u)

    # BFS to find the largest connected component
    visited: set[int] = set()
    largest_component: list[int] = []
    for node in adjacency:
        if node in visited:
            continue
        component: list[int] = []
        bfs_queue = deque([node])
        visited.add(node)
        while bfs_queue:
            current = bfs_queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    bfs_queue.append(neighbor)
        if len(component) > len(largest_component):
            largest_component = component

    largest_set = set(largest_component)
    new_edges: list[tuple[int, int]] = []
    new_fids: list[float] = []
    # keep only edges where both endpoints are in the largest component
    for i, (u, v) in enumerate(coupling_list):
        if u in largest_set and v in largest_set:
            new_edges.append((u, v))
            if i < len(edge_fidelities):
                new_fids.append(edge_fidelities[i])

    return new_edges, new_fids


def induce_target_subgraph(
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
    target_bits: list[int],
) -> tuple[list[tuple[int, int]], list[float]]:
    """Extract the subgraph induced by *target_bits*.

    Keeps only edges where **both** endpoints appear in *target_bits*,
    effectively restricting routing to a specific physical qubit subset.

    Args:
        coupling_list (list[tuple[int, int]]): Coupling graph edges as
            ``(u, v)`` pairs.
        edge_fidelities (list[float]): Per-edge fidelity, same order as
            *coupling_list*.
        target_bits (list[int]): Physical qubit IDs to retain.

    Returns:
        tuple[list[tuple[int, int]], list[float]]: Filtered
            ``(coupling_list, edge_fidelities)`` with only intra-subgraph
            edges.
    """
    target_set = set(target_bits)
    new_edges: list[tuple[int, int]] = []
    new_fids: list[float] = []
    # filter edges: keep only those where both endpoints are in target_bits
    for i, (u, v) in enumerate(coupling_list):
        if u in target_set and v in target_set:
            new_edges.append((u, v))
            if i < len(edge_fidelities):
                new_fids.append(edge_fidelities[i])
    return new_edges, new_fids


def build_logical_remap(
    gate_ops: list,
    measure_ops: list,
) -> IdRemap:
    """Build a dense-ID remapping if logical qubit IDs contain gaps.

    Scans all qubit IDs referenced by *gate_ops* and *measure_ops*.
    When the used IDs form a contiguous ``[0, max_id]`` range, returns
    an empty :class:`IdRemap` with ``dense_count == 0``.  Otherwise,
    returns an :class:`IdRemap` with a bijection from sparse original
    IDs to contiguous dense IDs.

    Args:
        gate_ops (list): Gate operations whose ``.targets`` reference
            logical qubit IDs.
        measure_ops (list): Measure operations whose ``.targets`` reference
            logical qubit IDs.

    Returns:
        IdRemap: An :class:`IdRemap` mapping original → dense IDs.
            When ``dense_count == 0``, no remapping is required.
    """
    # collect all used logical qubits (gates + measures), deduplicated
    used: set[int] = set()
    for gate in gate_ops:
        used.update(gate.targets)
    for measure in measure_ops:
        used.update(measure.targets)
    if not used:
        # empty circuit, return empty remap
        return IdRemap()
    max_id = max(used)
    # no gaps: used_count == max_id + 1, no remapping needed
    if len(used) == max_id + 1:
        # no gaps, return empty remap
        return IdRemap()
    sorted_used = sorted(used)
    # build orig->dense bidirectional mapping
    orig_to_dense = {orig: dense for dense, orig in enumerate(sorted_used)}
    return IdRemap(
        orig_to_dense=orig_to_dense,
        dense_to_orig=sorted_used,
        dense_count=len(sorted_used),
    )


def apply_logical_remap(
    gate_ops: list,
    measure_ops: list,
    remap: IdRemap,
) -> None:
    """Rewrite gate and measure targets to dense IDs in-place.

    Replaces every logical qubit ID in the ``.targets`` of *gate_ops* and
    *measure_ops* with its corresponding dense ID from *remap*.

    Args:
        gate_ops (list): Gate operations whose ``.targets`` will be
            rewritten.
        measure_ops (list): Measure operations whose ``.targets`` will be
            rewritten.
        remap (IdRemap): Mapping from original to dense IDs, as returned
            by :func:`build_logical_remap`.
    """
    orig_to_dense = remap.orig_to_dense
    # rewrite gate targets to dense IDs
    for gate in gate_ops:
        gate.targets = [orig_to_dense[target] for target in gate.targets]
    # rewrite measure targets to dense IDs
    for measure in measure_ops:
        measure.targets = [orig_to_dense[target] for target in measure.targets]


def restore_logical_mapping(
    remap: IdRemap,
    dense_mapping: list[int],
) -> list[int]:
    """Expand a dense-ID mapping back to original logical indices.

    Given a mapping produced during routing (indexed by dense logical ID),
    reconstruct a mapping indexed by the **original** (possibly sparse)
    logical IDs.  Unused original IDs are filled with ``-1``.

    Args:
        remap (IdRemap): The dense remapping that was applied before
            routing, as returned by :func:`build_logical_remap`.
        dense_mapping (list[int]): Physical-qubit mapping indexed by dense
            logical ID (``dense_mapping[dense_id]`` → physical qubit).

    Returns:
        list[int]: Physical-qubit mapping indexed by original logical ID.
            Entries for unused original IDs are ``-1``.
    """
    dense_to_orig = remap.dense_to_orig
    orig_size = max(dense_to_orig) + 1 if dense_to_orig else 0
    for orig_id in remap.orig_to_dense:
        orig_size = max(orig_size, orig_id + 1)
    # -1 for unused logical IDs
    restored = [-1] * orig_size
    # map dense_id -> orig_id -> physical qubit
    for dense_id in range(remap.dense_count):
        orig_id = dense_to_orig[dense_id]
        if dense_id < len(dense_mapping):
            restored[orig_id] = dense_mapping[dense_id]
    return restored


def select_best_single_qubits(
    single_qubit_fidelities: list[float],
    used: set[int] | None = None,
    count: int = 0,
) -> list[int]:
    """Select the highest-fidelity physical qubits for single-qubit mapping.

    Returns the top *count* physical qubits sorted by 1-q gate fidelity
    (descending), excluding any qubits already in *used*.

    Args:
        single_qubit_fidelities (list[float]): Per-qubit 1-q gate fidelity,
            indexed by physical qubit ID.  Only qubits with fidelity > 0
            are considered.
        used (set[int] | None): Physical qubit IDs to exclude.  Defaults
            to an empty set.
        count (int): Number of qubits to select.

    Returns:
        list[int]: Up to *count* physical qubit IDs sorted by fidelity
            (descending).  May be shorter than *count* if fewer candidates
            are available.
    """
    if used is None:
        used = set()
    # collect qubits with fidelity > 0 and not in used set
    candidates = [
        i
        for i, fid in enumerate(single_qubit_fidelities)
        if fid > 0.0 and i not in used
    ]
    # sort by fidelity descending, take top count
    candidates.sort(key=lambda i: single_qubit_fidelities[i], reverse=True)
    return candidates[:count]


def get_qubit_num_from_ir(gates_list: list) -> int:
    """Determine the logical qubit count from a gate list.

    Scans all ``.targets`` in *gates_list* and returns ``max(target) + 1``,
    which represents the minimum number of logical qubits needed to address
    every referenced qubit ID.

    Args:
        gates_list (list): Gate operations whose ``.targets`` reference
            logical qubit IDs.

    Returns:
        int: ``max(targets) + 1`` across all gates, or ``0`` when the list
            is empty or contains no target references.
    """
    bits_set: set[int] = set()
    # collect all qubit indices used in gates
    for gate in gates_list:
        bits_set.update(gate.targets)
    if not bits_set:
        return 0
    return max(bits_set) + 1


def build_single_qubit_mapping(
    gate_ops: list,
    measure_ops: list,
    target_bits: list[int],
    single_qubit_fidelities: list[float],
    logic_qubit_num: int,
) -> list[int]:
    """Build a logical-to-physical mapping for all-single-qubit circuits.

    Collects all used logical qubits (gates + measures), then assigns
    physical targets in order based on priority:
    target_bits > fidelity ranking > empty (identity fallback).

    Args:
        gate_ops (list): Gate operations whose ``.targets`` reference
            logical qubit IDs.
        measure_ops (list): Measure operations whose ``.targets`` reference
            logical qubit IDs.
        target_bits (list[int]): User-specified physical qubit IDs.
        single_qubit_fidelities (list[float]): Per-qubit 1-q gate fidelity.
        logic_qubit_num (int): Total number of logical qubits in the circuit.

    Returns:
        list[int]: Mapping from logical ID to physical ID, with ``-1``
            for unused logical IDs.  Returns an empty list when no
            target_bits and no fidelity data are available, or when
            fidelity-based selection yields fewer qubits than needed.

    Raises:
        ValueError: If ``target_bits`` count is less than circuit qubit count.
    """
    # collect all used logical qubits (gates + measures), sorted ascending
    used_set: set[int] = set()
    for gate in gate_ops:
        used_set.update(gate.targets)
    for measure in measure_ops:
        used_set.update(measure.targets)
    used_sorted = sorted(used_set)
    used_count = len(used_sorted)

    physical_targets: list[int] = []
    if target_bits:
        # target_bits non-empty: map to user-specified physical qubits
        target_set = sorted(set(target_bits))
        if len(target_set) < used_count:
            raise ValueError(
                f"target_bits count ({len(target_set)}) "
                f"< circuit qubit count ({used_count}); "
                f"not enough target qubits"
            )
        physical_targets = target_set
    elif single_qubit_fidelities:
        # no target_bits: pick top-N by fidelity
        physical_targets = select_best_single_qubits(
            single_qubit_fidelities, used=set(), count=used_count
        )
        if len(physical_targets) < used_count:
            # not enough physical qubits available
            return []
    else:
        # no target_bits and no fidelity data
        return []

    # pair logical qubits with physical targets in order
    mapping = [-1] * logic_qubit_num
    for order in range(used_count):
        mapping[used_sorted[order]] = physical_targets[order]
    return mapping


def find_connected_components(
    coupling_list: list[tuple[int, int]],
) -> dict[int, int]:
    """Find connected components of the coupling graph via BFS.

    Each node is mapped to the representative of its component, which
    is the minimum node ID within that component.

    Args:
        coupling_list (list[tuple[int, int]]): Coupling graph edges as
            ``(u, v)`` pairs.

    Returns:
        dict[int, int]: Mapping from node ID to its component
            representative (minimum node ID in that component).
    """
    # build undirected adjacency list
    adjacency: dict[int, list[int]] = {}
    for src, tgt in coupling_list:
        adjacency.setdefault(src, []).append(tgt)
        adjacency.setdefault(tgt, []).append(src)

    # BFS to find connected components
    component_map: dict[int, int] = {}
    for node in adjacency:
        if node in component_map:
            continue

        component: list[int] = []
        bfs_queue = deque([node])
        component_map[node] = node
        while bfs_queue:
            current = bfs_queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in component_map:
                    component_map[neighbor] = neighbor
                    bfs_queue.append(neighbor)

        # assign minimum node ID as component representative
        component_root = min(component)
        for qubit_id in component:
            component_map[qubit_id] = component_root

    return component_map
