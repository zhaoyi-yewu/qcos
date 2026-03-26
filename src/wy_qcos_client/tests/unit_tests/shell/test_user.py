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
from jsonrpcclient import Ok, Error

from wy_qcos_client.client import Client
from wy_qcos_client.common import errors
from wy_qcos_client.common.client_library import _s
from wy_qcos_client.common.constant import HttpCode
from wy_qcos_client.common.qcos_version import QcosVersion
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    command_manager,
)


DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
user_name = "test_user"
response = {
    "jsonrpc": "2.0",
    "result": {
        "user_name": user_name,
        "roles": ["user"],
        "is_enabled": True,
        "is_locked": False,
        "description": "Test user",
        "password_expiry_days": 30,
        "last_login": "2025-01-01T10:00:00",
    },
    "id": 0,
}
header_list = [
    "user_name",
    "roles",
    "is_enabled",
    "is_locked",
    "password_expiry_days",
    "last_login",
    "description",
]
jsonrpc_response = json.dumps(response)


shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
helper = CommandHelper()


class TestGetUserManagementStatus:
    """Test GetUserManagementStatus command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command([
            "get-user-management-status"
        ])[0](shell, None)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_user_management_status_success(
        self, mock_parse_jsonrpc_response
    ):
        """Test get_user_management_status with success."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"enabled": True}, "id"),
        ])

        with patch.object(
            shell.client, "get_user_management_status"
        ) as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_user_management_status_disabled(
        self, mock_parse_jsonrpc_response
    ):
        """Test get_user_management_status with disabled user management."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"enabled": False}, "id"),
        ])

        with patch.object(
            shell.client, "get_user_management_status"
        ) as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_user_management_status_with_details(
        self, mock_parse_jsonrpc_response
    ):
        """Test get_user_management_status with additional details."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"enabled": True, "max_users": 100, "current_users": 15}, "id"),
        ])

        with patch.object(
            shell.client, "get_user_management_status"
        ) as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_user_management_status_error(
        self, mock_parse_jsonrpc_response
    ):
        """Test get_user_management_status with error."""
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

        with patch.object(
            shell.client, "get_user_management_status"
        ) as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_NOT_FOUND,
                "Not Found",
                jsonrpc_response,
                None,
            )

            with pytest.raises(errors.GenericException):
                self.command.take_action(None)

            mock_call.assert_called_once()


