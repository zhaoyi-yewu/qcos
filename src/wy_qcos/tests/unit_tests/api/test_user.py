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

from wy_qcos.api.posiq.routes_jsonrpc.user import (
    get_user_mgmt_status,
    create_user,
    get_user,
    get_users,
    update_user,
    delete_user,
    create_role,
    get_role,
    get_roles,
    update_role,
    delete_role,
    change_password,
    get_login_logs,
    get_user_response,
    get_role_response,
    _mask_hidden_fields,
    get_user_manager,
)
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager


class TestMaskHiddenFields:
    """Test cases for _mask_hidden_fields function."""

    def test_mask_primitive_types(self):
        """Test masking primitive types."""
        assert _mask_hidden_fields("test") == "test"
        assert _mask_hidden_fields(123) == 123
        assert _mask_hidden_fields(True) is True
        assert _mask_hidden_fields(None) is None

    def test_mask_dict(self):
        """Test masking dictionary."""
        data = {"name": "test", "value": 123}
        result = _mask_hidden_fields(data)
        assert result == {"name": "test", "value": 123}

    def test_mask_list(self):
        """Test masking list."""
        data = [1, 2, 3, "test"]
        result = _mask_hidden_fields(data)
        assert result == [1, 2, 3, "test"]

    def test_mask_nested_structure(self):
        """Test masking nested structure."""
        data = {
            "users": [
                {"name": "user1", "details": {"age": 25}},
                {"name": "user2", "details": {"age": 30}},
            ]
        }
        result = _mask_hidden_fields(data)
        assert result == data

    def test_mask_pydantic_model(self):
        """Test masking Pydantic model."""
        user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed_password"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        result = _mask_hidden_fields(user)
        assert isinstance(result, dict)
        assert "user_name" in result
        assert result["user_name"] == "testuser"


class TestGetUserResponse:
    """Test cases for get_user_response function."""

    def test_get_user_response(self):
        """Test formatting user response."""
        user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed_password"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        result = get_user_response(user)
        assert "user_name" in result
        assert result["user_name"] == "testuser"
        assert "roles" in result
        assert result["roles"] == ["user"]
        assert "is_enabled" in result
        assert result["is_enabled"] is True


class TestGetRoleResponse:
    """Test cases for get_role_response function."""

    def test_get_role_response(self):
        """Test formatting role response."""
        role = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/test"],
            description="Test role",
        )
        result = get_role_response(role)
        assert "role_name" in result
        assert result["role_name"] == "testrole"
        assert "permissions" in result
        assert result["permissions"] == ["/v1/test"]


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


class TestGetUserMgmtStatus:
    """Test cases for get_user_mgmt_status function."""

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_get_user_mgmt_status(self, mock_config):
        """Test getting user management status."""
        mock_config.ENABLE_USER_MGMT = True
        mock_config.PASSWORD_EXPIRY_DAYS = 90
        mock_config.MAX_LOGIN_ATTEMPTS = 5
        mock_config.LOCKOUT_DURATION_MINUTES = 15

        result = get_user_mgmt_status()

        assert result.enabled is True
        assert result.password_expiry_days == 90
        assert result.max_login_attempts == 5
        assert result.lockout_duration_minutes == 15

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_get_user_mgmt_status_disabled(self, mock_config):
        """Test getting user management status when disabled."""
        mock_config.ENABLE_USER_MGMT = False
        mock_config.PASSWORD_EXPIRY_DAYS = 0

        result = get_user_mgmt_status()

        assert result.enabled is False


