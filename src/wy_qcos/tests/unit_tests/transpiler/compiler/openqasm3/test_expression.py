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

import pytest
from openqasm3 import ast

from wy_qcos.transpiler.cmss.compiler.openqasm3.expression import (
    ValueResolver,
    resolve_condition,
    join_integer_types,
    join_numeric_types,
)
from wy_qcos.transpiler.cmss.compiler.openqasm3 import types
from wy_qcos.transpiler.cmss.compiler.openqasm3.state import State, Parameter
from wy_qcos.transpiler.cmss.compiler.openqasm3.data import Symbol, Scope


class TestExpression:
    """Test cases for expression parsing and value resolution."""

    def setup_class(self):
        """Setup test fixtures."""
        self.state = State()
        # Add some test symbols to the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

    def test_join_integer_types(self):
        """Test joining integer types."""
        # Test with two Uint types
        uint1 = types.Uint(const=True, size=8)
        uint2 = types.Uint(const=True, size=16)
        result = join_integer_types(uint1, uint2)
        assert isinstance(result, types.Uint)
        assert result.const
        assert result.size == 16  # max(8, 16)

        # Test with Int and Uint
        int_type = types.Int(const=False, size=32)
        result = join_integer_types(uint1, int_type)
        assert isinstance(result, types.Int)
        assert not result.const
        assert result.size == 32

        # Test with Never type
        never_type = types.Never()
        result = join_integer_types(never_type, uint1)
        assert result == uint1

    def test_join_numeric_types(self):
        """Test joining numeric types."""
        # Test with two Float types
        float1 = types.Float(const=True, size=32)
        float2 = types.Float(const=False, size=64)
        result = join_numeric_types(float1, float2)
        assert isinstance(result, types.Float)
        assert not result.const
        assert result.size == 64

        # Test with Float and Int
        int_type = types.Int(const=True, size=16)
        result = join_numeric_types(float1, int_type)
        assert isinstance(result, types.Float)
        assert result.const
        assert result.size == 32

    def test_value_resolver_initialization(self):
        """Test ValueResolver initialization."""
        resolver = ValueResolver(self.state, strict=True)
        assert resolver._context == self.state
        assert resolver._strict

        resolver = ValueResolver(self.state, strict=False)
        assert not resolver._strict

    def test_resolve_method(self):
        """Test the resolve method entry point."""
        resolver = ValueResolver(self.state, strict=True)

        # Test with integer literal
        int_node = ast.IntegerLiteral(value=42)
        value, type_info = resolver.resolve(int_node)

        assert value == 42
        assert isinstance(type_info, types.Int)
        assert type_info.const

    def test_visit_integer_literal(self):
        """Test integer literal parsing."""
        resolver = ValueResolver(self.state, strict=True)

        node = ast.IntegerLiteral(value=123)
        value, type_info = resolver.visit(node)

        assert value == 123
        assert isinstance(type_info, types.Int)
        assert type_info.const

    def test_visit_float_literal(self):
        """Test float literal parsing."""
        resolver = ValueResolver(self.state, strict=True)

        node = ast.FloatLiteral(value=3.14)
        value, type_info = resolver.visit(node)

        assert value == 3.14
        assert isinstance(type_info, types.Float)
        assert type_info.const

    def test_visit_boolean_literal(self):
        """Test boolean literal parsing."""
        resolver = ValueResolver(self.state, strict=True)

        # Test true
        node = ast.BooleanLiteral(value=True)
        value, type_info = resolver.visit(node)
        assert value
        assert isinstance(type_info, types.Bool)
        assert type_info.const

        # Test false
        node = ast.BooleanLiteral(value=False)
        value, type_info = resolver.visit(node)
        assert not value
        assert isinstance(type_info, types.Bool)
        assert type_info.const

    def test_visit_bitstring_literal(self):
        """Test bitstring literal parsing."""
        resolver = ValueResolver(self.state, strict=True)

        node = ast.BitstringLiteral(value=0b1010, width=4)
        value, type_info = resolver.visit(node)

        assert value == 0b1010
        assert isinstance(type_info, types.Uint)
        assert type_info.const
        assert type_info.size == 4

    def test_visit_discrete_set(self):
        """Test discrete set parsing."""
        resolver = ValueResolver(self.state, strict=True)

        # Create integer literal nodes
        int1 = ast.IntegerLiteral(value=1)
        int2 = ast.IntegerLiteral(value=2)
        int3 = ast.IntegerLiteral(value=3)

        node = ast.DiscreteSet(values=[int1, int2, int3])
        value, type_info = resolver.visit(node)

        assert value == (1, 2, 3)
        assert isinstance(type_info, types.Sequence)
        assert isinstance(type_info.base, (types.Int, types.Uint))
        assert type_info.base.const

    def test_visit_range_definition(self):
        """Test range definition parsing."""
        resolver = ValueResolver(self.state, strict=True)

        # Test simple range
        start = ast.IntegerLiteral(value=0)
        end = ast.IntegerLiteral(value=5)
        node = ast.RangeDefinition(start=start, end=end, step=None)
        value, type_info = resolver.visit(node)

        assert isinstance(value, slice)
        assert value.start == 0
        assert value.stop == 6  # OpenQASM ranges are inclusive, so +1
        assert value.step is None
        assert isinstance(type_info, types.Range)

        # Test range with step
        step = ast.IntegerLiteral(value=2)
        node = ast.RangeDefinition(start=start, end=end, step=step)
        value, type_info = resolver.visit(node)

        assert value.step == 2

    def test_visit_identifier(self):
        """Test identifier parsing."""
        resolver = ValueResolver(self.state, strict=True)

        # Add a symbol to the state
        param = Parameter("theta")
        symbol = Symbol("theta", param, types.Angle(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        node = ast.Identifier(name="theta")
        value, type_info = resolver.visit(node)

        assert value == param
        assert isinstance(type_info, types.Angle)

    def test_visit_unary_expression_minus(self):
        """Test unary minus expression."""
        resolver = ValueResolver(self.state, strict=True)

        # Test with integer
        int_node = ast.IntegerLiteral(value=5)
        node = ast.UnaryExpression(
            op=ast.UnaryOperator["-"], expression=int_node
        )
        value, type_info = resolver.visit(node)

        assert value == -5
        assert isinstance(type_info, types.Int)
        assert type_info.const

        # Test with float
        float_node = ast.FloatLiteral(value=3.14)
        node = ast.UnaryExpression(
            op=ast.UnaryOperator["-"], expression=float_node
        )
        value, type_info = resolver.visit(node)

        assert value == -3.14
        assert isinstance(type_info, types.Float)
        assert type_info.const

    def test_visit_binary_expression_addition(self):
        """Test binary addition expression."""
        resolver = ValueResolver(self.state, strict=True)

        # Integer addition
        lhs = ast.IntegerLiteral(value=2)
        rhs = ast.IntegerLiteral(value=3)
        node = ast.BinaryExpression(
            op=ast.BinaryOperator["+"], lhs=lhs, rhs=rhs
        )
        value, type_info = resolver.visit(node)

        assert value == 5
        assert isinstance(type_info, types.Int)
        assert type_info.const

        # Float addition
        lhs = ast.FloatLiteral(value=1.5)
        rhs = ast.FloatLiteral(value=2.5)
        node = ast.BinaryExpression(
            op=ast.BinaryOperator["+"], lhs=lhs, rhs=rhs
        )
        value, type_info = resolver.visit(node)

        assert value == 4.0
        assert isinstance(type_info, types.Float)
        assert type_info.const

    def test_visit_binary_expression_subtraction(self):
        """Test binary subtraction expression."""
        resolver = ValueResolver(self.state, strict=True)

        lhs = ast.IntegerLiteral(value=10)
        rhs = ast.IntegerLiteral(value=3)
        node = ast.BinaryExpression(
            op=ast.BinaryOperator["-"], lhs=lhs, rhs=rhs
        )
        value, type_info = resolver.visit(node)

        assert value == 7
        assert isinstance(type_info, types.Int)
        assert type_info.const

    def test_visit_binary_expression_multiplication(self):
        """Test binary multiplication expression."""
        resolver = ValueResolver(self.state, strict=True)

        lhs = ast.IntegerLiteral(value=3)
        rhs = ast.IntegerLiteral(value=4)
        node = ast.BinaryExpression(
            op=ast.BinaryOperator["*"], lhs=lhs, rhs=rhs
        )
        value, type_info = resolver.visit(node)

        assert value == 12
        assert type_info.const

    def test_visit_binary_expression_division(self):
        """Test binary division expression."""
        resolver = ValueResolver(self.state, strict=True)

        lhs = ast.IntegerLiteral(value=10)
        rhs = ast.IntegerLiteral(value=2)
        node = ast.BinaryExpression(
            op=ast.BinaryOperator["/"], lhs=lhs, rhs=rhs
        )
        value, type_info = resolver.visit(node)

        assert value == 5.0
        assert type_info.const

    def test_generic_visit_error(self):
        """Test that generic_visit raises error for unsupported nodes."""
        resolver = ValueResolver(self.state, strict=True)

        # Create a dummy node that doesn't have a visitor method
        class DummyNode(ast.QASMNode):
            pass

        dummy_node = DummyNode()

        with pytest.raises(Exception) as exc_info:
            resolver.visit(dummy_node)

        assert "cannot be resolved into a value" in str(exc_info.value)

    def test_resolve_condition_bit_equal_bool(self):
        """Test resolve_condition with bit == bool."""
        # Setup: create a bit in the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

        # Add a bit symbol
        bit_index = 0
        symbol = Symbol("c", bit_index, types.Bit(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Create condition: c == true
        bit_node = ast.Identifier(name="c")
        bool_node = ast.BooleanLiteral(value=True)

        condition = ast.BinaryExpression(
            op=ast.BinaryOperator["=="], lhs=bit_node, rhs=bool_node
        )

        result = resolve_condition(condition, self.state)

        assert result == (0, True)

    def test_resolve_condition_bit_not_equal_bool(self):
        """Test resolve_condition with bit != bool."""
        # Setup: create a bit in the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

        # Add a bit symbol
        bit_index = 0
        symbol = Symbol("c", bit_index, types.Bit(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Create condition: c != true (which becomes c == false)
        bit_node = ast.Identifier(name="c")
        bool_node = ast.BooleanLiteral(value=True)

        condition = ast.BinaryExpression(
            op=ast.BinaryOperator["!="], lhs=bit_node, rhs=bool_node
        )

        result = resolve_condition(condition, self.state)

        assert result == (0, False)  # c != true is equivalent to c == false

    def test_resolve_condition_bitarray_equal_int(self):
        """Test resolve_condition with bitarray == int."""
        # Setup: create a bit array in the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

        # Add a bit array symbol
        bits = [0, 1, 2]
        symbol = Symbol("c", bits, types.BitArray(3), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Create condition: c == 3
        bitarray_node = ast.Identifier(name="c")
        int_node = ast.IntegerLiteral(value=3)

        condition = ast.BinaryExpression(
            op=ast.BinaryOperator["=="], lhs=bitarray_node, rhs=int_node
        )

        result = resolve_condition(condition, self.state)

        assert result == ((0, 1, 2), 3)

    def test_resolve_condition_single_bit(self):
        """Test resolve_condition with single bit (no comparison)."""
        # Setup: create a bit in the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

        # Add a bit symbol
        bit_index = 0
        symbol = Symbol("c", bit_index, types.Bit(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Create condition: just the bit (implies c == true)
        bit_node = ast.Identifier(name="c")

        result = resolve_condition(bit_node, self.state)

        assert result == (0, True)

    def test_resolve_condition_negated_bit(self):
        """Test resolve_condition with negated bit (~c)."""
        # Setup: create a bit in the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

        # Add a bit symbol
        bit_index = 0
        symbol = Symbol("c", bit_index, types.Bit(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Create condition: ~c (implies c == false)
        bit_node = ast.Identifier(name="c")
        neg_node = ast.UnaryExpression(
            op=ast.UnaryOperator["~"], expression=bit_node
        )

        result = resolve_condition(neg_node, self.state)

        assert result == (0, False)

    def test_resolve_condition_error_unsupported_comparison(self):
        """Test resolve_condition error for unsupported comparison."""
        # Setup: create a bit in the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

        # Add a bit symbol
        bit_index = 0
        symbol = Symbol("c", bit_index, types.Bit(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Create condition: c < 1 (unsupported operator)
        bit_node = ast.Identifier(name="c")
        int_node = ast.IntegerLiteral(value=1)

        condition = ast.BinaryExpression(
            op=ast.BinaryOperator["<"], lhs=bit_node, rhs=int_node
        )

        with pytest.raises(Exception) as exc_info:
            resolve_condition(condition, self.state)

        assert "unhandled binary operator" in str(exc_info.value)

    def test_resolve_condition_error_bitarray_not_equal(self):
        """Test resolve_condition error for bitarray != int."""
        # Setup: create a bit array in the state
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            SymbolTables,
        )

        self.state.symbol_table = SymbolTables()

        # Add a bit array symbol
        bits = [0, 1, 2]
        symbol = Symbol("c", bits, types.BitArray(3), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Create condition: c != 3 (unsupported for bit arrays)
        bitarray_node = ast.Identifier(name="c")
        int_node = ast.IntegerLiteral(value=3)

        condition = ast.BinaryExpression(
            op=ast.BinaryOperator["!="], lhs=bitarray_node, rhs=int_node
        )

        with pytest.raises(Exception) as exc_info:
            resolve_condition(condition, self.state)

        assert "only '==' is supported" in str(exc_info.value)

    def test_strict_mode_angle_float_operations(self):
        """Test strict mode for angle-float operations."""
        # Test in strict mode (should not allow angle + float)
        resolver_strict = ValueResolver(self.state, strict=True)

        # Create angle and float nodes
        angle_node = ast.Identifier(name="theta")
        float_node = ast.FloatLiteral(value=1.5)

        # Setup: add angle parameter
        param = Parameter("theta")
        symbol = Symbol("theta", param, types.Angle(), Scope.GLOBAL, None)
        self.state.symbol_table.insert(symbol)

        # Test addition in strict mode
        node = ast.BinaryExpression(
            op=ast.BinaryOperator["+"], lhs=angle_node, rhs=float_node
        )

        # In strict mode, this should return None, types.Error
        _, type_info = resolver_strict.visit(node)
        assert isinstance(type_info, types.Angle)

        # Test in non-strict mode (should allow angle + float)
        resolver_non_strict = ValueResolver(self.state, strict=False)
        _, type_info = resolver_non_strict.visit(node)

        # In non-strict mode, this should be allowed
        assert isinstance(type_info, types.Angle)

    def test_type_error_handling(self):
        """Test type error handling."""
        resolver = ValueResolver(self.state, strict=True)

        # Create an expression that will cause a type error
        # e.g., adding a boolean to an integer
        bool_node = ast.BooleanLiteral(value=True)
        int_node = ast.IntegerLiteral(value=5)

        node = ast.BinaryExpression(
            op=ast.BinaryOperator["+"], lhs=bool_node, rhs=int_node
        )

        # This should raise an exception due to type error
        with pytest.raises(Exception) as exc_info:
            resolver.visit(node)

        # Verify the exception message contains "type error"
        assert "type error" in str(exc_info.value)

    def test_nested_expressions(self):
        """Test nested expressions."""
        resolver = ValueResolver(self.state, strict=True)

        # Create nested expression: (2 + 3) * 4
        two = ast.IntegerLiteral(value=2)
        three = ast.IntegerLiteral(value=3)
        four = ast.IntegerLiteral(value=4)

        inner = ast.BinaryExpression(
            op=ast.BinaryOperator["+"], lhs=two, rhs=three
        )

        outer = ast.BinaryExpression(
            op=ast.BinaryOperator["*"], lhs=inner, rhs=four
        )

        value, type_info = resolver.visit(outer)

        assert value == 20
        assert isinstance(type_info, types.Angle)
        assert type_info.const
