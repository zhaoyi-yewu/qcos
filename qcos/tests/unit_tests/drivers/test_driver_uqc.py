#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from unittest.mock import patch, Mock

from uqc_client import UQC

from qcos.common.config import Config
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase
from qcos.drivers.uqc.driver_uqc import DriverUQCMatrix2

driver_uqc = DriverUQCMatrix2()


job_id = "00000000-0000-4000-8000-000000000001"
task_id = "123456"
num_qubits = 5
data = {"index": 0, "source_code": "code", "transpile_results": []}
data_type = DriverBase.DATA_TYPE_QASM3
shots = 1000
expect_task_status = "SUCCESS"
result = [
    [0.0, 445.4878490937944],
    [1.0, -4.955214948811051],
    [2.0, -6.847017287746492],
    [3.0, 0.07585668572173017],
    [4.0, -2.5351432750618055],
    [5.0, 0.029883709166450386],
    [6.0, -0.020592262083073097],
    [7.0, 0.0001740650579037159],
    [8.0, -6.396516297156177],
    [9.0, 0.009918688028538944],
    [10.0, 0.10303513818907799],
    [11.0, -0.00027354353342492685],
    [12.0, 0.010182466378285385],
    [13.0, 0.0006158458602779742],
    [14.0, 0.001151228390312002],
    [15.0, -2.2396678846350193e-5],
    [16.0, 555.0203605428987],
    [17.0, -1.2230414628635984],
    [18.0, 2.526727936733362],
    [19.0, -0.09235750190591845],
    [20.0, -1.2908471733718734],
    [21.0, -0.04458642243262779],
    [22.0, 1.0833418176157679],
    [23.0, -0.010628645040499313],
    [24.0, 19.096144719307357],
    [25.0, 0.8871730189846192],
    [26.0, -0.5080170301199354],
    [27.0, -0.010024576917872636],
    [28.0, -0.36955729966912587],
    [29.0, -0.009749086093121279],
    [30.0, -0.019221976218295026],
    [31.0, 0.00039622957709540456],
]


class TestDriverUqc:
    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs(self, mock_validate_schema):
        mock_validate_schema.return_value = True, None
        success, _ = driver_uqc.validate_driver_configs(Config)
        assert success is True

    def test_init_driver(self):
        assert driver_uqc.init_driver() is None

    @patch("qcos.drivers.uqc.driver_uqc.uqc_client.UQC")
    def test_fetch_configs(self, mock_uqc):
        mock_uqc.return_value = Mock()
        assert driver_uqc.fetch_configs() is None

    def test_cancel(self):
        assert driver_uqc.cancel("1") is None

    @patch.object(DriverUQCMatrix2, "normalize_task_results")
    @patch.object(DriverUQCMatrix2, "get_task_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(UQC, "submit_task")
    def test_run(
        self,
        mock_submit_task,
        mock_loop_with_timeout,
        mock_get_task_results,
        mock_normalize_task_results,
    ):
        mock_submit_task.return_value = task_id
        mock_loop_with_timeout.return_value = True, None, None
        mock_get_task_results.return_value = (
            True,
            [{"datasets": {"computational_basis_histogram": []}}],
        )
        mock_normalize_task_results.return_value = None
        driver_uqc._uqc = Mock()
        assert (
            driver_uqc.run(job_id, num_qubits, data, data_type, shots) is None
        )

    @patch.object(DriverUQCMatrix2, "get_task_status")
    def test_check_task_status(self, mock_get_task_status):
        mock_get_task_status.return_value = True, expect_task_status
        success = driver_uqc.check_task_status(task_id, expect_task_status)
        assert success is True

    @patch.object(UQC, "get_task_status")
    def test_get_task_status(self, mock_get_task_status):
        mock_get_task_status.return_value = expect_task_status
        driver_uqc._uqc = Mock()
        success, _ = driver_uqc.get_task_status(task_id)
        assert success is True

    def test_is_valid_shots(self):
        assert driver_uqc.is_valid_shots(shots) is None

    def test_normalize_task_results(self):
        results = driver_uqc.normalize_task_results(result, num_qubits, shots)
        assert len(results) == 32
