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
# ---------------------------------------------------------------------

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from jose import JWTError
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from wy_qcos.api.schemas import user as schemas
from wy_qcos.common.library import _s
from wy_qcos.user.security_manager import SecurityManager
from wy_qcos.user.user_manager import UserManager


class TestSecurityManager:
    """Test cases for SecurityManager functionality."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        # Ensure get_user returns None by default (not a Mock object)
        mock.get_user.return_value = None
        return mock

    @pytest.fixture
    def security_manager(self, mock_user_manager):
        """Create a SecurityManager instance with mocked dependencies."""
        return SecurityManager(mock_user_manager)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return schemas.User(
            user_name="testuser",
            password_hash=_s("hashed_password"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            last_login=None,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            locked_until=None,
            description="Test user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            failed_login_attempts=0,
        )

    def test_verify_password_success(self, security_manager):
        """Test successful password verification."""
        plain_password = _s("test_password")
        hashed_password = security_manager.get_password_hash(plain_password)

        result = security_manager.verify_password(
            plain_password, hashed_password
        )
        assert result is True

    def test_verify_password_failure(self, security_manager):
        """Test password verification failure."""
        plain_password = _s("test_password")
        wrong_password = _s("wrong_password")
        hashed_password = security_manager.get_password_hash(plain_password)

        result = security_manager.verify_password(
            wrong_password, hashed_password
        )
        assert result is False

    def test_get_password_hash(self, security_manager):
        """Test password hashing."""
        password = _s("test_password")
        hashed = security_manager.get_password_hash(password)

        # Hash should not be the same as plain password
        assert hashed != password
        # Should be able to verify the hash
        assert security_manager.verify_password(password, hashed)

    def test_check_account_lockout_no_attempts(self, security_manager):
        """Test account lockout check with no failed attempts."""
        result = security_manager.check_account_lockout("testuser")
        assert result is False

    def test_check_account_lockout_under_limit(self, security_manager):
        """Test account lockout check under the limit."""
        user_name = "testuser"
        # Add 4 failed attempts (under the limit of 5)
        security_manager.failed_attempts[user_name] = [
            datetime.now() - timedelta(minutes=i) for i in range(4)
        ]

        result = security_manager.check_account_lockout(user_name)
        assert result is False

    def test_check_account_lockout_over_limit_within_lockout_period(
        self, security_manager
    ):
        """Test account lockout check over the limit within lockout period."""
        user_name = "testuser"
        # Add 5 failed attempts within the last minute
        security_manager.failed_attempts[user_name] = [
            datetime.now() - timedelta(minutes=i) for i in range(5)
        ]

        result = security_manager.check_account_lockout(user_name)
        assert result is True

    def test_check_account_lockout_over_limit_after_lockout_period(
        self, security_manager
    ):
        """Test account lockout check over limit after lockout period."""
        user_name = "testuser"
        # Add 5 failed attempts from 30 min ago (beyond 15 min lockout)
        security_manager.failed_attempts[user_name] = [
            datetime.now() - timedelta(minutes=30 + i) for i in range(5)
        ]

        result = security_manager.check_account_lockout(user_name)
        assert result is False
        # Failed attempts should be cleared
        assert len(security_manager.failed_attempts[user_name]) == 0

    def test_record_failed_attempt(self, security_manager):
        """Test recording a failed login attempt."""
        user_name = "testuser"

        security_manager.record_failed_attempt(user_name)

        assert user_name in security_manager.failed_attempts
        assert len(security_manager.failed_attempts[user_name]) == 1
        assert isinstance(
            security_manager.failed_attempts[user_name][0], datetime
        )

    def test_record_successful_login(
        self, security_manager, mock_user_manager
    ):
        """Test recording a successful login."""
        user_name = "testuser"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        # Add some failed attempts first
        security_manager.failed_attempts[user_name] = [
            datetime.now() - timedelta(minutes=i) for i in range(3)
        ]

        security_manager.record_successful_login(
            user_name, ip_address, user_agent
        )

        # Failed attempts should be cleared
        assert len(security_manager.failed_attempts[user_name]) == 0
        # Login should be logged
        mock_user_manager.log_login_attempt.assert_called_once_with(
            user_name, ip_address, True, user_agent=user_agent
        )

    @patch("wy_qcos.user.security_manager.jwt.encode")
    def test_create_access_token(self, mock_encode, security_manager):
        """Test creating access token."""
        mock_encode.return_value = "mocked_token"
        data = {"sub": "testuser"}

        result = security_manager.create_access_token(data)

        assert result == "mocked_token"
        mock_encode.assert_called_once()

    @patch("wy_qcos.user.security_manager.jwt.encode")
    def test_create_refresh_token(self, mock_encode, security_manager):
        """Test creating refresh token."""
        mock_encode.return_value = "mocked_refresh_token"
        data = {"sub": "testuser"}

        result = security_manager.create_refresh_token(data)

        assert result == "mocked_refresh_token"
        mock_encode.assert_called_once()
        # Verify that type=refresh was added
        call_args = mock_encode.call_args[0][0]
        assert call_args["type"] == "refresh"

    @patch("wy_qcos.user.security_manager.jwt.decode")
    def test_verify_token_success(self, mock_decode, security_manager):
        """Test successful token verification."""
        expected_exp = datetime.now().timestamp() + 3600
        mock_decode.return_value = {"sub": "testuser", "exp": expected_exp}

        result = security_manager.verify_token("valid_token")

        assert result == {"sub": "testuser", "exp": expected_exp}
        mock_decode.assert_called_once()

    @patch("wy_qcos.user.security_manager.jwt.decode")
    def test_verify_token_failure(self, mock_decode, security_manager):
        """Test token verification failure."""
        mock_decode.side_effect = JWTError("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            security_manager.verify_token("invalid_token")

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    def test_authenticate_user_account_locked(
        self, security_manager, mock_user_manager
    ):
        """Test authentication when account is locked."""
        user_name = "testuser"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        # Simulate account lockout
        security_manager.failed_attempts[user_name] = [
            datetime.now() - timedelta(minutes=i) for i in range(5)
        ]

        with pytest.raises(HTTPException) as exc_info:
            security_manager.authenticate_user(
                user_name, "password", ip_address, user_agent
            )

        assert exc_info.value.status_code == 423
        assert "Account is temporarily locked" in str(exc_info.value.detail)

    def test_authenticate_user_not_found(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test authentication with non-existent user."""
        user_name = "nonexistent"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        mock_user_manager.get_user.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            security_manager.authenticate_user(
                user_name, "password", ip_address, user_agent
            )

        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in str(exc_info.value.detail)
        # Failed attempt should be recorded
        assert len(security_manager.failed_attempts[user_name]) == 1

    def test_authenticate_user_disabled(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test authentication with disabled user."""
        user_name = "testuser"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        # User is disabled
        sample_user.is_enabled = False
        mock_user_manager.get_user.return_value = sample_user

        with pytest.raises(HTTPException) as exc_info:
            security_manager.authenticate_user(
                user_name, "password", ip_address, user_agent
            )

        assert exc_info.value.status_code == 403
        assert "Account is disabled" in str(exc_info.value.detail)
        # Failed attempt should be recorded
        assert len(security_manager.failed_attempts[user_name]) == 1

    def test_authenticate_user_locked(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test authentication with locked user."""
        user_name = "testuser"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        # User is locked with future lockout time
        sample_user.is_locked = True
        sample_user.locked_until = datetime.now() + timedelta(minutes=10)
        mock_user_manager.get_user.return_value = sample_user

        with pytest.raises(HTTPException) as exc_info:
            security_manager.authenticate_user(
                user_name, "password", ip_address, user_agent
            )

        assert exc_info.value.status_code == 423
        assert "Account is locked" in str(exc_info.value.detail)
        # Failed attempt should be recorded
        assert len(security_manager.failed_attempts[user_name]) == 1

    def test_authenticate_user_invalid_password(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test authentication with invalid password."""
        user_name = "testuser"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        mock_user_manager.get_user.return_value = sample_user
        # Mock SecurityManager's own verify_password method
        with patch.object(
            security_manager, "verify_password", return_value=False
        ):
            with pytest.raises(HTTPException) as exc_info:
                security_manager.authenticate_user(
                    user_name, "wrong_password", ip_address, user_agent
                )

        assert exc_info.value.status_code == 401
        assert "Incorrect username or password" in str(exc_info.value.detail)
        # Failed attempt should be recorded
        assert len(security_manager.failed_attempts[user_name]) == 1

    def test_authenticate_user_password_expired(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test authentication with expired password."""
        user_name = "testuser"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        # Set password 100 days ago (expired if 90 days)
        sample_user.password_changed_at = datetime.now() - timedelta(days=100)
        mock_user_manager.get_user.return_value = sample_user
        # Mock SecurityManager's own verify_password method
        with patch.object(
            security_manager, "verify_password", return_value=True
        ):
            with pytest.raises(HTTPException) as exc_info:
                security_manager.authenticate_user(
                    user_name, "password", ip_address, user_agent
                )

        assert exc_info.value.status_code == 403
        assert "Password has expired" in str(exc_info.value.detail)

    def test_authenticate_user_success(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test successful authentication."""
        user_name = "testuser"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        mock_user_manager.get_user.return_value = sample_user
        # Mock SecurityManager's own verify_password method
        with patch.object(
            security_manager, "verify_password", return_value=True
        ):
            result = security_manager.authenticate_user(
                user_name, "password", ip_address, user_agent
            )

        assert result == sample_user
        assert result.last_login is not None
        assert result.failed_login_attempts == 0
        assert result.is_locked is False
        assert result.locked_until is None
        # Login should be logged
        mock_user_manager.log_login_attempt.assert_called_once_with(
            user_name, ip_address, True, user_agent=user_agent
        )

    def test_check_permissions_direct(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test permission checking with direct user permissions."""
        user_name = "testuser"
        resource = "/api/test"
        action = "call"

        # Mock that user has direct permission
        mock_user_manager.perms_check_enforce.return_value = True

        result = security_manager.check_permissions(
            sample_user, resource, action
        )

        assert result is True
        mock_user_manager.perms_check_enforce.assert_called_once_with(
            user_name, resource, action
        )

    def test_check_permissions_via_role(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test permission checking via role permissions."""
        resource = "/api/test"
        action = "call"

        # Mock that user doesn't have direct permission but role does
        mock_user_manager.perms_check_enforce.side_effect = [False, True]

        result = security_manager.check_permissions(
            sample_user, resource, action
        )

        assert result is True
        assert mock_user_manager.perms_check_enforce.call_count == 2

    def test_check_permissions_no_permissions(
        self, security_manager, mock_user_manager, sample_user
    ):
        """Test permission checking with no permissions."""
        resource = "/api/test"
        action = "call"

        # Mock that neither user nor roles have permission
        mock_user_manager.perms_check_enforce.return_value = False

        result = security_manager.check_permissions(
            sample_user, resource, action
        )

        assert result is False
        assert (
            mock_user_manager.perms_check_enforce.call_count == 2
        )  # User + role check

    def test_get_current_user_no_credentials(self, security_manager):
        """Test getting current user with no credentials."""
        with pytest.raises(HTTPException) as exc_info:
            security_manager.get_current_user(None)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in str(exc_info.value.detail)

    def test_get_current_user_invalid_token(self, security_manager):
        """Test getting current user with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            security_manager.get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    def test_get_current_user_user_not_found(
        self, security_manager, mock_user_manager
    ):
        """Test getting current user when user is not found."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        # Ensure get_user returns None for nonexistent user
        mock_user_manager.get_user.return_value = None

        with patch.object(
            security_manager,
            "verify_token",
            return_value={"sub": "nonexistent"},
        ):
            with pytest.raises(HTTPException) as exc_info:
                security_manager.get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "User not found" in str(exc_info.value.detail)

    def test_get_current_active_user_inactive(
        self, security_manager, sample_user
    ):
        """Test getting current active user when user is inactive."""
        sample_user.is_enabled = False

        with pytest.raises(HTTPException) as exc_info:
            security_manager.get_current_active_user(sample_user)

        assert exc_info.value.status_code == 400
        assert "Inactive user" in str(exc_info.value.detail)

    def test_get_current_active_user_success(
        self, security_manager, sample_user
    ):
        """Test successful retrieval of current active user."""
        result = security_manager.get_current_active_user(sample_user)

        assert result == sample_user
