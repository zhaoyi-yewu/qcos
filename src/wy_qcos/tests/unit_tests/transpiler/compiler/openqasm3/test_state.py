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
import pytest

from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
    Parameter,
    ParameterExpression,
    physical_qubit_index,
    AddressingMode,
    SymbolTables,
    SymbolTable,
    State,
    LocalScope,
    GateScope,
    _BUILTINS,
)
from wy_qcos.transpiler.cmss.compiler.openqasm3.data import Scope, Symbol
from wy_qcos.transpiler.cmss.compiler.openqasm3 import types
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit


class TestParameter:
    """Test cases for Parameter class."""

    def test_parameter_initialization(self):
        """Test Parameter initialization."""
        param = Parameter("theta")
        assert param.name == "theta"
        assert str(param) == "theta"
        assert repr(param) == "Parameter('theta')"

    def test_parameter_negation(self):
        """Test parameter negation."""
        param = Parameter("theta")
        neg_param = -param

        assert isinstance(neg_param, ParameterExpression)
        assert str(neg_param) == "-theta"
        assert param in neg_param.parameters

    def test_parameter_addition(self):
        """Test parameter addition."""
        param1 = Parameter("theta")
        param2 = Parameter("phi")

        # Parameter + int
        result = param1 + 5
        assert isinstance(result, ParameterExpression)
        assert str(result) == "(theta + 5)"
        assert param1 in result.parameters

        # Parameter + Parameter
        result = param1 + param2
        assert str(result) == "(theta + phi)"
        assert param1 in result.parameters
        assert param2 in result.parameters

        # int + Parameter
        result = 5 + param1
        assert str(result) == "(5 + theta)"

    def test_parameter_subtraction(self):
        """Test parameter subtraction."""
        param1 = Parameter("theta")
        param2 = Parameter("phi")

        # Parameter - int
        result = param1 - 3
        assert str(result) == "(theta - 3)"

        # Parameter - Parameter
        result = param1 - param2
        assert str(result) == "(theta - phi)"

        # int - Parameter
        result = 10 - param1
        assert str(result) == "(10 - theta)"

    def test_parameter_multiplication(self):
        """Test parameter multiplication."""
        param1 = Parameter("theta")
        param2 = Parameter("phi")

        # Parameter * int
        result = param1 * 2
        assert str(result) == "(theta * 2)"

        # Parameter * Parameter
        result = param1 * param2
        assert str(result) == "(theta * phi)"

        # int * Parameter
        result = 3 * param1
        assert str(result) == "(3 * theta)"

    def test_parameter_division(self):
        """Test parameter division."""
        param1 = Parameter("theta")
        param2 = Parameter("phi")

        # Parameter / int
        result = param1 / 2
        assert str(result) == "(theta / 2)"

        # Parameter / Parameter
        result = param1 / param2
        assert str(result) == "(theta / phi)"

        # int / Parameter
        result = 4 / param1
        assert str(result) == "(4 / theta)"


class TestParameterExpression:
    """Test cases for ParameterExpression class."""

    def test_parameter_expression_initialization(self):
        """Test ParameterExpression initialization."""
        param = Parameter("theta")
        expr = ParameterExpression("theta + 5", {param})

        assert expr.expression == "theta + 5"
        assert expr.parameters == {param}
        assert str(expr) == "theta + 5"
        assert (
            repr(expr)
            == "ParameterExpression('theta + 5', {Parameter('theta')})"
        )

    def test_parameter_expression_negation(self):
        """Test parameter expression negation."""
        param = Parameter("theta")
        expr = ParameterExpression("theta + 5", {param})
        neg_expr = -expr

        assert str(neg_expr) == "-(theta + 5)"
        assert expr.parameters == neg_expr.parameters

    def test_parameter_expression_arithmetic(self):
        """Test arithmetic operations with parameter expressions."""
        param1 = Parameter("theta")
        param2 = Parameter("phi")

        expr1 = ParameterExpression("theta + 1", {param1})
        expr2 = ParameterExpression("phi * 2", {param2})

        # Addition
        result = expr1 + expr2
        assert str(result) == "(theta + 1 + phi * 2)"
        assert param1 in result.parameters
        assert param2 in result.parameters

        # Subtraction
        result = expr1 - expr2
        assert str(result) == "(theta + 1 - phi * 2)"

        # Multiplication
        # result = expr1 * expr2
        # assert str(result) == "((theta + 1) * phi * 2)"

        # Division
        # result = expr1 / expr2
        # assert str(result) == "((theta + 1) / (phi * 2))"

    def test_parameter_expression_with_numbers(self):
        """Test parameter expressions with numbers."""
        param = Parameter("theta")
        expr = ParameterExpression("theta", {param})

        # With integers
        result = expr + 5
        assert str(result) == "(theta + 5)"

        result = 5 + expr
        assert str(result) == "(5 + theta)"

        # With floats
        result = expr * 3.14
        assert str(result) == "(theta * 3.14)"


