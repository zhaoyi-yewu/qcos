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
    Version,
)
from wy_qcos_client.common.qcos_version import QcosVersion

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
version = Version(shell, None)


class TestVersion:
    def test_get_parser(self):
        parser = version.get_parser("")
        assert parser is not None

    @patch.object(Client, "version")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(self, mock_check_results, mock_version):
        mock_client = Mock(spec=Namespace)
        mock_client.details = False
        mock_version.return_value = -1, None, None, None
        mock_check_results.return_value = {
            "capabilities": {
                "job_types": ["sample"],
                "profiling": 1,
                "tech_types": "ion_trap",
                "drivers": "DriverUQCMatrix2",
                "transpilers": {"cmss": "cmss"},
                "driver_transpiler_mappings": None,
            },
            "version": "0.0.1",
            "api_version": "0.1.0",
            "supported_api_versions": "0.1.0",
            "platform_version": "1.0.0",
            "auth_mode": "no",
        }
        assert version.take_action(mock_client) is None
