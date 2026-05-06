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

org_path = Library.set_driver_venv_path("DriverSpinQRpc", Config.VENV_DIR)

import json
import pytest
import sys
import unittest
import zerorpc
from unittest.mock import patch, MagicMock

from wy_qcos.common.library import _s
from wy_qcos.drivers.spinq.spinq_rpc.driver_spinq_rpc import DriverSpinQRpc
from wy_qcos.common.cmss.gate_operation import CX, H, RX, RY, RZ
from wy_qcos.common.cmss.measure import Measure

job_id = "00000000-0000-4000-8000-000000000001"
task_id = "123456"
session_id = "1000000000000000000000000000000000000001"
coupling_list = [
    (0, 1),
    (1, 0),
    (1, 2),
    (2, 1),
    (0, 3),
    (3, 0),
    (1, 4),
    (2, 5),
    (5, 2),
    (3, 4),
    (4, 3),
    (4, 5),
    (5, 4),
]
username = "username"
passwd = _s("")
num_qubits = 5
chip_name = "chip_name"
data = {"index": 0, "source_code": None, "transpile_results": []}
data_type = DriverSpinQRpc.DATA_TYPE_GATE_SEQUENCE
shots = 1024
results = {"task_result": {"qubit_result": {"000": 1, "010": 9}}}


def validate_converted_gate(actual_info, expected_info):
    assert actual_info["angle"] == expected_info["angle"]
    assert actual_info["controlQubit"] == expected_info["controlQubit"]
    assert actual_info["qubitIndex"] == expected_info["qubitIndex"]
    assert actual_info["type"] == expected_info["type"]
    assert actual_info["timeslot"] == expected_info["timeslot"]


