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
class TestUser:
    """User management system tests."""

    test_usernames = [
        "test_get_current",
        "test_user_st",
        "test_user_multi_roles",
        "test_user_enable_disable",
        "test_user_properties",
        "test_user_login_flow",
        "test_user_role_assignment",
        "test_user_description",
        "test_user_is_enabled",
        "test_user_is_locked",
        "test_user_failed_login",
        "test_user_last_login",
        "test_user_password_changed",
        "test_user_locked_until",
        "test_user_expiry_days",
        "test_user_update_is_enabled",
        "test_user_update_is_locked",
    ]

    @classmethod
    def _cleanup_test_users(cls):
        """Clean up test users."""
        for username in cls.test_usernames:
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
        cls.max_login_attempts = GLOBAL_CONFIGS["max_login_attempts"]

        # Admin credentials for cleanup operations
        cls.admin_user = GLOBAL_CONFIGS["admin_user"]
        cls.admin_password = GLOBAL_CONFIGS["admin_password"]

        # Test data variables
        cls.password = _s("TestPassword123!")
        cls.temp_password = _s("TempPass123!")
        cls.old_password = _s("OldPassword123!")
        cls.new_password = _s("NewPassword456!")

        # Store original auth mode for restoration
        cls.original_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(
            cls.admin_client,
            cls.virtual_instance_client,
            cls.original_auth_mode,
            Constant.AUTH_MODE_JWT,
        )

        # Initialize and clean up test resources
        cls._cleanup_test_users()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls._cleanup_test_users()
        current_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(
            cls.admin_client,
            cls.virtual_instance_client,
            current_auth_mode,
            cls.original_auth_mode,
        )

    @pytest.mark.smoke
    def test_get_current_test_user(self):
        """Test getting current test user."""
        username = "test_get_current"
        user_data = {
            "user_name": username,
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        StLibrary.create_user(self.admin_client, user_data)
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert user["user_name"] == username
        assert isinstance(user["is_enabled"], bool)
        login_response = StLibrary.login(
            self.client, username, str(self.password)
        )
        self.client.set_token(login_response["access_token"])
        # Verify user session is now active
        current_user = StLibrary.get_me(self.client)
        assert current_user is not None
        current_user["user_name"] = username

    @pytest.mark.smoke
    def test_create_and_delete_user(self):
        """Test creating and deleting user."""
        user_data = {
            "user_name": "test_user_st",
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        # Create user
        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user is not None
        assert new_user["user_name"] == "test_user_st"
        # Verify user is created
        user_info = StLibrary.get_user(
            self.admin_client, "test_user_st", is_name=True
        )
        assert user_info["user_name"] == "test_user_st"
        user_id = user_info["id"]

        # Delete user
        StLibrary.delete_user(self.admin_client, "test_user_st", is_name=True)

        # Verify user is deleted
        users = StLibrary.get_users(self.admin_client)
        assert user_id not in users

    @pytest.mark.smoke
    def test_get_all_users(self):
        """Test getting all users."""
        users = StLibrary.get_users(self.admin_client)
        assert users is not None
        assert len(users) > 0

        # Review returned data structure
        if isinstance(users, dict):
            for user_id, user_info in users.items():
                assert isinstance(user_id, str)
                assert isinstance(user_info, dict)
                assert "user_name" in user_info
        elif isinstance(users, list):
            for user in users:
                assert isinstance(user, dict)
                assert "user_name" in user

    @pytest.mark.smoke
    def test_user_with_multiple_roles(self):
        """Test assigning multiple roles to same user."""
        user_data = {
            "user_name": "test_user_multi_roles",
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN, Constant.ROLE_USER],
            "is_locked": False,
        }

        # Create user
        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == "test_user_multi_roles"
        # Verify user roles
        user_roles = StLibrary.get_roles(self.admin_client)
        assert user_roles is not None
        # Should have at least one role
        role_count = (
            len(user_roles) if isinstance(user_roles, (dict, list)) else 0
        )
        assert role_count > 0

    @pytest.mark.smoke
    def test_user_enable_disable_workflow(self):
        """Test user enable/disable workflow."""
        user_data = {
            "user_name": "test_user_enable_disable",
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        # Create user
        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == "test_user_enable_disable"
        # Verify user status
        user = StLibrary.get_user(
            self.admin_client, "test_user_enable_disable", is_name=True
        )
        assert user is not None
        # New user should be enabled
        assert isinstance(user["is_enabled"], bool)

    @pytest.mark.smoke
    def test_user_account_properties(self):
        """Test user account properties."""
        user_data = {
            "user_name": "test_user_properties",
            "password": self.password,
            "description": "Test user for property verification",
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        # Create user
        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user is not None
        # Verify user properties
        user = StLibrary.get_user(
            self.admin_client, "test_user_properties", is_name=True
        )
        assert user["user_name"] == "test_user_properties"
        assert "created_at" in user or "created_time" in user
        assert isinstance(user["is_enabled"], bool)

    @pytest.mark.smoke
    def test_user_creation_and_login_flow(self):
        """Test user creation and login flow."""
        username = "test_user_login_flow"
        user_data = {
            "user_name": username,
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        # Create user
        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # Login with new credentials
        login_result = StLibrary.login(
            self.client, username, str(self.password)
        )
        assert login_result is not None
        assert login_result["user_name"] == username
        # Verify user last_login
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert user.get("last_login") is not None
        assert user.get("password_changed_at") is not None
        assert user.get("created_at") is not None
        assert user.get("updated_at") is not None
        assert user.get("password_expiry_days") == 0
        assert user.get("password_expiry_days") == 0
        assert user.get("locked_until") is None

    @pytest.mark.smoke
    def test_user_role_assignment(self):
        """Test user role assignment workflow."""
        # Create a test user with a specific role
        username = "test_user_role_assignment"
        user_data = {
            "user_name": username,
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user is not None
        assert new_user["user_name"] == username

        user_id = new_user["id"]

        # Try to assign role if available
        StLibrary.update_user(self.client, user_id, ["user"])

        # Verify user
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None

    @pytest.mark.smoke
    def test_user_description_field(self):
        """Test user description field."""
        username = "test_user_description"
        description = "This is a test user for field testing"
        user_data = {
            "user_name": username,
            "password": self.password,
            "description": description,
            "is_locked": False,
        }

        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username

        # Get user and verify description
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert user.get("description") == description

    @pytest.mark.smoke
    def test_user_is_enabled_field(self):
        """Test user is_enabled field."""
        username = "test_user_is_enabled"
        user_data = {
            "user_name": username,
            "password": self.password,
            "is_enabled": False,
            "is_locked": False,
        }

        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # Get user and verify is_enabled
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert isinstance(user.get("is_enabled"), bool)
        assert user.get("is_enabled") is False
        # login user (disabled user should fail to login)
        status_code, reason, text, result = self.client.login(
            username, str(self.password)
        )
        assert status_code == HttpCode.SUCCESS_OK
        # Parse JSON response from text
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == -HttpCode.FORBIDDEN_ERROR

    @pytest.mark.smoke
    def test_user_is_locked_field(self):
        """Test user is_locked field."""
        username = "test_user_is_locked"
        user_data = {
            "user_name": username,
            "password": self.password,
            "is_locked": True,
        }

        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # Get user and verify is_locked
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert isinstance(user.get("is_locked"), bool)
        assert user.get("is_locked") is True
        # login user
        status_code, reason, text, result = self.client.login(
            username, self.password
        )
        assert status_code == HttpCode.SUCCESS_OK
        # Parse JSON response from text
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == -HttpCode.FORBIDDEN_ERROR

    @pytest.mark.smoke
    def test_update_user_is_enabled_field(self):
        """Test updating user is_enabled field."""
        username = "test_user_update_is_enabled"
        user_data = {
            "user_name": username,
            "password": self.password,
            "is_enabled": True,
            "is_locked": False,
        }

        # Create user with is_enabled=True
        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # Verify user is enabled
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert user.get("is_enabled") is True
        # Update user to disable it
        StLibrary.update_user(
            self.admin_client, user.get("id"), is_enabled=False
        )
        # Verify user is now disabled
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert user.get("is_enabled") is False
        # login user
        status_code, reason, text, result = self.client.login(
            username, self.password
        )
        assert status_code == HttpCode.SUCCESS_OK
        # Parse JSON response from text
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == -HttpCode.FORBIDDEN_ERROR

    @pytest.mark.smoke
    def test_update_user_is_locked_field(self):
        """Test updating user is_locked field."""
        username = "test_user_update_is_locked"
        user_data = {
            "user_name": username,
            "password": self.password,
            "is_locked": False,
        }

        # Create user with is_locked=False
        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # Verify user is not locked
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert user.get("is_locked") is False
        # Update user to lock it
        StLibrary.update_user(
            self.admin_client, user.get("id"), is_locked=True
        )
        # Verify user is now locked
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        assert user.get("is_locked") is True
        # login user
        status_code, reason, text, result = self.client.login(
            username, self.password
        )
        assert status_code == HttpCode.SUCCESS_OK
        # Parse JSON response from text
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == -HttpCode.FORBIDDEN_ERROR

    @pytest.mark.smoke
    def test_user_failed_login_attempts_field(self):
        """Test user failed_login_attempts field."""
        username = "test_user_failed_login"
        user_data = {
            "user_name": username,
            "password": self.password,
            "is_locked": False,
        }

        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # login user
        wrong_password = f"{self.password}_wrong"
        for i in range(self.max_login_attempts):
            status_code, reason, text, result = self.client.login(
                username, wrong_password
            )
            assert status_code == HttpCode.SUCCESS_OK
        # Get user and verify failed_login_attempts
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        is_locked = user.get("is_locked", False)
        assert is_locked is True

    @pytest.mark.smoke
    def test_user_last_login_field(self):
        """Test user last_login field."""
        username = "test_user_last_login"
        user_data = {
            "user_name": username,
            "password": self.password,
            "is_locked": False,
        }

        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # Get user before login - last_login should be None or not set
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        last_login_before = user.get("last_login")
        assert last_login_before is None
        # Login with the user
        StLibrary.login(self.client, username, str(self.password))
        # Get user after login - last_login should be set
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        last_login_after = user.get("last_login")
        # last_login should be populated after login
        assert last_login_after is not None

    @pytest.mark.smoke
    def test_user_password_expiry_days_field(self):
        """Test user password_expiry_days field."""
        username = "test_user_expiry_days"
        expiry_days = -1
        user_data = {
            "user_name": username,
            "password": self.password,
            "password_expiry_days": expiry_days,
            "is_locked": False,
        }

        new_user, _ = StLibrary.create_user(self.admin_client, user_data)
        assert new_user["user_name"] == username
        # Get user and verify password_expiry_days
        user = StLibrary.get_user(self.admin_client, username, is_name=True)
        assert user is not None
        retrieved_expiry_days = user.get("password_expiry_days")
        assert retrieved_expiry_days == expiry_days
        status_code, reason, text, result = self.client.login(
            username, self.password
        )
        assert status_code == HttpCode.SUCCESS_OK
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == -HttpCode.FORBIDDEN_ERROR
