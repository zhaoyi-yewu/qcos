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
    def test_ping(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.ping("msg")
        assert status_code == -1

    @patch.object(Client, "call_json_rpc")
    def test_system_info(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.system_info()
        assert result == "result"

    @patch.object(Client, "call_json_rpc")
    def test_show_mem(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.show_mem()
        assert result == "result"
        mock_call_json_rpc.assert_called_once_with(
            client.system_url, "show_mem", body_data=None
        )

    @patch.object(Client, "call_json_rpc")
    def test_debug_gc_default(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.debug_gc()
        assert result == "result"
        mock_call_json_rpc.assert_called_once_with(
            client.system_url, "debug_gc", {"generations": 2}
        )

    @patch.object(Client, "call_json_rpc")
    def test_debug_gc_custom_generations(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.debug_gc(generations=0)
        assert result == "result"
        mock_call_json_rpc.assert_called_once_with(
            client.system_url, "debug_gc", {"generations": 0}
        )

    @patch.object(Client, "call_json_rpc")
    def test_debug_tracemalloc_default(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.debug_tracemalloc()
        assert result == "result"
        mock_call_json_rpc.assert_called_once_with(
            client.system_url,
            "debug_tracemalloc",
            {"action": "snapshot", "nframe": 25},
        )

    @patch.object(Client, "call_json_rpc")
    def test_debug_tracemalloc_custom_nframe(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.debug_tracemalloc(nframe=10)
        assert result == "result"
        mock_call_json_rpc.assert_called_once_with(
            client.system_url,
            "debug_tracemalloc",
            {"action": "snapshot", "nframe": 10},
        )

    @patch.object(Client, "call_json_rpc")
    def test_debug_tracemalloc_stop(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.debug_tracemalloc(
            action="stop"
        )
        assert result == "result"
        mock_call_json_rpc.assert_called_once_with(
            client.system_url,
            "debug_tracemalloc",
            {"action": "stop", "nframe": 25},
        )

    @patch.object(Client, "call_json_rpc")
    def test_debug_tracemalloc_clear(self, mock_call_json_rpc):
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.debug_tracemalloc(
            action="clear"
        )
        assert result == "result"
        mock_call_json_rpc.assert_called_once_with(
            client.system_url,
            "debug_tracemalloc",
            {"action": "clear", "nframe": 25},
        )
