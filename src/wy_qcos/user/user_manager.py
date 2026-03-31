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
from datetime import datetime, timedelta

import casbin
import hashlib

from wy_qcos.api.schemas import user as schemas
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant

logger = logging.getLogger(__name__)

# Default admin user
DEFAULT_ADMIN_USERNAME = Constant.DEFAULT_ADMIN_USERNAME
DEFAULT_ADMIN_PASSWORD = (
    Config.ADMIN_PASSWORD
    if Config.ADMIN_PASSWORD
    else Constant.DEFAULT_ADMIN_PASSWORD
)
MAX_LOGIN_ENTRIES = 100


class UserManager:
    """User manager."""

    def __init__(
        self, access_control_model_file, access_control_policy_file, all_api
    ):
        """Init UserManager.

        Args:
            access_control_model_file (str): Access control model file path
            access_control_policy_file (str): Access control policy file path
            all_api: list of all API endpoints
        """
        self.users_db = {}
        self.roles_db = {}
        self.login_logs = []
        self.enforcer = None
        self.access_control_model_file = access_control_model_file
        self.access_control_policy_file = access_control_policy_file
        self.all_api = all_api
        self.init_enforcer()
        self.default_admin_policies = self.fetch_default_policies(
            role=Constant.ROLE_ADMIN
        )
        self.default_user_policies = self.fetch_default_policies(
            role=Constant.ROLE_USER
        )
        self.default_all_policies = self.fetch_default_policies()
        self.init_users()

    def get_permissions_list(self, policies):
        """Get permissions list."""
        permission_list = []
        for policy in policies:
            permission_list.append(policy[1])
        return permission_list

    def init_users(self):
        """Init users."""
        # Create admin role
        role = self.create_role(
            Constant.ROLE_ADMIN,
            permissions=self.get_permissions_list(
                self.get_default_policies(Constant.ROLE_ADMIN)
            ),
            description="Administrator with full permissions",
        )
        self.roles_db[Constant.ROLE_ADMIN] = role

        # Create user role
        role = self.create_role(
            Constant.ROLE_USER,
            permissions=self.get_permissions_list(
                self.get_default_policies(Constant.ROLE_USER)
            ),
            description="Regular user with basic permissions",
        )
        self.roles_db[Constant.ROLE_USER] = role

        # Create default admin user
        user = self.create_user(
            DEFAULT_ADMIN_USERNAME,
            DEFAULT_ADMIN_PASSWORD,
            [Constant.ROLE_ADMIN],
            True,
            False,
            0,
            description="Administrator with full permissions",
        )
        self.users_db[DEFAULT_ADMIN_USERNAME] = user

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
        """Add permission policy."""
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

    def fetch_default_policies(self, role=None):
        """Fetch default policies based on role.

        Args:
            role: role

        Returns:
            default policies
        """
        permissions = []
        if role is None or role == Constant.ROLE_ADMIN:
            # Admin role permissions
            permissions.append((Constant.ROLE_ADMIN, "*", "*"))
        if role is None or role == Constant.ROLE_USER:
            # User role permissions
            for api_entrypoint in self.all_api:
                for entrypoint_route in api_entrypoint.routes:
                    if not entrypoint_route.openapi_extra:
                        continue
                    objs = entrypoint_route.openapi_extra.get(
                        "allowed_roles", []
                    )
                    for obj in objs:
                        permissions.append((
                            obj,
                            entrypoint_route.path,
                            "call",
                        ))
                    if entrypoint_route.openapi_extra.get("no_auth", False):
                        permissions.append((
                            "*",
                            entrypoint_route.path,
                            "call",
                        ))
        permissions.sort()
        return permissions

    def get_default_policies(self, role=None, simple=False):
        """Get default policies based on role.

        Args:
            role: role
            simple: return simple list

        Returns:
            default policies
        """
        policies = []
        if role == Constant.ROLE_ADMIN:
            policies = self.default_admin_policies
        elif role == Constant.ROLE_USER:
            policies = self.default_user_policies
        else:
            policies = self.default_all_policies
        if simple:
            return [item[1] for item in policies]
        return policies

    def validate_user_name(self, user_name: str) -> None:
        """Validate user name.

        Args:
            user_name: user name

        Raises:
            ValueError: if user name is invalid
        """
        if len(user_name) < Constant.MIN_USER_LENGTH:
            raise ValueError(
                f"User name '{user_name}' is too short "
                f"(minimum {Constant.MIN_USER_LENGTH} characters)"
            )

        if len(user_name) > Constant.MAX_USER_LENGTH:
            raise ValueError(
                f"User name '{user_name}' is too long "
                f"(maximum {Constant.MAX_USER_LENGTH} characters)"
            )

    def validate_password(self, password: str) -> None:
        """Validate password.

        Args:
            password: password

        Raises:
            ValueError: if password is invalid
        """
        if len(password) < Constant.MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password is too short "
                f"(minimum {Constant.MIN_PASSWORD_LENGTH} characters)"
            )

        if len(password) > Constant.MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"Password is too long "
                f"(maximum {Constant.MAX_PASSWORD_LENGTH} characters)"
            )

    def validate_role_name(self, role_name: str) -> None:
        """Validate role name.

        Args:
            role_name: role name

        Raises:
            ValueError: if role name is invalid
        """
        if len(role_name) < Constant.MIN_ROLE_LENGTH:
            raise ValueError(
                f"Role name '{role_name}' is too short "
                f"(minimum {Constant.MIN_ROLE_LENGTH} characters)"
            )

        if len(role_name) > Constant.MAX_ROLE_LENGTH:
            raise ValueError(
                f"Role name '{role_name}' is too long "
                f"(maximum {Constant.MAX_ROLE_LENGTH} characters)"
            )

    def validate_description(self, description: str | None) -> None:
        """Validate description.

        Args:
            description: description

        Raises:
            ValueError: if description is invalid
        """
        if description and len(description) > Constant.MAX_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Description is too long "
                f"(maximum {Constant.MAX_DESCRIPTION_LENGTH} characters)"
            )

    def validate_roles(self, roles: list[str]) -> None:
        """Validate roles.

        Args:
            roles: list of roles

        Raises:
            ValueError: if roles are invalid
        """
        for role_name in roles:
            if not self.get_role(role_name):
                raise ValueError(f"Role '{role_name}' does not exist")

    def validate_permissions(self, permissions: list[str]) -> None:
        """Validate permissions.

        Args:
            permissions: list of permissions

        Raises:
            ValueError: if permissions are invalid
        """
        invalid_permissions = []
        for permission in permissions:
            if permission not in self.get_default_policies(simple=True):
                invalid_permissions.append(permission)
        if invalid_permissions:
            raise ValueError(
                f"Invalid permission: {', '.join(invalid_permissions)}"
            )

    def create_role(
        self,
        role_name: str,
        permissions: list[str] | None,
        description: str | None = None,
    ) -> schemas.Role:
        """Add role.

        Args:
            role_name: role name
            permissions: permissions
            description: description

        Returns:
            created role
        """
        # Validate inputs
        self.validate_role_name(role_name)
        self.validate_description(description)

        # Check if role already exists
        if role_name in self.roles_db:
            raise ValueError(f"Role '{role_name}' already exists")

        # assign user permissions if permissions are not specified
        if permissions is None:
            permissions = self.get_permissions_list(
                self.get_default_policies(Constant.ROLE_USER)
            )
        else:
            self.validate_permissions(permissions)

        role = schemas.Role(
            role_name=role_name,
            permissions=permissions,
            description=description,
        )

        # add policies
        for permission in permissions:
            self.perms_add_policy(role_name, permission, "call")

        self.roles_db[role_name] = role
        return role

    def update_role(
        self,
        role_name: str,
        permissions: list[str] | None,
        description: str | None = None,
    ) -> schemas.Role:
        """Update role.

        Args:
            role_name: role name
            permissions: permissions
            description: description

        Returns:
            updated role
        """
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found")

        # Validate inputs
        if description is not None:
            self.validate_description(description)
        if permissions is not None:
            self.validate_permissions(permissions)

        # update role
        if permissions is not None:
            role.permissions = permissions
        if description is not None:
            role.description = description

        # update policies
        if permissions is not None:
            # delete existing policies
            self.perms_remove_role(role_name)
            # add new policies
            for permission in permissions:
                self.perms_add_policy(role_name, permission, "call")

        return role

    def get_role(self, role_name: str) -> schemas.Role:
        """Get role by name.

        Args:
            role_name: name of the role

        Returns:
            role
        """
        return self.roles_db.get(role_name)

    def get_roles(self) -> dict[str, schemas.Role]:
        """Get roles.

        Returns:
            roles
        """
        return self.roles_db

    def delete_role(self, role_name: str) -> schemas.Role:
        """Delete role.

        Args:
            role_name: role name
        """
        if role_name not in self.roles_db:
            raise ValueError(f"Role '{role_name}' not found")
        self.perms_remove_role(role_name)
        return self.roles_db.pop(role_name)

    def create_user(
        self,
        user_name: str,
        password: str,
        roles: list[str],
        is_enable: bool,
        is_locked: bool,
        password_expiry_days: int,
        description: str | None = None,
    ):
        """Create user.

        Args:
            user_name: user name
            password: password
            roles: roles
            is_enable: is enable
            is_locked: is locked
            password_expiry_days: password expiry days
            description: description

        Returns:
            created user
        """
        # Validate inputs
        self.validate_user_name(user_name)
        self.validate_password(password)
        self.validate_description(description)
        self.validate_roles(roles)

        # Check if user already exists
        if user_name in self.users_db:
            raise ValueError(f"User '{user_name}' already exists")

        # Create user
        user = schemas.User(
            user_name=user_name,
            password_hash=UserManager.hash_password(password),
            roles=roles,
            password_expiry_days=password_expiry_days,
            is_enabled=is_enable,
            is_locked=is_locked,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            password_changed_at=datetime.now(),
        )

        # Add role permissions
        for role_name in roles:
            self.perms_add_role_for_user(user_name, role_name)

        self.users_db[user_name] = user
        return user

    def update_user(
        self,
        user_name: str,
        roles: list[str] | None = None,
        is_enabled: bool | None = None,
        is_locked: bool | None = None,
        password_expiry_days: int | None = None,
        description: str | None = None,
    ):
        """Update user.

        Args:
            user_name: user name
            roles: roles
            is_enabled: is enable
            is_locked: is locked
            password_expiry_days: password expiry days
            description: description

        Returns:
            updated user
        """
        user = self.get_user(user_name)
        if not user:
            raise ValueError(f"User '{user_name}' not found")

        # Validate inputs
        if roles is not None:
            self.validate_roles(roles)
        if description is not None:
            self.validate_description(description)

        # Update user fields
        if roles is not None:
            user.roles = roles
        if is_enabled is not None:
            user.is_enabled = is_enabled
        if is_locked is not None:
            user.is_locked = is_locked
        if password_expiry_days is not None:
            user.password_expiry_days = password_expiry_days
        if description is not None:
            user.description = description

        # Update the updated_at timestamp
        user.updated_at = datetime.now()

        # Update role permissions if roles changed
        if roles is not None:
            # delete existing roles
            self.perms_delete_role_for_user(user_name)
            # add new roles
            for role_name in roles:
                self.perms_add_role_for_user(user_name, role_name)

        return user

    def get_user(self, user_name: str | None = None) -> schemas.User:
        """Get user by name.

        Args:
            user_name: name of the user

        Returns:
            user
        """
        return self.users_db.get(user_name)

    def get_users(self) -> dict[str, schemas.User]:
        """Get users.

        Returns:
            users
        """
        return self.users_db

    def delete_user(self, user_name: str) -> schemas.User:
        """Delete user.

        Args:
            user_name: user name
        """
        self.perms_delete_role_for_user(user_name)
        return self.users_db.pop(user_name)

    def find_users_by_role(self, role_name: str) -> list[str]:
        """Find users by role name.

        Args:
            role_name: role name

        Returns:
            users
        """
        users = []
        for user, user_info in self.users_db.items():
            if role_name in user_info.roles:
                users.append(user)
        return users

    def log_login_attempt(
        self,
        user_name: str,
        ip_address: str,
        status: str,
        user_agent: str | None = None,
    ):
        """Log login attempt.

        Args:
            user_name: user name
            ip_address: ip address
            status: status
            user_agent: user agent
        """
        log_entry = schemas.LoginLog(
            user_name=user_name,
            ip_address=ip_address,
            login_status=status,
            user_agent=user_agent,
        )
        self.login_logs.append(log_entry)
        # Keep only last 1000 logs
        if len(self.login_logs) > MAX_LOGIN_ENTRIES:
            self.login_logs.pop(0)

    def get_login_logs(self):
        """Get login logs.

        Returns:
            login logs
        """
        return self.login_logs

    @staticmethod
    def is_password_expired(user: schemas.User) -> bool:
        """Check if password has expired.

        Args:
            user: user

        Returns:
            is_password_expired
        """
        if (
            not hasattr(user, "password_changed_at")
            or user.password_changed_at is None
        ):
            return False

        expiry_days = user.password_expiry_days or 0
        expiry_date = user.password_changed_at + timedelta(days=expiry_days)
        return datetime.now() > expiry_date

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256.

        Args:
            password: password

        Returns:
            hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def check_password(password: str, password_hash: str) -> bool:
        """Check if password matches hash.

        Args:
            password: password
            password_hash: hashed password

        Returns:
            passwords are matched
        """
        return UserManager.hash_password(password) == password_hash
