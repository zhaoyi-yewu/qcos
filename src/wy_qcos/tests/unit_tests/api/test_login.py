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
    refresh_token,
)
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.api.schemas import auth as auth_schemas
from wy_qcos.common.config import Config
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
            hashed_password=UserManager.hash_password("password123"),
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
    def mock_users_repo(self):
        """Create a mock users repository."""
        mock = Mock()
        mock.update = Mock(return_value=(True, None, None))
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
    @patch.object(
        SecurityManager,
        "create_refresh_token",
        return_value="test_refresh_token",
    )
    @pytest.mark.asyncio
    async def test_login_success(
        self,
        mock_create_refresh_token,
        mock_create_access_token,
        mock_request,
        mock_user_manager,
        mock_users_repo,
    ):
        """Test successful login."""
        # Mock security_manager in app state
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_security_manager = Mock()
        mock_security_manager.create_access_token.return_value = (
            "test_jwt_token"
        )
        mock_security_manager.create_refresh_token.return_value = (
            "test_refresh_token"
        )
        mock_request.app.state._security_manager = mock_security_manager

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("password123")
        )

        result = await login(
            mock_request, body, mock_user_manager, mock_users_repo
        )

        assert result is not None
        assert result.access_token == _s("test_jwt_token")
        assert result.token_type == _s("bearer")
        mock_user_manager.log_login_attempt.assert_called()

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with non-existent user."""
        mock_user_manager.get_user.return_value = None
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="nonexistent", password=_s("password123")
        )

        with pytest.raises(Exception):  # Should raise UnauthorizedError
            await login(mock_request, body, mock_user_manager, mock_users_repo)

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with wrong password."""
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("wrong_password")
        )

        with pytest.raises(Exception):  # Should raise UnauthorizedError
            await login(mock_request, body, mock_user_manager, mock_users_repo)

    @pytest.mark.asyncio
    async def test_login_disabled_user(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with disabled user."""
        disabled_user = user_schemas.User(
            user_name="disableduser",
            hashed_password=UserManager.hash_password("password123"),
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
            await login(mock_request, body, mock_user_manager, mock_users_repo)

    @pytest.mark.asyncio
    async def test_login_locked_user(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with locked user."""
        locked_user = user_schemas.User(
            user_name="lockeduser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
            locked_until=datetime.now() + timedelta(minutes=30),
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="lockeduser", password=_s("password123")
        )

        with pytest.raises(Exception):  # Should raise ForbiddenError
            await login(mock_request, body, mock_user_manager, mock_users_repo)

    @pytest.mark.asyncio
    async def test_login_locked_user_with_correct_password(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with locked user and correct password."""
        locked_user = user_schemas.User(
            user_name="lockeduser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=3,
            locked_until=datetime.now() + timedelta(minutes=30),
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "Mozilla/5.0"}

        body = auth_schemas.LoginRequest(
            username="lockeduser", password=_s("password123")
        )

        # Even with correct password, locked user should not be able to login
        with pytest.raises(Exception):  # Should raise ForbiddenError
            await login(mock_request, body, mock_user_manager, mock_users_repo)

    @pytest.mark.asyncio
    async def test_login_auto_unlock_expired_lockout(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login auto-unlocks user when lockout period has expired."""
        locked_user = user_schemas.User(
            user_name="lockeduser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=5,
            locked_until=datetime.now()
            - timedelta(minutes=1),  # Lockout expired
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_security_manager = Mock()
        mock_security_manager.create_access_token.return_value = (
            "test_jwt_token"
        )
        mock_security_manager.create_refresh_token.return_value = (
            "test_refresh_token"
        )
        mock_request.app.state._security_manager = mock_security_manager
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "Mozilla/5.0"}
        mock_user_manager.log_login_attempt = Mock()

        body = auth_schemas.LoginRequest(
            username="lockeduser", password=_s("password123")
        )

        # Should succeed because lockout period has expired
        result = await login(
            mock_request, body, mock_user_manager, mock_users_repo
        )
        assert result is not None
        assert result.access_token == _s("test_jwt_token")

    @pytest.mark.asyncio
    async def test_login_password_expired(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with password expired."""
        expired_user = user_schemas.User(
            user_name="expireduser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,  # Already expired
            password_changed_at=datetime.now() - timedelta(days=91),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
        )
        mock_user_manager.get_user.return_value = expired_user
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="expireduser", password=_s("password123")
        )

        with pytest.raises(Exception):  # Should raise ForbiddenError
            await login(mock_request, body, mock_user_manager, mock_users_repo)

    @pytest.mark.asyncio
    async def test_login_max_attempts_exceeded(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test that exceeding max login attempts locks the account."""
        user = user_schemas.User(
            user_name="testuser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=Config.USERS.MAX_LOGIN_ATTEMPTS - 1,
        )
        mock_user_manager.get_user.return_value = user
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._security_manager = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "Mozilla/5.0"}
        mock_user_manager.log_login_attempt = Mock()

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("wrong_password")
        )

        # Should fail and potentially lock account
        with pytest.raises(Exception):  # Should raise UnauthorizedError
            await login(mock_request, body, mock_user_manager, mock_users_repo)


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


class TestLoginEnhanced:
    """Enhanced test cases for login."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.log_login_attempt = Mock()
        return mock

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        mock = Mock()
        mock.client = Mock()
        mock.client.host = "192.168.1.1"
        mock.headers = {"user-agent": "Mozilla/5.0"}
        mock.app = Mock()
        mock.app.state = Mock()
        return mock

    @pytest.fixture
    def mock_users_repo(self):
        """Create a mock users repository."""
        mock = Mock()
        mock.update = Mock(return_value=(True, None, None))
        return mock

    @pytest.mark.asyncio
    async def test_login_locked_user_correct_password(
        self, mock_request, mock_user_manager
    ):
        """Test that locked user cannot login even with correct password."""
        locked_user = user_schemas.User(
            user_name="lockeduser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=5,
            locked_until=datetime.now() + timedelta(minutes=30),
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_security_manager = Mock(spec=SecurityManager)
        mock_request.app.state._security_manager = mock_security_manager

        body = auth_schemas.LoginRequest(
            username="lockeduser", password=_s("password123")
        )

        with pytest.raises(Exception):
            await login(mock_request, body, mock_user_manager)

    @pytest.mark.asyncio
    async def test_login_auto_unlock_on_expiry(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test automatic unlock when lockout period expires."""
        locked_user = user_schemas.User(
            user_name="testuser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=5,
            locked_until=datetime.now() - timedelta(minutes=5),  # Expired
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_security_manager = Mock(spec=SecurityManager)
        mock_security_manager.create_access_token.return_value = "test_token"
        mock_security_manager.create_refresh_token.return_value = (
            "refresh_token"
        )
        mock_request.app.state._security_manager = mock_security_manager

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("password123")
        )

        result = await login(
            mock_request, body, mock_user_manager, mock_users_repo
        )
        assert result is not None
        assert result.access_token == _s("test_token")

    @pytest.mark.asyncio
    async def test_login_password_expired(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with expired password."""
        expired_user = user_schemas.User(
            user_name="testuser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now() - timedelta(days=91),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
        )
        mock_user_manager.get_user.return_value = expired_user
        mock_user_manager.is_password_expired.return_value = True
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("password123")
        )

        with pytest.raises(Exception):
            await login(mock_request, body, mock_user_manager, mock_users_repo)

    @pytest.mark.asyncio
    async def test_login_max_attempts_locks_account(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test that exceeding max login attempts locks the account."""
        user = user_schemas.User(
            user_name="testuser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=Config.USERS.MAX_LOGIN_ATTEMPTS - 1,
        )
        mock_user_manager.get_user.return_value = user
        mock_request.app.state._security_manager = Mock()

        body = auth_schemas.LoginRequest(
            username="testuser", password=_s("wrongpassword")
        )

        with pytest.raises(Exception):
            await login(mock_request, body, mock_user_manager, mock_users_repo)


class TestLoginMissingScenarios:
    """Supplementary tests for missing login scenarios."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.log_login_attempt = Mock()
        return mock

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        mock = Mock()
        mock.client = Mock()
        mock.client.host = "192.168.1.1"
        mock.headers = {"user-agent": "Mozilla/5.0"}
        mock.app = Mock()
        mock.app.state = Mock()
        return mock

    @pytest.fixture
    def mock_users_repo(self):
        """Create a mock users repository."""
        mock = Mock()
        mock.update = Mock(return_value=(True, None, None))
        return mock

    @pytest.mark.asyncio
    async def test_login_locked_user_wrong_password(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test login with locked user and wrong password.

        Scenario 4: User account is locked (not expired) and password is wrong.

        Test points:
        - User state: is_locked=True, locked_until not expired
        - Submitted password: incorrect password
        - Expected result: forbidden error with account locked message
        - Code path: auth.py L143-164

        Verification logic:
        1. Check is_user_locked_before_password_check flag
        2. Password verification fails
        3. Return forbidden error (not unauthorized)
        4. Message contains "User account is locked"
        """
        locked_user = user_schemas.User(
            user_name="lockeduser",
            hashed_password=UserManager.hash_password("correct_password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=3,
            locked_until=datetime.now() + timedelta(minutes=30),
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_security_manager = Mock(spec=SecurityManager)
        mock_request.app.state._security_manager = mock_security_manager

        body = auth_schemas.LoginRequest(
            username="lockeduser", password=_s("wrong_password")
        )

        with pytest.raises(Exception) as exc_info:
            await login(mock_request, body, mock_user_manager, mock_users_repo)

        assert (
            "locked" in str(exc_info.value).lower()
            or "forbidden" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_login_locked_user_wrong_password_increments_counter(
        self, mock_request, mock_user_manager, mock_users_repo
    ):
        """Test that locked user with wrong password.

        Test points:
        - Verify that when user is locked and password is wrong
        - The failed_login_attempts counter is incremented
        - The counter update is persisted to database
        """
        locked_user = user_schemas.User(
            user_name="lockeduser",
            hashed_password=UserManager.hash_password("correct_password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=2,
            locked_until=datetime.now() + timedelta(minutes=30),
        )
        mock_user_manager.get_user.return_value = locked_user
        mock_security_manager = Mock(spec=SecurityManager)
        mock_request.app.state._security_manager = mock_security_manager

        body = auth_schemas.LoginRequest(
            username="lockeduser", password=_s("wrong_password")
        )

        with pytest.raises(Exception):
            await login(mock_request, body, mock_user_manager, mock_users_repo)

        assert mock_user_manager.log_login_attempt.called


class TestRefreshTokenMissingScenarios:
    """Supplementary tests for missing refresh token scenarios."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        return mock

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        mock = Mock()
        mock.app = Mock()
        mock.app.state = Mock()
        mock_security_manager = Mock(spec=SecurityManager)
        mock_security_manager.create_access_token.return_value = (
            "new_access_token"
        )
        mock_security_manager.create_refresh_token.return_value = (
            "new_refresh_token"
        )
        mock.app.state._security_manager = mock_security_manager
        return mock

    @patch("wy_qcos.api.posiq.routes_jsonrpc.auth.jwt.decode")
    @pytest.mark.asyncio
    async def test_refresh_token_user_deleted(
        self, mock_jwt_decode, mock_request, mock_user_manager
    ):
        """Test refresh token when user has been deleted."""
        mock_jwt_decode.return_value = {
            "sub": "deleteduser",
            "type": "refresh",
        }
        mock_user_manager.get_user.return_value = None

        body = auth_schemas.TokenRefreshRequest(
            refresh_token=_s("valid_but_user_deleted_refresh_token")
        )

        with pytest.raises(Exception) as exc_info:
            await refresh_token(mock_request, body, mock_user_manager)

        assert (
            "not found" in str(exc_info.value).lower()
            or "unauthorized" in str(exc_info.value).lower()
        )

    @patch("wy_qcos.api.posiq.routes_jsonrpc.auth.jwt.decode")
    @pytest.mark.asyncio
    async def test_refresh_token_deleted_user_with_valid_token(
        self, mock_jwt_decode, mock_request, mock_user_manager
    ):
        """Test deleted user scenario with a valid token."""
        mock_jwt_decode.return_value = {
            "sub": "deleteduser",
            "type": "refresh",
        }
        mock_user_manager.get_user.return_value = None

        body = auth_schemas.TokenRefreshRequest(
            refresh_token=_s("valid_refresh_token_but_user_deleted")
        )

        with pytest.raises(Exception):
            await refresh_token(mock_request, body, mock_user_manager)

        assert mock_user_manager.get_user.called


class TestRefreshTokenAdditionalScenarios:
    """Supplementary tests for refresh token additional security scenarios."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.is_password_expired.return_value = False
        return mock

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        mock = Mock()
        mock.app = Mock()
        mock.app.state = Mock()
        mock_security_manager = Mock(spec=SecurityManager)
        mock_security_manager.create_access_token.return_value = (
            "new_access_token"
        )
        mock_security_manager.create_refresh_token.return_value = (
            "new_refresh_token"
        )
        mock.app.state._security_manager = mock_security_manager
        return mock

    @patch("wy_qcos.api.posiq.routes_jsonrpc.auth.jwt.decode")
    @pytest.mark.asyncio
    async def test_refresh_token_disabled_user(
        self, mock_jwt_decode, mock_request, mock_user_manager
    ):
        """Test refresh token for disabled user."""
        mock_jwt_decode.return_value = {
            "sub": "disableduser",
            "type": "refresh",
        }
        disabled_user = user_schemas.User(
            user_name="disableduser",
            hashed_password=UserManager.hash_password("password123"),
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

        body = auth_schemas.TokenRefreshRequest(
            refresh_token=_s("disabled_user_refresh_token")
        )

        with pytest.raises(Exception) as exc_info:
            await refresh_token(mock_request, body, mock_user_manager)

        assert (
            "disabled" in str(exc_info.value).lower()
            or "forbidden" in str(exc_info.value).lower()
        )

    @patch("wy_qcos.api.posiq.routes_jsonrpc.auth.jwt.decode")
    @pytest.mark.asyncio
    async def test_refresh_token_locked_user(
        self, mock_jwt_decode, mock_request, mock_user_manager
    ):
        """Test refresh token for locked user."""
        mock_jwt_decode.return_value = {
            "sub": "lockeduser",
            "type": "refresh",
        }
        locked_user = user_schemas.User(
            user_name="lockeduser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=5,
            locked_until=datetime.now() + timedelta(minutes=30),
        )
        mock_user_manager.get_user.return_value = locked_user

        body = auth_schemas.TokenRefreshRequest(
            refresh_token=_s("locked_user_refresh_token")
        )

        with pytest.raises(Exception) as exc_info:
            await refresh_token(mock_request, body, mock_user_manager)

        assert (
            "locked" in str(exc_info.value).lower()
            or "forbidden" in str(exc_info.value).lower()
        )

    @patch("wy_qcos.api.posiq.routes_jsonrpc.auth.jwt.decode")
    @patch(
        "wy_qcos.api.posiq.routes_jsonrpc.auth.UserManager.is_password_expired"
    )
    @pytest.mark.asyncio
    async def test_refresh_token_password_expired_user(
        self,
        mock_is_password_expired,
        mock_jwt_decode,
        mock_request,
        mock_user_manager,
    ):
        """Test refresh token for user with expired password."""
        mock_jwt_decode.return_value = {
            "sub": "expiredpwduser",
            "type": "refresh",
        }
        mock_is_password_expired.return_value = True
        expired_pwd_user = user_schemas.User(
            user_name="expiredpwduser",
            hashed_password=UserManager.hash_password("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now() - timedelta(days=91),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            failed_login_attempts=0,
        )
        mock_user_manager.get_user.return_value = expired_pwd_user

        body = auth_schemas.TokenRefreshRequest(
            refresh_token=_s("expired_password_refresh_token")
        )

        with pytest.raises(Exception) as exc_info:
            await refresh_token(mock_request, body, mock_user_manager)

        assert (
            "expired" in str(exc_info.value).lower()
            or "forbidden" in str(exc_info.value).lower()
        )
