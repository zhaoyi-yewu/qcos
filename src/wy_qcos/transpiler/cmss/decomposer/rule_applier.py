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
import copy
import numexpr

from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation
from wy_qcos.transpiler.cmss.decomposer.equivalence_graph import (
    EquivalenceRule,
    ParamGate,
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
                return copy.deepcopy(list(decompose_cache[signature]))

            result: list[BaseOperation] = []
            # Gate is already in the target basis.
            if gate.name in target_gate_names:
                result = [gate]
                decompose_cache[signature] = result
                return copy.deepcopy(list(result))

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
            return copy.deepcopy(list(result))

        decomposed_circuit: list[BaseOperation] = []
        for gate in circuit:
            decomposed_circuit.extend(_decompose_gate(gate))

        return decomposed_circuit

    def apply_with_decomposition_table(
        self,
        circuit: list[BaseOperation],
        table: dict[ParamGate, list[ParamGate]],
    ) -> list[BaseOperation]:
        """Apply a pre-built decomposition table to a circuit.

        Each gate in the input circuit is replaced by its fully expanded
        decomposition sequence if a matching ParamGate template exists in
        the table. Parameter expressions are numerically evaluated using
        numexpr with the gate argument environment.

        Args:
            circuit: List of BaseOperation objects representing the input
                circuit.
            table: Mapping from template ParamGate to its expanded ParamGate
                decomposition sequence.

        Returns:
            A new list of BaseOperation objects after decomposition.

        Raises:
            ValueError: If parameter expression evaluation fails.
        """
        _expr_code_cache: dict[str, object] = {}

        _SAFE_GLOBALS = {
            "__builtins__": {},
            "pi": math.pi,
            "e": math.e,
        }

        def _eval_expr_cached(expr, env):
            code = _expr_code_cache.get(expr)

            if code is None:
                code = compile(expr, "<expr>", "eval")
                _expr_code_cache[expr] = code

            return float(eval(code, _SAFE_GLOBALS, env))  # pylint: disable=eval-used  # noqa: S307

        # Build name -> template lookup index.
        template_index: dict[str, ParamGate] = {
            template.name: template for template in table
        }

        new_ops: list[BaseOperation] = []

        for op in circuit:
            # Gate does not require decomposition.
            template = template_index.get(op.name)
            if template is None:
                new_ops.append(op)
                continue

            expanded_sequence = table[template]

            # -------- Qubit mapping --------
            qubit_map: dict[str, int] = dict(zip(template.qubits, op.targets))

            # -------- Parameter environment --------
            param_env: dict[str, float] = {
                "pi": math.pi,
                "e": math.e,
            }

            if template.params:
                for key, value in zip(template.params, op.arg_value or []):
                    param_env[key] = value

            # -------- Emit expanded gates --------
            for param_gate in expanded_sequence:
                mapped_qubits = [qubit_map[q] for q in param_gate.qubits]

                if param_gate.params:
                    try:
                        mapped_params = []
                        for expr in param_gate.params:
                            value = _eval_expr_cached(expr, param_env)
                            mapped_params.append(value)

                    except Exception as exc:
                        msg = (
                            "Parameter evaluation failed for gate "
                            f"{param_gate.name}: "
                            f"exprs={param_gate.params}, "
                            f"env={param_env}"
                        )
                        raise ValueError(msg) from exc
                else:
                    mapped_params = []

                new_ops.append(
                    create_gate(
                        param_gate.name,
                        mapped_qubits,
                        mapped_params,
                    )
                )

        return new_ops
