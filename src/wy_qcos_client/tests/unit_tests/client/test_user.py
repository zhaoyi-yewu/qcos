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

from unittest.mock import patch

from wy_qcos_client.client import Client
from wy_qcos_client.common.client_library import _s

client = Client()


class TestClientUser:
    """Test cases for user management API methods in Client."""

    @classmethod
    def setup_class(cls):
        cls.user_id = "00000000-0000-4000-8000-000000000001"
        cls.role_id = "10000000-0000-4000-8000-000000000001"
        cls.return_values = (200, "OK", "text", "result")

    @patch.object(Client, "call_json_rpc")
    def test_get_user_mgmt_status(self, mock_call_json_rpc):
        """Test get_user_mgmt_status method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_user_mgmt_status()
        assert status_code == 200
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "get_user_mgmt_status", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_create_user_basic(self, mock_call_json_rpc):
        """Test create_user method with basic parameters."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_user(
            user_name="testuser",
            password=_s("password123"),
            roles=["user"],
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once()
        call_args = mock_call_json_rpc.call_args[0]
        assert call_args[0] == client.user_url
        assert call_args[1] == "create_user"
        data = call_args[2]
        assert data["user_name"] == "testuser"
        assert data["password"] == _s("password123")
        assert data["roles"] == ["user"]

    @patch.object(Client, "call_json_rpc")
    def test_create_user_with_all_parameters(self, mock_call_json_rpc):
        """Test create_user method with all parameters."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_user(
            user_name="testuser",
            password=_s("password123"),
            roles=["admin", "user"],
            description="Test user",
            password_expiry_days=90,
            is_enabled=True,
            is_locked=False,
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["user_name"] == "testuser"
        assert data["description"] == "Test user"
        assert data["password_expiry_days"] == 90
        assert data["is_enabled"] is True
        assert data["is_locked"] is False

    @patch.object(Client, "call_json_rpc")
    def test_get_user(self, mock_call_json_rpc):
        """Test get_user method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_user(self.user_id)
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "get_user", {"user_id": self.user_id}
        )

    @patch.object(Client, "call_json_rpc")
    def test_update_user_basic(self, mock_call_json_rpc):
        """Test update_user method with basic parameters."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_user(
            user_id=self.user_id,
            roles=["admin"],
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        assert call_args[1] == "update_user"
        data = call_args[2]
        assert data["user_id"] == self.user_id
        assert data["roles"] == ["admin"]

    @patch.object(Client, "call_json_rpc")
    def test_update_user_with_all_parameters(self, mock_call_json_rpc):
        """Test update_user method with all parameters."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_user(
            user_id=self.user_id,
            roles=["user"],
            description="Updated description",
            password_expiry_days=60,
            is_enabled=False,
            is_locked=True,
        )
        assert status_code == 200
        data = mock_call_json_rpc.call_args[0][2]
        assert data["description"] == "Updated description"
        assert data["password_expiry_days"] == 60
        assert data["is_enabled"] is False
        assert data["is_locked"] is True

    @patch.object(Client, "call_json_rpc")
    def test_delete_user(self, mock_call_json_rpc):
        """Test delete_user method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.delete_user(self.user_id)
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url,
            "delete_user",
            {"user_id": self.user_id, "force": False},
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_users(self, mock_call_json_rpc):
        """Test get_users method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_users()
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "get_users", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_change_password(self, mock_call_json_rpc):
        """Test change_password method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.change_password(
            user_id=self.user_id,
            old_password=_s("oldpass123"),
            new_password=_s("newpass456"),
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url,
            "change_password",
            {
                "user_id": self.user_id,
                "old_password": _s("oldpass123"),
                "new_password": _s("newpass456"),
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_login_logs_without_user_id(self, mock_call_json_rpc):
        """Test get_login_logs method without user_id."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_login_logs(
            limit=50,
            offset=10,
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0][2]
        assert call_args["limit"] == 50
        assert call_args["offset"] == 10
        assert "user_id" not in call_args

    @patch.object(Client, "call_json_rpc")
    def test_get_login_logs_with_user_id(self, mock_call_json_rpc):
        """Test get_login_logs method with user_id."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_login_logs(
            user_id=self.user_id,
            limit=100,
            offset=0,
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0][2]
        assert call_args["user_id"] == self.user_id
        assert call_args["limit"] == 100
        assert call_args["offset"] == 0

    @patch.object(Client, "call_json_rpc")
    def test_get_login_logs_default_values(self, mock_call_json_rpc):
        """Test get_login_logs method with default values."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_login_logs()
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0][2]
        assert call_args["limit"] == 100
        assert call_args["offset"] == 0

    @patch.object(Client, "call_json_rpc")
    def test_clear_login_logs_all(self, mock_call_json_rpc):
        """Test clear_login_logs method without user_id or user_name."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.clear_login_logs()
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "clear_login_logs", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_clear_login_logs_with_user_id(self, mock_call_json_rpc):
        """Test clear_login_logs method with user_id."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.clear_login_logs(
            user_id=self.user_id
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "clear_login_logs", {"user_id": self.user_id}
        )

    @patch.object(Client, "call_json_rpc")
    def test_clear_login_logs_with_user_name(self, mock_call_json_rpc):
        """Test clear_login_logs method with user_name."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.clear_login_logs(
            user_name="testuser"
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "clear_login_logs", {"user_name": "testuser"}
        )


class TestSetUserMgmt:
    """Test cases for set_user_mgmt method in Client."""

    @classmethod
    def setup_class(cls):
        cls.return_values = (200, "OK", "text", "result")

    @patch.object(Client, "call_json_rpc")
    def test_set_user_mgmt_auth_mode_jwt(self, mock_call_json_rpc):
        """Test set_user_mgmt with JWT auth mode."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.set_user_mgmt(
            auth_mode="jwt"
        )
        assert status_code == 200
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once()
        call_args = mock_call_json_rpc.call_args[0]
        assert call_args[0] == client.user_url
        assert call_args[1] == "set_user_mgmt"
        data = call_args[2]
        assert data["auth_mode"] == "jwt"

    @patch.object(Client, "call_json_rpc")
    def test_set_user_mgmt_auth_mode_virtual_instance(self, mock_call_json_rpc):
        """Test set_user_mgmt with virtual_instance mode."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.set_user_mgmt(
            auth_mode="virtual_instance"
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once()
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["auth_mode"] == "virtual_instance"

    @patch.object(Client, "call_json_rpc")
    def test_set_user_mgmt_auth_mode_no(self, mock_call_json_rpc):
        """Test set_user_mgmt with no auth mode."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.set_user_mgmt(
            auth_mode="no"
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once()
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["auth_mode"] == "no"

    @patch.object(Client, "call_json_rpc")
    def test_set_user_mgmt_auth_mode_case_insensitive(self, mock_call_json_rpc):
        """Test set_user_mgmt with case-insensitive input."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.set_user_mgmt(
            auth_mode="JWT"
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once()
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        # Verify the mode is passed
        assert data["auth_mode"] == "JWT"

    @patch.object(Client, "call_json_rpc")
    def test_set_user_mgmt_auth_mode_invalid_mode(self, mock_call_json_rpc):
        """Test set_user_mgmt with invalid auth mode."""
        # Client doesn't validate, but the API will
        mock_call_json_rpc.return_value = (
            400,
            "Bad Request",
            "Invalid auth mode",
            None,
        )
        status_code, reason, text, result = client.set_user_mgmt(
            auth_mode="invalid_mode"
        )
        assert status_code == 400
        assert reason == "Bad Request"
