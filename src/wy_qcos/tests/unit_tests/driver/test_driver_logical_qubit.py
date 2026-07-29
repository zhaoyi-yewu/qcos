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


org_path = Library.set_driver_venv_path(
    "DriverLogicalQubit", Config.DEFAULT.VENV_DIR
)

import pytest
from unittest.mock import patch, Mock

from wy_qcos.driver.logical_qubit.driver_logical_qubit import (
    DriverLogicalQubit,
)
from wy_qcos.driver.driver_base import DriverBase

driver_logical_qubit = DriverLogicalQubit()
shots = 10
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {
    "index": 0,
    "source_code": "code",
    "transpile_results": [],
    "final_layout_dict": {job_id: {0: 0, 1: 1, 2: 9, 3: 4, 4: 3}},
}
data_type = DriverBase.DATA_TYPE_QASM2
result = {"count": {"11111": 9, "00000": 1}}


class TestDriverLogicalQubit:
    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs(self, mock_validate_schema):
        mock_validate_schema.return_value = True, None
        configs = {}
        success, _ = driver_logical_qubit.validate_driver_configs(configs)
        assert success is True

    def test_init_driver(self):
        assert driver_logical_qubit.init_driver() is None

    @patch("wy_qcos.driver.logical_qubit.driver_logical_qubit.LQCloudProvider")
    def test_fetch_configs(self, mock_task):
        mock_task.return_value = Mock()
        assert driver_logical_qubit.fetch_configs() is None

    def test_cancel(self):
        assert driver_logical_qubit.cancel("1") is None

    def test_get_task_results(self):
        mock_task = Mock()
        expected_data = {"status": "completed", "data": {"00": 9, "11": 1}}
        mock_task.result.return_value = expected_data
        success, result = driver_logical_qubit.get_task_results(mock_task)
        assert success is True

    def test_convert_results(self):
        mock_task = Mock()
        expected_data = {"00000": 9, "11111": 1}
        mock_task.get_counts.return_value = expected_data
        result = driver_logical_qubit.convert_results(mock_task)
        assert result["00000"] == 9

    def test_submit_task(self):
        driver_logical_qubit.backend = Mock()
        expected_task = Mock(name="FakeTaskObject")
        driver_logical_qubit.backend.run.return_value = expected_task
        result_task = driver_logical_qubit.submit_task("qc", shots)
        assert result_task == expected_task

    @pytest.mark.smoke
    @patch.object(DriverLogicalQubit, "convert_results")
    @patch.object(DriverLogicalQubit, "get_task_results")
    @patch.object(DriverLogicalQubit, "submit_task")
    @patch.object(DriverLogicalQubit, "convert_code")
    def test_run(
        self,
        mock_convert_code,
        mock_submit_task,
        mock_get_task_results,
        mock_convert_results,
    ):
        mock_convert_code.return_value = Mock()
        mock_submit_task.return_value = Mock()
        mock_get_task_results.return_value = (
            True,
            {"count": {"11111": 9, "00000": 1}},
        )
        mock_convert_results.return_value = {"11111": 9, "00000": 1}
        driver_logical_qubit.run(job_id, num_qubits, data, data_type, shots)
