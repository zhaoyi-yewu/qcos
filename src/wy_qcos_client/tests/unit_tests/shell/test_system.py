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

from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    DoGc,
    Ping,
    ShowMem,
    SystemInfo,
    TraceMem,
)
from wy_qcos_client.common.qcos_version import QcosVersion


DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
ping = Ping(shell, None)
system_info = SystemInfo(shell, None)
show_mem = ShowMem(shell, None)
do_gc = DoGc(shell, None)
trace_mem = TraceMem(shell, None)


class TestPing:
    def test_get_parser(self):
        parser = ping.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "ping")
    def test_take_action(self, mock_ping, mock_check_results):
        mock_client = Mock(spec=Namespace)
        mock_client.message = "msg"
        mock_ping.return_value = iter([None, None, None, None])
        mock_check_results.return_value = {"message": "msg"}

        assert ping.take_action(mock_client) is None


class TestSystemInfo:
    def test_get_parser(self):
        parser = system_info.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "system_info")
    def test_take_action(
        self, mock_system_info, mock_check_results, mock_get_table_data
    ):
        mock_system_info.return_value = iter([None, None, None, None])
        mock_check_results.return_value = None
        mock_get_table_data.return_value = None
        mock_client = Mock(spec=Namespace)
        table_values = system_info.take_action(mock_client)
        assert table_values is None


class TestShowMem:
    def test_get_parser(self):
        parser = show_mem.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "show_mem")
    def test_take_action(
        self, mock_show_mem, mock_check_results, mock_get_table_data
    ):
        mock_show_mem.return_value = iter([None, None, None, None])
        mock_check_results.return_value = None
        mock_get_table_data.return_value = None
        mock_client = Mock(spec=Namespace)
        table_values = show_mem.take_action(mock_client)
        assert table_values is None


class TestDoGc:
    def test_get_parser(self):
        parser = do_gc.get_parser("")
        assert parser is not None
        # verify --generations argument exists
        actions = {a.dest: a for a in parser._actions}
        assert "generations" in actions
        assert actions["generations"].default == 2
        assert actions["generations"].choices == [0, 1, 2]

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "debug_gc")
    def test_take_action(self, mock_debug_gc, mock_check_results):
        mock_debug_gc.return_value = iter([None, None, None, None])
        mock_check_results.return_value = {
            "collected": 10,
            "uncollectable": 0,
            "count_before": 100,
            "count_after": 90,
        }
        mock_client = Mock(spec=Namespace)
        mock_client.generations = 2
        # take_action prints output and returns None
        assert do_gc.take_action(mock_client) is None
        mock_debug_gc.assert_called_once_with(generations=2)


class TestTraceMem:
    def test_get_parser(self):
        parser = trace_mem.get_parser("")
        assert parser is not None
        # verify --action and --nframe arguments exist
        actions = {a.dest: a for a in parser._actions}
        assert "action" in actions
        assert actions["action"].default == "snapshot"
        assert actions["action"].choices == ["snapshot", "stop", "clear"]
        assert "nframe" in actions
        assert actions["nframe"].default == 25

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "debug_tracemalloc")
    def test_take_action_snapshot(
        self,
        mock_debug_tracemalloc,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_debug_tracemalloc.return_value = iter([None, None, None, None])
        mock_check_results.return_value = {
            "tracing": True,
            "traced_blocks": 5,
            "current": 2048,
            "peak": 4096,
            "top_stats": [
                {
                    "location": "/path/file.py:42",
                    "size": 1024,
                    "count": 5,
                }
            ],
        }
        mock_get_table_list_data.return_value = (
            ["location", "size", "count"],
            [],
        )
        mock_client = Mock(spec=Namespace)
        mock_client.action = "snapshot"
        mock_client.nframe = 25
        mock_client.sort_count = False
        result = trace_mem.take_action(mock_client)
        assert result is not None
        mock_debug_tracemalloc.assert_called_once_with(
            action="snapshot", nframe=25, sort_count=False
        )

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "debug_tracemalloc")
    def test_take_action_stop(
        self,
        mock_debug_tracemalloc,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_debug_tracemalloc.return_value = iter([None, None, None, None])
        mock_check_results.return_value = {
            "tracing": False,
            "traced_blocks": 0,
            "current": 0,
            "peak": 4096,
            "top_stats": [],
        }
        mock_get_table_list_data.return_value = (
            ["location", "size", "count"],
            [],
        )
        mock_client = Mock(spec=Namespace)
        mock_client.action = "stop"
        mock_client.nframe = 25
        mock_client.sort_count = False
        result = trace_mem.take_action(mock_client)
        assert result is not None
        mock_debug_tracemalloc.assert_called_once_with(
            action="stop", nframe=25, sort_count=False
        )
