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

import networkx as nx
from networkx import DiGraph
from networkx.algorithms import approximation as approx

from wy_qcos.transpiler.cmss.common.gate_operation import (
    create_gate,
)
from wy_qcos.transpiler.cmss.compiler.parser import (
    get_abs_tree,
    get_ir,
)
from wy_qcos.transpiler.cmss.mapping.utils.front_circuit import FrontCircuit
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


class DG(DiGraph):
    """Topology analysis and construction of a dependency graph."""

    def __init__(
        self,
    ):
        super().__init__()
        self.qubit_to_node = [None] * 500
        self.num_gate_2q = 0
        self.num_gate_1q = 0
        self.node_count = 0
        self.num_q = None
        self.origin_ir = None

    @property
    def num_gate(self):
        return self.num_gate_1q + self.num_gate_2q

    def get_shared_qubits(self, node1: int, node2: int):
        """Get qubits which exist in both node1 and node2.

        Args:
            node1 (int): id of node1
            node2 (int): id of node2

        Returns:
            list[int]: shared qubits list
        """
        qubits = []
        for q in self.get_node_qubits(node1):
            if q in self.get_node_qubits(node2):
                qubits.append(q)
        return qubits

    def add_line(self, node_in: int, node_out: int, qubits=None):
        """Connect two nodes using provided qubits.

        Args:
            node_in (int): id of node_in
            node_out (int): id of node_out
            qubits (list, optional): specified target. Defaults to None.
        """
        qubits_share = self.get_shared_qubits(node_in, node_out)
        qubits_used = []
        for edge_c in self.out_edges(node_in):
            qubits_used.extend(self.get_edge_qubits(edge_c))
        for edge_c in self.in_edges(node_out):
            qubits_used.extend(self.get_edge_qubits(edge_c))
        qubits_share_new = []
        for q in qubits_share:
            if q not in qubits_used:
                qubits_share_new.append(q)
        qubits_share = qubits_share_new

        if qubits is None:
            qubits = qubits_share
        edge_add = (node_in, node_out)
        if edge_add in self.edges:
            for q in qubits:
                if q not in self.edges[edge_add]["qubits"]:
                    self.edges[edge_add]["qubits"].append(q)
        else:
            self.add_edge(node_in, node_out, qubits=qubits)

    def add_multi_gates(self, gates: list, absorb=False):
        """Add multiple gates to the graph.

        Args:
            gates (list): list of gates
            absorb (bool, optional): Whether absorb the gate. Defaults to
                False.
        """
        for gate in gates:
            if absorb:
                self.add_gate_absorb(gate)
            else:
                self.add_gate(gate)

    def add_gate(self, format_gate: tuple, gate=None, add_edges=True):
        """Add a gate to the graph.

        Attributes of a node: gates, num_gate_1q, num_gate_2q, qubits.

        Args:
            format_gate (tuple): a tuple of (gate_name, (qubits), (parameters))
            gate(GateOperation): Gate Operation
            add_edges (bool, optional): wheater to add edges. Defaults to True.

        Returns:
            int: id of new node
        """
        # add node
        node_new = self.node_count
        self.node_count += 1
        self.add_node(node_new)
        self.nodes[node_new]["gate"] = [gate]
        self.nodes[node_new]["gates"] = [format_gate]
        self.nodes[node_new]["qubits"] = list(format_gate[1])
        (
            self.nodes[node_new]["num_gate_1q"],
            self.nodes[node_new]["num_gate_2q"],
        ) = (
            0,
            0,
        )
        if len(format_gate[1]) == 1:
            self.nodes[node_new]["num_gate_1q"] += 1
            self.num_gate_1q += 1
        if len(format_gate[1]) == 2:
            self.nodes[node_new]["num_gate_2q"] += 1
            self.num_gate_2q += 1
        if len(format_gate[1]) > 2:
            raise ValueError("more than 2 qubits")
        if add_edges:
            # add edges
            for q in format_gate[1]:
                node_parent = self.qubit_to_node[q]
                if node_parent is not None:
                    self.add_line(node_parent, node_new, [q])
                self.qubit_to_node[q] = node_new
        return node_new

    def get_dg_num_q(self):
        """Get the number of qubits in the dependency graph."""
        max_q = 0
        for node in self.nodes:
            # pylint: disable=unsubscriptable-object
            max_q = max(max_q, *self.nodes[node]["qubits"])
        self.num_q = max_q + 1
        return self.num_q

    def get_node_num_q(self, node):
        return len(self.nodes[node]["qubits"])

    def get_node_num_2q_gates(self, node):
        return self.nodes[node]["num_gate_2q"]

    def get_node_num_1q_gates(self, node):
        return self.nodes[node]["num_gate_1q"]

    def get_node_gates(self, node):
        return self.nodes[node]["gates"]

    def get_node_qubits(self, node):
        """Return the qubits associated with a node with robust type checks.

        This implementation accesses the underlying node data defensively and
        provides clear error messages if the node or expected attribute is not
        present or not in the expected format. It ensures the returned value
        is a list of qubits.
        """
        try:
            node_data = self.nodes[node]
        except Exception as exc:  # defensive: networkx node access may raise
            raise TypeError(f"无法访问节点 {node} 的数据: {exc}") from exc

        # Ensure node_data behaves like a mapping/dict
        if not isinstance(node_data, dict):
            try:
                node_data = dict(node_data)
            except Exception as exc:
                raise TypeError(
                    f"节点 {node} 的数据不可转换为 dict: {exc}"
                ) from exc

        if "qubits" not in node_data:
            raise KeyError(f"节点 {node} 缺少 'qubits' 属性")

        qubits = node_data["qubits"]
        if not isinstance(qubits, (list, tuple)):
            raise TypeError(f"节点 {node} 的 'qubits' 属性必须是列表或元组")

        # Normalize to list for callers
        return list(qubits)

    def get_node_depth(self, node: int):
        """Get depth of a node, one SWAP takes 3 depth.

        Args:
            node (int): id of a node

        Returns:
            int: depth of a node
        """
        qubit_depth = [0] * (max(self.get_node_qubits(node)) + 1)
        for name, qubits, _ in self.get_node_gates(node):
            current_ds = []
            for q in qubits:
                current_ds.append(qubit_depth[q])
            current_d = max(current_ds)
            if name in ("SWAP", "swap"):
                current_d += 3
            else:
                current_d += 1
            for q in qubits:
                qubit_depth[q] = current_d
        return max(qubit_depth)

    def get_edge_qubits(self, edge):
        return self.edges[edge]["qubits"]

    def set_edge_qubits(self, edge, qubits):
        self.edges[edge]["qubits"] = list(qubits)

    def add_gate_absorb(self, format_gate: tuple, gate=None):
        """Add a gate and absorb is if possible.

        Args:
            format_gate (tuple): a tuple of (gate_name, (qubits), (parameters))
            gate(GateOperation): Gate Operation

        Returns:
            int: id of new node
        """
        nodes_check = []
        for q in format_gate[1]:
            node_father = self.qubit_to_node[q]
            if node_father not in nodes_check and node_father is not None:
                nodes_check.append(node_father)
        # add node
        new_node = self.add_gate(format_gate, gate)
        # absorb
        for node_parent in nodes_check:
            if not self.check_absorbable(node_parent, new_node):
                continue
            new_node = self.cascade_node(new_node, node_parent)
        return new_node

    def cascade_node(self, node1: int, node2: int):
        """Combine two given nodes.

        Here we only update one node (node_in) and delete the other (node_out)
        instead of creating one node and deleting both.

        Args:
            node1 (int): id of node1
            node2 (int): id of node2

        Returns:
            int: id of new node
        """
        if not self.check_direct_dependency(node1, node2):
            if not self.check_parallel(node1, node2):
                raise ValueError("nodes are not direct dependency or parallel")
        if (node1, node2) in self.edges:
            node_in, node_out = node1, node2
        else:
            if (node2, node1) in self.edges:
                node_in, node_out = node2, node1
            else:
                # we accept two nodes are parallel
                node_in, node_out = node1, node2
        # update attributes
        self.nodes[node_in]["gate"].extend(self.nodes[node_out]["gate"])
        self.nodes[node_in]["gates"].extend(self.nodes[node_out]["gates"])
        for gate in self.nodes[node_out]["gates"]:
            if len(gate[1]) == 1:
                self.nodes[node_in]["num_gate_1q"] += 1
            if len(gate[1]) == 2:
                self.nodes[node_in]["num_gate_2q"] += 1
            for q in gate[1]:
                if q not in self.nodes[node_in]["qubits"]:
                    self.nodes[node_in]["qubits"].append(q)
        # delete node and add egdes
        for node in list(self.successors(node_out)):
            self.add_line(
                node_in,
                node,
                self.get_edge_qubits((node_out, node)),
            )
        for node in list(self.predecessors(node_out)):
            if node != node_in:
                self.add_line(
                    node,
                    node_in,
                    self.get_edge_qubits((node, node_out)),
                )
        # update qubit_to_node
        for q in self.get_node_qubits(node_out):
            if self.qubit_to_node[q] == node_out:
                self.qubit_to_node[q] = node_in
        self.remove_node(node_out)
        return node_in

    def from_qasm_string(self, qasm_string: str, absorb=True):
        """Parse OpenQASM string, build graph and get ir.

        Args:
            qasm_string (str): OpenQASM string
            absorb (bool, optional): Whether absorb the gate. Defaults to True.

        Returns:
            list: measure operations
        """
        abs_tree = get_abs_tree(qasm_string)
        cir = get_ir(abs_tree)
        qnum = cir.num_qubits
        self.convert_ir(cir)
        self.num_q = qnum
        self.num_q_log = qnum
        return self.from_ir(cir, absorb=absorb)

    def convert_ir(self, ir: QuantumCircuit):
        """Convert the target qubits from str to int in ir.

        Args:
            ir (QuantumCircuit): quantum circuit intermediate representation
        """
        gates_list = ir.get_operations()
        if len(gates_list) == 0:
            return []
        if isinstance(gates_list[0].targets[0], int):
            return ir
        for gate in gates_list:
            gate.targets = [int(q) for q in gate.targets]
        return ir

    def from_ir(self, circ: QuantumCircuit, absorb=True):
        """Build graph from circ.

        Args:
            circ (QuantumCircuit): quantum circuit
            absorb (bool, optional): Whether absorb the gate. Defaults to True.

        Returns:
            list: measure operations
        """
        measure_op = []
        for gate in circ.get_operations():
            name = gate.name
            if name in ("barrier", "measure"):
                if name == "measure":
                    measure_op.append(gate)
                continue
            format_gate = (name, tuple(gate.targets), gate.arg_value)
            if absorb:
                self.add_gate_absorb(format_gate, gate)
            else:
                self.add_gate(format_gate, gate)
        self.origin_ir = circ.get_operations()
        if self.num_q is None:
            self.num_q = self.get_dg_num_q()
        return measure_op

    def to_ir(self, add_barrier=False, decompose_swap=False):
        """Convert the DG to a ir.

        If decompose_swap is set to True, we will decompose each SWAP
        into 3 CNOTs.
        """
        # FrontCircuit is imported at module level to avoid
        # import-outside-toplevel

        # init circuits
        ag = nx.complete_graph(self.num_q)
        circuit = FrontCircuit(self, ag)
        ir = []
        # add qiskit gates one by one
        while circuit.num_remain_nodes > 0:
            front_nodes = circuit.front_layer
            if len(front_nodes) == 0:
                raise RuntimeError("No front nodes available")
            for node in front_nodes:
                gates = self.get_node_gates(node)
                for gate in gates:
                    if decompose_swap and gate[0] == "swap":
                        q0, q1 = gate[1]
                        ir.append(
                            create_gate(
                                "cx", targets=[q0, q1], arg_value=gate[2]
                            )
                        )
                        ir.append(
                            create_gate(
                                "cx", targets=[q1, q0], arg_value=gate[2]
                            )
                        )
                        ir.append(
                            create_gate(
                                "cx", targets=[q0, q1], arg_value=gate[2]
                            )
                        )
                    else:
                        ir.append(
                            create_gate(
                                gate[0],
                                targets=list(gate[1]),
                                arg_value=gate[2],
                            )
                        )
                if add_barrier:
                    ir.append(
                        create_gate("sync", targets=list(range(self.num_q)))
                    )
            circuit.execute_front_layer()
        return ir

    def draw(self):
        """Draw DG graph."""
        nx.draw(self, with_labels=1)

    def check_parallel(self, node1: int, node2: int):
        """Check two nodes are parallel or not.

        Args:
            node1 (int): id of node1.
            node2 (int): id of node2.

        Returns:
            bool: true if two nodes are parallel, false otherwise.
        """
        if (
            approx.local_node_connectivity(self, node1, node2) == 0
            and approx.local_node_connectivity(self, node2, node1) == 0
        ):
            return True
        else:
            return False

    def check_direct_dependency(self, node1: int, node2: int):
        """Check two nodes are directly dependent or not.

        We say node2 directly depends on node1 if
            1) two nodes share at least one qubit;
            2) for each shared qubit, there can't be any nodes existing between
               the two nodes;
            3) there can't be any path connecting node1 and node2 other than
               the edge in 1)

        If two node are directly dependent, these nodes can be absorbed or
        cascaded. Note that currently we won't accept node1 and node2 are
        parallel, in that case, we will return False! One can use
        self.check_parallel to check the parallelism between nodes.

        Args:
            node1 (int): id of node1.
            node2 (int): id of node2.

        Returns:
            bool: true if two nodes are directly dependent, false otherwise.
        """
        # check condition 1
        if (node1, node2) in self.edges:
            node_in, node_out = node1, node2
        else:
            if (node2, node1) in self.edges:
                node_in, node_out = node2, node1
            else:
                return False
        # condition 2 is covered in condition 3
        # check condition 3
        if approx.local_node_connectivity(self, node_in, node_out) > 1:
            return False
        return True

    def check_absorbable(self, node1: int, node2: int):
        """Check if node1 and node2 can be obsorbed to each other.

        node1 and node2 are absorbable if all qubits in node1 or node2 exist in
        node2 or node1 and they are directly dependent to each other.

        Args:
            node1 (int): id of node1.
            node2 (int): id of node2.

        Returns:
            bool: true if two nodes are absorbable, false otherwise.
        """
        if len(self.get_node_qubits(node1)) > len(self.get_node_qubits(node2)):
            node_abs, node_org = node2, node1
        else:
            node_abs, node_org = node1, node2
        for q in self.get_node_qubits(node_abs):
            if q not in self.get_node_qubits(node_org):
                return False
        if not self.check_direct_dependency(node_org, node_abs):
            return False
        return True
