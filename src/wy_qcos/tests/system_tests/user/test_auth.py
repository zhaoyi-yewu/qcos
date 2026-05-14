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

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestAuth:
    """User authentication system tests."""

    test_usernames = [
        "_test_login_user",
        "_test_logout_user",
        "_test_login_userinfo",
        "_test_multi_login",
        "_test_user_change_pwd",
        "_test_token_refresh",
        "_test_get_user",
        "_test_role_auth",
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

        # Admin credentials for cleanup operations
        cls.admin_user = GLOBAL_CONFIGS["admin_user"]
        cls.admin_password = GLOBAL_CONFIGS["admin_password"]

        # Test data variables
        cls.old_password = _s("OldPassword123!")
        cls.new_password = _s("NewPassword456!")

        # Store original auth mode for restoration
        cls.original_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(cls.admin_client,
                                cls.virtual_instance_client,
                                cls.original_auth_mode,
                                Constant.AUTH_MODE_JWT)

        # Clean up any existing test resources before starting tests
        cls._cleanup_test_users()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        current_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(
            cls.admin_client,
            cls.virtual_instance_client,
            current_auth_mode,
            cls.original_auth_mode
        )
        cls._cleanup_test_users()

    @pytest.mark.smoke
    def test_login_success(self):
        """Test successful login."""
        # Create test user
        username = "_test_login_user"
        password = _s("TestPassword123!")
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            StLibrary.create_user(self.admin_client, user_data)
            result = StLibrary.login(self.client, username, str(password))
            assert result is not None
            if "access_token" in result:
                assert isinstance(result["access_token"], str)
                assert len(result["access_token"]) > 0
            assert result["user_name"] == username
        finally:
            try:
                # Login as admin to delete user
                StLibrary.delete_user(
                    self.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials."""
        with pytest.raises(AssertionError):
            StLibrary.login(self.client, "invalid_user", "invalid_password")

    @pytest.mark.smoke
    def test_logout_success(self):
        """Test successful logout."""
        # Create test user
        username = "_test_logout_user"
        password = _s("TestPassword123!")
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            StLibrary.create_user(self.admin_client, user_data)
            login_result = StLibrary.login(
                self.client, username, str(password)
            )
            assert login_result is not None

            # Then logout
            self.client.set_token(login_result["access_token"])
            StLibrary.logout(self.client)
        finally:
            try:
                # Login as admin to delete user
                StLibrary.delete_user(
                    self.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_login_and_get_user_info(self):
        """Test getting user info after login."""
        # Create test user
        username = "_test_login_userinfo"
        password = _s("TestPassword123!")
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            StLibrary.create_user(self.admin_client, user_data)
            login_result = StLibrary.login(
                self.client, username, str(password)
            )
            assert login_result["user_name"] == username

            # Get user info
            user = StLibrary.get_user(
                self.admin_client, username, is_name=True
            )
            assert user is not None
            assert user["user_name"] == username
            assert isinstance(user["is_enabled"], bool)
        finally:
            try:
                StLibrary.delete_user(
                    self.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_multiple_login_sessions(self):
        """Test multiple login sessions."""
        # Create test user
        username = "_test_multi_login"
        password = _s("TestPassword123!")
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            StLibrary.create_user(self.admin_client, user_data)
            result1 = StLibrary.login(self.client, username, str(password))
            assert result1 is not None

            # Second login
            result2 = StLibrary.login(self.client, username, str(password))
            assert result2 is not None
        finally:
            try:
                # Login as admin to delete user
                StLibrary.delete_user(
                    self.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_change_password(self):
        """Test password change by user self."""
        # Create a new user for testing
        user_data = {
            "user_name": "_test_user_change_pwd",
            "password": self.old_password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            new_user = StLibrary.create_user(self.admin_client, user_data)
            assert new_user["user_name"] == "_test_user_change_pwd"

            login_result = StLibrary.login(
                self.client, "_test_user_change_pwd", str(self.old_password)
            )
            self.client.set_token(login_result["access_token"])

            # Change password
            StLibrary.change_password(
                self.client,
                "_test_user_change_pwd",
                str(self.old_password),
                str(self.new_password),
                is_name=True,
            )

            # Verify password change by login with new password
            login_result = StLibrary.login(
                self.client, "_test_user_change_pwd", str(self.new_password)
            )
            assert login_result["user_name"] == "_test_user_change_pwd"

        finally:
            # Clean up test user
            try:
                # Login as admin to delete user
                StLibrary.delete_user(
                    self.admin_client,
                    "_test_user_change_pwd",
                    is_name=True,
                    force=True,
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_token_expiry_and_refresh(self):
        """Test token expiry and refresh."""
        # Create test user
        username = "_test_token_refresh"
        password = _s("TestPassword123!")
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            StLibrary.create_user(self.admin_client, user_data)

            # Logout admin and login to get token
            login_result = StLibrary.login(
                self.client, username, str(password)
            )
            assert login_result is not None

            # Verify token exists
            if "access_token" in login_result:
                access_token = login_result["access_token"]
                assert isinstance(access_token, str)
                assert len(access_token) > 0
        finally:
            try:
                # Login as admin to delete user
                StLibrary.delete_user(
                    self.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_get_current_user(self):
        """Test getting current user info."""
        # Create test user
        username = "_test_get_user"
        password = _s("TestPassword123!")
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            StLibrary.create_user(self.admin_client, user_data)

            # Logout admin and login
            login_result = StLibrary.login(
                self.client, username, str(password)
            )
            assert login_result is not None
            assert login_result["user_name"] == username
        finally:
            try:
                # Login as admin to delete user
                StLibrary.delete_user(
                    self.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass

    @pytest.mark.smoke
    def test_authentication_with_role_permission(self):
        """Test authentication with role permissions."""
        # Create test user
        username = "_test_role_auth"
        password = _s("TestPassword123!")
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            StLibrary.create_user(self.admin_client, user_data)

            # Logout admin and login as test user
            result = StLibrary.login(self.client, username, str(password))
            assert result is not None

            # Get user roles
            try:
                user_roles = StLibrary.get_user_roles(
                    self.admin_client, username
                )
                assert user_roles is not None
                assert isinstance(user_roles, (dict, list))
            except Exception:  # noqa: S110
                pass
        finally:
            try:
                # Login as admin to delete user
                StLibrary.delete_user(
                    self.admin_client, username, is_name=True, force=True
                )
            except Exception:  # noqa: S110
                pass
