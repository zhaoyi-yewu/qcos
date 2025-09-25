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
import unittest
import zerorpc
from unittest.mock import patch, MagicMock

from qcos.drivers.spinq.driver_spinq_rpc import DriverSpinQRpc


job_id = "00000000-0000-4000-8000-000000000001"
task_id = "123456"
session_id = "1000000000000000000000000000000000000001"
coupling_list = [(0, 1), (1, 0), (1, 2), (2, 1), (0, 3), (3, 0),
                 (1, 4), (2, 5), (5, 2), (3, 4), (4, 3), (4, 5),
                 (5, 4)]
username = "username"
password = ""
num_qubits = 5
chip_name = "chip_name"
data = {'index': 0, 'source_code': None, 'transpile_results': []}
data_type = DriverSpinQRpc.DATA_TYPE_GATE_SEQUENCE
shots = 1024
results = {"00": shots}


class TestDriverSpinQRpc(unittest.TestCase):
    def setUp(self):
        self.driver = DriverSpinQRpc()
        self.driver._rpc_conn_str = "tcp://127.0.0.1:4242"
        self.driver.max_retries = 3
        self.mock_client = MagicMock()
        self.driver._client = self.mock_client

    def test_init_driver(self):
        assert self.driver.init_driver() is None

    @patch("zerorpc.Client")
    @patch.object(DriverSpinQRpc, "user_auth")
    def test_fetch_configs(self, mock_user_auth, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        _results = {
            "session_id": session_id,
            "coupling_list": coupling_list
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
            "password": "password"
        }
        success, err_msg = self.driver.validate_driver_configs(configs)
        assert success is True

        configs["rpc_port"] = str(DriverSpinQRpc.default_rpc_port)
        success, err_msg = self.driver.validate_driver_configs(configs)
        assert success is False

    @patch.object(DriverSpinQRpc, "submit_task")
    @patch.object(DriverSpinQRpc, "check_task_status")
    @patch.object(DriverSpinQRpc, "get_task_results")
    @patch.object(DriverSpinQRpc, "client_close")
    def test_run(self, mock_client_close, mock_get_task_results,
                 mock_check_task_status, mock_submit_task):
        mock_submit_task.return_value = True, "", task_id
        mock_check_task_status.return_value = True
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
            "coupling_list": []
        }
        self.mock_client.request_login.return_value = json.dumps(
            request_login_response)
        success, err_msg, _results = self.driver.user_auth(username, password)
        assert success is True
        assert err_msg is None
        assert _results == request_login_response

    def test_user_auth_rpc_error(self):
        self.mock_client.request_login.side_effect = \
            zerorpc.exceptions.LostRemote("Connection lost")
        self.mock_client.client.close = None
        self.mock_client.client.connect = None
        success, err_msg, _results = self.driver.user_auth(username, password)
        assert success is False
        assert err_msg is not None

    def test_submit_task(self):
        task_info = {
            "task_name": "task name",
            "task_gates": [],
            "measures": [],
            "task_desc": "task desc",
            "shots": shots
        }
        self.mock_client.push_task.return_value = 0, task_id
        success, err_msg, _task_id = self.driver.submit_task(task_info)
        assert success is True
        assert _task_id == task_id

    @patch.object(DriverSpinQRpc, "get_task_status")
    def test_check_task_status(self, mock_get_task_status):
        finished = 0
        mock_get_task_status.return_value = True, "", finished
        success = self.driver.check_task_status(task_id, [finished])
        assert success is True

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
