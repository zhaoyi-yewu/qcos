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

from abc import ABC
import networkx as nx
import rustworkx as rx
from copy import deepcopy
from collections import defaultdict

from wy_qcos.common.cmss.base_operation import BaseOperation, OperationType
from wy_qcos.common.cmss.move import Move
from wy_qcos.transpiler.common.errors import MappingException


class NASingleRoute(ABC):
    """NASingleRoute."""

    def __init__(self):
        self.qids = None
        self.logical_to_storage = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.operate_area = None
        self.storage_area = None
        self.qpu_config = None
        self.initial_layout = None
        self.final_layout = None

    def prepare_data(self, qbit_num, gates, qpu_configs):
        """配置qpu_config、gates、qbit_num，量子比特映射.

        Args:
            qbit_num: 比特数
            gates: 门列表
            qpu_configs: 拓扑
        """
        self.qpu_config = qpu_configs
        self.storage_area = self.qpu_config["storage_area"]
        self.operate_area = self.qpu_config["operate_area"]
        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config["coupler_map"].items():
            if (a not in self.operate_area) or (b not in self.operate_area):
                continue
            self.ag.add_edge(a, b)
        self.ag.shortest_length = dict(
            nx.shortest_path_length(
                self.ag,
                source=None,
                target=None,
                weight=None,
                method="dijkstra",
            )
        )

        self.gates = gates
        self.qbit_num = qbit_num
        if len(self.storage_area) < self.qbit_num:
            raise MappingException(
                f"not enough qubits, need {self.qbit_num}, "
                f"but only {len(self.storage_area)}."
            )

        err_dict = {}
        for k, v in self.qpu_config["readout_error"].items():
            if k in self.storage_area:
                err_dict[k] = v
        sq = sorted(err_dict.items(), key=lambda e: e[1])[: self.qbit_num]
        self.logical_to_storage = {
            a: b[0] for a, b in zip(range(self.qbit_num), sq)
        }
        self.qids = [int(q[0][1:]) for q in sq]
        self.initial_layout = dict(self.logical_to_storage)

    def execute_with_order(self):
        """遍历比特门，将逻辑量子比特映射到物理量子比特.

        Returns:
            从逻辑映射到物理量子比特的门列表
        """
        gates_on_qubit = {}
        measure = []
        for gate in self.gates:
            if len(gate.targets) != 1:
                raise MappingException(
                    f"invalid targets num: {len(gate.targets)}, "
                    f"Gate {gate.name} must have exactly one target"
                )
            gate.targets = [
                int(self.logical_to_storage[q][1:]) for q in gate.targets
            ]
            if gate.name == "measure":
                measure.append(gate)
                continue
            if gate.targets[0] not in gates_on_qubit:
                gates_on_qubit[gate.targets[0]] = []
            gates_on_qubit[gate.targets[0]].append(gate)

        gates = []
        for value in gates_on_qubit.values():
            gates += value
        gates += measure
        self.final_layout = dict(self.logical_to_storage)
        return gates, self.final_layout


