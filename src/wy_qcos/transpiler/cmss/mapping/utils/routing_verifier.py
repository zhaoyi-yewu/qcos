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
# MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Routing result verifier.

Verifies SABRE routing output by replaying the mapping transform:
builds a SABRE-style DAG from the original IR, then walks through
the physical gate list to confirm topology, gate identity,
dependency order, SWAP correctness, completeness, and final mapping
consistency.
"""

from networkx import Graph

from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import Node


def _build_dag(ir):
    """Build a SABRE-style DAG from the original IR for verification.

    Unlike SABRE's ``_build_dag``, this version keeps standalone
    single-qubit gates as pending (instead of immediately executing
    them), handles measure gates, and skips sync gates.
    Auto-supplements measures if the input has none.

    Args:
        ir (list): Original gate operations.

    Returns:
        tuple: (front_layer, pending_1q, counts, pending_measures)
            where counts is (total_1q, total_2q).
    """
    num_qubits = 0
    for gate in ir:
        for qubit in gate.targets:
            num_qubits = max(num_qubits, qubit + 1)

    pre_nodes = [None] * num_qubits
    front_layer = []
    pending_1q = []
    total_1q = 0
    total_2q = 0
    pending_measures = {}
    used_qubits = set()

    for gate in ir:
        name = gate.name
        targets = list(gate.targets)

        if name == "measure":
            for qubit in targets:
                pending_measures[qubit] = pending_measures.get(qubit, 0) + 1
            continue
        if name == "sync":
            continue

        used_qubits.update(targets)
        node = Node(gate)
        if len(targets) == 1:
            total_1q += 1
            pre = pre_nodes[targets[0]]
            if pre is not None:
                pre.attach.append(node)
            else:
                pending_1q.append(node)
        elif len(targets) == 2:
            total_2q += 1
            pre_number = 0
            for bit in targets:
                pre = pre_nodes[bit]
                if pre is not None and node not in pre.edges:
                    pre.edges.append(node)
                    pre_number += 1
            for bit in targets:
                pre_nodes[bit] = node
            node.pre_number = pre_number
            if pre_number == 0:
                front_layer.append(node)

    # auto-supplement measures if absent
    if not pending_measures:
        pending_measures = {qubit: 1 for qubit in used_qubits}

    return front_layer, pending_1q, (total_1q, total_2q), pending_measures


def _try_match(node_list, gate_name, gate_args, gate_targets, mapping):
    """Try to match a physical gate against a list of pending nodes.

    Matches by gate name, parameters, and physical qubit targets
    (derived from the current logical-to-physical mapping).

    Args:
        node_list (list[Node]): Pending nodes (pending_1q or
            front_layer).
        gate_name (str): Physical gate name.
        gate_args (list): Physical gate parameters.
        gate_targets (list): Physical gate targets.
        mapping (list[int]): Current logical-to-physical mapping.

    Returns:
        Node or None: The matched node, or None if no match.
    """
    for node in list(node_list):
        if node.gate.name != gate_name:
            continue
        if list(node.gate.arg_value) != gate_args:
            continue
        if len(node.bits) != len(gate_targets):
            continue
        expected_phy = [mapping[q] for q in node.bits]
        if expected_phy != gate_targets:
            continue
        node_list.remove(node)
        return node
    return None


def _apply_swap(mapping, phy_to_idx, swap_targets):
    """Update mapping and reverse index for a SWAP gate.

    Args:
        mapping (list[int]): Current mapping (modified in-place).
        phy_to_idx (dict[int, int]): Reverse mapping
            physical -> logical index (modified in-place).
        swap_targets (list[int]): Two physical qubit IDs.

    Returns:
        bool: True if the SWAP was applied, False if neither endpoint
            is in the mapping (invalid SWAP).
    """
    u_phy, v_phy = swap_targets
    if u_phy in phy_to_idx and v_phy in phy_to_idx:
        ui = phy_to_idx[u_phy]
        vi = phy_to_idx[v_phy]
        mapping[ui], mapping[vi] = mapping[vi], mapping[ui]
        phy_to_idx[u_phy] = vi
        phy_to_idx[v_phy] = ui
    elif u_phy in phy_to_idx:
        ui = phy_to_idx[u_phy]
        mapping[ui] = v_phy
        del phy_to_idx[u_phy]
        phy_to_idx[v_phy] = ui
    elif v_phy in phy_to_idx:
        vi = phy_to_idx[v_phy]
        mapping[vi] = u_phy
        del phy_to_idx[v_phy]
        phy_to_idx[u_phy] = vi
    else:
        return False
    return True


def check_routing(
    coupling_graph,
    ir,
    phy_gates,
    mapping,
    final_mapping=None,
):
    """Verify routing correctness by replaying the mapping transform.

    Walks through the physical gate list and matches each gate
    against a SABRE-style DAG built from the original IR.  Verifies:

    1. Topology: every 2-q gate + SWAP acts on adjacent physical
       qubits.
    2. Gate identity: output gate name + parameters match the
       original.
    3. Physical qubit match: output qubits match mapping[logical].
    4. Dependency order: each gate is executable when matched.
    5. SWAP mapping update: mapping is correctly updated by each
       SWAP.
    6. Gate completeness: all original gates executed, no extras.
    7. Final mapping consistency: accumulated SWAPs == reported
       mapping.

    Args:
        coupling_graph: networkx.Graph or list of coupling edges.
        ir (list): Original gate operations (logic circuit).
        phy_gates (list): Routed physical gate operations.
        mapping (list[int]): Initial logical-to-physical mapping,
            updated in-place during replay.
        final_mapping (list[int] | None): SABRE-reported final
            mapping.  None to skip the final-mapping check.

    Returns:
        bool: True if all checks pass, False otherwise.
    """
    if isinstance(coupling_graph, (list, tuple)):
        coupling_graph = Graph(coupling_graph)

    front_layer, pending_1q, (total_1q, total_2q), pending_measures = (
        _build_dag(ir)
    )

    # reverse mapping for O(1) SWAP and measure lookups
    phy_to_idx = {phy: idx for idx, phy in enumerate(mapping) if phy >= 0}

    executed_1q = 0
    executed_2q = 0
    idx = 0

    while idx < len(phy_gates):
        gate = phy_gates[idx]
        gate_name = gate.name
        gate_targets = list(gate.targets)
        gate_args = list(gate.arg_value)

        # Measure: verify physical qubit matches current mapping
        if gate_name == "measure":
            for phy_q in gate_targets:
                logic_q = phy_to_idx.get(phy_q)
                if logic_q is None:
                    return False
                if pending_measures.get(logic_q, 0) == 0:
                    return False
                pending_measures[logic_q] -= 1
                if pending_measures[logic_q] == 0:
                    del pending_measures[logic_q]
            idx += 1
            continue

        # Skip sync gates
        if gate_name == "sync":
            idx += 1
            continue

        # Try pending single-qubit gates first
        node = _try_match(
            pending_1q, gate_name, gate_args, gate_targets, mapping
        )
        if node is not None:
            executed_1q += 1
            idx += 1
            continue

        # Try front-layer 2-qubit gates
        node = _try_match(
            front_layer, gate_name, gate_args, gate_targets, mapping
        )
        if node is not None:
            u_phy, v_phy = gate_targets
            if not coupling_graph.has_edge(u_phy, v_phy):
                return False
            executed_2q += 1
            # Release attached single-qubit gates
            pending_1q.extend(node.attach)
            # Process successors
            for succ in node.edges:
                succ.pre_number -= 1
                if succ.pre_number == 0:
                    front_layer.append(succ)
            idx += 1
            continue

        # Routing SWAP: update mapping in-place
        if gate_name == "swap":
            if not _apply_swap(mapping, phy_to_idx, gate_targets):
                return False
            u_phy, v_phy = gate_targets
            if not coupling_graph.has_edge(u_phy, v_phy):
                return False
            idx += 1
            continue

        # No match found
        return False

    # Completeness: all gates must have been executed
    if executed_1q != total_1q or executed_2q != total_2q:
        return False
    if pending_1q or front_layer or pending_measures:
        return False

    # Final mapping consistency
    if final_mapping is not None:
        mapping_len = len(mapping)
        if mapping_len > len(final_mapping):
            return False
        for pos in range(mapping_len):
            if mapping[pos] != final_mapping[pos]:
                return False

    return True
