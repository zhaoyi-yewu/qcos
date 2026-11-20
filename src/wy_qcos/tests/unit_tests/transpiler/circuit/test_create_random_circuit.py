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

"""Tests for the random circuit creation command-line interface."""

import argparse
from builtins import FileNotFoundError
from unittest.mock import patch

import pytest

from wy_qcos.transpiler.cmss.create_random_circuit import (
    main,
    parse_args,
    parse_basis_gates,
    validate_args,
    validate_depth_mode,
    validate_gates_mode,
    view_qasm,
)
from wy_qcos.transpiler.cmss.circuit.utils import RandomCircuitGen


class TestParseArgs:
    """Tests for command-line argument parsing."""

    def test_missing_q_arg_defaults_to_none(self):
        """Test that a missing qubit argument defaults to none."""
        args = parse_args(["-d", "5"])
        assert args.num_qubits is None
        assert args.depth == 5

    def test_parse_view_mode(self):
        """Test parsing view mode arguments."""
        args = parse_args(["-v", "circuit.qasm"])
        assert args.view == "circuit.qasm"
        assert args.num_qubits is None
        assert args.depth is None
        assert args.num_gates is None

    def test_parse_view_with_other_args(self):
        """Test parsing view mode with generation arguments."""
        args = parse_args(["-v", "circuit.qasm", "-q", "5", "-d", "8"])
        assert args.view == "circuit.qasm"
        assert args.num_qubits == 5
        assert args.depth == 8

    def test_parse_depth_mode(self):
        """Test parsing depth mode arguments."""
        args = parse_args(["-q", "5", "-d", "8", "-t", "1", "-n", "0.3"])
        assert args.num_qubits == 5
        assert args.depth == 8
        assert args.num_gates is None
        assert args.gate_type == 1
        assert args.density == 0.3

    def test_parse_gates_mode(self):
        """Test parsing gate count mode arguments."""
        args = parse_args(["-q", "5", "-g", "10", "-b", "x,h,cx"])
        assert args.num_qubits == 5
        assert args.depth is None
        assert args.num_gates == 10
        assert args.basis_gates == "x,h,cx"

    def test_parse_default_values(self):
        """Test parsing optional argument default values."""
        args = parse_args(["-q", "5", "-d", "8"])
        assert args.gate_type is None
        assert args.density is None
        assert args.seed is None
        assert args.outfile is None
        assert args.basis_gates is None


class TestValidateArgs:
    """Tests for general argument validation."""

    def test_both_depth_and_gates(self):
        """Test that depth and gate count together are rejected."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=8,
            num_gates=10,
            density=None,
            basis_gates=None,
            gate_type=None,
            seed=None,
            outfile=None,
        )
        with pytest.raises(SystemExit):
            validate_args(ns)

    def test_neither_depth_nor_gates_error(self):
        """Test that omitting depth and gate count is rejected."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=None,
            num_gates=None,
            density=None,
            basis_gates=None,
            gate_type=None,
            seed=None,
            outfile=None,
        )
        with pytest.raises(SystemExit):
            validate_args(ns)

    def test_depth_only_passes(self):
        """Test that depth-only arguments pass validation."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=8,
            num_gates=None,
            density=None,
            basis_gates=None,
            gate_type=None,
            seed=None,
            outfile=None,
        )
        validate_args(ns)

    def test_gates_only_passes(self):
        """Test that gate-count-only arguments pass validation."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=None,
            num_gates=10,
            density=None,
            basis_gates=None,
            gate_type=None,
            seed=None,
            outfile=None,
        )
        validate_args(ns)


class TestValidateDepthMode:
    """Tests for depth mode argument validation."""

    def test_basis_gates_in_depth_mode_error(self):
        """Test that incompatible basis gates are rejected in depth mode."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=8,
            num_gates=None,
            density=None,
            basis_gates="x,h",
            gate_type=0,
            seed=None,
            outfile=None,
        )
        with pytest.raises(SystemExit):
            validate_depth_mode(ns)

    def test_no_basis_gates_in_depth_mode_passes(self):
        """Test that depth mode passes without basis gates."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=8,
            num_gates=None,
            density=None,
            basis_gates=None,
            gate_type=None,
            seed=None,
            outfile=None,
        )
        validate_depth_mode(ns)

    def test_basis_gates_with_gate_type_2_passes(self):
        """Test that basis gates pass with gate type two."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=8,
            num_gates=None,
            density=None,
            basis_gates="x,h,cx",
            gate_type=2,
            seed=None,
            outfile=None,
        )
        validate_depth_mode(ns)

    def test_basis_gates_with_gate_type_none_error(self):
        """Test that basis gates require an explicit gate type."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=8,
            num_gates=None,
            density=None,
            basis_gates="x,h",
            gate_type=None,
            seed=None,
            outfile=None,
        )
        with pytest.raises(SystemExit):
            validate_depth_mode(ns)


