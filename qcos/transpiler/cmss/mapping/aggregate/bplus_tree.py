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

from loguru import logger


class BPlusTreeNode:
    """B+树节点基类."""

    def __init__(self, is_leaf: bool = False):
        self.is_leaf = is_leaf
        self.keys: list[int] = []
        self.parent: BPlusTreeNode | None = None


class BPlusTreeInternalNode(BPlusTreeNode):
    """B+树内部节点."""

    def __init__(self):
        super().__init__(is_leaf=False)
        self.children: list[BPlusTreeNode] = []  # 子节点列表

    def insert_key_child(self, key: int, child: BPlusTreeNode):
        """插入键值对和对应的子节点.

        Args:
            key: 键值
            child: 子节点
        """
        # 找到插入位置
        insert_pos = 0
        while insert_pos < len(self.keys) and self.keys[insert_pos] < key:
            insert_pos += 1

        # 插入键值
        self.keys.insert(insert_pos, key)
        # 插入子节点（子节点数量比键值多1）
        self.children.insert(insert_pos + 1, child)
        child.parent = self

    def split(self) -> tuple["BPlusTreeInternalNode", int]:
        """分裂内部节点.

        Returns:
            Tuple[BPlusTreeInternalNode, int]: (新节点, 提升的键值)
        """
        mid = len(self.keys) // 2
        promote_key = self.keys[mid]

        # 创建新节点
        new_node = BPlusTreeInternalNode()
        new_node.keys = self.keys[mid + 1 :]
        new_node.children = self.children[mid + 1 :]

        # 更新新节点子节点的父指针
        for child in new_node.children:
            child.parent = new_node

        # 更新当前节点
        self.keys = self.keys[:mid]
        self.children = self.children[: mid + 1]

        return new_node, promote_key


class BPlusTreeLeafNode(BPlusTreeNode):
    """B+树叶子节点."""

    def __init__(self):
        super().__init__(is_leaf=True)
        self.values: list[list[int]] = []  # 存储候选区域数据
        self.next_leaf: BPlusTreeLeafNode | None = (
            None  # 指向下一个叶子节点的指针
        )

    def insert_key_value(self, key: int, value: list[int]):
        """插入键值对.

        Args:
            key: 键值（量子比特数量）
            value: 候选区域（量子比特列表）
        """
        # 找到插入位置
        insert_pos = 0
        while insert_pos < len(self.keys) and self.keys[insert_pos] < key:
            insert_pos += 1

        # 插入键值和对应的候选区域
        self.keys.insert(insert_pos, key)
        self.values.insert(insert_pos, value)

    def split(self) -> tuple["BPlusTreeLeafNode", int]:
        """分裂叶子节点.

        Returns:
            Tuple[BPlusTreeLeafNode, int]: (新节点, 提升的键值)
        """
        mid = len(self.keys) // 2
        promote_key = self.keys[mid]

        # 创建新节点
        new_node = BPlusTreeLeafNode()
        new_node.keys = self.keys[mid:]
        new_node.values = self.values[mid:]

        # 更新当前节点
        self.keys = self.keys[:mid]
        self.values = self.values[:mid]

        # 更新叶子节点链表
        new_node.next_leaf = self.next_leaf
        self.next_leaf = new_node

        return new_node, promote_key