class TestPhysicalQubitIndex:
    """Test cases for physical_qubit_index function."""

    def test_physical_qubit_index_valid(self):
        """Test valid physical qubit names."""
        assert physical_qubit_index("$0") == 0
        assert physical_qubit_index("$42") == 42
        assert physical_qubit_index("$999") == 999

    def test_physical_qubit_index_invalid(self):
        """Test invalid physical qubit names."""
        assert physical_qubit_index("q0") is None
        assert physical_qubit_index("0") is None
        assert physical_qubit_index("$") is None
        assert physical_qubit_index("$abc") is None

    def test_physical_qubit_index_with_symbol(self):
        """Test physical_qubit_index with Symbol object."""
        symbol = Symbol("$5", 5, types.Qubit(), Scope.GLOBAL, None)
        assert physical_qubit_index(symbol) == 5


class TestAddressingMode:
    """Test cases for AddressingMode class."""

    def test_initial_state(self):
        """Test initial addressing mode state."""
        mode = AddressingMode()
        assert not mode.is_physical()

    def test_set_physical_mode(self):
        """Test setting physical addressing mode."""
        mode = AddressingMode()

        # First time setting physical mode
        mode.set_physical_mode(None)
        assert mode.is_physical()

        # Setting again should not raise error
        mode.set_physical_mode(None)
        assert mode.is_physical()

    def test_set_virtual_mode(self):
        """Test setting virtual addressing mode."""
        mode = AddressingMode()

        # First time setting virtual mode
        mode.set_virtual_mode(None)
        assert not mode.is_physical()

        # Setting again should not raise error
        mode.set_virtual_mode(None)
        assert not mode.is_physical()

    def test_mode_conflict_physical_to_virtual(self):
        """Test conflict when switching from physical to virtual mode."""
        mode = AddressingMode()
        mode.set_physical_mode(None)

        with pytest.raises(Exception) as exc_info:
            mode.set_virtual_mode(None)

        assert "Mixing modes not currently supported" in str(exc_info.value)

    def test_mode_conflict_virtual_to_physical(self):
        """Test conflict when switching from virtual to physical mode."""
        mode = AddressingMode()
        mode.set_virtual_mode(None)

        with pytest.raises(Exception) as exc_info:
            mode.set_physical_mode(None)

        assert "Mixing modes not currently supported" in str(exc_info.value)