class TestValidateGatesMode:
    """Tests for gate count mode argument validation."""

    def test_density_in_gates_mode_error(self):
        """Test that density is rejected in gate count mode."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=None,
            num_gates=10,
            density=0.3,
            basis_gates=None,
            gate_type=None,
            seed=None,
            outfile=None,
        )
        with pytest.raises(SystemExit):
            validate_gates_mode(ns)

    def test_gate_type_in_gates_mode_error(self):
        """Test that gate type is rejected in gate count mode."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=None,
            num_gates=10,
            density=None,
            basis_gates=None,
            gate_type=1,
            seed=None,
            outfile=None,
        )
        with pytest.raises(SystemExit):
            validate_gates_mode(ns)

    def test_default_values_in_gates_mode_passes(self):
        """Test that default optional values pass gate count validation."""
        ns = argparse.Namespace(
            num_qubits=5,
            depth=None,
            num_gates=10,
            density=None,
            basis_gates=None,
            gate_type=None,
            seed=None,
            outfile=None,
        )
        validate_gates_mode(ns)


class TestParseBasisGates:
    """Tests for basis gate list parsing."""

    def test_none_returns_none(self):
        """Test that an absent basis gate value returns none."""
        assert parse_basis_gates(None) is None

    def test_parse_comma_separated(self):
        """Test parsing comma-separated basis gates."""
        result = parse_basis_gates("x,h,cx")
        assert result == ("x", "h", "cx")

    def test_parse_with_spaces(self):
        """Test parsing basis gates with surrounding spaces."""
        result = parse_basis_gates("x, h , cx")
        assert result == ("x", "h", "cx")


