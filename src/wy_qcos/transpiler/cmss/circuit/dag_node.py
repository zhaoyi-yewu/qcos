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

from collections.abc import Iterable


class DAGNode:
    """Parent class for DAGOpNode, DAGInNode, and DAGOutNode."""

    __slots__ = ["_node_id"]

    def __init__(self, nid=-1):
        """Create a node."""
        self._node_id = nid

    def __lt__(self, other):
        return self._node_id < other._node_id

    def __gt__(self, other):
        return self._node_id > other._node_id

    def __str__(self):
        return str(id(self))


class DAGOpNode(DAGNode):
    """Object to represent an Gate at a node in the DAGCircuit."""

    __slots__ = ["op", "qargs", "cargs", "sort_key"]

    def __init__(
        self, op, qargs: Iterable[int] = (), cargs: Iterable[int] = ()
    ):
        """Create an Gate node."""
        super().__init__()
        self.op = op
        self.qargs = tuple(qargs)
        self.cargs = tuple(cargs)
        self.sort_key = str(self.qargs)

    @property
    def name(self):
        """Returns the Gate name corresponding to the op for this node."""
        return self.op.name

    @name.setter
    def name(self, new_name):
        """Sets the Gate name corresponding to the op for this node."""
        self.op.name = new_name

    def __repr__(self):
        """Returns a representation of the DAGOpNode."""
        return (
            f"DAGOpNode(op={self.op}, qargs={self.qargs}, cargs={self.cargs})"
        )


class DAGInNode(DAGNode):
    """Object to represent an incoming wire node in the DAGCircuit."""

    __slots__ = ["wire", "sort_key"]

    def __init__(self, wire):
        """Create an incoming node."""
        super().__init__()
        self.wire = wire
        self.sort_key = str([])

    def __repr__(self):
        """Returns a representation of the DAGInNode."""
        return f"DAGInNode(wire={self.wire})"


class DAGOutNode(DAGNode):
    """Object to represent an outgoing wire node in the DAGCircuit."""

    __slots__ = ["wire", "sort_key"]

    def __init__(self, wire):
        """Create an outgoing node."""
        super().__init__()
        self.wire = wire
        self.sort_key = str([])

    def __repr__(self):
        """Returns a representation of the DAGOutNode."""
        return f"DAGOutNode(wire={self.wire})"
