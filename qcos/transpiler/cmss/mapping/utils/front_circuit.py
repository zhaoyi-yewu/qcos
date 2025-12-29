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

import numpy as np


def qubit_convert(q_list):
    pass


class FrontCircuit:
    """根据硬件拓扑、量子线路拓扑、映射表等来获取当前可执行的线路、可交换的比特等.

    Args:
        AG：硬件拓扑。
        DG：量子线路拓扑。
        num_q_log：逻辑比特数。
        num_q_phy：物理比特数。
        log_to_phy：逻辑比特到物理比特的映射表。
        phy_to_log：物理比特到逻辑比特的映射表。
        front_layer：量子线路拓扑中最前面一层的所有节点（门）。
    """

    def __init__(self, DG, AG, front_cir_from=None):
        """Initialize FrontCircuit.

        Args:
            DG: Dependency graph of the circuit.
            AG: Architecture graph of the quantum machine.
            front_cir_from: Optional FrontCircuit to copy from.
        """
        self.DG = DG
        self.AG = AG
        # self.num_q_phy = len(AG)
        # self.num_q_log = self.num_q_phy
        # the max. index of physical qubits + 1
        self.num_q_phy = max(list(AG.nodes)) + 1
        self.num_q_log = DG.num_q
        self.__hash = None
        # self.unassigned_q = self.num_q_log
        if front_cir_from is None:
            self.num_remain_nodes = len(DG)
            # 映射表初始化
            self.log_to_phy = [-1] * self.num_q_log
            self.phy_to_log = [-1] * self.num_q_phy
            # find first gates and front layer
            # first gate value is -1 when the qubit has no gate in the front
            self.first_gates = [-1] * self.num_q_log
            self.front_layer = []
            current_nodes = []
            used_nodes = []
            for node in DG.nodes:
                if DG.in_degree[node] == 0:
                    current_nodes.append(node)
                    self.front_layer.append(node)
            i = 0
            while i < self.num_q_log and len(current_nodes) > 0:
                current_nodes.sort()
                node = current_nodes.pop(0)
                used_nodes.append(node)
                qubits = DG.nodes[node]["qubits"]
                for q in qubits:
                    if self.first_gates[q] == -1:
                        self.first_gates[q] = node
                        i += 1
                for node_new in DG.successors(node):
                    if node_new not in used_nodes:
                        flag = True
                        for node_pre in DG.predecessors(node_new):
                            if node_pre not in used_nodes:
                                flag = False
                        if flag:
                            current_nodes.append(node_new)
            if i > self.num_q_log:
                raise ValueError("Too many iterations")
        else:
            # copy
            self.num_remain_nodes = front_cir_from.num_remain_nodes
            # initial mapping
            self.log_to_phy = front_cir_from.log_to_phy.copy()
            self.phy_to_log = front_cir_from.phy_to_log.copy()
            # find first gates and front layer
            self.first_gates = front_cir_from.first_gates.copy()
            self.front_layer = front_cir_from.front_layer.copy()

    def __hash__(self):
        if self.__hash is None:
            info = tuple(self.front_layer), tuple(self.log_to_phy)
            self.__hash = hash(info)
        return self.__hash

    def assign_mapping_from_list(self, map_list):
        """Here the indices in map_list represent logical qubits."""
        for q_log in range(self.num_q_log):
            q_phy = map_list[q_log]
            self.log_to_phy[q_log] = q_phy
            self.phy_to_log[q_phy] = q_log
        exe_gates = self.execute_gates()
        return exe_gates

    def assian_mapping_naive(self):
        map_list = list(range(self.num_q_log))
        return self.assign_mapping_from_list(map_list)

    def swap(self, swap_phy):
        """交换门插入，此时需要更新映射表."""
        q_phy0, q_phy1 = swap_phy
        q_log0, q_log1 = self.phy_to_log[q_phy0], self.phy_to_log[q_phy1]
        # update mapping
        self.phy_to_log[q_phy0] = q_log1
        self.phy_to_log[q_phy1] = q_log0
        if q_log0 != -1:
            self.log_to_phy[q_log0] = q_phy1
        if q_log1 != -1:
            self.log_to_phy[q_log1] = q_phy0
        # execute gates
        return self.execute_gates()

    def copy(self):
        return FrontCircuit(self.DG, self.AG, self)

    def swap_new(self, swap_phy):
        """Use a SWAP to get a new FrontCircuit object."""
        # new_cir = FrontCircuit(self.DG, self.AG, self)
        new_cir = self.copy()
        exe_gates = new_cir.swap(swap_phy)
        return new_cir, exe_gates

    def _executable(self, node):
        """量子比特耦合性检查，判断在当前映射表下两个逻辑比特对应的物理比特是否可做两比特门."""
        qubits = self.DG.nodes[node]["qubits"]
        if len(qubits) == 1:
            return True
        q_log0, q_log1 = qubits
        q_phy0, q_phy1 = self.log_to_phy[q_log0], self.log_to_phy[q_log1]
        if q_phy0 != -1 and q_phy1 != -1:
            if (q_phy0, q_phy1) in self.AG.edges:
                return True
        return False

    def execute_front_layer(self):
        """Execute all gates in the front layer regardless of mapping.

        However, we won't execute the following possible executable gates.
        """
        layer = self.front_layer.copy()
        for node_dg in layer:
            self.execute_gate(node_dg)

    def execute_gates(self):
        """Find all executable gates and execute them."""
        exe_gates = []
        i = 0
        max_i = len(self.front_layer) - 1
        while i <= max_i:
            current_node = self.front_layer[i]
            # check cnot executable
            if self._executable(current_node):
                self.execute_gate_index(i)
                exe_gates.append(current_node)
                max_i = len(self.front_layer) - 1
            else:
                i += 1
        return exe_gates

    def execute_gate_index(self, front_layer_i):
        """Execute specified gate without executing its successors.

        Args:
            front_layer_i: Index of the gate in the front layer.
        """
        self.num_remain_nodes -= 1
        exe_node = self.front_layer.pop(front_layer_i)
        qubits = self.DG.nodes[exe_node]["qubits"]
        nodes_next = list(self.DG.successors(exe_node))
        nodes_next.sort()
        for q in qubits:
            self.first_gates[q] = -1
        # deal with the successors of executed node
        # here we assume the indices of nodes in DG follows the topological
        # order
        for node in nodes_next:
            for q in self.DG.nodes[node]["qubits"]:
                if self.first_gates[q] == -1:
                    self.first_gates[q] = node
            flag = True
            for q in self.DG.nodes[node]["qubits"]:
                if self.first_gates[q] != node:
                    flag = False
                    break
            if flag:
                self.front_layer.append(node)

    def execute_gate(self, node_DG):
        """Execute specified gate without executing its successors.

        Args:
            node_DG: Node in the DG to be executed.
        """
        front_layer_i = self.front_layer.index(node_DG)
        self.execute_gate_index(front_layer_i)

    def execute_gate_remote(self, node_DG):
        """Execute a gate with remote CNOT and then execute all its successors.

        Args:
            node_DG: Node in DG to be executed with remote CNOT.

        Returns:
            tuple[list, list]: list1: [(cx1), cx2, ...] physical CNOTs needed
                for remote gates. list2: [node1, node2, ...] newly executed
                nodes in DG excluding the input node_DG.
        """
        # construct remote CNOTs
        qubits_log = self.DG.nodes[node_DG]["qubits"]
        qubits_phy = (
            self.log_to_phy[qubits_log[0]],
            self.log_to_phy[qubits_log[1]],
        )
        if self.AG.shortest_length[qubits_phy[0]][qubits_phy[1]] != 2:
            raise ValueError("Invalid qubit distance")
        bridge_q = self.AG.shortest_path[qubits_phy[0]][qubits_phy[1]][1]
        remote_cxs = [
            (qubits_phy[0], bridge_q),
            (bridge_q, qubits_phy[1]),
            (qubits_phy[0], bridge_q),
            (bridge_q, qubits_phy[1]),
        ]
        # execute nodes in DG
        front_layer_i = self.front_layer.index(node_DG)
        self.execute_gate_index(front_layer_i)
        exe_nodes = self.execute_gates()
        return remote_cxs, exe_nodes

    def pertinent_swaps(self, score_layer):
        """Get available swap gates that can be inserted now.

        Args:
            score_layer: Number of layers to consider for scoring each SWAP.

        Returns:
            swaps_phy: List of swap gates.
            h_scores: List of scores for each swap.
            h_scores_front: List of front scores for each swap.
        """
        swaps_phy = []
        h_scores = []
        h_scores_front = []
        qubits_phy_node = [-1] * self.num_q_phy
        # 交换只发生在当前层中剩余的所有门对应的比特中，
        # 先统计出所有可交换的比特
        for node in self.front_layer:
            q0, q1 = self.DG.nodes[node]["qubits"]
            q0_phy = self.log_to_phy[q0]
            q1_phy = self.log_to_phy[q1]
            qubits_phy_node[q0_phy] = node
            qubits_phy_node[q1_phy] = node

        # 对每一个可插入交换门的比特对做判断
        for swap in self.AG.edges:
            q0, q1 = swap
            qubits_phy_other = list(range(self.num_q_phy))
            # physical qubits before swap to those after swap
            qubits_phy_other[q0] = q1
            qubits_phy_other[q1] = q0
            involve_nodes = []
            # 首先比特需要在前面统计的可交换比特中
            if qubits_phy_node[q0] != -1:
                involve_nodes.append(qubits_phy_node[q0])
            if qubits_phy_node[q1] != -1:
                involve_nodes.append(qubits_phy_node[q1])
            # add swap and score info
            if len(involve_nodes) > 0:
                swaps_phy.append(swap)
                i = 0
                # 计算swap的成本
                current_score, current_score_front = 0, 0
                node_count = 0
                decay = 1
                for layer_i in range(score_layer):
                    i_max = len(involve_nodes)
                    while i <= i_max - 1:
                        node = involve_nodes[i]
                        i += 1
                        q0, q1 = self.DG.nodes[node]["qubits"]
                        q0, q1 = self.log_to_phy[q0], self.log_to_phy[q1]
                        # is this node relevant to the swap?
                        if q0 in swap or q1 in swap:
                            dis_before = self.AG.shortest_length[q0][q1]
                            q0_after = qubits_phy_other[q0]
                            q1_after = qubits_phy_other[q1]
                            dis_after = self.AG.shortest_length[q0_after][
                                q1_after
                            ]
                            score_add = dis_before - dis_after
                            # if score_add < 0 and layer_i > 0: continue
                            if layer_i == 0:
                                current_score_front += score_add
                            current_score += score_add * decay
                            node_count += 1
                            for node_next in self.DG.successors(node):
                                if node_next not in involve_nodes:
                                    involve_nodes.append(node_next)
                    decay *= 0.7
                h_scores.append(current_score / 1)
                h_scores_front.append(current_score_front)
        return swaps_phy, h_scores, h_scores_front

    def print(self):
        gate_phy = []
        for node in self.front_layer:
            q0, q1 = self.DG.nodes[node]["qubits"]
            gate_phy.append((self.log_to_phy[q0], self.log_to_phy[q1]))
        print("mapping from log to phy:", self.log_to_phy)
        print("remaining gates:", self.num_remain_nodes)
        print("front layer physical gates:", gate_phy)
        # print('qubits first gates:', self.first_gates)

    def print_front_layer_qubits(self):
        """Print the physical qubits in the front layer."""
        q = []
        for node in self.front_layer:
            q0, q1 = self.DG.nodes[node]["qubits"]
            q.append((self.log_to_phy[q0], self.log_to_phy[q1]))
        print(q)

    def print_front_layer_len(self):
        """Print the physical qubits in the front layer."""
        length = 0
        for node in self.front_layer:
            q0, q1 = self.DG.nodes[node]["qubits"]
            q0, q1 = self.log_to_phy[q0], self.log_to_phy[q1]
            length += self.AG.shortest_length[q0][q1] - 1
        print("lenght for cxs in front layer", length)

    def get_future_cx_fix_num(self, num_cx):
        """Get a specific number of unexecuted cx info.

        Args:
            num_cx: Number of CX gates to get.

        Returns:
            cx0: List of first operand physical qubits.
            cx1: List of second operand physical qubits.
        """
        first_gates_back_up = self.first_gates.copy()
        front_layer_back_up = self.front_layer.copy()
        num_remain_nodes_back_up = self.num_remain_nodes
        cx0 = []
        cx1 = []
        i = 0
        while i < num_cx and self.num_remain_nodes > 0:
            i += 1
            if len(self.front_layer) == 0:
                raise RuntimeError("Empty front layer")
            node = self.front_layer[0]
            q0, q1 = self.DG.nodes[node]["qubits"]
            cx0.append(self.log_to_phy[q0])
            cx1.append(self.log_to_phy[q1])
            self.execute_gate(node)
        # restore information
        if len(cx0) > num_cx:
            raise ValueError("Too many CNOT gates")
        self.first_gates = first_gates_back_up
        self.front_layer = front_layer_back_up
        self.num_remain_nodes = num_remain_nodes_back_up
        return cx0, cx1

    def get_future_cx_fix_num_with_single(self, num_cx):
        """Get a specific number of unexecuted cx info with single gate info.

        Args:
            num_cx: Number of CX gates to get.

        Returns:
            cx0: List of first operand physical qubits.
            cx1: List of second operand physical qubits.
            single_gate0: Number of single qubit gates for first qubit.
            single_gate1: Number of single qubit gates for second qubit.
        """
        first_gates_back_up = self.first_gates.copy()
        front_layer_back_up = self.front_layer.copy()
        num_remain_nodes_back_up = self.num_remain_nodes
        cx0 = []
        cx1 = []
        single_gate0, single_gate1 = [], []
        i = 0
        while i < num_cx and self.num_remain_nodes > 0:
            i += 1
            if len(self.front_layer) == 0:
                raise RuntimeError("Empty front layer")
            node = self.front_layer[0]
            q0, q1 = self.DG.nodes[node]["qubits"]
            d0, d1 = -1, -1
            cx0.append(self.log_to_phy[q0])
            cx1.append(self.log_to_phy[q1])
            # consider single-qubit gates
            for _, qubits, _ in self.DG.nodes[node]["gates"]:
                num_q = len(qubits)
                if num_q == 1:
                    q = qubits[0]
                    if q == q0:
                        d0 += 1
                    if q == q1:
                        d1 += 1
                if num_q == 2:
                    depth_after = max((d0, d1)) + 1
                    d0 = depth_after
                    d1 = depth_after
            single_gate0.append(d0)
            single_gate1.append(d1)
            self.execute_gate(node)
        # restore information
        if len(cx0) > num_cx:
            raise ValueError("Too many CNOT gates")
        self.first_gates = first_gates_back_up
        self.front_layer = front_layer_back_up
        self.num_remain_nodes = num_remain_nodes_back_up
        return cx0, cx1, single_gate0, single_gate1

    def get_future_cx_fix_num2(self, num_cx):
        """Get a specific number of unexecuted cx info layer by layer.

        Args:
            num_cx: Number of CX gates to get.

        Returns:
            cx0: List of first operand physical qubits.
            cx1: List of second operand physical qubits.
        """
        first_gates_back_up = self.first_gates.copy()
        front_layer_back_up = self.front_layer.copy()
        num_remain_nodes_back_up = self.num_remain_nodes
        cx0 = []
        cx1 = []
        i = 0
        while i < num_cx and self.num_remain_nodes > 0:
            for node in self.front_layer.copy():
                i += 1
                q0, q1 = self.DG.nodes[node]["qubits"]
                cx0.append(self.log_to_phy[q0])
                cx1.append(self.log_to_phy[q1])
                self.execute_gate(node)
        # restore information
        self.first_gates = first_gates_back_up
        self.front_layer = front_layer_back_up
        self.num_remain_nodes = num_remain_nodes_back_up
        return cx0, cx1

    def get_future_cx_fix_num3(self, num_cx):
        """Get a specific number of unexecuted cx info divided by layers.

        This method obtains gates layer by layer and returns tuples dividing
        gates according their layers.

        Args:
            num_cx: Number of CX gates to get.

        Returns:
            list: List of tuples where each tuple contains CX gates in one
                layer.
        """
        first_gates_back_up = self.first_gates.copy()
        front_layer_back_up = self.front_layer.copy()
        num_remain_nodes_back_up = self.num_remain_nodes
        i = 0
        cx_total = []
        while i < num_cx and self.num_remain_nodes > 0:
            cx_layer = []
            for node in self.front_layer.copy():
                i += 1
                q0, q1 = self.DG.nodes[node]["qubits"]
                cx0 = self.log_to_phy[q0]
                cx1 = self.log_to_phy[q1]
                if cx0 <= cx1:
                    cx_layer.append((cx0, cx1))
                else:
                    cx_layer.append((cx1, cx0))
                self.execute_gate(node)
            cx_layer.sort()
            cx_total.append(cx_layer)
        # restore information
        self.first_gates = first_gates_back_up
        self.front_layer = front_layer_back_up
        self.num_remain_nodes = num_remain_nodes_back_up
        return cx_total

    def check_equal(self, cir2):
        if (
            (self.log_to_phy == cir2.log_to_phy)
            and (self.phy_to_log == cir2.phy_to_log)
            and (self.num_remain_nodes == cir2.num_remain_nodes)
            and (self.front_layer == cir2.front_layer)
            and (self.first_gates == cir2.first_gates)
        ):
            return True
        else:
            return False

    def get_cir_matrix(self, num_layer):
        """Create a numpy matrix representing the circuit with CNOT gates.

        Args:
            num_layer: Number of layers.

        Returns:
            cir_map: Numpy matrix representing the circuit.
            i: Actual number of layers filled.
        """
        cir_map = np.zeros([num_layer, self.num_q_phy, self.num_q_phy]).astype(
            np.float32
        )
        DG = self.DG
        cir = self.copy()
        i = 0
        while i < num_layer:
            for node_dg in cir.front_layer:
                q0, q1 = DG.nodes[node_dg]["qubits"]
                q0_phy, q1_phy = (cir.log_to_phy[q0], cir.log_to_phy[q1])
                cir_map[i][q0_phy][q1_phy] = 1
                cir_map[i][q1_phy][q0_phy] = 1
            # go to next layer
            if len(cir.front_layer) == 0:
                break
            i += 1
            cir.execute_front_layer()
        return cir_map, i