class TestMain:
    """Tests for the random circuit creation entry point."""

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_depth_mode_success(self, MockRCG):
        """Test successful circuit generation in depth mode."""
        mock_rcg = MockRCG.return_value
        mock_rcg.num_qubits = 5
        mock_rcg.depth = 8
        mock_rcg.size = 27

        main(["-q", "5", "-d", "8", "-t", "1", "-n", "0.3", "-s", "42"])

        mock_rcg.random_circuit_with_depth.assert_called_once_with(
            num_qubits=5,
            depth=8,
            gate_type=1,
            density=0.3,
            seed=42,
            outfile=None,
        )
        mock_rcg.random_circuit_with_gates.assert_not_called()

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_gates_mode_success(self, MockRCG):
        """Test successful circuit generation in gate count mode."""
        mock_rcg = MockRCG.return_value
        mock_rcg.num_qubits = 5
        mock_rcg.depth = 3
        mock_rcg.size = 10

        main(["-q", "5", "-g", "10", "-b", "x,h,cx", "-s", "42"])

        mock_rcg.random_circuit_with_gates.assert_called_once_with(
            num_qubits=5,
            num_gates=10,
            basis_gates=("x", "h", "cx"),
            seed=42,
            outfile=None,
        )
        mock_rcg.random_circuit_with_depth.assert_not_called()

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_gates_mode_default_basis(self, MockRCG):
        """Test gate count mode with the default basis gates."""
        mock_rcg = MockRCG.return_value
        mock_rcg.num_qubits = 5
        mock_rcg.depth = 3
        mock_rcg.size = 10

        main(["-q", "5", "-g", "10"])

        mock_rcg.random_circuit_with_gates.assert_called_once_with(
            num_qubits=5,
            num_gates=10,
            seed=None,
            outfile=None,
        )
        mock_rcg.random_circuit_with_depth.assert_not_called()

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_depth_mode_default_values(self, MockRCG):
        """Test depth mode with default optional values."""
        mock_rcg = MockRCG.return_value
        mock_rcg.num_qubits = 5
        mock_rcg.depth = 8
        mock_rcg.size = 27

        main(["-q", "5", "-d", "8"])

        mock_rcg.random_circuit_with_depth.assert_called_once_with(
            num_qubits=5,
            depth=8,
            gate_type=0,
            density=0.05,
            seed=None,
            outfile=None,
        )
        mock_rcg.random_circuit_with_gates.assert_not_called()

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_depth_mode_with_basis_gates_error(self, MockRCG):
        """Test that incompatible depth mode basis gates are rejected."""
        with pytest.raises(SystemExit):
            main(["-q", "5", "-d", "8", "-t", "0", "-b", "x,h"])

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_depth_mode_custom_gates_success(self, MockRCG):
        """Test depth mode with valid custom gates."""
        mock_rcg = MockRCG.return_value
        mock_rcg.num_qubits = 5
        mock_rcg.depth = 8
        mock_rcg.size = 15

        main(["-q", "5", "-d", "8", "-t", "2", "-b", "x,h,cx", "-s", "42"])

        mock_rcg.random_circuit_with_depth.assert_called_once_with(
            num_qubits=5,
            depth=8,
            gate_type=2,
            density=0.05,
            seed=42,
            outfile=None,
            custom_gates=("x", "h", "cx"),
        )
        mock_rcg.random_circuit_with_gates.assert_not_called()

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_depth_mode_custom_gates_wrong_gate_type_error(self, MockRCG):
        """Test that custom gates with the wrong gate type are rejected."""
        with pytest.raises(SystemExit):
            main(["-q", "5", "-d", "8", "-b", "x,h"])

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_gates_mode_with_density_error(self, MockRCG):
        """Test that density in gate count mode is rejected."""
        with pytest.raises(SystemExit):
            main(["-q", "5", "-g", "10", "-n", "0.3"])

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_gates_mode_with_gate_type_error(self, MockRCG):
        """Test that gate type in gate count mode is rejected."""
        with pytest.raises(SystemExit):
            main(["-q", "5", "-g", "10", "-t", "1"])

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_both_depth_and_gates_error(self, MockRCG):
        """Test that specifying both generation modes is rejected."""
        with pytest.raises(SystemExit):
            main(["-q", "5", "-d", "8", "-g", "10"])

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_neither_depth_nor_gates_error(self, MockRCG):
        """Test that omitting both generation modes is rejected."""
        with pytest.raises(SystemExit):
            main(["-q", "5"])

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_with_outfile(self, MockRCG):
        """Test passing an output file to the circuit generator."""
        mock_rcg = MockRCG.return_value
        mock_rcg.num_qubits = 5
        mock_rcg.depth = 8
        mock_rcg.size = 27

        main(["-q", "5", "-d", "8", "-f", "test.qasm"])

        mock_rcg.random_circuit_with_depth.assert_called_once_with(
            num_qubits=5,
            depth=8,
            gate_type=0,
            density=0.05,
            seed=None,
            outfile="test.qasm",
        )

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    def test_missing_q_in_main_error(self, MockRCG):
        """Test that a missing qubit argument is rejected by main."""
        with pytest.raises(SystemExit):
            main(["-d", "5"])

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.view_qasm")
    def test_view_mode_calls_view_qasm(self, mock_view):
        """Test that view mode calls the QASM viewer."""
        main(["-v", "circuit.qasm"])
        mock_view.assert_called_once_with("circuit.qasm")

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.view_qasm")
    def test_view_mode_skips_validation(self, mock_view):
        """Test that view mode skips generation argument validation."""
        main(["-v", "circuit.qasm"])
        mock_view.assert_called_once()

    @patch("wy_qcos.transpiler.cmss.create_random_circuit.RandomCircuitGen")
    @patch("wy_qcos.transpiler.cmss.create_random_circuit.view_qasm")
    def test_view_mode_no_rcg_instantiated(self, mock_view, MockRCG):
        """Test that view mode does not instantiate the circuit generator."""
        main(["-v", "circuit.qasm"])
        MockRCG.assert_not_called()


