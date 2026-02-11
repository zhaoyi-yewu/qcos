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
from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation
from wy_qcos.transpiler.cmss.decomposer.rule_applier import RuleApplier
from wy_qcos.transpiler.cmss.decomposer.equivalence_graph import (
    EquivalenceGraph,
    ParamGate,
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
        gate_name_list = list({op.name for op in source})
        rule_dict = graph.get_optimal_decomposition_rule_dictionary(
            gate_name_list,
            target,
        )
        decomposed_circuit = self.applier.apply_path(source, target, rule_dict)
        return decomposed_circuit

    def get_decompose_rules(
        self,
        source: list[str],
        target: list[str],
    ) -> tuple[
        dict[ParamGate, list[ParamGate]],
        dict[str, int],
    ]:
        """Build the full decomposition table for given source gates.

        This method queries the global equivalence graph and builds a full
        decomposition table that expands each source ParamGate into a sequence
        of ParamGates expressed only in the given target (basis) gate set.

        Gates whose names are included in ``target`` will be treated as basis
        gates and will not be decomposed further.

        Args:
            source: List of source gate names that require decomposition.
            target: List of target (basis) gate names. Gates in this set are
                considered terminal and will not be expanded further.

        Returns:
            A tuple containing:
                - decomposition_table:
                    Mapping from each template ParamGate to its fully expanded
                    list of ParamGate objects expressed only using target
                    gates.
                - usage_stats:
                    Mapping from gate name to integer usage count collected
                    during decomposition.

        Raises:
            RuntimeError: If the global equivalence graph has not been
                initialized.
            ValueError: If a required decomposition rule is missing in the
                graph.
        """
        graph = Decomposer._graph
        if graph is None:
            raise RuntimeError("EquivalenceGraph was not initialized.")

        return graph.build_full_decomposition_table(source, target)

    def apply_decompose_rules(
        self,
        circuit: list[BaseOperation],
        table: dict[ParamGate, list[ParamGate]],
    ) -> list[BaseOperation]:
        """Apply a decomposition table to a quantum circuit.

        This method rewrites each gate in the input circuit using a precomputed
        decomposition table. If a gate matches a ParamGate template in the
        table, it is replaced by the corresponding expanded sequence. Parameter
        expressions are evaluated and qubits are remapped during expansion.

        Args:
            circuit: List of BaseOperation objects representing the input
                circuit to be decomposed.
            table: Decomposition table produced by
                ``build_full_decomposition_table``, mapping ParamGate templates
                to expanded ParamGate sequences.

        Returns:
            A new list of BaseOperation objects where all decomposable gates
            have been replaced by their target-basis expansions.

        Raises:
            ValueError: If parameter expression evaluation fails during
                expansion.
        """
        return self.applier.apply_with_decomposition_table(circuit, table)
