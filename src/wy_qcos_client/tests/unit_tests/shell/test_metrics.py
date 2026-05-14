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

from argparse import Namespace
from unittest.mock import patch, Mock

import pytest
from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    GetSystemHealth,
    GetApiStats,
    GetJobStats,
)
from wy_qcos_client.common.qcos_version import QcosVersion

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()


class TestGetSystemHealth:
    def test_get_parser(self):
        get_system_health = GetSystemHealth(shell, None)
        parser = get_system_health.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_system_health")
    def test_take_action(
        self,
        mock_get_system_health,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_system_health.return_value = (200, "OK", "text", None)
        mock_check_results.return_value = {
            "system_healthy": True,
            "heartbeat_timestamp": 1234567890.0,
            "component_status": {"fastapi": "online", "redis": "online"},
        }
        mock_get_table_list_data.return_value = None
        table_values = GetSystemHealth(shell, None).take_action(mock_client)
        assert table_values is None

    @patch.object(CommandHelper, "check_results")
    def test_take_action_invalid_response(self, mock_check_results):
        mock_client = Mock(spec=Namespace)
        mock_check_results.return_value = {
            "system_healthy": True,
            "heartbeat_timestamp": 1234567890.0,
        }
        from wy_qcos_client.common import errors

        with pytest.raises(errors.GenericException) as exc_info:
            GetSystemHealth(shell, None).take_action(mock_client)
        assert "'component_status' field is missing" in str(exc_info.value)


class TestGetApiStats:
    def test_get_parser(self):
        get_api_stats = GetApiStats(shell, None)
        parser = get_api_stats.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_api_stats")
    def test_take_action(
        self, mock_get_api_stats, mock_check_results, mock_get_table_list_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_api_stats.return_value = (200, "OK", "text", None)
        mock_check_results.return_value = {
            "total_requests": 1000,
            "last_hour_requests": 50,
            "last_day_requests": 500,
        }
        mock_get_table_list_data.return_value = None
        table_values = GetApiStats(shell, None).take_action(mock_client)
        assert table_values is None


class TestGetJobStats:
    def test_get_parser(self):
        get_job_stats = GetJobStats(shell, None)
        parser = get_job_stats.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_job_stats")
    def test_take_action(
        self, mock_get_job_stats, mock_check_results, mock_get_table_list_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_job_stats.return_value = (200, "OK", "text", None)
        mock_check_results.return_value = {
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
        mock_get_table_list_data.return_value = None
        table_values = GetJobStats(shell, None).take_action(mock_client)
        assert table_values is None
