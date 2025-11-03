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

from qcos.transpiler.cmss.circuit.dag_node import DAGInNode, DAGOutNode
from qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.common.gate_operation import X, H, CCX, CX


class TestDAGCircuit:
    data1 = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qreg q[2];
    h q[0];
    cx q[0], q[1];
    h q[1];
    """

    def test_ir_to_dag(self):
        tree = get_abs_tree(self.data1)
        _, ir = get_ir(tree)
        dag = DAGCircuit.ir_to_dag(ir)
        assert dag is not None
        assert isinstance(dag, DAGCircuit)
        op_nodes = dag.op_nodes()
        assert len(op_nodes) == 3
        assert len(dag.input_map) == 2
        assert len(dag.output_map) == 2

    def test_add_qubits(self):
        dag = DAGCircuit()
        dag.add_qubits(3)
        assert len(dag.input_map) == 3
        assert len(dag.output_map) == 3
        assert len(dag._multi_graph.nodes()) == 6

    def test_apply_operation_back(self):
        dag = DAGCircuit()
        dag.add_qubits(1)
        op = X([0])

        assert len(dag.input_map) == 1
        assert len(dag.output_map) == 1
        assert len(dag._multi_graph.nodes()) == 2

        dag.apply_operation_back(op)
        assert len(dag.input_map) == 1
        assert len(dag.output_map) == 1
        assert len(dag._multi_graph.nodes()) == 3

    def test_size_depth_width(self):
        dag = DAGCircuit()
        dag.add_qubits(3)
        assert dag.size() == 0
        assert dag.depth() == 0
        assert dag.width() == 3

        op1 = X([0])
        op2 = H([1])
        dag.apply_operation_back(op1)
        dag.apply_operation_back(op2)
        assert dag.size() == 2
        assert dag.depth() == 1
        assert dag.width() == 3

        op3 = H([0])
        dag.apply_operation_back(op3)
        assert dag.size() == 3
        assert dag.depth() == 2
        assert dag.width() == 3

    def test_topological_nodes(self):
        tree = get_abs_tree(self.data1)
        _, ir = get_ir(tree)
        dag = DAGCircuit.ir_to_dag(ir)

        nodes = list(dag.topological_nodes())
        op_nodes = list(dag.topological_op_nodes())
        nodes_name = []
        op_nodes_name = []
        for node in nodes:
            if isinstance(node, DAGInNode):
                nodes_name.append("in")
            elif isinstance(node, DAGOutNode):
                nodes_name.append("out")
            else:
                nodes_name.append(node.name)
        for node in op_nodes:
            op_nodes_name.append(node.name)

        assert len(nodes) == 7
        assert len(op_nodes) == 3
        assert nodes_name == ["in", "h", "in", "cx", "h", "out", "out"]
        assert op_nodes_name == ["h", "cx", "h"]

    def test_two_and_multi_qubit_ops(self):
        dag = DAGCircuit()
        dag.add_qubits(3)
        op1 = X([0])
        op2 = H([1])
        op3 = CX([0, 1])
        op4 = CCX([0, 1, 2])
        dag.apply_operation_back(op1)
        dag.apply_operation_back(op2)
        dag.apply_operation_back(op3)
        dag.apply_operation_back(op4)

        assert len(dag.two_qubit_ops()) == 1
        assert len(dag.multi_qubit_ops()) == 1

    def test_longest_path(self):
        tree = get_abs_tree(self.data1)
        _, ir = get_ir(tree)
        dag = DAGCircuit.ir_to_dag(ir)

        node_path = dag.longest_path()
        name_path = []
        for node in node_path:
            if isinstance(node, DAGInNode):
                name_path.append("in")
            elif isinstance(node, DAGOutNode):
                name_path.append("out")
            else:
                name_path.append(node.name)
        assert name_path == ["in", "h", "cx", "h", "out"]

    def test_successors_and_predecessors(self):
        dag = DAGCircuit()
        dag.add_qubits(2)
        op1 = H([0])
        op2 = H([1])
        op3 = CX([0, 1])
        op4 = H([0])
        op5 = H([1])

        node1 = dag.apply_operation_back(op1)
        node2 = dag.apply_operation_back(op2)
        node3 = dag.apply_operation_back(op3)
        node4 = dag.apply_operation_back(op4)
        node5 = dag.apply_operation_back(op5)

        node1_successors = list(dag.successors(node1))
        node1_predecessors = list(dag.predecessors(node1))
        assert len(node1_successors) == 1
        assert node1_successors[0].name == "cx"
        assert len(node1_predecessors) == 1
        assert isinstance(node1_predecessors[0], DAGInNode)

        node3_successors = list(dag.successors(node3))
        node3_predecessors = list(dag.predecessors(node3))
        assert len(node3_successors) == 2
        assert node3_successors[0].name == "h"
        assert node3_successors[1].name == "h"
        assert len(node3_predecessors) == 2
        assert node3_predecessors[0].name == "h"
        assert node3_predecessors[1].name == "h"

        assert not dag.is_successor(node2, node1)
        assert dag.is_successor(node2, node3)
        assert dag.is_predecessor(node4, node3)
        assert dag.is_predecessor(node5, node3)

    def test_remove_op_node(self):
        dag = DAGCircuit()
        dag.add_qubits(2)
        op1 = H([0])
        op2 = CX([0, 1])
        node1 = dag.apply_operation_back(op1)
        node2 = dag.apply_operation_back(op2)

        assert dag.node_counter == 6
        dag.remove_op_node(node1)
        assert dag.node_counter == 5
        dag.remove_op_node(node2)
        assert dag.node_counter == 4

    def test_count_ops(self):
        dag = DAGCircuit()
        dag.add_qubits(2)
        op1 = H([0])
        op2 = H([1])
        op3 = CX([0, 1])
        dag.apply_operation_back(op1)
        dag.apply_operation_back(op2)
        dag.apply_operation_back(op3)
        counts = dag.count_ops()
        assert counts["h"] == 2
        assert counts["cx"] == 1
