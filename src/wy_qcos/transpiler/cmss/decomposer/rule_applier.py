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
        """Recursively decomposes a quantum circuit using equivalence rules.

        Each gate in `circuit` is repeatedly decomposed using the rules in
        `rule_dict` until it becomes a target gate. Gates already belonging
        to the target set are not decomposed further.

        Args:
            circuit: A list of `BaseOperation` objects representing the
                original quantum circuit to decompose.
            target: A list of str representing the allowed target gate types.
                Only gates matching the names of these operations will appear
                in the final output.
            rule_dict: A dictionary mapping gate names to their
                corresponding `EquivalenceRule` decomposition rules.

        Returns:
            A list of `BaseOperation` objects representing the fully
            decomposed circuit.

        Raises:
            KeyError: If a gate that is not in the target set has no
                corresponding rule in `rule_dict`.
        """
        target_gate_names = set(target)

        def _decompose_gate(gate: BaseOperation) -> list[BaseOperation]:
            """Recursively decomposes a single gate.

            Args:
                gate: The gate to decompose.

            Returns:
                A list of `BaseOperation` objects representing the fully
                decomposed form of the gate.
            """
            # If the gate is already in the target basis, keep it.
            if gate.name in target_gate_names:
                return [gate]

            # If the gate cannot be decomposed, that's an error.
            if gate.name not in rule_dict:
                raise KeyError(
                    f"No decomposition rule available for gate: {gate.name!r}"
                )

            rule = rule_dict[gate.name]

            # Apply the rule to obtain intermediate gates.
            expanded_ops = self.apply_one_rule(gate, rule)

            # Recursively decompose each generated gate.
            results: list[BaseOperation] = []
            for op in expanded_ops:
                results.extend(_decompose_gate(op))

            return results

        decomposed_circuit: list[BaseOperation] = []
        for gate in circuit:
            decomposed_circuit.extend(_decompose_gate(gate))

        return decomposed_circuit