class TestCreateUser:
    """Test cases for create_user function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user.return_value = None
        mock.get_role.return_value = Mock(role_name="user")
        mock.create_user.return_value = user_schemas.User(
            user_name="newuser",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return mock

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_create_user_success(
        self, mock_config, mock_user_manager
    ):
        """Test successful user creation."""
        mock_config.PASSWORD_EXPIRY_DAYS = 90

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_username.return_value = (
            False, None, None
        )
        new_user = user_schemas.User(
            user_name="newuser",
            hashed_password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_users_repo.create_user.return_value = (
            True, None, new_user
        )
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True,
            None,
            Mock(role_name="user")
        )

        body = user_schemas.CreateUserRequest(
            user_name="newuser",
            password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
        )

        result = create_user(
            body,
            mock_request,
            mock_user_manager,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo,
        )

        assert result is not None
        assert result.user_name == "newuser"

    def test_create_user_duplicate(self, mock_user_manager):
        """Test creating user with duplicate name."""
        existing_user = user_schemas.User(
            user_name="existinguser",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.get_user.return_value = existing_user

        body = user_schemas.CreateUserRequest(
            user_name="existinguser",
            password=_s("password123"),
            roles=["user"],
        )

        with pytest.raises(Exception):
            create_user(body, None, mock_user_manager)


class TestGetUser:
    """Test cases for get_user function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        user_obj = user_schemas.User(
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
        mock.get_user_by_id = Mock(return_value=user_obj)
        return mock

    def test_get_user_success(self, mock_user_manager):
        """Test successful user retrieval."""
        mock_users_repo = Mock()
        user_obj = user_schemas.User(
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
        mock_users_repo.get_user_by_id.return_value = (
            True, None, user_obj
        )

        body = user_schemas.GetUserRequest(user_id="user-uuid-123")

        result = get_user(body, None, users_repo=mock_users_repo)

        assert result is not None
        assert result.user_name == "testuser"
        mock_users_repo.get_user_by_id.assert_called_once_with(
            "user-uuid-123"
        )

    def test_get_user_not_found(self, mock_user_manager):
        """Test getting non-existent user."""
        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (
            False, "Not found", None
        )

        body = user_schemas.GetUserRequest(user_id="nonexistent-uuid")

        with pytest.raises(Exception):
            get_user(body, None, users_repo=mock_users_repo)


class TestGetUsers:
    """Test cases for get_users function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        user1 = user_schemas.User(
            user_name="user1",
            hashed_password=_s("hashed1"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        user2 = user_schemas.User(
            user_name="user2",
            hashed_password=_s("hashed2"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock.get_users = Mock(return_value=[user1, user2])
        return mock

    def test_get_users_success(self, mock_user_manager):
        """Test successful retrieval of all users."""
        mock_users_repo = Mock()
        user1 = user_schemas.User(
            user_name="user1",
            hashed_password=_s("hashed1"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        user2 = user_schemas.User(
            user_name="user2",
            hashed_password=_s("hashed2"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_users_repo.get_users.return_value = (
            True, None, [user1, user2]
        )

        result = get_users(None, None, users_repo=mock_users_repo)

        assert isinstance(result, dict)
        assert len(result) == 2
        assert "user1" in result
        assert "user2" in result


class TestUpdateUser:
    """Test cases for update_user function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user_by_id = Mock(return_value=user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))
        mock.get_roles.return_value = {
            "user": Mock(role_name="user"),
            "admin": Mock(role_name="admin"),
        }
        mock.update_user.return_value = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=180,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock.permission_manager = Mock()
        mock.reload_role_permissions_from_db = Mock(return_value=True)
        return mock

    def test_update_user_success(self, mock_user_manager):
        """Test successful user update."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (
            True, None, Mock(user_name="testuser")
        )
        updated_user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=180,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_users_repo.update_user.return_value = (
            True, None, updated_user
        )
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True, None, Mock(role_name="admin")
        )

        body = user_schemas.UpdateUserRequest(
            user_id="user-uuid-123",
            roles=["admin"],
            password_expiry_days=180,
        )

        result = update_user(
            body, mock_request, mock_user_manager,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo
        )

        assert result is not None
        assert result.user_name == "testuser"


class TestDeleteUser:
    """Test cases for delete_user function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        user_obj = user_schemas.User(
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
        mock.get_user_by_id = Mock(return_value=user_obj)
        return mock

    def test_delete_user_success(self, mock_user_manager):
        """Test successful user deletion."""
        mock_users_repo = Mock()
        user_obj = user_schemas.User(
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
        mock_users_repo.get_user_by_id.return_value = (
            True, None, user_obj
        )
        # delete_user_by_id returns 2-tuple (success, error)
        mock_users_repo.delete_user_by_id.return_value = (
            True, None
        )

        body = user_schemas.DeleteUserRequest(user_id="user-uuid-123")

        result = delete_user(body, None, users_repo=mock_users_repo)

        assert result is not None
        assert result.user_name == "testuser"

    def test_delete_admin_user(self, mock_user_manager):
        """Test deleting admin user (should fail)."""
        admin_user = user_schemas.User(
            user_name=Constant.DEFAULT_ADMIN_USERNAME,
            hashed_password=_s("hashed"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.get_user_by_id = Mock(return_value=admin_user)

        body = user_schemas.DeleteUserRequest(user_id="admin-uuid")

        with pytest.raises(Exception):
            delete_user(body, None, mock_user_manager)


class TestCreateRole:
    """Test cases for create_role function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_role.return_value = None
        mock.get_default_policies.return_value = [
            "/v1/auth/get_current_user_info",
            "/v1/device/get_device",
        ]
        mock.create_role.return_value = user_schemas.Role(
            role_name="newrole",
            permissions=["/v1/device/get_device"],
            description="New role",
        )
        return mock

    def test_create_role_success(self, mock_user_manager):
        """Test successful role creation."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            False, None, None
        )
        new_role = user_schemas.Role(
            role_name="newrole",
            permissions=["/v1/device/get_device"],
            description="New role",
        )
        mock_roles_repo.create_role.return_value = (
            True, None, new_role
        )

        body = user_schemas.CreateRoleRequest(
            role_name="newrole",
            permissions=["/v1/device/get_device"],
            description="New role",
        )

        result = create_role(
            body, mock_request, mock_user_manager,
            roles_repo=mock_roles_repo
        )

        assert result is not None
        assert result.role_name == "newrole"

    def test_create_role_duplicate(self, mock_user_manager):
        """Test creating duplicate role."""
        existing_role = user_schemas.Role(
            role_name="existingrole",
            permissions=["/v1/device/get_device"],
            description="Existing role",
        )
        mock_user_manager.get_role.return_value = existing_role

        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True, None, existing_role
        )

        body = user_schemas.CreateRoleRequest(
            role_name="existingrole",
            permissions=["/v1/device/get_device"],
        )

        with pytest.raises(Exception):
            create_role(
                body, None, mock_user_manager,
                roles_repo=mock_roles_repo
            )


class TestGetRole:
    """Test cases for get_role function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        role_obj = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )
        mock.get_role_by_id = Mock(return_value=role_obj)
        return mock

    def test_get_role_success(self, mock_user_manager):
        """Test successful role retrieval."""
        mock_roles_repo = Mock()
        role_obj = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )
        mock_roles_repo.get_role_by_id.return_value = (
            True, None, role_obj
        )

        body = user_schemas.GetRoleRequest(role_id="testrole")

        result = get_role(body, None, roles_repo=mock_roles_repo)

        assert result is not None
        assert result.role_name == "testrole"


class TestGetRoles:
    """Test cases for get_roles function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        admin_role = user_schemas.Role(
            role_name="admin",
            permissions=["*"],
            description="Administrator",
        )
        user_role = user_schemas.Role(
            role_name="user",
            permissions=["/v1/device/get_device"],
            description="Regular user",
        )
        mock.get_roles = Mock(return_value=[admin_role, user_role])
        return mock

    def test_get_roles_success(self, mock_user_manager):
        """Test successful retrieval of all roles."""
        mock_roles_repo = Mock()
        admin_role = user_schemas.Role(
            role_name="admin",
            permissions=["*"],
            description="Administrator",
        )
        user_role = user_schemas.Role(
            role_name="user",
            permissions=["/v1/device/get_device"],
            description="Regular user",
        )
        mock_roles_repo.get_roles.return_value = (
            True, None, [admin_role, user_role]
        )

        result = get_roles(None, None, roles_repo=mock_roles_repo)

        assert isinstance(result, dict)
        assert len(result) == 2
        assert "admin" in result
        assert "user" in result


class TestUpdateRole:
    """Test cases for update_role function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_roles.return_value = {
            "testrole": user_schemas.Role(
                role_name="testrole",
                permissions=["/v1/device/get_device"],
                description="Test role",
            )
        }
        mock.get_default_policies.return_value = [
            "/v1/auth/get_current_user_info",
            "/v1/device/get_device",
            "/v1/device/get_devices",
        ]
        mock.update_role.return_value = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device", "/v1/device/get_devices"],
            description="Updated role",
        )
        return mock

    def test_update_role_success(self, mock_user_manager):
        """Test successful role update."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_roles_repo = Mock()
        existing_role = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )
        mock_roles_repo.get_role_by_id.return_value = (
            True, None, existing_role
        )
        updated_role = user_schemas.Role(
            role_name="testrole",
            permissions=[
                "/v1/device/get_device", "/v1/device/get_devices"
            ],
            description="Updated role",
        )
        mock_roles_repo.update_role.return_value = (
            True, None, updated_role
        )

        body = user_schemas.UpdateRoleRequest(
            role_id="testrole",
            permissions=[
                "/v1/device/get_device", "/v1/device/get_devices"
            ],
            description="Updated role",
        )

        result = update_role(
            body, mock_request, mock_user_manager,
            roles_repo=mock_roles_repo
        )

        assert result is not None
        assert result.role_name == "testrole"


class TestDeleteRole:
    """Test cases for delete_role function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_roles.return_value = {
            "testrole": user_schemas.Role(
                role_name="testrole",
                permissions=["/v1/device/get_device"],
                description="Test role",
            )
        }
        mock.find_users_by_role.return_value = []
        return mock

    def test_delete_role_success(self, mock_user_manager):
        """Test successful role deletion."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_roles_repo = Mock()
        role_obj = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )
        mock_roles_repo.get_role_by_id.return_value = (
            True, None, role_obj
        )
        # delete_role_by_id returns 2-tuple (success, error)
        mock_roles_repo.delete_role_by_id.return_value = (
            True, None
        )

        mock_users_repo = Mock()
        mock_users_repo.find_users_by_role.return_value = (
            True, None, []
        )
        mock_users_repo.get_users.return_value = (
            True, None, []
        )
        mock_users_repo.get_user_by_username.return_value = (
            True, None, Mock(id="user-uuid-123")
        )

        # Mock user_manager requires these for reload
        mock_user_manager.reload_role_permissions_from_db = Mock(
            return_value=True
        )

        body = user_schemas.DeleteRoleRequest(role_id="testrole")

        result = delete_role(
            body, mock_request, mock_user_manager,
            roles_repo=mock_roles_repo,
            users_repo=mock_users_repo
        )

        assert result is not None
        assert result.role_name == "testrole"

    def test_delete_admin_role(self, mock_user_manager):
        """Test deleting admin role (should fail)."""
        admin_role = user_schemas.Role(
            role_name=Constant.ROLE_ADMIN,
            permissions=["*"],
            description="Administrator",
        )
        mock_user_manager.get_roles.return_value = {
            Constant.ROLE_ADMIN: admin_role
        }

        body = user_schemas.DeleteRoleRequest(role_id=Constant.ROLE_ADMIN)

        with pytest.raises(Exception):
            delete_role(body, None, mock_user_manager)


class TestChangePassword:
    """Test cases for change_password function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user_by_id = Mock(return_value=user_schemas.User(
            user_name="testuser",
            hashed_password=UserManager.hash_password("old_password"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))
        return mock

    def test_change_password_success(self, mock_user_manager):
         """Test successful password change."""
         mock_users_repo = Mock()
         user_obj = user_schemas.User(
             user_name="testuser",
             hashed_password=UserManager.hash_password("old_password"),
             roles=["user"],
             is_enabled=True,
             is_locked=False,
             password_expiry_days=90,
             password_changed_at=datetime.now(),
             created_at=datetime.now(),
             updated_at=datetime.now(),
         )
         mock_users_repo.get_user_by_id.return_value = (
             True, None, user_obj
         )
         mock_users_repo.update_user.return_value = (
             True, None, user_obj
         )

         body = user_schemas.ChangePasswordRequest(
             user_id="user-uuid-123",
             old_password=_s("old_password"),
             new_password=_s("new_password123"),
         )

         result = change_password(
             body, None, users_repo=mock_users_repo
         )

         assert result is not None
         assert result.message == "Password changed successfully"

    def test_change_password_incorrect_old(self, mock_user_manager):
        """Test password change with incorrect old password."""
        body = user_schemas.ChangePasswordRequest(
            user_id="user-uuid-123",
            old_password=_s("wrong_password"),
            new_password=_s("new_password123"),
        )

        with pytest.raises(Exception):
            change_password(body, None, mock_user_manager)


class TestGetLoginLogs:
    """Test cases for get_login_logs function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        logs = [
            user_schemas.LoginLog(
                user_name="testuser",
                ip_address="192.168.1.1",
                login_time=datetime.now() - timedelta(hours=1),
                success=True,
                user_agent="Mozilla/5.0",
            ),
            user_schemas.LoginLog(
                user_name="testuser",
                ip_address="192.168.1.2",
                login_time=datetime.now() - timedelta(hours=2),
                success=False,
                failure_reason="Invalid password",
            ),
        ]
        mock.get_login_logs = Mock(return_value=logs)
        user_obj = user_schemas.User(
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
        mock.get_user_by_id = Mock(return_value=user_obj)
        return mock

    def test_get_login_logs_success(self, mock_user_manager):
        """Test successful retrieval of login logs."""
        mock_users_repo = Mock()
        now = datetime.now()
        # Create login logs with datetime for login_time (not ISO string)
        logs = [
            Mock(
                user_name="testuser",
                ip_address="192.168.1.1",
                login_time=now,
                user_agent="Mozilla/5.0",
                login_status=True,
                failure_reason=None,
            ),
            Mock(
                user_name="testuser",
                ip_address="192.168.1.2",
                login_time=now - timedelta(hours=1),
                user_agent=None,
                login_status=False,
                failure_reason="Invalid password",
            ),
        ]
        mock_users_repo.get_login_logs.return_value = (True, None, logs)
        mock_users_repo.get_user_by_username.return_value = (
            True, None, Mock(id="user-uuid-123")
        )

        body = user_schemas.GetLoginLogsRequest()

        result = get_login_logs(body, None, users_repo=mock_users_repo)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_login_logs_with_pagination(self, mock_user_manager):
        """Test login logs with pagination."""
        mock_users_repo = Mock()
        now = datetime.now()
        logs = [
            Mock(
                user_name="testuser",
                ip_address="192.168.1.1",
                login_time=now,
                user_agent="Mozilla/5.0",
                login_status=True,
                failure_reason=None,
            ),
        ]
        mock_users_repo.get_login_logs.return_value = (True, None, logs)
        mock_users_repo.get_user_by_username.return_value = (
            True, None, Mock(id="user-uuid-123")
        )

        body = user_schemas.GetLoginLogsRequest(limit=1, offset=0)

        result = get_login_logs(body, None, users_repo=mock_users_repo)

        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_login_logs_sorted_descending(self, mock_user_manager):
        """Test that login logs are sorted descending."""
        mock_users_repo = Mock()
        now = datetime.now()
        logs = [
            Mock(
                user_name="testuser",
                ip_address="192.168.1.1",
                login_time=now,
                user_agent="Mozilla/5.0",
                login_status=True,
                failure_reason=None,
            ),
            Mock(
                user_name="testuser",
                ip_address="192.168.1.2",
                login_time=now - timedelta(hours=1),
                user_agent=None,
                login_status=False,
                failure_reason="Invalid password",
            ),
        ]
        mock_users_repo.get_login_logs.return_value = (True, None, logs)
        mock_users_repo.get_user_by_username.return_value = (
            True, None, Mock(id="user-uuid-123")
        )

        body = user_schemas.GetLoginLogsRequest()

        result = get_login_logs(body, None, users_repo=mock_users_repo)

        assert len(result) == 2
        # login_time now is ISO string after conversion
        assert result[0].login_time >= result[1].login_time




class TestBoundaryConditions:
    """Test cases for boundary conditions in user management."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user.return_value = None
        mock.get_role.return_value = None
        return mock

    def test_create_user_with_minimum_length_username(
        self, mock_user_manager
    ):
        """Test creating user with minimum length username."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_username.return_value = (
            False, None, None
        )
        min_user = user_schemas.User(
            user_name="abc",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_users_repo.create_user.return_value = (
            True, None, min_user
        )
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True, None, Mock(role_name="user")
        )

        body = user_schemas.CreateUserRequest(
            user_name="abc",
            password=_s("password123"),
            roles=["user"],
        )

        result = create_user(
            body, mock_request, mock_user_manager,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo
        )
        assert result is not None

    def test_create_user_with_maximum_length_username(
        self, mock_user_manager
    ):
        """Test creating user with maximum length username."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()

        long_username = "a" * Constant.MAX_USER_LENGTH

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_username.return_value = (
            False, None, None
        )
        max_user = user_schemas.User(
            user_name=long_username,
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_users_repo.create_user.return_value = (
            True, None, max_user
        )
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True, None, Mock(role_name="user")
        )

        body = user_schemas.CreateUserRequest(
            user_name=long_username,
            password=_s("password123"),
            roles=["user"],
        )

        result = create_user(
            body, mock_request, mock_user_manager,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo
        )
        assert result is not None

    def test_create_role_with_no_permissions(self, mock_user_manager):
        """Test creating role with no permissions."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_user_manager.create_role.return_value = (
            user_schemas.Role(
                role_name="empty_role",
                permissions=[],
                description="Empty role",
            )
        )

        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            False, None, None
        )
        mock_roles_repo.create_role.return_value = (
            True, None, user_schemas.Role(
                role_name="empty_role",
                permissions=[],
                description="Empty role",
            )
        )

        body = user_schemas.CreateRoleRequest(
            role_name="empty_role",
            permissions=[],
        )

        result = create_role(
            body, mock_request, mock_user_manager,
            roles_repo=mock_roles_repo
        )
        assert result is not None
        assert result.permissions == []

    def test_create_role_with_wildcard_permission(self, mock_user_manager):
        """Test creating role with wildcard permission."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            False, None, None
        )
        wildcard_role = user_schemas.Role(
            role_name="full_access_role",
            permissions=["*"],
            description="Full access role",
        )
        mock_roles_repo.create_role.return_value = (
            True, None, wildcard_role
        )

        body = user_schemas.CreateRoleRequest(
            role_name="full_access_role",
            permissions=["*"],
        )

        result = create_role(
            body, mock_request, mock_user_manager,
            roles_repo=mock_roles_repo
        )
        assert result is not None
        assert "*" in result.permissions


class TestErrorHandlingChains:
    """Test error handling chains for user management APIs."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        return mock

    def test_create_user_with_invalid_role(self, mock_user_manager):
        """Test creating user with invalid role."""
        mock_user_manager.get_user.return_value = None
        mock_user_manager.get_role.return_value = None

        body = user_schemas.CreateUserRequest(
            user_name="testuser",
            password=_s("password123"),
            roles=["nonexistent_role"],
        )

        with pytest.raises(Exception):
            create_user(body, None, mock_user_manager)

    def test_delete_admin_user_fails(self, mock_user_manager):
        """Test that deleting admin user fails."""
        admin_user = user_schemas.User(
            user_name=Constant.DEFAULT_ADMIN_USERNAME,
            hashed_password=_s("hashed"),
            roles=["admin"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.get_user_by_id = Mock(return_value=admin_user)

        body = user_schemas.DeleteUserRequest(user_id="admin-uuid")

        with pytest.raises(Exception):
            delete_user(body, None, mock_user_manager)

    def test_update_user_to_invalid_role(self, mock_user_manager):
        """Test updating user with invalid role."""
        mock_user_manager.get_user_by_id = Mock(return_value=(
            user_schemas.User(
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
        ))
        mock_user_manager.get_roles.return_value = {
            "user": Mock(role_name="user")
        }

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (
            True, None, Mock(user_name="testuser")
        )
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            False, None, None
        )

        body = user_schemas.UpdateUserRequest(
            user_id="testuser-uuid",
            roles=["admin"],
        )

        with pytest.raises(Exception):
            update_user(
                body, None, mock_user_manager,
                users_repo=mock_users_repo,
                roles_repo=mock_roles_repo
            )

    def test_create_duplicate_role(self, mock_user_manager):
        """Test creating duplicate role."""
        existing_role = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
        )
        mock_user_manager.get_role.return_value = existing_role

        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True, None, existing_role
        )

        body = user_schemas.CreateRoleRequest(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
        )

        with pytest.raises(Exception):
            create_role(
                body, None, mock_user_manager,
                roles_repo=mock_roles_repo
            )


