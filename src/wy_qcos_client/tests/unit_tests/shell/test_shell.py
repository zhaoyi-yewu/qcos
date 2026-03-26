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

import json
from unittest.mock import patch, Mock

import pytest
from cliff.app import App
from cliff.commandmanager import CommandManager
from jsonrpcclient import Ok, Error

from wy_qcos_client.client import Client
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    set_debug_option,
    get_content_by_type,
)
from wy_qcos_client.common import errors
from wy_qcos_client.common.qcos_version import QcosVersion
from wy_qcos_client.common.constant import HttpCode, Constant
from wy_qcos_client.tests.unit_tests.constant_for_test import ConstantForTest

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
job_id = ConstantForTest.job_id
response = {
    "jsonrpc": "2.0",
    "result": {
        "job_id": job_id,
        "job_name": None,
        "job_status": "QUEUED",
        "job_priority": 5,
        "description": None,
        "backend": "uqc_matrix2",
        "driver_options": None,
        "transpiler": None,
        "transpiler_options": None,
        "circuit_aggregation": None,
        "shots": 100,
        "dry_run": False,
        "progress": -1,
        "creation_date": "2025-11-25T16:02:33.182619",
        "end_date": None,
    },
    "id": 0,
}
header_list = [
    "name",
    "alias_name",
    "version",
    "tech_type",
    "max_qubits",
    "transpiler",
    "description",
]
jsonrpc_response = json.dumps(response)


shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
helper = CommandHelper()


class TestQcosShell:
    def test_build_option_parser(self):
        parser = shell.build_option_parser(DESCRIPTION, VERSION)
        assert parser.description == DESCRIPTION

    @patch.object(App, "initialize_app")
    def test_initialize_app(self, mock_initialize_app):
        mock_initialize_app.return_value = None
        mock_options = Mock()
        shell.options = mock_options
        mock_options.api_host = "127.0.0.1"
        mock_options.use_ssl = False
        assert shell.initialize_app([]) is None


class TestCommandHelper:
    def test_handle_invalid_arguments(self):
        with pytest.raises(errors.InvalidArguments) as e:
            helper.handle_invalid_arguments([False, "Invalid backend"])
        assert "Invalid backend" in str(e)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_check_results(self, mock_parse_jsonrpc_response):
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok("result", "id"),
        ])
        helper.check_results(
            QcosShell.CMD_GROUP_VERSION,
            "version",
            HttpCode.SUCCESS_OK,
            "OK",
            jsonrpc_response,
        )

        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                404,
                "message",
                {
                    "errors": [
                        {"msg": "Not Found", "loc": ["loc1"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])
        with pytest.raises(errors.GenericException) as e:
            helper.check_results(
                QcosShell.CMD_GROUP_VERSION,
                "version",
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
            )
        assert "404" in str(e)

    def test_get_table_list_data(self):
        result = helper.get_table_list_data(
            [
                {"key": "value"},
            ],
            header_list,
        )
        assert result is not None

    def test_get_table_data(self):
        result = helper.get_table_data({
            "key": "value",
        })
        assert result is not None

    def test_get_content_by_type(self):
        get_content_by_type(Constant.CODE_TYPE_QASM, "\\qcos")
        success, _, _ = get_content_by_type(Constant.CODE_TYPE_QASM, "\\qcos")
        assert success is False

    @patch("argparse.ArgumentParser.parse_known_args")
    def test_set_debug_option(self, mock_parse_known_args):
        mock_client = Mock()
        mock_client.debug = True
        mock_parse_known_args.return_value = (mock_client, None)
        assert set_debug_option("args") is None


def test_set_debug_option():
    assert set_debug_option(None) is None


def test_get_content_by_type():
    success, _, _ = get_content_by_type("qasm", "")
    assert success is False