class BPlusTree:
    """B+树实现，用于快速查找量子比特候选区域.

    在论文:
    <A New Qubits Mapping Mechanism for Multiprogramming Quantum Computing>
    的基础上,使用B+树来存储和搜索可靠的映射区域
    """

    def __init__(self, order: int = 3):
        """初始化B+树.

        Args:
            order: B+树的阶数，默认为3
        """
        self.order = order
        self.root: BPlusTreeNode = (
            BPlusTreeLeafNode()
        )  # 初始时根节点是叶子节点
        self.min_keys = (order + 1) // 2  # 最小键值数量

    def insert(self, key: int, value: list[int]):
        """插入键值对.

        Args:
            key: 键值（量子比特数量）
            value: 候选区域（量子比特列表）
        """
        # 找到要插入的叶子节点
        leaf = self._find_leaf(key)

        # 插入到叶子节点
        leaf.insert_key_value(key, value)

        # 检查是否需要分裂
        if len(leaf.keys) > self.order:
            self._split_leaf(leaf)

    def _find_leaf(self, key: int) -> BPlusTreeLeafNode:
        """找到应该插入键值的叶子节点.

        使用自上而下的搜索方式.

        Args:
            key: 键值

        Returns:
            BPlusTreeLeafNode: 叶子节点
        """
        current = self.root

        # 从根节点向下遍历到叶子节点
        while not current.is_leaf:
            # 类型检查：确保是内部节点
            if isinstance(current, BPlusTreeInternalNode):
                # 找到合适的子节点路径
                child_index = 0
                while (
                    child_index < len(current.keys)
                    and current.keys[child_index] <= key
                ):
                    child_index += 1
                current = current.children[child_index]

        # 类型检查：确保是叶子节点
        if isinstance(current, BPlusTreeLeafNode):
            return current
        else:
            # 这种情况不应该发生，但为了类型安全
            raise RuntimeError("Expected leaf node but got internal node")

    def _split_leaf(self, leaf: BPlusTreeLeafNode):
        """分裂叶子节点.

        Args:
            leaf: 要分裂的叶子节点
        """
        new_leaf, promote_key = leaf.split()

        if leaf.parent is None:
            # 根节点分裂，创建新的根节点
            new_root = BPlusTreeInternalNode()
            new_root.keys = [promote_key]
            new_root.children = [leaf, new_leaf]
            leaf.parent = new_root
            new_leaf.parent = new_root
            self.root = new_root
        else:
            # 非根节点分裂
            parent = leaf.parent
            # 类型检查：确保父节点是内部节点
            if isinstance(parent, BPlusTreeInternalNode):
                parent.insert_key_child(promote_key, new_leaf)

                # 检查父节点是否需要分裂
                if len(parent.keys) > self.order:
                    self._split_internal(parent)

    def _split_internal(self, internal: BPlusTreeInternalNode):
        """分裂内部节点.

        Args:
            internal: 要分裂的内部节点
        """
        new_internal, promote_key = internal.split()

        if internal.parent is None:
            # 根节点分裂，创建新的根节点
            new_root = BPlusTreeInternalNode()
            new_root.keys = [promote_key]
            new_root.children = [internal, new_internal]
            internal.parent = new_root
            new_internal.parent = new_root
            self.root = new_root
        else:
            # 非根节点分裂
            parent = internal.parent
            # 类型检查：确保父节点是内部节点
            if isinstance(parent, BPlusTreeInternalNode):
                parent.insert_key_child(promote_key, new_internal)

                # 检查父节点是否需要分裂
                if len(parent.keys) > self.order:
                    self._split_internal(parent)

    def search_candidates(self, min_qubits: int) -> list[list[int]]:
        """搜索满足最小量子比特数量要求的候选区域.

        使用自上而下的搜索方式.

        Args:
            min_qubits: 最小量子比特数量

        Returns:
            List[List[int]]: 候选区域列表
        """
        candidates = []

        # 从根节点开始，自上而下搜索到叶子节点
        current = self.root

        # 如果根节点是叶子节点，直接搜索
        if current.is_leaf and isinstance(current, BPlusTreeLeafNode):
            for i, key in enumerate(current.keys):
                if key >= min_qubits:
                    candidates.append(current.values[i])
            return candidates

        # 从根节点开始向下搜索到合适的叶子节点
        while not current.is_leaf:
            # 类型检查：确保是内部节点
            if isinstance(current, BPlusTreeInternalNode):
                # 找到合适的子节点路径
                child_index = 0
                while (
                    child_index < len(current.keys)
                    and current.keys[child_index] <= min_qubits
                ):
                    child_index += 1
                current = current.children[child_index]

        # 现在current是叶子节点，从当前位置开始搜索所有满足条件的候选区域
        current_leaf: BPlusTreeLeafNode | None = (
            current if isinstance(current, BPlusTreeLeafNode) else None
        )
        while current_leaf is not None:
            # 在当前叶子节点中搜索
            for i, key in enumerate(current_leaf.keys):
                if key >= min_qubits:
                    candidates.append(current_leaf.values[i])

            # 移动到下一个叶子节点
            current_leaf = current_leaf.next_leaf

        return candidates

    def get_all_candidates(
        self,
    ) -> list[tuple[int, list[int]]]:
        """获取所有候选区域.

        Returns:
            List[Tuple[int, List[int]]]: (量子比特数量, 候选区域)的列表
        """
        all_candidates = []

        # 找到最左边的叶子节点
        current = self.root
        while not current.is_leaf:
            # 类型检查：确保是内部节点
            if isinstance(current, BPlusTreeInternalNode):
                current = current.children[0]
            else:
                break

        # 遍历所有叶子节点
        current_leaf: BPlusTreeLeafNode | None = (
            current if isinstance(current, BPlusTreeLeafNode) else None
        )
        while current_leaf is not None:
            for i, key in enumerate(current_leaf.keys):
                all_candidates.append((key, current_leaf.values[i]))
            current_leaf = current_leaf.next_leaf

        return all_candidates

    def print_tree(self):
        """打印B+树结构（用于调试）."""
        logger.info("B+ Tree Structure:")
        self._print_node(self.root, 0)

    def _print_node(self, node: BPlusTreeNode, level: int):
        """递归打印节点.

        Args:
            node: 节点
            level: 层级
        """
        indent = "  " * level
        if node.is_leaf:
            # 类型检查：确保是叶子节点
            if isinstance(node, BPlusTreeLeafNode):
                logger.info(
                    f"{indent}Leaf: keys={node.keys}, values={node.values}"
                )
        else:
            # 类型检查：确保是内部节点
            if isinstance(node, BPlusTreeInternalNode):
                logger.info(f"{indent}Internal: keys={node.keys}")
                for child in node.children:
                    self._print_node(child, level + 1)


