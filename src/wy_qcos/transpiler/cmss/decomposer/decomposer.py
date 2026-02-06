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
        rule_dict = graph.get_optimal_decomposition_rule_dictionary(
            source,
            target,
        )
        decomposed_circuit = self.applier.apply_path(source, target, rule_dict)
        return decomposed_circuit

    def get_decompose_rules(
        self,
        qasm_dict: dict[str, tuple[str, list[BaseOperation]]],
        target: list[str],
    ) -> tuple[
        dict[ParamGate, list[ParamGate]],
        dict[str, int],
    ]:
        """Build a full decomposition table from QASM operation groups.

        This method collects all operations from the given QASM dictionary,
        then builds a full decomposition table using the global equivalence
        graph. The resulting table maps each template ParamGate to its fully
        expanded sequence of target-basis ParamGates.

        Args:
            qasm_dict: Mapping from identifiers (such as module or block names)
                to lists of BaseOperation objects parsed from QASM.
            target: List of target (basis) gate names. Gates in this set will
                not be decomposed further.

        Returns:
            A decomposition table mapping each template ParamGate to a fully
            expanded list of ParamGate objects expressed only in target gates.

        Raises:
            ValueError: If a required decomposition rule is missing in the
                equivalence graph.
        """
        graph = Decomposer._graph
        if graph is None:
            raise RuntimeError("EquivalenceGraph was not initialized.")

        # Flatten all BaseOperation lists from the qasm_dict values.
        all_ops = [op for _, ops in qasm_dict.values() for op in ops]

        return graph.build_full_decomposition_table(all_ops, target)

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
