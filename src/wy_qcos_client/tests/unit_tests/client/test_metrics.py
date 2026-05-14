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

    @patch.object(Client, "call_json_rpc")
    def test_get_system_health(self, mock_call_json_rpc):
        """Test get_system_health method."""
        mock_call_json_rpc.return_value = (
            200,
            "OK",
            "text",
            {"healthy": True},
        )
        status_code, reason, text, result = client.get_system_health()
        assert status_code == 200
        assert reason == "OK"
        assert text == "text"
        assert result == {"healthy": True}
        mock_call_json_rpc.assert_called_once_with(
            client.metrics_url, "get_system_health", data=None
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_system_health_failure(self, mock_call_json_rpc):
        """Test get_system_health method with failure response."""
        mock_call_json_rpc.return_value = (
            500,
            "Internal Server Error",
            "error",
            None,
        )
        status_code, reason, text, result = client.get_system_health()
        assert status_code == 500
        assert reason == "Internal Server Error"
        assert text == "error"
        assert result is None

    @patch.object(Client, "call_json_rpc")
    def test_get_api_stats(self, mock_call_json_rpc):
        """Test get_api_stats method."""
        mock_call_json_rpc.return_value = (
            200,
            "OK",
            "text",
            {
                "total_requests": 1000,
                "last_hour_requests": 50,
                "last_day_requests": 500,
            },
        )
        status_code, reason, text, result = client.get_api_stats()
        assert status_code == 200
        assert reason == "OK"
        assert text == "text"
        assert result == {
            "total_requests": 1000,
            "last_hour_requests": 50,
            "last_day_requests": 500,
        }
        mock_call_json_rpc.assert_called_once_with(
            client.metrics_url, "get_api_stats", data=None
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_api_stats_failure(self, mock_call_json_rpc):
        """Test get_api_stats method with failure response."""
        mock_call_json_rpc.return_value = (
            500,
            "Internal Server Error",
            "error",
            None,
        )
        status_code, reason, text, result = client.get_api_stats()
        assert status_code == 500
        assert reason == "Internal Server Error"
        assert text == "error"
        assert result is None

    @patch.object(Client, "call_json_rpc")
    def test_get_job_stats(self, mock_call_json_rpc):
        """Test get_job_stats method."""
        mock_call_json_rpc.return_value = (
            200,
            "OK",
            "text",
            {
                "total": 100,
                "completed": 80,
                "failed": 10,
                "running": 5,
                "queued": 3,
                "cancelling": 1,
                "cancelled": 1,
                "deleted": 0,
                "unknown": 0,
            },
        )
        status_code, reason, text, result = client.get_job_stats()
        assert status_code == 200
        assert reason == "OK"
        assert text == "text"
        assert result == {
            "total": 100,
            "completed": 80,
            "failed": 10,
            "running": 5,
            "queued": 3,
            "cancelling": 1,
            "cancelled": 1,
            "deleted": 0,
            "unknown": 0,
        }
        mock_call_json_rpc.assert_called_once_with(
            client.metrics_url, "get_job_stats", data=None
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_job_stats_failure(self, mock_call_json_rpc):
        """Test get_job_stats method with failure response."""
        mock_call_json_rpc.return_value = (400, "Bad Request", "error", None)
        status_code, reason, text, result = client.get_job_stats()
        assert status_code == 400
        assert reason == "Bad Request"
        assert text == "error"
        assert result is None
