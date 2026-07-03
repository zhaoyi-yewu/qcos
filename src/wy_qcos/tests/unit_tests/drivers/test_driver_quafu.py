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

# ruff: noqa: E402
# load driver venv

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device

org_path = Library.set_driver_venv_path("DriverQuafu", Config.DEFAULT.VENV_DIR)

import pytest
from unittest.mock import patch, Mock

from wy_qcos.drivers.driver_base import DriverBase
from wy_qcos.drivers.quafu.driver_quafu import DriverQuafu

driver_quafu = DriverQuafu()
job_id = "00000000-0000-4000-8000-000000000001"
task_id = "123456"
num_qubits = 5
data = {"index": 0, "source_code": "code", "transpile_results": []}
data_type = DriverBase.DATA_TYPE_QASM2
shots = 1024
result = {
    "count": {"11": 382, "10": 636, "00": 2, "01": 4},
    "status": "Finished",
}
source_code = """
OPENQASM 2.0;
include "qelib1.inc";  
qreg q[2];
creg meas[2];
h q[1];
cx q[1],q[2];
measure q -> meas;
"""


@pytest.mark.driver
class TestDriverQuafu:
    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs(self, mock_validate_schema):
        mock_validate_schema.return_value = True, None
        configs = {}
        success, _ = driver_quafu.validate_driver_configs(configs)
        assert success is True

    def test_init_driver(self):
        assert driver_quafu.init_driver() is None

    @patch("wy_qcos.drivers.quafu.driver_quafu.Task")
    def test_fetch_configs(self, mock_task):
        mock_task.return_value = Mock()
        assert driver_quafu.fetch_configs() is None

    def test_cancel(self):
        assert driver_quafu.cancel("1") is None

    def test_get_task_results(self):
        driver_quafu.tmgr = Mock()
        driver_quafu.tmgr.result.return_value = {
            "11": 382,
            "10": 636,
            "00": 2,
            "01": 4,
        }
        success, results = driver_quafu.get_task_results("1")
        assert success is True
        assert results is not None

    def test_fetch_running_info(self):
        info = driver_quafu.fetch_running_info()
        assert info == {"status": Device.DEVICE_STATUS_ONLINE}

    def test_submit_task(self):
        driver_quafu.tmgr = Mock()
        driver_quafu.tmgr.run.return_value = "123456"
        tid = driver_quafu.submit_task("1")
        assert tid == "123456"

    @patch.object(DriverQuafu, "get_task_results")
    def test_check_task_status(self, mock_get_task_results):
        mock_get_task_results.return_value = True, result
        success, err_msg, status = driver_quafu.check_task_status(
            "123456", driver_quafu.task_status_success
        )
        assert success is True
        assert err_msg is None
        assert status == "Finished"

    @pytest.mark.smoke
    @patch.object(DriverQuafu, "get_task_results")
    @patch.object(DriverQuafu, "check_task_status")
    @patch.object(DriverQuafu, "submit_task")
    def test_run(
        self,
        mock_submit_task,
        mock_check_task_status,
        mock_get_task_results,
    ):
        mock_submit_task.return_value = "123456"
        mock_check_task_status.return_value = True, None, None
        mock_get_task_results.return_value = (
            True,
            {"count": {"11": 382, "10": 636, "00": 2, "01": 4}},
        )
        driver_quafu.run(job_id, num_qubits, data, data_type, shots)

    def test_convert_results(self):
        driver_quafu.convert_results(result)
        assert result["count"] == {"11": 382, "10": 636, "00": 2, "01": 4}

    def test_convert_code_with_valid_transpile_results(self):
        qubits_num = 1
        src_code = source_code
        transpile_results = []

        results = driver_quafu.convert_code(
            qubits_num, src_code, transpile_results
        )
        assert results == src_code

    def test_convert_code_with_invalid_transpile_results(self):
        """Test convert_code with invalid transpile results."""
        qubits_num = 1
        src_code = source_code
        transpile_results = [
            "invalid",
            "operations",
        ]  # Non-BaseOperation items

        results = driver_quafu.convert_code(
            qubits_num, src_code, transpile_results
        )
        assert results == src_code

    def test_convert_code_with_non_list_transpile_results(self):
        qubits_num = 1
        src_code = source_code
        transpile_results = "not a list"  # Non-list input

        results = driver_quafu.convert_code(
            qubits_num, src_code, transpile_results
        )
        assert results == src_code

    def test_convert_code_with_valid_base_operations(self):
        qubits_num = 1
        src_code = source_code
        transpile_results = []  # Empty list of BaseOperation instances

        results = driver_quafu.convert_code(
            qubits_num, src_code, transpile_results
        )
        assert results == src_code

    def test_convert_code_edge_case_empty_qasm(self):
        qubits_num = 0
        src_code = ""
        transpile_results = []

        results = driver_quafu.convert_code(
            qubits_num, src_code, transpile_results
        )
        assert results == src_code

    def test_convert_code_edge_case_none_transpile_results(self):
        qubits_num = 1
        src_code = source_code
        transpile_results = None

        results = driver_quafu.convert_code(
            qubits_num, src_code, transpile_results
        )
        assert results == src_code
