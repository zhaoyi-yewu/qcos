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
    GetTranspilers,
    GetTranspiler,
)
from wy_qcos_client.common.qcos_version import QcosVersion

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
get_transpiler = GetTranspiler(shell, None)
get_transpilers = GetTranspilers(shell, None)


class TestGetTranspilers:
    def test_get_parser(self):
        parser = get_transpilers.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_transpilers")
    def test_take_action(
        self,
        mock_get_transpilers,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_transpilers.return_value = iter([None, None, None, None])
        mock_get_table_list_data.return_value = None
        mock_check_results.return_value = None
        table_values = get_transpilers.take_action(mock_client)
        assert table_values is None


class TestGetTranspiler:
    def test_get_parser(self):
        parser = get_transpiler.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_transpiler")
    def test_take_action(
        self, mock_get_transpiler, mock_check_results, mock_get_table_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_client.transpiler_name = "transpiler"
        mock_get_transpiler.return_value = iter([None, None, None, None])
        mock_get_table_data.return_value = None
        mock_check_results.return_value = None
        table_values = get_transpiler.take_action(mock_client)
        assert table_values is None
