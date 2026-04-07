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
        result = pm.perms_check_enforce("user", "/api/test", "call")

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
        result = pm.perms_check_enforce("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_check_enforce_no_enforcer(self, mock_enforcer_class):
        """Test permission check without enforcer."""
        mock_enforcer_class.return_value = None

        pm = PermissionManager("model.conf", "policy.csv")
        pm.enforcer = None  # Simulate uninitialized enforcer

        result = pm.perms_check_enforce("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_check_enforce_exception(self, mock_enforcer_class):
        """Test permission check with exception."""
        mock_enforcer = Mock()
        mock_enforcer.enforce.side_effect = Exception("Enforce failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_check_enforce("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_policy_success(self, mock_enforcer_class):
        """Test adding permission policy success."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_add_policy("user", "/api/test", "call")

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
        result = pm.perms_add_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_policy_exception(self, mock_enforcer_class):
        """Test adding permission policy with exception."""
        mock_enforcer = Mock()
        mock_enforcer.add_policy.side_effect = Exception("Add failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_add_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_policy_success(self, mock_enforcer_class):
        """Test removing permission policy success."""
        mock_enforcer = Mock()
        mock_enforcer.remove_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_remove_policy("user", "/api/test", "call")

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
        result = pm.perms_remove_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_policy_exception(self, mock_enforcer_class):
        """Test removing permission policy with exception."""
        mock_enforcer = Mock()
        mock_enforcer.remove_policy.side_effect = Exception("Remove failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_remove_policy("user", "/api/test", "call")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_role_success(self, mock_enforcer_class):
        """Test removing role success."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_remove_role("admin")

        assert result is True
        mock_enforcer.delete_role.assert_called_once_with("admin")

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_role_failure(self, mock_enforcer_class):
        """Test removing role failure."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.return_value = False
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_remove_role("admin")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_remove_role_exception(self, mock_enforcer_class):
        """Test removing role with exception."""
        mock_enforcer = Mock()
        mock_enforcer.delete_role.side_effect = Exception("Delete failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_remove_role("admin")

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
        result = pm.perms_get_for_role("admin")

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
        result = pm.perms_get_for_role("admin")

        assert result == []

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_role_for_user_success(self, mock_enforcer_class):
        """Test adding role for user success."""
        mock_enforcer = Mock()
        mock_enforcer.add_grouping_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_add_role_for_user("testuser", "admin")

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
        result = pm.perms_add_role_for_user("testuser", "admin")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_add_role_for_user_exception(self, mock_enforcer_class):
        """Test adding role for user with exception."""
        mock_enforcer = Mock()
        mock_enforcer.add_grouping_policy.side_effect = Exception("Add failed")
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_add_role_for_user("testuser", "admin")

        assert result is False

    @patch("wy_qcos.user.permission_manager.casbin.Enforcer")
    def test_perms_delete_role_for_user_with_role(self, mock_enforcer_class):
        """Test deleting role for user with specific role."""
        mock_enforcer = Mock()
        mock_enforcer.remove_grouping_policy.return_value = True
        mock_enforcer_class.return_value = mock_enforcer

        pm = PermissionManager("model.conf", "policy.csv")
        result = pm.perms_delete_role_for_user("testuser", "admin")

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
        result = pm.perms_delete_role_for_user("testuser")

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
        result = pm.perms_delete_role_for_user("testuser", "admin")

        assert result is False