def build_bplus_tree_from_hierarchy(ht) -> BPlusTree:
    """从层次树构建B+树.

    层次树中的所有节点都是B+树中叶子节点对应的可选择区域.

    Args:
        ht: 层次树对象

    Returns:
        BPlusTree: 构建好的B+树
    """
    bplus_tree = BPlusTree()

    # 收集层次树中的所有节点作为候选区域
    all_nodes = []

    def collect_nodes(node):
        """递归收集所有节点."""
        if node is None:
            return
        # 只收集未被忽略且包含量子比特的节点
        if not node.ignore and len(node.qubits) > 0:
            all_nodes.append(node)
        collect_nodes(node.left)
        collect_nodes(node.right)

    collect_nodes(ht.root)
    # 按量子比特数量（社区大小）作为键值插入B+树
    for node in all_nodes:
        community_size = len(node.qubits)  # 社区大小作为B+树的键值
        community_qubits = node.qubits.copy()  # 社区包含的量子比特作为值
        bplus_tree.insert(community_size, community_qubits)

    logger.info(f"Built B+ tree with {len(all_nodes)} valid nodes")
    return bplus_tree


def get_block_bplus(ht, qnum: int) -> list[int] | None:
    """使用B+树快速查找满足量子比特数量要求的候选区域.

    Args:
        ht: 层次树对象
        qnum: 需要的量子比特数量

    Returns:
        Optional[List[int]]: 最佳候选区域，如果没有找到则返回None
    """
    # 如果B+树不存在，构建一个
    if not hasattr(ht, "bplus_tree") or ht.bplus_tree is None:
        ht.bplus_tree = build_bplus_tree_from_hierarchy(ht)

    # 使用B+树搜索候选区域
    candidates = ht.bplus_tree.search_candidates(qnum)

    if not candidates:
        logger.warning(f"No candidate regions found for {qnum} qubits")
        return None

    # 从候选区域中选择最佳候选区域
    # 优先选择恰好包含所需数量量子比特的区域，然后选择保真度最高的
    best_candidate = None
    max_fidelity = -1.0

    # 首先尝试找到恰好包含所需数量量子比特的区域
    exact_size_candidates = [c for c in candidates if len(c) == qnum]

    if exact_size_candidates:
        # 如果有恰好大小的候选区域，从中选择保真度最高的
        for candidate in exact_size_candidates:
            temp_node = type("TempNode", (), {"qubits": candidate})()
            fidelity = ht.average_fidelity(temp_node)

            if fidelity > max_fidelity:
                max_fidelity = fidelity
                best_candidate = candidate
    else:
        # 如果没有恰好大小的候选区域，从所有候选区域中选择保真度最高的
        for candidate in candidates:
            temp_node = type("TempNode", (), {"qubits": candidate})()
            fidelity = ht.average_fidelity(temp_node)

            if fidelity > max_fidelity:
                max_fidelity = fidelity
                best_candidate = candidate

    if best_candidate:
        logger.info(
            f"Found best candidate with {len(best_candidate)} qubits, "
            f"fidelity: {max_fidelity:.4f}"
        )
        # 找到包含最佳候选区域的节点并移除
        target_node = _find_node_with_qubits(ht.root, best_candidate)
        if target_node:
            _remove_used_nodes(ht, best_candidate)
        else:
            logger.warning(
                "Could not find exact node containing the best candidate"
            )

    return best_candidate


