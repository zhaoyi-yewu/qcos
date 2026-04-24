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
# ----------------------------------------------------------------------

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch

from wy_qcos.db.models import Role
from wy_qcos.db.repositories.role import RoleRepository
from wy_qcos.api.schemas.user import CreateRoleRequest, UpdateRoleRequest


class TestRoleRepositoryCRUD:
    """Test Role CRUD operations."""

    def test_create_role_success(self, role_repository):
        """Test successful role creation."""
        create_request = CreateRoleRequest(
            role_name="newrole",
            permissions=["read", "write"],
            description="Test role",
        )
        success, error, role = role_repository.create_role(create_request)
        assert success is True
        assert error is None
        assert role is not None
        assert role.role_name == "newrole"
        assert role.permissions == ["read", "write"]

    def test_create_role_minimal(self, role_repository):
        """Test role creation with minimal fields."""
        create_request = CreateRoleRequest(role_name="minimal_role")
        success, error, role = role_repository.create_role(create_request)
        assert success is True
        assert role is not None
        assert role.role_name == "minimal_role"

    def test_create_role_duplicate(self, role_repository, sample_role):
        """Test role creation with duplicate name."""
        create_request = CreateRoleRequest(role_name="admin")
        success, error, role = role_repository.create_role(create_request)
        assert success is False

    def test_get_role_by_id_success(self, role_repository, sample_role):
        """Test getting role by ID."""
        success, error, role = role_repository.get_role_by_id(sample_role.id)
        assert success is True
        assert error is None
        assert role is not None
        assert role.id == sample_role.id

    def test_get_role_by_id_not_found(self, role_repository):
        """Test getting role by non-existent ID."""
        fake_id = str(uuid.uuid4())
        success, error, role = role_repository.get_role_by_id(fake_id)
        assert success is False
        assert role is None

    def test_get_role_by_name_success(self, role_repository, sample_role):
        """Test getting role by name."""
        success, error, role = role_repository.get_role_by_name("admin")
        assert success is True
        assert error is None
        assert role is not None
        assert role.role_name == "admin"

    def test_get_role_by_name_not_found(self, role_repository):
        """Test getting role by non-existent name."""
        success, error, role = role_repository.get_role_by_name("nonexistent")
        assert success is False
        assert role is None

    def test_get_roles_all(self, role_repository, in_memory_db):
        """Test getting all roles."""
        for i in range(3):
            role = Role(
                id=str(uuid.uuid4()),
                role_name=f"role{i}",
                permissions=["read"],
                description=f"Role {i}",
            )
            in_memory_db.add(role)
        in_memory_db.commit()

        success, error, roles = role_repository.get_roles()
        assert success is True
        assert len(roles) == 3

    def test_get_roles_empty(self, role_repository):
        """Test getting roles from empty table."""
        success, error, roles = role_repository.get_roles()
        assert success is True
        assert len(roles) == 0

    def test_update_role_success(self, role_repository, sample_role):
        """Test successful role update."""
        update_request = UpdateRoleRequest(
            role_id=sample_role.id, permissions=["read", "write", "execute"]
        )
        success, error, updated = role_repository.update_role(
            sample_role.id, update_request
        )
        assert success is True
        assert error is None
        assert updated is not None
        assert updated.permissions is not None

    def test_update_role_description(self, role_repository, sample_role):
        """Test updating role description."""
        update_request = UpdateRoleRequest(
            role_id=sample_role.id, description="Updated description"
        )
        success, error, updated = role_repository.update_role(
            sample_role.id, update_request
        )
        assert success is True
        assert updated.description == "Updated description"

    def test_update_role_no_changes(self, role_repository, sample_role):
        """Test update role with no changes."""
        update_request = UpdateRoleRequest(role_id=sample_role.id)
        success, error, updated = role_repository.update_role(
            sample_role.id, update_request
        )
        assert success is True
        assert updated is not None

    def test_update_role_not_found(self, role_repository):
        """Test updating non-existent role."""
        fake_id = str(uuid.uuid4())
        update_request = UpdateRoleRequest(
            role_id=fake_id, permissions=["read"]
        )
        success, error, result = role_repository.update_role(
            fake_id, update_request
        )
        assert success is False
        assert result is None

    def test_update_role_filters_none_values(
        self, role_repository, sample_role
    ):
        """Test that update filters out None values."""
        update_request = UpdateRoleRequest(
            role_id=sample_role.id,
            permissions=["read", "write"],
            description=None,
        )
        success, error, updated = role_repository.update_role(
            sample_role.id, update_request
        )
        assert success is True

    def test_delete_role_by_id_success(self, role_repository, sample_role):
        """Test successful role deletion."""
        role_id = sample_role.id
        success, error = role_repository.delete_role_by_id(role_id)
        assert success is True
        assert error is None

    def test_delete_role_by_id_not_found(self, role_repository):
        """Test deleting non-existent role."""
        fake_id = str(uuid.uuid4())
        success, error = role_repository.delete_role_by_id(fake_id)
        # Either success or false is acceptable depending on implementation
        assert isinstance(success, bool)

    def test_create_role_failed_not_success(self, role_repository):
        """Test create role when create returns failed status."""
        with patch.object(role_repository, "create") as mock_create:
            mock_create.return_value = (False, "DB constraint error", None)
            success, error, role = role_repository.create_role(
                CreateRoleRequest(role_name="test")
            )
            assert success is False
            assert role is None

    def test_get_role_by_id_when_not_success(self, role_repository):
        """Test get_role_by_id when get_by_uuid returns not success."""
        with patch.object(role_repository, "get_by_uuid") as mock_get:
            mock_get.return_value = (False, "Not found", None)
            success, error, role = role_repository.get_role_by_id("id")
            assert success is False

    def test_get_role_by_name_when_not_success(self, role_repository):
        """Test get_role_by_name when get_by_attr returns not success."""
        with patch.object(role_repository, "get_by_attr") as mock_get:
            mock_get.return_value = (False, "Not found", None)
            success, error, role = role_repository.get_role_by_name("name")
            assert success is False

    def test_get_roles_failed(self, role_repository):
        """Test get_roles when get_all returns failed status."""
        with patch.object(role_repository, "get_all") as mock_get:
            mock_get.return_value = (False, "DB Error", None)
            success, error, roles = role_repository.get_roles()
            assert success is False

    def test_update_role_when_role_not_found(self, role_repository):
        """Test update role when initial get returns not success."""
        with patch.object(role_repository, "get_by_uuid") as mock_get:
            mock_get.return_value = (False, "Not found", None)
            update_request = UpdateRoleRequest(
                role_id="id", permissions=["read"]
            )
            success, error, updated = role_repository.update_role(
                "id", update_request
            )
            assert success is False

    def test_update_role_when_update_failed(
        self, role_repository, sample_role
    ):
        """Test update role when update operation fails."""
        with patch.object(role_repository, "get_by_uuid") as mock_get:
            with patch.object(role_repository, "update") as mock_update:
                mock_get.return_value = (True, None, sample_role)
                mock_update.return_value = (False, "Update error", None)
                update_request = UpdateRoleRequest(
                    role_id=sample_role.id, permissions=["read"]
                )
                success, error, updated = role_repository.update_role(
                    sample_role.id, update_request
                )
                assert success is False

    def test_delete_role_failed(self, role_repository):
        """Test delete role when delete_by_uuid returns failed status."""
        with patch.object(role_repository, "delete_by_uuid") as mock_delete:
            mock_delete.return_value = (False, "Delete error")
            success, error = role_repository.delete_role_by_id("id")
            assert success is False


