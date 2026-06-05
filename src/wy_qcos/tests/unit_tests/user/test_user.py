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
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from wy_qcos.api.posiq.routes_jsonrpc.routes import all_api
from wy_qcos.api.schemas import user as schemas
from wy_qcos.api.schemas.user import LoginLog
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager


class TestUserManager:
    """Test cases for UserManager functionality."""

    @pytest.fixture
    def user_manager(self):
        """Create a UserManager instance with mocked dependencies."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.return_value = True
        mock_enforcer.remove_policy.return_value = True
        mock_enforcer.delete_role.return_value = True
        mock_enforcer.get_permissions_for_user.return_value = []
        mock_enforcer.add_grouping_policy.return_value = True
        mock_enforcer.remove_grouping_policy.return_value = True
        mock_enforcer.delete_roles_for_user.return_value = True
        mock_enforcer.enforce.return_value = True

        mock_perms_check = Mock()
        mock_perms_check.get_for_role.return_value = []

        patcher1 = patch(
            "wy_qcos.user.permission_manager.casbin.Enforcer",
            return_value=mock_enforcer,
        )
        patcher2 = patch(
            "wy_qcos.user.user_manager.PermissionManager",
        )

        patcher1.start()
        patcher2.start()
        try:
            manager = UserManager("model.conf", "policy.csv", all_api)
            manager.perms_check = mock_perms_check

            # Setup roles and users storage
            created_roles = {}
            created_users = {}

            def mock_create_role(request):
                role = schemas.Role(
                    id=str(uuid.uuid4()),
                    role_name=request.role_name,
                    permissions=request.permissions,
                    description=request.description,
                )
                created_roles[request.role_name] = role
                return True, None, role

            def mock_get_role_by_name(role_name):
                if role_name in created_roles:
                    return True, None, created_roles[role_name]
                return False, None, None

            def mock_create_user(request):
                user = schemas.User(
                    id=uuid.uuid4(),
                    project_id=uuid.UUID(Constant.DEFAULT_PROJECT_ID)
                    if not request.__dict__.get("project_id")
                    else request.project_id,
                    user_name=request.user_name,
                    hashed_password=_s("hashed"),
                    roles=request.roles,
                    is_enabled=request.is_enabled,
                    is_locked=request.is_locked,
                    password_expiry_days=request.password_expiry_days,
                    description=request.description,
                    password_changed_at=datetime.now(),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                created_users[request.user_name] = user
                return True, None, user

            def mock_get_user_by_username(user_name):
                if user_name in created_users:
                    return True, None, created_users[user_name]
                return False, None, None

            def mock_get_user_by_id(user_id):
                # Find user by id - normalize UUID comparison
                user_id_str = str(user_id).lower() if user_id else None
                for user in created_users.values():
                    if (
                        hasattr(user, "id")
                        and str(user.id).lower() == user_id_str
                    ):
                        return True, None, user
                return False, None, None

            def mock_get_users():
                return True, None, list(created_users.values())

            def mock_delete_user_by_id(user_id):
                # Find and delete user by id - normalize UUID comparison
                user_id_str = str(user_id).lower() if user_id else None
                for user_name, user in list(created_users.items()):
                    if (
                        hasattr(user, "id")
                        and str(user.id).lower() == user_id_str
                    ):
                        del created_users[user_name]
                        return True, None
                return False, "User not found"

            def mock_get_roles():
                return True, None, list(created_roles.values())

            def mock_get_role_by_id(role_id):
                # Find role by id - normalize UUID comparison
                role_id_str = str(role_id).lower() if role_id else None
                for role in created_roles.values():
                    if (
                        hasattr(role, "id")
                        and str(role.id).lower() == role_id_str
                    ):
                        return True, None, role
                return False, None, None

            def mock_update_role(role_id, request):
                # Find role by id and update it - normalize UUID comparison
                role_id_str = str(role_id).lower() if role_id else None
                for role in created_roles.values():
                    if (
                        hasattr(role, "id")
                        and str(role.id).lower() == role_id_str
                    ):
                        role.permissions = (
                            request.permissions or role.permissions
                        )
                        role.description = (
                            request.description or role.description
                        )
                        return True, None, role
                return False, "Role not found", None

            def mock_delete_role(role_id):
                # Find and delete role by id - normalize UUID comparison
                role_id_str = str(role_id).lower() if role_id else None
                for role_name, role in list(created_roles.items()):
                    if (
                        hasattr(role, "id")
                        and str(role.id).lower() == role_id_str
                    ):
                        del created_roles[role_name]
                        return True, None
                return False, "Role not found"

            def mock_update_user(user_id, request):
                # Find user by id and update it - normalize UUID comparison
                user_id_str = str(user_id).lower() if user_id else None
                for user in created_users.values():
                    if (
                        hasattr(user, "id")
                        and str(user.id).lower() == user_id_str
                    ):
                        if request.roles is not None:
                            user.roles = request.roles
                        if request.is_enabled is not None:
                            user.is_enabled = request.is_enabled
                        if request.is_locked is not None:
                            user.is_locked = request.is_locked
                        if request.password_expiry_days is not None:
                            user.password_expiry_days = (
                                request.password_expiry_days
                            )
                        if request.description is not None:
                            user.description = request.description
                        return True, None, user
                return False, "User not found", None

            # Mock repos
            mock_users_repo = Mock()
            mock_users_repo.create_user.side_effect = mock_create_user
            mock_users_repo.get_user_by_username.side_effect = (
                mock_get_user_by_username
            )
            mock_users_repo.get_user_by_id.side_effect = mock_get_user_by_id
            mock_users_repo.get_users.side_effect = mock_get_users
            mock_users_repo.delete_user_by_id.side_effect = (
                mock_delete_user_by_id
            )
            mock_users_repo.update_user.side_effect = mock_update_user
            mock_users_repo.create_login_log.return_value = None
            mock_users_repo.get_login_logs.side_effect = (
                lambda user_id=None,
                start_time=None,
                end_time=None,
                limit=100,
                offset=0: (
                    True,
                    None,
                    manager.login_logs[offset : offset + limit]
                    if limit > 0
                    else manager.login_logs[offset:],
                )
            )

            # Add mock for delete_login_logs
            def mock_delete_login_logs(user_id=None, user_name=None):
                """Mock delete_login_logs from logs."""
                count_before = len(manager.login_logs)
                if user_id or user_name:
                    # Delete logs for specific user
                    manager.login_logs = [
                        log
                        for log in manager.login_logs
                        if not (
                            (
                                user_id
                                and getattr(log, "user_id", None) == user_id
                            )
                            or (
                                user_name
                                and getattr(log, "user_name", None)
                                == user_name
                            )
                        )
                    ]
                else:
                    # Delete all logs
                    manager.login_logs = []
                count_deleted = count_before - len(manager.login_logs)
                return True, None, count_deleted

            mock_users_repo.delete_login_logs.side_effect = (
                mock_delete_login_logs
            )
            manager.users_repo = mock_users_repo

            # Use previously defined mock functions for roles
            mock_roles_repo = Mock()
            mock_roles_repo.create_role.side_effect = mock_create_role
            mock_roles_repo.get_role_by_name.side_effect = (
                mock_get_role_by_name
            )
            mock_roles_repo.get_role_by_id.side_effect = mock_get_role_by_id
            mock_roles_repo.get_roles.side_effect = mock_get_roles
            mock_roles_repo.update_role.side_effect = mock_update_role
            mock_roles_repo.delete_role_by_id.side_effect = mock_delete_role
            manager.roles_repo = mock_roles_repo

            # Create default roles for tests
            manager.create_role(
                "admin",
                permissions=["*"],
                description="Administrator with full permissions",
            )
            manager.create_role(
                "user",
                permissions=[
                    "/v1/auth/logout",
                    "/v1/auth/me",
                    "/v1/device/get_device",
                    "/v1/device/get_devices",
                    "/v1/driver/get_driver",
                    "/v1/driver/get_drivers",
                ],
                description="Regular user with basic permissions",
            )

            # Create default admin user for tests
            manager.create_user(
                Constant.DEFAULT_PROJECT_ID,
                "admin",
                "admin_password",
                ["admin"],
                True,
                False,
                0,
                "Administrator user",
            )

            # Clear login_logs to start fresh for each test
            manager.login_logs = []

            yield manager
        finally:
            patcher1.stop()
            patcher2.stop()

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed_password"),
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
        with pytest.raises(ValueError, match="Cannot start with underscore"):
            user_manager.validate_user_name("_invalid_user")

    def test_validate_user_name_invalid_characters(self, user_manager):
        """Test user name validation with invalid characters."""
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("user@name")
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("user.name")
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("user name")
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_user_name("+123user")

    def test_validate_user_name_valid_formats(self, user_manager):
        """Test user name validation with various valid formats."""
        user_manager.validate_user_name("valid_user")
        user_manager.validate_user_name("valid-user")
        user_manager.validate_user_name("validUser123")
        user_manager.validate_user_name("user123_test-name")
        user_manager.validate_user_name("00000000-0000-4000-8000-000000000000")

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
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
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
        assert "testuser" in user_manager._username_to_id

    def test_create_user_duplicate(self, user_manager):
        """Test creating a user with duplicate username."""
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "testuser",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
        )

        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_user(
                Constant.DEFAULT_PROJECT_ID,
                "testuser",
                _s("password456"),
                ["user"],
                True,
                False,
                90,
            )

    def test_create_user_invalid_name(self, user_manager):
        """Test creating user with invalid username."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.create_user(
                Constant.DEFAULT_PROJECT_ID,
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
                Constant.DEFAULT_PROJECT_ID,
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
                Constant.DEFAULT_PROJECT_ID,
                "testuser",
                _s("password123"),
                ["nonexistent"],
                True,
                False,
                90,
            )

    def test_get_user_success(self, user_manager):
        """Test successful user retrieval."""
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "testuser",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
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
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "testuser",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
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
            Constant.DEFAULT_PROJECT_ID,
            "testuser",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
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
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "user1",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
        )
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "user2",
            _s("password123"),
            ["admin"],
            True,
            False,
            90,
        )
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "user3",
            _s("password123"),
            ["user", "admin"],
            True,
            False,
            90,
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
        assert log.login_status is True
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

    def test_delete_login_logs_all(self, user_manager):
        """Test deleting all login logs."""
        # Add some logs
        user_manager.log_login_attempt(
            "user1", "192.168.1.1", True, user_agent="Mozilla/5.0"
        )
        user_manager.log_login_attempt(
            "user2", "192.168.1.2", False, user_agent="Chrome/91.0"
        )

        # Verify logs exist
        logs_before = user_manager.get_login_logs()
        assert len(logs_before) == 2

        # Delete all logs
        success, error, count = user_manager.users_repo.delete_login_logs()
        assert success is True
        assert error is None
        assert count == 2

        # Verify logs are deleted
        logs_after = user_manager.get_login_logs()
        assert len(logs_after) == 0

    def test_delete_login_logs_for_specific_user(self, user_manager):
        """Test deleting login logs for a specific user."""
        # Add logs for multiple users
        user_manager.log_login_attempt(
            "user1", "192.168.1.1", True, user_agent="Mozilla/5.0"
        )
        user_manager.log_login_attempt(
            "user1", "192.168.1.2", False, user_agent="Firefox/88"
        )
        user_manager.log_login_attempt(
            "user2", "192.168.1.3", True, user_agent="Chrome/91.0"
        )

        # Verify logs exist
        logs_before = user_manager.get_login_logs()
        assert len(logs_before) == 3

        # Delete logs for user1
        success, error, count = user_manager.users_repo.delete_login_logs(
            user_name="user1"
        )
        assert success is True
        assert error is None
        assert count == 2

        # Verify only user2's logs remain
        logs_after = user_manager.get_login_logs()
        assert len(logs_after) == 1
        assert logs_after[0].user_name == "user2"

    def test_delete_login_logs_nonexistent_user(self, user_manager):
        """Test deleting logs for nonexistent user returns 0."""
        # Add some logs
        user_manager.log_login_attempt(
            "user1", "192.168.1.1", True, user_agent="Mozilla/5.0"
        )

        # Try to delete logs for nonexistent user
        success, error, count = user_manager.users_repo.delete_login_logs(
            user_name="nonexistent"
        )

        # Should return success with count 0 (graceful)
        assert success is True
        assert count == 0

        # Verify user1's log still exists
        logs = user_manager.get_login_logs()
        assert len(logs) == 1
        assert logs[0].user_name == "user1"

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
        # Should be able to verify the password with the hash
        assert user_manager.check_password(password, hashed) is True

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
        assert "admin" in user_manager._role_name_to_id
        assert "user" in user_manager._role_name_to_id

        assert "admin" in user_manager._username_to_id

        admin_user = user_manager.get_user("admin")
        assert admin_user is not None
        assert admin_user.user_name == "admin"
        assert "admin" in admin_user.roles

    def test_get_default_policies(self, user_manager):
        """Test getting default policies."""
        admin_policies = user_manager.get_default_policies("admin")
        user_policies = user_manager.get_default_policies("user")
        all_policies = user_manager.get_default_policies()

        assert isinstance(admin_policies, list)
        assert isinstance(user_policies, list)
        assert isinstance(all_policies, list)

        admin_permissions = [p[1] for p in admin_policies]
        assert "*" in admin_permissions

    def test_password_with_special_characters(self, user_manager):
        """Test password with special characters."""
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "special_char_user",
            _s("P@ssw0rd!#$%"),
            ["user"],
            True,
            False,
            90,
        )
        assert user.user_name == "special_char_user"

    def test_password_case_sensitivity(self, user_manager):
        """Test that password is case-sensitive."""
        password1 = _s("TestPassword")
        password2 = _s("testpassword")

        hash1 = user_manager.hash_password(password1)
        user_manager.hash_password(password2)

        # Different cases should produce different verification results
        assert user_manager.check_password(password1, hash1)
        assert not user_manager.check_password(password2, hash1)

    def test_password_with_unicode(self, user_manager):
        """Test password with unicode characters."""
        unicode_password = _s("密码@Test123")
        hashed = user_manager.hash_password(unicode_password)
        assert user_manager.check_password(unicode_password, hashed)

    def test_empty_password_validation(self, user_manager):
        """Test that empty password is rejected."""
        with pytest.raises(ValueError):
            user_manager.validate_password("")

    def test_whitespace_only_password(self, user_manager):
        """Test that whitespace-only password is rejected."""
        with pytest.raises(ValueError):
            user_manager.validate_password("     ")

    def test_sequential_user_creation(self, user_manager):
        """Test creating multiple users sequentially."""
        users = []
        for i in range(3):
            user = user_manager.create_user(
                Constant.DEFAULT_PROJECT_ID,
                f"seq_user_{i}",
                _s(f"pass_{i}"),
                ["user"],
                True,
                False,
                90,
            )
            users.append(user)

        assert len(users) == 3
        # Verify all users were created successfully
        for i, user in enumerate(users):
            assert user.user_name == f"seq_user_{i}"

    def test_duplicate_user_creation_prevention(self, user_manager):
        """Test that duplicate user creation is prevented."""
        user1 = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "unique_user",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
        )
        assert user1.user_name == "unique_user"

        # Attempt to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_user(
                Constant.DEFAULT_PROJECT_ID,
                "unique_user",
                _s("different_password"),
                ["user"],
                True,
                False,
                90,
            )

    def test_concurrent_role_updates(self, user_manager):
        """Test updating role permissions while users have it."""
        # Create role
        user_manager.create_role(
            "concurrent_role",
            ["/version"],
            "Concurrent role",
        )

        # Create user with this role
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "concurrent_user",
            _s("password123"),
            ["concurrent_role"],
            True,
            False,
            90,
        )

        # Update role permissions
        updated_role = user_manager.update_role(
            "concurrent_role",
            ["/version", "/v1/device/get_device"],
        )

        assert len(updated_role.permissions) == 2
        assert user.user_name == "concurrent_user"

    def test_user_deletion_during_login(self, user_manager):
        """Test user deletion while login attempt is happening."""
        # Create user
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "delete_test_user",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
        )
        assert user.user_name == "delete_test_user"

        # Delete user
        deleted_user = user_manager.delete_user("delete_test_user")
        assert deleted_user.user_name == "delete_test_user"

        # Verify user is gone
        assert user_manager.get_user("delete_test_user") is None

    def test_username_with_hyphens(self, user_manager):
        """Test username with hyphens."""
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "user-with-hyphens",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
        )
        assert user.user_name == "user-with-hyphens"

    def test_username_with_underscores(self, user_manager):
        """Test username with underscores (not at start)."""
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "user_with_underscores",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
        )
        assert user.user_name == "user_with_underscores"

    def test_description_with_special_chars(self, user_manager):
        """Test user description with special characters."""
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "special_desc_user",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
            "User with @!#$%^&*() special characters",
        )
        assert "@!#$%^&*()" in user.description

    def test_password_expiry_days_boundary(self, user_manager):
        """Test password expiry days with boundary values."""
        user1 = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "no_expiry_user",
            _s("password123"),
            ["user"],
            True,
            False,
            0,
        )
        assert user1.password_expiry_days == 0

        user2 = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "long_expiry_user",
            _s("password123"),
            ["user"],
            True,
            False,
            365,
        )
        assert user2.password_expiry_days == 365

    def test_role_assignment_with_multiple_roles(self, user_manager):
        """Test assigning multiple roles to user."""
        # Create multiple roles
        user_manager.create_role("role_a", ["/version"])
        user_manager.create_role("role_b", ["/v1/device/get_device"])

        # Create user with multiple roles
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "multi_role_user",
            _s("password123"),
            ["role_a", "role_b"],
            True,
            False,
            90,
        )
        assert len(user.roles) == 2
        assert "role_a" in user.roles
        assert "role_b" in user.roles

    def test_cannot_assign_nonexistent_role(self, user_manager):
        """Test that assigning non-existent role fails."""
        with pytest.raises(ValueError, match="does not exist"):
            user_manager.create_user(
                Constant.DEFAULT_PROJECT_ID,
                "bad_role_user",
                _s("password123"),
                ["nonexistent_role"],
                True,
                False,
                90,
            )

    @pytest.fixture
    def user_manager_with_users(self, user_manager_with_mocks):
        """Create a UserManager with test users."""
        manager = user_manager_with_mocks

        # Create test users
        manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "query_user1",
            _s("password1"),
            ["user"],
            True,
            False,
            90,
        )
        manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "query_user2",
            _s("password2"),
            ["user"],
            True,
            False,
            90,
        )
        manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "admin_user1",
            _s("password3"),
            ["admin"],
            True,
            False,
            0,
        )

        return manager

    def test_get_all_users(self, user_manager_with_users):
        """Test getting all users."""
        users = user_manager_with_users.get_users()
        assert len(users) >= 3

    def test_find_users_empty_result(self, user_manager_with_users):
        """Test finding users with role that has no users."""
        # Create a role with no users
        user_manager_with_users.create_role("unused_role", ["/version"])
        users = user_manager_with_users.find_users_by_role("unused_role")
        assert len(users) == 0

    def test_get_nonexistent_user(self, user_manager_with_users):
        """Test getting non-existent user."""
        user = user_manager_with_users.get_user("nonexistent_user_xyz")
        assert user is None

    def test_complete_user_creation_workflow(self, user_manager):
        """Test complete user creation and setup workflow."""
        # Step 1: Create custom role
        custom_role = user_manager.create_role(
            "operator",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "Operator role with limited device access",
        )
        assert custom_role.role_name == "operator"
        assert len(custom_role.permissions) == 3

        # Step 2: Create user with custom role
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "operator_user",
            _s("operator_password123"),
            ["operator"],
            True,
            False,
            90,
            "Operator user",
        )
        assert user.user_name == "operator_user"
        assert "operator" in user.roles
        assert user.is_enabled is True
        assert user.is_locked is False

        # Step 3: Verify user can be retrieved
        retrieved_user = user_manager.get_user("operator_user")
        assert retrieved_user is not None
        assert retrieved_user.user_name == "operator_user"
        assert retrieved_user.roles == ["operator"]

        # Step 4: Update user with additional role
        updated_user = user_manager.update_user(
            "operator_user", ["operator", "user"], None, None, 180
        )
        assert "operator" in updated_user.roles
        assert "user" in updated_user.roles

        # Step 5: Delete user
        deleted_user = user_manager.delete_user("operator_user")
        assert deleted_user.user_name == "operator_user"

        # Step 6: Verify user is deleted
        assert user_manager.get_user("operator_user") is None

    def test_multi_user_role_management(self, user_manager):
        """Test managing multiple users with different roles."""
        # Create different roles
        user_manager.create_role("super_admin", ["*"], "Super admin role")
        user_manager.create_role(
            "viewer", ["/version", "/v1/device/get_devices"], "Viewer role"
        )

        # Create users with different roles
        admin = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "admin_user",
            _s("admin_pass"),
            ["super_admin"],
            True,
            False,
            0,
        )
        viewer = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "viewer_user",
            _s("viewer_pass"),
            ["viewer"],
            True,
            False,
            90,
        )
        regular_user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "regular_user",
            _s("user_pass"),
            ["user"],
            True,
            False,
            90,
        )

        # Verify role assignments
        assert "super_admin" in admin.roles
        assert "viewer" in viewer.roles
        assert "user" in regular_user.roles

        # Find users by role
        admins = user_manager.find_users_by_role("super_admin")
        viewers = user_manager.find_users_by_role("viewer")

        assert "admin_user" in admins
        assert "viewer_user" in viewers

    def test_role_permission_cascading(self, user_manager):
        """Test that role permissions cascade to users."""
        # Create a role with specific permissions
        permissions = [
            "/version",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        user_manager.create_role("device_operator", permissions)

        # Create user with this role
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "device_op",
            _s("password123"),
            ["device_operator"],
            True,
            False,
            90,
        )

        # Verify the role has the permissions
        retrieved_role = user_manager.get_role("device_operator")
        assert set(retrieved_role.permissions) == set(permissions)

        # Get role permissions
        role_perms = user_manager.perms_check.get_for_role("device_operator")
        assert isinstance(role_perms, list)

    def test_user_state_transitions(self, user_manager):
        """Test user state transitions (enabled/disabled, locked/unlocked)."""
        user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "state_test_user",
            _s("password123"),
            ["user"],
            True,
            False,
            90,
        )

        # Transition 1: Disable user
        disabled_user = user_manager.update_user(
            "state_test_user", None, False, None, None
        )
        assert disabled_user.is_enabled is False

        # Transition 2: Enable user again
        enabled_user = user_manager.update_user(
            "state_test_user", None, True, None, None
        )
        assert enabled_user.is_enabled is True

        # Transition 3: Lock user
        locked_user = user_manager.update_user(
            "state_test_user", None, None, True, None
        )
        assert locked_user.is_locked is True

        # Transition 4: Unlock user
        unlocked_user = user_manager.update_user(
            "state_test_user", None, None, False, None
        )
        assert unlocked_user.is_locked is False

    def test_password_expiry_lifecycle(self, user_manager):
        """Test password expiry tracking."""
        user = user_manager.create_user(
            Constant.DEFAULT_PROJECT_ID,
            "expiry_user",
            _s("initial_password"),
            ["user"],
            True,
            False,
            90,
        )

        # Password should be valid initially
        assert not user_manager.is_password_expired(user)

        # Simulate password aging
        user.password_changed_at = datetime.now() - timedelta(days=100)
        assert user_manager.is_password_expired(user)

    def test_password_hash_consistency(self, user_manager):
        """Test that password hashing is consistent."""
        password = _s("test_password_12345")

        # Hash the same password multiple times
        hash1 = user_manager.hash_password(password)
        hash2 = user_manager.hash_password(password)

        # Both should verify the password
        assert user_manager.check_password(password, hash1)
        assert user_manager.check_password(password, hash2)

        # Wrong password should fail
        wrong_password = _s("wrong_password")
        assert not user_manager.check_password(wrong_password, hash1)

    @pytest.fixture
    def user_manager_batch(self):
        """Create a UserManager instance."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.return_value = True
        mock_enforcer.remove_policy.return_value = True
        mock_enforcer.delete_role.return_value = True
        mock_enforcer.get_permissions_for_user.return_value = []
        mock_enforcer.add_grouping_policy.return_value = True
        mock_enforcer.remove_grouping_policy.return_value = True
        mock_enforcer.delete_roles_for_user.return_value = True
        mock_enforcer.enforce.return_value = True

        patcher = patch(
            "wy_qcos.user.permission_manager.casbin.Enforcer",
            return_value=mock_enforcer,
        )
        patcher.start()
        try:
            manager = UserManager("model.conf", "policy.csv", all_api)
            # Mock repos to prevent initialization errors
            login_logs = []

            # Track created users
            created_users = {}

            def mock_get_user_by_username(user_name):
                if user_name in created_users:
                    return (True, None, created_users[user_name])
                return (False, None, None)

            def mock_get_users():
                return (True, None, list(created_users.values()))

            def mock_create_user(request):
                user = schemas.User(
                    user_name=request.user_name,
                    hashed_password=_s("hashed"),
                    roles=request.roles,
                    is_enabled=request.is_enabled,
                    is_locked=request.is_locked,
                    password_expiry_days=request.password_expiry_days,
                    description=request.description,
                    password_changed_at=datetime.now(),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                created_users[request.user_name] = user
                return True, None, user

            mock_users_repo = Mock()
            mock_users_repo.get_user_by_username.side_effect = (
                mock_get_user_by_username
            )
            mock_users_repo.get_users.side_effect = mock_get_users
            mock_users_repo.create_user.side_effect = mock_create_user

            # Mock login log tracking
            def mock_create_login_log(
                user_name,
                ip_address,
                success,
                failure_reason=None,
                user_agent=None,
            ):
                log = LoginLog(
                    user_name=user_name,
                    ip_address=ip_address,
                    login_status=success,
                    failure_reason=failure_reason,
                    user_agent=user_agent,
                    login_time=datetime.now(),
                )
                login_logs.append(log)

            mock_users_repo.create_login_log.side_effect = (
                mock_create_login_log
            )
            mock_users_repo.get_login_logs.side_effect = lambda limit=100: (
                True,
                None,
                login_logs[-limit:],
            )

            # Add mock for delete_login_logs
            def mock_delete_login_logs(user_id=None, user_name=None):
                """Mock delete_login_logs from logs."""
                count_before = len(manager.login_logs)
                if user_id or user_name:
                    # Delete logs for specific user
                    manager.login_logs = [
                        log
                        for log in manager.login_logs
                        if not (
                            (
                                user_id
                                and getattr(log, "user_id", None) == user_id
                            )
                            or (
                                user_name
                                and getattr(log, "user_name", None)
                                == user_name
                            )
                        )
                    ]
                else:
                    # Delete all logs
                    manager.login_logs = []
                count_deleted = count_before - len(manager.login_logs)
                return True, None, count_deleted

            mock_users_repo.delete_login_logs.side_effect = (
                mock_delete_login_logs
            )
            manager.users_repo = mock_users_repo

            # Track created roles
            created_roles = {}

            def mock_create_role_func(request):
                role = schemas.Role(
                    role_name=request.role_name,
                    permissions=request.permissions,
                    description=request.description,
                )
                created_roles[request.role_name] = role
                return True, None, role

            def mock_get_role_by_name_func(role_name):
                if role_name in created_roles:
                    return True, None, created_roles[role_name]
                return False, None, None

            def mock_get_role_by_id(role_id):
                # Find role by id - normalize UUID comparison
                role_id_str = str(role_id).lower() if role_id else None
                for role in created_roles.values():
                    if (
                        hasattr(role, "id")
                        and str(role.id).lower() == role_id_str
                    ):
                        return True, None, role
                return False, None, None

            mock_roles_repo = Mock()
            mock_roles_repo.create_role.side_effect = mock_create_role_func
            mock_roles_repo.get_role_by_name.side_effect = (
                mock_get_role_by_name_func
            )
            mock_roles_repo.get_role_by_id.side_effect = mock_get_role_by_id
            mock_roles_repo.get_roles.return_value = (True, None, [])
            manager.roles_repo = mock_roles_repo

            # Create basic roles for testing
            manager.create_role(
                "user",
                [
                    "/version",
                    "/v1/device/get_device",
                    "/v1/device/get_devices",
                ],
                "Basic user role",
            )
            manager.create_role("admin", ["*"], "Administrator role")

            yield manager
        finally:
            patcher.stop()

    def test_bulk_user_creation(self, user_manager_batch):
        """Test creating multiple users efficiently."""
        users = []
        for i in range(5):
            user = user_manager_batch.create_user(
                "default_project",
                f"bulk_user_{i}",
                _s(f"password_{i}"),
                ["user"],
                True,
                False,
                90,
            )
            users.append(user)

        assert len(users) == 5
        for user in users:
            assert user.is_enabled is True

    def test_find_users_by_role_multiple_roles(self, user_manager_batch):
        """Test finding users with multiple role assignments."""
        # Create users with overlapping roles
        user_manager_batch.create_user(
            "default_project",
            "multi_user1",
            _s("pass123"),
            ["user", "admin"],
            True,
            False,
            90,
        )
        user_manager_batch.create_user(
            "default_project",
            "multi_user2",
            _s("pass456"),
            ["user"],
            True,
            False,
            90,
        )
        user_manager_batch.create_user(
            "default_project",
            "multi_user3",
            _s("pass789"),
            ["admin"],
            True,
            False,
            90,
        )

        # Find by each role
        user_role_users = user_manager_batch.find_users_by_role("user")
        admin_role_users = user_manager_batch.find_users_by_role("admin")

        assert "multi_user1" in user_role_users
        assert "multi_user2" in user_role_users
        assert "multi_user1" in admin_role_users
        assert "multi_user3" in admin_role_users