def _find_node_with_qubits(node, qubits: list[int]):
    """递归查找包含指定量子比特的节点.

    Args:
        node: 当前节点
        qubits: 要查找的量子比特列表

    Returns:
        包含指定量子比特的节点，如果没有找到则返回None
    """
    if node is None or node.ignore:
        return None

    # 检查当前节点是否包含所有指定的量子比特
    node_qubits_set = set(node.qubits)
    target_qubits_set = set(qubits)

    if target_qubits_set.issubset(node_qubits_set):
        # 检查子节点是否也包含所有指定的量子比特
        left_result = _find_node_with_qubits(node.left, qubits)
        right_result = _find_node_with_qubits(node.right, qubits)

        # 如果子节点也包含，返回更具体的子节点
        if left_result is not None:
            return left_result
        if right_result is not None:
            return right_result

        # 如果当前节点包含且子节点不包含，返回当前节点
        return node

    return None


def _ignore_node(node):
    """递归标记节点及其所有子节点为忽略状态.

    Args:
        node: 要忽略的节点
    """
    if node is None:
        return
    node.ignore = True
    _ignore_node(node.left)
    _ignore_node(node.right)


def _remove_used_nodes(ht, used_qubits: list[int]):
    """从层次树中移除已使用的量子比特.

    使用与原始remove函数相同的逻辑，但确保已分配的量子比特从所有相关节点中删除.

    Args:
        ht: 层次树对象
        used_qubits: 已使用的量子比特列表
    """
    used_set = set(used_qubits)

    # 找到包含所有已使用量子比特的最具体节点
    target_node = _find_node_with_qubits(ht.root, used_qubits)

    if target_node is None:
        logger.warning("Could not find exact node containing all used qubits")
        return

    # 使用与原始remove函数相同的逻辑
    _ignore_node(target_node)
    removed_qubits = set(target_node.qubits)

    # 从父节点中移除已使用的量子比特
    if target_node.parent:
        if target_node.pos == 0:
            target_node.parent.left = None
        else:
            target_node.parent.right = None

        current_node = target_node
        while current_node.parent:
            parent = current_node.parent
            parent_qubits_set = set(parent.qubits)
            parent.qubits = list(parent_qubits_set ^ removed_qubits)
            current_node = parent

    # *：从层次树的其他节点中删除已使用的量子比特
    # 但只从包含已使用量子比特的节点中删除，不要从已经被标记为忽略的节点中删除
    def remove_qubits_from_other_nodes(node, used_qubits_set):
        """递归从其他节点中删除已使用的量子比特，但保持层次树结构.

        Args:
            node: 当前节点
            used_qubits_set: 已使用的量子比特集合
        """
        if node is None or node.ignore:
            return

        # 检查当前节点是否包含已使用的量子比特
        node_qubits_set = set(node.qubits)
        if used_qubits_set.intersection(node_qubits_set):
            # 从当前节点中删除已使用的量子比特
            remaining_qubits = node_qubits_set - used_qubits_set
            node.qubits = list(remaining_qubits)

            # 如果节点中没有任何量子比特了，标记为忽略
            if not node.qubits:
                node.ignore = True

        # 递归处理子节点
        remove_qubits_from_other_nodes(node.left, used_qubits_set)
        remove_qubits_from_other_nodes(node.right, used_qubits_set)

    # 从层次树的其他节点中删除已使用的量子比特
    # 但不要从已经被标记为忽略的节点中删除（这些节点已经被原始逻辑处理了）
    remove_qubits_from_other_nodes(ht.root, used_set)

    # 重建B+树以反映变化
    ht.bplus_tree = build_bplus_tree_from_hierarchy(ht)
