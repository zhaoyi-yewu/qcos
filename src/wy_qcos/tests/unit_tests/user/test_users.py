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

from wy_qcos.api import schemas
from wy_qcos.common.library import _s
from wy_qcos.common.constant import Constant
from wy_qcos.api.posiq.routes_jsonrpc.user import (
    change_password,
    create_user,
    delete_user,
    get_user,
    get_user_management_status,
    get_users,
    initialize_user_management,
    is_password_expired,
    lock_user,
    update_user,
)


class TestUsers:
    """Test cases for user management functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment before each test."""
        # Initialize user management for each test
        initialize_user_management()
        # Initialize password variable
        self.password = _s("password123")

    def test_get_user_management_status(self):
        """Test getting user management status."""
        response = get_user_management_status()

        assert isinstance(response, schemas.GetUserManagementStatusResponse)
        assert response.enabled is True
        assert response.password_expiry_days == 90
        assert response.max_login_attempts == 5
        assert response.lockout_duration_minutes == 30

    def test_create_user_success(self):
        """Test successful user creation."""
        request = schemas.CreateUserRequest(
            user_name="testuser",
            password=self.password,
            roles=["user"],
            is_enabled=True,
        )

        response = create_user(request)

        assert isinstance(response, schemas.CreateUserResponse)
        assert response.user_name == "testuser"
        assert response.roles == ["user"]
        assert response.is_enabled is True
        assert response.created_at is not None

    def test_create_user_duplicate(self):
        """Test creating a user with duplicate username."""
        request = schemas.CreateUserRequest(
            user_name="admin", password=self.password, roles=["admin"]
        )

        with pytest.raises(Exception):  # Should raise conflict error
            create_user(request)

    def test_create_user_invalid_name(self):
        """Test creating user with invalid username."""
        # Test validation error for username with space
        with pytest.raises(Exception):  # Should raise validation error
            schemas.CreateUserRequest(
                user_name="test user",  # Contains space
                password=self.password,
                roles=["user"],
            )

    def test_get_user_success(self):
        """Test successful user retrieval."""
        # First create a user with unique name
        create_request = schemas.CreateUserRequest(
            user_name="testuser1", password=self.password, roles=["user"]
        )
        create_user(create_request)

        # Then retrieve it
        request = schemas.GetUserRequest(user_name="testuser1")
        response = get_user(request)

        assert isinstance(response, schemas.GetUserResponse)
        assert response.user_name == "testuser1"
        assert response.roles == ["user"]
        assert response.is_enabled is True
        assert response.is_locked is False

    def test_get_user_not_found(self):
        """Test getting non-existent user."""
        request = schemas.GetUserRequest(user_name="nonexistent")

        with pytest.raises(Exception):  # Should raise not found error
            get_user(request)

    def test_update_user_success(self):
        """Test successful user update."""
        # Create user first
        create_request = schemas.CreateUserRequest(
            user_name="testuser2", password=self.password, roles=["user"]
        )
        create_user(create_request)

        # Update user
        update_request = schemas.UpdateUserRequest(
            user_name="testuser2", roles=["admin", "user"], is_enabled=False
        )
        response = update_user(update_request)

        assert isinstance(response, schemas.UpdateUserResponse)
        assert response.user_name == "testuser2"
        assert response.roles == ["admin", "user"]
        assert response.is_enabled is False
        assert response.updated_at is not None

    def test_update_user_not_found(self):
        """Test updating non-existent user."""
        update_request = schemas.UpdateUserRequest(
            user_name="nonexistent", roles=["admin"]
        )

        with pytest.raises(Exception):  # Should raise not found error
            update_user(update_request)

    def test_delete_user_success(self):
        """Test successful user deletion."""
        # Create user first
        create_request = schemas.CreateUserRequest(
            user_name="testuser3", password=self.password, roles=["user"]
        )
        create_user(create_request)

        # Delete user
        delete_request = schemas.DeleteUserRequest(user_name="testuser3")
        response = delete_user(delete_request)

        assert isinstance(response, schemas.DeleteUserResponse)
        assert response.user_name == "testuser3"
        assert response.deleted_at is not None

    def test_delete_user_not_found(self):
        """Test deleting non-existent user."""
        delete_request = schemas.DeleteUserRequest(user_name="nonexistent")

        with pytest.raises(Exception):  # Should raise not found error
            delete_user(delete_request)

    def test_lock_user_success(self):
        """Test successful user lock/unlock."""
        # Create user first
        create_request = schemas.CreateUserRequest(
            user_name="testuser3", password=self.password, roles=["user"]
        )
        create_user(create_request)

        # Lock user
        lock_request = schemas.LockUserRequest(
            user_name="testuser3", action="lock"
        )
        response = lock_user(lock_request)

        assert isinstance(response, schemas.LockUserResponse)
        assert response.user_name == "testuser3"
        assert response.is_locked is True
        assert response.locked_until is not None
        assert "locked" in response.message.lower()

    def test_unlock_user_success(self):
        """Test successful user unlock."""
        # Create and lock user first
        create_request = schemas.CreateUserRequest(
            user_name="testuser4", password=self.password, roles=["user"]
        )
        create_user(create_request)

        lock_request = schemas.LockUserRequest(
            user_name="testuser4", action="lock"
        )
        lock_user(lock_request)

        # Unlock user
        unlock_request = schemas.LockUserRequest(
            user_name="testuser4", action="unlock"
        )
        response = lock_user(unlock_request)

        assert isinstance(response, schemas.LockUserResponse)
        assert response.user_name == "testuser4"
        assert response.is_locked is False
        assert response.locked_until is None
        assert "unlocked" in response.message.lower()

    def test_get_users(self):
        """Test getting all users."""
        # Create test users
        create_request1 = schemas.CreateUserRequest(
            user_name="user1", password=self.password, roles=["user"]
        )
        create_request2 = schemas.CreateUserRequest(
            user_name="user2", password=self.password, roles=["admin"]
        )
        create_user(create_request1)
        create_user(create_request2)

        response = get_users()

        # Should return a dictionary of users
        assert isinstance(response, dict)
        assert len(response) >= 2  # At least admin + 2 test users

        # Check that our test users are in the response
        user_names = list(response.keys())
        assert "user1" in user_names
        assert "user2" in user_names

    def test_password_expiry_check(self):
        """Test password expiry checking."""
        # Create user with password expiry
        create_request = schemas.CreateUserRequest(
            user_name="testuser5",
            password=self.password,
            roles=["user"],
            password_expiry_days=7,
        )
        create_user(create_request)

        # Get user and check password expiry
        request = schemas.GetUserRequest(user_name="testuser5")
        user = get_user(request)

        # Password should not be expired initially
        user_obj = schemas.user.User(
            user_name=user.user_name,
            password_hash=_s("test_password_hash"),
            roles=user.roles,
            password_expiry_days=7,
            password_changed_at=datetime.fromisoformat(
                user.password_changed_at
            ),
        )

        assert not is_password_expired(user_obj)

        # Simulate old password change
        user_obj.password_changed_at = datetime.now() - timedelta(days=10)
        assert is_password_expired(user_obj)

    def test_user_validation(self):
        """Test user input validation."""
        # Test short username
        with pytest.raises(Exception):
            create_request = schemas.CreateUserRequest(
                user_name="a" * (Constant.MIN_USER_LENGTH - 1),  # Too short
                password=self.password,
                roles=["user"],
            )
            create_user(create_request)

        # Test long username
        with pytest.raises(Exception):
            create_request = schemas.CreateUserRequest(
                user_name="a" * (Constant.MAX_USER_LENGTH + 1),  # Too long
                password=self.password,
                roles=["user"],
            )
            create_user(create_request)

        # Test short password
        with pytest.raises(Exception):
            short_password = _s("a" * (Constant.MIN_PASSWORD_LENGTH - 1))
            create_request = schemas.CreateUserRequest(
                user_name="testuser",
                password=short_password,  # Too short
                roles=["user"],
            )
            create_user(create_request)

        # Test long password
        with pytest.raises(Exception):
            long_password = _s("a" * (Constant.MAX_PASSWORD_LENGTH + 1))
            create_request = schemas.CreateUserRequest(
                user_name="testuser",
                password=long_password,  # Too long
                roles=["user"],
            )
            create_user(create_request)

        # Test long description
        with pytest.raises(Exception):
            long_description = "a" * (Constant.MAX_DESCRIPTION_LENGTH + 1)
            create_request = schemas.CreateUserRequest(
                user_name="testuser",
                password=self.password,
                roles=["user"],
                description=long_description,  # Too long
            )
            create_user(create_request)

    def test_change_password_validation(self):
        """Test password change validation."""
        # Create user first
        create_request = schemas.CreateUserRequest(
            user_name="testuser6",
            password=self.password,
            roles=["user"],
        )
        create_user(create_request)

        # Test short new password
        with pytest.raises(Exception):
            short_password = _s("a" * (Constant.MIN_PASSWORD_LENGTH - 1))
            change_request = schemas.ChangePasswordRequest(
                user_name="testuser6",
                old_password=self.password,
                new_password=short_password,  # Too short
            )
            change_password(change_request)

        # Test long new password
        with pytest.raises(Exception):
            long_password = _s("a" * (Constant.MAX_PASSWORD_LENGTH + 1))
            change_request = schemas.ChangePasswordRequest(
                user_name="testuser6",
                old_password=self.password,
                new_password=long_password,  # Too long
            )
            change_password(change_request)
