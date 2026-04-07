#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of MulanPSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from wy_qcos.api.posiq.routes_jsonrpc.auth import (
    login,
    logout,
)
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.api.schemas import auth as auth_schemas
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager
from wy_qcos.user.security_manager import SecurityManager


class TestLogin:
    """Test cases for login function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user.return_value = user_schemas.User(
            user_name="testuser",
            password_hash=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
        )
        mock.log_login_attempt = Mock()
        return mock

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        mock = Mock()
        mock.client = Mock()
        mock.client.host = "192.168.1.1"
        mock.headers = {"user-agent": "Mozilla/5.0"}
        return mock

    @patch.object(
        SecurityManager, "create_access_token", return_value="test_jwt_token"
    )
    @pytest.mark.asyncio
    async def test_login_success(
        self, mock_create_access_token, mock_request, mock_user_manager
    ):
        """Test successful login."""
        # Mock security_manager in app state
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_security_manager = Mock()
        mock_security_manager.create_access_token.return_value = (
            "test_jwt_token"
        )
        mock_request.app.state._security_manager = mock_security_manager

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("password123")
        )

        result = await login(mock_request, body, mock_user_manager)

        assert result is not None
        assert result.access_token == _s("test_jwt_token")
        assert result.token_type == _s("bearer")
        mock_user_manager.log_login_attempt.assert_called()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, mock_request, mock_user_manager):
        """Test login with non-existent user."""
        mock_user_manager.get_user.return_value = None
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="nonexistent", password=_s("password123")
        )

        with pytest.raises(Exception):  # Should raise UnauthorizedError
            await login(mock_request, body, mock_user_manager)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, mock_request, mock_user_manager):
        """Test login with wrong password."""
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("wrong_password")
        )

        with pytest.raises(Exception):  # Should raise UnauthorizedError
            await login(mock_request, body, mock_user_manager)

    @pytest.mark.asyncio
    async def test_login_disabled_user(self, mock_request, mock_user_manager):
        """Test login with disabled user."""
        disabled_user = user_schemas.User(
            user_name="disableduser",
            password_hash=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=False,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
        )
        mock_user_manager.get_user.return_value = disabled_user
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="disableduser", password=_s("password123")
        )

        with pytest.raises(Exception):  # Should raise ForbiddenError
            await login(mock_request, body, mock_user_manager)

    @pytest.mark.asyncio
    async def test_login_locked_user(self, mock_request, mock_user_manager):
        """Test login with locked user."""
        locked_user = user_schemas.User(
            user_name="lockeduser",
            password_hash=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="lockeduser", password=_s("password123")
        )

        with pytest.raises(Exception):  # Should raise ForbiddenError
            await login(mock_request, body, mock_user_manager)


class TestLogout:
    """Test cases for logout function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.add_to_blacklist = Mock()
        return mock

    @pytest.fixture
    def mock_request_with_token(self):
        """Create a mock request object with authorization header."""
        mock = Mock()
        mock.headers = {"Authorization": "Bearer test_jwt_token"}
        return mock

    @pytest.fixture
    def mock_request_without_token(self):
        """Create a mock request object without authorization header."""
        mock = Mock()
        mock.headers = {}
        return mock

    @patch("wy_qcos.api.posiq.routes_jsonrpc.auth.jwt.decode")
    def test_logout_with_token(
        self, mock_jwt_decode, mock_request_with_token, mock_user_manager
    ):
        """Test logout with valid token."""
        mock_jwt_decode.return_value = {
            "jti": "token-jti-123",
            "exp": (datetime.now() + timedelta(hours=1)).timestamp(),
        }

        auth_data = {"user_id": "testuser"}
        result = logout(
            mock_request_with_token, None, auth_data, mock_user_manager
        )

        assert result is not None
        assert result.message == "Successfully logged out"
        mock_user_manager.add_to_blacklist.assert_called()

    def test_logout_without_token(
        self, mock_request_without_token, mock_user_manager
    ):
        """Test logout without token."""
        auth_data = {"user_id": "testuser"}
        result = logout(
            mock_request_without_token, None, auth_data, mock_user_manager
        )

        assert result is not None
        assert result.message == "Successfully logged out"

    def test_logout_without_auth_data(
        self, mock_request_without_token, mock_user_manager
    ):
        """Test logout without auth data."""
        result = logout(
            mock_request_without_token, None, None, mock_user_manager
        )

        assert result is not None
        assert result.message == "Successfully logged out"

    @patch("wy_qcos.api.posiq.routes_jsonrpc.auth.jwt.decode")
    def test_logout_invalid_token(
        self, mock_jwt_decode, mock_request_with_token, mock_user_manager
    ):
        """Test logout with invalid token."""
        mock_jwt_decode.side_effect = Exception("Invalid token")

        auth_data = {"user_id": "testuser"}
        result = logout(
            mock_request_with_token, None, auth_data, mock_user_manager
        )

        assert result is not None
        assert result.message == "Successfully logged out"


# Note: The following tests for refresh_token and get_current_user_info
# require FastAPI's TestClient for proper dependency injection testing.
# These tests are better suited for integration testing.
#
# class TestRefreshToken:
#     """Test cases for refresh_token function."""
#     ...
#
# class TestGetCurrentUserInfo:
#     """Test cases for get_current_user_info function."""
#     ...
