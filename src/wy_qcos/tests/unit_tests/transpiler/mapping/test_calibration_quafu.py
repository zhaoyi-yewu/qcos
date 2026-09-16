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
"""Unit tests for calibration_quafu module."""

from unittest.mock import MagicMock

import pytest

try:
    from wy_qcos.transpiler.cmss.mapping.utils.calibration_quafu import (
        QuafuFidelityCalibrator,
    )
except ModuleNotFoundError:
    pytest.skip("quark not installed", allow_module_level=True)

_CSV = (
    "Qubit,T1,T2,Freq,Fidelity,CZ\n"
    '0,100,100,5.0,0.99,"0_1:0.95\n2_3:0.90"\n'
    '1,100,100,5.0,0.98,"1_2:0.85"\n'
    '2,100,100,5.0,0.0,"2_3:0.0"\n'
    "3,100,100,5.0,0.97,\n"
)

_CSV_NO_EDGES = "Qubit,T1,T2,Freq,Fidelity,CZ\n0,100,100,5.0,0.99,\n"

_CSV_ZERO_FID = 'Qubit,T1,T2,Freq,Fidelity,CZ\n0,100,100,5.0,0.99,"0_1:0.0"\n'

_CSV_SHORT = (
    "Qubit,T1,T2,Freq,Fidelity,CZ\n0,100\n"
    '1,100,100,5.0,0.98,"1_2:0.85"\n'
    '2,100,100,5.0,0.97,"1_2:0.85"\n'
)


def _csv(tmp_path, data):
    """Write CSV data to temp file, return path."""
    p = tmp_path / "t.csv"
    p.write_text(data)
    return str(p)


class _Calibrator(QuafuFidelityCalibrator):
    """QuafuFidelityCalibrator with mocked Task, no token needed."""

    def __init__(
        self,
        csv_path="d.csv",
        chip="TestChip",
        shots=1024,
        timeout=300,
        submit_interval=0.25,
        output_dir=".",
    ):
        self.csv_path = csv_path
        self.chip = chip
        self.shots = shots
        self.timeout = timeout
        self.submit_interval = submit_interval
        self.output_dir = output_dir
        self._calibration_cache = None
        self._task_manager = MagicMock()


class TestLoadCalibration:
    def test_parse(self, tmp_path):
        calibrator = _Calibrator(csv_path=_csv(tmp_path, _CSV))
        edges, qubits, qreg = calibrator.load_calibration()
        assert len(edges) == 3
        assert {(0, 1), (1, 2), (2, 3)} == set(edges)
        assert (0, 0.99) in qubits
        assert (2, 0.0) in qubits
        assert qreg == 4

    def test_no_edges_raises(self, tmp_path):
        calibrator = _Calibrator(csv_path=_csv(tmp_path, _CSV_NO_EDGES))
        with pytest.raises(ValueError, match="No edges"):
            calibrator.load_calibration()

    def test_zero_fid_filtered(self, tmp_path):
        calibrator = _Calibrator(csv_path=_csv(tmp_path, _CSV_ZERO_FID))
        edges, qubits, qreg = calibrator.load_calibration()
        assert not edges
        assert len(qubits) == 1
        assert qreg == 2

    def test_short_row_skipped(self, tmp_path):
        calibrator = _Calibrator(csv_path=_csv(tmp_path, _CSV_SHORT))
        edges, qubits, _ = calibrator.load_calibration()
        assert (1, 2) in edges
        assert len(qubits) == 2
