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

from datetime import datetime, timedelta
import logging
import re

from sqlalchemy.orm import Session

from wy_qcos.api.schemas import user as schemas
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.db.repositories.user import UserRepository
from wy_qcos.db.repositories.role import RoleRepository
from wy_qcos.user.permission_manager import PermissionManager

logger = logging.getLogger(__name__)

# Default admin user
DEFAULT_ADMIN_USERNAME = Constant.DEFAULT_ADMIN_USERNAME
DEFAULT_ADMIN_PASSWORD = (
    Config.ADMIN_PASSWORD
    if Config.ADMIN_PASSWORD
    else Constant.DEFAULT_ADMIN_PASSWORD
)


class UserManager:
    """User manager."""

    def __init__(
        self,
        access_control_model_file: str,
        access_control_policy_file: str,
        all_api,
        db_session: Session = None,
    ):
        """Init UserManager.

        Args:
            db_session: Database session
            access_control_model_file: Access control model file path
            access_control_policy_file: Access control policy file path
            all_api: list of all API endpoints
        """
        self._db_session = db_session
        if db_session:
            self.users_repo = UserRepository(db_session)
            self.roles_repo = RoleRepository(db_session)
        else:
            # Backward compatibility mode - will be initialized later
            self.users_repo = None
            self.roles_repo = None

        self.all_api = all_api
        # Initialize permission manager for casbin access control
        self.permission_manager = PermissionManager(
            access_control_model_file, access_control_policy_file
        )
        # Internal data structures for managing users and roles
        self.users_db = {}
        self.roles_db = {}
        self._username_to_id = {}
        self._role_name_to_id = {}
        self.login_logs = []
        self.perms_check = self.permission_manager

        self.default_admin_policies = self.fetch_default_policies(
            role=Constant.ROLE_ADMIN
        )
        self.default_user_policies = self.fetch_default_policies(
            role=Constant.ROLE_USER
        )
        self.default_all_policies = self.fetch_default_policies()
        self.noauth_policies = self.fetch_default_policies(
            role=Constant.ROLE_ANY
        )
        self.init_users()
        self.load_role_permissions()

    def get_permissions_list(self, policies):
        """Get permissions list.

        Args:
            policies: permission policies

        Returns:
            permission list
        """
        permission_list = []
        for policy in policies:
            permission_list.append(policy[1])
        return permission_list

    def init_users(self):
        """Init users (idempotent - safe to run multiple times)."""
        # Skip if repos are not initialized (e.g., in tests)
        if self.roles_repo is None or self.users_repo is None:
            return

        # Create admin role only if not exists
        if not self.get_role(Constant.ROLE_ADMIN):
            self.create_role(
                Constant.ROLE_ADMIN,
                permissions=self.get_permissions_list(
                    self.get_default_policies(Constant.ROLE_ADMIN)
                ),
                description="Administrator with full permissions",
            )

        # Create user role only if not exists
        if not self.get_role(Constant.ROLE_USER):
            self.create_role(
                Constant.ROLE_USER,
                permissions=self.get_permissions_list(
                    self.get_default_policies(Constant.ROLE_USER)
                ),
                description="Regular user with basic permissions",
            )

        # Create default admin user only if not exists
        if not self.get_user(DEFAULT_ADMIN_USERNAME):
            self.create_user(
                DEFAULT_ADMIN_USERNAME,
                DEFAULT_ADMIN_PASSWORD,
                [Constant.ROLE_ADMIN],
                True,
                False,
                0,
                description="Administrator with full permissions",
            )

    def load_role_permissions(self):
        """Load all role permissions from database and add to permission system.

        This method reads all roles and their permissions from the database
        and adds them to the casbin-based permission manager.
        """
        # Skip if roles_repo not initialized (e.g., in tests)
        if self.roles_repo is None:
            return

        try:
            # Get all roles from database
            success, error, roles = self.roles_repo.get_roles()
            if not success or not roles:
                logger.info("No roles found in database to load")
                return

            # For each role, add its permissions to the permission system
            for role in roles:
                role_name = role.role_name
                permissions = role.permissions if role.permissions else []

                logger.info(f"Loading permissions for role: {role_name}")

                # Add each permission to the casbin policy
                for permission in permissions:
                    try:
                        self.perms_add_policy(role_name, permission, "call")
                        logger.debug(
                            f"Added policy: {role_name}, {permission}, call"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to add policy for role '{role_name}' "
                            f"and permission '{permission}': {e}"
                        )

            logger.info(
                "Successfully loaded all role permissions from database"
            )
        except Exception as e:
            logger.error(f"Failed to load role permissions: {e}")

    def perms_enforce(self, sub: str, obj: str, act: str) -> bool:
        """Permission enforce.

        Args:
            sub: sub
            obj: obj
            act: act

        Returns:
            policy enforced results: True, False
        """
        return self.permission_manager.enforce(sub, obj, act)

    def perms_add_policy(self, sub: str, obj: str, act: str) -> bool:
        """Add permission policy.

        Args:
            sub: sub
            obj: obj
            act: act

        Returns:
            policy added results: True, False
        """
        return self.permission_manager.add_policy(sub, obj, act)

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
        return self.permission_manager.remove_policy(sub, obj, act)

    def perms_remove_role(self, role_name):
        """Remove permission role.

        Args:
            role_name: role name

        Returns:
            role removed results: True, False
        """
        return self.permission_manager.remove_role(role_name)

    def perms_get_for_role(self, role: str) -> list:
        """Get all permissions for role.

        Args:
            role: role

        Returns:
            role permissions
        """
        return self.permission_manager.get_for_role(role)

    def perms_add_role_for_user(self, user: str, role: str) -> bool:
        """Add permission role for user.

        Args:
            user: user
            role: role
        """
        return self.permission_manager.add_role_for_user(user, role)

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
        return self.permission_manager.delete_role_for_user(user, role)

    def reload_role_permissions_from_db(self) -> bool:
        """Reload all role permissions from database to permission system.

        This method clears all policies and reloads them from the database,
        ensuring that any role permission changes are reflected in Casbin.

        Returns:
            True if reload successful, False otherwise
        """
        if not self.roles_repo:
            logger.warning(
                "RoleRepository not available, cannot reload permissions from database"
            )
            return False
        return self.permission_manager.reload_policy_from_db(self.roles_repo)

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

        # User role permissions
        for api_entrypoint in self.all_api:
            for entrypoint_route in api_entrypoint.routes:
                if not entrypoint_route.openapi_extra:
                    continue
                objs = entrypoint_route.openapi_extra.get("allowed_roles", [])
                for obj in objs:
                    if role is None or (
                        role == obj and role in [Constant.ROLE_USER]
                    ):
                        permissions.append((
                            obj,
                            entrypoint_route.path,
                            "call",
                        ))
                if entrypoint_route.openapi_extra.get("no_auth", False):
                    if role is None or role in [Constant.ROLE_ANY]:
                        permissions.append((
                            "*",
                            entrypoint_route.path,
                            "call",
                        ))
        permissions.sort()
        if role:
            logger.info(f"Permissions of role: {role}")
            for permission in permissions:
                logger.info(permission)
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
        elif role == Constant.ROLE_ANY:
            policies = self.noauth_policies
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

        # Check if user name starts with underscore
        if user_name.startswith("_"):
            raise ValueError(
                f"User name '{user_name}' cannot start with underscore"
            )

        # Check if user name contains only allowed characters:
        # letters (a-z, A-Z), digits (0-9), hyphen (-), underscore (_)
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", user_name):
            raise ValueError(
                f"User name '{user_name}' is invalid. "
                f"Must start with a letter and contain only letters, "
                f"digits, hyphens, or underscores"
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

        # Check if role name starts with underscore
        if role_name.startswith("_"):
            raise ValueError(
                f"Role name '{role_name}' cannot start with underscore"
            )

        # Check if role name contains only allowed characters:
        # letters (a-z, A-Z), digits (0-9), hyphen (-), underscore (_)
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", role_name):
            raise ValueError(
                f"Role name '{role_name}' is invalid. "
                f"Must start with a letter and contain only letters, "
                f"digits, hyphens, or underscores"
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
        success, _, existing_role = self.roles_repo.get_role_by_name(role_name)
        if success and existing_role:
            raise ValueError(f"Role '{role_name}' already exists")

        # assign user permissions if permissions are not specified
        if permissions is None:
            permissions = self.get_permissions_list(
                self.get_default_policies(Constant.ROLE_USER)
            )
        else:
            self.validate_permissions(permissions)

        # Create in database
        create_request = schemas.CreateRoleRequest(
            role_name=role_name,
            permissions=permissions,
            description=description or "",
        )
        success, error, role = self.roles_repo.create_role(create_request)
        if not success or not role:
            raise ValueError(f"Failed to create role: {error}")

        # Add to internal storage
        self.roles_db[role_name] = role
        if hasattr(role, "id"):
            self._role_name_to_id[role_name] = role.id

        # add policies
        for permission in permissions:
            self.perms_add_policy(role_name, permission, "call")

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

        # Update in database
        update_request = schemas.UpdateRoleRequest(
            role_id=role.id,
            permissions=permissions,
            description=description,
        )
        success, error, updated_role = self.roles_repo.update_role(
            role.id, update_request
        )
        if not success or not updated_role:
            raise ValueError(f"Failed to update role: {error}")

        # update policies
        if permissions is not None:
            # delete existing policies
            self.perms_remove_role(role_name)
            # add new policies
            for permission in permissions:
                self.perms_add_policy(role_name, permission, "call")

        return updated_role

    def get_role(self, role_name: str) -> schemas.Role | None:
        """Get role by name.

        Args:
            role_name: name of the role

        Returns:
            role
        """
        success, _, role = self.roles_repo.get_role_by_name(role_name)
        if success and role:
            return role
        return None

    def get_roles(self) -> dict[str, schemas.Role]:
        """Get roles keyed by role_name.

        Returns:
            roles keyed by role_name
        """
        # Return dict keyed by role_name for backward compatibility
        success, _, roles = self.roles_repo.get_roles()
        if success:
            return {role.role_name: role for role in roles}
        return {}

    def delete_role(self, role_name: str) -> schemas.Role:
        """Delete role.

        Args:
            role_name: role name
        """
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found")

        # Delete from database
        success, error = self.roles_repo.delete_role_by_id(role.id)
        if not success:
            raise ValueError(f"Failed to delete role: {error}")

        # Remove from internal storage
        if role_name in self.roles_db:
            del self.roles_db[role_name]
        if hasattr(role, "id") and role.id in self._role_name_to_id.values():
            # Remove from mapping
            self._role_name_to_id = {
                k: v for k, v in self._role_name_to_id.items() if v != role.id
            }

        # Remove policies
        self.perms_remove_role(role_name)

        return role

    def create_user(
        self,
        user_name: str,
        password: str,
        roles: list[str],
        is_enabled: bool,
        is_locked: bool,
        password_expiry_days: int,
        description: str | None = None,
    ):
        """Create user.

        Args:
            user_name: user name
            password: password
            roles: roles
            is_enabled: is enabled
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
        success, _, existing_user = self.users_repo.get_user_by_username(
            user_name
        )
        if success and existing_user:
            raise ValueError(f"User '{user_name}' already exists")

        # Create in database
        create_request = schemas.CreateUserRequest(
            user_name=user_name,
            password=password,
            roles=roles,
            is_enabled=is_enabled,
            is_locked=is_locked,
            password_expiry_days=password_expiry_days,
            description=description,
        )
        success, error, user = self.users_repo.create_user(create_request)
        if not success or not user:
            raise ValueError(f"Failed to create user: {error}")

        # Add to internal storage
        self.users_db[user_name] = user
        if hasattr(user, "id"):
            self._username_to_id[user_name] = user.id

        # Add role permissions
        for role_name in roles:
            self.perms_add_role_for_user(user_name, role_name)

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
            is_enabled: is enabled
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

        # Update in database
        update_request = schemas.UpdateUserRequest(
            user_id=user.id,
            roles=roles,
            is_enabled=is_enabled,
            is_locked=is_locked,
            password_expiry_days=password_expiry_days,
            description=description,
        )
        success, error, updated_user = self.users_repo.update_user(
            user.id, update_request
        )
        if not success or not updated_user:
            raise ValueError(f"Failed to update user: {error}")

        # Update role permissions if roles changed
        if roles is not None:
            # delete existing roles
            self.perms_delete_role_for_user(user_name)
            # add new roles
            for role_name in roles:
                self.perms_add_role_for_user(user_name, role_name)

        return updated_user

    def get_user(self, user_name: str | None = None) -> schemas.User | None:
        """Get user by name.

        Args:
            user_name: name of the user

        Returns:
            user
        """
        if user_name is None:
            return None

        success, _, user = self.users_repo.get_user_by_username(user_name)
        if success and user:
            return user
        return None

    def get_user_by_id(self, user_id: str) -> schemas.User | None:
        """Get user by ID.

        Args:
            user_id: user ID

        Returns:
            user
        """
        success, _, user = self.users_repo.get_user_by_id(user_id)
        if success and user:
            return user
        return None

    def get_user_by_name(self, user_name: str) -> schemas.User | None:
        """Get user by name.

        Args:
            user_name: name of the user

        Returns:
            user
        """
        return self.get_user(user_name)

    def get_users(self) -> dict[str, schemas.User]:
        """Get users.

        Returns:
            users
        """
        success, _, users = self.users_repo.get_users()
        if success:
            return {user.id: user for user in users}
        return {}

    def delete_user(self, user_name: str) -> schemas.User:
        """Delete user.

        Args:
            user_name: user name
        """
        user = self.get_user(user_name)
        if not user:
            raise ValueError(f"User '{user_name}' not found")

        # Delete from database
        success, error = self.users_repo.delete_user_by_id(user.id)
        if not success:
            raise ValueError(f"Failed to delete user: {error}")

        # Remove from internal storage
        if user_name in self.users_db:
            del self.users_db[user_name]
        if hasattr(user, "id") and user.id in self._username_to_id.values():
            # Remove from mapping
            self._username_to_id = {
                k: v for k, v in self._username_to_id.items() if v != user.id
            }

        # Remove permissions
        self.perms_delete_role_for_user(user_name)

        return user

    def find_users_by_role(self, role_name: str) -> list[str]:
        """Find users by role name.

        Args:
            role_name: role name

        Returns:
            list of usernames
        """
        users = []
        success, _, all_users = self.users_repo.get_users()
        if success:
            for user in all_users:
                if role_name in user.roles:
                    users.append(user.user_name)
        return users

    def log_login_attempt(
        self,
        user_name: str,
        ip_address: str,
        success: bool,
        failure_reason: str | None = None,
        user_agent: str | None = None,
    ):
        """Log login attempt.

        Args:
            user_name: user name
            ip_address: ip address
            success: whether login was successful
            failure_reason: reason for failure if not successful
            user_agent: user agent
        """
        # Create log entry
        from wy_qcos.api.schemas.user import LoginLog

        log_entry = LoginLog(
            user_name=user_name,
            ip_address=ip_address,
            success=success,
            failure_reason=failure_reason,
            user_agent=user_agent,
            timestamp=datetime.now(),
        )

        # Add to memory
        self.login_logs.append(log_entry)

        # Save to database directly with user_name
        self.users_repo.create_login_log(
            user_name, ip_address, success, failure_reason, user_agent
        )

        # Format login time in human-readable format
        login_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_str = "successful" if success else f"failed ({failure_reason})"
        logger.info(
            f"Login attempt: user={user_name}, "
            f"time={login_time_str}, "
            f"ip={ip_address}, "
            f"status={status_str}"
        )

    def get_login_logs(self, user_name: str | None = None, limit: int = 100):
        """Get login logs with optional user_name filter.

        Args:
            user_name: Filter logs by username (optional)
            limit: Maximum number of logs to return

        Returns:
            login logs
        """
        if user_name:
            success, _, logs = self.users_repo.get_login_logs(
                user_id=None, limit=limit
            )
            if success and logs:
                # Filter by user_name
                filtered_logs = [
                    log for log in logs if log.user_name == user_name
                ]
                return filtered_logs
            return []
        else:
            success, _, logs = self.users_repo.get_login_logs(limit=limit)
            if success:
                return logs
            return []

    def add_to_blacklist(self, token_jti: str, expires_at: datetime) -> None:
        """Add a token to the blacklist.

        Args:
            token_jti: Unique identifier of the token (JWT 'jti' claim)
            expires_at: When the token would have expired
        """
        success, error = self.users_repo.add_to_blacklist(
            token_jti, expires_at
        )
        if not success:
            logger.error(
                f"Failed to add token {token_jti} to blacklist: {error}"
            )
        # Clean up expired entries periodically
        self._cleanup_blacklist()

    def is_blacklisted(self, token_jti: str) -> bool:
        """Check if a token is blacklisted.

        Args:
            token_jti: Unique identifier of the token (JWT 'jti' claim)

        Returns:
            True if token is blacklisted, False otherwise
        """
        return self.users_repo.is_blacklisted(token_jti)

    def _cleanup_blacklist(self) -> None:
        """Remove expired entries from the blacklist."""
        self.users_repo.cleanup_blacklist()

    @staticmethod
    def is_password_expired(user: schemas.User) -> bool:
        """Check if password has expired.

        Args:
            user: user

        Returns:
            is_password_expired
        """
        # If password_expiry_days is not set or 0, password never expires
        if (
            not hasattr(user, "password_expiry_days")
            or not user.password_expiry_days
            or user.password_expiry_days <= 0
        ):
            return False

        if (
            not hasattr(user, "password_changed_at")
            or user.password_changed_at is None
        ):
            return False

        expiry_days = user.password_expiry_days
        expiry_date = user.password_changed_at + timedelta(days=expiry_days)
        return datetime.now() > expiry_date

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password.

        Args:
            password: password

        Returns:
            hashed password
        """
        # Use UserRepository for password hashing
        return UserRepository.hash_password(password)

    @staticmethod
    def check_password(password: str, password_hash: str) -> bool:
        """Check if password matches hash.

        Args:
            password: password
            password_hash: hashed password

        Returns:
            passwords are matched
        """
        # Use UserRepository for password verification
        return UserRepository.verify_password(password, password_hash)