@pytest.mark.driver
class TestDriverSpinQRpc(unittest.TestCase):
    def setUp(self):
        self.driver = DriverSpinQRpc()
        self.driver._rpc_conn_str = "tcp://127.0.0.1:4242"
        self.driver.max_retries = 3
        self.mock_client = MagicMock()
        self.driver._client = self.mock_client

    @classmethod
    def teardown_class(cls):
        sys.path = org_path

    def test_init_driver(self):
        assert self.driver.init_driver() is None

    @patch("zerorpc.Client")
    @patch.object(DriverSpinQRpc, "user_auth")
    def test_fetch_configs(self, mock_user_auth, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        _results = {
            "session_id": session_id,
            "coupling_list": coupling_list,
            "qpu_configs": {
                "num_qubits": 6,
                "coupling_map": coupling_list,
            },
        }
        mock_user_auth.return_value = True, "", _results
        assert self.driver.fetch_configs() is not None

    @patch.object(DriverSpinQRpc, "client_close")
    def test_close_driver(self, mock_client_close):
        mock_client_close.return_value = None
        assert self.driver.close_driver() is None
        self.driver._session_id = session_id
        assert self.driver.close_driver() is None

    def test_cancel(self):
        self.driver.cancel(job_id)

    def test_validate_driver_configs(self):
        configs = {
            "rpc_host": DriverSpinQRpc.default_rpc_host,
            "rpc_port": DriverSpinQRpc.default_rpc_port,
            "username": "username",
            "password": "password",
        }
        success, err_msg = self.driver.validate_driver_configs(configs)
        assert success is True

        configs["rpc_port"] = str(DriverSpinQRpc.default_rpc_port)
        success, err_msg = self.driver.validate_driver_configs(configs)
        assert success is False

    @pytest.mark.smoke
    @patch.object(DriverSpinQRpc, "submit_task")
    @patch.object(DriverSpinQRpc, "check_task_status")
    @patch.object(DriverSpinQRpc, "get_task_results")
    @patch.object(DriverSpinQRpc, "client_close")
    def test_run(
        self,
        mock_client_close,
        mock_get_task_results,
        mock_check_task_status,
        mock_submit_task,
    ):
        mock_submit_task.return_value = True, "", task_id
        mock_check_task_status.return_value = True, None, None
        mock_get_task_results.return_value = True, "", results
        mock_client_close.return_value = None
        self.driver.run(job_id, num_qubits, data, data_type, shots)
        assert self.driver.get_progress() == 100

    def test_user_auth(self):
        request_login_response = {
            "return_code": 0,
            "qubits_num": 5,
            "session_id": session_id,
            "chip_name": chip_name,
            "coupling_list": [],
        }
        self.mock_client.request_login.return_value = json.dumps(
            request_login_response
        )
        success, err_msg, _results = self.driver.user_auth(username, passwd)
        assert success is True
        assert err_msg is None
        assert _results == request_login_response

    def test_user_auth_rpc_error(self):
        self.mock_client.request_login.side_effect = (
            zerorpc.exceptions.LostRemote("Connection lost")
        )
        self.mock_client.client.close = None
        self.mock_client.client.connect = None
        success, err_msg, _results = self.driver.user_auth(username, passwd)
        assert success is False
        assert err_msg is not None

    def test_submit_task(self):
        # 设置 available_num_qubits，因为convert_gates需要它来初始化qubit_depth
        self.driver.available_num_qubits = 6
        h = H([0])
        cx = CX([1, 2])
        rx = RX([3], [1.0])
        ry = RY([4], [1.0])
        rz = RZ([5], [1.0])
        mea_targets = [0, 1, 2, 3, 4, 5]
        measure = Measure(mea_targets)
        transpile_results = [rx, ry, rz, h, cx, measure]
        task_gates, measures = self.driver.convert_gates(transpile_results, 6)
        assert measures == mea_targets
        assert len(task_gates) == 5

        validate_converted_gate(
            task_gates[0],
            {
                "angle": 1.0,
                "controlQubit": -1,
                "qubitIndex": 3,
                "type": "rx",
                "timeslot": 0,
            },
        )
        validate_converted_gate(
            task_gates[1],
            {
                "angle": 1.0,
                "controlQubit": -1,
                "qubitIndex": 4,
                "type": "ry",
                "timeslot": 0,
            },
        )
        validate_converted_gate(
            task_gates[2],
            {
                "angle": 1.0,
                "controlQubit": -1,
                "qubitIndex": 5,
                "type": "rz",
                "timeslot": 0,
            },
        )
        validate_converted_gate(
            task_gates[3],
            {
                "angle": 0,
                "controlQubit": -1,
                "qubitIndex": 0,
                "type": "h",
                "timeslot": 0,
            },
        )
        validate_converted_gate(
            task_gates[4],
            {
                "angle": 0,
                "controlQubit": 1,
                "qubitIndex": 2,
                "type": "cx",
                "timeslot": 0,
            },
        )
        task_info = {
            "task_name": "task name",
            "task_gates": task_gates,
            "measures": measures,
            "task_desc": "task desc",
            "shots": shots,
        }
        self.mock_client.push_task.return_value = 0, task_id
        success, err_msg, _task_id = self.driver.submit_task(task_info)
        assert success is True
        assert _task_id == task_id

    @patch.object(DriverSpinQRpc, "get_task_status")
    def test_check_task_status(self, mock_get_task_status):
        finished = 0
        mock_get_task_status.return_value = True, "", finished
        success, _, task_status = self.driver.check_task_status(
            task_id, [finished]
        )
        assert success is True
        assert task_status is finished

    def test_get_task_status(self):
        finished = 0
        self.mock_client.get_task_status = MagicMock()
        self.mock_client.get_task_status.return_value = finished
        success, err_msg, task_status = self.driver.get_task_status(task_id)
        assert success is True
        assert task_status == finished

    def test_get_task_results(self):
        self.mock_client.get_task_result.return_value = json.dumps(results)
        success, err_msg, response = self.driver.get_task_results(task_id)
        assert success is True
        assert response == results

    def test_client_close(self):
        self.mock_client.request_logout.return_value = None
        self.mock_client.close.return_value = None
        assert self.driver.client_close(username, session_id) is None

    def test_convert_results(self):
        self.mock_client.get_task_result.return_value = json.dumps(results)
        success, err_msg, response = self.driver.get_task_results(task_id)
        assert success is True
        assert response == results

        conv_results = self.driver.convert_results(response["task_result"])
        assert len(conv_results) == 2
        assert conv_results["000"] == 1
        assert conv_results["010"] == 9
