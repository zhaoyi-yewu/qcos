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
import jwt
import logging
from unittest.mock import patch, Mock
from datetime import datetime

from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    auth,
    auth_virt,
    auth_user,
    decode_jwt_token,
    get_current_user_from_token,
    get_user_manager,
    JWT_AUTH_SECRET_KEY,
    JWT_AUTH_ALGORITHM,
)
from wy_qcos.common.library import Library, _s
from wy_qcos.common.constant import Constant
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.user.user_manager import UserManager

# Import Constant for JWT audience
JWT_AUDIENCE = Constant.JWT_AUTH_AUDIENCE

# Suppress warning logs during tests (expected warnings for invalid tokens)
logging.getLogger(
    "wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication"
).setLevel(logging.ERROR)


class TestDecodeJwtToken:
    """Test cases for decode_jwt_token function."""

    def test_decode_valid_token(self):
        """Test decoding a valid JWT token."""
        payload = {
            "sub": "user-uuid-123",
            "jti": "token-jti-456",
            "exp": datetime.now().timestamp() + 3600,
            "aud": JWT_AUDIENCE,  # Add required audience claim
        }
        token = jwt.encode(
            payload, JWT_AUTH_SECRET_KEY, algorithm=JWT_AUTH_ALGORITHM
        )

        result = decode_jwt_token(token)

        assert result is not None
        assert result["sub"] == "user-uuid-123"
        assert result["jti"] == "token-jti-456"

    def test_decode_expired_token(self):
        """Test decoding an expired JWT token."""
        payload = {
            "sub": "user-uuid-123",
            "jti": "token-jti-456",
            "exp": datetime.now().timestamp() - 3600,  # Expired 1 hour ago
        }
        token = jwt.encode(
            payload, JWT_AUTH_SECRET_KEY, algorithm=JWT_AUTH_ALGORITHM
        )

        result = decode_jwt_token(token)

        assert result is None

    def test_decode_invalid_token(self):
        """Test decoding an invalid JWT token."""
        token = _s("invalid.jwt.token")

        result = decode_jwt_token(token)

        assert result is None

    def test_decode_token_with_wrong_secret(self):
        """Test decoding a token with wrong secret."""
        payload = {
            "sub": "user-uuid-123",
            "exp": datetime.now().timestamp() + 3600,
        }
        token = jwt.encode(
            payload, "wrong_secret", algorithm=JWT_AUTH_ALGORITHM
        )

        result = decode_jwt_token(token)

        assert result is None


