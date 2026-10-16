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
import copy
from collections import deque

import networkx as nx

from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.common.cmss.gate_operation import SWAP, GateOperation
from wy_qcos.common.cmss.measure import Measure
from wy_qcos.transpiler.cmss.mapping.utils.mapping_utils import (
    apply_logical_remap,
    build_single_qubit_mapping,
    build_logical_remap,
    compute_adaptive_fidelity_threshold,
    filter_low_fidelity,
    find_connected_components,
    get_qubit_num_from_ir,
    induce_target_subgraph,
    restore_logical_mapping,
    select_largest_component,
)
from wy_qcos.transpiler.cmss.mapping.init_mapping.sc_initial_mapping import (
    fidelity_aware_initial_mapping,
)


# BFS "infinity" sentinel for unreachable qubit pairs
_INF = 1000000


class Node:
    """DAG node wrapping a quantum gate for SABRE routing.

    Each node represents one gate in the directed acyclic graph (DAG)
    built from the input circuit.  ``edges`` tracks successor 2-q gates
    that depend on this node, while ``attach`` collects trailing
    single-qubit gates that can be emitted together with this 2-q gate.

    Attributes:
        gate (GateOperation): The underlying gate operation.
        bits (list[int]): Logical qubit IDs the gate acts on
            (copied from ``gate.targets``).
        edges (list[Node]): Successor nodes (gates blocked by this one).
        attach (list[Node]): Single-qubit gates immediately following
            this 2-q gate on the same qubit lines.
        pre_number (int): Number of predecessor nodes not yet executed.
            The node becomes executable when this reaches 0.
        index (int): Position in the node pool list, used by
            :meth:`SABRE.delta_heuristic_cost` for O(1) bookkeeping.
    """

    def __init__(self, gate: GateOperation):
        """Initialize a DAG node from a gate operation.

        Args:
            gate (GateOperation): The gate to wrap.  Its ``.targets``
                are copied into ``bits``.
        """
        self.gate: GateOperation = gate
        self.bits: list[int] = gate.targets
        # successor nodes of the current gate
        self.edges: list[Node] = []
        # single-qubit gates following this 2q gate, executed together
        self.attach: list[Node] = []
        # number of predecessor nodes not yet executed
        self.pre_number: int = 0
        # index in the node pool (used by delta_heuristic_cost)
        self.index: int = -1


