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

import numpy as np

from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit


class InverseCancellation:
    """Cancel inverse gates.

    Cancel specific Gates which are inverses of each other when they occur
    back-to-back.
    """

    def __init__(
        self,
        gates_to_cancel: list[
            GateOperation | tuple[GateOperation, GateOperation]
        ],
    ):
        for gates in gates_to_cancel:
            if isinstance(gates, GateOperation):
                if not self._is_inverse(gates):
                    raise ValueError(f"Gate {gates.name} is not self-inverse")
            elif isinstance(gates, tuple):
                if len(gates) != 2:
                    raise ValueError(
                        f"Too many or too few inputs: {gates}. \
                          Only two are allowed."
                    )
                if not self._is_inverse(gates[0], gates[1]):
                    raise ValueError(
                        f"Gate {gates[0].name} and {gates[1].name} \
                          are not inverse."
                    )
            else:
                raise ValueError(
                    f"InverseCancellation pass does not take input \
                      type {type(gates)}. Input must be a Gate."
                )

        self.self_inverse_gates = []
        self.inverse_gate_pairs = []
        self.self_inverse_gate_names = set()
        self.inverse_gate_pairs_names = set()

        for gates in gates_to_cancel:
            if isinstance(gates, GateOperation):
                self.self_inverse_gates.append(gates)
                self.self_inverse_gate_names.add(gates.name)
            else:
                self.inverse_gate_pairs.append(gates)
                self.inverse_gate_pairs_names.update(x.name for x in gates)

    def run(self, dag: DAGCircuit):
        """Run the InverseCancellation pass on `dag`.

        Args:
            dag: the directed acyclic graph to run on.

        Returns:
            DAGCircuit: Transformed DAG.
        """
        if self.self_inverse_gates:
            dag = self._run_on_self_inverse(dag)
        if self.inverse_gate_pairs:
            dag = self._run_on_inverse_pairs(dag)
        return dag

    def _is_inverse(
        self, gate1: GateOperation, gate2: GateOperation | None = None
    ) -> bool:
        """Check if two gates are inverses of each other.

        If `gate2` is None, this function checks whether `gate1` is
        self-inverse. Otherwise, this function checks whether `gate1` and
        `gate2` are inverses. Global phase is not considered. This is safe
        because the input gates are assumed to be basic gates.

        Args:
            gate1 (GateOperation): first gate.
            gate2 (GateOperation, optional): second gate. Defaults to None.

        Returns:
            bool: inverse or not.
        """
        op1 = gate1.to_matrix()
        if gate2 is None:
            op2 = op1
        else:
            op2 = gate2.to_matrix()

        if op1.shape != op2.shape:
            return False

        product = np.matmul(op1, op2)
        dim = op1.shape[0]
        identity = np.eye(dim, dtype=complex)

        return np.allclose(product, identity)

    def _run_on_self_inverse(self, dag: DAGCircuit):
        """Run self-inverse gates on `dag`.

        Args:
            dag: the directed acyclic graph to run on.

        Returns:
            DAGCircuit: Transformed DAG.
        """
        op_counts = dag.count_ops()
        if not self.self_inverse_gate_names.intersection(op_counts):
            return dag

        for gate in self.self_inverse_gates:
            gate_name = gate.name
            gate_count = op_counts.get(gate_name, 0)
            if gate_count <= 1:
                continue
            gate_runs = dag.collect_runs([gate_name])
            for gate_cancel_run in gate_runs:
                partitions = []
                chunk = []
                max_index = len(gate_cancel_run) - 1
                for i in range(len(gate_cancel_run)):
                    if gate_cancel_run[i].op.name == gate_name:
                        chunk.append(gate_cancel_run[i])
                    else:
                        if chunk:
                            partitions.append(chunk)
                            chunk = []
                        continue
                    # check qargs, cx[0, 1] and cx[1, 0] cannot cancel
                    if (
                        i == max_index
                        or gate_cancel_run[i].qargs
                        != gate_cancel_run[i + 1].qargs
                    ):
                        partitions.append(chunk)
                        chunk = []
                # Remove an even number of gates from each chunk
                for chunk in partitions:
                    if len(chunk) % 2 == 0:
                        dag.remove_op_node(chunk[0])
                    for node in chunk[1:]:
                        dag.remove_op_node(node)
        return dag

    def _run_on_inverse_pairs(self, dag: DAGCircuit):
        """Run inverse gate pairs on `dag`.

        Args:
            dag: the directed acyclic graph to run on.

        Returns:
            DAGCircuit: Transformed DAG.
        """
        op_counts = dag.count_ops()
        if not self.inverse_gate_pairs_names.intersection(op_counts):
            return dag

        for pair in self.inverse_gate_pairs:
            gate_0_name = pair[0].name
            gate_1_name = pair[1].name
            if gate_0_name not in op_counts or gate_1_name not in op_counts:
                continue
            gate_cancel_runs = dag.collect_runs([gate_0_name, gate_1_name])
            for dag_nodes in gate_cancel_runs:
                i = 0
                while i < len(dag_nodes) - 1:
                    if (
                        dag_nodes[i].qargs == dag_nodes[i + 1].qargs
                        and dag_nodes[i].op.name == pair[0].name
                        and dag_nodes[i + 1].op.name == pair[1].name
                    ):
                        dag.remove_op_node(dag_nodes[i])
                        dag.remove_op_node(dag_nodes[i + 1])
                        i = i + 2
                    elif (
                        dag_nodes[i].qargs == dag_nodes[i + 1].qargs
                        and dag_nodes[i].op.name == pair[1].name
                        and dag_nodes[i + 1].op.name == pair[0].name
                    ):
                        dag.remove_op_node(dag_nodes[i])
                        dag.remove_op_node(dag_nodes[i + 1])
                        i = i + 2
                    else:
                        i = i + 1
        return dag
