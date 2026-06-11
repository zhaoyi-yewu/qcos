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
import uuid

from wy_qcos.api.posiq.routes_jsonrpc.user import (
    get_user_mgmt,
    set_user_mgmt,
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
    clear_login_logs,
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


class TestGetUserMgmt:
    """Test cases for get_user_mgmt function."""

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_get_user_mgmt(self, mock_config):
        """Test getting user management status."""
        mock_config.DEFAULT.AUTH_MODE = Constant.AUTH_MODE_JWT
        mock_config.USERS.PASSWORD_EXPIRY_DAYS = 90
        mock_config.USERS.MAX_LOGIN_ATTEMPTS = 5
        mock_config.USERS.LOCKOUT_DURATION_MINUTES = 15

        result = get_user_mgmt()

        assert result.auth_mode == Constant.AUTH_MODE_JWT
        assert result.password_expiry_days == 90
        assert result.max_login_attempts == 5
        assert result.lockout_duration_minutes == 15

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_get_user_mgmt_no_mode(self, mock_config):
        """Test getting user management status when disabled."""
        mock_config.DEFAULT.AUTH_MODE = Constant.AUTH_MODE_NO
        mock_config.USERS.PASSWORD_EXPIRY_DAYS = 0

        result = get_user_mgmt()

        assert result.auth_mode == Constant.AUTH_MODE_NO


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
    def test_create_user_success(self, mock_config, mock_user_manager):
        """Test successful user creation."""
        mock_config.PASSWORD_EXPIRY_DAYS = 90

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_username.return_value = (False, None, None)
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
        mock_users_repo.create_user.return_value = (True, None, new_user)
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (
            True,
            None,
            Mock(role_name="user"),
        )

        body = user_schemas.CreateUserRequest(
            user_name="newuser",
            password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
        )

        mock_projects_repo = Mock()
        mock_projects_repo.project_exists.return_value = (True, None, True)

        result = create_user(
            body,
            mock_request,
            mock_user_manager,
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
        Mock()
        user_id = str(uuid.uuid4())
        user_id_uuid = uuid.UUID(user_id)
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
        mock_user_manager.get_user_by_id = Mock(return_value=user_obj)

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.GetUserRequest(user_id=user_id)
        auth_data = {"user_id": user_id_uuid, "roles": ["admin"]}

        result = get_user(body, mock_request, auth_data)

        assert result is not None
        assert result.user_name == "testuser"

    def test_get_user_not_found(self, mock_user_manager):
        """Test getting non-existent user."""
        mock_user_manager.get_user_by_id = Mock(return_value=None)

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        user_id = str(uuid.uuid4())
        body = user_schemas.GetUserRequest(user_id=user_id)

        with pytest.raises(Exception):
            get_user(body, mock_request, None)


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
        mock_user_manager.get_users = Mock(
            return_value={"uid1": user1, "uid2": user2}
        )

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        result = get_users(mock_request, None, None)

        assert isinstance(result, dict)
        assert len(result) == 2
        # Check that user names are in the response values
        user_names = [user.user_name for user in result.values()]
        assert "user1" in user_names
        assert "user2" in user_names


class TestUpdateUser:
    """Test cases for update_user function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user_by_id = Mock(
            return_value=user_schemas.User(
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
        )
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

        user_id = str(uuid.uuid4())
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
        mock_user_manager.update_user = Mock(return_value=updated_user)

        body = user_schemas.UpdateUserRequest(
            user_id=user_id,
            roles=["admin"],
            password_expiry_days=180,
        )

        result = update_user(
            body,
            mock_request,
            None,
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
        user_id = str(uuid.uuid4())
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
        mock_user_manager.get_user_by_id = Mock(return_value=user_obj)
        mock_user_manager.delete_user = Mock(return_value=user_obj)

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.DeleteUserRequest(user_id=user_id)

        result = delete_user(body, mock_request, None)

        assert result is not None
        assert result.user_name == "testuser"

    def test_delete_admin_user(self, mock_user_manager):
        """Test deleting admin user (should fail)."""
        admin_user = user_schemas.User(
            user_name=Constant.ADMIN_USERNAME,
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

        admin_id = str(uuid.uuid4())
        body = user_schemas.DeleteUserRequest(user_id=admin_id)

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

        new_role = user_schemas.Role(
            role_name="newrole",
            permissions=["/v1/device/get_device"],
            description="New role",
        )
        mock_user_manager.create_role = Mock(return_value=new_role)

        body = user_schemas.CreateRoleRequest(
            role_name="newrole",
            permissions=["/v1/device/get_device"],
            description="New role",
        )

        result = create_role(body, mock_request, None)
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
            True,
            None,
            existing_role,
        )

        body = user_schemas.CreateRoleRequest(
            role_name="existingrole",
            permissions=["/v1/device/get_device"],
        )

        with pytest.raises(Exception):
            create_role(body, None, mock_user_manager)

    @pytest.fixture
    def mock_user_manager_for_get_role(self):
        """Create a mock user manager for get_role."""
        mock = Mock(spec=UserManager)
        role_obj = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )
        mock.get_role_by_id = Mock(return_value=role_obj)
        return mock

    def test_get_role_success(self, mock_user_manager_for_get_role):
        """Test successful role retrieval."""
        role_id = str(uuid.uuid4())
        role_obj = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )
        mock_user_manager_for_get_role.get_role_by_id = Mock(
            return_value=role_obj
        )

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager_for_get_role

        body = user_schemas.GetRoleRequest(role_id=role_id)

        result = get_role(body, mock_request, None)

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
        mock_user_manager.get_roles = Mock(
            return_value={"admin_id": admin_role, "user_id": user_role}
        )

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        result = get_roles(mock_request, None, None)

        assert isinstance(result, dict)
        assert len(result) == 2
        # Check that role names are in the response values
        role_names = [role.role_name for role in result.values()]
        assert "admin" in role_names
        assert "user" in role_names


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

        role_id = str(uuid.uuid4())
        mock_roles_repo = Mock()
        existing_role = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )
        mock_roles_repo.get_role_by_id.return_value = (
            True,
            None,
            existing_role,
        )
        updated_role = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device", "/v1/device/get_devices"],
            description="Updated role",
        )
        mock_roles_repo.update_role.return_value = (True, None, updated_role)
        body = user_schemas.UpdateRoleRequest(
            role_id=role_id,
            permissions=["/v1/device/get_device", "/v1/device/get_devices"],
            description="Updated role",
        )
        result = update_role(body, mock_request, mock_user_manager)
        assert result is not None
        assert result.role_name == "testrole"
        result = update_role(body, mock_request, mock_user_manager)


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

        role_obj = user_schemas.Role(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
            description="Test role",
        )

        role_id = str(uuid.uuid4())
        mock_user_manager.get_role_by_id = Mock(return_value=role_obj)
        mock_user_manager.delete_role = Mock(return_value=role_obj)
        mock_user_manager.reload_role_permissions_from_db = Mock(
            return_value=True
        )

        body = user_schemas.DeleteRoleRequest(role_id=role_id)

        result = delete_role(
            body,
            mock_request,
            None,
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

        admin_role_id = str(uuid.uuid4())
        body = user_schemas.DeleteRoleRequest(role_id=admin_role_id)

        with pytest.raises(Exception):
            delete_role(body, None, mock_user_manager)


class TestChangePassword:
    """Test cases for change_password function."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user_by_id = Mock(
            return_value=user_schemas.User(
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
        )
        return mock

    def test_change_password_success(self, mock_user_manager):
        """Test successful password change."""
        user_id_str = str(uuid.uuid4())
        user_id_uuid = uuid.UUID(user_id_str)
        user_obj = user_schemas.User(
            id=user_id_uuid,
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
        mock_user_manager.change_password = Mock(return_value=user_obj)

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.ChangePasswordRequest(
            user_id=user_id_str,
            old_password=_s("old_password"),
            new_password=_s("new_password123"),
        )
        # admin role can change any user's password
        auth_data = {"user_id": user_id_uuid, "roles": ["admin"]}
        result = change_password(body, mock_request, auth_data)
        assert result is not None
        assert result.message == "Password changed successfully"

    def test_change_password_incorrect_old(self, mock_user_manager):
        """Test password change with incorrect old password."""
        user_id = str(uuid.uuid4())
        body = user_schemas.ChangePasswordRequest(
            user_id=user_id,
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
                login_status=True,
                user_agent="Mozilla/5.0",
            ),
            user_schemas.LoginLog(
                user_name="testuser",
                ip_address="192.168.1.2",
                login_time=datetime.now() - timedelta(hours=2),
                login_status=False,
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
        now = datetime.now()
        # Create proper login log dictionaries
        log1 = {
            "user_id": str(uuid.uuid4()),
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_name": "testuser",
            "ip_address": "192.168.1.1",
            "login_time": now.isoformat(),
            "user_agent": "Mozilla/5.0",
            "login_status": True,
            "failure_reason": None,
        }
        log2 = {
            "user_id": str(uuid.uuid4()),
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_name": "testuser",
            "ip_address": "192.168.1.2",
            "login_time": (now - timedelta(hours=1)).isoformat(),
            "user_agent": None,
            "login_status": False,
            "failure_reason": "Invalid password",
        }
        mock_user_manager.get_login_logs = Mock(return_value=[log1, log2])

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.GetLoginLogsRequest()

        result = get_login_logs(mock_request, body, None)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_login_logs_with_pagination(self, mock_user_manager):
        """Test login logs with pagination."""
        now = datetime.now()
        log = {
            "user_id": str(uuid.uuid4()),
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_name": "testuser",
            "ip_address": "192.168.1.1",
            "login_time": now.isoformat(),
            "user_agent": "Mozilla/5.0",
            "login_status": True,
            "failure_reason": None,
        }
        mock_user_manager.get_login_logs = Mock(return_value=[log])

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.GetLoginLogsRequest(limit=1, offset=0)

        result = get_login_logs(mock_request, body, None)

        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_login_logs_sorted_descending(self, mock_user_manager):
        """Test that login logs are sorted descending."""
        now = datetime.now()
        log1 = {
            "user_id": str(uuid.uuid4()),
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_name": "testuser",
            "ip_address": "192.168.1.1",
            "login_time": now.isoformat(),
            "user_agent": "Mozilla/5.0",
            "login_status": True,
            "failure_reason": None,
        }
        log2 = {
            "user_id": str(uuid.uuid4()),
            "project_id": Constant.DEFAULT_PROJECT_ID,
            "user_name": "testuser",
            "ip_address": "192.168.1.2",
            "login_time": (now - timedelta(hours=1)).isoformat(),
            "user_agent": None,
            "login_status": False,
            "failure_reason": "Invalid password",
        }
        mock_user_manager.get_login_logs = Mock(return_value=[log1, log2])

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.GetLoginLogsRequest()

        result = get_login_logs(mock_request, body, None)

        assert len(result) == 2
        # login_time now is ISO string after conversion
        assert result[0].login_time >= result[1].login_time


class TestClearLoginLogs:
    """Test cases for clear_login_logs function."""

    def test_clear_login_logs_all(self):
        """Test clearing all login logs."""
        mock_user_manager = Mock()
        mock_user_manager.clear_login_logs = Mock(return_value={"count": 42})

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.ClearLoginLogsRequest()

        result = clear_login_logs(mock_request, body, None)

        assert result is not None
        assert result["count"] == 42

    def test_clear_login_logs_for_user_id(self):
        """Test clearing login logs for a specific user by ID."""
        mock_user_manager = Mock()
        mock_user_manager.clear_login_logs = Mock(return_value={"count": 10})

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        user_id_str = "00000000-0000-4000-8000-000000000001"
        body = user_schemas.ClearLoginLogsRequest(user_id=user_id_str)
        result = clear_login_logs(mock_request, body, None)
        assert result is not None
        assert result["count"] == 10

    def test_clear_login_logs_for_user_name(self):
        """Test clearing login logs for a specific user by name."""
        mock_user_manager = Mock()
        mock_user_manager.clear_login_logs = Mock(return_value={"count": 5})

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.ClearLoginLogsRequest(user_name="testuser")

        result = clear_login_logs(mock_request, body, None)

        assert result is not None
        assert result["count"] == 5

    def test_clear_login_logs_user_not_found(self):
        """Test clearing logs when user is not found."""
        mock_user_manager = Mock()
        mock_user_manager.clear_login_logs = Mock(return_value={"count": 0})

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.ClearLoginLogsRequest(user_name="nonexistent")

        result = clear_login_logs(mock_request, body, None)

        assert result is not None
        assert result["count"] == 0

    def test_clear_login_logs_error(self):
        """Test clear_login_logs when database error occurs."""
        mock_users_repo = Mock()
        mock_users_repo.delete_login_logs.return_value = (
            False,
            "Database error",
            0,
        )

        body = user_schemas.ClearLoginLogsRequest()

        with pytest.raises(Exception):
            clear_login_logs(body, None)

    def test_clear_login_logs_both_parameters_error(self):
        """Test that specifying both user_id and user_name raises error."""
        from pydantic import ValidationError

        # ClearLoginLogsRequest should reject both parameters
        with pytest.raises(ValidationError):
            user_schemas.ClearLoginLogsRequest(
                user_id="00000000-0000-4000-8000-000000000001",
                user_name="testuser",
            )


class TestBoundaryConditions:
    """Test cases for boundary conditions in user management."""

    @pytest.fixture
    def mock_user_manager(self):
        """Create a mock user manager."""
        mock = Mock(spec=UserManager)
        mock.get_user.return_value = None
        mock.get_role.return_value = None
        return mock

    def test_create_user_with_minimum_length_username(self, mock_user_manager):
        """Test creating user with minimum length username."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

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
        mock_user_manager.create_user = Mock(return_value=min_user)

        body = user_schemas.CreateUserRequest(
            user_name="abc",
            password=_s("password123"),
            roles=["user"],
        )

        result = create_user(
            body,
            mock_request,
            None,
        )
        assert result is not None

    def test_create_user_with_maximum_length_username(self, mock_user_manager):
        """Test creating user with maximum length username."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        long_username = "a" * Constant.MAX_USER_LENGTH

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
        mock_user_manager.create_user = Mock(return_value=max_user)

        body = user_schemas.CreateUserRequest(
            user_name=long_username,
            password=_s("password123"),
            roles=["user"],
        )

        result = create_user(
            body,
            mock_request,
            None,
        )
        assert result is not None

    def test_create_role_with_no_permissions(self, mock_user_manager):
        """Test creating role with no permissions."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        mock_user_manager.create_role.return_value = user_schemas.Role(
            role_name="empty_role",
            permissions=[],
            description="Empty role",
        )

        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (False, None, None)
        mock_roles_repo.create_role.return_value = (
            True,
            None,
            user_schemas.Role(
                role_name="empty_role",
                permissions=[],
                description="Empty role",
            ),
        )

        body = user_schemas.CreateRoleRequest(
            role_name="empty_role",
            permissions=[],
        )

        result = create_role(body, mock_request, mock_user_manager)
        assert result is not None
        assert result.permissions == []

    def test_create_role_with_wildcard_permission(self, mock_user_manager):
        """Test creating role with wildcard permission."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        wildcard_role = user_schemas.Role(
            role_name="full_access_role",
            permissions=["*"],
            description="Full access role",
        )
        mock_user_manager.create_role = Mock(return_value=wildcard_role)

        body = user_schemas.CreateRoleRequest(
            role_name="full_access_role",
            permissions=["*"],
        )

        result = create_role(body, mock_request, mock_user_manager)
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
            user_name=Constant.ADMIN_USERNAME,
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

        admin_id = str(uuid.uuid4())
        body = user_schemas.DeleteUserRequest(user_id=admin_id)

        with pytest.raises(Exception):
            delete_user(body, None, mock_user_manager)

    def test_update_user_to_invalid_role(self, mock_user_manager):
        """Test updating user with invalid role."""
        mock_user_manager.get_user_by_id = Mock(
            return_value=(
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
            )
        )
        mock_user_manager.get_roles.return_value = {
            "user": Mock(role_name="user")
        }

        mock_users_repo = Mock()
        mock_users_repo.get_user_by_id.return_value = (
            True,
            None,
            Mock(user_name="testuser"),
        )
        mock_roles_repo = Mock()
        mock_roles_repo.get_role_by_name.return_value = (False, None, None)

        user_id = str(uuid.uuid4())
        body = user_schemas.UpdateUserRequest(
            user_id=user_id,
            roles=["admin"],
        )

        with pytest.raises(Exception):
            update_user(
                body,
                None,
                mock_user_manager,
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
            True,
            None,
            existing_role,
        )

        body = user_schemas.CreateRoleRequest(
            role_name="testrole",
            permissions=["/v1/device/get_device"],
        )

        with pytest.raises(Exception):
            create_role(body, None, mock_user_manager)


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
        mock_request.app.state._user_manager = mock_user_manager

        user_id = str(uuid.uuid4())
        disabled_user = user_schemas.User(
            id=user_id,
            project_id=Constant.DEFAULT_PROJECT_ID,
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
        mock_user_manager.update_user = Mock(return_value=disabled_user)

        body = user_schemas.UpdateUserRequest(
            user_id=user_id, is_enabled=False
        )

        result = update_user(
            body,
            mock_request,
            mock_user_manager,
        )
        assert result.is_enabled is False

    def test_lock_user_account(self, mock_user_manager):
        """Test locking user account."""
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._user_manager = mock_user_manager

        user_id = str(uuid.uuid4())
        locked_user = user_schemas.User(
            id=user_id,
            project_id=Constant.DEFAULT_PROJECT_ID,
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
        mock_user_manager.update_user = Mock(return_value=locked_user)

        body = user_schemas.UpdateUserRequest(user_id=user_id, is_locked=True)

        result = update_user(
            body,
            mock_request,
            None,
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


class TestAuthModeIntegration:
    """Test user management API with different auth modes."""

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_get_user_mgmt_with_no_mode(self, mock_config):
        """Test user management status with auth_mode=no."""
        mock_config.DEFAULT.AUTH_MODE = Constant.AUTH_MODE_NO
        mock_config.USERS.PASSWORD_EXPIRY_DAYS = 0

        result = get_user_mgmt()

        assert result.auth_mode == Constant.AUTH_MODE_NO

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_get_user_mgmt_with_jwt_mode(self, mock_config):
        """Test user management status with auth_mode=jwt."""
        mock_config.DEFAULT.AUTH_MODE = Constant.AUTH_MODE_JWT
        mock_config.USERS.PASSWORD_EXPIRY_DAYS = 90

        result = get_user_mgmt()

        assert result.auth_mode == Constant.AUTH_MODE_JWT
        assert result.password_expiry_days == 90

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_get_user_mgmt_with_virtual_instance_mode(self, mock_config):
        """Test user management status with auth_mode=virtual_instance."""
        mock_config.DEFAULT.AUTH_MODE = Constant.AUTH_MODE_VIRTUAL_INSTANCE
        mock_config.USERS.PASSWORD_EXPIRY_DAYS = 0

        result = get_user_mgmt()

        assert result.auth_mode == Constant.AUTH_MODE_VIRTUAL_INSTANCE

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_create_user_with_auth_mode_no(self, mock_config):
        """Test creating user when auth_mode=no (should still work)."""
        mock_config.AUTH_MODE = Constant.AUTH_MODE_NO
        mock_config.PASSWORD_EXPIRY_DAYS = 0

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()

        mock_user_manager = Mock(spec=UserManager)
        new_user = user_schemas.User(
            user_name="testuser_no_auth",
            hashed_password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.create_user = Mock(return_value=new_user)
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.CreateUserRequest(
            user_name="testuser_no_auth",
            password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
        )

        result = create_user(
            body,
            mock_request,
            None,
        )

        assert result is not None
        assert result.user_name == "testuser_no_auth"

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_create_user_with_auth_mode_jwt(self, mock_config):
        """Test creating user in JWT auth mode."""
        mock_config.AUTH_MODE = Constant.AUTH_MODE_JWT
        mock_config.PASSWORD_EXPIRY_DAYS = 90

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()

        mock_user_manager = Mock(spec=UserManager)
        new_user = user_schemas.User(
            user_name="testuser_jwt",
            hashed_password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=90,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.create_user = Mock(return_value=new_user)
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.CreateUserRequest(
            user_name="testuser_jwt",
            password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
        )

        result = create_user(
            body,
            mock_request,
            None,
        )

        assert result is not None
        assert result.user_name == "testuser_jwt"

    @patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config")
    def test_create_user_with_auth_mode_virtual_instance(self, mock_config):
        """Test creating user in virtual_instance auth mode."""
        mock_config.AUTH_MODE = Constant.AUTH_MODE_VIRTUAL_INSTANCE
        mock_config.PASSWORD_EXPIRY_DAYS = 0

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()

        mock_user_manager = Mock(spec=UserManager)
        new_user = user_schemas.User(
            user_name="testuser_virt",
            hashed_password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
            password_expiry_days=0,
            password_changed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_manager.create_user = Mock(return_value=new_user)
        mock_request.app.state._user_manager = mock_user_manager

        body = user_schemas.CreateUserRequest(
            user_name="testuser_virt",
            password=_s("password123"),
            roles=["user"],
            is_enabled=True,
            is_locked=False,
        )

        result = create_user(
            body,
            mock_request,
            None,
        )

        assert result is not None
        assert result.user_name == "testuser_virt"


class TestSetUserMgmt:
    """Test cases for set_user_mgmt API endpoint."""

    def test_set_user_mgmt_auth_mode_jwt(self):
        """Test setting auth mode to jwt."""
        body = user_schemas.SetUserMgmtRequest(auth_mode="jwt")

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.user.Config"
        ) as mock_config:
            with patch("wy_qcos.api.posiq.routes_jsonrpc.user.logger"):
                mock_config.AUTH_MODE = "no"
                result = set_user_mgmt(body, auth_data={"user_id": "admin"})

                assert result is not None
                assert result.auth_mode == "jwt"

    def test_set_user_mgmt_auth_mode_virtual_instance(self):
        """Test setting auth mode to virtual_instance."""
        body = user_schemas.SetUserMgmtRequest(auth_mode="virtual_instance")

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.user.Config"
        ) as mock_config:
            with patch("wy_qcos.api.posiq.routes_jsonrpc.user.logger"):
                mock_config.AUTH_MODE = "jwt"
                result = set_user_mgmt(body, auth_data={"user_id": "admin"})

                assert result is not None
                assert result.auth_mode == "virtual_instance"

    def test_set_user_mgmt_auth_mode_no(self):
        """Test setting auth mode to no."""
        body = user_schemas.SetUserMgmtRequest(auth_mode="no")

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.user.Config"
        ) as mock_config:
            with patch("wy_qcos.api.posiq.routes_jsonrpc.user.logger"):
                mock_config.AUTH_MODE = "jwt"
                result = set_user_mgmt(body, auth_data={"user_id": "admin"})

                assert result is not None
                assert result.auth_mode == "no"

    def test_set_user_mgmt_auth_mode_case_insensitive(self):
        """Test setting auth mode with case-insensitive input."""
        body = user_schemas.SetUserMgmtRequest(auth_mode="JWT")

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.user.Config"
        ) as mock_config:
            with patch("wy_qcos.api.posiq.routes_jsonrpc.user.logger"):
                mock_config.AUTH_MODE = "no"
                result = set_user_mgmt(body, auth_data={"user_id": "admin"})

                assert result is not None
                # Should normalize to lowercase
                assert result.auth_mode == "jwt"

    def test_set_user_mgmt_auth_mode_invalid_mode(self):
        """Test setting auth mode with invalid mode."""
        body = user_schemas.SetUserMgmtRequest(auth_mode="invalid_mode")

        with patch("wy_qcos.api.posiq.routes_jsonrpc.user.Config"):
            with pytest.raises(Exception):
                set_user_mgmt(body, auth_data={"user_id": "admin"})

    def test_set_user_mgmt_auth_mode_response_contains_auth_mode(self):
        """Test that set_user_mgmt response contains auth_mode."""
        body = user_schemas.SetUserMgmtRequest(auth_mode="jwt")

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.user.Config"
        ) as mock_config:
            with patch("wy_qcos.api.posiq.routes_jsonrpc.user.logger"):
                mock_config.AUTH_MODE = "no"
                result = set_user_mgmt(body, auth_data={"user_id": "admin"})

                # Verify response has expected fields
                assert hasattr(result, "auth_mode")
                assert result.auth_mode in ["no", "jwt", "virtual_instance"]
                if hasattr(result, "message"):
                    assert isinstance(result.message, str)
