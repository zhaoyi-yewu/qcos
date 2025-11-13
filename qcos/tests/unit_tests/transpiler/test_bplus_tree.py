#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from unittest.mock import Mock, patch

from qcos.transpiler.cmss.mapping.bplus_tree import (
    BPlusTreeNode,
    BPlusTreeInternalNode,
    BPlusTreeLeafNode,
    BPlusTree,
    build_bplus_tree_from_hierarchy,
    get_block_bplus,
    _find_node_with_qubits,
    _ignore_node,
    _remove_used_nodes,
)


class TestBPlusTreeNode:
    """测试B+树节点基类"""

    def test_init_leaf_node(self):
        """测试初始化叶子节点"""
        node = BPlusTreeNode(is_leaf=True)
        assert node.is_leaf is True
        assert not node.keys
        assert node.parent is None

    def test_init_internal_node(self):
        """测试初始化内部节点"""
        node = BPlusTreeNode(is_leaf=False)
        assert node.is_leaf is False
        assert not node.keys
        assert node.parent is None


class TestBPlusTreeInternalNode:
    """测试B+树内部节点"""

    def test_init(self):
        """测试内部节点初始化"""
        node = BPlusTreeInternalNode()
        assert node.is_leaf is False
        assert not node.keys
        assert not node.children
        assert node.parent is None

    def test_insert_key_child(self):
        """测试插入键值对和子节点"""
        node = BPlusTreeInternalNode()

        # 创建子节点
        child1 = BPlusTreeLeafNode()
        child2 = BPlusTreeLeafNode()

        # 插入键值对
        node.insert_key_child(5, child1)
        assert node.keys == [5]
        assert node.children == [child1]
        assert child1.parent == node

        # 插入更小的键值
        node.insert_key_child(3, child2)
        assert node.keys == [3, 5]
        assert node.children == [child1, child2]
        assert child2.parent == node

        # 插入中间的键值
        child3 = BPlusTreeLeafNode()
        node.insert_key_child(4, child3)
        assert node.keys == [3, 4, 5]
        assert node.children == [child1, child2, child3]
        assert child3.parent == node

    def test_split(self):
        """测试内部节点分裂"""
        node = BPlusTreeInternalNode()

        # 创建子节点
        children = [BPlusTreeLeafNode() for _ in range(6)]

        # 插入键值和子节点
        for i, child in enumerate(children):
            node.insert_key_child(i * 2, child)

        # 分裂节点
        new_node, promote_key = node.split()

        # 验证分裂结果
        assert promote_key == 6  # 中间键值
        assert node.keys == [0, 2, 4]  # 前半部分
        assert node.children == [
            children[0],
            children[1],
            children[2],
            children[3],
        ]  # 前半部分子节点
        assert new_node.keys == [8, 10]  # 后半部分
        assert new_node.children == [
            children[4],
            children[5],
        ]  # 后半部分子节点

        # 验证新节点子节点的父指针
        for child in new_node.children:
            assert child.parent == new_node


class TestBPlusTreeLeafNode:
    """测试B+树叶子节点"""

    def test_init(self):
        """测试叶子节点初始化"""
        node = BPlusTreeLeafNode()
        assert node.is_leaf is True
        assert not node.keys
        assert not node.values
        assert node.next_leaf is None

    def test_insert_key_value(self):
        """测试插入键值对"""
        node = BPlusTreeLeafNode()

        # 插入键值对
        node.insert_key_value(5, [1, 2, 3])
        assert node.keys == [5]
        assert node.values == [[1, 2, 3]]

        # 插入更小的键值
        node.insert_key_value(3, [4, 5])
        assert node.keys == [3, 5]
        assert node.values == [[4, 5], [1, 2, 3]]

        # 插入中间的键值
        node.insert_key_value(4, [6, 7, 8])
        assert node.keys == [3, 4, 5]
        assert node.values == [[4, 5], [6, 7, 8], [1, 2, 3]]

    def test_split(self):
        """测试叶子节点分裂"""
        node = BPlusTreeLeafNode()

        # 插入多个键值对
        for i in range(6):
            node.insert_key_value(i * 2, list(range(i * 2, i * 2 + 3)))

        # 分裂节点
        new_node, promote_key = node.split()

        # 验证分裂结果
        assert promote_key == 6  # 中间键值
        assert node.keys == [0, 2, 4]  # 前半部分
        assert node.values == [
            list(range(0, 3)),
            list(range(2, 5)),
            list(range(4, 7)),
        ]  # 前半部分值
        assert new_node.keys == [6, 8, 10]  # 后半部分
        assert new_node.values == [
            list(range(6, 9)),
            list(range(8, 11)),
            list(range(10, 13)),
        ]  # 后半部分值

        # 验证叶子节点链表
        assert node.next_leaf == new_node
        assert new_node.next_leaf is None


