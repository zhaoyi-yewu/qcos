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

# ruff: noqa: E402
# load driver venv
import sys

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

org_path = Library.set_driver_venv_path("DriverQiskitAerSim", Config.VENV_DIR)

import pytest
from unittest.mock import Mock, patch

from qiskit_aer.backends.aerbackend import AerBackend

from wy_qcos.drivers.qiskit.driver_qiskit_aer_sim import DriverQiskitAerSim

driver_aer_sim = DriverQiskitAerSim()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {"index": 0, "source_code": None, "transpile_results": []}
data_type = DriverQiskitAerSim.DATA_TYPE_GATE_SEQUENCE


class TestDriverQiskitAerSim:
    @classmethod
    def teardown_class(cls):
        sys.path = org_path

    def test_init_driver(self):
        assert driver_aer_sim.init_driver() is None

    def test_validate_driver_configs(self):
        configs = {}
        success, err_msg = driver_aer_sim.validate_driver_configs(configs)
        assert success is True

    def test_close_driver(self):
        assert driver_aer_sim.close_driver() is None

    @pytest.mark.smoke
    @patch.object(AerBackend, "run")
    def test_run(self, mock_run):
        mock_result_value = {"00": 45, "11": 55}
        mock_result_obj = Mock()
        mock_result_obj.mock_run.return_value = mock_result_value
        assert driver_aer_sim.run(job_id, num_qubits, data, data_type) is None

    def test_cancel(self):
        assert driver_aer_sim.cancel(job_id) is None
