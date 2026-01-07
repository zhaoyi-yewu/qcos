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
from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation
from wy_qcos.transpiler.cmss.decomposer.rule_applier import RuleApplier
from wy_qcos.transpiler.cmss.decomposer.equivalence_graph import (
    EquivalenceGraph,
)


class Decomposer:
    """Entry point for circuit decomposition.

    This class finds optimal decomposition paths for all operations in a
    circuit and applies them to generate an equivalent target circuit.
    """

    _graph: EquivalenceGraph | None = None

    def __init__(self):
        """Initializes the decomposer and shared equivalence graph."""
        if Decomposer._graph is None:
            Decomposer._graph = EquivalenceGraph()
        self.applier = RuleApplier()

    def decompose(
        self,
        source: list[BaseOperation],
        target: list[str],
    ) -> list[BaseOperation]:
        """Decomposes all operations in a circuit.

        For each operation in the source circuit, this method finds the
        shortest decomposition path based on the equivalence graph and
        replaces the operation accordingly.

        Args:
            source: A list of operations to be decomposed.
            target: A list of str representing the target basis.

        Returns:
            A list of operations representing the decomposed circuit.
        """
        graph = Decomposer._graph
        if graph is None:
            raise RuntimeError("EquivalenceGraph was not initialized.")
        rule_dict = graph.get_optimal_decomposition_rule_dictionary(
            source,
            target,
        )
        decomposed_circuit = self.applier.apply_path(source, target, rule_dict)
        return decomposed_circuit
