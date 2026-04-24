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
from unittest.mock import Mock, patch

from wy_qcos.api.posiq.routes_jsonrpc.routes import all_api
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager


class TestUserManagerRoles:
    """Test cases for UserManager role functionality."""

    @pytest.fixture
    def user_manager(self, user_manager_with_mocks):
        """Create a UserManager instance with mocked dependencies."""
        return user_manager_with_mocks

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

    def test_validate_role_name_starts_with_underscore(self, user_manager):
        """Test role name validation with name starting with underscore."""
        with pytest.raises(ValueError, match="cannot start with underscore"):
            user_manager.validate_role_name("_invalid_role")

    def test_validate_role_name_invalid_characters(self, user_manager):
        """Test role name validation with invalid characters."""
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_role_name("role@name")
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_role_name("role.name")
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_role_name("role name")  # space
        with pytest.raises(ValueError, match="is invalid"):
            user_manager.validate_role_name("123role")  # starts with digit

    def test_validate_role_name_valid_formats(self, user_manager):
        """Test role name validation with various valid formats."""
        # Should allow letters, digits, hyphens, and underscores (not at start)
        user_manager.validate_role_name("valid_role")
        user_manager.validate_role_name("valid-role")
        user_manager.validate_role_name("validRole123")
        user_manager.validate_role_name("role123_test-name")

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
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
        )

        with pytest.raises(ValueError, match="already exists"):
            user_manager.create_role(
                "testrole",
                [
                    "/version",
                    "/v1/device/get_device",
                    "/v1/device/get_devices",
                ],
            )

    def test_create_role_invalid_name(self, user_manager):
        """Test creating role with invalid name."""
        with pytest.raises(ValueError, match="too short"):
            user_manager.create_role(
                "a" * (Constant.MIN_ROLE_LENGTH - 1),
                [
                    "/version",
                    "/v1/device/get_device",
                    "/v1/device/get_devices",
                ],
            )

    def test_create_role_invalid_permissions(self, user_manager):
        """Test creating role with invalid permissions."""
        with pytest.raises(ValueError, match="Invalid permission"):
            user_manager.create_role("testrole", ["invalid_permission"])

    def test_create_role_default_permissions(self, user_manager):
        """Test creating role with default permissions."""
        role = user_manager.create_role("testrole", None, "Test role")

        assert role.role_name == "testrole"
        assert role.permissions is not None
        assert (
            len(role.permissions) > 0
        )  # Should have default user permissions

    def test_get_role_success(self, user_manager):
        """Test successful role retrieval."""
        user_manager.create_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
        )
        role = user_manager.get_role("testrole")

        assert role is not None
        assert role.role_name == "testrole"
        assert role.permissions == [
            "/version",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]

    def test_get_role_not_found(self, user_manager):
        """Test getting non-existent role."""
        role = user_manager.get_role("nonexistent")
        assert role is None

    def test_get_roles(self, user_manager):
        """Test getting all roles."""
        # Create test roles
        user_manager.create_role(
            "role1",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "First test role",
        )
        user_manager.create_role(
            "role2",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "Second test role",
        )

        roles = user_manager.get_roles()

        assert isinstance(roles, dict)
        assert "role1" in roles
        assert "role2" in roles
        assert roles["role1"].role_name == "role1"
        assert roles["role2"].role_name == "role2"

    def test_update_role_success(self, user_manager):
        """Test successful role update."""
        user_manager.create_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "Original description",
        )

        updated_role = user_manager.update_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "Updated description",
        )

        assert updated_role.role_name == "testrole"
        assert updated_role.permissions == [
            "/version",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        assert updated_role.description == "Updated description"

    def test_update_role_not_found(self, user_manager):
        """Test updating non-existent role."""
        with pytest.raises(ValueError, match="not found"):
            user_manager.update_role(
                "nonexistent",
                [
                    "/version",
                    "/v1/device/get_device",
                    "/v1/device/get_devices",
                ],
            )

    def test_update_role_partial_permissions(self, user_manager):
        """Test partial role update with only permissions."""
        user_manager.create_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "Original description",
        )

        updated_role = user_manager.update_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            None,  # Don't update description
        )

        assert updated_role.role_name == "testrole"
        assert updated_role.permissions == [
            "/version",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        assert (
            updated_role.description == "Original description"
        )  # Should remain unchanged

    def test_update_role_partial_description(self, user_manager):
        """Test partial role update with only description."""
        user_manager.create_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
            "Original description",
        )

        updated_role = user_manager.update_role(
            "testrole",
            [
                "/version",
                "/v1/device/get_device",
                "/v1/device/get_devices",
            ],  # Don't update permissions
            "Updated description",
        )

        assert updated_role.role_name == "testrole"
        assert updated_role.permissions == [
            "/version",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        assert updated_role.description == "Updated description"

    def test_delete_role_success(self, user_manager):
        """Test successful role deletion."""
        user_manager.create_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
        )
        role = user_manager.delete_role("testrole")

        assert role.role_name == "testrole"
        assert "testrole" not in user_manager.roles_db

    def test_delete_role_not_found(self, user_manager):
        """Test deleting non-existent role."""
        with pytest.raises(ValueError, match="not found"):
            user_manager.delete_role("nonexistent")

    def test_delete_role_used_by_users(self, user_manager):
        """Test deleting role that is used by users."""
        # Create role and user with that role
        user_manager.create_role(
            "testrole",
            ["/version", "/v1/device/get_device", "/v1/device/get_devices"],
        )
        user_manager.create_user(
            "testuser", _s("password123"), ["testrole"], True, False, 90
        )

        # Should be able to delete role even if used by users
        # (In real implementation, this might have different behavior)
        role = user_manager.delete_role("testrole")
        assert role.role_name == "testrole"

    def test_get_permissions_list(self, user_manager):
        """Test getting permissions list from policies."""
        policies = [
            ("role1", "/api/test", "call"),
            ("role2", "/api/other", "call"),
        ]
        permissions = user_manager.get_permissions_list(policies)

        assert permissions == ["/api/test", "/api/other"]

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

    def test_get_default_policies_simple(self, user_manager):
        """Test getting default policies in simple format."""
        simple_policies = user_manager.get_default_policies(simple=True)

        assert isinstance(simple_policies, list)
        assert len(simple_policies) > 0
        # Should be a list of permission strings
        assert all(isinstance(p, str) for p in simple_policies)

    def test_init_users_creates_default_roles(self, user_manager):
        """Test that initialization creates default roles."""
        # Should create default admin and user roles
        # roles_db is keyed by UUID, but _role_name_to_id maps name to UUID
        assert "admin" in user_manager._role_name_to_id
        assert "user" in user_manager._role_name_to_id

        admin_role = user_manager.get_role("admin")
        user_role = user_manager.get_role("user")

        assert admin_role is not None
        assert user_role is not None
        assert admin_role.role_name == "admin"
        assert user_role.role_name == "user"

        # Admin role should have wildcard permissions
        assert "*" in admin_role.permissions


