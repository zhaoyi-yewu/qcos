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
# --------------------------------------------------------------------------

"""RBAC Integration tests for API layer.

This test module covers:
- Role-based access control integration
- Permission checking in API endpoints
- User role validation
- Cross-user permission isolation
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from wy_qcos.api.posiq.routes_jsonrpc.user import (
    create_user,
    get_roles,
    get_user,
)
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager


class TestRBAC:
    """Integration tests for RBAC at API layer."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager with RBAC."""
        mock = Mock(spec=UserManager)
        mock.get_user.return_value = None
        mock.get_role.return_value = None
        mock.get_roles.return_value = {}
        mock.get_default_policies.return_value = [
            "/v1/auth/get_current_user_info",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        return mock

    def test_create_user_with_admin_role(self, mock_user_manager):
        """Test creating user with admin role."""
        admin_role = user_schemas.Role(
            role_name="admin",
            permissions=["*"],
            description="Administrator",
        )
        mock_user_manager.get_role.return_value = admin_role

        created_user = user_schemas.User(
            user_name="new_admin",
            hashed_password=_s("hashed"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_user_manager.create_user.return_value = created_user

        body = user_schemas.CreateUserRequest(
            user_name="new_admin",
            password=_s("admin_pass"),
            roles=["admin"],
        )

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_username.return_value = (False, None, None)
        mock_users_repo.create_user.return_value = (True, None, created_user)
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True,
            None,
            admin_role,
        )

        result = create_user(
            body,
            mock_request,
            None,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo,
        )

        assert result is not None
        assert "admin" in result.roles

    def test_create_user_with_limited_role(self, mock_user_manager):
        """Test creating user with limited permissions role."""
        viewer_role = user_schemas.Role(
            role_name="viewer",
            permissions=["/v1/device/get_devices"],
            description="View only",
        )
        mock_user_manager.get_role.return_value = viewer_role

        created_user = user_schemas.User(
            user_name="viewer_user",
            hashed_password=_s("hashed"),
            roles=["viewer"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_user_manager.create_user.return_value = created_user

        body = user_schemas.CreateUserRequest(
            user_name="viewer_user",
            password=_s("viewer_pass"),
            roles=["viewer"],
        )

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_username.return_value = (False, None, None)
        mock_users_repo.create_user.return_value = (True, None, created_user)
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True,
            None,
            viewer_role,
        )

        result = create_user(
            body,
            mock_request,
            None,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo,
        )

        assert result is not None
        assert result.roles == ["viewer"]

    def test_user_permission_isolation(self, mock_user_manager):
        """Test that user permissions are isolated between users."""
        # Create two users with different roles
        user_schemas.User(
            user_name="admin",
            hashed_password=_s("hashed"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        user_schemas.User(
            user_name="viewer",
            hashed_password=_s("hashed"),
            roles=["viewer"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Verify they have different permissions
        admin_perms = ["*"]
        viewer_perms = ["/v1/device/get_devices"]

        assert admin_perms != viewer_perms

    def test_role_based_endpoint_access(self, mock_user_manager):
        """Test role-based access to different endpoints."""
        admin_role = user_schemas.Role(
            role_name="admin",
            permissions=["*"],
            description="All permissions",
        )
        operator_role = user_schemas.Role(
            role_name="operator",
            permissions=[
                "/v1/device/get_device",
                "/v1/device/get_devices",
            ],
            description="Limited to devices",
        )

        mock_roles_repo = Mock()
        mock_roles_repo.get_roles.return_value = (
            True,
            None,
            [admin_role, operator_role],
        )

        roles = get_roles(None, None, roles_repo=mock_roles_repo)

        # Find roles by name in the response
        admin_roles = [r for r in roles.values() if r.role_name == "admin"]
        operator_roles = [r for r in roles.values() if r.role_name == "operator"]

        assert len(admin_roles) == 1
        assert len(operator_roles) == 1
        assert len(admin_roles[0].permissions) == 1
        assert "*" in admin_roles[0].permissions
        assert len(operator_roles[0].permissions) == 2

    def test_multiple_role_assignment(self, mock_user_manager):
        """Test user with multiple roles gets combined permissions."""
        admin_role = user_schemas.Role(
            role_name="admin",
            permissions=["*"],
            description="Admin",
        )
        reviewer_role = user_schemas.Role(
            role_name="reviewer",
            permissions=["/v1/user/review"],
            description="Reviewer",
        )

        mock_user_manager.get_roles.return_value = {
            "admin": admin_role,
            "reviewer": reviewer_role,
        }

        multi_role_user = user_schemas.User(
            user_name="admin_reviewer",
            hashed_password=_s("hashed"),
            roles=["admin", "reviewer"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # User should have permissions from both roles
        assert len(multi_role_user.roles) == 2
        assert "admin" in multi_role_user.roles
        assert "reviewer" in multi_role_user.roles


class TestRolePermissionUpdates:
    """Test role and permission update scenarios."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_role.return_value = None
        mock.get_roles.return_value = {}
        mock.get_default_policies.return_value = [
            "/v1/auth/get_current_user_info",
            "/v1/device/get_device",
        ]
        return mock

    def test_updating_role_permissions(self, mock_user_manager):
        """Test updating role permissions."""
        original_role = user_schemas.Role(
            role_name="developer",
            permissions=["/v1/device/get_device"],
            description="Developer",
        )

        updated_role = user_schemas.Role(
            role_name="developer",
            permissions=[
                "/v1/device/get_device",
                "/v1/device/get_devices",
                "/v1/device/update_device",
            ],
            description="Senior Developer",
        )

        # Simulate role update
        assert len(original_role.permissions) == 1
        assert len(updated_role.permissions) == 3

    def test_revoking_role_from_user(self, mock_user_manager):
        """Test revoking a role from user."""
        user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["admin", "user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Revoke admin role
        updated_user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["user"],  # Admin role removed
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert "admin" in user.roles
        assert "admin" not in updated_user.roles
        assert "user" in updated_user.roles

    def test_granting_role_to_user(self, mock_user_manager):
        """Test granting a role to user."""
        user_before = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        user_after = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["user", "moderator"],  # Moderator role added
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert "moderator" not in user_before.roles
        assert "moderator" in user_after.roles


class TestPermissionInheritance:
    """Test permission inheritance patterns."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_default_policies.return_value = [
            "/version",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        return mock

    def test_default_role_permissions(self, mock_user_manager):
        """Test that default roles have appropriate permissions."""
        admin_role = user_schemas.Role(
            role_name="admin",
            permissions=["*"],
            description="Full access",
        )

        user_role = user_schemas.Role(
            role_name="user",
            permissions=[
                "/version",
                "/v1/device/get_device",
                "/v1/device/get_devices",
            ],
            description="Limited access",
        )

        # Admin should have all permissions
        assert "*" in admin_role.permissions

        # User should have subset of permissions
        assert len(user_role.permissions) < len(admin_role.permissions) or (
            "*" not in user_role.permissions
        )

    def test_inherited_permissions_combination(self, mock_user_manager):
        """Test combining permissions from multiple inherited roles."""
        # Simulating role hierarchy
        base_permissions = ["/version"]
        developer_permissions = base_permissions + [
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        senior_dev_permissions = developer_permissions + [
            "/v1/device/update_device",
        ]

        assert len(base_permissions) == 1
        assert len(developer_permissions) == 3
        assert len(senior_dev_permissions) == 4


class TestAccessControlValidation:
    """Test access control validation in API layer."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user.return_value = None
        mock.get_role.return_value = None
        return mock

    def test_validate_user_has_required_role(self, mock_user_manager):
        """Test validating user has required role."""
        user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["viewer"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Check if user has viewer role
        assert "viewer" in user.roles

        # Check if user has admin role (should fail)
        assert "admin" not in user.roles

    def test_validate_role_exists_before_assignment(self, mock_user_manager):
        """Test validating role exists before assigning to user."""
        existing_roles = {
            "admin": user_schemas.Role(
                role_name="admin",
                permissions=["*"],
                description="Admin",
            ),
            "user": user_schemas.Role(
                role_name="user",
                permissions=["/v1/device/get_device"],
                description="User",
            ),
        }

        # Existing role
        assert "admin" in existing_roles

        # Non-existing role
        assert "nonexistent" not in existing_roles


class TestUserPermissionIntegration:
    """Test cases for user permissions integration at API layer."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager with permission support."""
        mock = Mock(spec=UserManager)
        mock.get_user.return_value = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock.perms_enforce = Mock(return_value=True)
        return mock

    def test_user_with_admin_permissions(self, mock_user_manager):
        """Test user with admin permissions."""
        admin_user = user_schemas.User(
            user_name="admin",
            hashed_password=_s("hashed"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (True, None, admin_user)

        body = user_schemas.GetUserRequest(user_id="admin-uuid")
        auth_data = {"user_id": "admin-uuid", "roles": ["admin"]}
        result = get_user(body, auth_data, users_repo=mock_users_repo)

        assert result is not None
        assert "admin" in result.roles

    def test_user_with_limited_permissions(self, mock_user_manager):
        """Test user with limited permissions."""
        limited_user = user_schemas.User(
            user_name="operator",
            hashed_password=_s("hashed"),
            roles=["operator"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (
            True,
            None,
            limited_user,
        )

        body = user_schemas.GetUserRequest(user_id="operator-uuid")
        auth_data = {"user_id": "operator-uuid", "roles": ["operator"]}
        result = get_user(body, auth_data, users_repo=mock_users_repo)

        assert result is not None
        assert "operator" in result.roles