class TestSymbolTables:
    """Test cases for SymbolTables class."""

    def setup_method(self):
        """Setup fresh SymbolTables for each test."""
        self.tables = SymbolTables()

    def test_initialization(self):
        """Test SymbolTables initialization."""
        assert len(self.tables) == 1
        assert self.tables[0].scope == Scope.GLOBAL

        # Should have builtins
        assert "pi" in self.tables
        assert "π" in self.tables
        assert "tau" in self.tables

    def test_insert_and_get_symbol(self):
        """Test inserting and retrieving symbols."""
        symbol = Symbol(
            "my_var", 42, types.Int(const=True), Scope.GLOBAL, None
        )
        self.tables.insert(symbol)

        retrieved = self.tables.get("my_var")
        assert retrieved == symbol

        # Non-existent symbol
        assert self.tables.get("non_existent") is None

    def test_duplicate_symbol_error(self):
        """Test error on duplicate symbol insertion."""
        symbol1 = Symbol(
            "my_var", 42, types.Int(const=True), Scope.GLOBAL, None
        )
        symbol2 = Symbol(
            "my_var", 43, types.Int(const=True), Scope.GLOBAL, None
        )

        self.tables.insert(symbol1)

        with pytest.raises(Exception) as exc_info:
            self.tables.insert(symbol2)

        assert "already inserted in symbol table" in str(exc_info.value)

    def test_symbol_visibility_in_gate_scope(self):
        """Test symbol visibility rules in gate scope."""
        # Push a gate scope
        gate_table = SymbolTable(Scope.GATE)
        self.tables.push(gate_table)

        # Try to get a non-const global symbol from gate scope
        symbol = Symbol(
            "my_var", 42, types.Int(const=False), Scope.GLOBAL, None
        )
        self.tables._global_symbol_table.symbols["my_var"] = symbol

        with pytest.raises(Exception) as exc_info:
            self.tables.get("my_var", None)

        assert "is not visible in the scope of a gate" in str(exc_info.value)

    def test_const_symbol_visible_in_gate_scope(self):
        """Test that const symbols are visible in gate scope."""
        # Push a gate scope
        gate_table = SymbolTable(Scope.GATE)
        self.tables.push(gate_table)

        # Const symbol should be visible
        symbol = Symbol(
            "my_const", 42, types.Int(const=True), Scope.GLOBAL, None
        )
        self.tables._global_symbol_table.symbols["my_const"] = symbol

        retrieved = self.tables.get("my_const", None)
        assert retrieved == symbol

    def test_gate_symbol_visible_in_gate_scope(self):
        """Test that gate symbols are visible in gate scope."""
        # Push a gate scope
        gate_table = SymbolTable(Scope.GATE)
        self.tables.push(gate_table)

        # Gate symbol should be visible
        gate_type = types.Gate(1, 1)
        symbol = Symbol("my_gate", lambda x: x, gate_type, Scope.GLOBAL, None)
        self.tables._global_symbol_table.symbols["my_gate"] = symbol

        retrieved = self.tables.get("my_gate", None)
        assert retrieved == symbol

    def test_push_and_pop_scopes(self):
        """Test pushing and popping symbol tables."""
        # Initial state
        assert len(self.tables) == 1
        assert self.tables[0].scope == Scope.GLOBAL

        # Push local scope
        local_table = SymbolTable(Scope.LOCAL)
        self.tables.push(local_table)
        assert len(self.tables) == 2
        assert self.tables[1].scope == Scope.LOCAL

        # Push gate scope
        gate_table = SymbolTable(Scope.GATE)
        self.tables.push(gate_table)
        assert len(self.tables) == 3
        assert self.tables[2].scope == Scope.GATE

        # Pop scopes
        self.tables.pop()
        assert len(self.tables) == 2
        assert self.tables[1].scope == Scope.LOCAL

        self.tables.pop()
        assert len(self.tables) == 1
        assert self.tables[0].scope == Scope.GLOBAL

    def test_globals_iterator(self):
        """Test iterating over global symbols."""
        # Add some global symbols
        symbol1 = Symbol("var1", 1, types.Int(), Scope.GLOBAL, None)
        symbol2 = Symbol("var2", 2, types.Int(), Scope.GLOBAL, None)

        self.tables.insert(symbol1)
        self.tables.insert(symbol2)

        # Get all globals
        globals = list(self.tables.globals())

        # Should include builtins and our symbols
        global_names = {s.name for s in globals}
        assert "var1" in global_names
        assert "var2" in global_names
        assert "pi" in global_names


