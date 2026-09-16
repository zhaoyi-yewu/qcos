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
"""Unit tests for calibration_base module."""

import tempfile
from pathlib import Path

import pytest

from wy_qcos.transpiler.cmss.mapping.utils.calibration_base import (
    EdgeResult,
    FidelityCalibrator,
    QubitResult,
    _edge_qubits,
    _fmt_err,
    extract_prob,
    write_fidelity_toml,
)


class _Calibrator(FidelityCalibrator):
    """Minimal concrete subclass for testing base class methods."""

    driver = "DriverDummy"

    def load_calibration(self):
        return (
            [(0, 1), (1, 2), (2, 3)],
            [(0, 0.99), (1, 0.98), (2, 0.97), (3, 0.0)],
            4,
        )

    def submit(self, name, qasm):
        return 0

    def wait_result(self, task_id):
        return {}

    def __init__(self, output_dir="."):
        self.chip = "TestChip"
        self.submit_interval = 0
        self.output_dir = output_dir
        self._calibration_cache = None


class TestExtractProb:
    def test_two_bits_match(self):
        counts = {"0011": 60, "0000": 40}
        assert extract_prob(counts, [0, 1], "11", 4) == pytest.approx(0.6)

    def test_single_bit_zero(self):
        counts = {"00": 70, "01": 30}
        assert extract_prob(counts, [0], "0", 2) == pytest.approx(0.7)

    def test_single_bit_one(self):
        counts = {"00": 30, "01": 70}
        assert extract_prob(counts, [0], "1", 2) == pytest.approx(0.7)

    def test_zero_padding(self):
        counts = {"1": 50, "0": 50}
        assert extract_prob(counts, [0], "1", 4) == pytest.approx(0.5)

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            extract_prob({"11": 1}, [0, 1], "1", 2)

    def test_empty_counts(self):
        assert extract_prob({}, [0], "0", 2) == 0.0


class TestEdgeQubits:
    def test_basic(self):
        assert _edge_qubits([(0, 1), (2, 3)]) == {0, 1, 2, 3}

    def test_overlapping(self):
        assert _edge_qubits([(0, 1), (1, 2)]) == {0, 1, 2}

    def test_empty(self):
        assert _edge_qubits([]) == set()


class TestFmtErr:
    def test_normal(self):
        assert _fmt_err(0.95) == 0.05

    def test_none(self):
        assert _fmt_err(None) == 1.0

    def test_zero(self):
        assert _fmt_err(0.0) == 1.0

    def test_rounding(self):
        assert _fmt_err(0.87656) == 0.1234


class TestWriteFidelityToml:
    def test_basic_output(self):
        edges = [EdgeResult(0, 1, 0.95), EdgeResult(1, 2, 0.90)]
        qubits = [QubitResult(0, 0.99), QubitResult(1, 0.0)]
        with tempfile.TemporaryDirectory() as d:
            path = write_fidelity_toml(
                edge_results=edges,
                qubit_results=qubits,
                chip="TestChip",
                qreg_size=3,
                driver="DriverQuafu",
                output_dir=d,
            )
            c = Path(path).read_text()
            assert "[testchip]" in c
            assert "qubits = 3" in c
            assert "coupler_map.CZ0_1 = ['Q0', 'Q1']" in c
            assert "readout_error.Q0 = 0.01" in c
            assert "readout_error.Q1 = 1.0" in c
            assert "coupler_error.CZ0_1 = 0.05" in c

    def test_undirected_merge(self):
        edges = [EdgeResult(0, 1, 0.90), EdgeResult(1, 0, 0.80)]
        with tempfile.TemporaryDirectory() as d:
            path = write_fidelity_toml(
                edge_results=edges,
                qubit_results=[],
                chip="Merge",
                qreg_size=2,
                driver="DriverQuafu",
                output_dir=d,
            )
            c = Path(path).read_text()
            assert c.count("coupler_map.CZ0_1") == 1
            assert "coupler_error.CZ0_1 = 0.15" in c

    def test_none_fid(self):
        edges = [EdgeResult(0, 1, None)]
        qubits = [QubitResult(0, None)]
        with tempfile.TemporaryDirectory() as d:
            path = write_fidelity_toml(
                edge_results=edges,
                qubit_results=qubits,
                chip="NoneChip",
                qreg_size=2,
                driver="DriverQuafu",
                output_dir=d,
            )
            c = Path(path).read_text()
            assert "readout_error.Q0 = 1.0" in c
            assert "coupler_error.CZ0_1 = 1.0" in c


class TestPlanEdgeGroups:
    def test_disjoint(self):
        calibrator = _Calibrator()
        groups = calibrator.plan_edge_groups([(0, 1), (2, 3)])
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_overlapping(self):
        calibrator = _Calibrator()
        assert len(calibrator.plan_edge_groups([(0, 1), (1, 2)])) == 2

    def test_chain(self):
        calibrator = _Calibrator()
        groups = calibrator.plan_edge_groups([(0, 1), (1, 2), (2, 3), (3, 4)])
        assert len(groups) == 2
        assert len(groups[0]) == 2
        assert len(groups[1]) == 2

    def test_empty(self):
        assert _Calibrator().plan_edge_groups([]) == []


