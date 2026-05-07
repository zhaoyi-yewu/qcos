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

import logging
import pytest

from wy_qcos.common.library import _s
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestRole:
    """Role management system tests."""

    test_roles = [
        "_test_role_st",
        "_test_role_perms",
    ]
    test_users = [
        "_test_user_st_role",
        "_test_user_remove_role",
    ]

    @classmethod
    def _cleanup_test_resources(cls):
        """Clean up test roles and users."""
        StLibrary.login(
            cls.admin_client, cls.admin_user, str(cls.admin_password)
        )
        for role_name in cls.test_roles:
            try:
                StLibrary.delete_role(
                    cls.admin_client, role_name, is_name=True
                )
            except Exception:
                logging.warning("Exception during cleanup")

        for username in cls.test_users:
            try:
                StLibrary.delete_user(
                    cls.admin_client, username, is_name=True, force=True
                )
            except Exception:
                logging.warning("Exception during cleanup")

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
        cls.password = _s("TestPassword123!")

        # Clean up any existing test resources before starting tests
        cls._cleanup_test_resources()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls._cleanup_test_resources()

    @pytest.mark.smoke
    def test_get_default_roles(self):
        """Test getting default roles."""
        roles = StLibrary.get_roles(self.admin_client)
        assert roles is not None
        assert isinstance(roles, (dict, list))
        # Check if contains admin role
        role_names = (
            list(roles.keys())
            if isinstance(roles, dict)
            else [r.get("role_name") for r in roles if isinstance(r, dict)]
        )
        assert len(role_names) > 0

    @pytest.mark.smoke
    def test_get_admin_role(self):
        """Test getting admin role info."""
        role = StLibrary.get_role(self.admin_client, "admin", is_name=True)
        assert role is not None
        assert role["role_name"] == "admin"
        assert "permissions" in role

    @pytest.mark.smoke
    def test_create_and_delete_role(self):
        """Test creating and deleting role."""
        # Create new role
        role_data = {
            "role_name": "_test_role_st",
            "permissions": ["read", "write"],
            "description": "Test role for system testing",
        }

        try:
            created_role = StLibrary.create_role(self.admin_client, role_data)
            assert created_role is not None
            assert created_role["role_name"] == "_test_role_st"
            assert "read" in created_role.get("permissions", [])

            # Verify role is created
            retrieved_role = StLibrary.get_role(
                self.admin_client, "_test_role_st", is_name=True
            )
            assert retrieved_role["role_name"] == "_test_role_st"

        finally:
            # Delete role
            try:
                StLibrary.delete_role(
                    self.admin_client, "_test_role_st", is_name=True
                )
            except Exception:
                logging.warning("Exception during cleanup")

    @pytest.mark.smoke
    def test_get_all_roles_list(self):
        """Test getting all roles list."""
        roles = StLibrary.get_roles(self.admin_client)
        assert roles is not None
        assert len(roles) > 0

        # Check structure of each role
        if isinstance(roles, dict):
            for role_id, role_info in roles.items():
                assert isinstance(role_id, str)
                assert isinstance(role_info, dict)
                assert "role_name" in role_info
        elif isinstance(roles, list):
            for role in roles:
                assert isinstance(role, dict)
                assert "role_name" in role
