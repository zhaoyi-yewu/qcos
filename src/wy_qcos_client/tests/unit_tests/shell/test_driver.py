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
    GetDrivers,
    GetDriver,
)
from wy_qcos_client.common.qcos_version import QcosVersion


DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
get_driver = GetDriver(shell, None)
get_drivers = GetDrivers(shell, None)


class TestGetDriver:
    def test_get_parser(self):
        parser = get_driver.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_driver")
    def test_take_action(
        self, mock_get_driver, mock_check_results, mock_get_table_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_client.driver_name = "driver"
        mock_get_driver.return_value = iter([None, None, None, None])
        mock_get_table_data.return_value = None
        mock_check_results.return_value = None
        table_values = get_driver.take_action(mock_client)
        assert table_values is None


class TestGetDrivers:
    def test_get_parser(self):
        parser = get_drivers.get_parser("")
        assert parser is not None

    @patch.object(Client, "get_drivers")
    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self, mock_check_results, mock_get_table_list_data, mock_get_drivers
    ):
        mock_get_drivers.return_value = -1, None, None, None
        mock_client = Mock(spec=Namespace)
        mock_get_table_list_data.return_value = None
        mock_check_results.return_value = None
        table_values = get_drivers.take_action(mock_client)
        assert table_values is None
