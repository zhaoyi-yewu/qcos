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

from __future__ import annotations

__all__ = ["ConvertVisitor"]

import copy
import re
import string
from collections.abc import Callable, Sequence, Iterator
from typing import (
    Any,
    NoReturn,
)
from openqasm3 import ast
from openqasm3.visitor import QASMVisitor

from wy_qcos.transpiler.cmss.compiler.openqasm3 import types
from wy_qcos.transpiler.cmss.compiler.openqasm3.data import Scope, Symbol
from wy_qcos.transpiler.cmss.compiler.openqasm3.exceptions import (
    ConversionError,
    raise_from_node,
)
from wy_qcos.transpiler.cmss.compiler.openqasm3.expression import (
    ValueResolver,
    resolve_condition,
)
from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
    State,
    GateScope,
    Parameter,
    ParameterExpression,
)
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import (
    GateOperation,
    create_gate,
    ControlGate,
    P,
    Reset,
    Measure,
)
from wy_qcos.common.cmss.sync import Sync
from wy_qcos.common.cmss.register import (
    QuantumRegister,
    ClassicalRegister,
)

_QASM2_IDENTIFIER = re.compile(r"[a-z]\w*", flags=re.ASCII)


def _create_standard_gate(gate_name, n_params, n_qubits):
    """Constructor function for creating standard gates.

    Args:
        gate_name (str): Name of the gate (e.g., "rx", "h", "cx")
        n_params (int): Number of parameters the gate expects
        n_qubits (int): Number of qubits the gate acts on

    Returns:
        Callable: A builder function that creates GateOperation instances
    """

    def builder(*args):
        targets = list(range(n_qubits))
        if n_params > 0:
            return create_gate(
                gate_name, targets=targets, arg_value=list(args)
            )
        else:
            return create_gate(gate_name, targets=targets)

    return builder


# Standard gates dictionary
# Format: "gate_name": (builder_function, n_arguments, n_qubits)
#   - builder_function: Builder function to create gate operation instances
#   - n_arguments: Number of parameters the gate expects
#   - n_qubits: Number of qubits the gate acts on
_STDGATES = {
    # Single-qubit gates
    "p": (_create_standard_gate("p", 1, 1), 1, 1),  # Phase gate
    "x": (_create_standard_gate("x", 0, 1), 0, 1),  # Pauli-X gate
    "y": (_create_standard_gate("y", 0, 1), 0, 1),  # Pauli-Y gate
    "z": (_create_standard_gate("z", 0, 1), 0, 1),  # Pauli-Z gate
    "h": (_create_standard_gate("h", 0, 1), 0, 1),  # Hadamard gate
    "s": (_create_standard_gate("s", 0, 1), 0, 1),  # S gate
    "sdg": (_create_standard_gate("sdg", 0, 1), 0, 1),  # S† gate
    "t": (_create_standard_gate("t", 0, 1), 0, 1),  # T gate
    "tdg": (_create_standard_gate("tdg", 0, 1), 0, 1),  # T† gate
    "sx": (_create_standard_gate("sx", 0, 1), 0, 1),  # √X gate
    # Rotation gates (single-qubit, 1 parameter)
    "rx": (_create_standard_gate("rx", 1, 1), 1, 1),  # Rotation around X-axis
    "ry": (_create_standard_gate("ry", 1, 1), 1, 1),  # Rotation around Y-axis
    "rz": (_create_standard_gate("rz", 1, 1), 1, 1),  # Rotation around Z-axis
    # Two-qubit gates
    "cx": (_create_standard_gate("cx", 0, 2), 0, 2),  # CNOT/Controlled-X
    "cy": (_create_standard_gate("cy", 0, 2), 0, 2),  # Controlled-Y
    "cz": (_create_standard_gate("cz", 0, 2), 0, 2),  # Controlled-Z
    "cp": (_create_standard_gate("cp", 1, 2), 1, 2),  # Controlled-phase
    "ch": (_create_standard_gate("ch", 0, 2), 0, 2),  # Controlled-Hadamard
    "swap": (_create_standard_gate("swap", 0, 2), 0, 2),  # SWAP gate
    # Two-qubit rotation gates
    "crx": (_create_standard_gate("crx", 1, 2), 1, 2),  # Controlled rotation X
    "cry": (_create_standard_gate("cry", 1, 2), 1, 2),  # Controlled rotation Y
    "crz": (_create_standard_gate("crz", 1, 2), 1, 2),  # Controlled rotation Z
    # Three-qubit gates
    "ccx": (_create_standard_gate("ccx", 0, 3), 0, 3),  # Toffoli/CCX gate
    "cswap": (_create_standard_gate("cswap", 0, 3), 0, 3),  # controlled-SWAP
    # General two-qubit gates
    "cu": (_create_standard_gate("cu", 4, 2), 4, 2),
    # Aliases and uppercase versions
    "CX": (_create_standard_gate("cx", 0, 2), 0, 2),
    "phase": (_create_standard_gate("p", 1, 1), 1, 1),
    "cphase": (_create_standard_gate("cp", 1, 2), 1, 2),
    # Identity gate
    "id": (_create_standard_gate("id", 0, 1), 0, 1),  # Identity gate
    # IBM Qiskit compatible U gates
    "u1": (_create_standard_gate("u1", 1, 1), 1, 1),  # U1 gate
    "u2": (_create_standard_gate("u2", 2, 1), 2, 1),  # U2 gate
    "u3": (_create_standard_gate("u3", 3, 1), 3, 1),  # U3 gate
    "u": (_create_standard_gate("u", 3, 1), 3, 1),  # General single-qubit
    "U": (_create_standard_gate("u", 3, 1), 3, 1),  # Uppercase U
}