class NARoute(ABC):
    """NARoute."""

    def __init__(self):
        self.qids = None
        self.logical_to_storage = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.operate_area = None
        self.storage_area = None
        self.qpu_config = None
        self.initial_layout = None
        self.final_layout = None

    def prepare_data(self, qbit_num, gates, qpu_configs):
        """配置qpu_config、gates、qbit_num，量子比特映射.

        Args:
            qbit_num: 比特数
            gates: 门列表
            qpu_configs: 拓扑
        """
        self.qpu_config = qpu_configs
        self.storage_area = self.qpu_config["storage_area"]
        self.operate_area = self.qpu_config["operate_area"]

        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config["coupler_map"].items():
            if (a not in self.operate_area) or (b not in self.operate_area):
                continue
            self.ag.add_edge(a, b)
        self.ag.shortest_length = dict(
            nx.shortest_path_length(
                self.ag,
                source=None,
                target=None,
                weight=None,
                method="dijkstra",
            )
        )

        self.gates = gates
        self.qbit_num = qbit_num
        if len(self.storage_area) < self.qbit_num:
            raise MappingException(
                f"not enough qubits, need {self.qbit_num}, "
                f"but only {len(self.operate_area)}."
            )

    def get_rx_dag(self):
        """Build a dependency graph (DAG) for IR using the rustworkx.

        Returns:
            dg (rx.PyDiGraph): The DAG object with node attributes
            measure_op (list): List of measurement operation gates
            node_indices (dict): Mapping dictionary from original gate indices
            to rustworkx node i
        """
        dg = rx.PyDiGraph()
        measure_op = []

        pre_nodes = defaultdict(lambda: -1)
        node_indices = {}

        for idx, gate in enumerate(self.gates):
            if gate.name in ("sync", "measure"):
                if gate.name == "measure":
                    measure_op.append(gate)
                continue

            if len(gate.targets) == 1:
                # single qubit gate
                qubit = gate.targets[0]
                if pre_nodes[qubit] == -1:
                    # gate first append on this qubit
                    node_idx = dg.add_node({
                        "gate": [gate],
                        "qubits": gate.targets,
                        "type": "single",
                        "original_idx": idx,
                    })
                    pre_nodes[qubit] = node_idx
                    node_indices[idx] = node_idx
                else:
                    prev_node_idx = pre_nodes[qubit]
                    prev_data = dg.get_node_data(prev_node_idx)
                    # If pre_node is a single-bit gate, then merge them.
                    if (
                        prev_data["type"] == "single"
                        and len(prev_data["qubits"]) == 1
                        and prev_data["qubits"][0] == qubit
                    ):
                        # Merge: Add the current gate to pre_node's gate list
                        prev_data["gate"].append(gate)
                    else:
                        # Create a new node and add edges
                        node_idx = dg.add_node({
                            "gate": [gate],
                            "qubits": gate.targets,
                            "type": "single",
                            "original_idx": idx,
                        })
                        dg.add_edge(prev_node_idx, node_idx, None)
                        pre_nodes[qubit] = node_idx
                        node_indices[idx] = node_idx
            else:
                # two-qubit gate
                node_idx = dg.add_node({
                    "gate": gate,
                    "qubits": gate.targets,
                    "type": "multi",
                    "original_idx": idx,
                })
                node_indices[idx] = node_idx

                for qid in gate.targets:
                    if pre_nodes[qid] != -1 and pre_nodes[qid] != node_idx:
                        dg.add_edge(pre_nodes[qid], node_idx, None)
                    pre_nodes[qid] = node_idx

        return dg, measure_op, node_indices

    def get_init_mapping(self):
        """比特初始映射及映射表构建.

        Description:
            完成DAG图的构建后，进行比特初始映射及映射表构建.

            dg：量子线路拓扑
            dg_opt：dg的深拷贝，用以将处理后的节点删除，并寻找新的可执行节点
            logical_to_storage(dict{logical_q: storage_p})：逻辑比特与存储区
            物理位置的映射（目前逻辑比特与存储区一一对应，方便维护）.
            logical_to_op(dict{logical_q: op_p | -1})：逻辑比特与操作区位置的
            映射（-1=不在操作区）.
            op_to_logical(dict{op_p: logical_q | -1})：操作区位置与逻辑比特的
            映射（-1=操作区位置为空）.
            op_occupied(set(op_p))：操作区已占用的位置集合.
            free_edges(set((op_p, op_p)))：两端都空闲的边集合.
            locked(set(op_p))：上锁的操作区位置（不可再移动）.
            res：最终映射后的指令集列表.
        """
        self.dg, self.measure, self.node_indices = self.get_rx_dag()

        self.pre_node = None
        self.dg_opt = self.dg.copy()
        err_dict = {}
        for k, v in self.qpu_config["readout_error"].items():
            if k in self.storage_area:
                err_dict[k] = v
        sq = sorted(err_dict.items(), key=lambda e: e[1])[: self.qbit_num]
        self.logical_to_storage = {
            a: b[0] for a, b in zip(range(self.qbit_num), sq)
        }
        self.logical_to_op = {a: -1 for a in range(self.qbit_num)}
        self.op_to_logical = {a: -1 for a in self.operate_area}
        self.op_occupied = set()
        self.free_edges = {tuple(sorted(e)) for e in self.ag.edges()}
        self.locked = set()
        self.res = []
        self.initial_layout = dict(self.logical_to_storage)

    def get_front_layer(self):
        """获取当前可执行的节点，节点可执行的条件是入度为0."""
        front_layer = set()
        for node_index in self.dg_opt.node_indices():
            if self.dg_opt.in_degree(node_index) == 0:
                front_layer.add(node_index)
        return front_layer

    def find_pos(self, dis):
        """在操作区中寻找可放置比特的位置，若不存在，则为-1.

        Args:
            dis (int): 与现有的比特间的距离至少为dis
        """
        disable_pos = set()
        for o in self.op_occupied:
            # 将操作区中已有比特以及与该比特距离小于dis的比特全部排除
            disable_pos.add(o)
            for nxt in self.ag.shortest_length[o]:
                if self.ag.shortest_length[o][nxt] < dis:
                    disable_pos.add(nxt)
        for o in self.operate_area:
            if o not in disable_pos:
                return o
        return -1

    def back(self, o):
        """将比特移回存储区，并更新映射表.

        Args:
            o: 操作区位置
        """
        q = self.op_to_logical[o]
        self.res.append(
            Move(targets=[q], arg_value=[o, self.logical_to_storage[q]])
        )
        self.logical_to_op[q] = -1
        self.op_to_logical[o] = -1
        self.op_occupied.remove(o)
        for nxt in self.ag.neighbors(o):
            if nxt not in self.op_occupied:
                self.free_edges.add(tuple(sorted((o, nxt))))

    def put(self, q, o):
        """将比特移到操作区，并更新映射表.

        Args:
            q: 需要操作的比特
            o: 操作区位置
        """
        self.res.append(
            Move(targets=[q], arg_value=[self.logical_to_storage[q], o])
        )  # f"put {q} {o}")
        self.logical_to_op[q] = o
        self.op_to_logical[o] = q
        self.op_occupied.add(o)
        for nxt in self.ag.neighbors(o):
            self.free_edges.discard(tuple(sorted((o, nxt))))

    def mov(self, o1, o2):
        """将比特从存取区的某一位置移到另一位置，并更新映射表.

        Args:
            o1: 操作区起始位置
            o2: 操作区目标位置
        """
        q = self.op_to_logical[o1]
        # f"mov {self.op_to_logical[o1]} {o2}")
        self.res.append(Move(targets=[q], arg_value=[o1, o2]))
        self.logical_to_op[q] = o2
        self.op_to_logical[o1] = -1
        self.op_to_logical[o2] = q
        self.op_occupied.remove(o1)
        self.op_occupied.add(o2)
        for nxt in self.ag.neighbors(o1):
            if nxt not in self.op_occupied:
                self.free_edges.add(tuple(sorted((o1, nxt))))
        for nxt in self.ag.neighbors(o2):
            self.free_edges.discard(tuple(sorted((o2, nxt))))

    def pre_back(self, nodes):
        """将操作区中不属于当前可执行门的比特移回存储区.

        Args:
            nodes (List): 当前可执行门列表
        """
        all_q = set()
        for node in nodes:
            qubits = self.dg.get_node_data(node)["qubits"]
            for q in qubits:
                all_q.add(q)
        ohas = self.op_occupied.copy()
        for o in ohas:
            if self.op_to_logical[o] not in all_q:
                self.back(o)

    def get_empty_neighbor(self, p):
        """获取操作区某一位置的相邻空位置.

        Args:
            p: 操作区位置
        """
        n = set(self.ag.neighbors(p))
        n -= n & self.op_occupied
        if len(n) > 0:
            return list(n)[0]
        return -1

    def get_unlocked_neighbor(self, p):
        """获取操作区某一位置的相邻非上锁位置.

        Args:
            p: 操作区位置
        """
        for nxt in self.ag.neighbors(p):
            if nxt not in self.locked:
                return nxt
        return -1

    def mov_to_neighbors(self, p1, p2):
        """将比特1和比特2移到相邻位置，前提为两个比特均已在操作区.

        Args:
            p1: 比特1当前所在的操作区位置
            p2: 比特2当前所在的操作区位置
        """
        # 如果直接相邻，则无需操作，直接返回
        if p2 in self.ag.neighbors(p1):
            return True
        # 找操作区p1的相邻空位置，若存在则将比特2移到该位置
        d = self.get_empty_neighbor(p1)
        if d != -1:
            self.mov(p2, d)
            self.locked.add(p1)
            self.locked.add(d)
            return True
        # 找操作区p2的相邻空位置，若存在则将比特1移到该位置
        d = self.get_empty_neighbor(p2)
        if d != -1:
            self.mov(p1, d)
            self.locked.add(p2)
            self.locked.add(d)
            return True
        # 找操作区p1的相邻非上锁位置，
        # 若存在则将比特2放到该位置，原位置的比特移回存储区
        d = self.get_unlocked_neighbor(p1)
        if d != -1:
            self.back(d)
            self.mov(p2, d)
            self.locked.add(p1)
            self.locked.add(d)
            return True
        # 找操作区p2的相邻非上锁位置，
        # 若存在则将比特1交换到该位置，原位置的比特移回存储区
        d = self.get_unlocked_neighbor(p2)
        if d != -1:
            self.back(d)
            self.mov(p2, d)
            self.locked.add(p2)
            self.locked.add(d)
            return True
        return False

    def put_to_neighbors1(self, p1, q):
        """将q放到p1的相邻位置，前提为q在存储区.

        Args:
            p1: 比特1当前所在的操作区位置
            q: 需要移动的比特
        """
        # 找操作区p1的相邻空位置，若存在则将q移到该位置
        d = self.get_empty_neighbor(p1)
        if d != -1:
            self.put(q, d)
            self.locked.add(p1)
            self.locked.add(d)
            return True
        return False

    def put_to_neighbors2(self, q1, q2):
        """将比特q1, q2放到相邻位置,前提为q1, q2均在存储区.

        Args:
            q1: 比特1
            q2: 比特2
        """
        if not self.free_edges:
            return False
        a, b = next(iter(self.free_edges))
        self.free_edges.discard((a, b))
        self.put(q1, a)
        self.put(q2, b)
        self.locked.add(a)
        self.locked.add(b)
        return True

    def execute_multi_nodes(self, nodes):
        """执行两比特门.

        Args:
            nodes (List): 所有当前可执行的两比特门对应的节点
        """
        # 重置锁定比特，通过mov_multi_nodes先将
        # 可同时执行的两比特门对应的比特位置调整好（放到相邻的位置).
        self.locked = set()
        remain = self.mov_multi_nodes(nodes)
        for node in remain:
            # 不能执行的两比特门，对应比特需要放回存储区
            for q in self.dg.get_node_data(node)["qubits"]:
                if self.logical_to_op[q] != -1:
                    self.back(self.logical_to_op[q])
        for node in nodes:
            if node in remain:
                continue
            self.pre_node = node
            self.res.append(self.dg.get_node_data(node)["gate"])
            self.dg_opt.remove_node(node)

    def mov_multi_nodes(self, nodes):
        """两比特门执行前，将比特先放置在操作区合适的位置.

        Args:
            nodes (List): 所有当前可执行的两比特门对应的节点
        """
        # 先将其余的量子比特移回操作区（单比特可操作区）
        self.pre_back(nodes)
        remain = []
        for node in nodes:
            # 每个两比特门判断当前两个比特的位置是否符合要求
            qubits = self.dg.get_node_data(node)["qubits"]
            p1, p2 = (
                self.logical_to_op[qubits[0]],
                self.logical_to_op[qubits[1]],
            )
            if p1 != -1 and p2 != -1:
                # 均在操作区
                if not self.mov_to_neighbors(p1, p2):
                    remain.append(node)
            elif p1 != -1 and p2 == -1:
                # 一个在操作区，一个在存储区
                if not self.put_to_neighbors1(p1, qubits[1]):
                    remain.append(node)
            elif p1 == -1 and p2 != -1:
                if not self.put_to_neighbors1(p2, qubits[0]):
                    remain.append(node)
            else:
                # 都在存储区
                if not self.put_to_neighbors2(qubits[0], qubits[1]):
                    remain.append(node)
        return remain

    def execute_single_node(self, node):
        """执行单比特门.

        Args:
            node: 当前可执行的单比特门对应的节点
        """
        # 无论原子在哪一个区域直接执行

        self.res += self.dg.get_node_data(node)["gate"]
        self.dg_opt.remove_node(node)

    def overlap(self, nd1, nd2):
        """判断两个单比特节点包含的门列表是否满足nd2为nd1的后缀.

        Description:
            若nd2为nd1的后缀, 则在执行nd1的所有单比特门时, 可在适当位置将nd2的
            比特放入操作区，后续单比特门可一起执行, 节省操作步骤.
            如nd1比特为Q1, 包含[H, X], nd2比特为Q2包含[X].
            一般执行顺序为: PUT Q1; H Q1; X Q1; BACK Q1; PUT Q2; X Q2.
            优化顺序: PUT Q1; H Q1; PUT Q2; X Q1 Q2.

        Args:
            nd1: 节点1
            nd2: 节点2
        """
        gt1 = self.dg.get_node_data(nd1)["gate"]
        gt2 = self.dg.get_node_data(nd2)["gate"]
        if len(gt1) < len(gt2):
            return False
        l = 0
        for i in range(len(gt1) - len(gt2), len(gt1)):
            if gt1[i].name != gt2[l].name:
                return False
            l += 1
        return True

    def add_put(self, res, opt):
        """将overlap中的put操作放入对应的位置.

        Args:
            res: 当前的指令集列表
            opt: put操作
        """
        q = opt.targets[0]
        i = len(res) - 1
        while i >= 0:
            # print("add put: ", res[i])
            if not isinstance(res[i], Move):
                break
            t = res[i]

            if t.operation_type == -2 and t.targets[0] == q:
                # 若有直接相邻的back操作，且作用在同一比特上，可消除
                op = t.arg_value[0]
                p = self.logical_to_op[q]
                self.op_occupied.remove(p)
                self.op_occupied.add(op)
                self.op_to_logical[p] = -1
                self.op_to_logical[op] = q
                self.logical_to_op[q] = op
                return res[:i] + res[i + 1 :]
            i -= 1
        res.append(opt)
        return res

    def adjust_pos(self, pos, posq):
        """调整put操作的位置，调用add_put，放入合适的位置.

        Args:
            pos: 所有的put操作
            posq: 操作对应的比特
        """
        if pos == []:
            return
        n = len(pos)
        res = self.res[-n:]
        self.res = self.res[:-n]
        new_res = []
        pre = 0
        targets = self.res[-1].targets.copy()

        for p, r, q in sorted(zip(pos, res, posq)):
            if p == pre:
                new_res = self.add_put(new_res, r)
                targets.append(q)
            else:
                if pre > 0:
                    for gate in self.res[pre:p]:
                        if not isinstance(gate, Move):
                            gate.targets = targets.copy()
                new_res += self.res[pre:p]
                # new_res.append(r)
                new_res = self.add_put(new_res, r)
                targets.append(q)
            pre = p

        for gate in self.res[pre:]:
            if not isinstance(gate, Move):
                gate.targets = targets.copy()

        new_res += self.res[pre:]
        self.res = new_res

    def execute_single_node_opt(self):
        """执行单比特门，通过overlap进行优化."""
        pos = []
        posq = []
        front_layer = self.front_layer.copy()
        for node in front_layer:
            if len(self.dg.get_node_data(node)["qubits"]) == 1:
                if self.pre_node is not None and self.overlap(
                    self.pre_node, node
                ):
                    q = self.dg.get_node_data(node)["qubits"][0]
                    p = self.find_pos(1)
                    if p != -1:
                        # 如果能找到空的位置，则移到操作区一起执行
                        self.put(q, p)
                        pos.append(
                            -1 * len(self.dg.get_node_data(node)["gate"])
                        )
                        posq.append(q)
                        self.dg_opt.remove_node(node)
                        self.front_layer.remove(node)
        self.adjust_pos(pos, posq)

    def get_max_common(self):
        """从当前可执行节点中找可执行的节点."""
        multi_qubits = set()
        multi_nodes = []
        comm = 0
        execute_node = None
        for node in self.front_layer:
            qubits = self.dg.get_node_data(node)["qubits"]
            # 如果为单比特门，优先选择比特已在操作区，且可执行的门的列表最长
            if len(self.dg.get_node_data(node)["qubits"]) == 1:
                if comm > 1:
                    continue
                if qubits[0] not in self.op_occupied and comm == 1:
                    continue

                if qubits[0] in self.op_occupied:
                    comm = 1

                # pylint: disable=invalid-sequence-index
                if execute_node is not None and len(
                    self.dg.get_node_data(execute_node)["qubits"]
                ) >= len(self.dg.get_node_data(node)["qubits"]):
                    continue
                execute_node = node
            else:
                # 如果为两比特门，添加到可执行列表中
                # （两比特门默认均为CX，可一起执行）
                multi_qubits.update(set(qubits))
                comm = max(comm, len(multi_qubits & self.op_occupied))
                multi_nodes.append(node)
        if comm <= 1:
            if execute_node is not None:
                return 1, execute_node
        return 2, multi_nodes

    def execute_with_order(self):
        """按顺序执行门，不进行优化."""
        self.get_init_mapping()

        for node in self.dg.node_indices():
            data = self.dg.get_node_data(node)
            if len(data["qubits"]) == 1:
                self.execute_single_node(node)
            else:
                self.execute_multi_nodes([node])

        self.res += self.measure

        # 遍历比特门，将逻辑量子比特映射到物理量子比特.
        operator_list = self.logical_to_storage
        for gate in self.res:
            if gate.name == "move":
                pid = gate.arg_value[1]
                operator_list[gate.targets[0]] = pid
                gate.arg_value = [
                    int(gate.arg_value[0][1:]),
                    int(gate.arg_value[1][1:]),
                ]
            else:
                gate.targets = [
                    int(operator_list[q][1:]) for q in gate.targets
                ]

        self.final_layout = dict(self.logical_to_storage)
        return self.res, self.final_layout

    def execute_with_opt(self):
        """按优化策略执行门，利用overlap和并行执行."""
        self.get_init_mapping()
        self.pre_node = None

        while self.dg_opt.num_nodes() > 0:
            self.front_layer = self.get_front_layer()
            if not self.front_layer:
                raise MappingException("cycle detected in DAG")
            comm, nodes = self.get_max_common()
            if comm == 1:
                self.execute_single_node_opt()
                self.execute_single_node(nodes)
                self.pre_node = nodes
            else:
                self.execute_multi_nodes(nodes)

        self.res += self.measure

        # 遍历比特门，将逻辑量子比特映射到物理量子比特.
        operator_list = self.logical_to_storage
        for gate in self.res:
            if gate.name == "move":
                pid = gate.arg_value[1]
                operator_list[gate.targets[0]] = pid
                gate.arg_value = [
                    int(gate.arg_value[0][1:]),
                    int(gate.arg_value[1][1:]),
                ]
            else:
                gate.targets = [
                    int(operator_list[q][1:]) for q in gate.targets
                ]

        self.final_layout = dict(self.logical_to_storage)
        return self.res, self.final_layout


