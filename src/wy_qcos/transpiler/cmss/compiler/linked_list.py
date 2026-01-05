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

from wy_qcos.transpiler.cmss.compiler.qtypes import Node as TreeNode


class LinkedNode:
    """作用域节点类."""

    def __init__(self, data):
        """初始化作用域节点，设置作用域内的变量信息.

        Args:
            data (dict): 作用域内的变量信息
        """
        self.data = data
        self.next = None
        self.previous = None


class LinkedList:
    """作用域链表类."""

    def __init__(self):
        """初始化作用域链表，设置链表的虚拟头节点."""
        # 链表中的节点数量
        self.size = 1
        # 链表的头节点
        self.head = LinkedNode(None)
        # 链表的尾节点
        self.tail = self.head

    def get_tail(self) -> LinkedNode:
        """获取最内部的符号表节点，一般用于获取当前作用域的符号表。.

        Returns:
            链表的尾节点
        """
        return self.tail

    def get_head(self) -> LinkedNode:
        """头节点，只作为头部，不存放符号表数据.

        Returns:
            链表的头节点
        """
        return self.head

    def add_tail(self, tail: LinkedNode, scope: TreeNode):
        """新增一个最内部的符号表节点，用在visitor新的作用域之前。.

        Args:
            tail (LinkedNode): 作用域节点
            scope (TreeNode): 抽象语法树节点
        """
        if scope is None or (scope.type not in ("block_body", "top")):
            raise TypeError("invalid scope tp add symbol table")

        if (
            tail.data is None
            or not isinstance(tail.data, dict)
            or len(tail.data) != 0
        ):
            raise TypeError("invalid data type when init symbol table")

        temp = self.tail
        temp.next = tail
        tail.previous = temp
        self.tail = tail
        self.size = self.size + 1

    def remove_tail(self) -> bool:
        """删除最内部的符号表，一般用于删除当前作用域的符号表.

        Returns:
            节点是否删除成功
        """
        if self.head == self.tail:
            return False
        prev = self.tail.previous
        prev.next = None
        self.tail.previous = None
        del self.tail
        self.tail = prev
        self.size = self.size - 1
        return True
