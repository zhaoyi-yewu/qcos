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

from functools import cached_property
import time

import numpy as np

from wy_qcos.transpiler.cmss.optimizer.template import (
    OptimizingTemplate,
    generate_hadamard_gate_templates,
    replace_all,
    generate_single_qubit_gate_templates,
    generate_cnot_ctrl_templates,
    generate_cnot_targ_templates,
)
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.dag_node import DAGOpNode
from wy_qcos.transpiler.cmss.circuit.collect_blocks import (
    BlockCollector,
)


class CliffordRzOptimization:
    _optimize_sub_method = {
        1: "reduce_hadamard_gates",
        2: "cancel_single_qubit_gates",
        3: "cancel_two_qubit_gates",
        4: "merge_rotations",
    }
    _optimize_routine = [1, 3, 2, 3, 1, 2, 4, 3, 2]

    def __init__(self, verbose=False) -> None:
        self.verbose = verbose

    @cached_property
    def hadamard_templates(self) -> list[OptimizingTemplate]:
        """Generate Hadamard gate optimization templates.

        Returns:
            list[OptimizingTemplate]: a list of h gate optimization templates.
        """
        return generate_hadamard_gate_templates()

    @cached_property
    def single_qubit_gate_templates(self):
        return generate_single_qubit_gate_templates()

    @cached_property
    def cnot_ctrl_template(self):
        return generate_cnot_ctrl_templates()

    @cached_property
    def cnot_targ_template(self):
        return generate_cnot_targ_templates()

    def reduce_hadamard_gates(self, dag: DAGCircuit) -> int:
        """Hadamard gate reduction algorithm.

        Args:
            dag (DAGCircuit): the DAG to be optimized.

        Returns:
            int: the count of reduced H gates.
        """
        cnt = 0
        for template in self.hadamard_templates:
            cnt += replace_all(dag, template)
        return cnt

    def get_next_node_on_specific_qubit(
        self, dag: DAGCircuit, cur_node: DAGOpNode, qubit: int
    ):
        """Get the next node on a specific qubit.

        We need the direct successor of a node along a specific qubit. However,
        `DAGCircuit.successors` returns all topological successors regardless
        of qubits. Therefore, we determine whether two nodes are directly
        adjacent on a given qubit by analyzing the predecessors of the
        candidate successor node.

        Args:
            dag (DAGCircuit): the dag containing the cur_node.
            cur_node (DAGOpNode): the current node.
            qubit (int): get the next node on this qubit.

        Returns:
            DAGOpNode: the next node.
        """
        if qubit not in cur_node.qargs:
            raise ValueError(f"{qubit} is not in qargs of {cur_node.name}.")
        next_nodes = list(dag.successors(cur_node))
        if len(next_nodes) == 0:
            return None
        if len(next_nodes) == 1:
            return next_nodes[0]

        for nxt in next_nodes:
            if isinstance(nxt, DAGOpNode):
                qubits_of_nxt = set(nxt.qargs)
            else:
                qubits_of_nxt = {nxt.wire}
            # the predecessors of `nxt` node
            pre_nodes_of_nxt = list(dag.predecessors(nxt))
            for pre_ in pre_nodes_of_nxt:
                if pre_ is cur_node:
                    continue
                # only precess the node between `cur_node` and `nxt`
                if pre_ in dag.ancestors(cur_node):
                    continue

                # the qubits of `pre_`
                if isinstance(pre_, DAGOpNode):
                    qargs = pre_.qargs
                else:
                    # DAGInNode or DAGOutNode
                    qargs = (pre_.wire,)

                for qubit_ in qargs:
                    if qubit_ in qubits_of_nxt:
                        # lies between `cur_node` and `nxt`, cause the
                        # operations to be non-adjacent on the `qubit_`
                        qubits_of_nxt.remove(qubit_)
            # if the specific `qubit` is still in `qubits_of_nxt`, indicates
            # that the cur_node is adjacent with nxt on the qubit
            if qubit in qubits_of_nxt:
                return nxt
        return None

    def cancel_single_qubit_gates(self, dag: DAGCircuit):
        """Merge Rz gates using commutation rules.

        Args:
            dag (DAGCircuit): the DAG to be optimized.

        Returns:
            int: the count of reduced Rz gates.
        """
        cnt = 0
        for node in list(dag.topological_op_nodes()):
            if node.name != "rz":
                continue

            # erase the gate if degree == 0
            if np.isclose(float(node.op.arg_value[0]), 0):
                dag.remove_op_node(node)
                cnt += 1
                continue

            c_node = node
            qubit_idx = node.qargs[0]
            while True:
                # next node
                n_node = self.get_next_node_on_specific_qubit(
                    dag, c_node, qubit_idx
                )
                if not isinstance(n_node, DAGOpNode):
                    break

                if n_node.name == "rz":
                    n_node.op.arg_value[0] += node.op.arg_value[0]
                    dag.remove_op_node(node)
                    cnt += 1
                    break

                # template matching
                mapping = None
                for template in self.single_qubit_gate_templates:
                    mapping = template.compare(dag, n_node, node.qargs[0])
                    if mapping:
                        out_node = template.template.output_map[
                            template.anchor
                        ]
                        last_node = list(
                            template.template.predecessors(out_node)
                        )[0]
                        c_node = mapping[id(last_node)]
                        break
                if not mapping:
                    break
        return cnt

    def cancel_two_qubit_gates(self, dag: DAGCircuit):
        """Merge cx gates using commutation rules.

        Args:
            dag (DAGCircuit): the DAG to be optimized.

        Returns:
            int: the count of reduced Rz gates.
        """
        cnt = 0
        for node in list(dag.topological_op_nodes()):
            if node.name != "cx":
                continue
            # the node has been deleted before
            if node not in dag.nodes():
                continue

            # current node
            c_ctrl_node, c_ctrl_qubit = node, node.qargs[0]
            c_targ_node, c_targ_qubit = node, node.qargs[1]
            while True:
                # next node
                n_ctrl_node = self.get_next_node_on_specific_qubit(
                    dag, c_ctrl_node, c_ctrl_qubit
                )
                if not isinstance(n_ctrl_node, DAGOpNode):
                    break
                n_targ_node = self.get_next_node_on_specific_qubit(
                    dag, c_targ_node, c_targ_qubit
                )
                if not isinstance(n_targ_node, DAGOpNode):
                    break
                # adjacent cx
                if (
                    id(n_ctrl_node) == id(n_targ_node)
                    and n_ctrl_node.name == "cx"
                    and n_ctrl_node.qargs == node.qargs
                ):
                    dag.remove_op_node(n_ctrl_node)
                    dag.remove_op_node(node)
                    cnt += 2
                    break

                # template matching from control qubit
                mapping = None
                for template in self.cnot_ctrl_template:
                    mapping = template.compare(dag, n_ctrl_node, c_ctrl_qubit)
                    if mapping:
                        # target qubit can not be in the template
                        reach = -1
                        for node_ in mapping.values():
                            if node_.qargs.count(c_targ_qubit):
                                reach = 1
                                break
                        if reach == 1:
                            mapping = None
                            continue

                        out_node = template.template.output_map[
                            template.anchor
                        ]
                        last_node = list(
                            template.template.predecessors(out_node)
                        )[0]
                        c_ctrl_node = mapping[id(last_node)]
                        break
                if mapping:
                    continue

                # template matching from target qubit
                for template in self.cnot_targ_template:
                    mapping = template.compare(dag, n_targ_node, c_targ_qubit)
                    if mapping:
                        # control qubit can not be in the template
                        reach = -1
                        for node_ in mapping.values():
                            if node_.qargs.count(c_ctrl_qubit):
                                reach = 1
                                break
                        if reach == 1:
                            mapping = None
                            continue

                        out_node = template.template.output_map[
                            template.anchor
                        ]
                        last_node = list(
                            template.template.predecessors(out_node)
                        )[0]
                        c_targ_node = mapping[id(last_node)]
                        break
                if not mapping:
                    break

        return cnt

    def merge_rotations(self, dag: DAGCircuit):
        """Optimize Rz gates using phase polynomials.

        Args:
            dag (DAGCircuit): dag to be optimized.

        Returns:
            int: the count of reduced Rz gates.
        """
        cnt = 0
        block_collector = BlockCollector(dag)
        blocks = block_collector.collect_all_matching_blocks(
            lambda node: node.op.name in ["cx", "rz", "x"],
        )
        for block in blocks:
            cnt += self.parse_cnot_rz_circuit(block, dag)
        return cnt

    def parse_cnot_rz_circuit(
        self, node_list: list[DAGOpNode], dag: DAGCircuit
    ):
        """Optimize Rz gates using phase polynomials.

        This function identifies phase polynomials in linear function
        representation and merges Rz gates on the same linear functions.

        Args:
            node_list (list[DAGOpNode]): subcircuit of Rz, CX, X gates.
            dag (DAGCircuit): dag to be optimized, including the subcircuit.

        Returns:
            int: the count of reduced Rz gates.
        """
        # phase polynomials, every item is a monomial and its phase
        phases = {}
        # first Rz gate of every monomial
        first_rz = {}
        # current linear function of every qubit
        cur_phases = {}
        # nodes to be removed
        to_remove = []
        # the count of reduced Rz gates
        cnt = 0

        for node in node_list:
            # initialize linear function of every qubit
            for qubit in node.qargs:
                if qubit not in cur_phases:
                    cur_phases[qubit] = 1 << (qubit + 1)

            if node.name == "cx":
                # update the linear function of target qubit
                control, target = node.qargs[0], node.qargs[1]
                cur_phases[target] = cur_phases[target] ^ cur_phases[control]
            elif node.name == "x":
                # flip the constant term of linear function
                qubit = node.qargs[0]
                cur_phases[qubit] = cur_phases[qubit] ^ 1
            elif node.name == "rz":
                # the monomial and sign of current qubit
                qubit_phase = cur_phases[node.qargs[0]]
                sign = -1 if qubit_phase & 1 else 1
                mono = qubit_phase >> 1
                # accumulate phase to phase polynomial
                phases[mono] = sign * node.op.arg_value[0] + (
                    phases[mono] if mono in phases else 0
                )
                if mono not in first_rz:
                    first_rz[mono] = (node, sign)
                else:
                    # already have Rz gate with same monomial
                    to_remove.append(node)

        for mono, pack in first_rz.items():
            node, sign = pack
            if np.isclose(float(phases[mono]), 0):
                dag.remove_op_node(node)
                cnt += 1
            else:
                node.op.arg_value = [sign * phases[mono]]

        for node in to_remove:
            dag.remove_op_node(node)
            cnt += 1

        return cnt

    def run(self, dag: DAGCircuit):
        """Optimize circuit with commutation rules.

        Args:
            dag (DAGCircuit): dag to be optimized.

        Returns:
            DAGCircuit: optimized dag.
        """
        routine = self._optimize_routine
        init_size = dag.size()
        dag.parameterize_all()

        gate_reduced_cnt = 0
        round_cnt = 0
        total_time = 0.0

        # optimize
        while True:
            round_cnt += 1
            if self.verbose:
                print(f"ROUND #{round_cnt}:")

            cnt = 0
            for step in routine:
                start_time = time.time()
                cur_cnt = getattr(self, self._optimize_sub_method[step])(dag)
                end_time = time.time()

                cnt += cur_cnt
                step_time = end_time - start_time
                total_time += step_time

                if self.verbose:
                    print(
                        f"\t{self._optimize_sub_method[step]}: {cur_cnt} "
                        f"gates reduced, cost {np.round(step_time, 3)} s"
                    )
            if cnt == 0:
                break

            gate_reduced_cnt += cnt

        dag.deparameterize_all()
        res_size = dag.size()

        if self.verbose:
            print(
                f"initially {init_size} gates, "
                f"reduced {gate_reduced_cnt} gates, "
                f"remain {res_size} gates, "
                f"cost {np.round(total_time, 3)} s "
            )

        return dag
