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
import math
import numexpr

from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation
from wy_qcos.transpiler.cmss.decomposer.equivalence_graph import (
    EquivalenceRule,
)
from wy_qcos.transpiler.cmss.common.gate_operation import create_gate


class RuleApplier:
    """Applies equivalence rules (RulePath) to actual quantum circuits.

    This class is responsible for mapping placeholder gates in rules to real
    gates in the circuit, automatically handling qubit and parameter mapping.
    """

    def apply_one_rule(
        self, op: BaseOperation, rule: EquivalenceRule
    ) -> list[BaseOperation]:
        """Applies a single equivalence rule to a specific gate operation.

        Args:
            op (BaseOperation): The gate operation to which the rule
                will be applied.
            rule (EquivalenceRule): The equivalence rule to apply.

        Returns:
            list[BaseOperation]: list of new gate operations after
                applying the rule.

        Notes:
            - Placeholder qubits in the rule are automatically mapped to
                the gate's qubits.
            - Placeholder parameters are automatically evaluated using
                the gate's argument values.
            - The symbol 'pi' is automatically available in parameter
                expressions.
        """
        # Automatically construct qubit mapping
        qubit_dict = dict(zip(rule.target.qubits, op.targets))

        # Automatically construct parameter mapping
        param_dict = {}
        if rule.target.params:
            param_dict = dict(zip(rule.target.params, op.arg_value))
        param_dict.update({"pi": math.pi})

        new_ops = []
        for src in rule.sources:
            # Map qubits
            mapped_qubits = [qubit_dict[q] for q in src.qubits]

            # Map parameters
            if src.params:
                mapped_params = [
                    (numexpr.evaluate(p, param_dict).item())
                    for p in src.params
                ]
            else:
                mapped_params = []

            new_ops.append(create_gate(src.name, mapped_qubits, mapped_params))

        return new_ops

    def apply_path(
        self,
        circuit: list[BaseOperation],
        target: list[str],
        rule_dict: dict[str, EquivalenceRule],
    ) -> list[BaseOperation]:
        """Recursively decompose a quantum circuit using equivalence rules.

        Each gate in the input circuit is recursively decomposed using the
        provided equivalence rules until it becomes a target gate. Results of
        gate decompositions are memoized to avoid repeated work and improve
        performance.

        Args:
            circuit: A list of ``BaseOperation`` objects representing the
                original quantum circuit.
            target: A list of gate names that are considered target (basis)
                gates. Gates whose ``name`` is in this list will not be
                decomposed further.
            rule_dict: A mapping from gate names to their corresponding
                ``EquivalenceRule`` objects used for decomposition.

        Returns:
            A list of ``BaseOperation`` objects representing the fully
            decomposed circuit, containing only target gates.

        Raises:
            KeyError: If a gate is not in the target set and no decomposition
                rule is found for it in ``rule_dict``.
        """
        target_gate_names = set(target)

        # Cache mapping gate signatures to their fully decomposed results.
        decompose_cache: dict[tuple, list[BaseOperation]] = {}

        def _gate_signature(gate: BaseOperation) -> tuple:
            """Generate a hashable signature for a gate.

            The signature uniquely identifies a gate by its type, targets,
            and parameters, and is used as a cache key for memoization.

            Args:
                gate: The gate for which to generate a signature.

            Returns:
                A tuple that uniquely represents the gate.
            """
            return (
                gate.name,
                tuple(gate.targets),
                tuple(gate.arg_value) if gate.arg_value is not None else None,
            )

        def _decompose_gate(gate: BaseOperation) -> list[BaseOperation]:
            """Recursively decompose a single gate into target gates.

            This function uses memoization to avoid recomputing the
            decomposition of identical gates.

            Args:
                gate: The ``BaseOperation`` to decompose.

            Returns:
                A list of ``BaseOperation`` objects representing the fully
                decomposed form of the input gate.

            Raises:
                KeyError: If the gate cannot be decomposed because no
                    corresponding rule exists.
            """
            signature = _gate_signature(gate)

            # Return cached result if available.
            if signature in decompose_cache:
                return list(decompose_cache[signature])

            result: list[BaseOperation] = []
            # Gate is already in the target basis.
            if gate.name in target_gate_names:
                result = [gate]
                decompose_cache[signature] = result
                return list(result)

            # No rule available for decomposition.
            if gate.name not in rule_dict:
                raise KeyError(
                    f"No decomposition rule available for gate: {gate.name!r}"
                )

            rule = rule_dict[gate.name]

            # Apply the equivalence rule once.
            expanded_ops = self.apply_one_rule(gate, rule)

            # Recursively decompose generated operations.
            for op in expanded_ops:
                result.extend(_decompose_gate(op))

            # Cache the fully decomposed result.
            decompose_cache[signature] = result
            return list(result)

        decomposed_circuit: list[BaseOperation] = []
        for gate in circuit:
            decomposed_circuit.extend(_decompose_gate(gate))

        return decomposed_circuit
