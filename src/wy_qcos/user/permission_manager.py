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

    def enforce(self, sub: str, obj: str, act: str) -> bool:
        """Permission enforce.

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

    def add_policy(self, sub: str, obj: str, act: str) -> bool:
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

    def remove_policy(
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

    def remove_role(self, role_name):
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

    def get_for_role(self, role: str) -> list:
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

    def add_role_for_user(self, user: str, role: str) -> bool:
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

    def delete_role_for_user(self, user: str, role: str | None = None) -> bool:
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

    def reload_policy(self) -> bool:
        """Reload all policies from policy file.

        This method reloads the access control policies from the
        policy file, ensuring that any changes to role permissions
        are reflected in the system.

        Returns:
            True if reload successful, False otherwise
        """
        try:
            if not self.enforcer:
                logger.warning("Casbin Enforcer not initialized")
                return False

            result = self.enforcer.load_policy()
            if result:
                logger.info("Successfully reloaded Casbin policies from file")
            else:
                logger.warning("Reload policies returned False")
            return result
        except Exception as e:
            logger.error(f"Failed to reload Casbin policies: {e}")
            return False

    def reload_policy_from_db(self, roles_repo=None) -> bool:
        """Reload all policies from database.

        This method clears all policies and reloads them from database,
        useful when role permissions are updated in the database.

        Args:
            roles_repo: RoleRepository instance to load roles and
                        permissions from

        Returns:
            True if reload successful, False otherwise
        """
        if not roles_repo:
            logger.warning(
                "RoleRepository not provided for reloading "
                "policies from database"
            )
            return False

        try:
            if not self.enforcer:
                logger.warning("Casbin Enforcer not initialized")
                return False

            # Clear all existing policies
            self.enforcer.clear_policy()
            logger.debug("Cleared all policies from memory")

            # Get all roles from database
            success, error, roles = roles_repo.get_roles()
            if not success or not roles:
                logger.info("No roles found in database to load")
                return True

            # Add each role's permissions to the enforcer
            for role in roles:
                role_name = role.role_name
                permissions = role.permissions if role.permissions else []

                logger.debug(f"Loading permissions for role: {role_name}")

                # Add each permission to the casbin policy
                for permission in permissions:
                    try:
                        result = self.add_policy(role_name, permission, "call")
                        if result:
                            logger.debug(
                                f"Added policy: {role_name}, {permission}, "
                                f"call"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Failed to add policy for role '{role_name}' "
                            f"and permission '{permission}': {e}"
                        )

            logger.info(
                "Successfully reloaded all role permissions from database"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to reload policies from database: {e}")
            return False

    def clear_policy(self) -> bool:
        """Clear all policies from memory.

        This method clears all policies from the Casbin enforcer,
        useful when policies need to be refreshed from database.

        Returns:
            True if clear successful, False otherwise
        """
        try:
            if not self.enforcer:
                logger.warning("Casbin Enforcer not initialized")
                return False

            self.enforcer.clear_policy()
            logger.info("Successfully cleared all Casbin policies from memory")
            return True
        except Exception as e:
            logger.error(f"Failed to clear Casbin policies: {e}")
            return False
