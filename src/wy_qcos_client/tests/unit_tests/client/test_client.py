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

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_call_json_rpc(self, mock_print_api_response, mock_call_http_api):
        mock_call_http_api.return_value = self.return_values
        mock_print_api_response.return_value = self.return_values
        status_code, reason, text, result = client.call_json_rpc(
            "http://127.0.0.1", "get", {}
        )
        assert status_code == -1
        mock_call_http_api.assert_called_once()

    def test_handle_invalid_arguments(self):
        assert client.handle_invalid_arguments([1, 2]) is None

    @patch("wy_qcos_client.client.jsonrpcclient.parse")
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


class TestTimeoutPrecedence:
    """Test timeout resolution in call_json_rpc."""

    def setup_method(self):
        """Reset class-level timeout flags before each test."""
        Client.timeout = 60
        Client.timeout_from_cli = False

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_cli_timeout_ignores_env(self, mock_print, mock_call_http_api):
        """When timeout_from_cli=True, env var is ignored."""
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        mock_print.return_value = [-1, "reason", "text", "result"]
        Client.timeout = 120
        Client.timeout_from_cli = True
        with patch.dict("os.environ", {"QCOS_CLIENT_TIMEOUT": "30"}):
            client.call_json_rpc("http://127.0.0.1", "get", {})
        kwargs = mock_call_http_api.call_args.kwargs
        assert kwargs["timeout"] == 120

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_env_timeout_when_not_from_cli(
        self, mock_print, mock_call_http_api
    ):
        """When timeout_from_cli=False, env var overrides default."""
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        mock_print.return_value = [-1, "reason", "text", "result"]
        Client.timeout = 60
        Client.timeout_from_cli = False
        with patch.dict("os.environ", {"QCOS_CLIENT_TIMEOUT": "45"}):
            client.call_json_rpc("http://127.0.0.1", "get", {})
        kwargs = mock_call_http_api.call_args.kwargs
        assert kwargs["timeout"] == 45

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_default_timeout_no_env(self, mock_print, mock_call_http_api):
        """When no cli and no env, default timeout is used."""
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        mock_print.return_value = [-1, "reason", "text", "result"]
        Client.timeout = 60
        Client.timeout_from_cli = False
        with patch.dict("os.environ", {}, clear=True):
            client.call_json_rpc("http://127.0.0.1", "get", {})
        kwargs = mock_call_http_api.call_args.kwargs
        assert kwargs["timeout"] == 60