class TestBPlusTree:
    """测试B+树主类"""

    def test_init(self):
        """测试B+树初始化"""
        tree = BPlusTree(order=3)
        assert tree.order == 3
        assert tree.min_keys == 2
        assert isinstance(tree.root, BPlusTreeLeafNode)
        assert tree.root.is_leaf is True

    def test_init_default_order(self):
        """测试默认阶数初始化"""
        tree = BPlusTree()
        assert tree.order == 3
        assert tree.min_keys == 2

    def test_insert_single(self):
        """测试插入单个键值对"""
        tree = BPlusTree(order=3)
        tree.insert(5, [1, 2, 3])

        assert isinstance(tree.root, BPlusTreeLeafNode)
        assert tree.root.keys == [5]
        assert tree.root.values == [[1, 2, 3]]

    def test_insert_multiple_no_split(self):
        """测试插入多个键值对但不分裂"""
        tree = BPlusTree(order=5)
        tree.insert(3, [1, 2])
        tree.insert(1, [3, 4])
        tree.insert(5, [5, 6])

        assert isinstance(tree.root, BPlusTreeLeafNode)
        assert tree.root.keys == [1, 3, 5]
        assert tree.root.values == [[3, 4], [1, 2], [5, 6]]

    def test_insert_leaf_split(self):
        """测试叶子节点分裂"""
        tree = BPlusTree(order=3)

        # 插入4个键值对，触发分裂
        tree.insert(1, [1])
        tree.insert(2, [2])
        tree.insert(3, [3])
        tree.insert(4, [4])

        # 根节点应该是内部节点
        assert isinstance(tree.root, BPlusTreeInternalNode)
        assert tree.root.keys == [3]  # 提升的键值

        # 应该有两个子节点
        assert len(tree.root.children) == 2
        left_child = tree.root.children[0]
        right_child = tree.root.children[1]

        assert isinstance(left_child, BPlusTreeLeafNode)
        assert isinstance(right_child, BPlusTreeLeafNode)
        assert left_child.keys == [1, 2]
        assert right_child.keys == [3, 4]

    def test_find_leaf(self):
        """测试查找叶子节点"""
        tree = BPlusTree(order=3)

        # 插入数据
        tree.insert(1, [1])
        tree.insert(3, [3])
        tree.insert(5, [5])

        # 测试查找
        leaf = tree._find_leaf(2)
        assert isinstance(leaf, BPlusTreeLeafNode)
        assert leaf.keys == [1, 3, 5]

    def test_search_candidates_leaf_root(self):
        """测试在叶子根节点中搜索候选区域"""
        tree = BPlusTree(order=3)

        # 插入数据
        tree.insert(2, [1, 2])
        tree.insert(4, [3, 4, 5, 6])
        tree.insert(6, [7, 8, 9, 10, 11, 12])

        # 搜索候选区域
        candidates = tree.search_candidates(3)
        assert len(candidates) == 2
        assert [3, 4, 5, 6] in candidates
        assert [7, 8, 9, 10, 11, 12] in candidates

    def test_search_candidates_no_match(self):
        """测试搜索无匹配的候选区域"""
        tree = BPlusTree(order=3)

        # 插入数据
        tree.insert(2, [1, 2])
        tree.insert(4, [3, 4, 5, 6])

        # 搜索不存在的候选区域
        candidates = tree.search_candidates(10)
        assert len(candidates) == 0

    def test_get_all_candidates(self):
        """测试获取所有候选区域"""
        tree = BPlusTree(order=3)

        # 插入数据
        tree.insert(2, [1, 2])
        tree.insert(4, [3, 4, 5, 6])
        tree.insert(6, [7, 8, 9, 10, 11, 12])

        # 获取所有候选区域
        all_candidates = tree.get_all_candidates()
        assert len(all_candidates) == 3

        # 验证结果包含所有键值对
        keys = [key for key, _ in all_candidates]
        assert 2 in keys
        assert 4 in keys
        assert 6 in keys

    def test_print_tree(self):
        """测试打印树结构"""
        tree = BPlusTree(order=3)
        tree.insert(1, [1])
        tree.insert(2, [2])

        # 测试打印不会抛出异常
        tree.print_tree()

    def test_complex_insertion_and_search(self):
        """测试复杂的插入和搜索场景"""
        tree = BPlusTree(order=3)

        # 插入多个数据，触发多次分裂
        for i in range(10):
            tree.insert(i, list(range(i, i + 3)))

        # 搜索候选区域
        candidates = tree.search_candidates(2)
        assert len(candidates) > 0

        # 验证所有候选区域都满足最小量子比特要求
        for candidate in candidates:
            assert len(candidate) >= 2

    def test_internal_node_split(self):
        """测试内部节点分裂"""
        tree = BPlusTree(order=3)

        # 插入足够多的数据以触发内部节点分裂
        for i in range(20):
            tree.insert(i, list(range(i, i + 2)))

        # 验证树结构
        assert isinstance(tree.root, BPlusTreeInternalNode)

        # 搜索应该仍然工作
        candidates = tree.search_candidates(5)
        assert len(candidates) > 0


