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
import pytest
from unittest.mock import patch

from wy_qcos.common.library import Library
from wy_qcos.drivers.spinq.spinq_nmr.driver_spinq_nmr import DriverSpinQNmr
from wy_qcos.transpiler.cmss.common.gate_operation import H

spinq_nmr = DriverSpinQNmr()

driver_config = {
    "remote_host": "127.0.0.1",
    "remote_port": 6060,
    "username": "admin",
    "signature": "",
    "transpiler": {
        "qpu_configs": {
            "qubits": 2,
            "coupler_map": {
                "CX1_2": ["Q1", "Q2"],
                "CX1_3": ["Q1", "Q3"],
                "CX2_1": ["Q2", "Q1"],
                "CX2_3": ["Q2", "Q3"],
                "CX3_1": ["Q3", "Q1"],
                "CX3_2": ["Q3", "Q2"],
            },
        }
    },
}
gate = H(targets=[1])
gates = [gate, gate]
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 2
task_codes = "S-260114-0005"
data = {"index": 0, "source_code": "code", "transpile_results": []}
data_type = DriverSpinQNmr.DATA_TYPE_GATE_SEQUENCE
shots = 10
result = [0.04928965, 0.08267435, 0.08869863, 0.77933737]
converted_result = {"01": 1, "10": 1, "11": 8}
user_name = "admin"
signature = ""
user_auth = {
    "status": 200,
    "msg": "",
    "token": "123456",
    "name": "spinq_visitor_002",
    "hasPassword": True,
}
user_auth_text = json.dumps(user_auth)
submit_task = {
    "status": 200,
    "msg": "",
    "task": {
        "tid": 52460,
        "tcode": "S-260114-0005",
        "tname": "newapitest1",
        "bitNum": 2,
        "shots": 10,
        "sourceType": "spinqit",
        "createdTime": "2026-01-14T06:17:50.438+0000",
        "platformCode": "triangulum_vp",
        "userName": "spinq_visitor_002",
        "timecost": 3.0,
    },
}
submit_task_text = json.dumps(submit_task)
get_result = {
    "status": 200,
    "msg": "",
    "taskStatus": "S",
    "taskErrMsg": None,
    "run": {
        "realMatrix": None,
        "imagMatrix": None,
        "module": [0.04928965, 0.08267435, 0.08869863, 0.77933737],
    },
}
get_result_text = json.dumps(get_result)


class TestDriverSpinQNmr:
    def test_init_driver(self):
        assert spinq_nmr.init_driver() is None

    def test_validate_driver_configs(self):
        success, err_msg = spinq_nmr.validate_driver_configs(driver_config)
        assert success is True
        assert err_msg is None

    def test_convert_gate(self):
        gate_info = spinq_nmr.convert_gate(gate, 1)
        assert gate_info["timeSlot"] == 1
        assert gate_info["gate"]["gname"] == "H"
        assert gate_info["gate"]["gtag"] == "C1"
        assert gate_info["qubits"] == [2]

    def test_convert_gates(self):
        circuits = spinq_nmr.convert_gates(gates, num_qubits)
        assert len(circuits["operations"]) == 2

    @patch.object(DriverSpinQNmr, "user_auth")
    def test_fetch_configs(self, mock_user_auth):
        mock_user_auth.return_value = True, None, task_codes
        assert spinq_nmr.fetch_configs() is None

    @pytest.mark.smoke
    @patch.object(DriverSpinQNmr, "convert_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverSpinQNmr, "submit_task")
    @patch.object(DriverSpinQNmr, "convert_gates")
    def test_run(
        self,
        mock_convert_gates,
        mock_submit_task,
        mock_loop_with_timeout,
        mock_convert_results,
    ):
        mock_convert_gates.return_value = None
        mock_submit_task.return_value = True, None, task_codes
        mock_loop_with_timeout.return_value = True, None, result
        mock_convert_results.return_value = converted_result
        assert (
            spinq_nmr.run(job_id, num_qubits, data, data_type, shots) is None
        )

    @patch.object(Library, "call_http_api")
    def test_user_auth(self, mock_call_http_api):
        mock_call_http_api.return_value = 200, None, user_auth_text, None
        success, err_msg, _ = spinq_nmr.user_auth(user_name, signature)
        assert success is True
        assert err_msg == ""

    @patch.object(Library, "call_http_api")
    def test_submit_task(self, mock_call_http_api):
        mock_call_http_api.return_value = 200, None, submit_task_text, None
        success, err_msg, task_code = spinq_nmr.submit_task("")
        assert success is True
        assert err_msg == ""
        assert task_code == task_codes

    @patch.object(Library, "call_http_api")
    def test_get_task_results(self, mock_call_http_api):
        mock_call_http_api.return_value = 200, None, get_result_text, None
        success, err_msg, results = spinq_nmr.get_task_results(
            task_codes, ["S"]
        )
        assert success is True
        assert err_msg == ""
        assert results == result

    def test_convert_results(self):
        convert_result = spinq_nmr.convert_results(result, num_qubits, shots)
        assert convert_result == converted_result
