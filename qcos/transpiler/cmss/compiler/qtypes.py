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

import typing as T
from enum import Enum


class Node:
    """抽象语法树节点类."""

    def __init__(
        self,
        node_type: str,
        children: list[T.Any] = [],
        leaf: T.Any = None,
        pos=None,
    ):
        """初始化抽象语法树节点，设置节点类型以及节点信息.

        Args:
            node_type (str): 节点名
            children (T.List[T.Any]): 子节点列表. Defaults to None.
            leaf (T.Any): 节点中的一些常量值. Defaults to None.
            pos (int): 节点对应语句所在原文位置（行号）. Defaults to None.
        """
        self.type = node_type
        if children:
            self.children = children
        else:
            self.children = []
        self.leaf = leaf
        self.pos = pos
        self.val = None


class RegType(Enum):
    """寄存器变量类型，QREG为量子寄存器变量，CREG为经典寄存器变量."""

    QREG = 1
    CREG = 2
