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

import casbin

logger = logging.getLogger(__name__)


class PermissionManager:
    """Permission manager using Casbin for access control."""

    def __init__(self, access_control_model_file, access_control_policy_file):
        """Init PermissionManager.

        Args:
            access_control_model_file (str): Access control model file path
            access_control_policy_file (str): Access control policy file path
        """
        self.enforcer = None
        self.access_control_model_file = access_control_model_file
        self.access_control_policy_file = access_control_policy_file
        self.init_enforcer()

    def init_enforcer(self):
        """Initialize Casbin Enforcer."""
        try:
            # Initialize Enforcer with policy file
            self.enforcer = casbin.Enforcer(
                self.access_control_model_file, self.access_control_policy_file
            )
            logger.info(
                "Casbin Enforcer initialized successfully with "
                "model file: %s, policy file: %s",
                self.access_control_model_file,
                self.access_control_policy_file,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Casbin Enforcer: {e}")
            raise

    def perms_check_enforce(self, sub: str, obj: str, act: str) -> bool:
        """Permission enforce check.

        Args:
            sub: sub
            obj: obj
            act: act

        Returns:
            policy enforced results: True, False
        """
        if not self.enforcer:
            logger.warning("Casbin Enforcer not initialized")
            return False

        try:
            result = self.enforcer.enforce(sub, obj, act)
            logger.debug(
                f"Permission enforce: {sub} -> {obj}:{act} = {result}"
            )
            return result
        except Exception as e:
            logger.error(f"Permission enforce failed: {e}")
            return False

    def perms_add_policy(self, sub: str, obj: str, act: str) -> bool:
        """Add permission policy.

        Args:
            sub: sub
            obj: obj
            act: act

        Returns:
            policy added results: True, False
        """
        try:
            result = self.enforcer.add_policy(sub, obj, act)
            if result:
                logger.debug(f"Added permission policy: {sub} -> {obj}:{act}")
            return result
        except Exception as e:
            logger.error(f"Failed to add permission policy: {e}")
            return False

    def perms_remove_policy(
        self, sub: str, obj: str | None = None, act: str | None = None
    ) -> bool:
        """Remove permission policy.

        Args:
            sub: sub
            obj: obj
            act: act

        Returns:
            policy removed results: True, False
        """
        try:
            result = self.enforcer.remove_policy(sub, obj, act)
            if result:
                logger.debug(
                    f"Removed permission policy: {sub} -> {obj}:{act}"
                )
            return result
        except Exception as e:
            logger.error(f"Failed to remove permission policy: {e}")
            return False

    def perms_remove_role(self, role_name):
        """Remove permission role.

        Args:
            role_name: role name

        Returns:
            role removed results: True, False
        """
        try:
            result = self.enforcer.delete_role(role_name)
            if result:
                logger.debug(f"Removed permission role: {role_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to remove permission role: {e}")
            return False

    def perms_get_for_role(self, role: str) -> list:
        """Get all permissions for role.

        Args:
            role: role

        Returns:
            role permissions
        """
        try:
            return self.enforcer.get_permissions_for_user(role)
        except Exception as e:
            logger.error(f"Failed to get permissions for role {role}: {e}")
            return []

    def perms_add_role_for_user(self, user: str, role: str) -> bool:
        """Add permission role for user.

        Args:
            user: user
            role: role
        """
        try:
            result = self.enforcer.add_grouping_policy(user, role)
            if result:
                logger.debug(f"Added permission role {role} for user {user}")
            return result
        except Exception as e:
            logger.error(f"Failed to add permission role for user {user}: {e}")
            return False

    def perms_delete_role_for_user(
        self, user: str, role: str | None = None
    ) -> bool:
        """Delete permission role for user.

        Args:
            user: user
            role: role

        Returns:
            role deleted for user results: True, False
        """
        try:
            if role:
                result = self.enforcer.remove_grouping_policy(user, role)
            else:
                result = self.enforcer.delete_roles_for_user(user)
            if result:
                logger.debug(f"Removed permission role {role} for user {user}")
            return result
        except Exception as e:
            logger.error(
                f"Failed to remove permission role for user {user}: {e}"
            )
            return False
