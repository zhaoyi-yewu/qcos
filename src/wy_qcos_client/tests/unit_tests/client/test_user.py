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
from unittest.mock import patch

from wy_qcos_client.client import Client
from wy_qcos_client.common.client_library import _s
from wy_qcos_client.common.constant import HttpCode
from wy_qcos_client.tests.unit_tests.constant_for_test import ConstantForTest


class TestClientUser:
    """Test client user management methods."""

    def setup_method(self):
        """Set up test method."""
        self.client = Client()
        self.user_name = "test_user"
        self.password = _s("test_password")
        self.roles = ["user"]
        self.job_id = ConstantForTest.job_id

    @patch.object(Client, "call_json_rpc")
    def test_get_user_management_status(self, mock_call_json_rpc):
        """Test get_user_management_status method."""
        # Mock successful response
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"enabled": True}}),
            None,
        )

        status_code, reason, text, result = (
            self.client.get_user_management_status()
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_user_management_status", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_create_user_success(self, mock_call_json_rpc):
        """Test create_user method with success."""
        # Mock successful response
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"user_name": self.user_name}}),
            None,
        )

        status_code, reason, text, result = self.client.create_user(
            self.user_name,
            self.password,
            self.roles,
            description="Test user",
            password_expiry_days=30,
            is_enabled=True,
            is_locked=False,
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "create_user",
            {
                "user_name": self.user_name,
                "password": self.password,
                "roles": self.roles,
                "description": "Test user",
                "password_expiry_days": 30,
                "is_enabled": True,
                "is_locked": False,
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_create_user_minimal(self, mock_call_json_rpc):
        """Test create_user method with minimal parameters."""
        # Mock successful response
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"user_name": self.user_name}}),
            None,
        )

        status_code, reason, text, result = self.client.create_user(
            self.user_name, self.password, self.roles
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "create_user",
            {
                "user_name": self.user_name,
                "password": self.password,
                "roles": self.roles,
                "is_enabled": True,
                "is_locked": True,
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_user(self, mock_call_json_rpc):
        """Test get_user method."""
        # Mock successful response
        user_data = {
            "user_name": self.user_name,
            "roles": self.roles,
            "is_enabled": True,
            "is_locked": False,
            "description": "Test user",
        }
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": user_data}),
            None,
        )

        status_code, reason, text, result = self.client.get_user(
            self.user_name
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_user", {"user_name": self.user_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_update_user_success(self, mock_call_json_rpc):
        """Test update_user method with success."""
        # Mock successful response
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"user_name": self.user_name}}),
            None,
        )

        status_code, reason, text, result = self.client.update_user(
            self.user_name,
            roles=["admin"],
            description="Updated user",
            password_expiry_days=60,
            is_enabled=False,
            is_locked=True,
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "update_user",
            {
                "user_name": self.user_name,
                "roles": ["admin"],
                "description": "Updated user",
                "password_expiry_days": 60,
                "is_enabled": False,
                "is_locked": True,
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_update_user_partial(self, mock_call_json_rpc):
        """Test update_user method with partial updates."""
        # Mock successful response
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"user_name": self.user_name}}),
            None,
        )

        status_code, reason, text, result = self.client.update_user(
            self.user_name, roles=["admin"]
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "update_user",
            {"user_name": self.user_name, "roles": ["admin"]},
        )

    @patch.object(Client, "call_json_rpc")
    def test_delete_user(self, mock_call_json_rpc):
        """Test delete_user method."""
        # Mock successful response
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"user_name": self.user_name}}),
            None,
        )

        status_code, reason, text, result = self.client.delete_user(
            self.user_name
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "delete_user", {"user_name": self.user_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_users(self, mock_call_json_rpc):
        """Test get_users method."""
        # Mock successful response
        users_data = {
            "user1": {"user_name": "user1", "roles": ["user"]},
            "user2": {"user_name": "user2", "roles": ["admin"]},
        }
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": users_data}),
            None,
        )

        status_code, reason, text, result = self.client.get_users()

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_users", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_create_role(self, mock_call_json_rpc):
        """Test create_role method."""
        # Mock successful response
        role_name = "test_role"
        permissions = {"read": True, "write": False}
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"role_name": role_name}}),
            None,
        )

        status_code, reason, text, result = self.client.create_role(
            role_name, permissions, description="Test role"
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "create_role",
            {
                "role_name": role_name,
                "permissions": permissions,
                "description": "Test role",
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_role(self, mock_call_json_rpc):
        """Test get_role method."""
        # Mock successful response
        role_name = "test_role"
        role_data = {"role_name": role_name, "permissions": {"read": True}}
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": role_data}),
            None,
        )

        status_code, reason, text, result = self.client.get_role(role_name)

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_role", {"role_name": role_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_update_role(self, mock_call_json_rpc):
        """Test update_role method."""
        # Mock successful response
        role_name = "test_role"
        permissions = {"read": True, "write": True}
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"role_name": role_name}}),
            None,
        )

        status_code, reason, text, result = self.client.update_role(
            role_name, permissions=permissions, description="Updated role"
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "update_role",
            {
                "role_name": role_name,
                "permissions": permissions,
                "description": "Updated role",
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_delete_role(self, mock_call_json_rpc):
        """Test delete_role method."""
        # Mock successful response
        role_name = "test_role"
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"role_name": role_name}}),
            None,
        )

        status_code, reason, text, result = self.client.delete_role(role_name)

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "delete_role", {"role_name": role_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_roles(self, mock_call_json_rpc):
        """Test get_roles method."""
        # Mock successful response
        roles_data = {
            "role1": {"role_name": "role1", "permissions": {"read": True}},
            "role2": {"role_name": "role2", "permissions": {"write": True}},
        }
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": roles_data}),
            None,
        )

        status_code, reason, text, result = self.client.get_roles()

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_roles", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_lock_user(self, mock_call_json_rpc):
        """Test lock_user method."""
        # Mock successful response
        action = "lock"
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"user_name": self.user_name}}),
            None,
        )

        status_code, reason, text, result = self.client.lock_user(
            self.user_name, action
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "lock_user",
            {"user_name": self.user_name, "action": action},
        )

    @patch.object(Client, "call_json_rpc")
    def test_change_password(self, mock_call_json_rpc):
        """Test change_password method."""
        # Mock successful response
        old_password = _s("old_password")
        new_password = _s("new_password")
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": {"user_name": self.user_name}}),
            None,
        )

        status_code, reason, text, result = self.client.change_password(
            self.user_name, old_password, new_password
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "change_password",
            {
                "user_name": self.user_name,
                "old_password": _s(old_password),
                "new_password": _s(new_password),
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_login_logs(self, mock_call_json_rpc):
        """Test get_login_logs method."""
        # Mock successful response
        logs_data = [
            {
                "user_name": self.user_name,
                "login_time": "2025-01-01T10:00:00",
                "ip_address": "127.0.0.1",
                "success": True,
            }
        ]
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": logs_data}),
            None,
        )

        status_code, reason, text, result = self.client.get_login_logs(
            self.user_name, limit=10, offset=0
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "get_login_logs",
            {"user_name": self.user_name, "limit": 10, "offset": 0},
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_login_logs_no_user(self, mock_call_json_rpc):
        """Test get_login_logs method without specifying user."""
        # Mock successful response
        logs_data = [
            {
                "user_name": self.user_name,
                "login_time": "2025-01-01T10:00:00",
                "ip_address": "127.0.0.1",
                "success": True,
            }
        ]
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            json.dumps({"result": logs_data}),
            None,
        )

        status_code, reason, text, result = self.client.get_login_logs(
            limit=10, offset=0
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "get_login_logs",
            {"limit": 10, "offset": 0},
        )

    @patch.object(Client, "call_json_rpc")
    def test_user_management_status_error(self, mock_call_json_rpc):
        """Test user management status with error response."""
        # Mock error response
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "User not found"}}),
            None,
        )

        status_code, reason, text, result = (
            self.client.get_user_management_status()
        )

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_user_management_status", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_create_user_error(self, mock_call_json_rpc):
        """Test create_user with error response."""
        # Mock error response
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_BAD_REQUEST,
            "Bad Request",
            json.dumps({"error": {"code": 400, "message": "Invalid data"}}),
            None,
        )

        status_code, reason, text, result = self.client.create_user(
            self.user_name, self.password, self.roles
        )

        assert status_code == HttpCode.ERROR_BAD_REQUEST
        assert reason == "Bad Request"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "create_user",
            {
                "user_name": self.user_name,
                "password": self.password,
                "roles": self.roles,
                "is_enabled": True,
                "is_locked": True,
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_user_not_found(self, mock_call_json_rpc):
        """Test get_user with not found response."""
        # Mock not found response
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "User not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.get_user(
            self.user_name
        )

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_user", {"user_name": self.user_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_update_user_not_found(self, mock_call_json_rpc):
        """Test update_user with not found response."""
        # Mock not found response
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "User not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.update_user(
            self.user_name, roles=["admin"]
        )

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "update_user",
            {"user_name": self.user_name, "roles": ["admin"]},
        )

    @patch.object(Client, "call_json_rpc")
    def test_delete_user_not_found(self, mock_call_json_rpc):
        """Test delete_user with not found response."""
        # Mock not found response
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "User not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.delete_user(
            self.user_name
        )

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "delete_user", {"user_name": self.user_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_create_role_error(self, mock_call_json_rpc):
        """Test create_role with error response."""
        # Mock error response
        role_name = "test_role"
        permissions = {"read": True}
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_BAD_REQUEST,
            "Bad Request",
            json.dumps({"error": {"code": 400, "message": "Invalid role"}}),
            None,
        )

        status_code, reason, text, result = self.client.create_role(
            role_name, permissions
        )

        assert status_code == HttpCode.ERROR_BAD_REQUEST
        assert reason == "Bad Request"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "create_role",
            {"role_name": role_name, "permissions": permissions},
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_role_not_found(self, mock_call_json_rpc):
        """Test get_role with not found response."""
        # Mock not found response
        role_name = "nonexistent_role"
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "Role not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.get_role(role_name)

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_role", {"role_name": role_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_update_role_not_found(self, mock_call_json_rpc):
        """Test update_role with not found response."""
        # Mock not found response
        role_name = "nonexistent_role"
        permissions = {"read": True}
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "Role not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.update_role(
            role_name, permissions=permissions
        )

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "update_role",
            {"role_name": role_name, "permissions": permissions},
        )

    @patch.object(Client, "call_json_rpc")
    def test_delete_role_not_found(self, mock_call_json_rpc):
        """Test delete_role with not found response."""
        # Mock not found response
        role_name = "nonexistent_role"
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "Role not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.delete_role(role_name)

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "delete_role", {"role_name": role_name}
        )

    @patch.object(Client, "call_json_rpc")
    def test_lock_user_not_found(self, mock_call_json_rpc):
        """Test lock_user with not found response."""
        # Mock not found response
        action = "lock"
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "User not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.lock_user(
            self.user_name, action
        )

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "lock_user",
            {"user_name": self.user_name, "action": action},
        )

    @patch.object(Client, "call_json_rpc")
    def test_change_password_invalid(self, mock_call_json_rpc):
        """Test change_password with invalid credentials."""
        # Mock invalid credentials response
        old_password = _s("wrong_password")
        new_password = _s("new_password")
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_UNAUTHORIZED,
            "Unauthorized",
            json.dumps({
                "error": {"code": 401, "message": "Invalid credentials"}
            }),
            None,
        )

        status_code, reason, text, result = self.client.change_password(
            self.user_name, old_password, new_password
        )

        assert status_code == HttpCode.ERROR_UNAUTHORIZED
        assert reason == "Unauthorized"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "change_password",
            {
                "user_name": self.user_name,
                "old_password": old_password,
                "new_password": new_password,
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_login_logs_user_not_found(self, mock_call_json_rpc):
        """Test get_login_logs with user not found."""
        # Mock not found response
        mock_call_json_rpc.return_value = (
            HttpCode.ERROR_NOT_FOUND,
            "Not Found",
            json.dumps({"error": {"code": 404, "message": "User not found"}}),
            None,
        )

        status_code, reason, text, result = self.client.get_login_logs(
            self.user_name
        )

        assert status_code == HttpCode.ERROR_NOT_FOUND
        assert reason == "Not Found"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url,
            "get_login_logs",
            {"user_name": self.user_name, "limit": 100, "offset": 0},
        )

    @patch.object(Client, "call_json_rpc")
    def test_connection_error(self, mock_call_json_rpc):
        """Test handling of connection errors."""
        # Mock connection error
        mock_call_json_rpc.return_value = (
            -1,
            "Connection error: Max retries exceeded",
            None,
            None,
        )

        status_code, reason, text, result = (
            self.client.get_user_management_status()
        )

        assert status_code == -1
        assert "Connection error" in reason
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_user_management_status", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_invalid_json_response(self, mock_call_json_rpc):
        """Test handling of invalid JSON response."""
        # Mock invalid JSON response
        mock_call_json_rpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            "invalid json response",
            None,
        )

        status_code, reason, text, result = (
            self.client.get_user_management_status()
        )

        assert status_code == HttpCode.SUCCESS_OK
        assert reason == "OK"
        assert text == "invalid json response"
        mock_call_json_rpc.assert_called_once_with(
            self.client.user_url, "get_user_management_status", {}
        )