class NAMultiRoute(ABC):
    """中性原子多路由（单比特任意位置、两比特固定操作区、防串扰驱散）.

    适配行列坐标网格配置（如 hanyuan1_100_new.toml），operate_area 支持
    区间字典 {row:[r1,r2], col:[c1,c2]}、整数、坐标列表三种格式，物理位点
    以网格序号 p = row * column + col 表示.
    """

    def __init__(self):
        self.qids = None
        self.logical_to_storage = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.pg = None
        self.operate_area = None
        self.all_sites = None
        self.qpu_config = None
        self.initial_layout = None
        self.rows = None
        self.cols = None

    def prepare_data(self, qbit_num, gates, qpu_configs):
        """配置qpu_config、gates、qbit_num，构建操作区拓扑与物理网格图.

        Args:
            qbit_num: 比特数
            gates: 门列表
            qpu_configs: 拓扑
        """
        self.qpu_config = qpu_configs
        self.rows = self.qpu_config.get("row")
        self.cols = self.qpu_config.get("column")

        self.operate_area = self.get_operate_area(
            self.qpu_config["operate_area"]
        )
        self.all_sites = self.operate_area

        self.ag = rx.PyGraph(multigraph=False)
        self.ag_val_to_idx = {}
        ag_edges = []
        for k, (a, b) in self.qpu_config["coupler_map"].items():
            if (a in self.operate_area) and (b in self.operate_area):
                if a not in self.ag_val_to_idx:
                    self.ag_val_to_idx[a] = self.ag.add_node(a)
                if b not in self.ag_val_to_idx:
                    self.ag_val_to_idx[b] = self.ag.add_node(b)
                ag_edges.append((self.ag_val_to_idx[a], self.ag_val_to_idx[b]))
        for ua, ub in ag_edges:
            self.ag.add_edge(ua, ub, None)

        self.pg = rx.PyGraph(multigraph=False)
        self.pg.add_nodes_from(list(range(self.rows * self.cols)))
        pg_edges = []
        for r in range(self.rows):
            for c in range(self.cols):
                p = r * self.cols + c
                if c < self.cols - 1:
                    pg_edges.append((p, p + 1))
                if r < self.rows - 1:
                    pg_edges.append((p, p + self.cols))
        self.pg.add_edges_from_no_data(pg_edges)

        self.gates = gates
        self.qbit_num = qbit_num

    def get_operate_area(self, operate_area):
        """解析operate_area，支持整数、坐标列表、区间字典三种格式.

        Args:
            operate_area: 操作区配置列表
        """
        ope = []
        for atom in operate_area:
            if isinstance(atom, int):
                if 0 <= atom < self.rows * self.cols:
                    ope.append(atom)
            elif isinstance(atom, list):
                if (
                    len(atom) == 2
                    and 0 <= atom[0] < self.rows
                    and 0 <= atom[1] < self.cols
                ):
                    ope.append(atom[0] * self.cols + atom[1])
            elif isinstance(atom, dict):
                r, c = atom.get("row", []), atom.get("col", [])
                if len(r) == 2 and len(c) == 2:
                    for i in range(r[0], r[1]):
                        for j in range(c[0], c[1]):
                            ope.append(i * self.cols + j)
        return ope

    def get_dg(self, gates, pos_num):
        """从门列表构建依赖图(DAG).

        Args:
            gates: 门列表
            pos_num: 操作区容量
        """
        dg = rx.PyDiGraph()
        measure = []
        pre_nodes = defaultdict(lambda: -1)

        for idx, gate in enumerate(gates):
            if gate.name in ("sync", "measure"):
                if gate.name == "measure":
                    measure.append(gate)
                continue

            if len(gate.targets) > pos_num:
                raise MappingException(
                    f"operate_area only holds {pos_num} qubits, "
                    f"gate {gate.name} needs {len(gate.targets)}"
                )

            if len(gate.targets) == 1:
                qubit = gate.targets[0]
                if pre_nodes[qubit] == -1:
                    node_idx = dg.add_node({
                        "gate": [gate],
                        "qubits": gate.targets,
                        "type": "single",
                    })
                    pre_nodes[qubit] = node_idx
                else:
                    prev_node_idx = pre_nodes[qubit]
                    prev_data = dg.get_node_data(prev_node_idx)
                    if prev_data["type"] == "single":
                        prev_data["gate"].append(gate)
                    else:
                        node_idx = dg.add_node({
                            "gate": [gate],
                            "qubits": gate.targets,
                            "type": "single",
                        })
                        dg.add_edge(prev_node_idx, node_idx, None)
                        pre_nodes[qubit] = node_idx
            else:
                node_idx = dg.add_node({
                    "gate": gate,
                    "qubits": gate.targets,
                    "type": "multi",
                })
                for qid in gate.targets:
                    if pre_nodes[qid] != -1:
                        dg.add_edge(pre_nodes[qid], node_idx, None)
                    pre_nodes[qid] = node_idx
        return dg, measure

    def get_init_mapping(self):
        """比特初始映射，首波两比特门图同构匹配，剩余比特按读取误差兜底."""
        self.dg, self.measure = self.get_dg(self.gates, len(self.operate_area))
        self.dg_opt = deepcopy(self.dg)
        self.res = []

        first_2q_layer = set()
        for node in self.dg_opt.node_indices():
            if self.dg_opt.get_node_data(node)["type"] == "multi":
                ancestors = rx.ancestors(self.dg_opt, node)
                has_multi_ancestor = any(
                    self.dg_opt.get_node_data(anc)["type"] == "multi"
                    for anc in ancestors
                )
                if not has_multi_ancestor:
                    first_2q_layer.add(node)

        initial_logical_graph = rx.PyGraph(multigraph=False)
        ilg_val_to_idx = {}
        for node in first_2q_layer:
            qubits = self.dg_opt.get_node_data(node)["qubits"]
            for q in qubits:
                if q not in ilg_val_to_idx:
                    ilg_val_to_idx[q] = initial_logical_graph.add_node(q)
            initial_logical_graph.add_edge(
                ilg_val_to_idx[qubits[0]], ilg_val_to_idx[qubits[1]], None
            )

        best_mapping = {}
        if initial_logical_graph.num_edges() > 0:
            if rx.graph_is_subgraph_isomorphic(self.ag, initial_logical_graph):
                vf2 = rx.graph_vf2_mapping(
                    self.ag, initial_logical_graph, subgraph=True
                )
                match = next(vf2)
                for phy_idx, log_idx in match.items():
                    p = self.ag.get_node_data(phy_idx)
                    q = initial_logical_graph.get_node_data(log_idx)
                    best_mapping[q] = p

        err_dict = self.qpu_config.get("readout_error", {})
        site_errors = [
            (site, err_dict.get(str(site), 5.0)) for site in self.all_sites
        ]
        sq = sorted(site_errors, key=lambda e: e[1])

        self.q_to_p = defaultdict(lambda: -1)
        self.p_to_q = defaultdict(lambda: -1)

        for q, p in best_mapping.items():
            self.q_to_p[q] = p
            self.p_to_q[p] = q

        unmapped_qs = [q for q in range(self.qbit_num) if q not in self.q_to_p]
        avail_ps = [p for p, err in sq if self.p_to_q[p] == -1]

        if len(unmapped_qs) > len(avail_ps):
            raise MappingException(
                "not enough sites to place all logical qubits"
            )

        for q, p in zip(unmapped_qs, avail_ps):
            self.q_to_p[q] = p
            self.p_to_q[p] = q

        self.initial_layout = {q: p for q, p in self.q_to_p.items() if p != -1}

    def get_front_layer(self):
        """获取当前可执行的节点（入度为0）."""
        return {
            node
            for node in self.dg_opt.node_indices()
            if self.dg_opt.in_degree(node) == 0
        }

    def get_mapping(self):
        """获取逻辑比特到物理位置的映射表."""
        return {q: p for q, p in self.q_to_p.items()}

    def is_site_safe(self, site, exclude_sites=None):
        """判断一个位置是否安全（无寄生耦合风险）."""
        exclude_sites = exclude_sites or []
        site_idx = self.ag_val_to_idx.get(site)
        if site_idx is None:
            return True
        for neighbor_idx in self.ag.neighbors(site_idx):
            neighbor = self.ag.get_node_data(neighbor_idx)
            occ = self.p_to_q.get(neighbor, -1)
            if occ != -1 and neighbor not in exclude_sites:
                return False
        return True

    def find_empty_site(self, curr_p, exclude_sites=None):
        """BFS寻找最近的安全空位，返回路径或-1."""
        exclude_sites = exclude_sites or []
        queue = [curr_p]
        pre = defaultdict(lambda: -1)
        visited = {curr_p}

        def get_path(curr):
            path = []
            while curr != -1:
                path.append(curr)
                curr = pre[curr]
            return path[::-1]

        while queue:
            curr = queue.pop(0)
            if (
                curr != curr_p
                and self.p_to_q[curr] == -1
                and curr not in exclude_sites
            ):
                if self.is_site_safe(curr, exclude_sites):
                    return get_path(curr)
            for neighbor in self.pg.neighbors(curr):
                if neighbor not in visited:
                    occ = self.p_to_q.get(neighbor, -1)
                    if occ != -1 and neighbor not in exclude_sites:
                        continue
                    visited.add(neighbor)
                    queue.append(neighbor)
                    pre[neighbor] = curr
        return -1

    def get_empty_path(self, start_p, end_p, exclude_sites=None):
        """BFS搜索：寻找从start_p到end_p的物理相邻空位路径."""
        if start_p == end_p:
            return []
        exclude_sites = exclude_sites or []
        queue = [[start_p]]
        visited = {start_p}
        while queue:
            path = queue.pop(0)
            curr = path[-1]
            if curr == end_p:
                return path
            for neighbor in self.pg.neighbors(curr):
                if neighbor not in visited:
                    if neighbor == end_p or (
                        self.p_to_q.get(neighbor, -1) == -1
                        and neighbor not in exclude_sites
                    ):
                        visited.add(neighbor)
                        queue.append(path + [neighbor])
        return None

    def _do_move(self, q, path):
        """执行底层Move指令并更新映射表."""
        frm, to = path[0], path[-1]
        self.res.append(Move(targets=[frm], arg_value=path))
        self.p_to_q[frm] = -1
        self.p_to_q[to] = q
        self.q_to_p[q] = to

    def move_qubit(self, q, target_p):
        """将逻辑比特移动到目标位置，包含多步寻路与智能避让机制."""
        curr_p = self.q_to_p[q]
        if curr_p == target_p:
            return

        if self.p_to_q[target_p] != -1:
            occupying_q = self.p_to_q[target_p]
            temp_q = self.p_to_q[target_p]
            self.p_to_q[target_p] = -1
            incoming_path = self.get_empty_path(curr_p, target_p)
            self.p_to_q[target_p] = temp_q
            exclude_for_eviction = [curr_p, target_p]
            if incoming_path:
                exclude_for_eviction.extend(incoming_path[:-1])
            empty_p = self.find_empty_site(
                target_p, exclude_sites=exclude_for_eviction
            )
            if empty_p == -1:
                raise MappingException(
                    f"no empty site to evict qubit {occupying_q}"
                )
            self._do_move(occupying_q, empty_p)

        final_path = self.get_empty_path(curr_p, target_p)
        if final_path:
            self._do_move(q, final_path)
        else:
            raise MappingException(
                f"deadlock: cannot move qubit {q} from {curr_p} to {target_p}"
            )

    def execute_single_nodes(self, nodes):
        """执行单比特门：In-place执行，无需移动."""
        for node in nodes:
            gates = self.dg.get_node_data(node)["gate"]
            for gate in gates:
                gate.targets = [self.q_to_p[q] for q in gate.targets]
                self.res.append(gate)
            self.dg_opt.remove_node(node)

    def find_best_operate_edge(self, q1, q2, exclude_nodes=None):
        """寻找代价最小的操作边，需避开已被占用的节点."""
        exclude_nodes = exclude_nodes or set()
        best_edge = None
        min_cost = float("inf")
        for edge in self.ag.edge_list():
            p1 = self.ag.get_node_data(edge[0])
            p2 = self.ag.get_node_data(edge[1])
            edge_vals = (p1, p2)
            if p1 in exclude_nodes or p2 in exclude_nodes:
                continue
            evictions = 0
            for p in edge_vals:
                occ = self.p_to_q[p]
                if occ != -1 and occ != q1 and occ != q2:
                    evictions += 1
            arrivals = 0
            if self.q_to_p[q1] not in edge_vals:
                arrivals += 1
            if self.q_to_p[q2] not in edge_vals:
                arrivals += 1
            cost = evictions + arrivals * 1.5
            if cost < min_cost:
                min_cost = cost
                best_edge = edge_vals
                if cost == 0:
                    break
        return best_edge

    def disperse_inactive_qubits(self, active_edges):
        """发射全局脉冲前，驱散非参与比特."""
        locked_sites = set()
        for p1, p2 in active_edges:
            locked_sites.update([p1, p2])
        inactive_qs = [
            q
            for q in range(self.qbit_num)
            if self.q_to_p[q] not in locked_sites
        ]
        for q in inactive_qs:
            curr_p = self.q_to_p[q]
            if not self.is_site_safe(curr_p):
                safe_p = self.find_empty_site(curr_p, exclude_sites=[curr_p])
                if safe_p == -1:
                    raise MappingException(
                        f"no empty site to disperse qubit {q}"
                    )
                self._do_move(q, safe_p)

    def execute_multi_nodes(self, nodes):
        """执行两比特门（支持并行），并保证全局脉冲的安全."""
        active_edges = []
        active_nodes = set()
        for node in nodes:
            qubits = self.dg.get_node_data(node)["qubits"]
            q1, q2 = qubits[0], qubits[1]
            p1, p2 = self.q_to_p[q1], self.q_to_p[q2]
            p1_idx = self.ag_val_to_idx.get(p1)
            p2_idx = self.ag_val_to_idx.get(p2)
            if (
                p1 in self.operate_area
                and p2 in self.operate_area
                and p1_idx is not None
                and p2_idx is not None
                and self.ag.has_edge(p1_idx, p2_idx)
            ):
                active_edges.append((p1, p2))
                active_nodes.update([p1, p2])
            else:
                target_edge = self.find_best_operate_edge(
                    q1, q2, exclude_nodes=active_nodes
                )
                if not target_edge:
                    raise MappingException(
                        f"no operate edge for qubits {q1}, {q2}"
                    )
                tp1, tp2 = target_edge
                p1, p2 = self.q_to_p[q1], self.q_to_p[q2]
                if p1 == tp2 or p2 == tp1:
                    tp1, tp2 = tp2, tp1
                self.move_qubit(q1, tp1)
                self.move_qubit(q2, tp2)
                active_edges.append((tp1, tp2))
                active_nodes.update([tp1, tp2])
        self.disperse_inactive_qubits(active_edges)
        self.res.append(
            BaseOperation(
                "cz",
                targets=[],
                operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
            )
        )
        for node in nodes:
            self.dg_opt.remove_node(node)

    def execute_with_order(self):
        """按拓扑序执行门，单比特门原地执行，两比特门移动到操作边后全局脉冲.

        Returns:
            从逻辑映射到物理量子比特的门列表
        """
        self.get_init_mapping()
        while self.dg_opt.num_nodes() > 0:
            front = self.get_front_layer()
            if not front:
                raise MappingException("cycle detected in DAG")
            single_nodes = [
                n
                for n in front
                if self.dg.get_node_data(n)["type"] == "single"
            ]
            if single_nodes:
                self.execute_single_nodes(single_nodes)
            else:
                multi_nodes = [
                    n
                    for n in front
                    if self.dg.get_node_data(n)["type"] != "single"
                ]
                self.execute_multi_nodes(multi_nodes)

        for gate in self.measure:
            gate.targets = [self.q_to_p[q] for q in gate.targets]
            self.res.append(gate)

        self.final_mapping = self.get_mapping()
        return self.res, self.final_mapping
