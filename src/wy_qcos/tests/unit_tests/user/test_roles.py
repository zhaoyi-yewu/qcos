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

from wy_qcos.api import schemas
from wy_qcos.common.constant import Constant
from wy_qcos.api.posiq.routes_jsonrpc.user import (
    create_role,
    delete_role,
    get_role,
    get_roles,
    initialize_user_management,
    update_role,
)


class TestRoles:
    """Test cases for role management functionality."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment before each test."""
        # Initialize user management for each test
        initialize_user_management()

    def test_create_role_success(self):
        """Test successful role creation."""
        request = schemas.CreateRoleRequest(
            role_name="testrole",
            permissions=["read", "write"],
            description="Test role for testing",
        )

        response = create_role(request)

        assert isinstance(response, schemas.CreateRoleResponse)
        assert response.role_name == "testrole"
        assert response.permissions == ["read", "write"]
        assert response.description == "Test role for testing"

    def test_create_role_duplicate(self):
        """Test creating a role with duplicate name."""
        request = schemas.CreateRoleRequest(
            role_name="admin",
            permissions=["read", "write", "delete"],
            description="Admin role",
        )

        with pytest.raises(Exception):  # Should raise conflict error
            create_role(request)

    def test_create_role_invalid_name(self):
        """Test creating role with invalid name."""
        # Test validation error for role name with space
        with pytest.raises(Exception):  # Should raise validation error
            schemas.CreateRoleRequest(
                role_name="test role",  # Contains space
                permissions=["read"],
                description="Invalid role name",
            )

    def test_get_role_success(self):
        """Test successful role retrieval."""
        # First create a role with unique name
        create_request = schemas.CreateRoleRequest(
            role_name="testrole1",
            permissions=["read", "write"],
            description="Test role",
        )
        create_role(create_request)

        # Then retrieve it
        request = schemas.GetRoleRequest(role_name="testrole1")
        response = get_role(request)

        assert isinstance(response, schemas.GetRoleResponse)
        assert response.role_name == "testrole1"
        assert response.permissions == ["read", "write"]
        assert response.description == "Test role"

    def test_get_role_not_found(self):
        """Test getting non-existent role."""
        request = schemas.GetRoleRequest(role_name="nonexistent")

        with pytest.raises(Exception):  # Should raise not found error
            get_role(request)

    def test_update_role_success(self):
        """Test successful role update."""
        # Create role first
        create_request = schemas.CreateRoleRequest(
            role_name="testrole2",
            permissions=["read"],
            description="Original description",
        )
        create_role(create_request)

        # Update role
        update_request = schemas.UpdateRoleRequest(
            role_name="testrole2",
            permissions=["read", "write", "delete"],
            description="Updated description",
        )
        response = update_role(update_request)

        assert isinstance(response, schemas.UpdateRoleResponse)
        assert response.role_name == "testrole2"
        assert response.permissions == ["read", "write", "delete"]
        assert response.description == "Updated description"

    def test_update_role_not_found(self):
        """Test updating non-existent role."""
        update_request = schemas.UpdateRoleRequest(
            role_name="nonexistent",
            permissions=["read"],
            description="New description",
        )

        with pytest.raises(Exception):  # Should raise not found error
            update_role(update_request)

    def test_delete_role_success(self):
        """Test successful role deletion."""
        # Create role first
        create_request = schemas.CreateRoleRequest(
            role_name="testrole3",
            permissions=["read"],
            description="Test role",
        )
        create_role(create_request)

        # Delete role
        delete_request = schemas.DeleteRoleRequest(role_name="testrole3")
        response = delete_role(delete_request)

        assert isinstance(response, schemas.DeleteRoleResponse)
        assert response.role_name == "testrole3"

    def test_delete_role_not_found(self):
        """Test deleting non-existent role."""
        delete_request = schemas.DeleteRoleRequest(role_name="nonexistent")

        with pytest.raises(Exception):  # Should raise not found error
            delete_role(delete_request)

    def test_get_roles(self):
        """Test getting all roles."""
        # Create test roles
        create_request1 = schemas.CreateRoleRequest(
            role_name="role1",
            permissions=["read"],
            description="First test role",
        )
        create_request2 = schemas.CreateRoleRequest(
            role_name="role2",
            permissions=["write"],
            description="Second test role",
        )
        create_role(create_request1)
        create_role(create_request2)

        response = get_roles()

        # Should return a dictionary of roles
        assert isinstance(response, dict)
        assert len(response) >= 2  # At least admin + 2 test roles

        # Check that our test roles are in the response
        role_names = list(response.keys())
        assert "role1" in role_names
        assert "role2" in role_names

    def test_role_validation(self):
        """Test role input validation."""
        # Test short role name
        with pytest.raises(Exception):
            create_request = schemas.CreateRoleRequest(
                role_name="a" * (Constant.MIN_ROLE_LENGTH - 1),  # Too short
                permissions=["read"],
                description="Invalid role name",
            )
            create_role(create_request)

        # Test long role name
        with pytest.raises(Exception):
            create_request = schemas.CreateRoleRequest(
                role_name="a" * (Constant.MAX_ROLE_LENGTH + 1),  # Too long
                permissions=["read"],
                description="Invalid role name",
            )
            create_role(create_request)

        # Test long description
        with pytest.raises(Exception):
            create_request = schemas.CreateRoleRequest(
                role_name="testrole",
                permissions=["read"],
                description="a" * (Constant.MAX_DESCRIPTION_LENGTH + 1),
            )
            create_role(create_request)

    def test_role_permissions(self):
        """Test role permissions handling."""
        # Test role with empty permissions
        create_request = schemas.CreateRoleRequest(
            role_name="emptyrole",
            permissions=[],
            description="Role with no permissions",
        )
        response = create_role(create_request)

        assert response.permissions == []

        # Test role with multiple permissions
        create_request = schemas.CreateRoleRequest(
            role_name="multirole",
            permissions=["read", "write", "delete", "execute"],
            description="Role with multiple permissions",
        )
        response = create_role(create_request)

        assert len(response.permissions) == 4
        assert "read" in response.permissions
        assert "write" in response.permissions
        assert "delete" in response.permissions
        assert "execute" in response.permissions

    def test_update_role_partial(self):
        """Test partial role updates."""
        # Create role first
        create_request = schemas.CreateRoleRequest(
            role_name="testrole4",
            permissions=["read"],
            description="Original description",
        )
        create_role(create_request)

        # Update only permissions
        update_request = schemas.UpdateRoleRequest(
            role_name="testrole4", permissions=["read", "write"]
        )
        response = update_role(update_request)

        assert response.role_name == "testrole4"
        assert response.permissions == ["read", "write"]
        assert (
            response.description == "Original description"
        )  # Should remain unchanged

        # Update only description
        update_request = schemas.UpdateRoleRequest(
            role_name="testrole4", description="New description"
        )
        response = update_role(update_request)

        assert response.role_name == "testrole4"
        assert response.permissions == [
            "read",
            "write",
        ]  # Should remain unchanged
        assert response.description == "New description"

    def test_default_admin_role(self):
        """Test that default admin role exists after initialization."""
        # Admin role should exist after initialization
        request = schemas.GetRoleRequest(role_name="admin")
        response = get_role(request)

        assert isinstance(response, schemas.GetRoleResponse)
        assert response.role_name == "admin"
        assert (
            "*" in response.permissions
        )  # Admin role has wildcard permissions
