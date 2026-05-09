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
import rustworkx as rx

from wy_qcos.common.cmss.gate_operation import SWAP
from wy_qcos.common.cmss.gate_operation import GateOperation


class Node:
    def __init__(self, gate: GateOperation):
        # The GateOperation corresponding to the current node
        self.gate: GateOperation = gate
        self.bits: list[int] = gate.targets
        # successor nodes of the current gate
        self.edges = []
        # A series of single-qubit gates following a two-qubit gate,
        # which can be executed together with this node
        self.attach: list[Node] = []
        # number of predecessor nodes not yet executed
        self.pre_number: int = 0


class SABRE:
    def __init__(
        self,
        coupling_list: list | nx.Graph,
        extention_size: int = 20,
        weight: float = 0.5,
        decay: float = 0.001,
    ):
        """Initialize SABRE mapping algorithm.

        ref: "Tackling the qubit mapping problem for NISQ-era quantum devices".

        Args:
            coupling_list (list | nx.Graph): The coupling graph of the quantum
                machine.
            extention_size (int, optional): Size of the extention set used by
                the lookahead strategy. Defaults to 20.
            weight (float, optional): Weight parameter for combining basic and
                extended heuristic costs. Defaults to 0.5.
            decay (float, optional): Decay factor used to reduce the influence
                of frequently swapped qubits. Defaults to 0.001.
        """
        if isinstance(coupling_list, nx.Graph):
            coupling_list = coupling_list.edges
        self.coupling_graph, self.phy_idx_map = self.get_rx_graph(
            coupling_list
        )
        self.phy_qubit_num = self.coupling_graph.num_nodes()
        self.extention_size = extention_size
        self.weight = weight
        self.decay = decay

        # the current mapping during the mapping process
        # logic to physical
        self.cur_l2p = []
        # physical to logic
        self.cur_p2l = []
        # distance matrix between physical qubits
        self.dist = rx.graph_all_pairs_dijkstra_path_lengths(
            self.coupling_graph, lambda _: 1
        )
        # front layer of DAG: nodes that can be executed now
        self.front_layer: list[Node] = []

        # final result
        self.phy2logic = []
        self.logic2phy = []
        self.phy_exe_gates = []

    def get_rx_graph(self, coupling_list: list):
        """Convert a topology list to an rx.PyGraph.

        Args:
            coupling_list (list): The hardware topology list.

        Returns:
            rx.PyGraph, dict: The graph object and a mapping from physical
                qubit to its index in the graph.
        """
        coupling_graph = rx.PyGraph(multigraph=False)
        nodes = []
        for edge in coupling_list:
            nodes.extend(edge)
        nodes = list(set(nodes))
        node_indices = coupling_graph.add_nodes_from(nodes)
        phy_idx_map = {}
        for i, node in enumerate(node_indices):
            phy_idx_map[node] = i
        coupling_graph.add_edges_from_no_data(coupling_list)
        return coupling_graph, phy_idx_map

    def execute(self, gates_list: list[GateOperation], initial_l2p=None):
        """Execute the SABRE mapping on the input circuit (IR).

        Args:
            gates_list (list[GateOperation]): a list of gates.
            initial_l2p (list[int], optional): initial logical to physical
                mapping. Defaults to None.
        """
        logic_qubit_num = self.get_qubit_num_from_ir(gates_list)
        phy_qubit_num = self.phy_qubit_num

        # initialize logical to physical mapping
        if initial_l2p is None:
            self.cur_l2p = list(range(phy_qubit_num))
        else:
            used_qubits = set(initial_l2p)
            remain_qubits = [
                q for q in range(phy_qubit_num) if q not in used_qubits
            ]
            # add remaining unmapped qubits at the end
            self.cur_l2p = initial_l2p + remain_qubits

        # physical to logical mapping
        self.cur_p2l = [0 for _ in range(phy_qubit_num)]
        for logical, physical in enumerate(self.cur_l2p):
            self.cur_p2l[physical] = logical

        # list of physical gates to be executed, including SWAP gates
        phy_exe_gates = []
        # list storing the latest node acting on each logical qubit
        pre_nodes: list[Node | None] = [None for _ in range(logic_qubit_num)]
        for gate in gates_list:
            node = Node(gate)
            # in-degree of the node
            pre_number = 0
            if len(node.bits) == 1:
                pre_node = pre_nodes[node.bits[0]]
                if pre_node is not None:
                    pre_node.attach.append(node)
                else:
                    # can execute in physical
                    phy_exe_gates.append(self.phy_gate(node.gate))
            elif len(node.bits) == 2:
                for bit in node.bits:
                    pre_node = pre_nodes[bit]
                    # add a edge from pre_node to node and add in-degree
                    if pre_node is not None and node not in pre_node.edges:
                        pre_node.edges.append(node)
                        pre_number += 1
                # update pre_nodes
                for bit in node.bits:
                    pre_nodes[bit] = node

                node.pre_number = pre_number
                # can execute in logical
                if pre_number == 0:
                    self.front_layer.append(node)

        # The main process of the SABRE algorithm
        decay = [1 for _ in range(phy_qubit_num)]
        # reset the decay parameters every 5 search steps
        decay_cycle = 5
        decay_time = 0
        while len(self.front_layer) > 0:
            decay_time += 1
            # reset the decay parameters
            if decay_time % decay_cycle == 0:
                decay = [1 for _ in range(phy_qubit_num)]

            exe_gate_list = []
            for node in self.front_layer:
                # can execute in physical
                if self.can_execute(node):
                    exe_gate_list.append(node)
                    phy_exe_gates.append(self.phy_gate(node.gate))
                    # the single qubit gate attached to the node
                    for gate_node in node.attach:
                        if not isinstance(gate_node, Node):
                            raise ValueError("The attached gate is not a Node")
                        phy_exe_gates.append(self.phy_gate(gate_node.gate))
            if len(exe_gate_list) != 0:
                for node in exe_gate_list:
                    self.front_layer.remove(node)
                    for successor in node.edges:
                        successor.pre_number -= 1
                        if successor.pre_number < 0:
                            raise ValueError("The pre_number of node is < 0")
                        if successor.pre_number == 0:
                            self.front_layer.append(successor)
                decay = [1 for _ in range(phy_qubit_num)]
            else:
                # no gate can be executed in physical
                # need to find the best swap
                candidate_list = self.obtain_swaps()
                best_swap = []
                best_score = 0
                cur_best_mapping = []
                # calculate the base cost
                (
                    base_cost,
                    extend_size,
                    front_qubit_gate_map,
                    extend_qubit_gate_map,
                ) = self.heuristic_cost(self.cur_l2p)
                for swap in candidate_list:
                    temp_mapping = self.get_temp_mapping(swap)
                    # The cost change caused by the current candidate swap gate
                    delta = self.delta_heuristic_cost(
                        self.cur_l2p,
                        temp_mapping,
                        swap,
                        extend_size,
                        front_qubit_gate_map,
                        extend_qubit_gate_map,
                    )
                    H_score = base_cost + delta
                    H_score = H_score * max(
                        decay[self.cur_p2l[swap[0]]],
                        decay[self.cur_p2l[swap[1]]],
                    )
                    if len(best_swap) == 0 or H_score < best_score:
                        best_score = H_score
                        best_swap = swap
                        cur_best_mapping = temp_mapping

                # update the current mapping
                self.cur_p2l[best_swap[0]], self.cur_p2l[best_swap[1]] = (
                    self.cur_p2l[best_swap[1]],
                    self.cur_p2l[best_swap[0]],
                )
                self.cur_l2p = cur_best_mapping
                # insert a SWAP gate
                phy_exe_gates.append(SWAP([best_swap[0], best_swap[1]]))
                decay[self.cur_p2l[best_swap[0]]] += self.decay
                decay[self.cur_p2l[best_swap[1]]] += self.decay
        # final mapping
        self.phy2logic = self.cur_p2l
        self.logic2phy = self.cur_l2p
        self.phy_exe_gates = phy_exe_gates

    def get_qubit_num_from_ir(self, gates_list: list[GateOperation]) -> int:
        """Get the logic qubit number from the gates_list.

        Args:
            gates_list (list[GateOperation]): a list of gates.

        Returns:
            int: number of logic qubits.
        """
        bits_set = set()
        for gate in gates_list:
            bits_set.update(gate.targets)
        logic_qubit_num = max(bits_set) + 1
        return logic_qubit_num

    def can_execute(self, node: Node):
        """Whether the node can be executed in physical."""
        if len(node.bits) == 1:
            return True
        elif len(node.bits) == 2:
            logic0, logic1 = node.bits
            phy0, phy1 = self.cur_l2p[logic0], self.cur_l2p[logic1]
            phy0_idx = self.phy_idx_map[phy0]
            phy1_idx = self.phy_idx_map[phy1]
            return self.coupling_graph.has_edge(phy0_idx, phy1_idx)
        else:
            raise ValueError("The number of node.bits is not 1 or 2")

    def obtain_swaps(self):
        """Obtain all candidate swap gates."""
        candidates = []
        phy_bits = set()
        # Only consider SWAPs related to the front layer
        for node in self.front_layer:
            if len(node.bits) == 1:
                continue
            # Extract logical qubits and map them to physical qubits
            phy_bits = phy_bits.union({self.cur_l2p[bit] for bit in node.bits})

        # Traverse all edges
        for edge in self.coupling_graph.edge_list():
            if edge[0] in phy_bits or edge[1] in phy_bits:
                candidates.append(edge)
        return candidates

    def get_temp_mapping(self, edge: tuple):
        """Generate a new logic to physical mapping with a swap.

        Args:
            edge (tuple): a tuple of (u,v), indicate a swap gate.

        Returns:
            list[int]: a new logic to physical mapping.
        """
        new_mapping = self.cur_l2p.copy()
        u, v = edge[0], edge[1]
        new_mapping[self.cur_p2l[u]] = v
        new_mapping[self.cur_p2l[v]] = u
        return new_mapping

    def phy_gate(self, logic_gate: GateOperation) -> GateOperation:
        """Mapping a logic gate to a phy gate with logic2phy.

        Args:
            logic_gate (GateOperation): a logic gate, with logic qubits in
                targets.

        Returns:
            GateOperation: a physical gate, with physical qubits in targets.
        """
        # BaseOperation, e.g Measure.
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

    def heuristic_cost(self, logic2phy: list):
        """The heuristic_cost function, calculate the cost of the new mapping.

        Args:
            logic2phy (list): a logic to physical mapping.

        Returns:
            float: the heuristic cost of the new mapping.
        """
        # basic heuristic based on current front layer
        h_basic = 0.0
        # extend heuristic from lookahead set
        h_extend = 0.0

        front_layer = self.front_layer
        dist = self.dist
        extention_size = self.extention_size

        # map from qubit -> gates that include the qubit
        front_qubit_gate_map = {}
        # compute cost of front layer
        for node in front_layer:
            q0, q1 = node.bits
            idx0 = self.phy_idx_map[logic2phy[q0]]
            idx1 = self.phy_idx_map[logic2phy[q1]]
            h_basic += dist[idx0][idx1]
            front_qubit_gate_map.setdefault(q0, []).append(node)
            front_qubit_gate_map.setdefault(q1, []).append(node)
        f_count = len(front_layer)
        if f_count > 0:
            h_basic /= f_count

        # lookahead extension set
        extend_set = []
        extend_qubit_gate_map = {}
        # temporary queue to store nodes whose indegree is modified
        temp_indegree = {}
        extend_queue = deque(front_layer)
        while len(extend_set) < extention_size and extend_queue:
            node = extend_queue.popleft()
            for successor in node.edges:
                if successor not in temp_indegree:
                    new_deg = successor.pre_number - 1
                else:
                    new_deg = temp_indegree[successor] - 1
                temp_indegree[successor] = new_deg
                if new_deg == 0:
                    extend_set.append(successor)
                    extend_queue.append(successor)
                    q0, q1 = successor.bits
                    extend_qubit_gate_map.setdefault(q0, []).append(successor)
                    extend_qubit_gate_map.setdefault(q1, []).append(successor)

        # compute cost of extension set
        e_count = len(extend_set)
        for node in extend_set:
            idx0 = self.phy_idx_map[logic2phy[node.bits[0]]]
            idx1 = self.phy_idx_map[logic2phy[node.bits[1]]]
            h_extend += dist[idx0][idx1]
        if e_count > 0:
            h_extend /= e_count

        return (
            h_basic + self.weight * h_extend,
            e_count,
            front_qubit_gate_map,
            extend_qubit_gate_map,
        )

    def delta_heuristic_cost(
        self,
        old_l2p: list,
        new_l2p: list,
        swap: tuple,
        extend_size: int,
        front_qubit_gate_map: dict,
        extend_qubit_gate_map: dict,
    ):
        """Calculate the incremental cost after applying a swap gate.

        Args:
            old_l2p (list): Original logical-to-physical qubit mapping.
            new_l2p (list): New logical-to-physical qubit mapping.
            swap (tuple): The candidate swap gate that transforms old_l2p to
                new_l2p.
            extend_size (int): Size of the extension set, used for normalizing
                the cost.
            front_qubit_gate_map (dict): Mapping from qubits in the front layer
                to the gates they affect, for quickly finding the cost impact
                of a swap.
            extend_qubit_gate_map (dict): Same as above, but for the lookahead
                extension layer.

        Returns:
            float: Incremental cost after applying the swap gate.
        """
        phy_idx_map = self.phy_idx_map
        dist = self.dist
        # Logical qubits corresponding to the candidate swap gate
        logic_q0, logic_q1 = self.cur_p2l[swap[0]], self.cur_p2l[swap[1]]

        def _delta_sum(nodes):
            """Compute the incremental cost for a set of nodes."""
            delta = 0.0
            for node in nodes:
                q0, q1 = node.bits
                delta += (
                    dist[phy_idx_map[new_l2p[q0]]][phy_idx_map[new_l2p[q1]]]
                    - dist[phy_idx_map[old_l2p[q0]]][phy_idx_map[old_l2p[q1]]]
                )
            return delta

        # All front-layer gates affected by the two qubits of the swap
        affected_front_nodes = set(
            front_qubit_gate_map.get(logic_q0, [])
        ) | set(front_qubit_gate_map.get(logic_q1, []))
        delta_front = _delta_sum(affected_front_nodes)

        f_count = len(self.front_layer)
        if f_count > 0:
            delta_front /= f_count

        # All extension-layer gates affected by the two qubits of the swap
        affected_extend_nodes = set(
            extend_qubit_gate_map.get(logic_q0, [])
        ) | set(extend_qubit_gate_map.get(logic_q1, []))
        delta_extend = _delta_sum(affected_extend_nodes)

        delta_extend *= self.weight
        if extend_size > 0:
            delta_extend /= extend_size

        return delta_front + delta_extend
