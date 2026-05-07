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

import os
from unittest.mock import patch

from wy_qcos_client.client import Client
from wy_qcos_client.common.client_library import _s

client = Client()


class TestClientLogin:
    """Test cases for authentication API methods in Client."""

    @classmethod
    def setup_class(cls):
        cls.return_values = (200, "OK", "text", "result")

    @patch.object(Client, "call_json_rpc")
    def test_login(self, mock_call_json_rpc):
        """Test login method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.login(
            username="admin",
            password=_s("admin123"),
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.auth_url,
            "login",
            {"username": "admin", "password": "admin123"},
        )

    @patch.object(Client, "call_json_rpc")
    def test_login_invalid_credentials(self, mock_call_json_rpc):
        """Test login with invalid credentials."""
        mock_call_json_rpc.return_value = (
            401,
            "Unauthorized",
            "Invalid username or password",
            {},
        )
        status_code, reason, text, result = client.login(
            username="admin",
            password=_s("wrongpassword"),
        )
        assert status_code == 401

    @patch.object(Client, "call_json_rpc")
    def test_login_locked_account(self, mock_call_json_rpc):
        """Test login with locked account."""
        mock_call_json_rpc.return_value = (
            403,
            "Forbidden",
            "User account is locked",
            {},
        )
        status_code, reason, text, result = client.login(
            username="lockeduser",
            password=_s("password123"),
        )
        assert status_code == 403

    @patch.object(Client, "call_json_rpc")
    def test_logout(self, mock_call_json_rpc):
        """Test logout method."""
        mock_call_json_rpc.return_value = self.return_values
        client.set_token("test_token")
        status_code, reason, text, result = client.logout()
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.auth_url, "logout", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_logout_without_token(self, mock_call_json_rpc):
        """Test logout without a valid token."""
        mock_call_json_rpc.return_value = (
            401,
            "Unauthorized",
            "No token provided",
            {},
        )
        client.set_token(None)
        status_code, reason, text, result = client.logout()
        assert status_code == 401

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token(self, mock_call_json_rpc):
        """Test refresh_token method."""
        mock_response = {
            "access_token": "new_token_123",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }
        mock_call_json_rpc.return_value = (
            200,
            "OK",
            "text",
            mock_response,
        )
        client.set_token("old_token")
        os.environ["QCOS_REFRESH_TOKEN"] = _s("old_refresh_token")
        status_code, reason, text, result = client.refresh_token()
        assert status_code == 200
        assert client.get_token() == "new_token_123"
        if "QCOS_REFRESH_TOKEN" in os.environ:
            del os.environ["QCOS_REFRESH_TOKEN"]

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_invalid(self, mock_call_json_rpc):
        """Test refresh_token with invalid refresh token."""
        mock_call_json_rpc.return_value = (
            401,
            "Unauthorized",
            "Invalid or expired refresh token",
            {},
        )
        client.set_token("old_token")
        os.environ["QCOS_REFRESH_TOKEN"] = _s("invalid_token")
        status_code, reason, text, result = client.refresh_token()
        assert status_code == 401
        if "QCOS_REFRESH_TOKEN" in os.environ:
            del os.environ["QCOS_REFRESH_TOKEN"]

    @patch.object(Client, "call_json_rpc")
    def test_get_me(self, mock_call_json_rpc):
        """Test get_me method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_me()
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(client.auth_url, "me", {})

    @patch.object(Client, "call_json_rpc")
    def test_get_me_unauthorized(self, mock_call_json_rpc):
        """Test get_me when not authenticated."""
        mock_call_json_rpc.return_value = (
            401,
            "Unauthorized",
            "Authentication required",
            {},
        )
        client.set_token(None)
        status_code, reason, text, result = client.get_me()
        assert status_code == 401

    @patch.object(Client, "call_json_rpc")
    def test_login_disabled_account(self, mock_call_json_rpc):
        """Test login with disabled account."""
        mock_call_json_rpc.return_value = (
            403,
            "Forbidden",
            "User account is disabled",
            {},
        )
        status_code, reason, text, result = client.login(
            username="disableduser",
            password=_s("password123"),
        )
        assert status_code == 403

    @patch.object(Client, "call_json_rpc")
    def test_login_password_expired(self, mock_call_json_rpc):
        """Test login with expired password."""
        mock_call_json_rpc.return_value = (
            403,
            "Forbidden",
            "Password has expired",
            {},
        )
        status_code, reason, text, result = client.login(
            username="testuser",
            password=_s("password123"),
        )
        assert status_code == 403

    def test_set_token(self):
        """Test set_token method."""
        client.set_token("test_token_123")
        assert client.get_token() == "test_token_123"

    def test_get_token(self):
        """Test get_token method."""
        client.set_token("another_token")
        token = client.get_token()
        assert token == _s("another_token")

    def test_clear_token(self):
        """Test clear_token method."""
        client.set_token("token_to_clear")
        client.clear_token()
        assert client.get_token() is None