class SABRE:
    """SABRE mapping algorithm.

    SABRE routing implementation with fidelity-aware routing,
    stuck detection with Dijkstra fallback, target_bits subgraph support,
    logical qubit densification, and all-single-qubit shortcut.
    """

    def __init__(
        self,
        coupling_list: list | nx.Graph,
        edge_fidelities: list | None = None,
        single_qubit_fidelities: list | None = None,
        target_bits: list | None = None,
        fidelity_threshold: float = -1.0,
        fidelity_weight: float = 0.5,
        extension_size: int = 20,
        weight: float = 0.5,
        decay: float = 0.001,
    ):
        """Initialize SABRE.

        Args:
            coupling_list: coupling graph edges (list of pairs or nx.Graph).
            edge_fidelities: per-edge CZ fidelity
                (same order as coupling_list).
                Empty/None to disable fidelity filtering.
            single_qubit_fidelities: per-physical-qubit 1q fidelity.
            target_bits: restrict routing to these physical qubits (induced
                subgraph).  Empty/None for full chip.
            fidelity_threshold: edge fidelity cutoff.  <0 = adaptive
                (mean - std, clamped [0.3, 0.9]).
            fidelity_weight: weight for DenseLayout fidelity scoring [0, 1].
            extension_size: lookahead extension set size.
            weight: front/extend cost blend weight.
            decay: SWAP decay factor.
        """
        # --- store parameters ---
        if isinstance(coupling_list, nx.Graph):
            coupling_list = list(coupling_list.edges)

        self.edge_fidelities = list(edge_fidelities) if edge_fidelities else []
        self.single_qubit_fidelities = (
            list(single_qubit_fidelities) if single_qubit_fidelities else []
        )
        self.fidelity_weight = fidelity_weight
        self.target_bits = list(target_bits) if target_bits else []
        self.extension_size = extension_size
        self.weight = weight
        self.decay = decay

        # adaptive fidelity threshold
        if fidelity_threshold < 0.0:
            self.fidelity_threshold = compute_adaptive_fidelity_threshold(
                self.edge_fidelities
            )
        else:
            self.fidelity_threshold = fidelity_threshold

        # --- preprocess coupling graph ---
        # work on copies so the caller's lists are untouched
        self.coupling_list = [tuple(edge) for edge in coupling_list]

        # save original max chip qubit ID (before filtering)
        self._max_chip_qubit = 0
        for u, v in self.coupling_list:
            self._max_chip_qubit = max(self._max_chip_qubit, u, v)

        if self.target_bits:
            # induced subgraph: skip filter + largest_component
            self.coupling_list, self.edge_fidelities = induce_target_subgraph(
                self.coupling_list, self.edge_fidelities, self.target_bits
            )
        else:
            # fidelity filter + largest connected component
            if self.edge_fidelities and self.fidelity_threshold > 0.0:
                self.coupling_list, self.edge_fidelities = filter_low_fidelity(
                    self.coupling_list,
                    self.edge_fidelities,
                    self.single_qubit_fidelities,
                    self.fidelity_threshold,
                )
            self.coupling_list, self.edge_fidelities = (
                select_largest_component(
                    self.coupling_list, self.edge_fidelities
                )
            )

        # --- build internal graph structures (indexed by physical ID) ---
        self._build_coupling_graph()

        # distance matrix (BFS, indexed by physical ID)
        self._init_distance_matrix()

        # state (populated by execute / _execute_routing)
        self.cur_l2p: list[int] = []
        self.cur_p2l: list[int] = []
        self.front_layer: list[Node] = []
        self.phy2logic: list[int] = []
        self.logic2phy: list[int] = []
        self.initial_l2p: list[int] = []
        self.phy_exe_gates: list = []

        # pre-allocated buffers for heuristic cost
        self._front_qubit_gate_map: list[list[Node]] = []
        self._extend_qubit_gate_map: list[list[Node]] = []
        self._temp_indegree: list[int] = []
        self._touched_indices: list[int] = []

    def _build_coupling_graph(self):
        """Build adjacency list and adjacency matrix."""
        max_id = 0
        unique_qubits = set()
        for u, v in self.coupling_list:
            max_id = max(max_id, u, v)
            unique_qubits.add(u)
            unique_qubits.add(v)

        # _max_phy_id: used for indexing arrays
        # (dist/adj_list/adj_matrix/cur_l2p/cur_p2l)
        self._max_phy_id = max_id
        # phy_qubit_num: count of unique physical qubits
        # (excluding isolated ones)
        self.phy_qubit_num = len(unique_qubits)
        array_size = max_id + 1

        self._adj_list = [[] for _ in range(array_size)]
        self._adj_matrix = [[False] * array_size for _ in range(array_size)]
        for u, v in self.coupling_list:
            if not self._adj_matrix[u][v]:
                self._adj_list[u].append(v)
                self._adj_list[v].append(u)
                self._adj_matrix[u][v] = True
                self._adj_matrix[v][u] = True

    def _init_distance_matrix(self):
        """BFS shortest-path distances, indexed by physical qubit ID.

        Performs BFS from each physical qubit to compute shortest path lengths
        to all other qubits. Results stored in _dist matrix for O(1) lookup
        during heuristic cost calculation.
        """
        array_size = self._max_phy_id + 1
        self._dist = [[_INF] * array_size for _ in range(array_size)]
        for start in range(array_size):
            if not self._adj_list[start]:
                continue
            self._dist[start][start] = 0
            queue = deque([start])
            # BFS main loop: traverse neighbors layer by layer
            while queue:
                curr = queue.popleft()
                for neighbor in self._adj_list[curr]:
                    # update if shorter path found
                    nd = self._dist[start][curr] + 1
                    if self._dist[start][neighbor] > nd:
                        self._dist[start][neighbor] = nd
                        queue.append(neighbor)

    def _extend_l2p_with_unused_qubits(self, old_size: int) -> None:
        """Extend ``cur_l2p`` to cover all logical qubits.

        Prioritizes assigning physical qubits that are neighbors of already-
        mapped qubits, then falls back to any qubit with edges.  Isolated
        physical qubits are never assigned.

        Args:
            old_size (int): Number of entries in ``cur_l2p`` before extension.

        Raises:
            RuntimeError: If the chip has too few usable physical qubits.
        """
        logic_qubit_num = self._logic_qubit_num
        array_size = self._max_phy_id + 1

        used_phy = [False] * array_size
        for i in range(old_size):
            phy = self.cur_l2p[i]
            if 0 <= phy < array_size:
                used_phy[phy] = True

        # collect unused neighbors of already-assigned qubits
        neighbors: list[int] = []
        seen_neighbors: set[int] = set()
        for i in range(old_size):
            for neighbor in self._adj_list[self.cur_l2p[i]]:
                if not used_phy[neighbor] and neighbor not in seen_neighbors:
                    neighbors.append(neighbor)
                    seen_neighbors.add(neighbor)
        neighbors.sort()

        # assign neighbors first
        assigned = old_size
        for phy in neighbors:
            if assigned >= logic_qubit_num:
                break
            if not used_phy[phy]:
                self.cur_l2p[assigned] = phy
                used_phy[phy] = True
                assigned += 1

        # fall back to any qubit with edges
        for phy in range(array_size):
            if assigned >= logic_qubit_num:
                break
            if not used_phy[phy] and self._adj_list[phy]:
                self.cur_l2p[assigned] = phy
                used_phy[phy] = True
                assigned += 1

        if assigned < logic_qubit_num:
            raise RuntimeError(
                f"Not enough physical qubits: need {logic_qubit_num} "
                f"but chip has {array_size}"
            )

    def _build_dag(self, gates_list: list, logic_qubit_num: int):
        """Build dependency DAG from gate list.

        Creates a directed acyclic graph where nodes represent gates and
        edges represent dependencies (gates that must execute in sequence).
        Single-qubit gates are attached to the previous two-qubit gate on
        the same qubit. Two-qubit gates depend on their predecessor gates.

        Args:
            gates_list: List of gate operations.
            logic_qubit_num: Number of logical qubits.

        Returns:
            tuple: (node_pool, result) where node_pool contains all DAG nodes
                and result contains gates that can execute immediately.
        """
        pre_nodes: list[Node | None] = [None] * logic_qubit_num
        self.front_layer = []
        result: list = []
        node_pool: list[Node] = []

        # pre-allocate heuristic buffers
        self._front_qubit_gate_map = [[] for _ in range(logic_qubit_num)]
        self._extend_qubit_gate_map = [[] for _ in range(logic_qubit_num)]
        self._temp_indegree = [-1] * len(gates_list)
        self._touched_indices = []

        # build DAG by processing each gate
        for gate in gates_list:
            if gate.name == "sync":
                continue
            node = Node(gate)
            node.index = len(node_pool)
            node_pool.append(node)
            pre_number = 0

            if len(node.bits) == 1:
                # single-qubit gate: attach to previous 2q gate
                # or execute immediately
                pre_node = pre_nodes[node.bits[0]]
                if pre_node is not None:
                    pre_node.attach.append(node)
                else:
                    result.append(self.phy_gate(node.gate))
            elif len(node.bits) == 2:
                # two-qubit gate: add edges from predecessors
                for bit in node.bits:
                    pre_node = pre_nodes[bit]
                    if pre_node is not None and node not in pre_node.edges:
                        pre_node.edges.append(node)
                        pre_number += 1
                # update last gate on each qubit
                for bit in node.bits:
                    pre_nodes[bit] = node
                node.pre_number = pre_number
                # gate with no dependencies can execute immediately
                if pre_number == 0:
                    self.front_layer.append(node)
        return node_pool, result

    def _all_single_qubit_mapping(
        self,
        gate_ops: list[GateOperation],
        measure_ops: list,
    ) -> list[GateOperation]:
        """Direct mapping for circuits with no two-qubit gates.

        Validates target_bits
        bounds, delegates to ``build_single_qubit_mapping``, and falls
        back to identity mapping when no target_bits or fidelity data
        are available.

        Args:
            gate_ops (list[GateOperation]): Single-qubit gate operations.
            measure_ops (list): Measure operations (used to collect qubit
                IDs but not rewritten here).

        Returns:
            list[GateOperation]: Gates with targets rewritten to physical IDs.

        Raises:
            ValueError: If ``target_bits`` is out of range, has fewer
                entries than circuit qubits, or the chip has too few
                physical qubits.
        """
        # target_bits bounds validation
        if self.target_bits:
            max_valid = self._max_chip_qubit
            if self.single_qubit_fidelities:
                max_valid = max(
                    max_valid, len(self.single_qubit_fidelities) - 1
                )
            for tb in self.target_bits:
                if tb < 0 or tb > max_valid:
                    raise ValueError(
                        f"target_bit {tb} out of range [0, {max_valid}]"
                    )

        # delegate to build_single_qubit_mapping
        mapping = build_single_qubit_mapping(
            gate_ops,
            measure_ops,
            self.target_bits,
            self.single_qubit_fidelities,
            self._logic_qubit_num,
        )

        if not mapping:
            # no target_bits and no fidelity data: identity mapping
            available_phys = (
                len(self.single_qubit_fidelities)
                if self.single_qubit_fidelities
                else self._max_chip_qubit + 1
            )
            if self._logic_qubit_num > available_phys:
                raise ValueError(
                    f"Circuit requires {self._logic_qubit_num} qubits, "
                    f"but chip only has {available_phys} available qubits"
                )
            self.logic2phy = list(range(self._logic_qubit_num))
            self.initial_l2p = list(self.logic2phy)
            return list(gate_ops)

        # rewrite gate targets to physical IDs
        routed: list[GateOperation] = []
        for gate in gate_ops:
            gate = copy.deepcopy(gate)
            gate.targets = [
                mapping[target]
                if 0 <= target < len(mapping) and mapping[target] >= 0
                else target
                for target in gate.targets
            ]
            routed.append(gate)

        self.logic2phy = mapping
        self.initial_l2p = list(self.logic2phy)
        return routed

    def execute(
        self,
        gates_list: list,
        initial_l2p: list[int] | None = None,
    ) -> None:
        """Execute SABRE mapping on the input circuit.

        Preprocessing pipeline:

        1. Separate measure/sync from regular gates.
        2. Densify logical qubit IDs if sparse.
        3. Compute ``logic_qubit_num``.
        4. Auto-supplement measure if absent.
        5. Detect ``has_2q``; validate ``target_bits`` connectivity.
        6. Dispatch to ``_all_single_qubit_mapping`` or ``_execute_routing``.
        7. Append measure with updated physical targets.
        8. Restore logical mapping if densified.

        After execution the following attributes are populated:
        ``logic2phy``, ``initial_l2p``, ``phy_exe_gates``.

        Args:
            gates_list (list): Input gate list (may include Measure/Sync).
            initial_l2p (list[int] | None): Optional
                logical-to-physical
                mapping.  ``None`` uses identity mapping.
        """
        # 1. Separate measure/sync
        regular_gates = []
        measure_ops = []
        for gate in gates_list:
            if gate is None:
                raise ValueError(
                    "SABRE routing does not accept None gate operations"
                )
            if gate.name == "measure":
                measure_ops.append(gate)
            elif gate.name == "sync":
                continue
            else:
                regular_gates.append(gate)

        # 2. Logical qubit densification
        remap = build_logical_remap(regular_gates, measure_ops)
        did_preprocess = remap.dense_count > 0
        if did_preprocess:
            apply_logical_remap(regular_gates, measure_ops, remap)
            logic_qubit_num = remap.dense_count
        else:
            logic_qubit_num = get_qubit_num_from_ir(regular_gates)
            for measure in measure_ops:
                qubit_count = measure.targets[0] + 1
                logic_qubit_num = max(logic_qubit_num, qubit_count)
        self._logic_qubit_num = logic_qubit_num

        # 3. Auto-supplement measure
        # Always auto-supplement
        if not measure_ops:
            measure_ops = [Measure([i]) for i in range(logic_qubit_num)]

        # 4. Detect has_2q
        has_2q = any(
            gate.operation_type >= OperationType.DOUBLE_QUBIT_OPERATION.value
            for gate in regular_gates
        )

        # 5. target_bits connectivity validation
        if has_2q and self.target_bits:
            comp_map = find_connected_components(self.coupling_list)
            root = -1
            for target_bit in self.target_bits:
                comp = comp_map.get(target_bit)
                if comp is None:
                    raise ValueError(
                        f"target_bits do not form a connected graph: "
                        f"target_bit {target_bit} is isolated in the "
                        f"induced subgraph"
                    )
                if root == -1:
                    root = comp
                elif comp != root:
                    raise ValueError(
                        "target_bits do not form a connected graph"
                    )

        # 6. Compute fidelity-aware initial layout for 2-qubit circuits
        if has_2q and not initial_l2p:
            initial_l2p = fidelity_aware_initial_mapping(
                regular_gates,
                self.coupling_list,
                self.edge_fidelities,
                self.single_qubit_fidelities,
                logic_qubit_num,
                self.fidelity_weight,
            )

        # 7. Dispatch
        if not has_2q:
            routed_gates = self._all_single_qubit_mapping(
                regular_gates, measure_ops
            )
        else:
            routed_gates = self._execute_routing(regular_gates, initial_l2p)

        final_mapping = self.logic2phy

        # 8. Append measure with updated physical targets
        phy_exe_gates: list = list(routed_gates)
        for measure in measure_ops:
            logic_q = measure.targets[0]
            physical_q = (
                final_mapping[logic_q]
                if logic_q < len(final_mapping)
                else logic_q
            )
            physical_measure = Measure([physical_q])
            phy_exe_gates.append(physical_measure)

        self.phy_exe_gates = phy_exe_gates

        # 9. Restore logical mapping if densified
        if did_preprocess:
            self.logic2phy = restore_logical_mapping(remap, self.logic2phy)
            if self.initial_l2p:
                self.initial_l2p = restore_logical_mapping(
                    remap, self.initial_l2p
                )

    def _execute_routing(
        self, gates_list: list, initial_l2p: list | None
    ) -> list:
        """Core SABRE routing loop with stuck detection and Dijkstra fallback.

        Algorithm outline:

        1. Build DAG from gate dependencies.
        2. Maintain ``front_layer`` (gates ready to execute).
        3. Execute feasible gates when possible.
        4. Otherwise, find the best SWAP to insert based on heuristic.
        5. Use Dijkstra fallback when stuck (too many SWAPs without progress).

        Args:
            gates_list (list): Regular (non-measure, non-sync) gate operations.
            initial_l2p (list[int] | None): Optional
                logical-to-physical
                mapping.  ``None`` uses identity mapping.

        Returns:
            list: Routed ``GateOperation`` list (without measure gates).

        Raises:
            RuntimeError: If routing gets stuck with no candidate SWAPs or
                exceeds the maximum iteration count.
            ValueError: If a node's pre_number goes negative, indicating
                a DAG corruption.
        """
        logic_qubit_num = self._logic_qubit_num
        array_size = self._max_phy_id + 1

        # --- initialize mapping ---
        if initial_l2p is None or len(initial_l2p) == 0:
            # no initial mapping: prefer physical qubits with edges to avoid
            # isolated nodes that would cause routing to stall
            graph_qubits = [i for i in range(array_size) if self._adj_list[i]]
            self.cur_l2p = [
                graph_qubits[i] if i < len(graph_qubits) else i
                for i in range(logic_qubit_num)
            ]
        else:
            self.cur_l2p = list(initial_l2p)
            old_size = len(self.cur_l2p)
            if old_size > logic_qubit_num:
                self.cur_l2p = self.cur_l2p[:logic_qubit_num]
            elif old_size < logic_qubit_num:
                self.cur_l2p.extend([-1] * (logic_qubit_num - old_size))
                self._extend_l2p_with_unused_qubits(old_size)
        self.initial_l2p = list(self.cur_l2p)

        # build reverse mapping: physical -> logical
        # (-1 means no logical qubit)
        self.cur_p2l = [-1] * array_size
        for logical in range(logic_qubit_num):
            physical = self.cur_l2p[logical]
            if physical < array_size:
                self.cur_p2l[physical] = logical

        # --- build DAG: track dependencies between gates ---
        _, result = self._build_dag(gates_list, logic_qubit_num)

        # --- main SABRE loop: iteratively execute gates or insert SWAPs ---
        decay_list = [1.0] * array_size
        decay_cycle = 5
        decay_time = 0
        # safety limit: prevent infinite loops
        max_iter = len(gates_list) * 100 + 10000
        iter_count = 0
        swaps_since_progress = 0
        # stuck detection: if too many SWAPs without progress, use Dijkstra
        stuck_threshold = max(logic_qubit_num * 2, 20)
        # checkpoint for backtracking when stuck
        checkpoint_l2p = list(self.cur_l2p)
        checkpoint_p2l = list(self.cur_p2l)
        checkpoint_result_size = len(result)

        while self.front_layer:
            decay_time += 1
            # reset decay periodically to prevent qubit bias
            if decay_time % decay_cycle == 0:
                decay_list = [1.0] * array_size

            # try to execute feasible gates
            exe_gate_list = []
            for node in self.front_layer:
                if self.can_execute(node):
                    exe_gate_list.append(node)
                    result.append(self.phy_gate(node.gate))
                    for gate_node in node.attach:
                        result.append(self.phy_gate(gate_node.gate))

            if exe_gate_list:
                # gates executed successfully: remove from front_layer
                # use set for O(1) lookup instead of list.remove() O(n)
                executed_set = set(id(node) for node in exe_gate_list)
                self.front_layer = [
                    node
                    for node in self.front_layer
                    if id(node) not in executed_set
                ]
                # update successors' dependency counts
                for node in exe_gate_list:
                    for successor in node.edges:
                        successor.pre_number -= 1
                        if successor.pre_number < 0:
                            raise ValueError("The pre_number of node is < 0")
                        if successor.pre_number == 0:
                            self.front_layer.append(successor)
                decay_list = [1.0] * array_size
                # save checkpoint after successful gate execution
                checkpoint_l2p = list(self.cur_l2p)
                checkpoint_p2l = list(self.cur_p2l)
                checkpoint_result_size = len(result)
                swaps_since_progress = 0
            else:
                # no gate can execute — find best SWAP
                candidate_list = self.obtain_swaps()
                if not candidate_list:
                    raise RuntimeError(
                        "SABRE routing stuck: no candidate SWAPs. "
                        "The coupling graph may be disconnected."
                    )

                iter_count += 1
                if iter_count > max_iter:
                    raise RuntimeError(
                        f"SABRE routing stuck: exceeded max iterations "
                        f"({max_iter})."
                    )

                # stuck detection + backtrack + Dijkstra
                swaps_since_progress += 1
                if swaps_since_progress > stuck_threshold:
                    # too many SWAPs without progress: backtrack to checkpoint
                    # and use Dijkstra shortest path to guarantee convergence
                    self.cur_l2p = list(checkpoint_l2p)
                    self.cur_p2l = list(checkpoint_p2l)
                    result = result[:checkpoint_result_size]
                    swaps_since_progress = 0
                    self._dijkstra_fallback(result)
                    continue

                # calculate base cost
                base_cost, actual_extend_size = self.heuristic_cost(
                    self.cur_l2p
                )

                best_swap = None
                best_score = 0.0
                # evaluate each candidate SWAP
                for swap in candidate_list:
                    delta = self.delta_heuristic_cost(
                        self.cur_l2p, swap, actual_extend_size
                    )
                    h_score = base_cost + delta
                    # apply decay factor to discourage
                    # repeatedly swapping same qubits
                    h_score *= max(decay_list[swap[0]], decay_list[swap[1]])
                    if best_swap is None or h_score < best_score:
                        best_score = h_score
                        best_swap = swap

                # apply best SWAP: update mappings inline
                lq0 = self.cur_p2l[best_swap[0]]
                lq1 = self.cur_p2l[best_swap[1]]
                if lq0 >= 0:
                    self.cur_l2p[lq0] = best_swap[1]
                if lq1 >= 0:
                    self.cur_l2p[lq1] = best_swap[0]
                self.cur_p2l[best_swap[0]], self.cur_p2l[best_swap[1]] = (
                    self.cur_p2l[best_swap[1]],
                    self.cur_p2l[best_swap[0]],
                )

                # insert SWAP gate and update decay
                result.append(SWAP([best_swap[0], best_swap[1]]))
                decay_list[best_swap[0]] += self.decay
                decay_list[best_swap[1]] += self.decay

        # final mapping
        self.phy2logic = list(self.cur_p2l)
        self.logic2phy = list(self.cur_l2p)
        return result

    def _dijkstra_fallback(self, phy_exe_gates: list) -> None:
        """Insert SWAPs along the shortest path to guarantee convergence.

        When the heuristic gets stuck (too many SWAPs without progress), fall
        back to Dijkstra shortest path.  This guarantees convergence by always
        making progress toward executing at least one front-layer gate.

        Args:
            phy_exe_gates (list): Accumulator list to which SWAP gates are
                appended in-place.

        Raises:
            RuntimeError: If all front-layer gates are unreachable.
        """
        # step 1: pick 2q gate with shortest physical distance in front layer
        stuck_node = None
        min_dist = _INF
        for node in self.front_layer:
            if len(node.bits) != 2:
                continue
            phy0 = self.cur_l2p[node.bits[0]]
            phy1 = self.cur_l2p[node.bits[1]]
            dist = self._dist[phy0][phy1]
            if dist < min_dist:
                min_dist = dist
                stuck_node = node
        if stuck_node is None or min_dist >= _INF:
            raise RuntimeError(
                "SABRE routing stuck: front layer gates unreachable."
            )

        # step 2: reconstruct shortest path via BFS distance matrix
        # trace back from destination to source
        src_phy = self.cur_l2p[stuck_node.bits[0]]
        dst_phy = self.cur_l2p[stuck_node.bits[1]]
        path = []
        curr = dst_phy
        while self._dist[src_phy][curr] > 0:
            path.append(curr)
            for neighbor in self._adj_list[curr]:
                step = self._dist[src_phy][curr] - 1
                if self._dist[src_phy][neighbor] == step:
                    curr = neighbor
                    break
        path.reverse()

        # step 3: insert SWAPs along the path
        # each SWAP brings the two qubits one step closer
        prev_phy = src_phy
        for i in range(len(path) - 1):
            swap_from = prev_phy
            swap_to = path[i]
            phy_exe_gates.append(SWAP([swap_from, swap_to]))
            # update mappings after each SWAP
            lq0 = self.cur_p2l[swap_from]
            lq1 = self.cur_p2l[swap_to]
            if lq0 >= 0:
                self.cur_l2p[lq0] = swap_to
            if lq1 >= 0:
                self.cur_l2p[lq1] = swap_from
            self.cur_p2l[swap_from], self.cur_p2l[swap_to] = (
                self.cur_p2l[swap_to],
                self.cur_p2l[swap_from],
            )
            prev_phy = swap_to

    def can_execute(self, node: Node) -> bool:
        """Check if node can be executed on the current physical mapping.

        A single-qubit gate is always executable.  A two-qubit gate requires
        its two mapped physical qubits to be adjacent in the coupling graph.

        Args:
            node (Node): The DAG node to check.

        Returns:
            bool: ``True`` if the gate can be executed immediately.

        Raises:
            ValueError: If the node has neither 1 nor 2 target qubits.
        """
        if len(node.bits) == 1:
            return True
        if len(node.bits) == 2:
            phy0 = self.cur_l2p[node.bits[0]]
            phy1 = self.cur_l2p[node.bits[1]]
            return self._adj_matrix[phy0][phy1]
        raise ValueError("The number of node.bits is not 1 or 2")

    def obtain_swaps(self) -> list:
        """Obtain all candidate SWAP gates adjacent to the front layer.

        Only enumerates edges adjacent to front-layer physical qubits,
        reducing the search space from all edges to relevant ones.

        Returns:
            list[tuple[int, int]]: Deduplicated ``(u, v)`` pairs with
                ``u <= v``, each representing a candidate SWAP.
        """
        # only enumerate edges adjacent to front-layer physical qubits
        # this reduces search space from all edges to relevant ones
        candidates = []
        seen = set()
        for node in self.front_layer:
            if len(node.bits) == 1:
                continue
            for bit in node.bits:
                phy = self.cur_l2p[bit]
                for neighbor in self._adj_list[phy]:
                    u, v = min(phy, neighbor), max(phy, neighbor)
                    if (u, v) not in seen:
                        seen.add((u, v))
                        candidates.append((u, v))
        return candidates

    def phy_gate(self, logic_gate: GateOperation) -> GateOperation:
        """Map a logical gate to a physical gate using ``cur_l2p``.

        Creates a copy of *logic_gate* with ``targets`` rewritten from
        logical to physical qubit IDs according to the current mapping.

        Args:
            logic_gate (GateOperation): Gate in logical qubit space.

        Returns:
            GateOperation: New gate with physical qubit targets.
        """
        if not isinstance(logic_gate, GateOperation):
            physical_gate = copy.deepcopy(logic_gate)
        else:
            physical_gate = GateOperation(
                name=logic_gate.name,
                targets=logic_gate.targets,
                arg_value=logic_gate.arg_value.copy(),
                operation_type=logic_gate.operation_type,
                hermitian=logic_gate.hermitian,
            )
        physical_gate.targets = [
            self.cur_l2p[bit] for bit in logic_gate.targets
        ]
        return physical_gate

    def heuristic_cost(self, logic2phy: list[int]) -> tuple[float, int]:
        """Compute heuristic cost and populate qubit-gate maps.

        The heuristic has two components:

        1. **Front layer cost**: average distance of gates ready to execute.
        2. **Lookahead cost**: average distance of upcoming gates in the
           extension set, weighted by ``self.weight``.

        Also populates ``_front_qubit_gate_map`` and
        ``_extend_qubit_gate_map`` for the incremental
        :meth:`delta_heuristic_cost` optimization.

        Args:
            logic2phy (list[int]): Current logical-to-physical mapping.

        Returns:
            tuple[float, int]: ``(h_total, e_count)`` where *h_total* is the
                blended heuristic cost and *e_count* is the number of
                extension-set gates considered.
        """
        h_basic = 0.0
        h_extend = 0.0

        # clear qubit-gate maps
        for v in self._front_qubit_gate_map:
            v.clear()
        for v in self._extend_qubit_gate_map:
            v.clear()

        # front layer cost
        for node in self.front_layer:
            q0, q1 = node.bits
            h_basic += self._dist[logic2phy[q0]][logic2phy[q1]]
            self._front_qubit_gate_map[q0].append(node)
            self._front_qubit_gate_map[q1].append(node)
        f_count = len(self.front_layer)
        if f_count > 0:
            h_basic /= f_count

        # lookahead: build extension set using BFS from front layer
        # reset temp_indegree only for touched indices (optimization)
        for idx in self._touched_indices:
            self._temp_indegree[idx] = -1
        self._touched_indices.clear()

        bfs_queue = list(self.front_layer)
        queue_pos = 0
        e_count = 0

        while e_count < self.extension_size and queue_pos < len(bfs_queue):
            node = bfs_queue[queue_pos]
            queue_pos += 1
            for successor in node.edges:
                idx = successor.index
                if self._temp_indegree[idx] == -1:
                    self._temp_indegree[idx] = successor.pre_number
                    self._touched_indices.append(idx)
                self._temp_indegree[idx] -= 1
                # when all predecessors executed, add to extension set
                if self._temp_indegree[idx] == 0:
                    bfs_queue.append(successor)
                    e_count += 1
                    q0, q1 = successor.bits
                    h_extend += self._dist[logic2phy[q0]][logic2phy[q1]]
                    self._extend_qubit_gate_map[q0].append(successor)
                    self._extend_qubit_gate_map[q1].append(successor)

        if e_count > 0:
            h_extend /= e_count

        return h_basic + self.weight * h_extend, e_count

    def delta_heuristic_cost(
        self, old_l2p: list, swap: tuple, extend_size: int
    ) -> float:
        """Incremental heuristic cost change after applying a SWAP.

        Instead of recomputing the full heuristic for every candidate SWAP,
        compute only the delta (change in cost).  This avoids copying the
        entire mapping and recalculating distances for unaffected gates.

        Args:
            old_l2p (list[int]): Current logical-to-physical mapping.
            swap (tuple[int, int]): Physical qubit pair ``(u, v)`` to swap.
            extend_size (int): Number of gates in the extension set
                (from :meth:`heuristic_cost`), used for normalization.

        Returns:
            float: The change in heuristic cost caused by the SWAP.
        """
        logic_q0 = self.cur_p2l[swap[0]]
        logic_q1 = self.cur_p2l[swap[1]]

        def new_phy(logical_q):
            """Return the new physical ID of *logical_q* after the SWAP.

            Args:
                logical_q (int): Logical qubit ID to map.

            Returns:
                int: New physical qubit ID after applying the SWAP.
            """
            if logical_q == logic_q0:
                return swap[1]
            if logical_q == logic_q1:
                return swap[0]
            return old_l2p[logical_q]

        def compute_delta(qubit_gate_map):
            """Sum distance deltas for gates touching the swapped qubits.

            Args:
                qubit_gate_map (list[list[Node]]): Mapping from logical qubit
                    ID to the list of DAG nodes involving that qubit.

            Returns:
                float: Total change in heuristic distance caused by the SWAP.
            """
            delta = 0.0
            # process nodes involving logic_q0
            if 0 <= logic_q0 < len(qubit_gate_map):
                for node in qubit_gate_map[logic_q0]:
                    q0, q1 = node.bits
                    delta += (
                        self._dist[new_phy(q0)][new_phy(q1)]
                        - self._dist[old_l2p[q0]][old_l2p[q1]]
                    )
            # process nodes involving logic_q1 (skip already counted above)
            if 0 <= logic_q1 < len(qubit_gate_map):
                for node in qubit_gate_map[logic_q1]:
                    if logic_q0 in (node.bits[0], node.bits[1]):
                        continue
                    q0, q1 = node.bits
                    delta += (
                        self._dist[new_phy(q0)][new_phy(q1)]
                        - self._dist[old_l2p[q0]][old_l2p[q1]]
                    )
            return delta

        delta_front = compute_delta(self._front_qubit_gate_map)
        f_count = len(self.front_layer)
        if f_count > 0:
            delta_front /= f_count

        delta_extend = compute_delta(self._extend_qubit_gate_map)
        delta_extend *= self.weight
        if extend_size > 0:
            delta_extend /= extend_size

        return delta_front + delta_extend
