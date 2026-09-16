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
        "created_at": "2025-11-25T16:02:33.182619",
        "started_at": None,
        "ended_at": None,
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
        # verify --timeout option exists with default None
        actions = {a.dest: a for a in parser._actions}
        assert "timeout" in actions
        assert actions["timeout"].default is None
        assert actions["timeout"].type is int

    @patch.object(App, "initialize_app")
    def test_initialize_app(self, mock_initialize_app):
        mock_initialize_app.return_value = None
        mock_options = Mock()
        shell.options = mock_options
        mock_options.api_host = "127.0.0.1"
        mock_options.use_ssl = False
        mock_options.timeout = None
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


class TestTimeoutPrecedence:
    """Test timeout resolution precedence in initialize_app."""

    def _setup_options(self, cli_timeout=None):
        """Build a mock options namespace for initialize_app."""
        mock_options = Mock()
        mock_options.api_host = "127.0.0.1"
        mock_options.api_port = 8000
        mock_options.use_ssl = False
        mock_options.ssl_certfile = None
        mock_options.ssl_keyfile = None
        mock_options.ssl_cafile = None
        mock_options.timeout = cli_timeout
        return mock_options

    @patch.object(App, "initialize_app")
    @patch("wy_qcos_client.shell.Client")
    def test_cli_timeout_overrides_env(
        self, mock_client_cls, mock_initialize_app
    ):
        """Command line --timeout takes precedence over env var."""
        mock_initialize_app.return_value = None
        shell.options = self._setup_options(cli_timeout=120)
        with patch.dict("os.environ", {"QCOS_CLIENT_TIMEOUT": "30"}):
            shell.initialize_app([])
        mock_client_cls.assert_called_once()
        kwargs = mock_client_cls.call_args.kwargs
        assert kwargs["timeout"] == 120
        assert kwargs["timeout_from_cli"] is True

    @patch.object(App, "initialize_app")
    @patch("wy_qcos_client.shell.Client")
    def test_env_timeout_when_no_cli(
        self, mock_client_cls, mock_initialize_app
    ):
        """Env var used when command line timeout not specified."""
        mock_initialize_app.return_value = None
        shell.options = self._setup_options(cli_timeout=None)
        with patch.dict("os.environ", {"QCOS_CLIENT_TIMEOUT": "45"}):
            shell.initialize_app([])
        kwargs = mock_client_cls.call_args.kwargs
        assert kwargs["timeout"] == 45
        assert kwargs["timeout_from_cli"] is False

    @patch.object(App, "initialize_app")
    @patch("wy_qcos_client.shell.Client")
    def test_default_timeout_when_no_cli_no_env(
        self, mock_client_cls, mock_initialize_app
    ):
        """Default 60s used when neither cli nor env specified."""
        mock_initialize_app.return_value = None
        shell.options = self._setup_options(cli_timeout=None)
        with patch.dict("os.environ", {}, clear=True):
            shell.initialize_app([])
        kwargs = mock_client_cls.call_args.kwargs
        assert kwargs["timeout"] == 60
        assert kwargs["timeout_from_cli"] is False
