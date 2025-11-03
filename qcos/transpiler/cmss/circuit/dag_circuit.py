#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from collections import OrderedDict
from collections.abc import Generator
from typing import Any
import rustworkx as rx

from qcos.transpiler.cmss.circuit.dag_node import (
    DAGOpNode,
    DAGInNode,
    DAGOutNode,
)


class DAGCircuit:
    """
    Quantum circuit as a directed acyclic graph.

    There are 3 types of nodes in the graph: inputs, outputs, and operations.
    The nodes are connected by directed edges that correspond to qubits.
    """

    def __init__(self):
        """Create an empty circuit."""
        self.name = None

        # Set of wires idx in the dag
        self._wires = set()

        # Map from wire idx to input nodes of the graph
        self.input_map = OrderedDict()

        # Map from wire idx to output nodes of the graph
        self.output_map = OrderedDict()

        # DAG Graph
        self._multi_graph = rx.PyDAG()

        # List of qubit wires that the DAG acts on.
        self.qubits: list[int] = []

        # counts of gates
        self._op_names = {}

    @property
    def wires(self):
        """Return a list of the wires in order."""
        return self.qubits

    @property
    def node_counter(self):
        """
        Returns the number of nodes in the dag.
        """
        return len(self._multi_graph)

    def add_qubits(self, num_qubits):
        """
        Add qubit wires.

        Args:
            num_qubits (int): number of qubits
        """
        for qubit in range(num_qubits):
            self.qubits.append(qubit)
            self._add_wire(qubit)

    def _add_wire(self, wire):
        """Add a qubit to the circuit.

        Args:
            wire (int): the wire to be added
        """
        if wire not in self._wires:
            self._wires.add(wire)
            inp_node = DAGInNode(wire=wire)
            outp_node = DAGOutNode(wire=wire)

            input_map_id, output_map_id = self._multi_graph.add_nodes_from(
                [inp_node, outp_node]
            )
            inp_node._node_id = input_map_id
            outp_node._node_id = output_map_id
            self.input_map[wire] = inp_node
            self.output_map[wire] = outp_node
            self._multi_graph.add_edge(
                inp_node._node_id, outp_node._node_id, wire
            )
        else:
            raise ValueError(f"duplicate wire {wire}")

    def _increment_op(self, op):
        """Increase the count of a given operation.

        Args:
            op: an operation, can be `GateOperation`.
        """
        if op.name in self._op_names:
            self._op_names[op.name] += 1
        else:
            self._op_names[op.name] = 1

    def _decrement_op(self, op):
        """Decrease the count of a given operation.

        Args:
            op: an operation, can be `GateOperation`.
        """
        if self._op_names[op.name] == 1:
            del self._op_names[op.name]
        else:
            self._op_names[op.name] -= 1

    def apply_operation_back(self, op, qargs=None):
        """Apply an operation/gate to the output of the circuit.

        Args:
            op: the operation associated with the DAG node
            qargs: qubits that op will be applied to,
                GateOperation has targets, so qargs can be None.
        Returns:
            DAGOpNode: the node for the op that was added to the dag
        """
        if qargs is None:
            qargs = op.targets
        node = DAGOpNode(op=op, qargs=qargs)
        node._node_id = self._multi_graph.add_node(node)
        self._increment_op(op)

        self._multi_graph.insert_node_on_in_edges_multiple(
            node._node_id,
            [self.output_map[int(bit)]._node_id for bit in qargs],
        )
        return node

    def size(self):
        """Return the number of operations.

        Returns:
            int: the circuit size
        """
        length = len(self._multi_graph) - 2 * len(self._wires)
        return length

    def depth(self):
        """Return the circuit depth.

        Returns:
            int: the circuit depth
        """
        depth = rx.dag_longest_path_length(self._multi_graph) - 1
        return depth if depth >= 0 else 0

    def width(self):
        """Return the total number of qubits used by the circuit."""
        return len(self._wires)

    def topological_nodes(self, key=None):
        """
        Yield nodes in topological order.

        Args:
            key (Callable): A callable which will take a DAGNode object and
                return a string sort key. If not specified the
                :attr:`~.DAGNode.sort_key` attribute will be used as the
                sort key for each node.

        Returns:
            generator(DAGNode): node in topological order
        """

        def _key(x):
            return x.sort_key

        if key is None:
            key = _key

        return iter(
            rx.lexicographical_topological_sort(self._multi_graph, key=key)
        )

    def topological_op_nodes(self, key=None) -> Generator[DAGOpNode, Any, Any]:
        """
        Yield op nodes in topological order.

        Allowed to pass in specific key to break ties in top order

        Args:
            key (Callable): A callable which will take a DAGNode object and
                return a string sort key. If not specified the
                :attr:`~.DAGNode.sort_key` attribute will be used as the
                sort key for each node.

        Returns:
            generator(DAGOpNode): op node in topological order
        """
        return (
            nd
            for nd in self.topological_nodes(key)
            if isinstance(nd, DAGOpNode)
        )

    def node(self, node_id):
        """Get the node in the dag.

        Args:
            node_id(int): Node identifier.

        Returns:
            node: the node.
        """
        return self._multi_graph[node_id]

    def nodes(self):
        """Iterator for node values.

        Yield:
            node: the node.
        """
        yield from self._multi_graph.nodes()

    def op_nodes(self):
        """Get the list of "op" nodes in the dag.

        Returns:
            list[DAGOpNode]: the list of op node.
        """
        nodes = []
        for node in self._multi_graph.nodes():
            if isinstance(node, DAGOpNode):
                nodes.append(node)
        return nodes

    def two_qubit_ops(self):
        """Get list of 2 qubit operations."""
        ops = []
        for node in self.op_nodes():
            if len(node.qargs) == 2:
                ops.append(node)
        return ops

    def multi_qubit_ops(self):
        """Get list of 3+ qubit operations."""
        ops = []
        for node in self.op_nodes():
            if len(node.qargs) >= 3:
                ops.append(node)
        return ops

    def longest_path(self):
        """Returns the longest path in the dag as a list of DAGNodes."""
        return [
            self._multi_graph[x]
            for x in rx.dag_longest_path(self._multi_graph)
        ]

    def successors(self, node):
        """Returns iterator of the successors of a node as DAGNodes."""
        return iter(self._multi_graph.successors(node._node_id))

    def predecessors(self, node):
        """Returns iterator of the predecessors of a node as DAGNodes."""
        return iter(self._multi_graph.predecessors(node._node_id))

    def is_successor(self, node, node_succ):
        """Checks if a second node is in the successors of node."""
        return self._multi_graph.has_edge(node._node_id, node_succ._node_id)

    def is_predecessor(self, node, node_pred):
        """Checks if a second node is in the predecessors of node."""
        return self._multi_graph.has_edge(node_pred._node_id, node._node_id)

    def remove_op_node(self, node):
        """Remove an operation node n.

        Add edges from predecessors to successors.
        """
        if not isinstance(node, DAGOpNode):
            raise ValueError(
                f"The method remove_op_node only works on DAGOpNodes."
                f"A {type(node)} node type was wrongly provided."
            )

        self._multi_graph.remove_node_retain_edges(
            node._node_id,
            use_outgoing=False,
            condition=lambda edge1, edge2: edge1 == edge2,
        )
        self._decrement_op(node.op)

    def count_ops(self):
        """Count the occurrences of operation names.

        Returns:
            Mapping[str, int]: a mapping of operation names to
                the number of times it appears.
        """
        return self._op_names.copy()

    @classmethod
    def ir_to_dag(cls, ir: list):
        """Convert IR to DAGCircuit.

        Args:
            ir (list): gates list.

        Returns:
            DAGCircuit: DAGCircuit corresponding to IR.
        """
        dag_circuit = DAGCircuit()

        # count the number of qubits
        tmp_qubits = set()
        for gate in ir:
            tmp_qubits.update(gate.targets)
        num_qubits = max(int(x) for x in tmp_qubits) + 1

        dag_circuit.add_qubits(num_qubits)
        # Add gates to the DAG
        for gate in ir:
            dag_circuit.apply_operation_back(gate)
        return dag_circuit