class TestState:
    """Test cases for State class."""

    def setup_method(self):
        """Setup fresh State for each test."""
        self.state = State("test source")

    def test_state_initialization(self):
        """Test State initialization."""
        assert self.state.scope == Scope.GLOBAL
        assert self.state._source == "test source"
        assert isinstance(self.state.circuit, QuantumCircuit)
        assert isinstance(self.state.symbol_table, SymbolTables)
        assert isinstance(self.state.addressing_mode, AddressingMode)
        assert self.state.all_parameters == set()
        assert self.state.qubit_mapping == {}
        assert self.state.next_qubit_index == 0

    def test_allocate_qubit(self):
        """Test qubit allocation."""
        # Allocate first qubit
        index1 = self.state.allocate_qubit("q0")
        assert index1 == 0
        assert self.state.qubit_mapping["q0"] == 0
        assert self.state.next_qubit_index == 1
        assert self.state.circuit.num_qubits == 1

        # Allocate second qubit
        index2 = self.state.allocate_qubit("q1")
        assert index2 == 1
        assert self.state.next_qubit_index == 2
        assert self.state.circuit.num_qubits == 2

        # Re-allocate existing qubit
        index3 = self.state.allocate_qubit("q0")
        assert index3 == 0
        assert self.state.next_qubit_index == 2  # Should not increment

    def test_get_qubit_index(self):
        """Test getting qubit index."""
        # Before allocation
        assert self.state.get_qubit_index("q0") is None

        # After allocation
        self.state.allocate_qubit("q0")
        assert self.state.get_qubit_index("q0") == 0

        # Non-existent qubit
        assert self.state.get_qubit_index("non_existent") is None

    def test_new_with_local_scope(self):
        """Test creating new state with local scope."""
        # Set up some state
        self.state.allocate_qubit("q0")
        self.state.all_parameters.add(Parameter("theta"))

        # Create new state with local scope
        new_state = State.new_with_local_scope(self.state)

        # Verify properties
        assert new_state.scope == Scope.LOCAL
        assert new_state._source == self.state._source
        assert new_state.circuit is self.state.circuit
        assert new_state.addressing_mode is self.state.addressing_mode

        # Should have copied qubit mapping
        assert new_state.qubit_mapping == {"q0": 0}
        assert new_state.next_qubit_index == 1

        # Should have empty parameters set
        assert new_state.all_parameters == set()

        # Symbol table should have new scope
        assert len(new_state.symbol_table) == len(self.state.symbol_table)
        assert new_state.symbol_table._top_symbol_table.scope == Scope.LOCAL

    def test_new_with_gate_scope(self):
        """Test creating new state with gate scope."""
        # Set up some state
        self.state.allocate_qubit("q0")

        # Create new state with gate scope
        new_state = State.new_with_gate_scope(self.state)

        # Verify properties
        assert new_state.scope == Scope.GATE
        assert new_state._source == self.state._source
        assert new_state.addressing_mode is self.state.addressing_mode

        # Should have new circuit
        assert isinstance(new_state.circuit, QuantumCircuit)
        assert new_state.circuit is not self.state.circuit

        # Should have fresh qubit mapping
        assert new_state.qubit_mapping == {}
        assert new_state.next_qubit_index == 0

        # Should have empty parameters set
        assert new_state.all_parameters == set()

        # Symbol table should have new scope
        assert len(new_state.symbol_table) == len(self.state.symbol_table)
        assert new_state.symbol_table._top_symbol_table.scope == Scope.GATE

    def test_unique_name_generation(self):
        """Test unique name generation."""
        # Add a symbol to ensure names are unique
        symbol = Symbol("my_var", 42, types.Int(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Generate unique names
        name1 = self.state.unique_name("prefix")
        name2 = self.state.unique_name("prefix")
        name3 = self.state.unique_name("other")

        # Names should be unique
        assert name1 != name2
        assert name1.startswith("prefix_")
        assert name3.startswith("other_")

        # Generated names should not be in symbol table
        assert name1 not in self.state.symbol_table
        assert name2 not in self.state.symbol_table
        assert name3 not in self.state.symbol_table


class TestLocalScope:
    """Test cases for LocalScope context manager."""

    def test_local_scope_context_manager(self):
        """Test LocalScope as context manager."""
        state = State()

        with LocalScope(state) as local_state:
            # Inside context
            assert local_state.scope == Scope.LOCAL
            assert len(local_state.symbol_table) == len(state.symbol_table)
            assert (
                local_state.symbol_table._top_symbol_table.scope == Scope.LOCAL
            )

        # After context
        assert len(state.symbol_table) == 1
        assert state.symbol_table._top_symbol_table.scope == Scope.GLOBAL

    def test_local_scope_symbol_isolation(self):
        """Test symbol isolation in local scope."""
        state = State()

        # Add global symbol
        global_symbol = Symbol(
            "global_var", 1, types.Int(), Scope.GLOBAL, None
        )
        state.symbol_table.insert(global_symbol)

        with LocalScope(state) as local_state:
            # Add local symbol
            local_symbol = Symbol(
                "local_var", 2, types.Int(), Scope.LOCAL, None
            )
            local_state.symbol_table.insert(local_symbol)

            # Both symbols should be visible in local scope
            assert local_state.symbol_table.get("global_var") is not None
            assert local_state.symbol_table.get("local_var") is not None

        # After context, only global symbol should be visible
        assert state.symbol_table.get("global_var") is not None
        assert state.symbol_table.get("local_var") is None


class TestGateScope:
    """Test cases for GateScope context manager."""

    def test_gate_scope_context_manager(self):
        """Test GateScope as context manager."""
        state = State()

        with GateScope(state) as gate_state:
            # Inside context
            assert gate_state.scope == Scope.GATE
            assert len(gate_state.symbol_table) == len(state.symbol_table)
            assert (
                gate_state.symbol_table._top_symbol_table.scope == Scope.GATE
            )

            # Should have fresh circuit
            assert isinstance(gate_state.circuit, QuantumCircuit)
            assert gate_state.circuit is not state.circuit

        # After context
        assert len(state.symbol_table) == 1
        assert state.symbol_table._top_symbol_table.scope == Scope.GLOBAL

    def test_gate_scope_qubit_isolation(self):
        """Test qubit isolation in gate scope."""
        state = State()
        state.allocate_qubit("q0")

        with GateScope(state) as gate_state:
            # Gate scope should have its own qubit mapping
            assert gate_state.qubit_mapping == {}
            assert gate_state.next_qubit_index == 0

            # Allocate qubit in gate scope
            gate_state.allocate_qubit("internal_q")
            assert gate_state.qubit_mapping["internal_q"] == 0
            assert gate_state.next_qubit_index == 1

        # Original state should be unchanged
        assert state.qubit_mapping == {"q0": 0}
        assert state.next_qubit_index == 1


def test_builtin_constants():
    """Test builtin mathematical constants."""
    assert "pi" in _BUILTINS
    assert "π" in _BUILTINS
    assert "tau" in _BUILTINS
    assert "τ" in _BUILTINS
    assert "euler" in _BUILTINS
    assert "ℇ" in _BUILTINS

    # Check values

    assert _BUILTINS["pi"].data == math.pi
    assert _BUILTINS["π"].data == math.pi
    assert _BUILTINS["tau"].data == math.tau
    assert _BUILTINS["τ"].data == math.tau
    assert _BUILTINS["euler"].data == math.e
    assert _BUILTINS["ℇ"].data == math.e

    # Check types
    for symbol in _BUILTINS.values():
        assert isinstance(symbol.type, types.Float)
        assert symbol.type.const
        assert symbol.scope == Scope.BUILTIN


class TestStateIntegration:
    """Integration tests for State and related classes."""

    def test_complete_workflow(self):
        """Test a complete workflow with State."""
        # Initialize state
        state = State("OPENQASM 3.0;")

        # Set addressing mode
        state.addressing_mode.set_virtual_mode(None)

        # Add parameters
        theta = Parameter("theta")
        state.all_parameters.add(theta)

        # Add parameter to symbol table
        param_symbol = Symbol(
            "theta", theta, types.Angle(), Scope.GLOBAL, None
        )
        state.symbol_table.insert(param_symbol)

        # Allocate qubits
        q0_index = state.allocate_qubit("q[0]")
        q1_index = state.allocate_qubit("q[1]")

        assert q0_index == 0
        assert q1_index == 1
        assert state.circuit.num_qubits == 2

        # Create local scope
        with LocalScope(state) as local_state:
            # Add local variable
            local_symbol = Symbol("local", 42, types.Int(), Scope.LOCAL, None)
            local_state.symbol_table.insert(local_symbol)

            # Verify symbols are accessible
            assert local_state.symbol_table.get("theta") is not None
            assert local_state.symbol_table.get("local") is not None

        # Create gate scope
        with GateScope(state) as gate_state:
            # Gate scope should see const symbols
            assert gate_state.symbol_table.get("pi") is not None

            # Gate scope should not see non-const global symbols
            # (depends on implementation, may raise exception)

            # Allocate qubits in gate scope
            gate_q_index = gate_state.allocate_qubit("a")
            assert gate_q_index == 0
            assert gate_state.circuit.num_qubits == 1

        # Verify original state is unchanged
        assert state.qubit_mapping == {"q[0]": 0, "q[1]": 1}
        assert state.circuit.num_qubits == 2
        assert theta in state.all_parameters

    def test_parameter_expression_integration(self):
        """Test parameter expressions in State context."""
        state = State()

        # Create parameters
        theta = Parameter("theta")
        phi = Parameter("phi")

        # Add to state
        state.all_parameters.add(theta)
        state.all_parameters.add(phi)

        # Create parameter expression
        expr = theta + phi * 2

        # Verify expression
        assert isinstance(expr, ParameterExpression)
        assert str(expr) == "(theta + (phi * 2))"
        assert theta in expr.parameters
        assert phi in expr.parameters
