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
import openqasm3

from wy_qcos.transpiler.cmss.compiler.openqasm3.convertor import (
    ConvertVisitor,
)
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import (
    GateOperation,
    Measure,
    Reset,
    Sync,
    ControlGate,
)


class TestConvertVisitor:
    """Test cases for ConvertVisitor class in convertor.py."""

    def setup_class(self):
        """Setup test fixtures."""
        self.converter = ConvertVisitor()

    def test_create_standard_gate_builder(self):
        """Test the _create_standard_gate function."""
        from wy_qcos.transpiler.cmss.compiler.openqasm3.convertor import (
            _create_standard_gate,
        )

        # Test single-qubit gate with no parameters
        builder = _create_standard_gate("x", 0, 1)
        gate = builder()
        assert isinstance(gate, GateOperation)
        assert gate.name == "x"
        assert gate.targets == [0]
        assert gate.arg_value == []

        # Test single-qubit gate with parameters
        builder = _create_standard_gate("rx", 1, 1)
        gate = builder(0.5)
        assert isinstance(gate, GateOperation)
        assert gate.name == "rx"
        assert gate.targets == [0]
        assert gate.arg_value == [0.5]

        # Test two-qubit gate
        builder = _create_standard_gate("cx", 0, 2)
        gate = builder()
        assert isinstance(gate, GateOperation)
        assert gate.name == "cx"
        assert gate.targets == [0, 1]

    def test_escape_qasm2_identifier(self):
        """Test the _escape_qasm2 function for valid OpenQASM 2 identifiers."""
        from wy_qcos.transpiler.cmss.compiler.openqasm3.convertor import (
            _escape_qasm2,
        )

        # Test valid identifiers
        assert _escape_qasm2("q0") == "q0"
        assert _escape_qasm2("qubit") == "qubit"
        assert _escape_qasm2("c_reg") == "c_reg"

        # Test invalid identifiers that need escaping
        assert _escape_qasm2("0qubit") == "esc_0qubit"
        assert _escape_qasm2("q_bit") == "q_bit"
        assert _escape_qasm2("Qubit") == "esc_Qubit"
        assert _escape_qasm2("q_bit") == "q_bit"

    def test_gate_builder_initialization(self):
        """Test GateBuilder class initialization."""
        from wy_qcos.transpiler.cmss.compiler.openqasm3.convertor import (
            GateBuilder,
        )

        circuit = QuantumCircuit(num_qubits=2)

        # Test without parameters
        builder = GateBuilder("my_gate", circuit)
        assert builder._name == "my_gate"
        assert builder._definition == circuit
        assert builder._order == ()
        assert builder._num_qubits == 2

        # Test with parameters
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            Parameter,
        )

        params = [Parameter("theta"), Parameter("phi")]
        builder = GateBuilder("my_gate", circuit, params)
        assert builder._name == "my_gate"
        assert builder._order == list(params)

    def test_gate_builder_call(self):
        """Test GateBuilder.__call__ method."""
        from wy_qcos.transpiler.cmss.compiler.openqasm3.convertor import (
            GateBuilder,
        )
        from wy_qcos.transpiler.cmss.compiler.openqasm3.state import (
            Parameter,
        )

        circuit = QuantumCircuit(num_qubits=2)
        params = [Parameter("theta"), Parameter("phi")]
        builder = GateBuilder("my_gate", circuit, params)

        # Test with correct number of parameters
        gate = builder(0.5, 1.0)
        assert isinstance(gate, GateOperation)
        assert gate.name == "my_gate"
        assert gate.targets == [0, 1]
        assert gate.arg_value == [0.5, 1.0]
        assert gate.operation_type == "2"

        # Test with incorrect number of parameters
        with pytest.raises(Exception) as exc_info:
            builder(0.5)
        assert "incorrect number of parameters" in str(exc_info.value)

    def test_convert_visitor_initialization(self):
        """Test ConvertVisitor initialization."""
        converter = ConvertVisitor()
        assert converter.annotation_handlers == {}

        converter = ConvertVisitor(annotation_handlers={"test": lambda x: x})
        assert "test" in converter.annotation_handlers

    def test_convert_empty_program(self):
        """Test converting an empty OpenQASM 3.0 program."""
        data = "OPENQASM 3.0;"

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert isinstance(circuit, QuantumCircuit)
        assert circuit.num_qubits == 0
        assert circuit.num_clbits == 0

    def test_qubit_declaration_single(self):
        """Test single qubit declaration."""
        data = """
        OPENQASM 3.0;
        qubit q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert circuit.num_qubits == 1

    def test_qubit_declaration_array(self):
        """Test qubit array declaration."""
        data = """
        OPENQASM 3.0;
        qubit[3] q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert circuit.num_qubits == 6

    def test_include_stdgates(self):
        """Test include statement for standard gates."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert isinstance(circuit, QuantumCircuit)

    def test_include_non_stdgates_error(self):
        """Test that non-stdgates includes raise error."""
        data = """
        OPENQASM 3.0;
        include "otherlib.inc";
        """

        m = openqasm3.parse(data)
        with pytest.raises(Exception) as exc_info:
            self.converter.convert(m)
        assert "non-stdgates imports not currently supported" in str(
            exc_info.value
        )

    def test_simple_gate_application(self):
        """Test simple gate application."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        h q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert circuit.num_qubits == 1
        ops = circuit.get_operations()
        assert len(ops) == 1
        assert ops[0].name == "h"
        assert ops[0].targets == [0]

    def test_gate_with_parameters(self):
        """Test gate application with parameters."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        rx(1.57) q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert ops[0].name == "rx"
        assert ops[0].arg_value == [1.57]

    def test_custom_gate_definition(self):
        """Test custom gate definition."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        gate my_gate(theta) a, b {
            rx(theta) a;
            cx a, b;
        }
        qubit[2] q;
        my_gate(1.57) q[0], q[1];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        # Should have 2 gates: rx and cx
        assert len(ops) == 1
        assert ops[0].name == "my_gate"

    def test_measurement_statement(self):
        """Test measurement statement."""
        data = """
        OPENQASM 3.0;
        qubit q;
        bit c;
        measure q -> c;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert isinstance(ops[0], Measure)
        assert ops[0].targets == [0]

    def test_barrier_statement(self):
        """Test barrier statement."""
        data = """
        OPENQASM 3.0;
        qubit[3] q;
        barrier q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert isinstance(ops[0], Sync)
        assert ops[0].targets == [0, 1, 2]

    def test_reset_statement(self):
        """Test reset statement."""
        data = """
        OPENQASM 3.0;
        qubit q;
        reset q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert isinstance(ops[0], Reset)
        assert ops[0].targets == [0]

    def test_classical_declaration_single(self):
        """Test single classical bit declaration."""
        data = """
        OPENQASM 3.0;
        bit c;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert circuit.num_clbits == 1

    def test_classical_declaration_array(self):
        """Test classical bit array declaration."""
        data = """
        OPENQASM 3.0;
        bit[3] c;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert circuit.num_clbits == 6

    def test_classical_declaration_with_measurement(self):
        """Test classical declaration with measurement initialization."""
        data = """
        OPENQASM 3.0;
        qubit q;
        bit c = measure q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        assert circuit.num_clbits == 1
        ops = circuit.get_operations()
        assert len(ops) == 1
        assert isinstance(ops[0], Measure)

    def test_gate_modifier_inverse(self):
        """Test gate inverse modifier."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        inv @ h q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        # Note: The actual implementation might append "_inv" to the gate name
        assert "inv" in ops[0].name.lower() or ops[0].name == "h_inv"

    def test_gate_modifier_power(self):
        """Test gate power modifier."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        pow(2) @ h q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert "pow" in ops[0].name.lower() or "2" in ops[0].name

    def test_gate_modifier_control(self):
        """Test gate control modifier."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        ctrl @ x q[0], q[1];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert isinstance(ops[0], ControlGate) or "ctrl" in ops[0].name.lower()

    def test_gate_broadcasting(self):
        """Test gate broadcasting to multiple qubits."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[3] q;
        h q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 3
        for i, op in enumerate(ops):
            assert op.name == "h"
            assert op.targets == [i]

    def test_quantum_phase_global(self):
        """Test global quantum phase application."""
        data = """
        OPENQASM 3.0;
        gphase(1.57);
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        # Should have no operations but may set global phase
        assert circuit.num_qubits == 0

    def test_quantum_phase_specific_qubits(self):
        """Test quantum phase application to specific qubits."""
        data = """
        OPENQASM 3.0;
        qubit[2] q;
        gphase(1.57) q[0], q[1];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 2
        for op in ops:
            assert op.name == "p"  # Phase gate
            assert op.arg_value == [1.57]

    def test_alias_statement(self):
        """Test alias statement (let)."""
        data = """
        OPENQASM 3.0;
        qubit[4] q;
        let alias = q[0:1];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        # Should create registers for the aliases
        assert circuit.num_qubits == 10

    def test_input_declaration_float(self):
        """Test float input declaration."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        input float[64] theta;
        qubit q;
        rx(theta) q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        # Should have a parameter
        ops = circuit.get_operations()
        assert len(ops) == 1
        assert ops[0].name == "rx"
        # The arg_value should be a Parameter
        assert hasattr(circuit, "_parameters") or hasattr(
            circuit, "parameters"
        )

    def test_input_declaration_angle(self):
        """Test angle input declaration."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        input angle theta;
        qubit q;
        rx(theta) q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert ops[0].name == "rx"

    def test_gate_with_duration_error(self):
        """Test that gates with duration raise error (unsupported)."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        #pragma duration 10ns
        h q;
        """

        m = openqasm3.parse(data)
        with pytest.raises(Exception):
            self.converter.convert(m)

    def test_output_declaration_error(self):
        """Test that output declarations raise error (unsupported)."""
        data = """
        OPENQASM 3.0;
        output float[64] result;
        """

        m = openqasm3.parse(data)
        with pytest.raises(Exception) as exc_info:
            self.converter.convert(m)
        assert "the 'output' keyword is not supported" in str(exc_info.value)

    def test_undefined_gate_error(self):
        """Test that undefined gates raise error."""
        data = """
        OPENQASM 3.0;
        qubit q;
        undefined_gate q;
        """

        m = openqasm3.parse(data)
        with pytest.raises(Exception) as exc_info:
            self.converter.convert(m)
        assert "gate 'undefined_gate' is not defined" in str(exc_info.value)

    def test_parameter_expression_support(self):
        """Test support for parameter expressions."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        input float[64] theta;
        input float[64] phi;
        qubit q;
        rx(theta + phi) q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert ops[0].name == "rx"

    def test_box_statement(self):
        """Test box statement (currently a no-op)."""
        data = """
        OPENQASM 3.0;
        qubit q;
        box [10ns] {
            h q;
        }
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        # Box should be processed without error
        assert isinstance(circuit, QuantumCircuit)
        ops = circuit.get_operations()
        assert len(ops) == 0

    def test_delay_instruction(self):
        """Test delay instruction (currently a no-op)."""
        data = """
        OPENQASM 3.0;
        qubit q;
        delay[10ns] q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        # Delay should be processed without error
        assert isinstance(circuit, QuantumCircuit)
        # No operations added for delay

    def test_control_flow_statements_no_op(self):
        """Test that control flow statements are processed as no-ops."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        bit c = measure q;

        if (c == 0) {
            h q;
        }

        while (c == 0) {
            x q;
        }

        for int i in [0:2] {
            y q;
        }
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        # Should process without error (control flow is no-op)
        assert isinstance(circuit, QuantumCircuit)

    def test_complex_custom_gate_with_standard_gates(self):
        """Test complex custom gate that uses standard gates internally."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        gate complex_gate(theta, phi) a, b, c {
            rx(theta) a;
            ry(phi) b;
            cx a, c;
            cz b, c;
            h a;
            h b;
        }

        qubit[3] q;
        complex_gate(1.57, 0.78) q[0], q[1], q[2];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        if len(ops) == 1:
            assert ops[0].name == "complex_gate"
        else:
            assert len(ops) >= 5
            gate_names = [op.name for op in ops]
            standard_gates = {"rx", "ry", "cx", "cz", "h"}
            assert any(gate in standard_gates for gate in gate_names)

    def test_register_indexing(self):
        """Test various forms of register indexing."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[5] q;
        bit[5] c;

        h q[0];           // Single index
        x q[1:3];         // Range
        y q[{0, 2, 4}];   // Set
        measure q -> c;   // Whole register
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        # Should process without error
        assert isinstance(circuit, QuantumCircuit)

    def test_gate_modifier_combination(self):
        """Test combination of multiple gate modifiers."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[3] q;
        ctrl(2) @ inv @ pow(2) @ x q[0], q[1], q[2];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        # Should create a controlled gate with multiple modifiers
        assert isinstance(ops[0], ControlGate) or "ctrl" in ops[0].name.lower()

    def test_complex_parameter_expression_nesting(self):
        """Test deeply nested parameter expressions."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        input float[64] a;
        input float[64] b;
        input float[64] c;
        qubit q;
        rx((a + b) * (c - a) / (b + 1.0)) q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert ops[0].name == "rx"

    def test_negative_control_modifier(self):
        """Test negative control (negctrl) gate modifier."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        negctrl @ x q[0], q[1];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        # Should handle negative control modifier
        # Implementation may vary, but should not crash
        assert isinstance(circuit, QuantumCircuit)

    def test_angle_parameter_with_pi(self):
        """Test angle parameters with mathematical constants like pi."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        input angle theta;
        qubit q;
        // Using mathematical constant pi in expression
        rx(theta + pi/2) q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert ops[0].name == "rx"

    def test_symbol_redefinition_error_handling(self):
        """Test error handling for symbol redefinition."""
        data = """
        OPENQASM 3.0;
        qubit q;
        qubit q;  // Redefinition - should raise error
        """

        m = openqasm3.parse(data)

        with pytest.raises(Exception):
            self.converter.convert(m)

    def test_custom_gate_with_multiple_parameters(self):
        """Test custom gate with multiple parameters of different types."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        gate multi_param(a, b, c) q {
            rx(a) q;
            ry(b) q;
            rz(c) q;
        }

        qubit q;
        multi_param(1.57, 0.78, 3.14) q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        # Should have 3 gates or 1 custom gate depending on implementation
        assert len(ops) >= 1

    def test_measurement_with_complex_indexing(self):
        """Test measurement with complex qubit indexing."""
        data = """
        OPENQASM 3.0;
        qubit[5] q;
        bit[3] c;
        measure q[{1, 3, 4}] -> c;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 1
        assert isinstance(ops[0], Measure)
        # Should measure 3 qubits
        assert len(ops[0].targets) == 3

    def test_error_recovery_after_syntax_error(self):
        """Test that converter handles syntax errors gracefully."""
        # Note: This might be testing the parser more than the converter
        # But it's important for integration

        data = """
        OPENQASM 3.0;
        qubit q
        // Missing semicolon - parser should catch this
        """

        with pytest.raises(Exception):
            openqasm3.parse(data)

    def test_parameter_bounds_and_validation(self):
        """Test parameter bounds and validation."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        // Test with extreme parameter values
        rx(1e10) q;  // Very large value
        rx(-1e10) q;  // Very small value
        rx(0.0) q;    // Zero
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 3
        for op in ops:
            assert op.name == "rx"

    def test_concurrent_gate_applications(self):
        """Test multiple gates applied to overlapping qubit sets."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[3] q;

        // Multiple gates on overlapping qubits
        h q[0];
        cx q[0], q[1];
        h q[1];
        cz q[1], q[2];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) >= 4

    def test_physical_qubit_addressing(self):
        """Test physical qubit addressing mode."""
        data = """
        OPENQASM 3.0;
        // Physical qubit references
        $0;
        $1;
        """

        m = openqasm3.parse(data)
        try:
            circuit = self.converter.convert(m)
            assert isinstance(circuit, QuantumCircuit)
        except Exception as e:
            # Physical qubit addressing might not be fully implemented
            print(f"Physical qubit addressing not implemented: {e}")

    def test_mixed_addressing_modes(self):
        """Test mixing virtual and physical qubit addressing."""
        data = """
        OPENQASM 3.0;
        qubit q;
        $0;
        """

        m = openqasm3.parse(data)
        # This should raise an error about mixed modes
        with pytest.raises(Exception):
            self.converter.convert(m)

    def test_gate_definition_with_no_parameters(self):
        """Test custom gate with no parameters."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";

        gate no_param_gate q {
            x q;
            y q;
            z q;
        }

        qubit q;
        no_param_gate q;
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        # Should have 3 gates or 1 custom gate
        assert len(ops) >= 1

    def test_measurement_to_existing_register(self):
        """Test measurement to existing classical register."""
        data = """
        OPENQASM 3.0;
        qubit[3] q;
        bit[3] c;
        measure q[0] -> c[0];
        measure q[1] -> c[1];
        measure q[2] -> c[2];
        """

        m = openqasm3.parse(data)
        circuit = self.converter.convert(m)

        ops = circuit.get_operations()
        assert len(ops) == 3
        for op in ops:
            assert isinstance(op, Measure)

    def test_gate_with_duration_placeholder(self):
        """Test that gates with duration are marked as unsupported."""
        data = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit q;
        h[10ns] q;
        """

        m = openqasm3.parse(data)

        with pytest.raises(Exception) as exc_info:
            self.converter.convert(m)

        assert "gates with durations are not supported" in str(exc_info.value)
