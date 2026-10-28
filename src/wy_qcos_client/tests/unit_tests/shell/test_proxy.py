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

"""Unit tests for the get-proxy-health shell command."""

from argparse import Namespace
from unittest.mock import Mock, patch

import pytest
from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client
from wy_qcos_client.common import errors
from wy_qcos_client.common.qcos_version import QcosVersion
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    GetProxyHealth,
)

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()


def _make_target(
    name="prometheus",
    status="online",
    enabled=True,
    healthy=True,
    latency_ms=3,
    base_url="http://127.0.0.1:9090",
    detail="",
):
    return {
        "name": name,
        "path": f"/v1/proxy/{name}",
        "base_url": base_url,
        "enabled": enabled,
        "healthy": healthy,
        "status": status,
        "latency_ms": latency_ms,
        "detail": detail,
    }


class TestGetProxyHealth:
    """Tests for the GetProxyHealth shell command."""

    def test_get_parser(self):
        cmd = GetProxyHealth(shell, None)
        parser = cmd.get_parser("")
        assert parser is not None

    def test_group_is_proxy(self):
        """The command must be registered under the Proxy group."""
        assert GetProxyHealth.group == QcosShell.CMD_GROUP_PROXY
        assert QcosShell.CMD_GROUP_PROXY == "Proxy"
        assert QcosShell.CMD_GROUP_PROXY in QcosShell.CMD_GROUPS

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_proxy_health")
    def test_take_action_all_online(
        self,
        mock_get_proxy_health,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_proxy_health.return_value = (200, "OK", "text", None)
        mock_check_results.return_value = {
            "targets": [
                _make_target("prometheus"),
                _make_target("alertmanager", base_url="http://127.0.0.1:9093"),
            ],
        }
        mock_get_table_list_data.return_value = None
        table_values = GetProxyHealth(shell, None).take_action(mock_client)
        assert table_values is None

        # Inspect what was passed to get_table_list_data.
        # The shell calls it as (stats_list, header_list, is_dict=False)
        # so we read positional args and check the kwarg explicitly.
        stats_list, header_list = mock_get_table_list_data.call_args[0]
        assert (
            mock_get_table_list_data.call_args.kwargs.get("is_dict") is False
        )
        assert "NAME" in header_list
        assert "STATUS" in header_list
        assert "LATENCY_MS" in header_list
        assert "BASE_URL" in header_list
        assert len(stats_list) == 2
        assert stats_list[0]["NAME"] == "prometheus"
        assert stats_list[0]["STATUS"] == "online"
        assert stats_list[0]["HEALTHY"] is True

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_proxy_health")
    def test_take_action_with_offline_and_disabled(
        self,
        mock_get_proxy_health,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_proxy_health.return_value = (200, "OK", "text", None)
        mock_check_results.return_value = {
            "targets": [
                _make_target(
                    "prometheus",
                    status="offline",
                    healthy=False,
                    latency_ms=None,
                    detail="connect error: connection refused",
                ),
                _make_target(
                    "alertmanager",
                    status="disabled",
                    enabled=False,
                    healthy=False,
                    latency_ms=None,
                    base_url="",
                    detail="base_url not configured",
                ),
            ],
        }
        mock_get_table_list_data.return_value = None
        GetProxyHealth(shell, None).take_action(mock_client)

        stats_list = mock_get_table_list_data.call_args[0][0]
        assert (
            mock_get_table_list_data.call_args.kwargs.get("is_dict") is False
        )
        # Offline row keeps the detail text
        assert stats_list[0]["STATUS"] == "offline"
        assert stats_list[0]["HEALTHY"] is False
        assert stats_list[0]["LATENCY_MS"] == "-"
        assert "connect error" in stats_list[0]["DETAIL"]
        # Disabled row shows empty base_url
        assert stats_list[1]["STATUS"] == "disabled"
        assert stats_list[1]["ENABLED"] is False
        assert stats_list[1]["BASE_URL"] == ""

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_proxy_health")
    def test_take_action_missing_targets_field(
        self, mock_get_proxy_health, mock_check_results
    ):
        """Malformed response (no 'targets' key) must raise."""
        mock_client = Mock(spec=Namespace)
        mock_get_proxy_health.return_value = (200, "OK", "text", None)
        mock_check_results.return_value = {"unexpected": "shape"}
        with pytest.raises(errors.GenericException) as exc_info:
            GetProxyHealth(shell, None).take_action(mock_client)
        assert "'targets' field is missing" in str(exc_info.value)
