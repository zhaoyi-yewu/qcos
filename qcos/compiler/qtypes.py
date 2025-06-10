import typing as T
from enum import Enum


class Node:
    """
    抽象语法树节点类
    """

    def __init__(self, node_type: str, children: T.List[T.Any] = None, leaf: T.Any = None, pos=None):
        """
        初始化抽象语法树节点，设置节点类型以及节点信息
        参数:
        node_type (str): 节点名
        children (T.List[T.Any], optional): 子节点列表. Defaults to None.
        leaf (T.Any, optional): 节点中的一些常量值. Defaults to None.
        pos (_type_, optional): 节点对应语句所在原文位置（行号）. Defaults to None.
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
    """
    寄存器变量类型，QREG为量子寄存器变量，CREG为经典寄存器变量
    """
    QREG = 1
    CREG = 2
