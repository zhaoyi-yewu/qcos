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

from wy_qcos_client.client import Client

client = Client()


class TestClient:
    @classmethod
    def setup_class(cls):
        cls.return_values = [-1, "reason", "text", "result"]

    def test_print_api_response(self):
        assert client.print_api_response("200", "OK", "no") is None

    @patch.object(Client, "print_api_response")
    def test_call_json_rpc(self, mock_print_api_response):
        mock_print_api_response.return_value = self.return_values
        status_code, reason, text, result = client.call_json_rpc(
            "127.0.0.1", "get", {}
        )
        assert status_code == -1

    def test_handle_invalid_arguments(self):
        assert client.handle_invalid_arguments([1, 2]) is None

    @patch("wy_qcos_client.client.parse")
    def test_parse_jsonrpc_response(self, mock_parse):
        mock_parse.return_value = None
        success, parse = client.parse_jsonrpc_response(None)
        assert not success

    @patch.object(Client, "call_json_rpc")
    def test_calibrate_device(self, mock_call_json_rpc):
        """Test calibrate_device method."""
        mock_call_json_rpc.return_value = (200, "OK", "text", "result")
        status_code, reason, text, result = client.calibrate_device(
            "device", {"options": "value"}
        )
        assert status_code == 200
        assert reason == "OK"
        assert text == "text"
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_get_calibrate_results(self, mock_call_json_rpc):
        """Test get_calibrate_results method."""
        mock_call_json_rpc.return_value = (200, "OK", "text", "result")
        status_code, reason, text, result = client.get_calibrate_results(
            "device"
        )
        assert status_code == 200
        assert reason == "OK"
        assert text == "text"
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_set_device_options(self, mock_call_json_rpc):
        """Test set_device_options method."""
        mock_call_json_rpc.return_value = (200, "OK", "text", "result")
        status_code, reason, text, result = client.set_device_options(
            "device", {"options": "value"}
        )
        assert status_code == 200
        assert reason == "OK"
        assert text == "text"
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_get_device_options(self, mock_call_json_rpc):
        """Test get_device_options method."""
        mock_call_json_rpc.return_value = (200, "OK", "text", "result")
        status_code, reason, text, result = client.get_device_options("device")
        assert status_code == 200
        assert reason == "OK"
        assert text == "text"
        assert result == "result"