def _escape_qasm2(name: str) -> str:
    """Escape a `name` to produce a valid OpenQASM 2 identifier.

    Args:
        name (str): Original identifier name

    Returns:
        str: Escaped identifier that conforms to OpenQASM 2 regex pattern

    This is necessary for registers as of Terra 0.22 beacuse their names have
    an initialisation check that they match this regex. It should be able to
    be removed once that restriction is lifted.
    """
    if _QASM2_IDENTIFIER.fullmatch(name):
        return name
    name = re.sub(r"\W", "_", name)
    if not name or name[0] not in string.ascii_lowercase:
        name = "esc_" + name
    return name


class GateBuilder:
    def __init__(
        self,
        name: str,
        definition: QuantumCircuit,
        order: Sequence[Parameter] | None = None,
    ):
        self._name = name
        self._definition = definition
        self._order = order if order is not None else ()
        self._num_qubits = definition.num_qubits

    """Initialize a gate builder for custom quantum gates.

    Args:
        name (str): Name of the custom gate
        definition (QuantumCircuit): Circuit that defines the gate's behavior
        order (Sequence[Parameter] | None): Ordered list of gate parameters

    The gate builder creates GateOperation instances with the specified
    parameters applied to the defined circuit.
    """

    def __call__(self, *parameters):
        if len(parameters) != len(self._order):
            raise ConversionError(
                "incorrect number of parameters in call. Expecting "
                f" {len(self._order)}, got {len(parameters)}."
            )

        targets = list(range(self._num_qubits))

        # Create gate operation
        gate = GateOperation(
            name=self._name,
            targets=targets,
            arg_value=list(parameters) if parameters else [],
            operation_type=str(self._num_qubits),
        )

        return gate


