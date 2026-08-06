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
    GcMem,
    ListWorkers,
    Ping,
    RestartWorker,
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
do_gc = GcMem(shell, None)
trace_mem = TraceMem(shell, None)
list_workers = ListWorkers(shell, None)
restart_worker = RestartWorker(shell, None)


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


class TestGcMem:
    def test_get_parser(self):
        parser = do_gc.get_parser("")
        assert parser is not None
        # verify --generations argument exists
        actions = {a.dest: a for a in parser._actions}
        assert "generations" in actions
        assert actions["generations"].default == 2
        assert actions["generations"].choices == [0, 1, 2]

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "gc_mem")
    def test_take_action(self, mock_gc_mem, mock_check_results):
        mock_gc_mem.return_value = iter([None, None, None, None])
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
        mock_gc_mem.assert_called_once_with(generations=2)


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
    @patch.object(Client, "trace_mem")
    def test_take_action_snapshot(
        self,
        mock_trace_mem,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_trace_mem.return_value = iter([None, None, None, None])
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
        mock_trace_mem.assert_called_once_with(
            action="snapshot", nframe=25, sort_count=False
        )

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "trace_mem")
    def test_take_action_stop(
        self,
        mock_trace_mem,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_trace_mem.return_value = iter([None, None, None, None])
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
        mock_trace_mem.assert_called_once_with(
            action="stop", nframe=25, sort_count=False
        )


class TestListWorkers:
    def test_get_parser(self):
        parser = list_workers.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "list_workers")
    def test_take_action(self, mock_list, mock_check, mock_table):
        mock_list.return_value = iter([None, None, None, None])
        mock_check.return_value = {
            "workers": [
                {
                    "worker_name": "process-device|dummy",
                    "work_pool": "device|dummy",
                    "worker_status": "ONLINE",
                    "pid": 123,
                }
            ]
        }
        mock_table.return_value = (
            ["worker_name", "work_pool", "worker_status", "pid"],
            [["process-device|dummy", "device|dummy", "ONLINE", 123]],
        )

        mock_client = Mock(spec=Namespace)
        result = list_workers.take_action(mock_client)
        assert result is not None
        mock_list.assert_called_once()


class TestRestartWorker:
    def test_get_parser(self):
        parser = restart_worker.get_parser("")
        assert parser is not None

    @patch("builtins.print")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "restart_worker")
    def test_take_action(self, mock_restart, mock_check, mock_print):
        mock_restart.return_value = iter([None, None, None, None])
        mock_check.return_value = {
            "success": True,
            "message": "restarted successfully",
            "worker_name": "process-device|dummy",
        }

        mock_client = Mock(spec=Namespace)
        mock_client.worker_name = "process-device|dummy"
        # take_action returns None for a Command
        assert restart_worker.take_action(mock_client) is None
        mock_restart.assert_called_once_with(
            worker_name="process-device|dummy"
        )
