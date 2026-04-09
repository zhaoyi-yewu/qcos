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

from wy_qcos.api.posiq.routes_jsonrpc.routes import all_api
from wy_qcos.api.schemas import user as schemas
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager


class TestUserManager:
    """Test cases for UserManager functionality."""

    @pytest.fixture
    def user_manager(self):
        """Create a UserManager instance with mocked dependencies."""
        # Mock the Casbin enforcer
        mock_enforcer = Mock()
        mock_enforcer.add_policy.return_value = True
        mock_enforcer.remove_policy.return_value = True
        mock_enforcer.delete_role.return_value = True
        mock_enforcer.get_permissions_for_user.return_value = []
        mock_enforcer.add_grouping_policy.return_value = True
        mock_enforcer.remove_grouping_policy.return_value = True
        mock_enforcer.delete_roles_for_user.return_value = True
        mock_enforcer.enforce.return_value = True

        with patch(
            "wy_qcos.user.permission_manager.casbin.Enforcer",
            return_value=mock_enforcer,
        ):
            manager = UserManager("model.conf", "policy.csv", all_api)
            return manager

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

    def test_validate_user_name_success(self, user_manager):
        """Test successful user name validation."""
        # Valid user name
        user_manager.validate_user_name("validuser")
        user_manager.validate_user_name("user123")
        user_manager.validate_user_name("a" * Constant.MIN_USER_LENGTH)
        user_manager.validate_user_name("a" * Constant.MAX_USER_LENGTH)

    def test_validate_user_name_too_short(self, user_manager):
        """Test user name validation with too short name."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.validate_user_name(
                "a" * (Constant.MIN_USER_LENGTH - 1)
            )

    def test_validate_user_name_too_long(self, user_manager):
        """Test user name validation with too long name."""
        with pytest.raises(ValueError, match="too long"):
            user_manager.validate_user_name(
                "a" * (Constant.MAX_USER_LENGTH + 1)
            )

    def test_validate_user_name_starts_with_underscore(self, user_manager):
        """Test user name validation with name starting with underscore."""
        with pytest.raises(ValueError, match="cannot start with underscore"):
            user_manager.validate_user_name("_invalid_user")

    def test_validate_user_name_invalid_characters(self, user_manager):
        """Test user name validation with invalid characters."""
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("user@name")
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("user.name")
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("user name")  # space
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("123user")  # starts with digit

    def test_validate_user_name_valid_formats(self, user_manager):
        """Test user name validation with various valid formats."""
        # Should allow letters, digits, hyphens, and underscores (not at start)
        user_manager.validate_user_name("valid_user")
        user_manager.validate_user_name("valid-user")
        user_manager.validate_user_name("validUser123")
        user_manager.validate_user_name("user123_test-name")

    def test_validate_password_success(self, user_manager):
        """Test successful password validation."""
        # Valid passwords
        user_manager.validate_password("validpassword")
        user_manager.validate_password("a" * Constant.MIN_PASSWORD_LENGTH)
        user_manager.validate_password("a" * Constant.MAX_PASSWORD_LENGTH)

    def test_validate_password_too_short(self, user_manager):
        """Test password validation with too short password."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.validate_password(
                "a" * (Constant.MIN_PASSWORD_LENGTH - 1)
            )

    def test_validate_password_too_long(self, user_manager):
        """Test password validation with too long password."""
        with pytest.raises(ValueError, match="too long"):
            user_manager.validate_password(
                "a" * (Constant.MAX_PASSWORD_LENGTH + 1)
            )

    def test_validate_role_name_success(self, user_manager):
        """Test successful role name validation."""
        # Valid role names
        user_manager.validate_role_name("validrole")
        user_manager.validate_role_name("role123")
        user_manager.validate_role_name("a" * Constant.MIN_ROLE_LENGTH)
        user_manager.validate_role_name("a" * Constant.MAX_ROLE_LENGTH)

    def test_validate_role_name_too_short(self, user_manager):
        """Test role name validation with too short name."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.validate_role_name(
                "a" * (Constant.MIN_ROLE_LENGTH - 1)
            )

    def test_validate_role_name_too_long(self, user_manager):
        """Test role name validation with too long name."""
        with pytest.raises(ValueError, match="too long"):
            user_manager.validate_role_name(
                "a" * (Constant.MAX_ROLE_LENGTH + 1)
            )

    def test_validate_description_success(self, user_manager):
        """Test successful description validation."""
        # Valid descriptions
        user_manager.validate_description(None)
        user_manager.validate_description("")
        user_manager.validate_description(
            "a" * Constant.MAX_DESCRIPTION_LENGTH
        )

    def test_validate_description_too_long(self, user_manager):
        """Test description validation with too long description."""
        with pytest.raises(ValueError, match="too long"):
            user_manager.validate_description(
                "a" * (Constant.MAX_DESCRIPTION_LENGTH + 1)
            )

    def test_validate_roles_success(self, user_manager):
        """Test successful roles validation."""
        # Create roles (avoid conflicts with defaults)
        user_manager.create_role(
            "testrole1",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
        )
        user_manager.create_role(
            "testrole2",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
        )

        # Valid roles
        user_manager.validate_roles(["testrole1"])
        user_manager.validate_roles(["testrole1", "testrole2"])
        user_manager.validate_roles([])

    def test_validate_roles_invalid(self, user_manager):
        """Test roles validation with invalid roles."""
        with pytest.raises(ValueError, match="does not exist"):
            user_manager.validate_roles(["nonexistent"])

    def test_validate_permissions_success(self, user_manager):
        """Test successful permissions validation."""
        # Valid permissions - use actual API paths from default policies
        user_manager.validate_permissions([])
        # Use permissions from the default policies
        default_perms = user_manager.get_default_policies(simple=True)
        if len(default_perms) >= 3:
            user_manager.validate_permissions(default_perms[:3])
        else:
            user_manager.validate_permissions(default_perms)

    def test_validate_permissions_invalid(self, user_manager):
        """Test permissions validation with invalid permissions."""
        with pytest.raises(ValueError, match="Invalid permission"):
            user_manager.validate_permissions(["invalid_permission"])

    def test_create_role_success(self, user_manager):
        """Test successful role creation."""
        role = user_manager.create_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "Test role description",
        )

        assert role.role_name == "testrole"
        assert role.permissions == [
            "/version",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        assert role.description == "Test role description"
        # roles_db is keyed by UUID, but _role_name_to_id maps name to UUID
        assert "testrole" in user_manager._role_name_to_id

    def test_create_role_duplicate(self, user_manager):
        """Test creating a role with duplicate name."""
        user_manager.create_role(
            "testrole", ["/version", "/v1/device/get_device"]
        )

        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_role(
                "testrole", ["/version", "/v1/device/get_device"]
            )

    def test_create_role_invalid_name(self, user_manager):
        """Test creating role with invalid name."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.create_role(
                "a" * (Constant.MIN_ROLE_LENGTH - 1), ["/version"]
            )

    def test_create_role_invalid_permissions(self, user_manager):
        """Test creating role with invalid permissions."""
        with pytest.raises(ValueError, match="Invalid permission"):
            user_manager.create_role("testrole2", ["invalid_permission"])

    def test_get_role_success(self, user_manager):
        """Test successful role retrieval."""
        user_manager.create_role(
            "testrole", ["/version", "/v1/device/get_device"]
        )
        role = user_manager.get_role("testrole")

        assert role is not None
        assert role.role_name == "testrole"
        assert role.permissions == ["/version", "/v1/device/get_device"]

    def test_get_role_not_found(self, user_manager):
        """Test getting non-existent role."""
        role = user_manager.get_role("nonexistent")
        assert role is None

    def test_update_role_success(self, user_manager):
        """Test successful role update."""
        user_manager.create_role(
            "testrole", ["/version"], "Original description"
        )

        updated_role = user_manager.update_role(
            "testrole",
            ["/version", "/v1/device/get_device"],
            "Updated description",
        )

        assert updated_role.role_name == "testrole"
        assert updated_role.permissions == [
            "/version",
            "/v1/device/get_device",
        ]
        assert updated_role.description == "Updated description"

    def test_update_role_not_found(self, user_manager):
        """Test updating non-existent role."""
        with pytest.raises(ValueError, match="not found"):
            user_manager.update_role("nonexistent", ["/version"])

    def test_delete_role_success(self, user_manager):
        """Test successful role deletion."""
        user_manager.create_role("testrole", ["/version"])
        role = user_manager.delete_role("testrole")

        assert role.role_name == "testrole"
        assert "testrole" not in user_manager.roles_db

    def test_delete_role_not_found(self, user_manager):
        """Test deleting non-existent role."""
        with pytest.raises(ValueError, match="not found"):
            user_manager.delete_role("nonexistent")

    def test_create_user_success(self, user_manager):
        """Test successful user creation."""
        # Use default "user" role that already exists from init_users

        user = user_manager.create_user(
            "testuser",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
            "Test user description",
        )

        assert user.user_name == "testuser"
        assert user.roles == ["user"]
        assert user.is_enabled is True
        assert user.is_locked is False
        assert user.password_expiry_days == 90
        assert user.description == "Test user description"
        # users_db is keyed by UUID, but _username_to_id maps name to UUID
        assert "testuser" in user_manager._username_to_id

    def test_create_user_duplicate(self, user_manager):
        """Test creating a user with duplicate username."""
        user_manager.create_user(
            "testuser", _s("password123"), ["user"], True, False, 90
        )

        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_user(
                "testuser", _s("password456"), ["user"], True, False, 90
            )

    def test_create_user_invalid_name(self, user_manager):
        """Test creating user with invalid username."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.create_user(
                "a" * (Constant.MIN_USER_LENGTH - 1),
                _s("password123"),
                ["user"],
                True,
                False,
                90,
            )

    def test_create_user_invalid_password(self, user_manager):
        """Test creating user with invalid password."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.create_user(
                "testuser",
                "a" * (Constant.MIN_PASSWORD_LENGTH - 1),
                ["user"],
                True,
                False,
                90,
            )

    def test_create_user_invalid_roles(self, user_manager):
        """Test creating user with invalid roles."""
        with pytest.raises(ValueError, match="does not exist"):
            user_manager.create_user(
                "testuser", _s("password123"), ["nonexistent"], True, False, 90
            )

    def test_get_user_success(self, user_manager):
        """Test successful user retrieval."""
        user_manager.create_user(
            "testuser", _s("password123"), ["user"], True, False, 90
        )
        user = user_manager.get_user("testuser")

        assert user is not None
        assert user.user_name == "testuser"
        assert user.roles == ["user"]

    def test_get_user_not_found(self, user_manager):
        """Test getting non-existent user."""
        user = user_manager.get_user("nonexistent")
        assert user is None

    def test_update_user_success(self, user_manager):
        """Test successful user update."""
        # Create user (roles already exist from init_users)
        user_manager.create_user(
            "testuser", _s("password123"), ["user"], True, False, 90
        )

        updated_user = user_manager.update_user(
            "testuser",
            ["user", "admin"],
            False,
            True,
            180,
            "Updated description",
        )

        assert updated_user.user_name == "testuser"
        assert updated_user.roles == ["user", "admin"]
        assert updated_user.is_enabled is False
        assert updated_user.is_locked is True
        assert updated_user.password_expiry_days == 180
        assert updated_user.description == "Updated description"
        assert updated_user.updated_at is not None

    def test_update_user_not_found(self, user_manager):
        """Test updating non-existent user."""
        with pytest.raises(ValueError, match="not found"):
            user_manager.update_user("nonexistent", ["user"])

    def test_delete_user_success(self, user_manager):
        """Test successful user deletion."""
        user_manager.create_user(
            "testuser", _s("password123"), ["user"], True, False, 90
        )
        user = user_manager.delete_user("testuser")

        assert user.user_name == "testuser"
        assert "testuser" not in user_manager.users_db

    def test_delete_user_not_found(self, user_manager):
        """Test deleting non-existent user."""
        with pytest.raises(ValueError, match="not found"):
            user_manager.delete_user("nonexistent")

    def test_find_users_by_role(self, user_manager):
        """Test finding users by role."""
        # Use default roles that already exist from init_users

        user_manager.create_user(
            "user1", _s("password123"), ["user"], True, False, 90
        )
        user_manager.create_user(
            "user2", _s("password123"), ["admin"], True, False, 90
        )
        user_manager.create_user(
            "user3", _s("password123"), ["user", "admin"], True, False, 90
        )

        users_with_user_role = user_manager.find_users_by_role("user")
        users_with_admin_role = user_manager.find_users_by_role("admin")

        assert "user1" in users_with_user_role
        assert "user3" in users_with_user_role
        assert "user2" in users_with_admin_role
        assert "user3" in users_with_admin_role

    def test_log_login_attempt(self, user_manager):
        """Test logging login attempts."""
        user_manager.log_login_attempt(
            "testuser", "192.168.1.1", True, user_agent="Mozilla/5.0"
        )

        assert len(user_manager.login_logs) == 1
        log = user_manager.login_logs[0]
        assert log.user_name == "testuser"
        assert log.ip_address == "192.168.1.1"
        assert log.success is True
        assert log.user_agent == "Mozilla/5.0"

    def test_get_login_logs(self, user_manager):
        """Test getting login logs."""
        # Add some logs
        user_manager.log_login_attempt(
            "user1", "192.168.1.1", True, user_agent="Mozilla/5.0"
        )
        user_manager.log_login_attempt(
            "user2", "192.168.1.2", False, user_agent="Chrome/91.0"
        )

        logs = user_manager.get_login_logs()
        assert len(logs) == 2
        assert logs[0].user_name == "user1"
        assert logs[1].user_name == "user2"

    def test_is_password_expired_false(self, user_manager, sample_user):
        """Test password expiry check when not expired."""
        # Password changed recently
        sample_user.password_changed_at = datetime.now() - timedelta(days=1)
        sample_user.password_expiry_days = 90

        assert not user_manager.is_password_expired(sample_user)

    def test_is_password_expired_true(self, user_manager, sample_user):
        """Test password expiry check when expired."""
        # Password changed 100 days ago with 90 day expiry
        sample_user.password_changed_at = datetime.now() - timedelta(days=100)
        sample_user.password_expiry_days = 90

        assert user_manager.is_password_expired(sample_user)

    def test_is_password_expired_no_expiry_date(
        self, user_manager, sample_user
    ):
        """Test password expiry check when no expiry date set."""
        sample_user.password_changed_at = None

        assert not user_manager.is_password_expired(sample_user)

    def test_hash_password(self, user_manager):
        """Test password hashing."""
        password = _s("test_password")
        hashed = user_manager.hash_password(password)

        # Hash should not be the same as plain password
        assert hashed != password
        # Should be consistent
        assert user_manager.hash_password(password) == hashed

    def test_check_password(self, user_manager):
        """Test password checking."""
        password = _s("test_password")
        hashed = user_manager.hash_password(password)

        assert user_manager.check_password(password, hashed) is True
        assert (
            user_manager.check_password(_s("wrong_password"), hashed) is False
        )

    def test_init_users(self, user_manager):
        """Test user initialization."""
        # Should create default admin and user roles
        # roles_db is keyed by UUID, but _role_name_to_id maps name to UUID
        assert "admin" in user_manager._role_name_to_id
        assert "user" in user_manager._role_name_to_id

        # Should create default admin user
        # users_db is keyed by UUID, but _username_to_id maps name to UUID
        assert "admin" in user_manager._username_to_id

        admin_user = user_manager.get_user("admin")
        assert admin_user is not None
        assert admin_user.user_name == "admin"
        assert "admin" in admin_user.roles

    def test_get_default_policies(self, user_manager):
        """Test getting default policies."""
        # Should return policies for different roles
        admin_policies = user_manager.get_default_policies("admin")
        user_policies = user_manager.get_default_policies("user")
        all_policies = user_manager.get_default_policies()

        assert isinstance(admin_policies, list)
        assert isinstance(user_policies, list)
        assert isinstance(all_policies, list)

        # Admin policies should include wildcard permissions
        admin_permissions = [p[1] for p in admin_policies]
        assert "*" in admin_permissions

    def test_get_permissions_list(self, user_manager):
        """Test getting permissions list from policies."""
        policies = [
            ("role1", "/api/test", "call"),
            ("role2", "/api/other", "call"),
        ]
        permissions = user_manager.get_permissions_list(policies)

        assert permissions == ["/api/test", "/api/other"]
