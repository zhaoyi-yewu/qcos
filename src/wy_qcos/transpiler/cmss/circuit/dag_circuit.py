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

from collections import OrderedDict
from collections.abc import Generator
from typing import Any
import rustworkx as rx
import numpy as np

from wy_qcos.transpiler.cmss.circuit.dag_node import (
    DAGOpNode,
    DAGInNode,
    DAGOutNode,
    DAGNode,
)
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation
from wy_qcos.transpiler.cmss.common.gate_operation import create_gate


class DAGCircuit:
    """Quantum circuit as a directed acyclic graph.

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
        """Returns the number of nodes in the dag."""
        return len(self._multi_graph)

    def add_qubits(self, num_qubits):
        """Add qubit wires.

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

            input_map_id, output_map_id = self._multi_graph.add_nodes_from([
                inp_node,
                outp_node,
            ])
            inp_node._node_id = input_map_id
            outp_node._node_id = output_map_id
            self.input_map[wire] = inp_node
            self.output_map[wire] = outp_node
            self._multi_graph.add_edge(
                inp_node._node_id, outp_node._node_id, wire
            )
        else:
            raise ValueError(f"duplicate wire {wire}")

    def rename_op(self, old_op: GateOperation, new_op: GateOperation):
        """Convert between Rz and T,Z,S gates.

        Args:
            old_op (GateOperation): decrease old_op count.
            new_op (GateOperation): increase new_op count.
        """
        phase_gates = ["s", "sdg", "t", "tdg", "z"]
        if not (old_op.name == "rz" and new_op.name in phase_gates) and not (
            new_op.name == "rz" and old_op.name in phase_gates
        ):
            raise ValueError(
                f"can not convert {old_op.name} to {new_op.name}."
            )
        if self._op_names.get(old_op.name, 0) > 0:
            self._decrement_op(old_op)
            self._increment_op(new_op)
        else:
            raise ValueError(f"no {old_op.name} in the dag.")

    def parameterize_all(self):
        """Convert all T/Tdg/S/Sdg/Z into Rz gates."""
        para_rule = {
            "s": np.pi / 2,
            "t": np.pi / 4,
            "sdg": -np.pi / 2,
            "tdg": -np.pi / 4,
            "z": np.pi,
        }

        for node in self.topological_op_nodes():
            if node.name in ["s", "t", "sdg", "tdg", "z"]:
                old_op = node.op
                new_op = create_gate(
                    "rz",
                    targets=node.op.targets,
                    arg_value=[para_rule[node.name]],
                )
                self.rename_op(old_op, new_op)
                node.op = new_op
                node.name = "rz"

    def deparameterize_all(self):
        """Convert all Rz gates into T/Tdg/S/Sdg/Z."""
        depara_rule = {
            0: ["id"],
            1: ["t"],
            2: ["s"],
            3: ["s", "t"],
            4: ["z"],
            5: ["z", "t"],
            6: ["sdg"],
            7: ["tdg"],
        }
        for node in self.topological_op_nodes():
            if node.name == "rz":
                times = np.mod(node.op.arg_value[0], 2 * np.pi) / (np.pi / 4)
                if not np.isclose(round(times), times, rtol=0):
                    continue
                g_list = depara_rule[round(times) % 8]
                if len(g_list) > 1:
                    continue
                if g_list[0] == "id":
                    self.remove_op_node(node)
                    continue
                old_op = node.op
                new_op = create_gate(
                    g_list[0], targets=node.op.targets, arg_value=[]
                )
                self.rename_op(old_op, new_op)
                node.op = new_op
                node.name = g_list[0]

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

    def apply_operation_front(self, op, qargs=None, cargs=None) -> DAGOpNode:
        """Apply an operation to the input of the circuit.

        Args:
            op: the operation associated with the DAG node
            qargs: qubits that op will be applied to
            cargs (tuple[Clbit]): cbits that op will be applied to

        Returns:
            DAGOpNode: the node for the op that was added to the dag
        """
        if qargs is None:
            qargs = op.targets
        node = DAGOpNode(op=op, qargs=qargs)
        node._node_id = self._multi_graph.add_node(node)
        self._increment_op(op)

        self._multi_graph.insert_node_on_out_edges_multiple(
            node._node_id,
            [self.input_map[int(bit)]._node_id for bit in qargs],
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

    def nodes_on_wire(self, wire, only_ops=False):
        """Iterator for nodes that affect a given wire.

        Args:
            wire (Bit): the wire to be looked at.
            only_ops (bool): True if only the ops nodes are wanted;
                        otherwise, all nodes are returned.

        Yield:
            Iterator: the successive nodes on the given wire

        Raises:
            ValueError: if the given wire doesn't exist in the DAG
        """
        current_node = self.input_map.get(wire, None)
        if not current_node:
            raise ValueError(
                f"The given wire {str(wire)} is not present in the circuit"
            )

        more_nodes = True
        while more_nodes:
            more_nodes = False
            # allow user to just get ops on the wire - not input/output nodes
            if isinstance(current_node, DAGOpNode) or not only_ops:
                yield current_node

            try:
                current_node = self._multi_graph.find_adjacent_node_by_edge(
                    current_node._node_id, lambda x: wire == x
                )
                more_nodes = True
            except rx.NoSuitableNeighbors:
                pass

    def topological_nodes(self, key=None):
        """Yield nodes in topological order.

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
        """Yield op nodes in topological order.

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

    def ancestors(self, node):
        """Returns set of the ancestors of a node."""
        return {
            self._multi_graph[x]
            for x in rx.ancestors(self._multi_graph, node._node_id)
        }

    def descendants(self, node):
        """Returns set of the descendants of a node."""
        return {
            self._multi_graph[x]
            for x in rx.descendants(self._multi_graph, node._node_id)
        }

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

    def collect_runs(self, namelist):
        """Return a set of runs of "op" nodes with the given names.

        For example, "... h q[0]; cx q[0],q[1]; cx q[0],q[1]; h q[1]; .."
        would produce the tuple of cx nodes as an element of the set returned
        from a call to collect_runs(["cx"]). If instead the cx nodes were
        "cx q[0],q[1]; cx q[1],q[0];", the method would still return the
        pair in a tuple. The namelist can contain names that are not
        in the circuit's basis.

        Nodes must have only one successor to continue the run.
        """

        def filter_fn(node):
            return isinstance(node, DAGOpNode) and node.op.name in namelist

        group_list = rx.collect_runs(self._multi_graph, filter_fn)
        return {tuple(x) for x in group_list}

    def count_ops(self):
        """Count the occurrences of operation names.

        Returns:
            Mapping[str, int]: a mapping of operation names to
                the number of times it appears.
        """
        return self._op_names.copy()

    def replace_block_with_op(
        self, node_block: list[DAGNode], op, cycle_check=True
    ):
        """Replace a block of nodes with a single node.

        Args:
            node_block (list[DAGNode]): A list of dag nodes that represents the
                node block to be replaced
            op (GateOperation): The operation to replace the block with.
            cycle_check (bool, optional): check that replacing with a single
                node would introduce a cycle. Defaults to True.

        Returns:
            DAGOpNode: The op node that replaces the block.
        """
        block_qargs = set()
        block_ids = [x._node_id for x in node_block]

        # If node block is empty return early
        if not node_block:
            raise ValueError("Can't replace an empty node_block")

        for nd in node_block:
            if isinstance(nd, DAGOpNode):
                block_qargs |= set(nd.qargs)

        new_node = DAGOpNode(op, block_qargs)

        try:
            new_node._node_id = self._multi_graph.contract_nodes(
                block_ids, new_node, check_cycle=cycle_check
            )
        except rx.DAGWouldCycle as ex:
            raise ValueError(
                "Replacing the specified node block would introduce a cycle"
            ) from ex

        self._increment_op(op)

        for nd in node_block:
            if isinstance(nd, DAGOpNode):
                self._decrement_op(nd.op)

        return new_node

    def substitute_node_with_dag(self, node: DAGOpNode, input_dag, wires=None):
        """Replace one node with dag.

        Args:
            node (DAGOpNode): node to substitute.
            input_dag (DAGCircuit): circuit that will substitute the node.
            wires (list | dict): gives an order for qubits in the input
                circuit. Defaults to None.

        Returns:
            dict: maps node IDs from input_dag to their new node in self.
        """
        if not isinstance(node, DAGOpNode):
            raise ValueError(f"expected node DAGOpNode, got {type(node)}")

        if isinstance(wires, dict):
            wire_map = wires
        else:
            wires = input_dag.wires if wires is None else wires
            node_wire_order = list(node.qargs)

            if len(wires) != len(node_wire_order):
                raise ValueError(
                    f"bit mapping invalid: expected {len(node_wire_order)}, \
                        got {len(wires)}"
                )
            wire_map = dict(zip(wires, node_wire_order))
            if len(wire_map) != len(node_wire_order):
                raise ValueError(
                    "bit mapping invalid: some bits have duplicate entries"
                )
        for _, our_wire in wire_map.items():
            if our_wire not in self.input_map:
                raise ValueError(
                    f"bit mapping invalid: {our_wire} is not in this DAG"
                )

        reverse_wire_map = {b: a for a, b in wire_map.items()}
        in_dag = input_dag

        # Add wire from pred to succ if no ops on mapped wire on in_dag
        for in_dag_wire, self_wire in wire_map.items():
            input_node = in_dag.input_map[in_dag_wire]
            output_node = in_dag.output_map[in_dag_wire]
            if in_dag._multi_graph.has_edge(
                input_node._node_id, output_node._node_id
            ):
                pred = self._multi_graph.find_predecessors_by_edge(
                    node._node_id, lambda edge, wire=self_wire: edge == wire
                )[0]
                succ = self._multi_graph.find_successors_by_edge(
                    node._node_id, lambda edge, wire=self_wire: edge == wire
                )[0]
                self._multi_graph.add_edge(
                    pred._node_id, succ._node_id, self_wire
                )

        # Exclude any nodes from in_dag that are not a DAGOpNode or are on
        # bits outside the set specified by the wires kwarg
        def filter_fn(node):
            if not isinstance(node, DAGOpNode):
                return False
            for qarg in node.qargs:
                if qarg not in wire_map:
                    return False
            return True

        # Map edges into and out of node to the appropriate node from in_dag
        def edge_map_fn(source, _target, self_wire):
            wire = reverse_wire_map[self_wire]
            # successor edge
            if source == node._node_id:
                wire_output_id = in_dag.output_map[wire]._node_id
                out_index = in_dag._multi_graph.predecessor_indices(
                    wire_output_id
                )[0]
                # Edge directly from input nodes to output nodes in in_dag are
                # already handled prior to calling rustworkx. Don't map these
                # edges in rustworkx.
                if not isinstance(in_dag._multi_graph[out_index], DAGOpNode):
                    return None
            # predecessor edge
            else:
                wire_input_id = in_dag.input_map[wire]._node_id
                out_index = in_dag._multi_graph.successor_indices(
                    wire_input_id
                )[0]
                # Edge directly from input nodes to output nodes in in_dag are
                # already handled prior to calling rustworkx. Don't map these
                # edges in rustworkx.
                if not isinstance(in_dag._multi_graph[out_index], DAGOpNode):
                    return None
            return out_index

        # Adjust edge weights from in_dag
        def edge_weight_map(wire):
            return wire_map[wire]

        node_map = self._multi_graph.substitute_node_with_subgraph(
            node._node_id,
            in_dag._multi_graph,
            edge_map_fn,
            filter_fn,
            edge_weight_map,
        )
        self._decrement_op(node.op)

        # Iterate over nodes of input_circuit and update wires in node objects
        # migrated from in_dag
        for old_node_index, new_node_index in node_map.items():
            # update node attributes
            old_node = in_dag._multi_graph[old_node_index]
            m_op = old_node.op

            m_qargs = [wire_map[x] for x in old_node.qargs]
            m_cargs = [wire_map[x] for x in old_node.cargs]
            new_node = DAGOpNode(m_op, qargs=m_qargs, cargs=m_cargs)
            new_node._node_id = new_node_index
            self._multi_graph[new_node_index] = new_node
            self._increment_op(new_node.op)

        return {k: self._multi_graph[v] for k, v in node_map.items()}

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

    @classmethod
    def circuit_to_dag(cls, circ: QuantumCircuit):
        """Convert QuantumCircuit to DAGCircuit.

        Args:
            circ (QuantumCircuit): quantum circuit.

        Returns:
            DAGCircuit: DAGCircuit corresponding to circuit.
        """
        dag_circuit = DAGCircuit()

        # count the number of qubits
        tmp_qubits = set()
        for gate in circ.get_operations():
            tmp_qubits.update(gate.targets)
        num_qubits = max(int(x) for x in tmp_qubits) + 1

        dag_circuit.add_qubits(num_qubits)
        # Add gates to the DAG
        for gate in circ.get_operations():
            dag_circuit.apply_operation_back(gate)
        return dag_circuit

    def dag_to_circuit(self, num_qubits: int = 0):
        """Convert DAG to QuantumCircuit.

        Args:
            num_qubits (int): number of qubits in the circuit.

        Returns:
            QuantumCircuit: QuantumCircuit corresponding to DAG.
        """
        if num_qubits > 0:
            circ = QuantumCircuit(num_qubits)
        else:
            circ = QuantumCircuit()
        gate_list = []
        for node in self.topological_op_nodes():
            if isinstance(node, DAGOpNode):
                gate_list.append(node.op)
        circ.append_operations(gate_list)
        return circ

    def get_multi_graph(self):
        """Get DAG Graph.

        Returns:
            rx.PyDAG: DAG Graph
        """
        return self._multi_graph

    def two_qubit_ops_to_dag(self):
        """Convert two-qubit gates operations into a DAG.

        Returns:
            DAGCircuit: Directed acyclic graph containing two-bit gates.
        """
        new_dag = DAGCircuit()
        new_dag.add_qubits(len(self.qubits))
        # Traverse DAG's two-qubit gates and add them to the new DAG
        for node in self.two_qubit_ops():
            new_dag.apply_operation_back(node.op)
        return new_dag

    def edges(self, nodes=None):
        """Iterator for edge values and source and dest node.

        Args:
            nodes (DAGOpNode, DAGInNode, or DAGOutNode | list):
                Either a list of nodes or a single input node.

        Yield:
            edge: the edge in the same format as out_edges the tuple
                (source node, destination node, edge data).
        """
        if nodes is None:
            nodes = self._multi_graph.nodes()

        elif isinstance(nodes, (DAGOpNode, DAGInNode, DAGOutNode)):
            nodes = [nodes]
        for node in nodes:
            raw_nodes = self._multi_graph.out_edges(node._node_id)
            for source, dest, edge in raw_nodes:
                yield (
                    self._multi_graph[source],
                    self._multi_graph[dest],
                    edge,
                )
