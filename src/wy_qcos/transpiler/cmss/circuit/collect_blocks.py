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

from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.dag_node import DAGOpNode


class BlockCollector:
    """Dividing a DAG into blocks of nodes that satisfy certain criteria."""

    def __init__(self, dag: DAGCircuit):
        self.dag = dag
        self._pending_nodes = None
        self._in_degree = None
        self._collect_from_back = False
        if not isinstance(dag, DAGCircuit):
            raise ValueError("The input object is not a DAG.")

    def _setup_in_degrees(self):
        """Calculate the in-degree of each node.

        The in-degree is the number of unprocessed immediate predecessors, it
        is set up at the start and updated throughout the algorithm.
        Additionally, ``_pending_nodes`` explicitly keeps the list of nodes
        whose ``_in_degree`` is 0.
        """
        self._pending_nodes = []
        self._in_degree = {}
        for node in self._op_nodes():
            deg = len(self._direct_preds(node))
            self._in_degree[node] = deg
            if deg == 0:
                self._pending_nodes.append(node)

    def _op_nodes(self):
        """Returns DAG nodes."""
        return self.dag.op_nodes()

    def _direct_preds(self, node):
        """Returns direct predecessors of a node."""
        if self._collect_from_back:
            return [
                pred
                for pred in self.dag.successors(node)
                if isinstance(pred, DAGOpNode)
            ]
        else:
            return [
                pred
                for pred in self.dag.predecessors(node)
                if isinstance(pred, DAGOpNode)
            ]

    def _direct_succs(self, node):
        """Returns direct successors of a node."""
        if self._collect_from_back:
            return [
                succ
                for succ in self.dag.predecessors(node)
                if isinstance(succ, DAGOpNode)
            ]
        else:
            return [
                succ
                for succ in self.dag.successors(node)
                if isinstance(succ, DAGOpNode)
            ]

    def _have_uncollected_nodes(self):
        """Returns whether there are uncollected (pending) nodes."""
        return len(self._pending_nodes) > 0

    def collect_matching_block(self, filter_fn):
        """Collects the largest block that matches the filter function."""
        current_block = []
        unprocessed_pending_nodes = self._pending_nodes
        self._pending_nodes = []

        # Iteratively process unprocessed_pending_nodes:
        # - any node that does not match filter_fn is added to pending_nodes
        # - any node that match filter_fn is added to the current_block, and
        # some of its successors may be moved to unprocessed_pending_nodes.
        while unprocessed_pending_nodes:
            new_pending_nodes = []
            for node in unprocessed_pending_nodes:
                if filter_fn(node):
                    current_block.append(node)

                    # update the _in_degree of node's successors
                    for suc in self._direct_succs(node):
                        self._in_degree[suc] -= 1
                        if self._in_degree[suc] == 0:
                            new_pending_nodes.append(suc)
                else:
                    self._pending_nodes.append(node)
            unprocessed_pending_nodes = new_pending_nodes

        return current_block

    def collect_all_matching_blocks(
        self,
        filter_fn,
        split_blocks=True,
        min_block_size=2,
        collect_from_back=False,
    ):
        """Collects all blocks that match a given filtering function filter_fn.

        This iteratively finds the largest block that does not match filter_fn,
        then the largest block that matches filter_fn, and so on, until no
        more uncollected nodes remain. Intuitively, finding larger blocks of
        non-matching nodes helps to find larger blocks of matching nodes later
        on.

        Args:
            filter_fn : the filter function.
            split_blocks (bool, optional): If true, split collected blocks into
                sub-blocks over disjoint qubit subsets. Defaults to True.
            min_block_size (int, optional): the minimum number of gates in the
                block for the block to be collected. Defaults to 2.
            collect_from_back (bool, optional): collect blocks from the outputs
                towards the inputs of the circuit. Defaults to False.
        """

        def not_filter_fn(node):
            """Returns the opposite of filter_fn."""
            return not filter_fn(node)

        # the collection direction must be specified before setting in-degrees
        self._collect_from_back = collect_from_back
        self._setup_in_degrees()

        # Iteratively collect non-matching and matching blocks.
        matching_blocks = []
        while self._have_uncollected_nodes():
            self.collect_matching_block(not_filter_fn)
            matching_block = self.collect_matching_block(filter_fn)
            if matching_block:
                matching_blocks.append(matching_block)

        # If the option split_blocks is set, refine blocks by splitting them
        # into sub-blocks over disconnected qubit subsets.
        if split_blocks:
            tmp_blocks = []
            for block in matching_blocks:
                tmp_blocks.extend(BlockSplitter().run(block))
            matching_blocks = tmp_blocks

        # If we are collecting from the back, both the order of the blocks
        # and the order of nodes in each block should be reversed.
        if self._collect_from_back:
            matching_blocks = [block[::-1] for block in matching_blocks[::-1]]

        # Keep only blocks with at least min_block_sizes.
        matching_blocks = [
            block for block in matching_blocks if len(block) >= min_block_size
        ]

        return matching_blocks


class BlockSplitter:
    """Splits a block of nodes into sub-blocks over disjoint qubits.

    The implementation is based on the Disjoint Set Union data structure.
    """

    def __init__(self):
        """Initialize DSU data structures."""
        # qubit's group leader
        self.leader = {}
        # qubit's group
        self.group = {}

    def find_leader(self, index: int):
        """Find leader in DSU.

        Args:
            index (int): bit index to find.

        Returns:
            int: leader qubit index.
        """
        # if qubit not in leader dict, initialize it
        if index not in self.leader:
            self.leader[index] = index
            self.group[index] = []
            return index
        # if already leader
        if self.leader[index] == index:
            return index
        # recursive find
        self.leader[index] = self.find_leader(self.leader[index])
        return self.leader[index]

    def union_leaders(self, index1, index2):
        """Union in DSU.

        Args:
            index1 (int): First qubit index.
            index2 (int): Second qubit index.
        """
        leader1 = self.find_leader(index1)
        leader2 = self.find_leader(index2)
        if leader1 == leader2:
            return
        if len(self.group[leader1]) < len(self.group[leader2]):
            leader1, leader2 = leader2, leader1

        self.leader[leader2] = leader1
        self.group[leader1].extend(self.group[leader2])
        self.group[leader2].clear()

    def run(self, block):
        """Splits block of nodes into sub-blocks over disjoint qubits.

        Args:
            block (list): List of nodes to split.

        Returns:
            list: List of sub-blocks, each containing nodes acting on connected
                qubit sets.
        """
        # process all nodes, build connectivity
        for node in block:
            indices = node.qargs
            if not indices:
                continue
            first = indices[0]
            for index in indices[1:]:
                # merge all qubits involved in this node into same set
                self.union_leaders(first, index)
            leader = self.find_leader(first)
            self.group[leader].append(node)

        blocks = []
        for index, value in self.leader.items():
            if value == index:
                blocks.append(self.group[index])

        return blocks