class TestBPlusTreeHelperFunctions:
    """测试B+树辅助函数"""

    def test_build_bplus_tree_from_hierarchy(self):
        """测试从层次树构建B+树"""
        # 创建模拟的层次树
        mock_node1 = Mock()
        mock_node1.ignore = False
        mock_node1.qubits = [1, 2, 3]
        mock_node1.left = None
        mock_node1.right = None

        mock_node2 = Mock()
        mock_node2.ignore = False
        mock_node2.qubits = [4, 5, 6, 7]
        mock_node2.left = None
        mock_node2.right = None

        mock_root = Mock()
        mock_root.ignore = False
        mock_root.qubits = [1, 2, 3, 4, 5, 6, 7]
        mock_root.left = mock_node1
        mock_root.right = mock_node2

        mock_ht = Mock()
        mock_ht.root = mock_root

        # 构建B+树
        bplus_tree = build_bplus_tree_from_hierarchy(mock_ht)

        # 验证B+树
        assert isinstance(bplus_tree, BPlusTree)
        all_candidates = bplus_tree.get_all_candidates()
        assert len(all_candidates) == 3  # 3个有效节点

        # 验证键值
        keys = [key for key, _ in all_candidates]
        assert 3 in keys  # mock_node1
        assert 4 in keys  # mock_node2
        assert 7 in keys  # mock_root

    def test_build_bplus_tree_with_ignored_nodes(self):
        """测试构建B+树时忽略被标记的节点"""
        # 创建模拟的层次树，包含被忽略的节点
        mock_ignored_node = Mock()
        mock_ignored_node.ignore = True
        mock_ignored_node.qubits = [8, 9]
        mock_ignored_node.left = None
        mock_ignored_node.right = None

        mock_valid_node = Mock()
        mock_valid_node.ignore = False
        mock_valid_node.qubits = [1, 2]
        mock_valid_node.left = None
        mock_valid_node.right = None

        mock_root = Mock()
        mock_root.ignore = False
        mock_root.qubits = [1, 2, 3]
        mock_root.left = mock_valid_node
        mock_root.right = mock_ignored_node

        mock_ht = Mock()
        mock_ht.root = mock_root

        # 构建B+树
        bplus_tree = build_bplus_tree_from_hierarchy(mock_ht)

        # 验证只包含有效节点
        all_candidates = bplus_tree.get_all_candidates()
        assert len(all_candidates) == 2  # 只有2个有效节点

        # 验证不包含被忽略节点的量子比特
        all_qubits = []
        for _, qubits in all_candidates:
            all_qubits.extend(qubits)
        assert 8 not in all_qubits
        assert 9 not in all_qubits

    def test_get_block_bplus_success(self):
        """测试成功获取候选区域"""
        # 创建模拟的层次树
        mock_ht = Mock()
        mock_ht.bplus_tree = None

        # 模拟B+树
        mock_bplus_tree = Mock()
        mock_bplus_tree.search_candidates.return_value = [
            [1, 2, 3],
            [4, 5, 6, 7],
        ]

        # 模拟层次树的average_fidelity方法
        def mock_average_fidelity(node):
            return 0.9 if len(node.qubits) == 3 else 0.8

        mock_ht.average_fidelity = mock_average_fidelity

        with patch(
            "qcos.transpiler.cmss.mapping.bplus_tree."
            "build_bplus_tree_from_hierarchy"
        ) as mock_build:
            mock_build.return_value = mock_bplus_tree

            with patch(
                "qcos.transpiler.cmss.mapping.bplus_tree."
                "_find_node_with_qubits"
            ) as mock_find:
                mock_find.return_value = Mock()

                with patch(
                    "qcos.transpiler.cmss.mapping.bplus_tree."
                    "_remove_used_nodes"
                ):
                    result = get_block_bplus(mock_ht, 3)

                    # 验证结果
                    assert result == [1, 2, 3]  # 应该返回恰好3个量子比特的区域
                    mock_build.assert_called_once_with(mock_ht)
                    mock_bplus_tree.search_candidates.assert_called_once_with(
                        3
                    )

    def test_get_block_bplus_no_candidates(self):
        """测试没有候选区域的情况"""
        mock_ht = Mock()
        mock_ht.bplus_tree = None

        mock_bplus_tree = Mock()
        mock_bplus_tree.search_candidates.return_value = []

        with patch(
            "qcos.transpiler.cmss.mapping.bplus_tree."
            "build_bplus_tree_from_hierarchy"
        ) as mock_build:
            mock_build.return_value = mock_bplus_tree

            result = get_block_bplus(mock_ht, 10)

            # 验证结果
            assert result is None
            mock_build.assert_called_once_with(mock_ht)

    def test_find_node_with_qubits(self):
        """测试查找包含指定量子比特的节点"""
        # 创建模拟节点
        mock_node = Mock()
        mock_node.ignore = False
        mock_node.qubits = [1, 2, 3, 4, 5]
        mock_node.left = None
        mock_node.right = None

        # 测试找到包含量子比特的节点
        result = _find_node_with_qubits(mock_node, [2, 3])
        assert result == mock_node

        # 测试找不到的情况
        result = _find_node_with_qubits(mock_node, [6, 7])
        assert result is None

        # 测试忽略的节点
        mock_node.ignore = True
        result = _find_node_with_qubits(mock_node, [2, 3])
        assert result is None

    def test_find_node_with_qubits_recursive(self):
        """测试递归查找包含指定量子比特的节点"""
        # 创建子节点
        mock_child = Mock()
        mock_child.ignore = False
        mock_child.qubits = [1, 2]
        mock_child.left = None
        mock_child.right = None

        # 创建父节点
        mock_parent = Mock()
        mock_parent.ignore = False
        mock_parent.qubits = [1, 2, 3, 4, 5]
        mock_parent.left = mock_child
        mock_parent.right = None

        # 测试找到更具体的子节点
        result = _find_node_with_qubits(mock_parent, [1, 2])
        assert result == mock_child

    def test_ignore_node(self):
        """测试忽略节点"""
        # 创建节点层次结构
        mock_child1 = Mock()
        mock_child1.ignore = False
        mock_child1.left = None
        mock_child1.right = None

        mock_child2 = Mock()
        mock_child2.ignore = False
        mock_child2.left = None
        mock_child2.right = None

        mock_node = Mock()
        mock_node.ignore = False
        mock_node.left = mock_child1
        mock_node.right = mock_child2

        # 忽略节点
        _ignore_node(mock_node)

        # 验证所有节点都被标记为忽略
        assert mock_node.ignore is True
        assert mock_child1.ignore is True
        assert mock_child2.ignore is True

    def test_remove_used_nodes(self):
        """测试移除已使用的节点"""
        # 创建模拟的层次树
        mock_ht = Mock()
        mock_ht.root = Mock()
        mock_ht.bplus_tree = None

        with patch(
            "qcos.transpiler.cmss.mapping.bplus_tree._find_node_with_qubits"
        ) as mock_find:
            mock_target_node = Mock()
            mock_target_node.qubits = [1, 2, 3]
            mock_target_node.parent = None
            mock_find.return_value = mock_target_node

            with patch(
                "qcos.transpiler.cmss.mapping.bplus_tree._ignore_node"
            ) as mock_ignore:
                with patch(
                    "qcos.transpiler.cmss.mapping.bplus_tree."
                    "build_bplus_tree_from_hierarchy"
                ) as mock_build:
                    _remove_used_nodes(mock_ht, [1, 2, 3])

                    # 验证调用
                    mock_find.assert_called_once_with(mock_ht.root, [1, 2, 3])
                    mock_ignore.assert_called_once_with(mock_target_node)
                    mock_build.assert_called_once_with(mock_ht)

    def test_remove_used_nodes_no_target(self):
        """测试移除已使用节点时找不到目标节点"""
        mock_ht = Mock()
        mock_ht.root = Mock()

        with patch(
            "qcos.transpiler.cmss.mapping.bplus_tree._find_node_with_qubits"
        ) as mock_find:
            mock_find.return_value = None

            # 应该不会抛出异常
            _remove_used_nodes(mock_ht, [1, 2, 3])

            mock_find.assert_called_once_with(mock_ht.root, [1, 2, 3])


