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

import copy

from networkx import Graph

from wy_qcos.transpiler.cmss.common.gate_operation import SWAP
from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation


class Node:
    def __init__(self, gate: GateOperation):
        # The GateOperation corresponding to the current node
        self.gate = gate
        self.bits = gate.targets
        # successor nodes of the current gate
        self.edges = []
        # A series of single-qubit gates following a two-qubit gate,
        # which can be executed together with this node
        self.attach = []
        # number of predecessor nodes not yet executed
        self.pre_number = 0


class SABRE:
    def __init__(
        self,
        coupling_graph: Graph,
        extention_size: int = 20,
        weight: float = 0.5,
        decay: float = 0.001,
    ):
        """Initialize SABRE mapping algorithm.

        ref: "Tackling the qubit mapping problem for NISQ-era quantum devices".

        Args:
            coupling_graph (Graph): The coupling graph of the quantum machine.
            extention_size (int, optional): Size of the extention set used by
                the lookahead strategy. Defaults to 20.
            weight (float, optional): Weight parameter for combining basic and
                extended heuristic costs. Defaults to 0.5.
            decay (float, optional): Decay factor used to reduce the influence
                of frequently swapped qubits. Defaults to 0.001.
        """
        self.coupling_graph = coupling_graph
        self.phy_qubit_num = len(self.coupling_graph.nodes())
        self.extention_size = extention_size
        self.weight = weight
        self.decay = decay

        # the current mapping during the mapping process
        # logic to physical
        self.cur_l2p = []
        # physical to logic
        self.cur_p2l = []
        # distance matrix between physical qubits
        self.dist = []
        # front layer of DAG: nodes that can be executed now
        self.front_layer = []
        # calculate the distance matrix
        self.cal_distance_matrix()

        # final result
        self.phy2logic = []
        self.logic2phy = []
        self.phy_exe_gates = []

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
            self.cur_l2p = copy.deepcopy(initial_l2p)
            # add remaining unmapped qubits at the end
            remain_qubits = list(range(phy_qubit_num))
            for number in initial_l2p:
                remain_qubits.remove(number)
            self.cur_l2p.extend(remain_qubits)

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
                    for gate in node.attach:
                        phy_exe_gates.append(self.phy_gate(gate.gate))
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
                for swap in candidate_list:
                    temp_mapping = self.get_temp_mapping(swap)
                    H_score = self.heuristic_cost(temp_mapping)
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
        logic_qubit_num = len(bits_set)
        return logic_qubit_num

    def cal_distance_matrix(self):
        """Calculate the distance matrix of the coupling graph."""
        dist = []
        phy_qubit_num = self.phy_qubit_num

        for _ in range(phy_qubit_num):
            # phy_qubit_num serves as a sentinel
            dist.append([phy_qubit_num for _ in range(phy_qubit_num)])

        # Dijkstra algorithm
        for edge in self.coupling_graph.edges():
            dist[edge[0]][edge[1]] = 1
            dist[edge[1]][edge[0]] = 1
        for k in range(phy_qubit_num):
            for i in range(phy_qubit_num):
                if i == k:
                    continue
                for j in range(phy_qubit_num):
                    if j in (i, k):
                        continue
                    dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
        self.dist = dist

    def can_execute(self, node: Node):
        """Whether the node can be executed in physical."""
        if len(node.bits) == 1:
            return True
        elif len(node.bits) == 2:
            return self.coupling_graph.has_edge(
                self.cur_l2p[node.bits[0]], self.cur_l2p[node.bits[1]]
            )
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
        for edge in self.coupling_graph.edges():
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
        physical_gate = copy.deepcopy(logic_gate)
        physical_gate.targets = [
            self.cur_l2p[bit] for bit in logic_gate.targets
        ]
        return physical_gate

    def heuristic_cost(self, newl2p: list):
        """The heuristic_cost function, calculate the cost of the new mapping.

        Args:
            newl2p (list): a new logic to physical mapping.

        Returns:
            float: the heuristic cost of the new mapping.
        """
        # basic heuristic based on current front layer
        h_basic = 0
        # extend heuristic from lookahead set
        h_extend = 0
        f_count = len(self.front_layer)
        extend_queue = []

        # compute cost of front layer
        for node in self.front_layer:
            h_basic += (
                self.dist[newl2p[node.bits[0]]][newl2p[node.bits[1]]] / f_count
            )
            extend_queue.append(node)

        # lookahead extension set
        e_set = []
        # temporary queue to store nodes whose indegree is modified
        dec_queue = []
        while len(e_set) < self.extention_size and len(extend_queue) > 0:
            node = extend_queue.pop(0)
            dec_queue.append(node)
            for successor in node.edges:
                successor.pre_number -= 1
                if successor.pre_number == 0:
                    e_set.append(successor)
                    extend_queue.append(successor)

        # compute cost of extension set
        e_count = len(e_set)
        for node in e_set:
            h_extend += (
                self.dist[newl2p[node.bits[0]]][newl2p[node.bits[1]]] / e_count
            )

        # restore pre_number
        for node in dec_queue:
            for n in node.edges:
                n.pre_number += 1

        return h_basic + self.weight * h_extend
