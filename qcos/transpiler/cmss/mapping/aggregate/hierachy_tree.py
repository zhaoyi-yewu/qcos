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

import networkx as nx


class Node:
    def __init__(self, qubits, left=None, right=None, ignore=False) -> None:
        """搜索树节点，也称作社区，每个节点包含一组量子比特.

        Args:
            qubits: 节点包含的量子比特
            left: 左子节点. Defaults to None.
            right: 右子节点. Defaults to None.
            ignore: 是否忽略该节点. Defaults to False.
        """
        self.qubits = qubits
        self.left = left
        self.right = right
        self.ignore = ignore
        self.parent = None
        self.pos = -1


class HierarchyTree:
    """基于CDAP构建搜索树.

    Args:
        qpu_config: 硬件配置，包含硬件拓扑信息
        weight: 错误率所占权重，越高表示越看中门和测量的保真度，
                0表示只关心耦合情况
        Defaults to 1.0.
    """

    def __init__(self, qpu_config, weight=1.0) -> None:
        ag = nx.Graph()
        for k, e in qpu_config["coupler_map"].items():
            ag.add_edge(
                e[0], e[1], weight=1.0 - qpu_config["coupler_error"][k] / 100
            )

        for q in ag.nodes():
            ag.nodes[q]["weight"] = 1.0
            if q in qpu_config["readout_error"]:
                ag.nodes[q]["weight"] = (
                    1.0 - qpu_config["readout_error"][q] / 100
                )

        self.graph = ag
        self.edge_count = len(ag.edges())
        self.weight = weight
        self.root = None
        self.all_qubits = qpu_config["qubits"]

    def construct(self):
        """构建层次树，每次合并两个节点，直到最终只剩下一个节点."""
        nodes = self.origin_node()
        while len(nodes) != 1:
            i, j = self.calc_merge_gain(nodes)
            node = Node(
                nodes[i].qubits + nodes[j].qubits,
                left=nodes[i],
                right=nodes[j],
            )
            node.left.parent = node
            node.left.pos = 0
            node.right.parent = node
            node.right.pos = 1
            new_nodes = [node]
            for x in range(len(nodes)):
                if x in (i, j):
                    continue
                new_nodes.append(nodes[x])
            nodes = new_nodes
        self.root = nodes[0]

    def origin_node(self):
        """初始叶节点，每个比特/位置为一个叶节点.

        Returns: 节点
        """
        nodes = []
        for node in self.graph.nodes():
            nodes.append(Node([node]))
        return nodes

    def visit(self, node):
        if node is None:
            return
        self.visit(node.left)
        self.visit(node.right)

    def get_all_leaf(self):
        """dfs获取所有的叶节点.

        Returns: 所有的叶节点
        """
        leafs = []

        def dfs(node):
            if node is None:
                return
            if node.left is None and node.right is None:
                leafs.append(node)
            else:
                dfs(node.left)
                dfs(node.right)

        dfs(self.root)
        return leafs

    def average_fidelity(self, node):
        """当前节点的平均保真度，主要为节点包含比特的测量保真度和两比特门保真度.

        Args:
            node: 节点

        Returns: 当前节点的平均保真度
        """
        n = len(node.qubits)
        read_f = sum(self.graph.nodes[q]["weight"] for q in node.qubits) / n
        cx_f, en = 0.0, 0
        for i in range(n):
            for j in range(i):
                if self.graph.has_edge(node.qubits[i], node.qubits[j]):
                    cx_f += self.graph.edges[(node.qubits[i], node.qubits[j])][
                        "weight"
                    ]
                    en += 1
        if en > 0:
            cx_f /= en
        fidelity = read_f * cx_f
        return fidelity

    def calc_modularity(self, nodes):
        """衡量当前划分的指标.

        Args:
            nodes: 当前划分下所有的节点

        Returns: 模块度
        """
        modularity = 0
        for node in nodes:
            if node.ignore is True:
                continue
            eii, ai = 0, 0
            for i in range(len(node.qubits)):
                for j in range(i):
                    if self.graph.has_edge(node.qubits[i], node.qubits[j]):
                        eii += 1
                ai += self.graph.degree(node.qubits[i])
            ai -= eii
            modularity += eii / self.edge_count - (ai / self.edge_count) ** 2
        return modularity

    def calc_eigenvector(self, node_a, node_b):
        """计算两个节点间的平均两比特门保真度，以及平均测量保真度.

        Args:
            node_a: 节点a
            node_b: 节点b

        Returns: 两个节点间的平均两比特门保真度，以及平均测量保真度
        """
        e = 0
        ecnt = 0
        v = 0
        qubits = set()
        for qa in node_a.qubits:
            for qb in node_b.qubits:
                if self.graph.has_edge(qa, qb):
                    e += self.graph.edges[(qa, qb)]["weight"]
                    ecnt += 1
                    qubits.add(qa)
                    qubits.add(qb)
        for q in qubits:
            v += self.graph.nodes[q]["weight"]
        if e == 0 or v == 0:
            return 0
        eigenvector = (e / ecnt) * (v / len(qubits)) * self.weight
        return eigenvector

    def calc_merge_gain(self, nodes):
        """奖励函数，每次找奖励函数值最大的合并方案.

        F = Qmerge - Qori + w * EV.

        Args:
            nodes: 当前划分下所有的节点

        Returns: 奖励函数值最大的合并方案
        """
        q_origin = self.calc_modularity(nodes)
        n = len(nodes)
        max_f = -1e8
        comb = (-1, -1)
        for i in range(n):
            node_a = nodes[i]
            node_a.ignore = True
            for j in range(i):
                node_b = nodes[j]
                node_b.ignore = True
                new_node = Node(node_a.qubits + node_b.qubits)
                nodes.append(new_node)
                q_merged = self.calc_modularity(nodes)
                f = q_merged - q_origin + self.calc_eigenvector(node_a, node_b)
                if f > max_f:
                    max_f = f
                    comb = (i, j)
                nodes.pop(-1)
                node_b.ignore = False
            node_a.ignore = False
        return comb


def remove(node):
    ignore_node(node)
    removed_qubits = set(node.qubits)
    if node.parent:
        if node.pos == 0:
            node.parent.left = None
        else:
            node.parent.right = None
        while node.parent:
            qubits = set(node.parent.qubits)
            node.parent.qubits = list(qubits ^ removed_qubits)
            node = node.parent


def ignore_node(node):
    if node is None:
        return
    node.ignore = True
    ignore_node(node.left)
    ignore_node(node.right)


def get_block(ht, qnum):
    leafs = ht.get_all_leaf()
    candidates = []
    seen = set()
    for leaf in leafs:
        while leaf is not None:
            if not leaf.ignore and len(leaf.qubits) >= qnum:
                # 使用id来确保每个节点只添加一次
                node_id = id(leaf)
                if node_id not in seen:
                    seen.add(node_id)
                    candidates.append(leaf)
                break
            leaf = leaf.parent
    if not candidates:
        return None

    # 按确定性规则排序：
    # 1. 保真度降序（负号用于降序）
    # 2. 节点/社区大小升序（优先选择更小的节点，避免资源浪费）
    # 3. qubits排序（确定性排序）
    candidates.sort(
        key=lambda node: (
            -ht.average_fidelity(node),
            len(node.qubits),
            tuple(sorted(node.qubits)),
        )
    )

    best_node = candidates[0]
    remove(best_node)
    return best_node.qubits.copy()
