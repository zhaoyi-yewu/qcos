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
import logging
from unittest.mock import Mock, patch
from datetime import datetime

from wy_qcos.api.posiq.routes_jsonrpc.routes import all_api
from wy_qcos.api.schemas import user as schemas
from wy_qcos.common.library import _s
from wy_qcos.common.constant import Constant
from wy_qcos.user.user_manager import UserManager


# Suppress verbose logs during tests
def pytest_configure(config):
    """Configure pytest to suppress verbose logging from user_manager."""
    logging.getLogger("wy_qcos.user.user_manager").setLevel(logging.WARNING)


@pytest.fixture(scope="function")
def user_manager_with_mocks():
    """Create a UserManager with full mock setup - used by most tests."""
    mock_enforcer = Mock()
    mock_enforcer.add_policy.return_value = True
    mock_enforcer.remove_policy.return_value = True
    mock_enforcer.delete_role.return_value = True
    mock_enforcer.get_permissions_for_user.return_value = []
    mock_enforcer.add_grouping_policy.return_value = True
    mock_enforcer.remove_grouping_policy.return_value = True
    mock_enforcer.delete_roles_for_user.return_value = True
    mock_enforcer.enforce.return_value = True

    patcher1 = patch(
        "wy_qcos.user.permission_manager.casbin.Enforcer",
        return_value=mock_enforcer,
    )

    # Create a mock PermissionManager that properly returns lists
    mock_perm_manager = Mock()
    mock_perm_manager.get_for_role.return_value = []
    mock_perm_manager.enforce.return_value = True
    mock_perm_manager.add_policy.return_value = True

    patcher2 = patch(
        "wy_qcos.user.user_manager.PermissionManager",
        return_value=mock_perm_manager,
    )

    patcher1.start()
    patcher2.start()

    try:
        manager = UserManager("model.conf", "policy.csv", all_api)

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
            return (True, None, role)

        def mock_get_role_by_name(role_name):
            if role_name in created_roles:
                return (True, None, created_roles[role_name])
            return (False, None, None)

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
            return (True, None, user)

        def mock_get_user_by_username(user_name):
            if user_name in created_users:
                return (True, None, created_users[user_name])
            return (False, None, None)

        def mock_get_user_by_id(user_id):
            user_id_str = str(user_id).lower() if user_id else None
            for user in created_users.values():
                if hasattr(user, "id") and str(user.id).lower() == user_id_str:
                    return (True, None, user)
            return (False, None, None)

        def mock_get_users(filters=None):
            return (True, None, list(created_users.values()))

        def mock_delete_user_by_id(user_id):
            # Normalize user_id to string for comparison
            user_id_str = str(user_id).lower() if user_id else None
            for user_name, user in list(created_users.items()):
                if hasattr(user, "id") and str(user.id).lower() == user_id_str:
                    del created_users[user_name]
                    return (True, None)
            return (False, "User not found")

        def mock_delete_role(role_id):
            # Normalize role_id to string for comparison
            role_id_str = str(role_id).lower() if role_id else None
            for role_name, role in list(created_roles.items()):
                if hasattr(role, "id") and str(role.id).lower() == role_id_str:
                    del created_roles[role_name]
                    return (True, None)
            return (False, "Role not found")

        def mock_get_role_by_id(role_id):
            role_id_str = str(role_id).lower() if role_id else None
            for role in created_roles.values():
                if hasattr(role, "id") and str(role.id).lower() == role_id_str:
                    return (True, None, role)
            return (False, None, None)

        def mock_get_roles(filters=None):
            return (True, None, list(created_roles.values()))

        def mock_update_role(role_id, request):
            # Normalize role_id to string for comparison
            role_id_str = str(role_id).lower() if role_id else None
            for role in created_roles.values():
                if hasattr(role, "id") and str(role.id).lower() == role_id_str:
                    role.permissions = request.permissions or role.permissions
                    role.description = request.description or role.description
                    return (True, None, role)
            return (False, "Role not found", None)

        def mock_update_user(user_id, request):
            # Normalize user_id to string for comparison
            user_id_str = str(user_id).lower() if user_id else None
            for user_name, user in created_users.items():
                if hasattr(user, "id") and str(user.id).lower() == user_id_str:
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
                    return (True, None, user)
            return (False, "User not found", None)

        mock_users_repo = Mock()
        mock_users_repo.create_user.side_effect = mock_create_user
        mock_users_repo.get_user_by_username.side_effect = (
            mock_get_user_by_username
        )
        mock_users_repo.get_user_by_id.side_effect = mock_get_user_by_id
        mock_users_repo.get_users.side_effect = mock_get_users
        mock_users_repo.delete_user_by_id.side_effect = mock_delete_user_by_id
        mock_users_repo.update_user.side_effect = mock_update_user
        mock_users_repo.create_login_log.return_value = None
        mock_users_repo.get_login_logs.side_effect = (
            lambda user_id=None, start_time=None, end_time=None,
            limit=100, offset=0: (
                True,
                None,
                manager.login_logs[offset : offset + limit]
                if limit > 0
                else manager.login_logs[offset:],
            )
        )
        manager.users_repo = mock_users_repo

        mock_roles_repo = Mock()
        mock_roles_repo.create_role.side_effect = mock_create_role
        mock_roles_repo.get_role_by_name.side_effect = mock_get_role_by_name
        mock_roles_repo.get_role_by_id.side_effect = mock_get_role_by_id
        mock_roles_repo.get_roles.side_effect = mock_get_roles
        mock_roles_repo.update_role.side_effect = mock_update_role
        mock_roles_repo.delete_role_by_id.side_effect = mock_delete_role
        manager.roles_repo = mock_roles_repo
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


@pytest.fixture(scope="function", name="user_manager")
def user_manager_fixture(user_manager_with_mocks):
    """Provide user_manager as the fixture name for tests."""
    yield user_manager_with_mocks