class ConvertVisitor(QASMVisitor[State]):
    """Internal visitor of converting OpenQASM 3 AST to QuantumCircuit.

    The other methods on this class are internal only, and generally not
    part of the public interface.
    """

    # This class assumes that the given AST was a valid OpenQASM 3 program.
    # It is not within our scope for this simple package to gracefully handle
    # arbitrary semantically invalid programs. In some places, such as symbol
    # definitions, we do some simple checks to help everyone's sanity, as the
    # reference package doesn't yet do this.

    # pylint: disable=missing-function-docstring,unused-argument

    def __init__(
        self,
        annotation_handlers: dict[str, Any] | None = None,
    ):
        self.annotation_handlers = annotation_handlers or {}

    def convert(
        self, node: ast.Program, *, source: str | None = None
    ) -> QuantumCircuit:
        """Convert a program node into a :class:`QuantumCircuit`.

        Args:
            node (ast.Program): Root node of the OpenQASM 3 AST
            source (str | None): Optional source code string for error messages

        Returns:
            QuantumCircuit: Converted quantum circuit representation

        If given, `source` is a string containing the OpenQASM 3 source code
        that was parsed into `node`.  This is used to generated improved error
        messages. A :class:`.State` containing information about the
        conversion is returned. The :class:`QuantumCircuit` is stored in
        property thereof named `circuit`.
        """
        state: State = self.visit(node, State(source))
        if hasattr(state.circuit, "_parameters"):
            state.circuit._parameters = state.all_parameters
        elif hasattr(state.circuit, "parameters"):
            pass
        return state.circuit

    def _raise_previously_defined(
        self, new: Symbol, old: Symbol, node: ast.QASMNode
    ) -> NoReturn:
        message = f"'{new.name}' is already defined."
        if old.definer and (span := old.definer.span) is not None:
            message += f" Previous definition on line {span.start_line}."
        raise_from_node(node, message)

    def _define_gate(
        self,
        name: str,
        definition: Callable,
        n_parameters: int,
        n_qubits: int,
        definer: ast.QASMNode,
        context: State,
    ) -> State:
        """Define a quantum gate in the symbol table.

        Args:
            name (str): Name of the gate
            definition (Callable): Function that builds gate instances
            n_parameters (int): Number of parameters the gate accepts
            n_qubits (int): Number of qubits the gate operates on
            definer (ast.QASMNode): AST node that defines the gate
            context (State): Current conversion state

        Returns:
            State: Updated state with gate added to symbol table

        Raises:
            ConversionError: If gate is already defined with same name
        """
        if context.scope is not Scope.GLOBAL:
            raise_from_node(definer, "gates can only be declared globally")
        type = types.Gate(n_parameters, n_qubits)
        symbol = Symbol(name, definition, type, Scope.GLOBAL, definer)
        if (previous := context.symbol_table.get(name, definer)) is not None:
            self._raise_previously_defined(symbol, previous, definer)
        context.symbol_table.insert(symbol)
        return context

    def _apply_gate_modifier(
        self,
        modifier: ast.QuantumGateModifier,
        gate: GateOperation,
        context: State,
    ) -> GateOperation:
        """Apply gate modifiers (inv, pow, ctrl, negctrl) to a gate operation.

        Args:
            modifier (ast.QuantumGateModifier): Modifier AST node
            gate (GateOperation): Base gate operation to modify
            context (State): Current conversion state

        Returns:
            GateOperation: Modified gate operation

        Raises:
            ConversionError: If modifier is unsupported or arguments invalid

        Supports inverse, power, and control modifiers with proper
        argument validation and gate transformation.
        """
        if modifier.modifier is ast.GateModifierName.inv:
            if hasattr(gate, "inverse"):
                return gate.inverse()
            else:
                if hasattr(gate, "arg_value") and gate.arg_value is not None:
                    if gate.name.lower() in ["rx", "ry", "rz", "p", "r"]:
                        new_args = (
                            [-arg for arg in gate.arg_value]
                            if isinstance(gate.arg_value, list)
                            else [-gate.arg_value]
                        )
                        if new_args is None:
                            new_args = []
                        return create_gate(gate.name, gate.targets, new_args)
                return GateOperation(
                    name=f"{gate.name}_inv",
                    targets=gate.targets,
                    arg_value=gate.arg_value,
                    operation_type=gate.operation_type,
                    hermitian=gate.hermitian,
                )

        elif modifier.modifier is ast.GateModifierName.pow:
            if modifier.argument is None:
                raise_from_node(
                    modifier, "'pow' requires exactly one argument"
                )

            exponent = self._resolve_constant_float(modifier.argument, context)

            if hasattr(gate, "power"):
                return gate.power(exponent)
            else:
                if gate.name.lower() in ["rx", "ry", "rz"] and hasattr(
                    gate, "arg_value"
                ):
                    new_arg = (
                        [arg * exponent for arg in gate.arg_value]
                        if gate.arg_value
                        else []
                    )
                    return create_gate(gate.name, gate.targets, new_arg)
                else:
                    return GateOperation(
                        name=f"{gate.name}_pow_{exponent}",
                        targets=gate.targets,
                        arg_value=gate.arg_value,
                        operation_type=gate.operation_type,
                        hermitian=gate.hermitian,
                    )

        elif modifier.modifier in (
            ast.GateModifierName.ctrl,
            ast.GateModifierName.negctrl,
        ):
            num_controls = (
                1
                if modifier.argument is None
                else self._resolve_constant_int(modifier.argument, context)
            )

            if modifier.modifier is ast.GateModifierName.ctrl:
                ctrl_state = (1 << num_controls) - 1
            else:  # negctrl
                ctrl_state = 0
            if hasattr(gate, "targets") and gate.targets is not None:
                total_qubits = num_controls + len(gate.targets)
                temp_targets = list(range(total_qubits))
            else:
                temp_targets = list(range(num_controls + 1))

            return ControlGate(
                base_gate=gate,
                num_controls=num_controls,
                ctrl_state=ctrl_state,
                targets=temp_targets,
            )

        else:
            raise_from_node(
                modifier, f"unsupported gate modifier: {modifier.modifier}"
            )

    def _broadcast_gate(
        self,
        arguments: Sequence[int | Sequence[int]],
        node: ast.QASMNode,
    ) -> Iterator[tuple[int, ...]]:
        """Broadcast gate arguments to handle qubit arrays of different length.

        Args:
            arguments (Sequence[int | Sequence[int]]): Mixed int/qubit arrays
            node (ast.QASMNode): AST node for error reporting

        Returns:
            Iterator[tuple[int, ...]]: Iterator of broadcasted qubit tuples

        Raises:
            ConversionError: If argument lengths are mismatched

        Handles OpenQASM's broadcasting semantics where single qubits
        are repeated to match array lengths.
        """
        max_length = 1
        for arg in arguments:
            if isinstance(arg, list):
                max_length = max(max_length, len(arg))

        def args():
            for argument in arguments:
                if isinstance(argument, int):
                    yield (argument,) * max_length
                elif len(argument) != max_length:
                    raise_from_node(
                        node, "mismatched lengths in gate broadcast"
                    )
                else:
                    yield tuple(argument)

        return zip(*args())

    def _parse_annotation(self, node: ast.Annotation, context: State) -> Any:
        return node.keyword

    def _resolve_generic(
        self, node: ast.Expression, context: State, strict: bool
    ) -> tuple[Any, types.Type]:
        return ValueResolver(context, strict).resolve(node)

    def _resolve_constant_int(
        self, node: ast.Expression, context: State
    ) -> int:
        """Resolve expression to a constant integer value.

        Args:
            node (ast.Expression): Expression AST node
            context (State): Current conversion state

        Returns:
            int: Constant integer value

        Raises:
            ConversionError: If expression is not a constant integer
        """
        value, type = self._resolve_generic(node, context, strict=True)
        if not isinstance(type, (types.Int, types.Uint)) or not type.const:
            raise_from_node(node, "required a constant integer")
        return value

    def _resolve_constant_float(
        self, node: ast.Expression, context: State
    ) -> float:
        """Resolve an expression to a constant floating-point number.

        Args:
            node (ast.Expression): The expression AST node to resolve
            context (State): Conversion state containing symbols and types

        Returns:
            float: The resolved constant floating-point value

        Raises:
            ConversionError: If the expression cannot be resolved to a constant
            floating-point number or if it's not constant

        This method validates that the expression represents a constant numeric
        value (int, uint, or float) and returns it as a float.
        """
        value, type = self._resolve_generic(node, context, strict=True)
        if (
            not isinstance(type, (types.Int, types.Uint, types.Float))
            or not type.const
        ):
            raise_from_node(node, "required a constant floating-point number")
        return value

    def _resolve_constant_duration(
        self, node: ast.Expression, context: State
    ) -> tuple[float, str]:
        """Resolve an expression to a constant duration value with unit.

        Args:
            node (ast.Expression): The expression AST node to resolve
            context (State): Conversion state containing symbols and types

        Returns:
            tuple[float, str]: A tuple containing (duration_value, unit_name)

        Raises:
            ConversionError: If the expression cannot be resolved to a constant
            duration or if it's not constant

        This method is used for time-based operations like delays, where
        a duration with specific unit (e.g., "dt", "ns") is required.
        """
        value, type = self._resolve_generic(node, context, strict=True)
        if not isinstance(type, types.Duration) or not type.const:
            raise_from_node(node, "required a constant duration")
        return value

    def _resolve_angle(
        self, node: ast.Expression, context: State
    ) -> float | ParameterExpression:
        value, type = self._resolve_generic(node, context, strict=False)
        if not isinstance(
            type, (types.Int, types.Uint, types.Angle, types.Float)
        ):
            raise_from_node(node, "required an angle-like value")
        return value

    def _resolve_carg(
        self, node: ast.Expression, context: State
    ) -> int | list[int]:
        value, type = self._resolve_generic(node, context, strict=True)
        if not isinstance(type, (types.Bit, types.BitArray)):
            raise_from_node(node, "required a bit or bit register")
        return value

    def _resolve_qarg(
        self, node: ast.Expression, context: State
    ) -> int | list[int]:
        """Resolve expression to a qubit or qubit array.

        Args:
            node (ast.Expression): Expression AST node
            context (State): Current conversion state

        Returns:
            int | list[int]: Single qubit index or list of qubit indices

        Raises:
            ConversionError: If expression is not a valid qubit reference
        """
        value, type_info = self._resolve_generic(node, context, strict=True)
        if not isinstance(
            type_info, (types.Qubit, types.HardwareQubit, types.QubitArray)
        ):
            raise_from_node(node, "required a qubit or qubit register")

        if isinstance(type_info, types.Qubit) or isinstance(
            type_info, types.HardwareQubit
        ):
            if not isinstance(value, int):
                raise_from_node(
                    node, f"expected integer qubit index, got {type(value)}"
                )
            return value

        elif isinstance(type_info, types.QubitArray):
            if not isinstance(value, list) or not all(
                isinstance(i, int) for i in value
            ):
                raise_from_node(
                    node,
                    (
                        f"expected list of integer qubit indices, "
                        f"got {type(value)}"
                    ),
                )
            return value

        raise_from_node(node, "invalid qubit type")

    def _resolve_condition(
        self, node: ast.Expression, context: State
    ) -> tuple[ClassicalRegister, int] | tuple[int, bool]:
        """Resolve an expression to its value and type.

        Args:
            node (ast.Expression): Expression AST node
            context (State): Current conversion state
            strict (bool): Whether to enforce strict type checking

        Returns:
            tuple[Any, types.Type]: (value, type) pair

        Uses ValueResolver to evaluate expressions and determine their types.
        """
        lhs, rhs = resolve_condition(node, context)
        if isinstance(lhs, int):
            if not isinstance(rhs, bool):
                raise_from_node(
                    node,
                    (
                        f"Expected bool for single bit comparison, "
                        f"got {type(rhs)}"
                    ),
                )
            return (lhs, rhs)
        elif isinstance(lhs, tuple):
            if not isinstance(rhs, int):
                raise_from_node(
                    node,
                    f"Expected int for bit array comparison, got {type(rhs)}",
                )
            bits_list = list(lhs)
            name = context.unique_name()
            register = ClassicalRegister(
                name=_escape_qasm2(name), bits=bits_list
            )
            context.circuit.add_register(register)
            bit_array_type = types.BitArray(len(bits_list))
            context.symbol_table.insert(
                Symbol(name, register, bit_array_type, Scope.NONE, None)
            )
            return (register, rhs)
        elif isinstance(lhs, ClassicalRegister):
            if not isinstance(rhs, int):
                raise_from_node(
                    node,
                    f"Expected int for bit array comparison, got {type(rhs)}",
                )
            return (lhs, rhs)
        else:
            raise_from_node(
                node,
                f"Unexpected type for condition LHS: {type(lhs)}. "
                f"Expected int, tuple[int, ...] or ClassicalRegister.",
            )

    # Everything below is the implementation of the visitor itself.
    # The general `visit` method is derived from the base class.

    def generic_visit(self, node, context=None):
        raise_from_node(
            node, f"node of type {node.__class__.__name__} is not supported"
        )

    def visit_Program(self, node: ast.Program, context: State) -> State:
        """Process the root Program node of OpenQASM 3 AST.

        Args:
            node (ast.Program): Program AST node
            context (State): Current conversion state

        Returns:
            State: Updated state after processing all statements

        Traverses all statements in the program and processes them
        sequentially.
        """
        for statement in node.statements:
            context = self.visit(statement, context)
        return context

    def visit_Include(self, node: ast.Include, context: State) -> State:
        """Process an include statement in OpenQASM 3 code.

        Args:
            node (ast.Include): The include statement AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with standard gates defined from the include

        Raises:
            ConversionError: If the included file is not "stdgates.inc"

        This method handles the 'include "stdgates.inc"' statement by defining
        all standard quantum gates in the symbol table. It only defines gates
        that haven't been defined yet to avoid conflicts with user-defined
        gates.
        """
        if node.filename != "stdgates.inc":
            raise_from_node(
                node, "non-stdgates imports not currently supported"
            )
        for name, (builder, n_arguments, n_qubits) in _STDGATES.items():
            if context.symbol_table.get(name, node) is None:
                context = self._define_gate(
                    name, builder, n_arguments, n_qubits, node, context
                )
        return context

    def visit_QubitDeclaration(
        self, node: ast.QubitDeclaration, context: State
    ) -> State:
        """Process a qubit declaration.

        Args:
            node (ast.QubitDeclaration): Qubit declaration AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with qubit(s) registered

        Allocates qubit indices, creates quantum registers if needed,
        and adds symbols to the symbol table.
        """
        context.addressing_mode.set_virtual_mode(node)
        name = node.qubit.name
        if node.size is None:
            index = context.allocate_qubit(name)
            symbol = Symbol(name, index, types.Qubit(), Scope.GLOBAL, node)
        else:
            size = self._resolve_constant_int(node.size, context)

            indices = []
            for i in range(size):
                qubit_name = f"{name}[{i}]"
                index = context.allocate_qubit(qubit_name)
                indices.append(index)

            register = QuantumRegister(size, name=name)
            context.circuit.add_register(register)

            symbol = Symbol(
                name, indices, types.QubitArray(size), Scope.GLOBAL, node
            )

        context.symbol_table.insert(symbol)
        return context

    def visit_QuantumGateDefinition(
        self, node: ast.QuantumGateDefinition, context: State
    ) -> State:
        """Process a quantum gate definition.

        Args:
            node (ast.QuantumGateDefinition): Gate definition AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with gate defined

        Creates a GateScope for the gate body, defines standard gates within
        the scope, processes parameters and qubits, and registers the gate.
        """
        num_qubits_needed = len(node.qubits)
        gate_circuit = QuantumCircuit(num_qubits=num_qubits_needed)

        with GateScope(context) as inner:
            inner.circuit = gate_circuit

            # 1. Define the standard gate within the scope of the custom gate
            for gate_name, (builder, n_args, n_qubits) in _STDGATES.items():
                # Create a standard gate symbol with the scope of the
                # current scope（Scope.GATE).
                gate_type = types.Gate(n_args, n_qubits)
                symbol = Symbol(
                    name=gate_name,
                    data=builder,
                    type=gate_type,
                    scope=Scope.GATE,
                    definer=node,
                )
                inner.symbol_table.insert(symbol)

            # 2. Set the qubit mapping.
            for i, qubit_name in enumerate(node.qubits):
                index = i
                inner.qubit_mapping[qubit_name.name] = index
                inner.symbol_table.insert(
                    Symbol(
                        qubit_name.name,
                        index,
                        types.Qubit(),
                        Scope.GATE,
                        node,
                    )
                )

            # 3. Set parameters.
            parameters = [Parameter(name.name) for name in node.arguments]
            for parameter in parameters:
                inner.symbol_table.insert(
                    Symbol(
                        parameter.name,
                        parameter,
                        types.Angle(),
                        Scope.GATE,
                        node,
                    )
                )
                inner.all_parameters.add(parameter)

            # 4. Processing statements in the body of the text
            for statement in node.body:
                self.visit(statement, inner)

        # 5. Define the gate itself
        return self._define_gate(
            node.name.name,
            GateBuilder(node.name.name, inner.circuit, parameters),
            len(parameters),
            num_qubits_needed,
            node,
            context,
        )

    def visit_QuantumGate(
        self, node: ast.QuantumGate, context: State
    ) -> State:
        """Process a quantum gate invocation.

        Args:
            node (ast.QuantumGate): Gate invocation AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with gate operation added to circuit

        Raises:
            ConversionError: If gate is undefined or arguments are invalid

        Resolves gate definition, parameters, and qubits, applies modifiers,
        creates gate operation, and appends to the circuit.
        """
        if node.duration is not None:
            raise_from_node(node, "gates with durations are not supported.")

        if (
            gate_symbol := context.symbol_table.get(node.name.name, node)
        ) is None:
            raise_from_node(node, f"gate '{node.name.name}' is not defined.")
        if not isinstance(gate_symbol.type, types.Gate):
            message = (
                f"'{node.name.name}' is a '{gate_symbol.type.pretty()}',"
                f"not a gate."
            )
            if (span := gate_symbol.definer.span) is not None:
                message += f" Definition on line {span.start_line}"
            raise_from_node(node, message)
        gate_builder = gate_symbol.data
        arguments = [
            self._resolve_angle(argument, context)
            for argument in node.arguments
        ]
        try:
            gate = gate_builder(*arguments)
        except TypeError as e:
            raise_from_node(
                node, f"Unable to create gate '{node.name.name}': {e}"
            )
        for modifier in reversed(node.modifiers):
            gate = self._apply_gate_modifier(modifier, gate, context)

        qubit_indices = []
        for qarg in node.qubits:
            resolved = self._resolve_qarg(qarg, context)
            if isinstance(resolved, int):
                qubit_indices.append([resolved])
            elif isinstance(resolved, list):
                qubit_indices.append(resolved)
            else:
                raise_from_node(
                    qarg, f"Invalid qubit specification: {type(resolved)}"
                )

        for qubits in self._broadcast_gate_indices(qubit_indices, node):
            if isinstance(gate, ControlGate):
                total_qubits_needed = (
                    gate.num_controls + len(gate.base_gate.targets)
                    if hasattr(gate.base_gate, "targets")
                    else gate.num_controls + 1
                )

                if len(qubits) != total_qubits_needed:
                    raise_from_node(
                        node,
                        (
                            f"Contrl gate needs {total_qubits_needed} qubit, "
                            f"but provided {len(qubits)}."
                        ),
                    )

                gate_copy = ControlGate(
                    base_gate=gate.base_gate,
                    num_controls=gate.num_controls,
                    ctrl_state=gate.ctrl_state,
                    targets=list(qubits),
                )
            else:
                gate_copy = self._copy_gate_with_targets(gate, qubits)
            context.circuit.append(gate_copy)

        arguments = [
            self._resolve_angle(argument, context)
            for argument in node.arguments
        ]

        for arg in arguments:
            if isinstance(arg, Parameter):
                context.all_parameters.add(arg)
            elif isinstance(arg, ParameterExpression):
                context.all_parameters.update(arg.parameters)
        return context

    def _copy_gate_with_targets(self, gate, targets):
        """Copy a gate operation and set new target qubits.

        Args:
            gate: Original gate operation
            targets: New target qubit indices

        Returns:
            GateOperation: Copy of gate with updated targets

        Creates a deep copy of the gate and updates its target qubits
        while preserving all other properties.
        """
        gate_copy = copy.deepcopy(gate)

        if hasattr(gate_copy, "targets"):
            gate_copy.targets = list(targets)
        elif hasattr(gate_copy, "_targets"):
            gate_copy._targets = list(targets)
        else:
            pass

        return gate_copy

    def _broadcast_gate_indices(
        self,
        arguments: Sequence[int | Sequence[int]],
        node: ast.QASMNode,
    ) -> Iterator[tuple[int, ...]]:
        """Broadcast integer index parameters for gate application.

        Args:
            arguments (Sequence[int | Sequence[int]]): Mixed indices
            node (ast.QASMNode): AST node for error reporting

        Returns:
            Iterator[tuple[int, ...]]: Iterator of broadcasted indices

        Raises:
            ConversionError: If argument types or lengths are invalid

        Converts mixed integer and list arguments into aligned tuples
        for gate application across multiple qubits.
        """
        max_length = 1
        for arg in arguments:
            if isinstance(arg, list):
                max_length = max(max_length, len(arg))

        def get_indices(arg):
            if isinstance(arg, int):
                return [arg] * max_length
            elif isinstance(arg, list):
                if len(arg) != max_length:
                    raise_from_node(
                        node, "mismatched lengths in gate broadcast"
                    )
                return arg
            else:
                raise_from_node(node, f"invalid argument type: {type(arg)}")

        all_indices = [get_indices(arg) for arg in arguments]
        return zip(*all_indices)

    def visit_QuantumPhase(
        self, node: ast.QuantumPhase, context: State
    ) -> State:
        """Process a quantum phase application (gphase).

        Args:
            node (ast.QuantumPhase): Phase application AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with phase gate(s) added to circuit

        Applies phase to all qubits if no specific qubits are provided,
        otherwise applies to specified qubits. Handles global phase
        and gate modifiers.
        """
        angle = self._resolve_angle(node.argument, context)

        if not node.qubits:
            num_qubits = context.circuit.num_qubits

            if num_qubits == 0:
                if isinstance(angle, (Parameter, ParameterExpression)):
                    pass
                else:
                    current_phase = context.circuit.global_phase
                    context.circuit.set_global_phase(current_phase + angle)
            else:
                for i in range(num_qubits):
                    phase_op: GateOperation = P(targets=[i], arg_value=[angle])

                    for modifier in reversed(node.modifiers):
                        phase_op = self._apply_gate_modifier(
                            modifier, phase_op, context
                        )

                    context.circuit.append(phase_op)

            return context

        for qarg in node.qubits:
            qubit = self._resolve_qarg(qarg, context)
            if isinstance(qubit, int):
                phase_op_qubit: GateOperation = P(
                    targets=[qubit], arg_value=[angle]
                )

                for modifier in reversed(node.modifiers):
                    phase_op_qubit = self._apply_gate_modifier(
                        modifier, phase_op_qubit, context
                    )

                context.circuit.append(phase_op_qubit)
            elif isinstance(qubit, list):
                for q in qubit:
                    phase_op_q: GateOperation = P(
                        targets=[q], arg_value=[angle]
                    )

                    for modifier in reversed(node.modifiers):
                        phase_op_q = self._apply_gate_modifier(
                            modifier, phase_op_q, context
                        )

                context.circuit.append(phase_op_q)
            else:
                raise_from_node(
                    qarg, f"Invalid qubit specification: {type(qubit)}"
                )

        return context

    def visit_QuantumMeasurementStatement(
        self, node: ast.QuantumMeasurementStatement, context: State
    ) -> State:
        """Process a quantum measurement statement.

        Args:
            node (ast.QuantumMeasurementStatement): The measurement statement
                AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with measurement operation added to circuit

        Raises:
            ConversionError: If the measurement doesn't save its result or
            if the target qubit specification is invalid

        This method handles OpenQASM 3 measurement statements like
        "measure q -> c" by creating a measurement operation and adding
        it to the quantum circuit.
        """
        if node.target is None:
            raise_from_node(node, "measurements must save their result")
        measured = self._resolve_qarg(node.measure.qubit, context)
        if isinstance(measured, int):
            measure_op = Measure(targets=[measured])
        elif isinstance(measured, list):
            measure_op = Measure(targets=measured)
        else:
            raise_from_node(
                node.measure.qubit,
                f"Invalid measurement target: {type(measured)}",
            )

        context.circuit.append(measure_op)

        return context

    def visit_QuantumBarrier(
        self, node: ast.QuantumBarrier, context: State
    ) -> State:
        """Process a quantum barrier (barrier) statement.

        Args:
            node (ast.QuantumBarrier): The barrier statement AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with barrier operation added to circuit

        This method handles the OpenQASM 3 barrier statement, which prevents
        optimizations from moving operations across the barrier. It creates
        a synchronization (Sync) operation for the specified qubits.
        """
        qubit_indices = []
        for qarg in node.qubits:
            resolved = self._resolve_qarg(qarg, context)
            if isinstance(resolved, int):
                qubit_indices.append(resolved)
            elif isinstance(resolved, list):
                qubit_indices.extend(resolved)
            else:
                raise_from_node(
                    qarg, f"Invalid qubit specification: {type(resolved)}"
                )

        barrier_op = Sync(targets=qubit_indices)
        context.circuit.append(barrier_op)
        return context

    def visit_QuantumReset(
        self, node: ast.QuantumReset, context: State
    ) -> State:
        """Process a quantum reset statement.

        Args:
            node (ast.QuantumReset): The reset statement AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with reset operation added to circuit

        Raises:
            ConversionError: If the qubit specification is invalid

        This method handles the OpenQASM 3 reset statement, which resets
        specified qubits to the kit 0 state. It creates a Reset operation
        for single qubits or qubit arrays.
        """
        qubit = self._resolve_qarg(node.qubits, context)

        if isinstance(qubit, int):
            reset_op = Reset(targets=[qubit])
        elif isinstance(qubit, list):
            reset_op = Reset(targets=qubit)
        else:
            raise_from_node(
                node.qubits, f"Invalid qubit specification: {type(qubit)}"
            )

        context.circuit.append(reset_op)

        return context

    def visit_ClassicalDeclaration(
        self, node: ast.ClassicalDeclaration, context: State
    ) -> State:
        """Process a classical bit declaration statement.

        Args:
            node (ast.ClassicalDeclaration): Classical declaration AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with classical bits/registers defined

        Raises:
            ConversionError: If declaration is not in global scope or
            if the type is not supported

        This method handles declarations of classical bits and registers,
        including initialization with measurement results. It supports
        both single-bit declarations and bit arrays (registers).
        """
        if context.scope is not Scope.GLOBAL:
            raise_from_node(node, "only global declarations are supported")
        if not isinstance(node.type, ast.BitType):
            type_name = node.type.__class__.__name__[
                :-4
            ].lower()  # Cheeky quick hack.
            raise_from_node(
                node, f"declarations of type '{type_name}' are not supported"
            )
        name = node.identifier.name
        if node.type.size is None:
            bit_index = context.circuit.num_clbits
            context.circuit.set_num_clbits(bit_index + 1)
            symbol = Symbol(name, bit_index, types.Bit(), context.scope, node)
        else:
            size = self._resolve_constant_int(node.type.size, context)
            context.circuit.set_num_clbits(context.circuit.num_clbits + size)

            register = ClassicalRegister(size, name=_escape_qasm2(name))
            context.circuit.add_register(register)
            symbol = Symbol(
                name, register, types.BitArray(size), context.scope, node
            )
        context.symbol_table.insert(symbol)
        if node.init_expression is not None:
            if not isinstance(node.init_expression, ast.QuantumMeasurement):
                raise_from_node(
                    node.init_expression,
                    "initialisation of classical bits is not supported",
                )
            measured = self._resolve_qarg(node.init_expression.qubit, context)
            measure_op = None
            if isinstance(measured, int):
                measure_op = Measure(targets=[measured])
            elif isinstance(measured, list):
                measure_op = Measure(targets=measured)
            context.circuit.append(measure_op)
        return context

    def visit_IODeclaration(
        self, node: ast.IODeclaration, context: State
    ) -> State:
        if node.io_identifier is ast.IOKeyword.output:
            raise_from_node(node, "the 'output' keyword is not supported")
        type_info: types.Type
        if isinstance(node.type, ast.FloatType):
            size = (
                None
                if node.type.size is None
                else self._resolve_constant_int(node.type.size, context)
            )
            type_info = types.Float(size=size)
        elif isinstance(node.type, ast.AngleType):
            size = (
                None
                if node.type.size is None
                else self._resolve_constant_int(node.type.size, context)
            )
            type_info = types.Angle(size=size)
        else:
            raise_from_node(
                node, "only 'float' and 'angle' inputs are supported"
            )
        name = node.identifier.name
        parameter = Parameter(name)
        symbol = Symbol(name, parameter, type_info, Scope.GLOBAL, node)
        context.symbol_table.insert(symbol)
        context.all_parameters.add(parameter)
        return context

    def visit_BreakStatement(
        self, node: ast.BreakStatement, context: State
    ) -> State:
        # context.circuit.break_loop()
        return context

    def visit_ContinueStatement(
        self, node: ast.ContinueStatement, context: State
    ) -> State:
        # context.circuit.continue_loop()
        return context

    def visit_BranchingStatement(
        self, node: ast.BranchingStatement, context: State
    ) -> State:
        return context

    def visit_WhileLoop(self, node: ast.WhileLoop, context: State) -> State:
        return context

    def visit_ForInLoop(self, node: ast.ForInLoop, context: State) -> State:
        """Process a for-in loop statement.

        Args:
            node (ast.ForInLoop): The for-in loop AST node
            context (State): Current conversion state

        Returns:
            State: Unchanged state (for-in loops are placeholders)

        Raises:
            ConversionError: If loop variable type is not integer or
            if the range/set cannot be resolved

        Note:
            Currently, for-in loops are not fully implemented and
            are treated as no-ops. The method validates loop syntax
            but doesn't execute the loop body.
        """
        if not isinstance(node.type, (ast.IntType, ast.UintType)):
            raise_from_node(node, "only integer loop variables are supported")
        indexset, indextype = self._resolve_generic(
            node.set_declaration, context, strict=True
        )
        if not isinstance(indextype, (types.Range, types.Sequence)):
            raise_from_node(
                node.set_declaration,
                "only ranges and discrete integer sets are supported",
            )
        if isinstance(indextype, types.Range):
            # indexset is a slice.  Convert to range.
            if indexset.start is None or indexset.stop is None:
                raise_from_node(
                    node.set_declaration,
                    "for-loop ranges must have a start and end",
                )
            indexset = (
                range(indexset.start, indexset.stop)
                if indexset.step is None
                else range(indexset.start, indexset.stop, indexset.step)
            )
        return context

    def visit_Box(self, node: ast.Box, context: State) -> State:
        """Process a box (timing annotation) statement.

        Args:
            node (ast.Box): The box statement AST node
            context (State): Current conversion state

        Returns:
            State: Updated state with timing information (if provided)

        This method handles timing annotations for quantum operations,
        including duration specifications and custom annotations.
        Future implementations will use this timing information for
        circuit scheduling and optimization.
        """
        kwargs: dict[str, Any] = {}
        if node.duration is not None:
            duration, unit = self._resolve_constant_duration(
                node.duration, context
            )
            kwargs["duration"] = duration
            kwargs["unit"] = unit
        if node.annotations:
            kwargs["annotations"] = [
                self._parse_annotation(annotation, context)
                for annotation in reversed(node.annotations)
            ]

        return context

    def visit_DelayInstruction(
        self, node: ast.DelayInstruction, context: State
    ) -> State:
        """Process a delay instruction statement.

        Args:
            node (ast.DelayInstruction): The delay instruction AST node
            context (State): Current conversion state

        Returns:
            State: Updated state (delay operations are placeholders)

        Note:
            Currently, delay instructions are not fully implemented and
            are treated as no-ops. Future implementations will add
            timing and scheduling support for delay operations.
        """
        duration, unit = self._resolve_constant_duration(
            node.duration, context
        )
        if not node.qubits:
            # context.circuit.delay(duration, unit=unit)
            return context
        for qarg in node.qubits:
            pass
        return context

    def visit_AliasStatement(
        self, node: ast.AliasStatement, context: State
    ) -> State:
        """Process an alias statement (let) in OpenQASM 3 code.

        Args:
            node (ast.AliasStatement): The alias statement AST node
            context (State): Current conversion state containing symbols and
                types

        Returns:
            State: Updated state with alias registered in symbol table

        Raises:
            ConversionError: If the aliased value is not a bit or qubit
                register

        This method handles the OpenQASM 3 'let' statement, which creates an
        alias (reference) to an existing quantum or classical register.
        The alias is added to the symbol table with the original register's
        bits/type, allowing the alias to be used interchangeably with the
        original register in subsequent statements.

        Example:
            let alias_name = q[0:1];
        """
        bits, type_info = self._resolve_generic(
            node.value, context, strict=True
        )
        name = node.target.name
        inner_name = _escape_qasm2(name)
        if context.scope is not Scope.GLOBAL:
            inner_name = context.unique_name(inner_name)

        register: ClassicalRegister | QuantumRegister
        if isinstance(type_info, types.BitArray):
            register = ClassicalRegister(name=inner_name, bits=bits)
        elif isinstance(type_info, types.QubitArray):
            register = QuantumRegister(name=inner_name, bits=bits)
        else:
            raise_from_node(
                node.value,
                (
                    f"aliases must be of registers of either clbits or "
                    f"qubits, not '{type_info.pretty()}'"
                ),
            )
        context.circuit.add_register(register)
        context.symbol_table.insert(
            Symbol(name, register, type_info, context.scope, node)
        )
        return context
