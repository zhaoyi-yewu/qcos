#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from unittest.mock import Mock, patch

from qiskit_aer.backends.aerbackend import AerBackend

from qcos.drivers.qiskit.driver_qiskit_aer_sim import DriverQiskitAerSim

driver_aer_sim = DriverQiskitAerSim()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {"index": 0, "source_code": None, "transpile_results": []}
data_type = DriverQiskitAerSim.DATA_TYPE_GATE_SEQUENCE


class TestDriverQiskitAerSim:
    def test_init_driver(self):
        assert driver_aer_sim.init_driver() is None

    def test_validate_driver_configs(self):
        configs = {}
        success, err_msg = driver_aer_sim.validate_driver_configs(configs)
        assert success is True

    def test_close_driver(self):
        assert driver_aer_sim.close_driver() is None

    @patch.object(AerBackend, "run")
    def test_run(self, mock_run):
        mock_result_value = "模拟结果"
        mock_result_obj = Mock()
        mock_result_obj.mock_run.return_value = mock_result_value
        assert driver_aer_sim.run(job_id, num_qubits, data, data_type) is None
