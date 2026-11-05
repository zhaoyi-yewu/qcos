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
from unittest.mock import MagicMock, patch, Mock

import pytest
from cliff.app import App
from cliff.commandmanager import CommandManager
from jsonrpcclient import Ok, Error

from wy_qcos_client.client import Client
from wy_qcos_client.shell import (
    CommandHelper,
    HelpAction,
    QcosShell,
    get_content_by_type,
    set_debug_option,
)
from wy_qcos_client.common import errors

import cliff.help as cliff_help
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
        """Default 600s used when neither cli nor env specified."""
        mock_initialize_app.return_value = None
        shell.options = self._setup_options(cli_timeout=None)
        with patch.dict("os.environ", {}, clear=True):
            shell.initialize_app([])
        kwargs = mock_client_cls.call_args.kwargs
        assert kwargs["timeout"] == 600
        assert kwargs["timeout_from_cli"] is False


class TestParseFilters:
    """Cover CommandHelper.parse_filters branches."""

    def test_none_input(self):
        assert CommandHelper.parse_filters(None) is None

    def test_empty_list(self):
        assert CommandHelper.parse_filters([]) is None

    def test_single_pair(self):
        assert CommandHelper.parse_filters(["name=x"]) == {"name": "x"}

    def test_strips_whitespace(self):
        assert CommandHelper.parse_filters([" name = x "]) == {"name": "x"}

    def test_multiple_keys(self):
        filters = CommandHelper.parse_filters(["a=1", "b=2"])
        assert filters == {"a": "1", "b": "2"}

    def test_repeated_key_collects_list(self):
        filters = CommandHelper.parse_filters(["a=1", "a=2"])
        assert filters == {"a": ["1", "2"]}

    def test_repeated_key_three_times(self):
        filters = CommandHelper.parse_filters(["a=1", "a=2", "a=3"])
        assert filters == {"a": ["1", "2", "3"]}

    def test_value_with_equals_sign(self):
        assert CommandHelper.parse_filters(["k=v=w"]) == {"k": "v=w"}

    def test_missing_equals_raises(self):
        with pytest.raises(errors.InvalidArguments, match="key=value"):
            CommandHelper.parse_filters(["noequals"])

    def test_empty_key_raises(self):
        with pytest.raises(errors.InvalidArguments, match="empty key"):
            CommandHelper.parse_filters(["=value"])


class TestDisableCliffSort:
    def test_disables_when_sort_present(self):
        parsed_args = Mock(sort="name", sort_columns=["a"], sort_direction=1)
        CommandHelper.disable_cliff_sort(parsed_args)
        assert parsed_args.sort_columns == []
        assert parsed_args.sort_direction is None

    def test_noop_when_sort_absent(self):
        parsed_args = Mock(sort=None, sort_columns=["a"], sort_direction=1)
        CommandHelper.disable_cliff_sort(parsed_args)
        assert parsed_args.sort_columns == ["a"]
        assert parsed_args.sort_direction == 1


class TestHandleInvalidArguments:
    def test_string_becomes_list(self):
        with pytest.raises(errors.InvalidArguments, match="oops"):
            CommandHelper.handle_invalid_arguments([False, "oops"])

    def test_list_message_joined(self):
        with pytest.raises(errors.InvalidArguments, match="a\nb"):
            CommandHelper.handle_invalid_arguments([False, ["a", "b"]])

    def test_success_no_raise(self):
        assert CommandHelper.handle_invalid_arguments([True, ""]) is None


class FakeOk:
    def __init__(self, result):
        self.result = result


class FakeErr:
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message
        self.data = data