class TestPlanQubitGroups:
    def test_with_dead(self):
        calibrator = _Calibrator()
        groups = calibrator.plan_qubit_groups([(0, 0.99), (1, 0.0), (2, 0.95)])
        assert len(groups) == 2
        qubits, apply_x = groups[0]
        assert qubits == [0, 2]
        assert apply_x is False

    def test_all_dead(self):
        assert _Calibrator().plan_qubit_groups([(0, 0.0)]) == []

    def test_all_alive(self):
        calibrator = _Calibrator()
        assert len(calibrator.plan_qubit_groups([(0, 0.9), (1, 0.8)])) == 2


class TestBuildEdgeCircuit:
    def test_qasm_content(self):
        calibrator = _Calibrator()
        task = calibrator.build_edge_circuit([(0, 1), (2, 3)], 4)
        assert "OPENQASM 2.0;" in task.qasm
        assert "cx q[0],q[1];" in task.qasm
        assert "cx q[2],q[3];" in task.qasm

    def test_bit_map(self):
        calibrator = _Calibrator()
        task = calibrator.build_edge_circuit([(0, 1), (2, 3)], 4)
        assert task.bit_map == {0: 0, 1: 1, 2: 2, 3: 3}

    def test_non_contiguous(self):
        calibrator = _Calibrator()
        task = calibrator.build_edge_circuit([(0, 2)], 4)
        assert task.bit_map == {0: 0, 2: 1}


class TestBuildQubitCircuit:
    def test_measure_only(self):
        calibrator = _Calibrator()
        task = calibrator.build_qubit_circuit(
            [0, 2], apply_x=False, qreg_size=4
        )
        assert "x q[" not in task.qasm
        assert "measure q[0] -> c[0];" in task.qasm

    def test_with_x(self):
        calibrator = _Calibrator()
        task = calibrator.build_qubit_circuit(
            [0, 2], apply_x=True, qreg_size=4
        )
        assert "x q[0];" in task.qasm


class TestExtractEdgeFids:
    def test_extraction(self):
        calibrator = _Calibrator()
        task = calibrator.build_edge_circuit([(0, 1), (2, 3)], 4)
        counts = {"1111": 90, "0000": 10}
        fids = calibrator.extract_edge_fids([(0, 1), (2, 3)], task, counts)
        assert fids[(0, 1)] == pytest.approx(0.9)
        assert fids[(2, 3)] == pytest.approx(0.9)


class TestExtractQubitProbs:
    def test_no_x(self):
        calibrator = _Calibrator()
        task = calibrator.build_qubit_circuit(
            [0, 1], apply_x=False, qreg_size=4
        )
        probs = calibrator.extract_qubit_probs(
            [0, 1], False, task, {"00": 60, "01": 40}
        )
        assert probs[0] == pytest.approx(0.6)
        assert probs[1] == pytest.approx(1.0)

    def test_with_x(self):
        calibrator = _Calibrator()
        task = calibrator.build_qubit_circuit(
            [0, 1], apply_x=True, qreg_size=4
        )
        probs = calibrator.extract_qubit_probs(
            [0, 1], True, task, {"11": 80, "00": 20}
        )
        assert probs[0] == pytest.approx(0.8)


class TestComputeQubitFids:
    def test_alive(self):
        calibrator = _Calibrator()
        results = calibrator._compute_qubit_fids(
            [(0, 0.99), (1, 0.0)], {0: 0.9}, {0: 0.8}
        )
        assert results[0].measured_fid == pytest.approx(0.85)
        assert results[1].measured_fid == 0.0

    def test_dead(self):
        calibrator = _Calibrator()
        results = calibrator._compute_qubit_fids([(0, 0.0)], {}, {})
        assert results[0].measured_fid == 0.0


class TestSubmitAll:
    def test_structure(self):
        calibrator = _Calibrator()
        calibrator.submit = lambda name, qasm: 1
        edge_groups = [[(0, 1), (2, 3)], [(1, 2)]]
        qubit_groups = [([0, 1, 2], False), ([0, 1, 2], True)]
        pending = calibrator._submit_all(edge_groups, qubit_groups, 4)
        assert len(pending) == 4
        assert pending[0][0] == "edge"
        assert pending[2][0] == "qubit"
        assert pending[2][1][1] is False
        assert pending[3][1][1] is True


class TestCollectAll:
    def test_edge_and_qubit(self):
        calibrator = _Calibrator()
        task_e = calibrator.build_edge_circuit([(0, 1), (2, 3)], 4)
        task_q0 = calibrator.build_qubit_circuit([0, 1, 2], False, 4)
        task_q1 = calibrator.build_qubit_circuit([0, 1, 2], True, 4)
        results = {
            1: {"count": {"1111": 90, "0000": 10}},
            2: {"count": {"000": 95, "111": 5}},
            3: {"count": {"111": 90, "000": 10}},
        }
        calibrator.wait_result = lambda tid: results.get(tid, {})
        pending = [
            ("edge", [(0, 1), (2, 3)], task_e, 1),
            ("qubit", ([0, 1, 2], False), task_q0, 2),
            ("qubit", ([0, 1, 2], True), task_q1, 3),
        ]
        edge_res, m_probs, x_probs = calibrator._collect_all(pending)
        assert len(edge_res) == 2
        assert edge_res[0].measured_fid == pytest.approx(0.9)
        assert m_probs[0] == pytest.approx(0.95)
        assert x_probs[0] == pytest.approx(0.9)