class TestViewQasm:
    """Tests for viewing QASM circuit summaries."""

    def _write_qasm(self, path, qasm_str):
        path.write_text(qasm_str, encoding="utf-8")

    def test_view_qasm_success(self, tmp_path, capsys):
        """Test viewing a valid QASM circuit."""
        qasm = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[2];\n"
            "creg c[2];\n"
            "h q[0];\n"
            "cx q[0],q[1];\n"
        )
        f = tmp_path / "simple.qasm"
        self._write_qasm(f, qasm)

        view_qasm(str(f))
        out = capsys.readouterr().out
        assert "filename: simple.qasm" in out
        assert "num_qubits: 2" in out
        assert "depth:" in out
        assert "num_gates:" in out

    def test_view_qasm_file_not_found(self):
        """Test that viewing a missing QASM file raises an exception."""
        with pytest.raises(FileNotFoundError):
            view_qasm("/nonexistent/path/circuit.qasm")

    def test_view_qasm_with_r_gate(self, tmp_path, capsys):
        """Test viewing a QASM circuit containing an R gate."""
        qasm = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[2];\n"
            "creg c[2];\n"
            "r(1.5,2.5) q[0];\n"
            "cx q[0],q[1];\n"
        )
        f = tmp_path / "r_gate.qasm"
        self._write_qasm(f, qasm)

        view_qasm(str(f))
        out = capsys.readouterr().out
        assert "filename: r_gate.qasm" in out
        assert "num_qubits: 2" in out

    def test_view_qasm_with_u_gate(self, tmp_path, capsys):
        """Test viewing a QASM circuit containing a U gate."""
        qasm = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[2];\n"
            "creg c[2];\n"
            "u(1.0,2.0,3.0) q[0];\n"
            "h q[1];\n"
        )
        f = tmp_path / "u_gate.qasm"
        self._write_qasm(f, qasm)

        view_qasm(str(f))
        out = capsys.readouterr().out
        assert "filename: u_gate.qasm" in out
        assert "num_qubits: 2" in out

    def test_view_qasm_with_u3_gate(self, tmp_path, capsys):
        """Test viewing a QASM circuit containing U3 and U2 gates."""
        qasm = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[3];\n"
            "creg c[3];\n"
            "u3(0.1,0.2,0.3) q[0];\n"
            "u2(0.4,0.5) q[1];\n"
            "cx q[0],q[2];\n"
        )
        f = tmp_path / "u3_gate.qasm"
        self._write_qasm(f, qasm)

        view_qasm(str(f))
        out = capsys.readouterr().out
        assert "filename: u3_gate.qasm" in out
        assert "num_qubits: 3" in out

    def test_view_qasm_output_format(self, tmp_path, capsys):
        """Test the QASM summary output format."""
        qasm = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[1];\n"
            "creg c[1];\n"
            "h q[0];\n"
        )
        f = tmp_path / "format_test.qasm"
        self._write_qasm(f, qasm)

        view_qasm(str(f))
        out = capsys.readouterr().out.strip()
        lines = out.split("\n")
        assert len(lines) == 4
        assert lines[0].startswith("filename:")
        assert lines[1].startswith("num_qubits:")
        assert lines[2].startswith("depth:")
        assert lines[3].startswith("num_gates:")

    def test_view_qasm_empty_circuit(self, tmp_path, capsys):
        """Test viewing an empty QASM circuit."""
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
        f = tmp_path / "empty.qasm"
        self._write_qasm(f, qasm)

        view_qasm(str(f))
        out = capsys.readouterr().out
        assert "num_qubits: 2" in out
        assert "num_gates: 0" in out

    def test_view_qasm_generated_by_rcg(self, tmp_path, capsys):
        """Test viewing a QASM file created by the circuit generator."""
        rcg = RandomCircuitGen()
        outfile = tmp_path / "generated.qasm"
        rcg.random_circuit_with_depth(
            num_qubits=5,
            depth=10,
            gate_type=2,
            seed=42,
            density=0.5,
            outfile=str(outfile),
        )

        view_qasm(str(outfile))
        out = capsys.readouterr().out
        assert "filename: generated.qasm" in out
        assert "num_qubits: 5" in out
        assert "depth:" in out
        assert "num_gates:" in out

    def test_view_qasm_via_main(self, tmp_path, capsys):
        """Test viewing a QASM circuit through the main entry point."""
        qasm = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[2];\n"
            "creg c[2];\n"
            "h q[0];\n"
            "cx q[0],q[1];\n"
            "h q[1];\n"
        )
        f = tmp_path / "via_main.qasm"
        self._write_qasm(f, qasm)

        main(["-v", str(f)])
        out = capsys.readouterr().out
        assert "filename: via_main.qasm" in out
        assert "num_qubits: 2" in out
        assert "depth: 3" in out
        assert "num_gates: 3" in out
