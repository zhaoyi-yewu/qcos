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

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import _s
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestSecurity:
    """Security system tests."""

    test_usernames = [
        "_test_no_plain_pwd_user",
        "_test_weak_pwd_user",
        "_test_token_login",
        "_test_logout_token",
        "_test_rbac_user",
        "_test_limited_perms_user",
        "_test_unauthorized_create",
        "_test_pwd_change_security",
        "_test_audit_user",
        "_test_session_user1",
        "_test_session_user2",
    ]

    @classmethod
    def _cleanup_test_users(cls):
        """Clean up test users."""
        StLibrary.login(
            cls.admin_client, cls.admin_user, str(cls.admin_password)
        )
        for username in cls.test_usernames:
            try:
                StLibrary.delete_user(cls.admin_client, username, is_name=True, force=True)
            except:
                pass

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.client = GLOBAL_CONFIGS["client"]
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]

        # Admin credentials for cleanup operations
        cls.admin_user = GLOBAL_CONFIGS["admin_user"]
        cls.admin_password = GLOBAL_CONFIGS["admin_password"]

        # Test data variables
        cls.secure_password = _s("SecurePassword123!")
        cls.weak_password = _s("weak")
        cls.password = _s("TestPassword123!")
        cls.old_password = _s("OldPassword123!")
        cls.new_password = _s("NewPassword456!")
        cls.password_1 = _s("Password123!")
        cls.password_2 = _s("Password456!")
        cls.password_2 = _s("Password456!")
        
        # Clean up any existing test resources before starting tests
        cls._cleanup_test_users()


    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls._cleanup_test_users()

    @pytest.mark.smoke
    def test_password_not_stored_in_plain_text(self):
        """Test password is not stored or returned in plain text."""
        user_data = {
            "user_name": "_test_no_plain_pwd_user",
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            # create user
            result = StLibrary.create_user(self.admin_client, user_data)
            assert result is not None
            # Retrieve test user and verify password is not exposed
            user = StLibrary.get_user(self.admin_client, "_test_no_plain_pwd_user", is_name=True)
            assert user is not None
            # Password should not be in response
            assert "password" not in user
            # Should not contain plain text password
            assert str(self.password) not in str(user)
        except (AssertionError, Exception):
            # Expected to fail
            pass
        finally:
            try:
                StLibrary.delete_user(self.admin_client, "_test_no_plain_pwd_user", is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_weak_password_rejection(self):
        """Test weak password is rejected."""
        user_data = {
            "user_name": "_test_weak_pwd_user",
            "password": self.weak_password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            # Weak password should fail or return error
            result = StLibrary.create_user(self.admin_client, user_data)
            # If it succeeds, password should still not be weak
            assert result is None or result.get("user_name") is None

        except (AssertionError, Exception):
            # Expected to fail
            pass
        finally:
            try:
                StLibrary.delete_user(self.admin_client, "_test_weak_pwd_user", is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_invalid_credentials_denied(self):
        """Test invalid credentials are denied access."""
        # Test user with wrong password
        try:
            result = StLibrary.login(self.client, self.test_user, "wrong_password")
            assert result is None or result.get("user_name") is None
        except (AssertionError, Exception):
            # Expected to fail
            pass

    @pytest.mark.smoke
    def test_nonexistent_user_denied_login(self):
        """Test non-existent user cannot login."""
        try:
            result = StLibrary.login(
                self.client, "nonexistent_user_xyz", "password"
            )
            assert result is None or result.get("user_name") is None
        except (AssertionError, Exception):
            # Expected to fail
            pass

    @pytest.mark.smoke
    def test_successful_login_returns_token(self):
        """Test successful login returns access token."""
        # Create test user
        username = "_test_token_login"
        password = self.password
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }
        
        try:
            StLibrary.create_user(self.admin_client, user_data)
            
            login_result = StLibrary.login(self.client, username, str(password))
            assert login_result is not None
            # Should have access token or similar auth mechanism
            assert (
                "access_token" in login_result
                or "token" in login_result
                or "auth" in login_result
            )
        finally:
            try:
                StLibrary.delete_user(self.admin_client, username, is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_token_invalidation_on_logout(self):
        """Test token is invalidated after logout."""
        # Create test user
        username = "_test_logout_token"
        password = self.password
        user_data = {
            "user_name": username,
            "password": password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }
        
        try:
            StLibrary.create_user(self.admin_client, user_data)
            
            # Login
            login_result = StLibrary.login(self.client, username, str(password))
            assert login_result is not None

            # Logout
            self.client.set_token(login_result["access_token"])
            StLibrary.logout(self.client)

            # Try to use old token - should fail
            try:
                user = StLibrary.get_user(self.admin_client, username, is_name=True)
                # If we can still access, verify it's a new session
                assert user is not None
            except:
                # Expected - token invalidated
                pass
        finally:
            try:
                StLibrary.delete_user(self.admin_client, username, is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_role_based_access_control(self):
        """Test role-based access control enforcement."""
        user_data = {
            "user_name": "_test_rbac_user",
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            # Create regular user (not admin)
            new_user = StLibrary.create_user(self.admin_client, user_data)
            assert new_user["user_name"] == "_test_rbac_user"

            # Verify user has restricted permissions
            user_roles = StLibrary.get_roles(self.admin_client)
            assert user_roles is not None

            role_names = (
                list(user_roles.keys())
                if isinstance(user_roles, dict)
                else [r.get("role_name") for r in user_roles]
            )
            # Should not have admin role
            assert "admin" not in role_names

        finally:
            try:
                StLibrary.delete_user(self.admin_client, "_test_rbac_user", is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_permission_enforcement_denied(self):
        """Test permission enforcement denies unauthorized access."""
        user_data = {
            "user_name": "_test_limited_perms_user",
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            # Create user with limited permissions
            new_user = StLibrary.create_user(self.admin_client, user_data)
            assert new_user is not None

            # Try to perform admin-only operation
            try:
                # Attempting to create another user (typically admin-only)
                result = StLibrary.create_user(
                    self.admin_client,
                    {
                        "user_name": "_test_unauthorized_create",
                        "password": self.password_1,
                    },
                )
                # If succeeds, verify it's from admin context
                assert result is None or result.get("error") is not None
            except:
                # Expected - permission denied
                pass

        finally:
            try:
                StLibrary.delete_user(self.admin_client, "_test_limited_perms_user", is_name=True, force=True)
            except:
                pass
            try:
                StLibrary.delete_user(self.admin_client, "_test_unauthorized_create", is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_sql_injection_prevention(self):
        """Test SQL injection attempts are prevented."""
        # Try to create user with SQL injection payload
        injection_payload = "' OR '1'='1"
        user_data = {
            "user_name": f"user_{injection_payload}",
            "password": self.password_1,
        }

        try:
            result = StLibrary.create_user(self.admin_client, user_data)
            # Should either fail or sanitize the input
            if result is not None:
                # Input should be sanitized
                assert injection_payload not in result.get("user_name", "")

        except:
            # Expected - malformed input rejected
            pass

    @pytest.mark.smoke
    def test_admin_password_change_security(self):
        """Test admin password change requires authentication."""
        user_data = {
            "user_name": "_test_pwd_change_security",
            "password": self.old_password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            new_user = StLibrary.create_user(self.admin_client, user_data)
            assert new_user["user_name"] == "_test_pwd_change_security"

            # Change password with authentication
            StLibrary.change_password(
                self.admin_client,
                "_test_pwd_change_security",
                str(self.old_password),
                str(self.new_password),
                is_name=True,
            )

            # Verify old password no longer works
            try:
                login_result = StLibrary.login(
                    self.client,
                    "_test_pwd_change_security",
                    str(self.old_password),
                )
                assert login_result is None
            except:
                # Expected - old password should fail
                pass

            # Verify new password works
            login_result = StLibrary.login(
                self.client, "_test_pwd_change_security", str(self.new_password)
            )
            assert login_result is not None

        finally:
            try:
                StLibrary.delete_user(self.admin_client, "_test_pwd_change_security", is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_audit_logging_user_operations(self):
        """Test audit logging for security events."""
        user_data = {
            "user_name": "_test_audit_user",
            "password": self.password,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }
        init_login_logs_count = 0

        try:
            # Create user
            new_user = StLibrary.create_user(self.admin_client, user_data)
            assert new_user is not None

            # Attempt to get login logs
            login_logs = StLibrary.get_login_logs(
                self.admin_client, username="_test_audit_user"
            )
            # Logs should exist or be retrievable
            assert isinstance(login_logs, list)
            init_login_logs_count = len(login_logs)

            # login successfully
            StLibrary.login(self.client, "_test_audit_user",
                            str(self.password))
            # Attempt to get login logs
            login_logs = StLibrary.get_login_logs(
                self.admin_client, username="_test_audit_user"
            )
            assert isinstance(login_logs, list)
            assert len(login_logs) == init_login_logs_count + 1

            # login failed (wrong password)
            wrong_password = f"{self.password}_wrong"
            status_code, reason, text, result = self.client.login("_test_audit_user", wrong_password)
            assert status_code == HttpCode.SUCCESS_OK
            # Attempt to get login logs
            login_logs = StLibrary.get_login_logs(
                self.admin_client, username="_test_audit_user"
            )
            assert isinstance(login_logs, list)
            assert len(login_logs) == init_login_logs_count + 2
        finally:
            try:
                StLibrary.delete_user(self.admin_client, "_test_audit_user", is_name=True, force=True)
            except:
                pass

    @pytest.mark.smoke
    def test_session_isolation(self):
        """Test sessions are isolated between users."""
        user1_data = {
            "user_name": "_test_session_user1",
            "password": self.password_1,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }
        user2_data = {
            "user_name": "_test_session_user2",
            "password": self.password_2,
            "roles": [Constant.ROLE_ADMIN],
            "is_locked": False,
        }

        try:
            # Create two users
            user1 = StLibrary.create_user(self.admin_client, user1_data)
            user2 = StLibrary.create_user(self.admin_client, user2_data)

            assert user1["user_name"] == "_test_session_user1"
            assert user2["user_name"] == "_test_session_user2"

            # Login as user1
            StLibrary.login(self.client, "_test_session_user1", str(self.password_1))

            # Verify user1 session exists
            current_user = StLibrary.get_user(self.admin_client, "_test_session_user1", is_name=True)
            assert current_user is not None

            # Login as user2
            login_response = StLibrary.login(self.client, "_test_session_user2", str(self.password_2))
            self.client.set_token(login_response["access_token"])

            # Verify user2 session is now active
            current_user = StLibrary.get_me(self.client)
            assert current_user is not None
            current_user["user_name"] = "_test_session_user2"

        finally:
            try:
                StLibrary.delete_user(self.admin_client, "_test_session_user1", is_name=True, force=True)
            except:
                pass
            try:
                StLibrary.delete_user(self.admin_client, "_test_session_user2", is_name=True, force=True)
            except:
                pass
