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

import json
from unittest.mock import patch

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library
from wy_qcos.drivers.ciqtek.driver_ciqtek_ion_1 import DriverCiqtekIon1
from wy_qcos.drivers.driver_base import DriverBase

driver_ion_trap = DriverCiqtekIon1()
response_data = {
    "code": 10000,
    "msg": "请求成功",
    "data": {
        "access_token": "",
        "expires_in": 7200,
        "experimentId": "",
        "status": 2,
        "result": {},
    },
}
get_data = json.dumps(response_data)
result = [
    {"name": "00", "value": 0.25},
    {"name": "01", "value": 0.25},
    {"name": "10", "value": 0.25},
    {"name": "11", "value": 0.25},
]
job_id = "00000000-0000-4000-8000-000000000001"
task_id = "123456"
num_qubits = 2
data = {"index": 0, "source_code": "code", "transpile_results": []}
data_type = DriverBase.DATA_TYPE_QASM2
shots = 100


class TestDriverCiqtekIon1:
    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs(self, mock_validate_schema):
        mock_validate_schema.return_value = True, None
        success, _ = driver_ion_trap.validate_driver_configs(Config)
        assert success is True

    def test_init_driver(self):
        assert driver_ion_trap.init_driver() is None

    def test_close_driver(self):
        assert driver_ion_trap.close_driver() is None

    @patch.object(DriverCiqtekIon1, "get_access_token")
    @patch.object(DriverCiqtekIon1, "refresh_access_token")
    def test_fetch_config(self, mock_refresh, mock_get):
        mock_refresh.return_value = True, None, ""
        mock_get.return_value = True, None, ""
        assert driver_ion_trap.fetch_configs() is None

    @patch.object(Library, "call_http_api")
    def test_get_access_token(self, mock_call_http):
        mock_call_http.return_value = 200, None, get_data, None
        success, _, _ = driver_ion_trap.get_access_token("", "")
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_refresh_access_token(self, mock_call_http):
        mock_call_http.return_value = 200, None, get_data, None
        success, _, _ = driver_ion_trap.refresh_access_token("")
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_submit_task(self, mock_call_http):
        mock_call_http.return_value = 200, None, get_data, None
        success, _, _ = driver_ion_trap.submit_task("", "")
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_get_task_result(self, mock_call_http):
        mock_call_http.return_value = 200, None, get_data, None
        success, _, _ = driver_ion_trap.get_task_result("", [2])
        assert success is True

    def test_convert_result(self):
        converted_result = driver_ion_trap.convert_result(result, shots)
        assert converted_result["00"] == 25

    @patch.object(DriverCiqtekIon1, "convert_result")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverCiqtekIon1, "submit_task")
    def test_run(
        self, mock_submit_task, mock_loop_with_timeout, mock_convert_result
    ):
        mock_loop_with_timeout.return_value = True, None, ""
        mock_submit_task.return_value = True, None, ""
        mock_convert_result.return_value = ""
        assert (
            driver_ion_trap.run(job_id, num_qubits, data, data_type, shots)
            is None
        )
