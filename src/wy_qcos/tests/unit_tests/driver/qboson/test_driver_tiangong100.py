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

from unittest.mock import patch

import pytest

from wy_qcos.common.library import Library, _s
from wy_qcos.driver.qboson.driver_tiangong100 import DriverTiangong100

driver_tiangong100 = DriverTiangong100()
driver_tiangong100.base_url = ""
username = "username"
passwd = _s("")
job_id = "00000000-0000-4000-8000-000000000001"
task_id = "123456"
num_qubits = 5
data = {"index": 0, "source_code": "code", "transpile_results": []}
data_type = DriverTiangong100.DATA_TYPE_GATE_SEQUENCE
shots = 1024


@pytest.mark.driver
class TestDriverTiangong100:
    def test_init_driver(self):
        assert driver_tiangong100.init_driver() is None

    def test_validate_driver_configs(self):
        configs = {}
        success, err_msg = driver_tiangong100.validate_driver_configs(configs)
        assert success is False

    def test_close_driver(self):
        assert driver_tiangong100.close_driver() is None

    @pytest.mark.smoke
    @patch.object(DriverTiangong100, "get_task_results")
    @patch.object(DriverTiangong100, "get_task_id")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverTiangong100, "submit_tasks")
    @patch.object(DriverTiangong100, "upload_file")
    @patch.object(DriverTiangong100, "check_device_status")
    @patch.object(DriverTiangong100, "user_auth")
    @patch.object(Library, "is_valid_url")
    def test_run(
        self,
        mock_is_valid_url,
        mock_user_auth,
        mock_check_device_status,
        mock_upload_file,
        mock_submit_tasks,
        mock_loop_with_timeout,
        mock_get_task_id,
        mock_get_task_results,
    ):
        mock_is_valid_url.return_value = False
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert "Invalid URL " in str(context.value)

        mock_is_valid_url.return_value = True
        mock_loop_with_timeout.return_value = iter([False, "", ""])
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert "Authorize failed " in str(context.value)

        mock_loop_with_timeout.side_effect = [
            iter([True, "", ""]),
            iter([False, "", ""]),
        ]
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert str(context.value) is not None

        mock_loop_with_timeout.side_effect = [
            iter([True, "", ""]),
            iter([True, "", ""]),
            iter([False, "", ""]),
        ]
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert "Failed to upload file " in str(context.value)

        mock_loop_with_timeout.side_effect = [
            iter([True, "", ""]),
            iter([True, "", ""]),
            iter([
                True,
                "",
                {"creator": "admin", "id": task_id, "name": username},
            ]),
            iter([False, "", ""]),
        ]
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert "Failed to submit task " in str(context.value)

        mock_loop_with_timeout.side_effect = [
            iter([True, "", ""]),
            iter([True, "", ""]),
            iter([
                True,
                "",
                {"creator": "admin", "id": task_id, "name": username},
            ]),
            iter([True, "", ""]),
            iter([False, "", ""]),
        ]
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert "Failed to wait for task " in str(context.value)

        mock_loop_with_timeout.side_effect = [
            iter([True, "", ""]),
            iter([True, "", ""]),
            iter([
                True,
                "",
                {"creator": "admin", "id": task_id, "name": username},
            ]),
            iter([True, "", ""]),
            iter([True, "", ""]),
        ]
        mock_get_task_id.return_value = iter([False, "", {"id": task_id}])
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert "Failed to get task id " in str(context.value)

        mock_loop_with_timeout.side_effect = [
            iter([True, "", ""]),
            iter([True, "", ""]),
            iter([
                True,
                "",
                {"creator": "admin", "id": task_id, "name": username},
            ]),
            iter([True, "", ""]),
            iter([True, "", ""]),
        ]
        mock_get_task_id.return_value = iter([True, "", {"id": task_id}])
        mock_get_task_results.return_value = iter([False, "", ""])
        with pytest.raises(ValueError) as context:
            driver_tiangong100.run(job_id, num_qubits, data, data_type)
        assert "Failed to get task results " in str(context.value)

        mock_loop_with_timeout.side_effect = [
            iter([True, "", ""]),
            iter([True, "", ""]),
            iter([
                True,
                "",
                {"creator": "admin", "id": task_id, "name": username},
            ]),
            iter([True, "", ""]),
            iter([True, "", ""]),
        ]
        mock_get_task_id.return_value = iter([True, "", {"id": task_id}])
        mock_get_task_results.return_value = iter([True, "", ""])
        assert (
            driver_tiangong100.run(job_id, num_qubits, data, data_type) is None
        )

    @patch.object(Library, "call_http_api")
    def test_user_auth(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "","msg": ""}',
            "",
        ])
        success, err_msg, token = driver_tiangong100.user_auth(
            username, passwd
        )
        assert success is False

        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "","msg": ""}',
            "",
        ])
        success, err_msg, token = driver_tiangong100.user_auth(
            username, passwd
        )
        assert success is False

    @patch.object(Library, "call_http_api")
    def test_check_device_status(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "0","msg": "","data": {"status": 0,"status_desc": 1}}',
            "",
        ])
        success, err_msg, _ = driver_tiangong100.check_device_status(job_id)
        assert success is False

    @patch.object(Library, "call_http_api")
    def test_upload_file(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "0",'
            '"msg": "",'
            '"data": {'
            '"creator": "",'
            '"id": "",'
            ' "name": ""'
            "}}",
            "",
        ])
        success, err_msg, file_info = driver_tiangong100.upload_file(
            job_id, "", data
        )
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_submit_tasks(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "0","msg": ""}',
            "",
        ])
        success, err_msg, _ = driver_tiangong100.submit_tasks([])
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_get_task_id(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "0","msg": "","data": {}}',
            "",
        ])
        success, err_msg, task_info = driver_tiangong100.get_task_id(task_id)
        assert success is False

    @patch.object(DriverTiangong100, "get_task_id")
    def test_check_task_status(self, mock_get_task_id):
        mock_get_task_id.return_value = iter([True, "", {"id": task_id}])
        success, _, _ = driver_tiangong100.check_task_status(job_id, [])
        assert success is False

    @patch.object(Library, "call_http_api")
    def test_get_task_results(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "0","msg": "","data": {"out_data": 0,"visual_data": 0}}',
            "",
        ])
        success, err_msg, result = driver_tiangong100.get_task_results(job_id)
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_delete_task(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([
            200,
            "",
            '{"code": "0","msg": ""}',
            "",
        ])
        success, err_msg = driver_tiangong100.delete_task(job_id)
        assert success is True

    def test_get_fake_results(self):
        result = driver_tiangong100.get_fake_results(num_qubits, shots, data)
        assert len(result) == 10

    def test_cancel(self):
        assert driver_tiangong100.cancel(job_id) is None
