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

from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.dag_node import DAGOpNode


class AdjacentPhaseOptPass:
    """Merge adjacent phase gates."""

    def __init__(self) -> None:
        # gate to be optimized
        self.phase_gates = {"rx", "ry", "rz", "crx", "cry", "crz", "u1"}

    def run(self, dag: DAGCircuit, basis_gates: set | None = None):
        """Optimize the dag by merging adjacent phase gates.

        Args:
            dag (DAGCircuit): dag to be optimized.
            basis_gates (set, optional): basis gates after decompose.

        Returns:
            int: the number of reduced gates.
        """
        cnt = 0
        rz_phase_gates = {"s", "sdg", "t", "tdg", "z"}
        op_counts = dag.count_ops()
        phase_gates = self.phase_gates.intersection(op_counts.keys())
        if rz_phase_gates.intersection(op_counts.keys()):
            phase_gates.add("rz")

        if basis_gates is not None:
            phase_gates = phase_gates.intersection(basis_gates)

        if rz_phase_gates.intersection(op_counts.keys()):
            dag.parameterize_all_rz()

        for node in dag.topological_op_nodes():
            if node.name not in phase_gates:
                continue
            n_node = list(dag.successors(node))[0]
            if not isinstance(n_node, DAGOpNode):
                continue
            if (
                node.op.name == n_node.op.name
                and node.op.targets == n_node.op.targets
            ):
                n_node.op.arg_value[0] += node.op.arg_value[0]
                dag.remove_op_node(node)
                cnt += 1

        op_counts = dag.count_ops()
        if op_counts.get("rz", 0) > 0:
            if basis_gates is None or rz_phase_gates.issubset(basis_gates):
                dag.deparameterize_all_rz()
        return cnt
