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
    Ping,
    SystemInfo,
)
from wy_qcos_client.common.qcos_version import QcosVersion


DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
ping = Ping(shell, None)
system_info = SystemInfo(shell, None)


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
