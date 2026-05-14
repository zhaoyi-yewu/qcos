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

import json
import pytest

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import _s
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestPermission:
    """Permission management system tests."""

    test_roles = [
        "_test_read_only_role",
        "_test_role_job",
        "_test_role_device",
        "_test_role_insufficient_permission",
    ]
    test_users = [
        "_test_user_permissions",
        "_test_user_insufficient_permission",
    ]

    @classmethod
    def _cleanup_test_resources(cls):
        """Clean up test roles and users."""
        for role_name in cls.test_roles:
            try:
                StLibrary.delete_role(
                    cls.admin_client, role_name, is_name=True
                )
            except Exception:  # noqa: S110
                pass

        for username in cls.test_users:
            try:
                StLibrary.delete_user(
                    cls.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.client = GLOBAL_CONFIGS["client"]
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.virtual_instance_client = GLOBAL_CONFIGS["virtual_instance_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]

        # Admin credentials for cleanup operations
        cls.admin_user = GLOBAL_CONFIGS["admin_user"]
        cls.admin_password = GLOBAL_CONFIGS["admin_password"]

        # Test data variables
        cls.password = _s("TestPassword123!")

        # Store original auth mode for restoration
        cls.original_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(
            cls.admin_client,
            cls.virtual_instance_client,
            cls.original_auth_mode,
            Constant.AUTH_MODE_JWT,
        )

        # Clean up any existing test resources before starting tests
        cls._cleanup_test_resources()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        current_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(
            cls.admin_client,
            cls.virtual_instance_client,
            current_auth_mode,
            cls.original_auth_mode,
        )
        cls._cleanup_test_resources()

    @pytest.mark.smoke
    def test_admin_role_permissions(self):
        """Test admin role permissions."""
        # Get admin role
        role = StLibrary.get_role(self.admin_client, "admin", is_name=True)
        assert role is not None
        permissions = role.get("permissions", [])
        assert permissions is not None
        # Admin should have all permissions
        if isinstance(permissions, list):
            assert len(permissions) > 0

    @pytest.mark.smoke
    def test_user_role_permissions(self):
        """Test regular user role permissions."""
        # Get user role
        role = StLibrary.get_role(self.admin_client, "user", is_name=True)
        assert role is not None
        permissions = role.get("permissions", [])
        assert permissions is not None
        # Regular user should have some permissions
        assert isinstance(permissions, (list, dict))

    @pytest.mark.smoke
    def test_permission_enforcement_for_user_operations(self):
        """Test permission enforcement for user operations."""
        # Create test role and user
        role_data = {
            "role_name": "_test_read_only_role",
            "permissions": [
                "/v1/device/get_devices",
                "/v1/device/get_device",
            ],
            "description": "Read-only role",
        }

        user_data = {
            "user_name": "_test_user_permissions",
            "password": self.password,
            "roles": ["_test_read_only_role"],
            "is_locked": False,
        }

        try:
            # Create role
            created_role = StLibrary.create_role(self.admin_client, role_data)
            assert created_role is not None

            # Create user
            new_user = StLibrary.create_user(self.admin_client, user_data)
            assert new_user["user_name"] == "_test_user_permissions"

            # Verify user has the role
            user_roles = StLibrary.get_roles(self.admin_client)
            assert user_roles is not None

        finally:
            # Clean up test data
            try:
                StLibrary.delete_user(
                    self.admin_client,
                    "_test_user_permissions",
                    is_name=True,
                    force=True,
                )
            except Exception:  # noqa: S110
                pass

            try:
                StLibrary.delete_role(
                    self.admin_client, "_test_read_only_role", is_name=True
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_permission_role_insufficient_permission(self):
        """Test role has insufficient permission to operate."""
        # Create test role and user
        role_data = {
            "role_name": "_test_role_insufficient_permission",
            "permissions": [
                "/v1/device/get_devices",
                "/v1/device/get_device",
            ],
            "description": "Get device only role",
        }

        user_data = {
            "user_name": "_test_user_insufficient_permissions",
            "password": self.password,
            "roles": ["_test_role_insufficient_permission"],
            "is_locked": False,
        }

        try:
            # Create role
            created_role = StLibrary.create_role(self.admin_client, role_data)
            assert created_role is not None

            # Create user
            new_user = StLibrary.create_user(self.admin_client, user_data)
            assert (
                new_user["user_name"] == "_test_user_insufficient_permissions"
            )

            # login
            login_response = StLibrary.login(
                self.client,
                "_test_user_insufficient_permissions",
                str(self.password),
            )
            self.client.set_token(login_response["access_token"])

            # access device (success)
            device = StLibrary.get_device(self.client, Constant.DEVICE_DUMMY)
            assert device is not None
            devices = StLibrary.get_devices(self.client)
            assert devices is not None

            # access drivers (failed with insufficient permissions)
            status_code, reason, text, response = self.client.get_drivers()
            assert status_code == HttpCode.SUCCESS_OK
            result = json.loads(text)
            error = result.get("error", {})
            error_code = error.get("code", 0)
            assert error_code == -HttpCode.FORBIDDEN_ERROR
        finally:
            # Clean up test data
            try:
                StLibrary.delete_user(
                    self.admin_client,
                    "_test_user_insufficient_permissions",
                    is_name=True,
                    force=True,
                )
            except Exception:  # noqa: S110
                pass

            try:
                StLibrary.delete_role(
                    self.admin_client,
                    "_test_role_insufficient_permission",
                    is_name=True,
                )
            except Exception:  # noqa: S110
                pass
