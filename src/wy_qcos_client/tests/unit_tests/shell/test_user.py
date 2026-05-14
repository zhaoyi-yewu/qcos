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
from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client
from wy_qcos_client.shell import (
    QcosShell,
    CreateUser,
    UpdateUser,
    GetUser,
    GetUsers,
    DeleteUser,
    CreateRole,
    GetRole,
    UpdateRole,
    DeleteRole,
    GetRoles,
    ChangePassword,
    GetLoginLogs,
    ClearLoginLogs,
    GetUserMgmt,
    Login,
    Logout,
    RefreshToken,
    Whoami,
)
from wy_qcos_client.common import errors
from wy_qcos_client.common.client_library import _s
from wy_qcos_client.common.qcos_version import QcosVersion

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")

user_id = "00000000-0000-4000-8000-000000000001"
role_id = "10000000-0000-4000-8000-000000000001"

response = {
    "jsonrpc": "2.0",
    "result": {},
    "id": 0,
}
jsonrpc_response = json.dumps(response)

shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()


class TestGetUserMgmt:
    """Test cases for GetUserMgmt command."""

    def test_get_parser(self):
        cmd = GetUserMgmt(shell, None)
        parser = cmd.get_parser("get-user-mgmt")
        assert parser is not None

    @patch.object(Client, "get_user_mgmt_status")
    def test_take_action(self, mock_get_user_mgmt_status):
        """Test GetUserMgmt take_action method."""
        mock_get_user_mgmt_status.return_value = (
            200,
            "OK",
            jsonrpc_response,
            {"result": {"enabled": True}},
        )
        cmd = GetUserMgmt(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        result = cmd.take_action(parsed_args)
        assert result is not None


class TestCreateUser:
    """Test cases for CreateUser command."""

    def test_get_parser(self):
        cmd = CreateUser(shell, None)
        parser = cmd.get_parser("create-user")
        assert parser is not None

    @patch.object(Client, "create_user")
    def test_take_action_basic(self, mock_create_user):
        """Test CreateUser take_action with basic parameters."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"user_name": "testuser", "id": user_id},
            "id": 0,
        }
        mock_create_user.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = CreateUser(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_name = "testuser"
        parsed_args.password = _s("password123")
        parsed_args.role_names = None
        parsed_args.description = None
        parsed_args.password_expiry_days = None
        parsed_args.disable_action = False
        parsed_args.lock_action = False
        cmd.take_action(parsed_args)
        mock_create_user.assert_called_once()

    @patch.object(Client, "create_user")
    def test_take_action_with_roles(self, mock_create_user):
        """Test CreateUser with custom roles."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"user_name": "testuser", "id": user_id},
            "id": 0,
        }
        mock_create_user.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = CreateUser(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_name = "testuser"
        parsed_args.password = _s("password123")
        parsed_args.role_names = ["admin", "operator"]
        parsed_args.description = "Test user"
        parsed_args.password_expiry_days = 90
        parsed_args.disable_action = True
        parsed_args.lock_action = True
        cmd.take_action(parsed_args)
        # Check that create_user was called and roles were passed
        assert mock_create_user.called
        # create_user is called with positional args:
        call_args = mock_create_user.call_args[0]
        # roles is the 3rd positional argument (index 2)
        assert call_args[2] == ["admin", "operator"]


class TestUpdateUser:
    """Test cases for UpdateUser command."""

    def test_get_parser(self):
        cmd = UpdateUser(shell, None)
        parser = cmd.get_parser("update-user")
        assert parser is not None

    @patch.object(Client, "update_user")
    def test_take_action_basic(self, mock_update_user):
        """Test UpdateUser take_action with basic parameters."""
        mock_update_user.return_value = (200, "OK", jsonrpc_response, {})
        cmd = UpdateUser(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = user_id
        parsed_args.role_names = None
        parsed_args.description = None
        parsed_args.password_expiry_days = None
        parsed_args.enable_action = None
        parsed_args.disable_action = None
        parsed_args.lock_action = None
        parsed_args.unlock_action = None
        cmd.take_action(parsed_args)
        mock_update_user.assert_called_once()

    @patch.object(Client, "update_user")
    def test_take_action_with_enable(self, mock_update_user):
        """Test UpdateUser with enable action."""
        mock_update_user.return_value = (200, "OK", jsonrpc_response, {})
        cmd = UpdateUser(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = user_id
        parsed_args.role_names = ["admin"]
        parsed_args.description = "Updated user"
        parsed_args.password_expiry_days = 60
        parsed_args.enable_action = True
        parsed_args.disable_action = None
        parsed_args.lock_action = None
        parsed_args.unlock_action = None
        cmd.take_action(parsed_args)

    @patch.object(Client, "update_user")
    def test_take_action_with_lock(self, mock_update_user):
        """Test UpdateUser with lock action."""
        mock_update_user.return_value = (200, "OK", jsonrpc_response, {})
        cmd = UpdateUser(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = user_id
        parsed_args.role_names = None
        parsed_args.description = None
        parsed_args.password_expiry_days = None
        parsed_args.enable_action = None
        parsed_args.disable_action = None
        parsed_args.lock_action = True
        parsed_args.unlock_action = None
        cmd.take_action(parsed_args)


class TestGetUser:
    """Test cases for GetUser command."""

    def test_get_parser(self):
        cmd = GetUser(shell, None)
        parser = cmd.get_parser("get-user")
        assert parser is not None

    @patch.object(Client, "get_user")
    def test_take_action(self, mock_get_user):
        """Test GetUser take_action method."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "id": user_id,
                "user_name": "testuser",
                "roles": ["user"],
                "is_enabled": True,
                "is_locked": False,
                "password_expiry_days": 0,
                "description": "Test user",
            },
            "id": 0,
        }
        mock_get_user.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetUser(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.user_id = user_id
        result = cmd.take_action(parsed_args)
        assert result is not None


class TestGetUsers:
    """Test cases for GetUsers command."""

    def test_get_parser(self):
        cmd = GetUsers(shell, None)
        parser = cmd.get_parser("list-users")
        assert parser is not None

    @patch.object(Client, "get_users")
    def test_take_action(self, mock_get_users):
        """Test GetUsers take_action method."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "testuser": {
                    "id": user_id,
                    "user_name": "testuser",
                    "roles": ["user"],
                    "is_enabled": True,
                    "is_locked": False,
                    "password_expiry_days": 90,
                    "description": "Test user",
                }
            },
            "id": 0,
        }
        mock_get_users.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetUsers(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        result = cmd.take_action(parsed_args)
        assert result is not None

    @patch.object(Client, "get_users")
    def test_take_action_empty(self, mock_get_users):
        """Test GetUsers with no users."""
        # Return a successful response with empty result
        mock_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": 0,
        }
        mock_get_users.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetUsers(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        result = cmd.take_action(parsed_args)
        assert result is not None


class TestDeleteUser:
    """Test cases for DeleteUser command."""

    def test_get_parser(self):
        cmd = DeleteUser(shell, None)
        parser = cmd.get_parser("delete-user")
        assert parser is not None

    @patch.object(Client, "delete_user")
    def test_take_action(self, mock_delete_user):
        """Test DeleteUser take_action method."""
        mock_delete_user.return_value = (200, "OK", jsonrpc_response, {})
        cmd = DeleteUser(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.user_id = user_id
        parsed_args.force = False
        cmd.take_action(parsed_args)
        mock_delete_user.assert_called_once_with(user_id, force=False)


class TestCreateRole:
    """Test cases for CreateRole command."""

    def test_get_parser(self):
        cmd = CreateRole(shell, None)
        parser = cmd.get_parser("create-role")
        assert parser is not None

    @patch.object(Client, "create_role")
    def test_take_action(self, mock_create_role):
        """Test CreateRole take_action method."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"role_name": "test_role", "id": role_id},
            "id": 0,
        }
        mock_create_role.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = CreateRole(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.role_name = "test_role"
        parsed_args.permissions = json.dumps(["read", "write"])
        parsed_args.description = "Test role"
        cmd.take_action(parsed_args)
        mock_create_role.assert_called_once()

    def test_take_action_invalid_json(self):
        """Test CreateRole with invalid JSON permissions."""
        cmd = CreateRole(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.role_name = "test_role"
        parsed_args.permissions = "invalid json"
        parsed_args.description = None
        with pytest.raises(errors.InvalidArguments):
            cmd.take_action(parsed_args)


class TestGetRole:
    """Test cases for GetRole command."""

    def test_get_parser(self):
        cmd = GetRole(shell, None)
        parser = cmd.get_parser("get-role")
        assert parser is not None

    @patch.object(Client, "get_role")
    def test_take_action(self, mock_get_role):
        """Test GetRole take_action method."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "id": role_id,
                "role_name": "test_role",
                "permissions": ["read", "write"],
                "description": "Test role",
            },
            "id": 0,
        }
        mock_get_role.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetRole(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.role_id = role_id
        result = cmd.take_action(parsed_args)
        assert result is not None


class TestUpdateRole:
    """Test cases for UpdateRole command."""

    def test_get_parser(self):
        cmd = UpdateRole(shell, None)
        parser = cmd.get_parser("update-role")
        assert parser is not None

    @patch.object(Client, "update_role")
    def test_take_action(self, mock_update_role):
        """Test UpdateRole take_action method."""
        mock_update_role.return_value = (200, "OK", jsonrpc_response, {})
        cmd = UpdateRole(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.role_id = role_id
        parsed_args.permissions = json.dumps(["read", "write", "delete"])
        parsed_args.description = "Updated role"
        cmd.take_action(parsed_args)
        mock_update_role.assert_called_once()

    @patch.object(Client, "update_role")
    def test_take_action_without_permissions(self, mock_update_role):
        """Test UpdateRole without permissions parameter."""
        mock_update_role.return_value = (200, "OK", jsonrpc_response, {})
        cmd = UpdateRole(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.role_id = role_id
        parsed_args.permissions = None
        parsed_args.description = "Updated description only"
        cmd.take_action(parsed_args)

    def test_take_action_invalid_json(self):
        """Test UpdateRole with invalid JSON permissions."""
        cmd = UpdateRole(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.role_id = role_id
        parsed_args.permissions = "invalid json"
        parsed_args.description = None
        with pytest.raises(errors.InvalidArguments):
            cmd.take_action(parsed_args)


class TestDeleteRole:
    """Test cases for DeleteRole command."""

    def test_get_parser(self):
        cmd = DeleteRole(shell, None)
        parser = cmd.get_parser("delete-role")
        assert parser is not None

    @patch.object(Client, "delete_role")
    def test_take_action(self, mock_delete_role):
        """Test DeleteRole take_action method."""
        mock_delete_role.return_value = (200, "OK", jsonrpc_response, {})
        cmd = DeleteRole(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.role_id = role_id
        cmd.take_action(parsed_args)
        mock_delete_role.assert_called_once_with(role_id)


class TestGetRoles:
    """Test cases for GetRoles command."""

    def test_get_parser(self):
        cmd = GetRoles(shell, None)
        parser = cmd.get_parser("list-roles")
        assert parser is not None

    @patch.object(Client, "get_roles")
    def test_take_action(self, mock_get_roles):
        """Test GetRoles take_action method.

        Note: GetRoles expects a dict format (like {"role1": {...}}) not list,
        because it uses is_dict=True in get_table_list_data.
        """
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "test_role": {
                    "id": role_id,
                    "role_name": "test_role",
                    "permissions": ["read", "write"],
                    "description": "Test role",
                }
            },
            "id": 0,
        }
        mock_get_roles.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetRoles(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        result = cmd.take_action(parsed_args)
        assert result is not None

    @patch.object(Client, "get_roles")
    def test_take_action_empty(self, mock_get_roles):
        """Test GetRoles with no roles."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": 0,
        }
        mock_get_roles.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetRoles(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        result = cmd.take_action(parsed_args)
        assert result is not None


class TestChangePassword:
    """Test cases for ChangePassword command."""

    def test_get_parser(self):
        cmd = ChangePassword(shell, None)
        parser = cmd.get_parser("change-password")
        assert parser is not None

    @patch.object(Client, "change_password")
    def test_take_action(self, mock_change_password):
        """Test ChangePassword take_action method."""
        mock_change_password.return_value = (200, "OK", jsonrpc_response, {})
        cmd = ChangePassword(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        parsed_args.user_id = user_id
        parsed_args.old_password = _s("oldpass123")
        parsed_args.new_password = _s("newpass456")
        cmd.take_action(parsed_args)
        mock_change_password.assert_called_once_with(
            user_id, "oldpass123", "newpass456"
        )


class TestGetLoginLogs:
    """Test cases for GetLoginLogs command."""

    def test_get_parser(self):
        cmd = GetLoginLogs(shell, None)
        parser = cmd.get_parser("list-login-logs")
        assert parser is not None

    @patch.object(Client, "get_login_logs")
    def test_take_action_with_user_id(self, mock_get_login_logs):
        """Test GetLoginLogs with user_id."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": [
                {
                    "user_name": "testuser",
                    "login_time": "2024-01-01T10:00:00",
                    "ip_address": "192.168.1.1",
                    "success": True,
                    "failure_reason": None,
                }
            ],
            "id": 0,
        }
        mock_get_login_logs.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetLoginLogs(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = user_id
        parsed_args.user_name = None
        parsed_args.limit = 100
        parsed_args.offset = 0
        result = cmd.take_action(parsed_args)
        assert result is not None

    @patch.object(Client, "get_login_logs")
    def test_take_action_without_user_id(self, mock_get_login_logs):
        """Test GetLoginLogs without user_id."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {},
            "id": 0,
        }
        mock_get_login_logs.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = GetLoginLogs(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = None
        parsed_args.limit = 50
        parsed_args.offset = 10
        result = cmd.take_action(parsed_args)
        assert result is not None


class TestClearLoginLogs:
    """Test cases for ClearLoginLogs command."""

    def test_get_parser(self):
        cmd = ClearLoginLogs(shell, None)
        parser = cmd.get_parser("clear-login-logs")
        assert parser is not None

    @patch.object(Client, "clear_login_logs")
    @patch("builtins.input", return_value="y")
    def test_take_action_all_logs_with_confirmation(
        self, mock_input, mock_clear_login_logs
    ):
        """Test ClearLoginLogs clearing all logs with user confirmation."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"count": 42},
            "id": 0,
        }
        mock_clear_login_logs.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = ClearLoginLogs(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = None
        parsed_args.user_name = None
        parsed_args.force = False
        result = cmd.take_action(parsed_args)
        assert result is not None
        mock_clear_login_logs.assert_called_once_with()

    @patch.object(Client, "clear_login_logs")
    def test_take_action_with_user_id_force(self, mock_clear_login_logs):
        """Test ClearLoginLogs with user_id and force flag."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"count": 5},
            "id": 0,
        }
        mock_clear_login_logs.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = ClearLoginLogs(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = user_id
        parsed_args.user_name = None
        parsed_args.force = True
        result = cmd.take_action(parsed_args)
        assert result is not None
        mock_clear_login_logs.assert_called_once_with(user_id=user_id)

    @patch.object(Client, "clear_login_logs")
    def test_take_action_with_user_name_force(self, mock_clear_login_logs):
        """Test ClearLoginLogs with user_name and force flag."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"count": 10},
            "id": 0,
        }
        mock_clear_login_logs.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        cmd = ClearLoginLogs(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = None
        parsed_args.user_name = "admin"
        parsed_args.force = True
        result = cmd.take_action(parsed_args)
        assert result is not None
        mock_clear_login_logs.assert_called_once_with(user_name="admin")

    @patch.object(Client, "clear_login_logs")
    @patch("builtins.input", return_value="n")
    def test_take_action_user_cancel(self, mock_input, mock_clear_login_logs):
        """Test ClearLoginLogs when user cancels operation."""
        cmd = ClearLoginLogs(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.user_id = None
        parsed_args.user_name = None
        parsed_args.force = False
        cmd.take_action(parsed_args)
        # Should return None when user cancels
        mock_clear_login_logs.assert_not_called()


class TestLogin:
    """Test cases for Login command."""

    def test_get_parser(self):
        cmd = Login(shell, None)
        parser = cmd.get_parser("login")
        assert parser is not None

    @patch.object(Client, "login")
    def test_take_action(self, mock_login):
        """Test Login take_action method."""
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
        mock_login.assert_called_once_with("admin", "admin123")

    @patch.object(Client, "login")
    def test_take_action_token_only(self, mock_login):
        """Test Login with token_only flag."""
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
        parsed_args.token_only = True
        parsed_args.access_token = False
        parsed_args.refresh_token = False
        cmd.take_action(parsed_args)

    @patch.object(Client, "login")
    def test_take_action_no_token(self, mock_login):
        """Test Login when no access_token in response."""
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
        parsed_args = Mock()
        parsed_args.username = "admin"
        parsed_args.password = _s("wrongpassword")
        parsed_args.token_only = False
        with pytest.raises(Exception):
            cmd.take_action(parsed_args)


class TestLogout:
    """Test cases for Logout command."""

    def test_get_parser(self):
        cmd = Logout(shell, None)
        parser = cmd.get_parser("logout")
        assert parser is not None

    @patch.object(Client, "logout")
    def test_take_action(self, mock_logout):
        """Test Logout take_action method."""
        mock_logout.return_value = (200, "OK", jsonrpc_response, {})
        cmd = Logout(shell, None)
        cmd.app = shell
        parsed_args = Mock()
        cmd.take_action(parsed_args)
        mock_logout.assert_called_once()


class TestRefreshToken:
    """Test cases for RefreshToken command."""

    def test_get_parser(self):
        cmd = RefreshToken(shell, None)
        parser = cmd.get_parser("refresh-token")
        assert parser is not None

    @patch.object(Client, "call_json_rpc")
    def test_take_action(self, mock_call_json_rpc):
        """Test RefreshToken take_action method."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "access_token": "newtoken456",
                "refresh_token": "refresh789",
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
    def test_take_action_token_only(self, mock_call_json_rpc):
        """Test RefreshToken with token_only flag."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "access_token": "newtoken456",
                "refresh_token": "refresh789",
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
        parsed_args.token_only = True
        parsed_args.refresh_token = _s("refresh123")
        cmd.take_action(parsed_args)


class TestWhoami:
    """Test cases for Whoami command."""

    def test_get_parser(self):
        cmd = Whoami(shell, None)
        parser = cmd.get_parser("whoami")
        assert parser is not None

    @patch.object(Client, "get_me")
    def test_take_action(self, mock_get_me):
        """Test Whoami take_action method."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "user_id": user_id,
                "username": "admin",
                "roles": ["admin"],
            },
            "id": 0,
        }
        mock_get_me.return_value = (
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


class TestSetUserMgmt:
    """Test cases for SetUserMgmt command."""

    def test_get_parser(self):
        from wy_qcos_client.shell import SetUserMgmt
        cmd = SetUserMgmt(shell, None)
        parser = cmd.get_parser("set-user-mgmt")
        assert parser is not None

    @patch.object(Client, "set_user_mgmt")
    def test_take_action_auth_mode_jwt(self, mock_set_user_mgmt):
        """Test SetUserMgmt with JWT auth mode."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"auth_mode": "jwt", "message": "Auth mode updated"},
            "id": 0,
        }
        mock_set_user_mgmt.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        from wy_qcos_client.shell import SetUserMgmt
        cmd = SetUserMgmt(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.auth_mode = "jwt"
        cmd.take_action(parsed_args)
        mock_set_user_mgmt.assert_called_once_with("jwt")

    @patch.object(Client, "set_user_mgmt")
    def test_take_action_auth_mode_virtual_instance(self, mock_set_user_mgmt):
        """Test SetUserMgmt with virtual_instance auth mode."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"auth_mode": "virtual_instance", "message": "Auth mode updated"},
            "id": 0,
        }
        mock_set_user_mgmt.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        from wy_qcos_client.shell import SetUserMgmt
        cmd = SetUserMgmt(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.auth_mode = "virtual_instance"
        cmd.take_action(parsed_args)
        mock_set_user_mgmt.assert_called_once_with("virtual_instance")

    @patch.object(Client, "set_user_mgmt")
    def test_take_action_auth_mode_no(self, mock_set_user_mgmt):
        """Test SetUserMgmt with no auth mode."""
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"auth_mode": "no", "message": "Auth mode updated"},
            "id": 0,
        }
        mock_set_user_mgmt.return_value = (
            200,
            "OK",
            json.dumps(mock_response),
            mock_response["result"],
        )
        from wy_qcos_client.shell import SetUserMgmt
        cmd = SetUserMgmt(shell, None)
        cmd.app = shell
        cmd.app.stdout = Mock()
        parsed_args = Mock()
        parsed_args.auth_mode = "no"
        cmd.take_action(parsed_args)
        mock_set_user_mgmt.assert_called_once_with("no")
