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
# ----------------------------------------------------------------------

import json
from unittest.mock import patch

import pytest

from qcos.common.library import Library
from qcos.drivers.qboson.driver_tiangong1000 import DriverTiangong1000

driver_tiangong1000 = DriverTiangong1000()
job_id = "00000000-0000-4000-8000-000000000001"
data_index = "123456"
num_qubits = 5
data = {"index": 0, "source_code": "code", "transpile_results": []}
data_type = DriverTiangong1000.DATA_TYPE_GATE_SEQUENCE
shots = 1024
user_id = "000000000000001"
password_sdk_code = ""


class TestDriverTiangong1000:
    def test_init_driver(self):
        assert driver_tiangong1000.init_driver() is None

    def test_validate_driver_configs(self):
        configs = {
            "domain_url_auth": "https://open-pre.qboson.com",
            "domain_url_task": "https://new-open-pre.qboson.com/",
            "user_id": "000000000000001",
            "password_sdk_code": "",
        }
        success, err_msg = driver_tiangong1000.validate_driver_configs(configs)
        assert success is True

        configs = {}
        success, err_msg = driver_tiangong1000.validate_driver_configs(configs)
        assert success is False

    @patch.object(DriverTiangong1000, "get_task_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverTiangong1000, "submit_tasks")
    @patch.object(DriverTiangong1000, "user_auth")
    @patch.object(Library, "is_valid_url")
    def test_run(
        self,
        mock_is_valid_url,
        mock_user_auth,
        mock_submit_tasks,
        mock_loop_with_timeout,
        mock_get_task_status,
    ):
        mock_is_valid_url.return_value = False
        with pytest.raises(ValueError) as context:
            driver_tiangong1000.run(job_id, num_qubits, data, data_type)
        assert "Invalid URL " in str(context.value)

        mock_is_valid_url.return_value = True
        mock_user_auth.return_value = iter([False, "", None])
        with pytest.raises(ValueError) as context:
            driver_tiangong1000.run(job_id, num_qubits, data, data_type)
        assert "Authorize failed " in str(context.value)

        mock_user_auth.return_value = iter([True, "", "fakeToken"])
        mock_submit_tasks.return_value = iter([False, "", "123"])
        with pytest.raises(ValueError) as context:
            driver_tiangong1000.run(job_id, num_qubits, data, data_type)
        assert "Failed to submit task: " in str(context.value)

        mock_user_auth.return_value = iter([True, "", "fakeToken"])
        mock_submit_tasks.return_value = iter([True, "", "123"])
        mock_loop_with_timeout.return_value = iter([False, "", ""])
        with pytest.raises(ValueError) as context:
            driver_tiangong1000.run(job_id, num_qubits, data, data_type)
        assert "Failed to wait for task " in str(context.value)

        mock_user_auth.return_value = iter([True, "", "fakeToken"])
        mock_submit_tasks.return_value = iter([True, "", "123"])
        mock_loop_with_timeout.return_value = iter([True, "", ""])
        mock_get_task_status.return_value = iter([False, "", ""])
        with pytest.raises(ValueError) as context:
            driver_tiangong1000.run(job_id, num_qubits, data, data_type)
        assert "Failed to get task results " in str(context.value)

        mock_user_auth.return_value = iter([True, "", "fakeToken"])
        mock_submit_tasks.return_value = iter([True, "", "123"])
        mock_loop_with_timeout.return_value = iter([True, "", ""])
        mock_get_task_status.return_value = iter([True, "", "-109"])
        assert (
            driver_tiangong1000.run(job_id, num_qubits, data, data_type)
            is None
        )

    @patch.object(Library, "call_http_api")
    def test_user_auth(self, mock_call_http_api):
        json_dict = {
            "code": "",
            "msg": "",
        }
        mock_call_http_api.return_value = iter(
            [503, "", json.dumps(json_dict), ""]
        )
        success, err_msg, token = driver_tiangong1000.user_auth(
            user_id, password_sdk_code
        )
        assert success is False

        json_dict = {"code": "0", "msg": "", "data": {"token": "ABCD"}}
        mock_call_http_api.return_value = iter(
            [200, "", json.dumps(json_dict), ""]
        )
        success, err_msg, token = driver_tiangong1000.user_auth(
            user_id, password_sdk_code
        )
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_submit_tasks(self, mock_call_http_api):
        json_dict = {"code": "0", "msg": "", "data": {"task_id": "1"}}
        mock_call_http_api.return_value = iter(
            [200, "", json.dumps(json_dict), ""]
        )
        success, err_msg, task_id = driver_tiangong1000.submit_tasks(
            job_id, data_index, data
        )
        assert success is True
        assert task_id == "1"

    @patch.object(DriverTiangong1000, "get_task_realtime_result")
    def test_check_task_status(self, mock_get_task_realtime_result):
        mock_get_task_realtime_result.return_value = iter([False, "", None])
        success = driver_tiangong1000.check_task_status("1", 5)
        assert success is False

        mock_get_task_realtime_result.return_value = iter(
            [
                True,
                "",
                {"task_status": driver_tiangong1000.task_status_completed},
            ]
        )
        success = driver_tiangong1000.check_task_status(
            "1", [driver_tiangong1000.task_status_completed]
        )
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_get_task_realtime_result(self, mock_call_http_api):
        json_dict = {
            "code": "0",
            "msg": "",
            "data": {
                "task_status": 1,
                "qubo_value": [-109],
                "qubo_solution_data": [-109],
                "visual_data": [80],
            },
        }
        mock_call_http_api.return_value = iter(
            [
                200,
                "",
                json.dumps(json_dict),
                "",
            ]
        )
        success, err_msg, realtime_status = (
            driver_tiangong1000.get_task_realtime_result("2")
        )
        assert success is True
        assert realtime_status["task_status"] == 1
        assert realtime_status["qubo_value"] == [-109]
        assert realtime_status["qubo_solution_data"] == [-109]
        assert realtime_status["visual_data"] == [80]

    @patch.object(DriverTiangong1000, "get_task_realtime_result")
    def test_get_results(self, mock_get_task_realtime_result):
        mock_get_task_realtime_result.return_value = iter(
            [
                False,
                "",
                {"task_status": driver_tiangong1000.task_status_completed},
            ]
        )
        success, err_msg, realtime_status = (
            driver_tiangong1000.get_task_realtime_result("2")
        )
        assert success is False

        mock_get_task_realtime_result.return_value = iter(
            [True, "", {"task_result": -109}]
        )
        success, err_msg, realtime_status = (
            driver_tiangong1000.get_task_realtime_result("2")
        )
        assert success is True
        assert realtime_status["task_result"] == -109