class TestUserStatusManagement:
    """Test user status management (enabled/disabled, locked/unlocked)."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        return mock

    def test_disable_user(self, mock_user_manager):
        """Test disabling a user."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()

        disabled_user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=False,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.get_user_by_id = Mock(return_value=(
            user_schemas.User(
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
        ))
        mock_user_manager.update_user.return_value = disabled_user

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (
            True, None, Mock(user_name="testuser")
        )
        mock_users_repo.update_user.return_value = (
            True, None, disabled_user
        )
        mock_roles_repo = Mock()

        body = user_schemas.UpdateUserRequest(
            user_id="testuser-uuid", is_enabled=False
        )

        result = update_user(
            body, mock_request, mock_user_manager,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo
        )
        assert result.is_enabled is False

    def test_lock_user_account(self, mock_user_manager):
        """Test locking user account."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()

        locked_user = user_schemas.User(
            user_name="testuser",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=True,
            is_locked=True,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.get_user_by_id = Mock(return_value=(
            user_schemas.User(
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
        ))
        mock_user_manager.update_user.return_value = locked_user

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (
            True, None, Mock(user_name="testuser")
        )
        mock_users_repo.update_user.return_value = (
            True, None, locked_user
        )
        mock_roles_repo = Mock()

        body = user_schemas.UpdateUserRequest(
            user_id="testuser-uuid", is_locked=True
        )

        result = update_user(
            body, mock_request, mock_user_manager,
            users_repo=mock_users_repo,
            roles_repo=mock_roles_repo
        )
        assert result.is_locked is True

    def test_cannot_login_when_disabled(self, mock_user_manager):
        """Test that disabled user cannot login."""
        disabled_user = user_schemas.User(
            user_name="disabled_user",
            hashed_password=_s("hashed"),
            roles=["user"],
            is_enabled=False,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.get_user.return_value = disabled_user

        assert disabled_user.is_enabled is False