class TestCreateUser:
    """Test CreateUser command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["create-user"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_success(self, mock_parse_jsonrpc_response):
        """Test create_user with success."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = ["user"]
            parsed_args.description = "Test user"
            parsed_args.password_expiry_days = 30
            parsed_args.disable_action = False
            parsed_args.lock_action = False

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                "test_password",
                ["user"],
                "Test user",
                30,
                True,
                False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_multiple_roles(self, mock_parse_jsonrpc_response):
        """Test create_user with multiple roles."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with multiple roles
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = ["user", "admin", "operator"]
            parsed_args.description = "Multi-role user"
            parsed_args.password_expiry_days = 90
            parsed_args.disable_action = False
            parsed_args.lock_action = False

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                "test_password",
                ["user", "admin", "operator"],
                "Multi-role user",
                90,
                True,
                False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_no_expiry(self, mock_parse_jsonrpc_response):
        """Test create_user with no password expiry."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with no password expiry
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = ["user"]
            parsed_args.description = "User with no expiry"
            parsed_args.password_expiry_days = 0
            parsed_args.disable_action = False
            parsed_args.lock_action = False

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                "test_password",
                ["user"],
                "User with no expiry",
                0,
                True,
                False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_with_special_characters(
        self, mock_parse_jsonrpc_response
    ):
        """Test create_user with special characters in description."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with special characters
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = ["user"]
            parsed_args.description = "User with special chars: @#$%^&*()"
            parsed_args.password_expiry_days = 30
            parsed_args.disable_action = False
            parsed_args.lock_action = False

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                "test_password",
                ["user"],
                "User with special chars: @#$%^&*()",
                30,
                True,
                False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_default_roles(self, mock_parse_jsonrpc_response):
        """Test create_user with default roles."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with no role names
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = None
            parsed_args.description = "Test user"
            parsed_args.password_expiry_days = 30
            parsed_args.disable_action = False
            parsed_args.lock_action = False

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                "test_password",
                ["user"],
                "Test user",
                30,
                True,
                False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_disabled(self, mock_parse_jsonrpc_response):
        """Test create_user with disabled account."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with disabled account
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = ["user"]
            parsed_args.description = "Test user"
            parsed_args.password_expiry_days = 30
            parsed_args.disable_action = True
            parsed_args.lock_action = False

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                "test_password",
                ["user"],
                "Test user",
                30,
                False,
                False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_locked(self, mock_parse_jsonrpc_response):
        """Test create_user with locked account."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with locked account
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = ["user"]
            parsed_args.description = "Test user"
            parsed_args.password_expiry_days = 30
            parsed_args.disable_action = False
            parsed_args.lock_action = True

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                "test_password",
                ["user"],
                "Test user",
                30,
                True,
                True,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_user_error(self, mock_parse_jsonrpc_response):
        """Test create_user with error."""
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                400,
                "Bad Request",
                {
                    "errors": [
                        {"msg": "Invalid data", "loc": ["password"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "create_user") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_BAD_REQUEST,
                "Bad Request",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.password = _s("test_password")
            parsed_args.role_names = ["user"]
            parsed_args.description = "Test user"
            parsed_args.password_expiry_days = 30
            parsed_args.disable_action = False
            parsed_args.lock_action = False

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once()


class TestGetUser:
    """Test GetUser command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["get-user"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_user_success(self, mock_parse_jsonrpc_response):
        """Test get_user with success."""
        user_data = {
            "user_name": user_name,
            "roles": ["user"],
            "is_enabled": True,
            "is_locked": False,
            "description": "Test user",
            "password_expiry_days": 30,
            "last_login": "2025-01-01T10:00:00",
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(user_data, "id"),
        ])

        with patch.object(shell.client, "get_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(user_name)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_user_not_found(self, mock_parse_jsonrpc_response):
        """Test get_user with not found."""
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                404,
                "Not Found",
                {
                    "errors": [
                        {"msg": "User not found", "loc": ["user_name"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "get_user") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_NOT_FOUND,
                "Not Found",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(user_name)


class TestGetUsers:
    """Test GetUsers command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["list-users"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_users_success(self, mock_parse_jsonrpc_response):
        """Test get_users with success."""
        users_data = {
            "user1": {
                "user_name": "user1",
                "roles": ["user"],
                "is_enabled": True,
                "is_locked": False,
                "password_expiry_days": 30,
                "last_login": "2025-01-01T10:00:00",
                "description": "User 1",
            },
            "user2": {
                "user_name": "user2",
                "roles": ["admin"],
                "is_enabled": True,
                "is_locked": False,
                "password_expiry_days": 0,
                "last_login": "2025-01-02T10:00:00",
                "description": "User 2",
            },
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(users_data, "id"),
        ])

        with patch.object(shell.client, "get_users") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_users_with_disabled_users(self, mock_parse_jsonrpc_response):
        """Test get_users with disabled users."""
        users_data = {
            "user1": {
                "user_name": "user1",
                "roles": ["user"],
                "is_enabled": True,
                "is_locked": False,
                "password_expiry_days": 30,
                "last_login": "2025-01-01T10:00:00",
                "description": "Active user",
            },
            "user2": {
                "user_name": "user2",
                "roles": ["admin"],
                "is_enabled": False,
                "is_locked": False,
                "password_expiry_days": 0,
                "last_login": "2025-01-02T10:00:00",
                "description": "Disabled user",
            },
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(users_data, "id"),
        ])

        with patch.object(shell.client, "get_users") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_users_with_locked_users(self, mock_parse_jsonrpc_response):
        """Test get_users with locked users."""
        users_data = {
            "user1": {
                "user_name": "user1",
                "roles": ["user"],
                "is_enabled": True,
                "is_locked": False,
                "password_expiry_days": 30,
                "last_login": "2025-01-01T10:00:00",
                "description": "Active user",
            },
            "user2": {
                "user_name": "user2",
                "roles": ["admin"],
                "is_enabled": True,
                "is_locked": True,
                "password_expiry_days": 0,
                "last_login": "2025-01-02T10:00:00",
                "description": "Locked user",
            },
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(users_data, "id"),
        ])

        with patch.object(shell.client, "get_users") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_users_with_complex_roles(self, mock_parse_jsonrpc_response):
        """Test get_users with complex role assignments."""
        users_data = {
            "admin_user": {
                "user_name": "admin_user",
                "roles": ["admin", "operator", "auditor"],
                "is_enabled": True,
                "is_locked": False,
                "password_expiry_days": 90,
                "last_login": "2025-01-01T10:00:00",
                "description": "Multi-role admin user",
            },
            "basic_user": {
                "user_name": "basic_user",
                "roles": ["user"],
                "is_enabled": True,
                "is_locked": False,
                "password_expiry_days": 30,
                "last_login": "2025-01-02T10:00:00",
                "description": "Basic user",
            },
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(users_data, "id"),
        ])

        with patch.object(shell.client, "get_users") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_users_empty(self, mock_parse_jsonrpc_response):
        """Test get_users with empty result."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({}, "id"),
        ])

        with patch.object(shell.client, "get_users") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            with patch.object(shell.stdout, "write") as mock_write:
                self.command.take_action(None)

                mock_call.assert_called_once()
                mock_write.assert_called_once_with("No users found\n")

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_users_error(self, mock_parse_jsonrpc_response):
        """Test get_users with error."""
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                500,
                "Internal Server Error",
                {
                    "errors": [
                        {"msg": "Server error", "loc": ["server"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "get_users") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_INTERNAL_SERVER_ERROR,
                "Internal Server Error",
                jsonrpc_response,
                None,
            )

            with pytest.raises(errors.GenericException):
                self.command.take_action(None)

            mock_call.assert_called_once()


class TestUpdateUser:
    """Test UpdateUser command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["update-user"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_success(self, mock_parse_jsonrpc_response):
        """Test update_user with success."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin"]
            parsed_args.description = "Updated user"
            parsed_args.password_expiry_days = 60
            parsed_args.enable_action = None
            parsed_args.disable_action = False
            parsed_args.lock_action = None
            parsed_args.unlock_action = None

            with patch.object(shell.stdout, "write") as mock_write:
                self.command.take_action(parsed_args)

                mock_call.assert_called_once_with(
                    user_name,
                    roles=["admin"],
                    description="Updated user",
                    password_expiry_days=60,
                    is_enabled=None,
                    is_locked=None,
                )
                mock_write.assert_called_once_with(
                    f"User updated: {user_name}"
                )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_multiple_actions(self, mock_parse_jsonrpc_response):
        """Test update_user with multiple actions."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with multiple actions
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin", "operator"]
            parsed_args.description = "Updated multi-role user"
            parsed_args.password_expiry_days = 120
            parsed_args.enable_action = None
            parsed_args.disable_action = False
            parsed_args.lock_action = None
            parsed_args.unlock_action = True

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                roles=["admin", "operator"],
                description="Updated multi-role user",
                password_expiry_days=120,
                is_enabled=None,
                is_locked=False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_no_changes(self, mock_parse_jsonrpc_response):
        """Test update_user with no changes."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with no changes
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = None
            parsed_args.description = None
            parsed_args.password_expiry_days = None
            parsed_args.enable_action = None
            parsed_args.disable_action = None
            parsed_args.lock_action = None
            parsed_args.unlock_action = None

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                roles=["user"],
                is_enabled=None,
                is_locked=None,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_complex_description(
        self, mock_parse_jsonrpc_response
    ):
        """Test update_user with complex description."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with complex description
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin"]
            parsed_args.description = (
                "Updated user with complex description: "
                "includes special chars @#$%^&*() and unicode: Hello World"
            )
            parsed_args.password_expiry_days = 90
            parsed_args.enable_action = None
            parsed_args.disable_action = False
            parsed_args.lock_action = None
            parsed_args.unlock_action = None

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                roles=["admin"],
                description="Updated user with complex description: includes "
                "special chars @#$%^&*() and unicode: Hello World",
                password_expiry_days=90,
                is_enabled=None,
                is_locked=None,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_enable(self, mock_parse_jsonrpc_response):
        """Test update_user with enable action."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with enable action
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin"]
            parsed_args.description = "Updated user"
            parsed_args.password_expiry_days = 60
            parsed_args.enable_action = True
            parsed_args.disable_action = None
            parsed_args.lock_action = None
            parsed_args.unlock_action = None

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                roles=["admin"],
                description="Updated user",
                password_expiry_days=60,
                is_enabled=True,
                is_locked=None,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_disable(self, mock_parse_jsonrpc_response):
        """Test update_user with disable action."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with disable action
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin"]
            parsed_args.description = "Updated user"
            parsed_args.password_expiry_days = 60
            parsed_args.enable_action = None
            parsed_args.disable_action = True
            parsed_args.lock_action = None
            parsed_args.unlock_action = None

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                roles=["admin"],
                description="Updated user",
                password_expiry_days=60,
                is_enabled=False,
                is_locked=None,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_lock(self, mock_parse_jsonrpc_response):
        """Test update_user with lock action."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with lock action
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin"]
            parsed_args.description = "Updated user"
            parsed_args.password_expiry_days = 60
            parsed_args.enable_action = None
            parsed_args.disable_action = None
            parsed_args.lock_action = True
            parsed_args.unlock_action = None

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                roles=["admin"],
                description="Updated user",
                password_expiry_days=60,
                is_enabled=None,
                is_locked=True,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_unlock(self, mock_parse_jsonrpc_response):
        """Test update_user with unlock action."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with unlock action
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin"]
            parsed_args.description = "Updated user"
            parsed_args.password_expiry_days = 60
            parsed_args.enable_action = None
            parsed_args.disable_action = None
            parsed_args.lock_action = None
            parsed_args.unlock_action = True

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name,
                roles=["admin"],
                description="Updated user",
                password_expiry_days=60,
                is_enabled=None,
                is_locked=False,
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_user_error(self, mock_parse_jsonrpc_response):
        """Test update_user with error."""
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                404,
                "Not Found",
                {
                    "errors": [
                        {"msg": "User not found", "loc": ["user_name"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "update_user") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_NOT_FOUND,
                "Not Found",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.role_names = ["admin"]
            parsed_args.description = "Updated user"
            parsed_args.password_expiry_days = 60
            parsed_args.enable_action = None
            parsed_args.disable_action = None
            parsed_args.lock_action = None
            parsed_args.unlock_action = None

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once()


class TestDeleteUser:
    """Test DeleteUser command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["delete-user"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_delete_user_success(self, mock_parse_jsonrpc_response):
        """Test delete_user with success."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "delete_user") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(user_name)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_delete_user_not_found(self, mock_parse_jsonrpc_response):
        """Test delete_user with not found."""
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                404,
                "Not Found",
                {
                    "errors": [
                        {"msg": "User not found", "loc": ["user_name"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "delete_user") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_NOT_FOUND,
                "Not Found",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(user_name)


class TestChangePassword:
    """Test ChangePassword command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["change-password"])[
            0
        ](shell, None)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_change_password_success(self, mock_parse_jsonrpc_response):
        """Test change_password with success."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"user_name": user_name}, "id"),
        ])

        with patch.object(shell.client, "change_password") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.old_password = _s("old_password")
            parsed_args.new_password = _s("new_password")

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name, "old_password", "new_password"
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_change_password_invalid_credentials(
        self, mock_parse_jsonrpc_response
    ):
        """Test change_password with invalid credentials."""
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                401,
                "Unauthorized",
                {
                    "errors": [
                        {"msg": "Invalid credentials", "loc": ["password"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "change_password") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_UNAUTHORIZED,
                "Unauthorized",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.old_password = _s("wrong_password")
            parsed_args.new_password = _s("new_password")

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                user_name, "wrong_password", "new_password"
            )


class TestGetLoginLogs:
    """Test GetLoginLogs command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["list-login-logs"])[
            0
        ](shell, None)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_success(self, mock_parse_jsonrpc_response):
        """Test get_login_logs with success."""
        logs_data = [
            {
                "user_name": user_name,
                "login_time": "2025-01-01T10:00:00",
                "ip_address": "127.0.0.1",
                "success": True,
            },
            {
                "user_name": user_name,
                "login_time": "2025-01-02T10:00:00",
                "ip_address": "192.168.1.1",
                "success": False,
            },
        ]
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(logs_data, "id"),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.limit = 10
            parsed_args.offset = 0

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(user_name, 10, 0)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_with_different_ip_addresses(
        self, mock_parse_jsonrpc_response
    ):
        """Test get_login_logs with different IP addresses."""
        logs_data = [
            {
                "user_name": user_name,
                "login_time": "2025-01-01T10:00:00",
                "ip_address": "192.168.1.100",
                "success": True,
            },
            {
                "user_name": user_name,
                "login_time": "2025-01-01T11:00:00",
                "ip_address": "10.0.0.1",
                "success": True,
            },
            {
                "user_name": user_name,
                "login_time": "2025-01-01T12:00:00",
                "ip_address": "203.0.113.1",
                "success": False,
            },
        ]
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(logs_data, "id"),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.limit = 10
            parsed_args.offset = 0

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(user_name, 10, 0)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_with_different_time_formats(
        self, mock_parse_jsonrpc_response
    ):
        """Test get_login_logs with different time formats."""
        logs_data = [
            {
                "user_name": user_name,
                "login_time": "2025-01-01 10:00:00",
                "ip_address": "127.0.0.1",
                "success": True,
            },
            {
                "user_name": user_name,
                "login_time": "2025-01-02T10:00:00Z",
                "ip_address": "192.168.1.1",
                "success": False,
            },
        ]
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(logs_data, "id"),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.limit = 10
            parsed_args.offset = 0

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(user_name, 10, 0)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_with_large_limit(
        self, mock_parse_jsonrpc_response
    ):
        """Test get_login_logs with large limit."""
        logs_data = [
            {
                "user_name": user_name,
                "login_time": "2025-01-01T10:00:00",
                "ip_address": "127.0.0.1",
                "success": True,
            },
        ]
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(logs_data, "id"),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with large limit
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.limit = 1000
            parsed_args.offset = 0

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(user_name, 1000, 0)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_with_offset(self, mock_parse_jsonrpc_response):
        """Test get_login_logs with offset."""
        logs_data = [
            {
                "user_name": user_name,
                "login_time": "2025-01-01T10:00:00",
                "ip_address": "127.0.0.1",
                "success": True,
            },
        ]
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(logs_data, "id"),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with offset
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.limit = 10
            parsed_args.offset = 5

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(user_name, 10, 5)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_no_user(self, mock_parse_jsonrpc_response):
        """Test get_login_logs without specifying user."""
        logs_data = [
            {
                "user_name": user_name,
                "login_time": "2025-01-01T10:00:00",
                "ip_address": "127.0.0.1",
                "success": True,
            },
        ]
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(logs_data, "id"),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args without user_name
            parsed_args = Mock()
            parsed_args.user_name = None
            parsed_args.limit = 10
            parsed_args.offset = 0

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(None, 10, 0)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_empty(self, mock_parse_jsonrpc_response):
        """Test get_login_logs with empty result."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok([], "id"),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.limit = 10
            parsed_args.offset = 0

            with patch.object(shell.stdout, "write") as mock_write:
                self.command.take_action(parsed_args)

                mock_call.assert_called_once_with(user_name, 10, 0)
                mock_write.assert_called_once_with("No login logs found\n")

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_login_logs_error(self, mock_parse_jsonrpc_response):
        """Test get_login_logs with error."""
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                500,
                "Internal Server Error",
                {
                    "errors": [
                        {"msg": "Server error", "loc": ["server"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "get_login_logs") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_INTERNAL_SERVER_ERROR,
                "Internal Server Error",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.user_name = user_name
            parsed_args.limit = 10
            parsed_args.offset = 0

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(user_name, 10, 0)


class TestCreateRole:
    """Test CreateRole command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["create-role"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_role_success(self, mock_parse_jsonrpc_response):
        """Test create_role with success."""
        role_name = "test_role"
        permissions = {"read": True, "write": False}
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "create_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = "Test role"

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name, permissions, "Test role"
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_role_complex_permissions(
        self, mock_parse_jsonrpc_response
    ):
        """Test create_role with complex permissions."""
        role_name = "admin_role"
        permissions = {
            "read": True,
            "write": True,
            "delete": False,
            "execute": True,
            "admin": True,
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "create_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with complex permissions
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = (
                "Administrator role with complex permissions"
            )

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name,
                permissions,
                "Administrator role with complex permissions",
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_role_empty_permissions(self, mock_parse_jsonrpc_response):
        """Test create_role with empty permissions."""
        role_name = "empty_role"
        permissions = {}
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "create_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with empty permissions
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = "Role with no permissions"

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name, permissions, "Role with no permissions"
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_role_nested_permissions(self, mock_parse_jsonrpc_response):
        """Test create_role with nested permissions structure."""
        role_name = "nested_role"
        permissions = {
            "user_management": {
                "create": True,
                "read": True,
                "update": False,
                "delete": False,
            },
            "system": {"read": True, "config": False},
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "create_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with nested permissions
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = "Role with nested permission structure"

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name, permissions, "Role with nested permission structure"
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_create_role_invalid_json(self, mock_parse_jsonrpc_response):
        """Test create_role with invalid JSON permissions."""
        role_name = "test_role"
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "create_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with invalid JSON
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = "invalid json"
            parsed_args.description = "Test role"

            with pytest.raises(errors.InvalidArguments):
                self.command.take_action(parsed_args)

            mock_call.assert_not_called()


class TestGetRole:
    """Test GetRole command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["get-role"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_role_success(self, mock_parse_jsonrpc_response):
        """Test get_role with success."""
        role_name = "test_role"
        role_data = {"role_name": role_name, "permissions": {"read": True}}
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(role_data, "id"),
        ])

        with patch.object(shell.client, "get_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name

            result = self.command.take_action(parsed_args)

            assert result is not None
            mock_call.assert_called_once_with(role_name)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_role_not_found(self, mock_parse_jsonrpc_response):
        """Test get_role with not found."""
        role_name = "nonexistent_role"
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                404,
                "Not Found",
                {
                    "errors": [
                        {"msg": "Role not found", "loc": ["role_name"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "get_role") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_NOT_FOUND,
                "Not Found",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(role_name)


class TestGetRoles:
    """Test GetRoles command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["list-roles"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_roles_success(self, mock_parse_jsonrpc_response):
        """Test get_roles with success."""
        roles_data = {
            "role1": {"role_name": "role1", "permissions": {"read": True}},
            "role2": {"role_name": "role2", "permissions": {"write": True}},
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok(roles_data, "id"),
        ])

        with patch.object(shell.client, "get_roles") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            result = self.command.take_action(None)

            assert result is not None
            mock_call.assert_called_once()

    @patch.object(Client, "parse_jsonrpc_response")
    def test_get_roles_empty(self, mock_parse_jsonrpc_response):
        """Test get_roles with empty result."""
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({}, "id"),
        ])

        with patch.object(shell.client, "get_roles") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            with patch.object(shell.stdout, "write") as mock_write:
                self.command.take_action(None)

                mock_call.assert_called_once()
                mock_write.assert_called_once_with("No roles found\n")


class TestUpdateRole:
    """Test UpdateRole command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["update-role"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_role_success(self, mock_parse_jsonrpc_response):
        """Test update_role with success."""
        role_name = "test_role"
        permissions = {"read": True, "write": True}
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "update_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = "Updated role"

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name, permissions, "Updated role"
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_role_complex_permissions(
        self, mock_parse_jsonrpc_response
    ):
        """Test update_role with complex permissions."""
        role_name = "admin_role"
        permissions = {
            "read": True,
            "write": True,
            "delete": False,
            "execute": True,
            "admin": True,
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "update_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with complex permissions
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = (
                "Updated administrator role with complex permissions"
            )

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name,
                permissions,
                "Updated administrator role with complex permissions",
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_role_empty_permissions(self, mock_parse_jsonrpc_response):
        """Test update_role with empty permissions."""
        role_name = "empty_role"
        permissions = {}
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "update_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with empty permissions
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = "Updated role with no permissions"

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name, permissions, "Updated role with no permissions"
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_role_nested_permissions(self, mock_parse_jsonrpc_response):
        """Test update_role with nested permissions structure."""
        role_name = "nested_role"
        permissions = {
            "user_management": {
                "create": True,
                "read": True,
                "update": False,
                "delete": False,
            },
            "system": {"read": True, "config": False},
        }
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "update_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with nested permissions
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = json.dumps(permissions)
            parsed_args.description = (
                "Updated role with nested permission structure"
            )

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(
                role_name,
                permissions,
                "Updated role with nested permission structure",
            )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_update_role_invalid_json(self, mock_parse_jsonrpc_response):
        """Test update_role with invalid JSON permissions."""
        role_name = "test_role"
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "update_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args with invalid JSON
            parsed_args = Mock()
            parsed_args.role_name = role_name
            parsed_args.permissions = "invalid json"
            parsed_args.description = "Updated role"

            with pytest.raises(errors.InvalidArguments):
                self.command.take_action(parsed_args)

            mock_call.assert_not_called()


class TestDeleteRole:
    """Test DeleteRole command."""

    def setup_method(self):
        """Set up test method."""
        self.command = shell.command_manager.find_command(["delete-role"])[0](
            shell, None
        )

    @patch.object(Client, "parse_jsonrpc_response")
    def test_delete_role_success(self, mock_parse_jsonrpc_response):
        """Test delete_role with success."""
        role_name = "test_role"
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "delete_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(role_name)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_delete_role_admin_role(self, mock_parse_jsonrpc_response):
        """Test delete_role with admin role."""
        role_name = "admin_role"
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "delete_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(role_name)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_delete_role_empty_permissions_role(
        self, mock_parse_jsonrpc_response
    ):
        """Test delete_role with role that has empty permissions."""
        role_name = "empty_permissions_role"
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "delete_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(role_name)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_delete_role_nested_permissions_role(
        self, mock_parse_jsonrpc_response
    ):
        """Test delete_role with role that has nested permissions."""
        role_name = "nested_permissions_role"
        mock_parse_jsonrpc_response.return_value = iter([
            True,
            Ok({"role_name": role_name}, "id"),
        ])

        with patch.object(shell.client, "delete_role") as mock_call:
            mock_call.return_value = (
                HttpCode.SUCCESS_OK,
                "OK",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name

            self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(role_name)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_delete_role_not_found(self, mock_parse_jsonrpc_response):
        """Test delete_role with not found."""
        role_name = "nonexistent_role"
        mock_parse_jsonrpc_response.return_value = iter([
            False,
            Error(
                404,
                "Not Found",
                {
                    "errors": [
                        {"msg": "Role not found", "loc": ["role_name"]},
                    ],
                    "details": "",
                },
                "",
            ),
        ])

        with patch.object(shell.client, "delete_role") as mock_call:
            mock_call.return_value = (
                HttpCode.ERROR_NOT_FOUND,
                "Not Found",
                jsonrpc_response,
                None,
            )

            # Mock parsed args
            parsed_args = Mock()
            parsed_args.role_name = role_name

            with pytest.raises(errors.GenericException):
                self.command.take_action(parsed_args)

            mock_call.assert_called_once_with(role_name)
