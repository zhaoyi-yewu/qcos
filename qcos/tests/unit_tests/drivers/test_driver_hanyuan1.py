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

import pytest

from unittest.mock import patch

from qcos.common.constant import HttpCode
from qcos.common.library import Library
from qcos.drivers.cascoldatom.driver_hanyuan1 import DriverHanyuan1


driver_hanyuan1 = DriverHanyuan1()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {"index": 0, "source_code": None, "transpile_results": []}
data_type = DriverHanyuan1.DATA_TYPE_GATE_SEQUENCE
shots = 1024
method_name = "method_name"


class TestDriverHanyuan1:
    def test_init_driver(self):
        assert driver_hanyuan1.init_driver() is None

    def test_close_driver(self):
        assert driver_hanyuan1.close_driver() is None

    def test_cancel(self):
        assert driver_hanyuan1.cancel(job_id) is None

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs(self, mock_validate_schema):
        configs = {}
        mock_validate_schema.return_value = iter([True, ""])
        success, err_msg = driver_hanyuan1.validate_driver_configs(configs)
        assert success is True

        mock_validate_schema.return_value = iter([False, ""])
        success, err_msg = driver_hanyuan1.validate_driver_configs(configs)
        assert success is False

    @patch.object(DriverHanyuan1, "get_task_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverHanyuan1, "submit_task")
    def test_run(
        self, mock_submit_task, mock_loop_with_timeout, mock_get_task_results
    ):
        mock_submit_task.return_value = iter([False, ""])
        with pytest.raises(ValueError) as context:
            driver_hanyuan1.run(job_id, num_qubits, data, data_type)
        assert "Failed to submit task " in str(context.value)

        mock_submit_task.return_value = iter([True, ""])
        mock_loop_with_timeout.return_value = iter([False, "", ""])
        with pytest.raises(ValueError) as context:
            driver_hanyuan1.run(job_id, num_qubits, data, data_type)
        assert "Failed to wait for task " in str(context.value)

        mock_submit_task.return_value = iter([True, ""])
        mock_loop_with_timeout.return_value = iter([True, "", ""])
        mock_get_task_results.return_value = iter([False, "", ""])
        with pytest.raises(ValueError) as context:
            driver_hanyuan1.run(job_id, num_qubits, data, data_type)
        assert "Failed to get task results " in str(context.value)

        mock_submit_task.return_value = iter([True, ""])
        mock_loop_with_timeout.return_value = iter([True, "", ""])
        mock_get_task_results.return_value = iter([True, "", ""])
        assert driver_hanyuan1.run(job_id, num_qubits, data, data_type) is None

    def test_print_api_response(self):
        driver_hanyuan1.verbose = True
        assert (
            driver_hanyuan1.print_api_response("200", "reason", "edit") is None
        )

    def test_check_task_status(self):
        success, _, _ = driver_hanyuan1.check_task_status(job_id, 1, [])
        assert success is False

    @patch.object(DriverHanyuan1, "call_json_rpc")
    def test_get_task_results(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = iter([
            HttpCode.SUCCESS_OK,
            "no",
            "error",
            {"result": {"status": "success", "result": None}},
        ])

        success, err_msg, result = driver_hanyuan1.get_task_results(job_id, 1)
        assert success is False

    @patch.object(DriverHanyuan1, "call_json_rpc")
    def test_submit_task(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = iter([
            HttpCode.SUCCESS_OK,
            "no",
            "error",
            "error",
        ])
        datas = [{"name": "H", "target": "q1", "arg_value": "pi"}]
        success, err_msg = driver_hanyuan1.submit_task(
            job_id, num_qubits, datas, data_type, shots, 1
        )
        assert success is False
        success, err_msg = driver_hanyuan1.submit_task(
            job_id, num_qubits, datas, data_type, shots, 1
        )
        assert success is False

    @patch.object(Library, "call_http_api")
    def test_call_json_rpc(self, mock_call_http_api):
        mock_call_http_api.return_value = iter(["200", "no", True, "success"])
        status_code, reason, text, result = driver_hanyuan1.call_json_rpc(
            driver_hanyuan1.base_url, method_name, data
        )
        assert status_code == "200"
