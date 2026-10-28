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

"""Unit tests for Client.get_proxy_health."""

from unittest.mock import patch

from wy_qcos_client.client import Client


class TestGetProxyHealth:
    """Tests for Client.get_proxy_health."""

    @patch.object(Client, "call_json_rpc")
    def test_get_proxy_health(self, mock_call_json_rpc):
        """Happy path: server returns a list of proxy targets."""
        client = Client()
        mock_call_json_rpc.return_value = (
            200,
            "OK",
            "text",
            {
                "targets": [
                    {
                        "name": "prometheus",
                        "path": "/v1/proxy/prometheus",
                        "base_url": "http://127.0.0.1:9090",
                        "enabled": True,
                        "healthy": True,
                        "status": "online",
                        "latency_ms": 3,
                        "detail": "",
                    }
                ]
            },
        )
        status_code, reason, text, result = client.get_proxy_health()
        assert status_code == 200
        assert reason == "OK"
        assert result["targets"][0]["name"] == "prometheus"
        assert result["targets"][0]["status"] == "online"
        mock_call_json_rpc.assert_called_once_with(
            client.metrics_url, "get_proxy_health", body_data=None
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_proxy_health_failure(self, mock_call_json_rpc):
        """Failure path: server returns 500."""
        client = Client()
        mock_call_json_rpc.return_value = (
            500,
            "Internal Server Error",
            "error",
            None,
        )
        status_code, reason, text, result = client.get_proxy_health()
        assert status_code == 500
        assert reason == "Internal Server Error"
        assert result is None