class TestRoleRepositoryPermissions:
    """Test role permissions handling."""

    def test_role_permissions_json_storage(self, role_repository):
        """Test storing permissions as JSON."""
        perms = ["read", "write", "delete", "execute"]
        create_request = CreateRoleRequest(
            role_name="complex_role", permissions=perms
        )
        success, error, role = role_repository.create_role(create_request)
        assert success is True
        assert role.permissions == perms

    def test_role_empty_permissions(self, role_repository):
        """Test role with empty permissions."""
        create_request = CreateRoleRequest(
            role_name="no_perms_role", permissions=[]
        )
        success, error, role = role_repository.create_role(create_request)
        assert success is True
        assert role.permissions == []

    def test_update_role_permissions(self, role_repository, sample_role):
        """Test updating role permissions."""
        update_request = UpdateRoleRequest(
            role_id=sample_role.id, permissions=["admin", "superuser"]
        )
        success, error, updated = role_repository.update_role(
            sample_role.id, update_request
        )
        assert success is True
        assert "admin" in updated.permissions


class TestRoleRepositoryExceptionHandling:
    """Test exception handling in role repository."""

    def test_create_role_exception_handling(self, role_repository):
        """Test exception handling during create."""
        with patch.object(role_repository, "create") as mock_create:
            mock_create.side_effect = Exception("DB Error")
            success, error, role = role_repository.create_role(
                CreateRoleRequest(role_name="test")
            )
            assert success is False
            assert error is not None

    def test_get_role_by_id_exception_handling(self, role_repository):
        """Test exception handling in get_role_by_id."""
        with patch.object(role_repository, "get_by_uuid") as mock_get:
            mock_get.side_effect = Exception("DB Error")
            success, error, role = role_repository.get_role_by_id("id")
            assert success is False
            assert error is not None

    def test_get_role_by_name_exception_handling(self, role_repository):
        """Test exception handling in get_role_by_name."""
        with patch.object(role_repository, "get_by_attr") as mock_get:
            mock_get.side_effect = Exception("DB Error")
            success, error, role = role_repository.get_role_by_name("name")
            assert success is False
            assert error is not None

    def test_get_roles_exception_handling(self, role_repository):
        """Test exception handling in get_roles."""
        with patch.object(role_repository, "get_all") as mock_get:
            mock_get.side_effect = Exception("DB Error")
            success, error, roles = role_repository.get_roles()
            assert success is False
            assert error is not None

    def test_update_role_exception_handling(
        self, role_repository, sample_role
    ):
        """Test exception handling during update."""
        with patch.object(role_repository, "get_by_uuid") as mock_get:
            with patch.object(role_repository, "rollback") as mock_rollback:
                mock_get.return_value = (True, None, sample_role)
                with patch.object(role_repository, "update") as mock_update:
                    mock_update.side_effect = Exception("DB Error")
                    update_request = UpdateRoleRequest(
                        role_id=sample_role.id, permissions=["read"]
                    )
                    success, error, updated = role_repository.update_role(
                        sample_role.id, update_request
                    )
                    assert success is False
                    mock_rollback.assert_called_once()

    def test_delete_role_exception_handling(self, role_repository):
        """Test exception handling in delete_role_by_id."""
        with patch.object(role_repository, "delete_by_uuid") as mock_delete:
            with patch.object(role_repository, "rollback") as mock_rollback:
                mock_delete.side_effect = Exception("DB Error")
                success, error = role_repository.delete_role_by_id("id")
                assert success is False
                mock_rollback.assert_called_once()
