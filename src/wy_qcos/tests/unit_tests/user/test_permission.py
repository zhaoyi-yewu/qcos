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

from wy_qcos.user.permission_manager import PermissionManager


class TestPermissionManager:
    """Test cases for PermissionManager functionality."""

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_init_success(self, mock_enforcer_class):
        """Test successful initialization."""
        mock_enforcer = Mock()
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        assert pm.enforcer == mock_enforcer
        assert pm.access_control_model_file == "model.conf"
        assert pm.access_control_policy_file == "policy.csv"
        mock_enforcer_class.assert_called_once_with("model.conf", "policy.csv")

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_init_failure(self, mock_enforcer_class):
        """Test initialization failure."""
        mock_enforcer_class.side_effect = Exception("Failed to init")

        with pytest.raises(Exception):
            PermissionManager("model.conf", "policy.csv")

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_check_enforce_success(self, mock_enforcer_class):
        """Test permission check enforcement success."""
        mock_enforcer = Mock()
        mock_enforcer.enforce.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.enforce("user", "/api/test", "call")

        assert result is True
        mock_enforcer.enforce.assert_called_once_with(
            "user", "/api/test", "call"
        )

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_check_enforce_failure(self, mock_enforcer_class):
        """Test permission check enforcement failure."""
        mock_enforcer = Mock()
        mock_enforcer.enforce.return_value = False
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.enforce("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_check_enforce_no_enforcer(self, mock_enforcer_class):
        """Test permission check without enforcer."""
        mock_enforcer_class.return_value = None

        pm = PermissionManager("model.conf", "policy.csv")
        pm.enforcer = None  # Simulate uninitialized enforcer

        result = pm.enforce("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_check_enforce_exception(self, mock_enforcer_class):
        """Test permission check with exception."""
        mock_enforcer = Mock()
        mock_enforcer.enforce.side_effect = Exception("Enforce failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.enforce("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_policy_success(self, mock_enforcer_class):
        """Test adding permission policy success."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.add_policy("user", "/api/test", "call")

        assert result is True
        mock_enforcer.add_policy.assert_called_once_with(
            "user", "/api/test", "call"
        )

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_policy_failure(self, mock_enforcer_class):
        """Test adding permission policy failure."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.return_value = False
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.add_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_policy_exception(self, mock_enforcer_class):
        """Test adding permission policy with exception."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.side_effect = Exception("Add failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.add_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_policy_success(self, mock_enforcer_class):
        """Test removing permission policy success."""
        mock_enforcer = Mock()
        mock_enforcer.remove_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.remove_policy("user", "/api/test", "call")

        assert result is True
        mock_enforcer.remove_policy.assert_called_once_with(
            "user", "/api/test", "call"
        )

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_policy_failure(self, mock_enforcer_class):
        """Test removing permission policy failure."""
        mock_enforcer = Mock()
        mock_enforcer.remove_policy.return_value = False
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.remove_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_policy_exception(self, mock_enforcer_class):
        """Test removing permission policy with exception."""
        mock_enforcer = Mock()
        mock_enforcer.remove_policy.side_effect = Exception("Remove failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.remove_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_role_success(self, mock_enforcer_class):
        """Test removing role success."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.remove_role("admin")

        assert result is True
        mock_enforcer.delete_role.assert_called_once_with("admin")

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_role_failure(self, mock_enforcer_class):
        """Test removing role failure."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.return_value = False
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.remove_role("admin")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_role_exception(self, mock_enforcer_class):
        """Test removing role with exception."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.side_effect = Exception("Delete failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.remove_role("admin")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_get_for_role_success(self, mock_enforcer_class):
        """Test getting permissions for role success."""
        mock_enforcer = Mock()
        mock_enforcer.get_permissions_for_user.return_value = [
            ["/api/test", "call"],
            ["/api/other", "call"],
        ]
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.get_for_role("admin")

        assert result == [["/api/test", "call"], ["/api/other", "call"]]
        mock_enforcer.get_permissions_for_user.assert_called_once_with("admin")

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_get_for_role_exception(self, mock_enforcer_class):
        """Test getting permissions for role with exception."""
        mock_enforcer = Mock()
        mock_enforcer.get_permissions_for_user.side_effect = Exception(
            "Get failed"
        )
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.get_for_role("admin")

        assert result == []

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_role_for_user_success(self, mock_enforcer_class):
        """Test adding role for user success."""
        mock_enforcer = Mock()
        mock_enforcer.add_grouping_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.add_role_for_user("testuser", "admin")

        assert result is True
        mock_enforcer.add_grouping_policy.assert_called_once_with(
            "testuser", "admin"
        )

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_role_for_user_failure(self, mock_enforcer_class):
        """Test adding role for user failure."""
        mock_enforcer = Mock()
        mock_enforcer.add_grouping_policy.return_value = False
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.add_role_for_user("testuser", "admin")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_role_for_user_exception(self, mock_enforcer_class):
        """Test adding role for user with exception."""
        mock_enforcer = Mock()
        mock_enforcer.add_grouping_policy.side_effect = Exception("Add failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.add_role_for_user("testuser", "admin")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_delete_role_for_user_with_role(self, mock_enforcer_class):
        """Test deleting role for user with specific role."""
        mock_enforcer = Mock()
        mock_enforcer.remove_grouping_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.delete_role_for_user("testuser", "admin")

        assert result is True
        mock_enforcer.remove_grouping_policy.assert_called_once_with(
            "testuser", "admin"
        )

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_delete_role_for_user_without_role(
        self, mock_enforcer_class
    ):
        """Test deleting all roles for user."""
        mock_enforcer = Mock()
        mock_enforcer.delete_roles_for_user.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.delete_role_for_user("testuser")

        assert result is True
        mock_enforcer.delete_roles_for_user.assert_called_once_with("testuser")

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_delete_role_for_user_exception(self, mock_enforcer_class):
        """Test deleting role for user with exception."""
        mock_enforcer = Mock()
        mock_enforcer.remove_grouping_policy.side_effect = Exception(
            "Remove failed"
        )
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.delete_role_for_user("testuser", "admin")

        assert result is False


class TestAdvancedPermissionScenarios:
    """Test cases for advanced permission management scenarios."""

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_wildcard_permission_enforcement(self, mock_enforcer_class):
        """Test wildcard permission enforcement."""
        mock_enforcer = Mock()
        mock_enforcer.enforce.side_effect = lambda user, resource, action: (
            True if resource == "*" else False
        )
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Admin with wildcard should have all permissions
        assert pm.enforce("admin", "*", "call") is True
        assert pm.enforce("admin", "/api/test", "call") is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_multiple_permission_paths(self, mock_enforcer_class):
        """Test permission checking with multiple paths."""
        mock_enforcer = Mock()

        def enforce_side_effect(user, resource, action):
            allowed_perms = {
                ("user", "/api/read", "call"): True,
                ("user", "/api/write", "call"): False,
                ("user", "/api/list", "call"): True,
            }
            return allowed_perms.get((user, resource, action), False)

        mock_enforcer.enforce.side_effect = enforce_side_effect
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # User can read
        assert pm.enforce("user", "/api/read", "call") is True
        # User cannot write
        assert pm.enforce("user", "/api/write", "call") is False
        # User can list
        assert pm.enforce("user", "/api/list", "call") is True

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_permission_inheritance_chain(self, mock_enforcer_class):
        """Test permission inheritance through role hierarchy."""
        mock_enforcer = Mock()

        # Setup role hierarchy: user -> developer -> admin
        def get_permissions_side_effect(role):
            hierarchy = {
                "user": [["/api/read", "call"]],
                "developer": [
                    ["/api/read", "call"],
                    ["/api/write", "call"],
                    ["/api/delete", "call"],
                ],
                "admin": [["/api/*", "call"]],
            }
            return hierarchy.get(role, [])

        mock_enforcer.get_permissions_for_user.side_effect = (
            get_permissions_side_effect
        )
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Get permissions for each role
        user_perms = pm.get_for_role("user")
        dev_perms = pm.get_for_role("developer")
        admin_perms = pm.get_for_role("admin")

        assert len(user_perms) == 1
        assert len(dev_perms) == 3
        assert len(admin_perms) == 1

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_adding_conflicting_policies(self, mock_enforcer_class):
        """Test handling of conflicting permission policies."""
        mock_enforcer = Mock()

        # Track added policies
        added_policies = []

        def add_policy_side_effect(*args):
            added_policies.append(args)
            return True

        mock_enforcer.add_policy.side_effect = add_policy_side_effect
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Add policy that allows access
        assert pm.add_policy("user", "/api/test", "call") is True
        # Add conflicting policy (would need application logic to detect)
        assert pm.add_policy("user", "/api/test", "call") is True

        assert len(added_policies) == 2

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_remove_inherited_permissions(self, mock_enforcer_class):
        """Test removing permissions from inherited roles."""
        mock_enforcer = Mock()
        mock_enforcer.remove_policy.return_value = True
        mock_enforcer.remove_grouping_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Remove specific permission
        assert pm.remove_policy("developer", "/api/write", "call") is True
        # Remove role from user
        assert pm.delete_role_for_user("testuser", "developer") is True

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_permission_scope_boundaries(self, mock_enforcer_class):
        """Test permission scoping and boundaries."""
        mock_enforcer = Mock()

        def enforce_scope(user, resource, action):
            # User can only access /api/profile/self resources
            if resource.startswith("/api/profile/self"):
                return True
            if resource.startswith("/api/profile"):
                return False
            if resource.startswith("/api"):
                return False
            return False

        mock_enforcer.enforce.side_effect = enforce_scope
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # User can access own profile
        assert pm.enforce("user", "/api/profile/self", "call") is True
        # User cannot access other profiles
        assert pm.enforce("user", "/api/profile/other", "call") is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_resource_wildcard_matching(self, mock_enforcer_class):
        """Test wildcard matching in resource paths."""
        mock_enforcer = Mock()

        def enforce_wildcard(user, resource, action):
            # If permission has wildcard in path
            allowed = [
                "/api/device/*",
                "/api/*/list",
                "/api/*/get_*",
            ]
            for perm in allowed:
                # Simple wildcard matching
                if perm == "*":
                    return True
                if "*" in perm:
                    prefix = perm.split("*")[0]
                    if resource.startswith(prefix):
                        return True
            return resource.startswith("/api")

        mock_enforcer.enforce.side_effect = enforce_wildcard
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Wildcard matching
        assert pm.enforce("user", "/api/device/123", "call") is True
        assert pm.enforce("user", "/api/device/456/detail", "call") is True

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_role_permission_aggregation(self, mock_enforcer_class):
        """Test aggregation of permissions from multiple roles."""
        mock_enforcer = Mock()

        def get_aggregated_perms(user):
            # User has multiple roles, aggregate all permissions
            # Return combined permissions
            return [["/api/read", "call"], ["/api/write", "call"]]

        mock_enforcer.get_permissions_for_user.side_effect = (
            get_aggregated_perms
        )
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        perms = pm.get_for_role("multi_role_user")
        assert len(perms) == 2

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_permission_delegation(self, mock_enforcer_class):
        """Test permission delegation through role assignment."""
        mock_enforcer = Mock()
        mock_enforcer.add_grouping_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Delegate role to user
        assert pm.add_role_for_user("john", "reviewer") is True
        assert pm.add_role_for_user("john", "approver") is True

        # Verify calls were made
        assert mock_enforcer.add_grouping_policy.call_count == 2

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_permission_revocation_cascade(self, mock_enforcer_class):
        """Test cascading effects of permission revocation."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.return_value = True
        mock_enforcer.delete_roles_for_user.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Revoke entire role (affects all users with this role)
        assert pm.remove_role("temporary_role") is True

        # Remove specific role from user
        assert pm.delete_role_for_user("contractor") is True


class TestPermissionCachingAndValidation:
    """Test cases for permission caching and validation."""

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_enforce_with_cache_miss(self, mock_enforcer_class):
        """Test enforcement when cache misses."""
        mock_enforcer = Mock()
        mock_enforcer.enforce.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # First call should go to enforcer
        result1 = pm.enforce("user", "/api/test", "call")
        assert result1 is True

        # Verify enforcer was called
        assert mock_enforcer.enforce.call_count >= 1

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_permission_validation_edge_cases(self, mock_enforcer_class):
        """Test permission validation edge cases."""
        mock_enforcer = Mock()

        def enforce_edge_cases(user, resource, action):
            # Handle empty/null cases
            if not user or not resource or not action:
                return False
            return True

        mock_enforcer.enforce.side_effect = enforce_edge_cases
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Empty user
        assert pm.enforce("", "/api/test", "call") is False
        # Empty resource
        assert pm.enforce("user", "", "call") is False
        # Empty action
        assert pm.enforce("user", "/api/test", "") is False
        # Valid request
        assert pm.enforce("user", "/api/test", "call") is True

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_policy_synchronization(self, mock_enforcer_class):
        """Test policy synchronization after changes."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.return_value = True
        mock_enforcer.remove_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Add policy
        pm.add_policy("user", "/api/new", "call")
        # Remove policy
        pm.remove_policy("user", "/api/old", "call")

        # Verify both operations were called
        assert mock_enforcer.add_policy.call_count == 1
        assert mock_enforcer.remove_policy.call_count == 1


class TestPermissionErrorHandling:
    """Test cases for permission management error handling."""

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_permission_check_with_invalid_enforcer(self, mock_enforcer_class):
        """Test permission check when enforcer is invalid."""
        mock_enforcer_class.return_value = None

        pm = PermissionManager("model.conf", "policy.csv")
        pm.enforcer = None

        # Should return False safely
        result = pm.enforce("user", "/api/test", "call")
        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_policy_operations_with_errors(self, mock_enforcer_class):
        """Test policy operations when errors occur."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.side_effect = Exception("Policy conflict")
        mock_enforcer.remove_policy.side_effect = Exception("Not found")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Should return False on exception
        result = pm.add_policy("user", "/api/test", "call")
        assert result is False

        result = pm.remove_policy("user", "/api/test", "call")
        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_role_management_errors(self, mock_enforcer_class):
        """Test role management error handling."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.side_effect = Exception("Role in use")
        mock_enforcer.add_grouping_policy.side_effect = Exception(
            "Duplicate role"
        )
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")

        # Should handle errors gracefully
        result = pm.remove_role("admin")
        assert result is False

        result = pm.add_role_for_user("user", "admin")
        assert result is False


class TestPermissionManagerReload:
    """Test cases for reload methods in PermissionManager."""

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_success(self, mock_enforcer_class):
        """Test successful policy reload."""
        mock_enforcer = Mock()
        mock_enforcer.load_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.reload_policy()

        assert result is True
        mock_enforcer.load_policy.assert_called_once()

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_enforcer_not_initialized(self, mock_enforcer_class):
        """Test reload when enforcer not initialized."""
        mock_enforcer_class.return_value = Mock()
        pm = PermissionManager("model.conf", "policy.csv")
        pm.enforcer = None

        result = pm.reload_policy()

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_exception(self, mock_enforcer_class):
        """Test reload with exception."""
        mock_enforcer = Mock()
        mock_enforcer.load_policy.side_effect = Exception("Load failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.reload_policy()

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_load_returns_false(self, mock_enforcer_class):
        """Test reload when load_policy returns False."""
        mock_enforcer = Mock()
        mock_enforcer.load_policy.return_value = False
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.reload_policy()

        assert result is False


class TestPermissionManagerReloadFromDb:
    """Test cases for reload from database."""

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_from_db_no_repo(self, mock_enforcer_class):
        """Test reload from db without repository."""
        mock_enforcer_class.return_value = Mock()
        pm = PermissionManager("model.conf", "policy.csv")

        result = pm.reload_policy_from_db(None)

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_from_db_enforcer_not_initialized(
        self, mock_enforcer_class
    ):
        """Test reload from db when enforcer not initialized."""
        mock_enforcer_class.return_value = Mock()
        pm = PermissionManager("model.conf", "policy.csv")
        pm.enforcer = None

        result = pm.reload_policy_from_db(Mock())

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_from_db_success(self, mock_enforcer_class):
        """Test successful reload from database."""
        mock_enforcer = Mock()
        mock_enforcer.clear_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        mock_repo = Mock()
        mock_role = Mock()
        mock_role.role_name = "admin"
        mock_role.permissions = ["/api/test", "/api/other"]
        mock_repo.get_roles.return_value = (True, None, [mock_role])

        pm = PermissionManager("model.conf", "policy.csv")
        pm.add_policy = Mock(return_value=True)

        result = pm.reload_policy_from_db(mock_repo)

        assert result is True
        mock_enforcer.clear_policy.assert_called_once()
        mock_repo.get_roles.assert_called_once()

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_from_db_empty_roles(self, mock_enforcer_class):
        """Test reload from db with empty roles."""
        mock_enforcer = Mock()
        mock_enforcer_class.return_value = mock_enforcer

        mock_repo = Mock()
        mock_repo.get_roles.return_value = (True, None, None)

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.reload_policy_from_db(mock_repo)

        assert result is True

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_from_db_repo_error(self, mock_enforcer_class):
        """Test reload from db when repo returns error."""
        mock_enforcer = Mock()
        mock_enforcer.clear_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        mock_repo = Mock()
        mock_repo.get_roles.return_value = (False, "Error", None)

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.reload_policy_from_db(mock_repo)

        assert result is True

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_reload_policy_from_db_add_policy_exception(
        self, mock_enforcer_class
    ):
        """Test reload from db with add_policy exception."""
        mock_enforcer = Mock()
        mock_enforcer.clear_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        mock_repo = Mock()
        mock_role = Mock()
        mock_role.role_name = "admin"
        mock_role.permissions = ["/api/test"]
        mock_repo.get_roles.return_value = (True, None, [mock_role])

        pm = PermissionManager("model.conf", "policy.csv")
        pm.add_policy = Mock(side_effect=Exception("Add failed"))

        result = pm.reload_policy_from_db(mock_repo)

        assert result is True  # Should complete despite exception


class TestPermissionManagerClear:
    """Test cases for clear methods."""

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_clear_policy_success(self, mock_enforcer_class):
        """Test successful clear policy."""
        mock_enforcer = Mock()
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.clear_policy()

        assert result is True
        mock_enforcer.clear_policy.assert_called_once()

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_clear_policy_enforcer_not_initialized(self, mock_enforcer_class):
        """Test clear when enforcer not initialized."""
        mock_enforcer_class.return_value = Mock()
        pm = PermissionManager("model.conf", "policy.csv")
        pm.enforcer = None

        result = pm.clear_policy()

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_clear_policy_exception(self, mock_enforcer_class):
        """Test clear with exception."""
        mock_enforcer = Mock()
        mock_enforcer.clear_policy.side_effect = Exception("Clear failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.clear_policy()

        assert result is False