class TestGetCurrentUserFromToken:
    """Test cases for get_current_user_from_token function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.is_blacklisted.return_value = False
        return mock

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return user_schemas.User(
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

    def test_no_token(self, mock_user_manager):
        """Test with no token provided."""
        result = get_current_user_from_token(None, mock_user_manager)
        assert result is None

    def test_valid_token_with_valid_user(self, mock_user_manager, sample_user):
        """Test with valid token and valid user."""
        # Create a valid token
        payload = {
            "sub": "user-uuid-123",
            "jti": "token-jti-456",
            "exp": datetime.now().timestamp() + 3600,
            "aud": JWT_AUDIENCE,  # Add required audience claim
        }
        token = jwt.encode(
            payload, JWT_AUTH_SECRET_KEY, algorithm=JWT_AUTH_ALGORITHM
        )

        mock_user_manager.get_user_by_id.return_value = sample_user
        mock_user_manager.is_blacklisted.return_value = False

        result = get_current_user_from_token(token, mock_user_manager)

        assert result is not None
        assert result.user_name == "testuser"
        mock_user_manager.get_user_by_id.assert_called_once_with(
            "user-uuid-123"
        )

    def test_token_with_blacklisted_jti(self, mock_user_manager):
        """Test with blacklisted token JTI."""
        payload = {
            "sub": "user-uuid-123",
            "jti": "blacklisted-jti",
            "exp": datetime.now().timestamp() + 3600,
        }
        token = jwt.encode(
            payload, JWT_AUTH_SECRET_KEY, algorithm=JWT_AUTH_ALGORITHM
        )

        mock_user_manager.is_blacklisted.return_value = True

        result = get_current_user_from_token(token, mock_user_manager)

        assert result is None

    def test_token_with_disabled_user(self, mock_user_manager):
        """Test with token for disabled user."""
        payload = {
            "sub": "user-uuid-123",
            "jti": "token-jti-456",
            "exp": datetime.now().timestamp() + 3600,
        }
        token = jwt.encode(
            payload, JWT_AUTH_SECRET_KEY, algorithm=JWT_AUTH_ALGORITHM
        )

        disabled_user = user_schemas.User(
            user_name="disableduser",
            password_hash=_s("hashed_password"),
            roles=["user"],
            is_enabled=False,  # Disabled
            is_locked=False,
            last_login=None,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            locked_until=None,
            description="Disabled user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            failed_login_attempts=0,
        )

        mock_user_manager.get_user_by_id.return_value = disabled_user
        mock_user_manager.is_blacklisted.return_value = False

        result = get_current_user_from_token(token, mock_user_manager)

        assert result is None

    def test_token_with_nonexistent_user(self, mock_user_manager):
        """Test with token for non-existent user."""
        payload = {
            "sub": "nonexistent-uuid",
            "jti": "token-jti-456",
            "exp": datetime.now().timestamp() + 3600,
        }
        token = jwt.encode(
            payload, JWT_AUTH_SECRET_KEY, algorithm=JWT_AUTH_ALGORITHM
        )

        mock_user_manager.get_user_by_id.return_value = None
        mock_user_manager.is_blacklisted.return_value = False

        result = get_current_user_from_token(token, mock_user_manager)

        assert result is None


class TestAuthVirt:
    """Test cases for auth_virt function."""

    @patch.object(Library, "decrypt_virtual_instance_id")
    def test_auth_virt_success(self, mock_decrypt):
        """Test successful virtual instance authentication."""
        mock_decrypt.return_value = (
            True,
            None,
            ["device1", "device2"],
            "instance-123",
        )

        result = auth_virt("encrypted-instance-id")

        assert result is not None
        assert result["device_names"] == ["device1", "device2"]
        assert result["instance_id"] == "instance-123"

    @patch.object(Library, "decrypt_virtual_instance_id")
    def test_auth_virt_admin_user(self, mock_decrypt):
        """Test virtual instance authentication for admin user."""
        mock_decrypt.return_value = (
            True,
            None,
            ["all"],
            "all",
        )

        result = auth_virt("admin-encrypted-instance-id")

        assert result is None  # Admin user returns None

    def test_auth_virt_no_instance_id(self):
        """Test virtual instance authentication with no instance ID."""
        with pytest.raises(Exception):  # Should raise unauthorized error
            auth_virt(None)

    @patch.object(Library, "decrypt_virtual_instance_id")
    def test_auth_virt_decryption_failure(self, mock_decrypt):
        """Test virtual instance authentication with decryption failure."""
        mock_decrypt.return_value = (
            False,
            "Decryption error",
            [],
            None,
        )

        with pytest.raises(Exception):  # Should raise unauthorized error
            auth_virt("invalid-encrypted-instance-id")


class TestAuthUser:
    """Test cases for auth_user function."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        mock = Mock()
        mock.url = Mock()
        mock.url.path = "/v1/test/resource"
        return mock

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.perms_check_enforce.return_value = True
        return mock

    def test_auth_user_success(self, mock_request, mock_user_manager):
        """Test successful user authentication with valid permissions."""
        auth_data = {
            "user_id": "testuser",
            "roles": ["user", "admin"],
            "auth_method": "jwt",
        }

        result = auth_user(mock_request, auth_data, mock_user_manager)

        assert result is not None
        assert result == auth_data
        mock_user_manager.perms_check_enforce.assert_called()

    def test_auth_user_no_auth_data(self, mock_request, mock_user_manager):
        """Test user authentication with no auth data."""
        with pytest.raises(Exception):  # Should raise unauthorized error
            auth_user(mock_request, None, mock_user_manager)

    def test_auth_user_no_roles(self, mock_request, mock_user_manager):
        """Test user authentication with no roles."""
        auth_data = {
            "user_id": "testuser",
            "roles": [],
            "auth_method": "jwt",
        }

        with pytest.raises(Exception):  # Should raise forbidden error
            auth_user(mock_request, auth_data, mock_user_manager)

    def test_auth_user_insufficient_permissions(
        self, mock_request, mock_user_manager
    ):
        """Test user authentication with insufficient permissions."""
        auth_data = {
            "user_id": "testuser",
            "roles": ["user"],
            "auth_method": "jwt",
        }

        mock_user_manager.perms_check_enforce.return_value = False

        with pytest.raises(Exception):  # Should raise forbidden error
            auth_user(mock_request, auth_data, mock_user_manager)


class TestGetUserManager:
    """Test cases for get_user_manager function."""

    def test_get_user_manager(self):
        """Test getting user manager from request."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_user_manager = Mock(spec=UserManager)
        mock_request.app.state._user_manager = mock_user_manager

        result = get_user_manager(mock_request)

        assert result == mock_user_manager


class TestAuth:
    """Test cases for main auth function."""

    @patch.object(Library, "decrypt_virtual_instance_id")
    @patch(
        "wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication.Config"
    )
    @pytest.mark.asyncio
    @pytest.mark.smoke
    async def test_auth_virt_mode(
        self, mock_config, mock_decrypt_virtual_instance_id
    ):
        """Test authentication in virtual instance mode."""
        mock_config.ENABLE_VIRT = True
        mock_decrypt_virtual_instance_id.return_value = (
            True,
            None,
            ["dummy", "tiangong100"],
            "f5840120bca448628cad4d990b29d673",
        )
        auth_data = await auth("test")
        assert auth_data["device_names"] == ["dummy", "tiangong100"]
        assert auth_data["instance_id"] == "f5840120bca448628cad4d990b29d673"
