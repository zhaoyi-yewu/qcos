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

from unittest.mock import patch

from qcos.client.client import Client
from qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)

client = Client()


class TestClient:
    @classmethod
    def setup_class(cls):
        cls.return_values = [-1, "reason", "text", "result"]
        cls.job_id = ConstantForTest.job_id
        cls.job_ids = ConstantForTest.job_ids

    def test_print_api_response(self):
        client.print_api_response("200", "no", "no")

    @patch.object(Client, "print_api_response")
    def test_call_json_rpc(self, mock_print_api_response):
        mock_print_api_response.return_value = self.return_values
        status_code, reason, text, result = client.call_json_rpc(
            "127.0.0.1", "get", {}
        )
        assert status_code == -1

    def test_handle_invalid_arguments(self):
        client.handle_invalid_arguments([1, 2])

    @patch.object(Client, "call_json_rpc")
    def test_version(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.version()
        assert reason == "reason"

    @patch.object(Client, "call_json_rpc")
    def test_get_drivers(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_drivers()
        assert text == "text"

    @patch.object(Client, "call_json_rpc")
    def test_get_driver(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_driver("driver")
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_get_devices(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_devices()
        assert status_code == -1

    @patch.object(Client, "call_json_rpc")
    def test_get_device(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_device("device")
        assert reason == "reason"

    @patch.object(Client, "call_json_rpc")
    def test_get_transpilers(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_transpilers()
        assert text == "text"

    @patch.object(Client, "call_json_rpc")
    def test_get_transpiler(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_transpiler("transpiler")
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_ping(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.ping("msg")
        assert status_code == -1

    @patch.object(Client, "call_json_rpc")
    def test_submit_job(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.submit_job("msg")
        assert reason == "reason"

    @patch.object(Client, "call_json_rpc")
    def test_get_job_status(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_job_status(self.job_id)
        assert text == "text"

    @patch.object(Client, "call_json_rpc")
    def test_get_jobs(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_jobs()
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_cancel_jobs(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.cancel_jobs(self.job_ids)
        assert status_code == -1

    @patch.object(Client, "call_json_rpc")
    def test_delete_jobs(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.delete_jobs(self.job_ids)
        assert reason == "reason"

    @patch.object(Client, "call_json_rpc")
    def test_set_job_results(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.set_job_results(
            self.job_id, "result"
        )
        assert text == "text"

    @patch.object(Client, "call_json_rpc")
    def test_system_info(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.system_info()
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_get_job_results(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_job_results(self.job_id)
        assert status_code == -1

    @patch("qcos.client.client.parse")
    def test_parse_jsonrpc_response(self, mock_parse):
        mock_parse.return_value = None
        success, parse = client.parse_jsonrpc_response(None)
        assert not success

    @patch.object(Client, "call_json_rpc")
    def test_update_job(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_job("msg")
        assert reason == "reason"
