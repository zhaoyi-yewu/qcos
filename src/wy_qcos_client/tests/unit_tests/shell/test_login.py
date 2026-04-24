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

from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client
from wy_qcos_client.shell import (
    QcosShell,
    Login,
    Logout,
    RefreshToken,
    Whoami,
)
from wy_qcos_client.common.client_library import _s
from wy_qcos_client.common.qcos_version import QcosVersion

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()


class TestShellAuth:
    """Test cases for authentication commands in Shell."""

    @patch.object(Client, "login")
    def test_login_command_success(self, mock_login):
        """Test successful login command."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "access_token": "token123",
                "refresh_token": "refresh123",
                "expires_in": 3600,
                "refresh_expires_in": 7200,
            },
            "id": 0,
        }
        mock_login.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Login(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.username = "admin"
        parsed_args.password = _s("admin123")
        parsed_args.token_only = False
        parsed_args.access_token = False
        parsed_args.refresh_token = False
        cmd.take_action(parsed_args)
        mock_login.assert_called_once()

    @patch.object(Client, "login")
    def test_login_command_invalid_credentials(self, mock_login):
        """Test login with invalid credentials."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"error": "Invalid credentials"},
            "id": 0,
        }
        mock_login.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Login(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.username = "admin"
        parsed_args.password = _s("wrongpass")
        parsed_args.token_only = False
        try:
            cmd.take_action(parsed_args)
        except Exception as e:
            print(f"Expected test exception: {type(e).__name__}: {e}")
        mock_login.assert_called_once()

    @patch.object(Client, "logout")
    def test_logout_command_success(self, mock_logout):
        """Test successful logout command."""
        response = {"jsonrpc": "2.0", "result": {}, "id": 0}
        mock_logout.return_value = (
            200,
            "OK",
            json.dumps(response),
            response["result"],
        )
        cmd = Logout(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        cmd.take_action(parsed_args)
        mock_logout.assert_called_once()

    @patch.object(Client, "logout")
    def test_logout_command_without_token(self, mock_logout):
        """Test logout without a token."""
        response = {"jsonrpc": "2.0", "result": {}, "id": 0}
        mock_logout.return_value = (
            401,
            "Unauthorized",
            json.dumps(response),
            response["result"],
        )
        cmd = Logout(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        try:
            cmd.take_action(parsed_args)
        except Exception as e:
            print(f"Expected test exception: {type(e).__name__}: {e}")
        mock_logout.assert_called_once()

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_command_success(self, mock_call_json_rpc):
        """Test successful refresh token command."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "access_token": "new_token",
                "refresh_token": "refresh456",
                "expires_in": 3600,
                "refresh_expires_in": 7200,
            },
            "id": 0,
        }
        mock_call_json_rpc.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        shell.client.auth_url = "http://localhost:18400/v1/auth"
        cmd = RefreshToken(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.token_only = False
        parsed_args.refresh_token = _s("refresh123")
        cmd.take_action(parsed_args)
        mock_call_json_rpc.assert_called_once()

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_command_expired(self, mock_call_json_rpc):
        """Test refresh token with expired refresh token."""
        mock_response = {"jsonrpc": "2.0", "result": {}, "id": 0}
        mock_call_json_rpc.return_value = (
            401,
            "Unauthorized",
            json.dumps(mock_response),
            mock_response["result"],
        )
        shell.client.auth_url = "http://localhost:18400/v1/auth"
        cmd = RefreshToken(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.token_only = False
        parsed_args.refresh_token = _s("invalid_token")
        try:
            cmd.take_action(parsed_args)
        except Exception:
            print("Expected exception during test")
        mock_call_json_rpc.assert_called_once()

    @patch.object(Client, "get_current_user")
    def test_get_current_user_command_success(self, mock_get_user):
        """Test successful get current user command."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "id": "user123",
                "user_name": "admin",
                "roles": ["admin"],
            },
            "id": 0,
        }
        mock_get_user.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Whoami(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        result = cmd.take_action(parsed_args)
        assert result is not None
        mock_get_user.assert_called_once()

    @patch.object(Client, "get_current_user")
    def test_get_current_user_command_unauthorized(self, mock_get_user):
        """Test get current user when not authenticated."""
        mock_response = {"jsonrpc": "2.0", "result": {}, "id": 0}
        mock_get_user.return_value = (
            401,
            "Unauthorized",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Whoami(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        try:
            cmd.take_action(parsed_args)
        except Exception:
            print("Expected exception during test")
        mock_get_user.assert_called_once()

    @patch.object(Client, "login")
    def test_login_locked_account(self, mock_login):
        """Test login with locked account."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": 0,
        }
        mock_login.return_value = (
            403,
            "Forbidden",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Login(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.username = "testuser"
        parsed_args.password = _s("pass123")
        parsed_args.token_only = False
        try:
            cmd.take_action(parsed_args)
        except Exception:
            print("Expected exception during test")
        mock_login.assert_called_once()

    @patch.object(Client, "login")
    def test_login_disabled_account(self, mock_login):
        """Test login with disabled account."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": 0,
        }
        mock_login.return_value = (
            403,
            "Forbidden",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Login(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.username = "disableduser"
        parsed_args.password = _s("pass123")
        parsed_args.token_only = False
        try:
            cmd.take_action(parsed_args)
        except Exception:
            print("Expected exception during test")
        mock_login.assert_called_once()

    @patch.object(Client, "login")
    def test_login_password_expired(self, mock_login):
        """Test login with expired password."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": 0,
        }
        mock_login.return_value = (
            403,
            "Forbidden",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Login(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.username = "testuser"
        parsed_args.password = _s("pass123")
        parsed_args.token_only = False
        try:
            cmd.take_action(parsed_args)
        except Exception:
            print("Expected exception during test")
        mock_login.assert_called_once()

    @patch.object(Client, "login")
    def test_login_max_attempts_exceeded(self, mock_login):
        """Test login after max attempts exceeded."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": 0,
        }
        mock_login.return_value = (
            403,
            "Forbidden",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = Login(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.username = "testuser"
        parsed_args.password = _s("pass123")
        parsed_args.token_only = False
        try:
            cmd.take_action(parsed_args)
        except Exception:
            print("Expected exception during test")
        mock_login.assert_called_once()