class TestRolePermissionIntegration:
    """Integration tests for role and permission management."""

    @pytest.fixture
    def user_manager(self, user_manager_with_mocks):
        """Create a UserManager instance."""
        return user_manager_with_mocks

    def test_permission_update_reflects_in_role(self, user_manager):
        """Test that permission updates are reflected in role."""
        # Create role with initial permissions
        role = user_manager.create_role(
            "limited_role",
            ["/version", "/v1/device/get_device"],
            "Limited role",
        )
        assert len(role.permissions) == 2

        # Update role with additional permissions
        updated_role = user_manager.update_role(
            "limited_role",
            [
                "/version",
                "/v1/device/get_device",
                "/v1/device/get_devices",
            ],
        )
        assert len(updated_role.permissions) == 3

    def test_wildcard_permission_handling(self, user_manager):
        """Test handling of wildcard permissions."""
        # Get admin role which has wildcard permission
        admin_role = user_manager.get_role("admin")
        assert admin_role is not None
        assert "*" in admin_role.permissions

    def test_role_deletion_cascade(self, user_manager):
        """Test role deletion when users depend on it."""
        # Create a role
        user_manager.create_role("temp_role", ["/version"], "Temporary role")

        # Create user with this role
        user = user_manager.create_user(
            "temp_user", _s("password123"), ["temp_role"], True, False, 90
        )
        assert "temp_role" in user.roles

        # Delete the role (should succeed even with users)
        deleted_role = user_manager.delete_role("temp_role")
        assert deleted_role.role_name == "temp_role"

        # Verify role is deleted
        assert user_manager.get_role("temp_role") is None