class TestCheckResultsBranches:
    """Cover check_results result/error/exception branches."""

    def _text(self, obj):
        return json.dumps(obj)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_success_returns_result(self, mock_parse):
        mock_parse.return_value = (True, FakeOk({"a": 1}))
        ret = helper.check_results(
            "res",
            "op",
            HttpCode.SUCCESS_OK,
            "OK",
            self._text({"result": {"a": 1}}),
        )
        assert ret == {"a": 1}

    @patch.object(Client, "parse_jsonrpc_response")
    def test_error_with_validation_details(self, mock_parse):
        mock_parse.return_value = (
            False,
            FakeErr(
                -32602,
                "Invalid params",
                {
                    "errors": [{"msg": "bad", "loc": ["body", "name"]}],
                    "details": "detail text",
                },
            ),
        )
        with pytest.raises(errors.GenericException) as exc:
            helper.check_results(
                "res",
                "op",
                HttpCode.SUCCESS_OK,
                "OK",
                self._text({"error": {}}),
            )
        assert "bad" in str(exc.value)
        assert "detail text" in str(exc.value)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_error_without_data(self, mock_parse):
        mock_parse.return_value = (
            False,
            FakeErr(-32600, "Invalid Request"),
        )
        with pytest.raises(errors.GenericException, match="Invalid Request"):
            helper.check_results(
                "res",
                "op",
                HttpCode.SUCCESS_OK,
                "OK",
                self._text({"error": {}}),
            )

    def test_non_success_status(self):
        with pytest.raises(errors.GenericException, match="Server Error"):
            helper.check_results("res", "op", 500, "Server Error", "")

    @patch.object(Client, "parse_jsonrpc_response")
    def test_invalid_json_body(self, mock_parse):
        # shell.py converts the JSONDecodeError to str(e) before joining,
        # so a malformed JSON body surfaces as GenericException.
        with pytest.raises(errors.GenericException, match="Expecting"):
            helper.check_results(
                "res", "op", HttpCode.SUCCESS_OK, "OK", "not-json"
            )
        mock_parse.assert_not_called()


class TestGetTableListDataBranches:
    def test_dict_values(self):
        data = {"d1": {"name": "d1", "status": "online"}}
        headers, values = helper.get_table_list_data(
            data, ["name", "status"], is_dict=True
        )
        assert headers == ("NAME", "STATUS")
        assert values == (("d1", "online"),)

    def test_list_values(self):
        data = [{"name": "d1", "status": "online"}]
        headers, values = helper.get_table_list_data(data, ["name", "status"])
        assert headers == ("NAME", "STATUS")
        assert values == (("d1", "online"),)

    def test_none_value_becomes_empty(self):
        data = [{"name": "d1", "status": None}]
        _headers, values = helper.get_table_list_data(data, ["name", "status"])
        assert values == (("d1", ""),)

    def test_ignore_header_list(self):
        data = [{"name": "d1", "status": "x", "secret": "s"}]
        _headers, values = helper.get_table_list_data(
            data,
            ["name", "status", "secret"],
            ignore_header_list=["secret"],
        )
        assert values == (("d1", "x"),)

    def test_empty_dict_input(self):
        headers, values = helper.get_table_list_data(
            {}, ["name"], is_dict=True
        )
        assert headers == ()
        assert values == (())


class TestGetTableDataBranches:
    def test_drops_none(self):
        headers, values = helper.get_table_data({"a": 1, "b": None})
        assert headers == ("A",)
        assert values == (1,)

    def test_keep_none(self):
        headers, values = helper.get_table_data(
            {"a": 1, "b": None}, keep_value_none=True
        )
        assert headers == ("A", "B")
        assert values == (1, None)


class TestHelpAction:
    def _make_app(self):
        app = Mock()
        app.stdout = MagicMock()

        # One command entry per registered command group so that
        # grouped_cmds covers every group in QcosShell.CMD_GROUPS.
        # A factory avoids the late-binding closure pitfall: every
        # entry must return its own mock, not the last loop one.
        def _make_entry(group):
            cmd_mock = Mock(
                get_description=lambda: "desc line1\nline2",
                group=group,
            )
            entry = Mock()
            entry.load.return_value = lambda shell, cmd: cmd_mock
            return entry

        app.command_manager = [
            (f"cmd_{group}", _make_entry(group))
            for group in QcosShell.CMD_GROUPS
        ]
        return app

    def test_help_prints_groups_and_raises(self):
        app = self._make_app()
        parser = Mock()
        action = HelpAction(option_strings=[], dest="help", default=app)

        with pytest.raises(cliff_help.HelpExit):
            action(parser, None, None)
        written = "".join(str(c) for c in app.stdout.write.call_args_list)
        assert "Commands for API" in written
        # one_liner.capitalize() upper-cases the first character
        assert "Desc line1" in written
        assert "[AI]" in written
