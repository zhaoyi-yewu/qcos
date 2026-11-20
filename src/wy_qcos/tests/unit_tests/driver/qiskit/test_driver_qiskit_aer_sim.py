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
# ---------------------------------------------------------------------
# pylint: disable=bad-continuation

"""Tests for the Qiskit Aer driver and ideal simulation."""

# ruff: noqa: E402
# load driver venv
import json
import sys

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

org_path = Library.set_driver_venv_path(
    "DriverQiskitAerSim", Config.DEFAULT.VENV_DIR
)

import pytest
from unittest.mock import Mock, patch


from wy_qcos.driver.qiskit.driver_qiskit_aer_sim import (
    DriverQiskitAerSim,
    _run_ideal_simulation_cli,
)
from wy_qcos.engine import ideal_simulator

driver_aer_sim = DriverQiskitAerSim()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {"index": 0, "source_code": None, "transpile_results": []}
data_type = DriverQiskitAerSim.DATA_TYPE_GATE_SEQUENCE


@pytest.mark.driver
class TestDriverQiskitAerSim:
    """Test the Qiskit Aer simulator driver."""

    @classmethod
    def teardown_class(cls):
        """Restore the original module search path."""
        sys.path = org_path

    def test_init_driver(self):
        """Test Aer simulator driver initialization."""
        assert driver_aer_sim.init_driver() is None

    def test_validate_driver_configs(self):
        """Test Aer simulator configuration validation."""
        configs = {}
        success, err_msg = driver_aer_sim.validate_driver_configs(configs)
        assert success is True

    def test_close_driver(self):
        """Test closing the Aer simulator driver."""
        assert driver_aer_sim.close_driver() is None

    @pytest.mark.smoke
    @patch("wy_qcos.driver.qiskit.driver_qiskit_aer_sim.AerSimulator")
    def test_run(self, mock_aer_sim):
        """Test running a circuit and retrieving counts."""
        mock_counts = {"00": 45, "11": 55}
        mock_result_obj = Mock()
        mock_result_obj.get_counts.return_value = mock_counts
        mock_job_obj = Mock()
        mock_job_obj.result.return_value = mock_result_obj
        mock_simulator = Mock()
        mock_simulator.run.return_value = mock_job_obj
        mock_aer_sim.return_value = mock_simulator

        assert driver_aer_sim.run(job_id, num_qubits, data, data_type) is None

        results = driver_aer_sim.get_results(job_id, data["index"])
        assert results == mock_counts

    def test_cancel(self):
        """Test cancelling an Aer simulator job."""
        assert driver_aer_sim.cancel(job_id) is None

    def test_ideal_simulation_cli_reads_qasm_file(
        self, tmp_path, capsys, monkeypatch
    ):
        """Test reading QASM and printing simulation probabilities."""
        source_code = 'OPENQASM 2.0; include "qelib1.inc";'
        source_path = tmp_path / "source.qasm"
        source_path.write_text(source_code, encoding="utf-8")
        simulate = Mock(return_value={"0": 1.0})
        monkeypatch.setattr(
            "wy_qcos.driver.qiskit.driver_qiskit_aer_sim."
            "simulate_qasm_probabilities",
            simulate,
        )

        assert _run_ideal_simulation_cli(source_path) == 0

        simulate.assert_called_once_with(source_code)
        assert json.loads(capsys.readouterr().out) == {"0": 1.0}

    @patch("wy_qcos.engine.ideal_simulator._run_command")
    @patch("wy_qcos.engine.ideal_simulator.Library.get_driver_venv")
    def test_ideal_simulator_uses_absolute_interpreter(
        self, mock_get_venv, mock_run
    ):
        """Test use of an absolute Python interpreter path."""
        mock_get_venv.return_value = (sys.executable, {})
        mock_run.return_value = Mock(
            returncode=0, stdout='{"0": 1.0}', stderr=""
        )

        result = ideal_simulator.simulate_qasm_probabilities("OPENQASM 2.0;")

        assert result == {"0": 1.0}
        command = mock_run.call_args.args[0]
        assert command[0] == sys.executable

    @patch("wy_qcos.engine.ideal_simulator._run_command")
    @patch("wy_qcos.engine.ideal_simulator.Library.get_driver_venv")
    def test_ideal_simulator_rejects_path_interpreter(
        self, mock_get_venv, mock_run
    ):
        """Test rejection of a non-absolute interpreter path."""
        mock_get_venv.return_value = ("python3", {})

        with pytest.raises(ValueError, match="absolute path"):
            ideal_simulator.simulate_qasm_probabilities("OPENQASM 2.0;")

        mock_run.assert_not_called()