class TestBPlusTreeEdgeCases:
    """测试B+树边界情况"""

    def test_empty_tree_search(self):
        """测试空树搜索"""
        tree = BPlusTree()
        candidates = tree.search_candidates(1)
        assert not candidates

    def test_empty_tree_get_all(self):
        """测试空树获取所有候选区域"""
        tree = BPlusTree()
        all_candidates = tree.get_all_candidates()
        assert not all_candidates

    def test_single_node_tree(self):
        """测试单节点树"""
        tree = BPlusTree()
        tree.insert(1, [1, 2])

        candidates = tree.search_candidates(1)
        assert len(candidates) == 1
        assert [1, 2] in candidates

    def test_duplicate_keys(self):
        """测试重复键值"""
        tree = BPlusTree()
        tree.insert(1, [1, 2])
        tree.insert(1, [3, 4])  # 重复键值

        # 应该都能插入
        all_candidates = tree.get_all_candidates()
        assert len(all_candidates) == 2

    def test_large_order_tree(self):
        """测试大阶数B+树"""
        tree = BPlusTree(order=10)

        # 插入多个数据
        for i in range(20):
            tree.insert(i, list(range(i, i + 2)))

        # 搜索应该正常工作
        candidates = tree.search_candidates(5)
        assert len(candidates) > 0

    def test_find_leaf_with_internal_root(self):
        """测试在内部根节点中查找叶子节点"""
        tree = BPlusTree(order=3)

        # 插入足够数据触发分裂
        for i in range(10):
            tree.insert(i, [i])

        # 验证根节点是内部节点
        assert isinstance(tree.root, BPlusTreeInternalNode)

        # 查找叶子节点应该正常工作
        leaf = tree._find_leaf(5)
        assert isinstance(leaf, BPlusTreeLeafNode)

    def test_search_candidates_with_internal_root(self):
        """测试在内部根节点中搜索候选区域"""
        tree = BPlusTree(order=3)

        # 插入数据触发分裂
        for i in range(10):
            tree.insert(i, [i, i + 1])

        # 搜索候选区域
        candidates = tree.search_candidates(1)
        assert len(candidates) > 0

        # 验证所有候选区域都满足要求
        for candidate in candidates:
            assert len(candidate) >= 1
