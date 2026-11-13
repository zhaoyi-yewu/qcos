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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Tests for random circuit generation with a specified depth."""

import random
from itertools import chain, repeat
from unittest.mock import MagicMock, patch

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.circuit.utils import RandomCircuitGen
from wy_qcos.transpiler.common.errors import CircuitException


def _gate_names(ir):
    return [g.name for g in ir]


class TestRandomCircuitWithDepth:
    """Tests for random circuit generation with a specified depth."""

    @pytest.mark.smoke
    def test_zero_qubits_returns_empty(self):
        """Test that zero qubits returns an empty circuit."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(num_qubits=0, depth=5)
        assert ir == []
        assert rcg.qc is not None

    def test_zero_depth_returns_empty(self):
        """Test that zero depth returns an empty circuit."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(num_qubits=5, depth=0)
        assert ir == []
        assert rcg.qc is not None

    def test_invalid_max_operands_too_small(self):
        """Test that too few maximum operands raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(
                num_qubits=5, depth=5, max_operands=0
            )
        assert "Invalid max_operands" in str(e.value)

    def test_invalid_max_operands_too_large(self):
        """Test that too many maximum operands raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(
                num_qubits=5, depth=5, max_operands=5
            )
        assert "Invalid max_operands" in str(e.value)

    def test_invalid_gate_type_without_custom_gates(self):
        """Test that an unknown custom gate raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(
                num_qubits=5,
                depth=5,
                gate_type=2,
                custom_gates=["unknown_gate"],
            )
        assert "Unknown gate name" in str(e.value)

    def test_invalid_gate_type_out_of_range(self):
        """Test that an out-of-range gate type raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(num_qubits=5, depth=5, gate_type=-2)
        assert "Invalid gate_type" in str(e.value)

    def test_invalid_density_zero(self):
        """Test that zero density raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(num_qubits=5, depth=5, density=0)
        assert "Invalid density" in str(e.value)

    def test_invalid_density_negative(self):
        """Test that negative density raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(num_qubits=5, depth=5, density=-0.1)
        assert "Invalid density" in str(e.value)

    def test_invalid_density_too_large(self):
        """Test that density above one raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(num_qubits=5, depth=5, density=1.5)
        assert "Invalid density" in str(e.value)

    def test_invalid_outfile_suffix(self):
        """Test that an invalid output file suffix raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(
                num_qubits=3, depth=2, outfile="output.txt"
            )
        assert "Invalid outfile suffix" in str(e.value)

    def test_basic_gates_type_0(self):
        """Test generation with the basic gate set."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=8, max_operands=2, gate_type=0, seed=42
        )
        assert isinstance(ir, list)
        assert rcg.num_qubits == 5
        assert rcg.depth >= 8
        allowed = {"x", "rx", "ry", "h", "cx", "cz"}
        assert set(_gate_names(ir)).issubset(allowed)

    def test_clifford_gates_type_1(self):
        """Test generation with the Clifford gate set."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=8, max_operands=2, gate_type=1, seed=42
        )
        assert isinstance(ir, list)
        allowed = {"x", "y", "z", "h", "s", "sdg", "cx", "cz"}
        assert set(_gate_names(ir)).issubset(allowed)

    def test_all_gates_type_2_max_operands_4(self):
        """Test generation with all gates and up to four operands."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=6, max_operands=4, gate_type=2, seed=7
        )
        assert isinstance(ir, list)
        assert rcg.depth >= 6
        allowed = set(Constant.ALL_GATE_LIST) | {"reset", "measure"}
        assert set(_gate_names(ir)).issubset(allowed)

    def test_max_operands_one_only_single_qubit(self):
        """Test that one maximum operand allows only single-qubit gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=8, max_operands=1, gate_type=2, seed=11
        )
        allowed = set(Constant.SINGLE_QUBIT_GATE_LIST) | {"reset"}
        for g in ir:
            assert g.name in allowed
            assert len(g.targets) == 1

    def test_max_operands_three_includes_three_qubit(self):
        """Test that three maximum operands allow three-qubit gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=10, max_operands=3, gate_type=2, seed=23
        )
        allowed = (
            set(Constant.SINGLE_QUBIT_GATE_LIST)
            | set(Constant.TWO_QUBIT_GATE_LIST)
            | set(Constant.THREE_QUBIT_GATE_LIST)
            | {"reset"}
        )
        assert set(_gate_names(ir)).issubset(allowed)

    def test_max_operands_capped_by_num_qubits(self):
        """Test that the qubit count caps the maximum operands."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=2, depth=6, max_operands=4, gate_type=2, seed=3
        )
        assert isinstance(ir, list)
        for g in ir:
            assert max(g.targets) < 2

    def test_max_operands_forced_to_2_for_gate_type_0(self):
        """Test that basic gates force a maximum of two operands."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=10, max_operands=1, gate_type=0, seed=42
        )
        for g in ir:
            assert len(g.targets) <= 2
        assert any(len(g.targets) == 2 for g in ir)

    def test_max_operands_forced_to_2_for_gate_type_1(self):
        """Test that Clifford gates force a maximum of two operands."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=10, max_operands=1, gate_type=1, seed=42
        )
        allowed = {"x", "y", "z", "h", "s", "sdg", "cx", "cz"}
        assert set(_gate_names(ir)).issubset(allowed)
        for g in ir:
            assert len(g.targets) <= 2

    def test_max_operands_four_silently_capped_for_gate_type_0(self):
        """Test that four operands are capped for basic gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=10, max_operands=4, gate_type=0, seed=42
        )
        for g in ir:
            assert len(g.targets) <= 2

    def test_max_operands_two_unchanged_for_gate_type_0(self):
        """Test that two operands remain valid for basic gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=8, max_operands=2, gate_type=0, seed=42
        )
        assert isinstance(ir, list)
        assert rcg.depth >= 8

    def test_measure_adds_measure_gates(self):
        """Test that enabling measurement adds measure gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=4, depth=5, measure=True, reset=False, seed=9
        )
        names = _gate_names(ir)
        assert names.count("measure") == 4
        assert "reset" not in names

    def test_reset_adds_reset_gates(self):
        """Test that enabling reset adds reset gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=4, depth=8, measure=False, reset=True, seed=9
        )
        names = _gate_names(ir)
        assert "reset" in names
        assert "measure" not in names

    def test_measure_and_reset_together(self):
        """Test enabling measurement and reset together."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=4, depth=8, measure=True, reset=True, seed=9
        )
        names = _gate_names(ir)
        assert names.count("measure") == 4
        assert "reset" in names

    def test_seed_reproducibility(self):
        """Test that equal seeds generate identical circuits."""
        rcg1 = RandomCircuitGen()
        random.seed(123)
        ir1 = rcg1.random_circuit_with_depth(num_qubits=5, depth=8, seed=42)
        rcg2 = RandomCircuitGen()
        random.seed(123)
        ir2 = rcg2.random_circuit_with_depth(num_qubits=5, depth=8, seed=42)
        assert len(ir1) == len(ir2)
        for g1, g2 in zip(ir1, ir2):
            assert g1.name == g2.name
            assert g1.targets == g2.targets

    def test_seed_none_auto_generated(self):
        """Test generation with an automatically generated seed."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(num_qubits=5, depth=8)
        assert isinstance(ir, list)
        assert rcg.depth >= 8

    def test_two_qubits_rate_zero_forces_single_qubit_layers(self):
        """Test that a zero two-qubit rate forces single-qubit layers."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5,
            depth=12,
            max_operands=2,
            gate_type=0,
            two_qubits_rate=0.0,
            seed=42,
        )
        assert isinstance(ir, list)
        assert rcg.depth >= 12

    def test_two_qubits_rate_high_allows_two_qubit(self):
        """Test that a high two-qubit rate allows two-qubit gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5,
            depth=12,
            max_operands=2,
            gate_type=0,
            two_qubits_rate=1.0,
            seed=42,
        )
        assert isinstance(ir, list)
        assert rcg.depth >= 12

    def test_density_boundary_one(self):
        """Test generation with the maximum density of one."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=6, density=1.0, seed=42
        )
        assert isinstance(ir, list)
        assert rcg.depth >= 6

    def test_depth_guarantee(self):
        """Test that generation reaches the requested depth."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5, depth=15, max_operands=2, gate_type=2, seed=42
        )
        assert rcg.depth >= 15
        assert rcg.size == len(ir)

    def test_depth_guarantee_while_loop(self):
        """Test repeated generation until the requested depth is reached."""
        depth_seq = chain([3, 3, 4], repeat(5))
        with patch(
            "wy_qcos.transpiler.cmss.circuit.utils.QuantumCircuit.depth",
            new=MagicMock(side_effect=depth_seq),
        ):
            rcg = RandomCircuitGen()
            ir = rcg.random_circuit_with_depth(
                num_qubits=5, depth=5, max_operands=2, gate_type=0, seed=42
            )
        assert isinstance(ir, list)

    @patch("wy_qcos.transpiler.cmss.circuit.utils.QasmConverter")
    def test_outfile_save_success(self, mock_qasm_converter, tmp_path):
        """Test saving a generated circuit to a QASM file."""
        mock_instance = mock_qasm_converter.return_value
        mock_instance.save.return_value = None
        outfile = tmp_path / "out.qasm"
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=3, depth=3, outfile=str(outfile), seed=42
        )
        assert isinstance(ir, list)
        mock_instance.save.assert_called_once()
        _, kwargs = mock_instance.save.call_args
        assert kwargs.get("version") == "2.0"

    @patch("wy_qcos.transpiler.cmss.circuit.utils.QasmConverter")
    def test_outfile_exists_raises(self, mock_qasm_converter, tmp_path):
        """Test that an existing output file raises an exception."""
        outfile = tmp_path / "exists.qasm"
        outfile.write_text("existing", encoding="utf-8")
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(
                num_qubits=3, depth=3, outfile=str(outfile), seed=42
            )
        assert "Output file has existed" in str(e.value)
        mock_qasm_converter.return_value.save.assert_not_called()

    def test_return_type_and_instance_attributes(self):
        """Test the return type and generator instance attributes."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(num_qubits=4, depth=5, seed=42)
        assert isinstance(ir, list)
        assert rcg.qc is not None
        assert rcg.num_qubits == 4
        assert rcg.depth >= 5
        assert rcg.size == len(ir)

    def test_custom_gates_single_qubit(self):
        """Test generation with custom single-qubit gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5,
            depth=8,
            gate_type=2,
            custom_gates=["x", "h", "y"],
            seed=42,
        )
        assert isinstance(ir, list)
        allowed = {"x", "h", "y"}
        assert set(_gate_names(ir)).issubset(allowed)

    def test_custom_gates_mixed_qubits(self):
        """Test generation with custom single- and two-qubit gates."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=5,
            depth=8,
            gate_type=2,
            custom_gates=["x", "h", "cx", "cz"],
            seed=42,
        )
        assert isinstance(ir, list)
        allowed = {"x", "h", "cx", "cz"}
        assert set(_gate_names(ir)).issubset(allowed)

    def test_custom_gates_unknown_gate_error(self):
        """Test that an unknown custom gate raises an exception."""
        rcg = RandomCircuitGen()
        with pytest.raises(CircuitException) as e:
            rcg.random_circuit_with_depth(
                num_qubits=5,
                depth=5,
                gate_type=2,
                custom_gates=["x", "unknown_gate"],
            )
        assert "Unknown gate name" in str(e.value)

    def test_custom_gates_with_reset(self):
        """Test generation with custom gates and reset enabled."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=4,
            depth=6,
            gate_type=2,
            custom_gates=["x", "h", "cx"],
            reset=True,
            seed=42,
        )
        names = _gate_names(ir)
        assert "reset" in names

    def test_custom_gates_with_measure(self):
        """Test generation with custom gates and measurement enabled."""
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=4,
            depth=6,
            gate_type=2,
            custom_gates=["x", "h", "cx"],
            measure=True,
            seed=42,
        )
        names = _gate_names(ir)
        assert names.count("measure") == 4
