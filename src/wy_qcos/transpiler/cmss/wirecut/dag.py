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
from wy_qcos.transpiler.cmss.circuit.register import QuantumRegister
from wy_qcos.transpiler.cmss.compiler.parser import Parser


class DAG:
    """DAG class."""

    def __init__(self, parser: Parser):
        """Init DAG class.

        Args:
            parser (Parser): parser
        """
        # opt_circuit represents the preprocessed circuit
        self.opt_circuit = parser.opt_circuit
        # The input circuit from the user is arbitrary and needs to be
        # preprocessed into a circuit consisting only of single-qubit gates
        # and two-qubit gates.
        self.opt_dag = DAGCircuit.ir_to_dag(self.opt_circuit)
        # Directed acyclic graphs containing only two-bit gates
        self.knit_dag = self.opt_dag.two_qubit_ops_to_dag()

    def knit_dag_to_graph(self):
        """Convert the DAG into a graph structure as input for the MIP module.

        Returns:
            nvertex (int): Number of nodes
            edge_list (List[List[int, int]]): Edge list
        """
        topo_nodes = list(self.knit_dag.topological_op_nodes())
        # Generate a mapping between nodes and sequence numbers
        node_dict = {node: idx for idx, node in enumerate(topo_nodes)}
        # Get the number of nodes
        nvertex = len(node_dict)
        # Generate edge list (only operates on connections between nodes)
        edge_list = []
        for edge in self.knit_dag.edges():
            src = edge[0]
            dest = edge[1]
            if isinstance(src, DAGOpNode) and isinstance(dest, DAGOpNode):
                edge_list.append([node_dict[src], node_dict[dest]])
        return nvertex, edge_list

    def parse_subgraphs(self, subgraphs):
        """Converte list of subgraphs into list of strings in specific format.

        Args:
            subgraphs (List[List[int]]): Subgraph list

        Returns:
            List[List[str]]: List of strings corresponding to cutting scheme
        """
        # Get the list of nodes after topological sorting
        topo_nodes = list(self.knit_dag.topological_op_nodes())
        depth_dict = self.get_knit_dag_depth(topo_nodes)
        # Generate mapping between nodes and sequence numbers
        node_dict = dict(enumerate(topo_nodes))
        result = []
        for subgraph in subgraphs:
            lst = []
            for node_id in subgraph:
                node = node_dict[node_id]
                global_indices = [
                    self.knit_dag.qubits.index(q) for q in node.qargs
                ]
                graph_qubits = (
                    f"q[{global_indices[0]}]"
                    f"{depth_dict[node_id][global_indices[0]]} "
                    f"q[{global_indices[1]}]"
                    f"{depth_dict[node_id][global_indices[1]]}"
                )
                lst.append(graph_qubits)
            result.append(lst)
        return result

    def get_knit_dag_depth(self, topo_nodes):
        """Obtain depth information for all gates in the DAG.

        Returns:
            depth_dict (Dict[int, Dict[int, int]]): Deep Information Dictionary
        """
        # Get the indices of all qubits and sort them to ensure determinism
        qubit_indices = sorted(self.knit_dag.qubits)
        # Initialize the current depth of each qubit to 0
        current_depth = {qubit: 0 for qubit in qubit_indices}
        depth_dict = {}
        # Traverse all nodes in topological order
        for node_id, node in enumerate(topo_nodes):
            # Record the depth of the current node on each qubit
            node_depth = {}
            # Traverse all quantum bits affected by the current node
            for qubit in node.qargs:
                qubit_index = qubit
                if qubit_index in qubit_indices:
                    # Record the current node's depth on this qubit
                    node_depth[qubit_index] = current_depth[qubit_index]
                    # Update the depth of this qubit
                    current_depth[qubit_index] += 1
            # Depth information of storage nodes
            depth_dict[node_id] = node_depth
        return depth_dict

    def split_dag(self, cut_positions):
        """Split the DAG into multiple sub-DAGs according to cutting positions.

        Args:
            cut_positions (List[int]): List of cutting positions

        Returns:
            List[DAGCircuit]: List of sub DAGs after cutting
        """
        if not cut_positions:
            return [self.knit_dag]
        cut_positions = sorted(cut_positions)
        if cut_positions[-1] >= len(list(self.knit_dag.two_qubit_ops())):
            raise ValueError(
                "The cutting position exceeds the total number of "
                "circuit gates."
            )
        sub_dags = []
        start_idx = 0
        two_qubit_nodes = list(self.knit_dag.two_qubit_ops())
        for cut_pos in cut_positions + [len(two_qubit_nodes)]:
            sub_dag = DAGCircuit()
            used_qubits = set()
            for node in two_qubit_nodes[start_idx:cut_pos]:
                for qarg in node.qargs:
                    used_qubits.add(qarg)
            if used_qubits:
                qreg = QuantumRegister(len(self.knit_dag.qregs["q"]), "q")
                sub_dag.add_qreg(qreg)
                for node in two_qubit_nodes[start_idx:cut_pos]:
                    sub_dag.apply_operation_back(node.op, node.qargs)
                sub_dags.append(sub_dag)
            start_idx = cut_pos
        return sub_dags

    def add_single_qubit_gates(self, sub_dags):
        """Add single-bit gate operations to each sub DAG.

        Args:
            sub_dags (List[DAGCircuit]): Sub-DAG list containing two-bit gates.

        Returns:
            List[DAGCircuit]: List of sub DAGs after adding single-qubit gates.
        """
        # Retrieve all operational nodes of the original DAG
        original_nodes = list(self.opt_dag.topological_op_nodes())
        # Obtain the index positions of two-qubit gates in the original DAG
        two_qubit_indices = [
            i for i, node in enumerate(original_nodes) if len(node.qargs) == 2
        ]
        complete_sub_dags = []
        start_idx = 0
        for sub_dag in sub_dags:
            new_dag = DAGCircuit()
            new_dag.add_qreg(self.opt_dag.qregs["q"])
            # Get the number of two-qubit gates in the current sub-DAG
            sub_dag_two_qubit_count = len(list(sub_dag.two_qubit_ops()))
            # Get all operations within this range (including single-bit
            # and two-bit operations)
            if start_idx == 0:
                start_pos = 0
            else:
                start_pos = two_qubit_indices[start_idx - 1] + 1
            # Modify the calculation logic for the end position
            if start_idx + sub_dag_two_qubit_count >= len(two_qubit_indices):
                # If it is the last sub DAG, use all remaining nodes
                end_pos = len(original_nodes)
            else:
                end_pos = (
                    two_qubit_indices[start_idx + sub_dag_two_qubit_count - 1]
                    + 1
                )
            # Add all gates within this range
            for node in original_nodes[start_pos:end_pos]:
                new_dag.apply_operation_back(node.op, node.qargs)
            complete_sub_dags.append(new_dag)
            start_idx += sub_dag_two_qubit_count
        return complete_sub_dags

    def to_tuple_representation(self):
        """Convert DAG to tuple representation.

        Returns:
            int: vertex
            List[Tuple[int, int]]: edges
            Dict[Operation, int]: op_to_vertex
        """
        two_qubit_nodes = list(self.knit_dag.two_qubit_ops())
        vertex = len(two_qubit_nodes)
        node_to_vertex = {
            id(node): idx for idx, node in enumerate(two_qubit_nodes)
        }
        edges = []
        last_vertex_on_qubit = {}
        for node in two_qubit_nodes:
            current_vertex = node_to_vertex[id(node)]
            for qarg in node.qargs:
                if qarg in last_vertex_on_qubit:
                    edges.append((last_vertex_on_qubit[qarg], current_vertex))
                last_vertex_on_qubit[qarg] = current_vertex
        op_to_vertex = {}
        for node in two_qubit_nodes:
            op_to_vertex[id(node.op)] = node_to_vertex[id(node)]
        all_nodes = list(self.opt_dag.topological_op_nodes())

        # Find the corresponding two-qubit gate vertex for single-qubit gate
        current_two_qubit_idx = 0
        for node in all_nodes:
            if len(node.qargs) == 1:
                target_qubit = node.qargs[0]
                found = False
                for i in range(current_two_qubit_idx, len(two_qubit_nodes)):
                    two_q_node = two_qubit_nodes[i]
                    if target_qubit in two_q_node.qargs:
                        op_to_vertex[id(node.op)] = node_to_vertex[
                            id(two_q_node)
                        ]
                        found = True
                        break
                if not found and target_qubit in last_vertex_on_qubit:
                    op_to_vertex[id(node.op)] = last_vertex_on_qubit[
                        target_qubit
                    ]
            else:
                current_two_qubit_idx += 1
        return vertex, edges, op_to_vertex
