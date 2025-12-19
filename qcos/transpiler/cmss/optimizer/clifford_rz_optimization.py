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

from functools import cached_property

from qcos.transpiler.cmss.optimizer.template import (
    OptimizingTemplate,
    generate_hadamard_gate_templates,
    replace_all,
)
from qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit


class CliffordRzOptimization:
    def __init__(self, level="light", verbose=False) -> None:
        self.level = level
        self.verbose = verbose

    @cached_property
    def hadamard_templates(self) -> list[OptimizingTemplate]:
        """Generate Hadamard gate optimization templates.

        Returns:
            list[OptimizingTemplate]: a list of h gate optimization templates.
        """
        return generate_hadamard_gate_templates()

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
