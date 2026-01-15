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
        pass

    def run(self, dag: DAGCircuit):
        """Optimize the dag by merging adjacent phase gates.

        Args:
            dag (DAGCircuit): dag to be optimized.

        Returns:
            int: the number of reduced gates.
        """
        cnt = 0
        phase_gates = ["rx", "ry", "rz", "crx", "cry", "crz", "u1"]
        dag.parameterize_all()
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

        dag.deparameterize_all()
        return cnt
