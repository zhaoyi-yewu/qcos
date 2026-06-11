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
import uuid
from typing import Any

from sqlalchemy.orm import Session

from wy_qcos.api.schemas import user as schemas
from wy_qcos.api.schemas.user import LoginLog
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.db.models.user import User as UserModel
from wy_qcos.db.models import Job
from wy_qcos.db.repositories.user import UserRepository
from wy_qcos.db.repositories.role import RoleRepository
from wy_qcos.db.repositories.project import ProjectRepository
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.user.permission_manager import PermissionManager
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)

# Default admin user
DEFAULT_ADMIN_PASSWORD = (
    Config.USERS.ADMIN_PASSWORD
    if Config.USERS.ADMIN_PASSWORD
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
        self.users_repo: UserRepository | None = None
        self.roles_repo: RoleRepository | None = None
        self.projects_repo: ProjectRepository | None = None
        self.job_repo: JobRepository | None = None
        if db_session:
            self.users_repo = UserRepository(db_session)
            self.roles_repo = RoleRepository(db_session)
            self.projects_repo = ProjectRepository(db_session)
            self.job_repo = JobRepository(db_session)

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
        self.init_db()
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

    def init_db(self):
        """Init database (idempotent - safe to run multiple times).

        Creates default projects, roles, and admin user.
        """
        # Skip if repos are not initialized (e.g., in tests)
        if (
            self.projects_repo is None
            or self.roles_repo is None
            or self.users_repo is None
        ):
            return

        def init_projects(project_id, project_name):
            """Initialize a project if not already exists.

            Creates a new project in the database if it doesn't already exist.
            Logs success or failure of the operation.

            Args:
                project_id: Unique identifier (UUID) for the project
                project_name: Human-readable name of the project

            Returns:
                None. Logs project status to logger.
            """
            success, _, existing_project = (
                self.projects_repo.get_project_by_id(project_id)
            )
            if not (success and existing_project):
                success, error, project = self.projects_repo.create_project(
                    project_id, project_name
                )
                if not success:
                    error_msg = (
                        f"Failed to create project: {project_name} "
                        f"(id: {project_id}) Reason: {error}"
                    )
                    logger.error(error_msg)
            else:
                info_msg = (
                    f"Project: {project_name} (id: {project_id}) "
                    f"already exists"
                )
                logger.info(info_msg)

        def init_roles(role_name, description=""):
            """Initialize a role if not already exists.

            Creates a new role with default permissions if not exists.
            Assigns permissions based on the role type.

            Args:
                role_name: Name of the role to create
                description: Optional description of the role's purpose

            Returns:
                None. Created role is stored internally in roles_db.
            """
            if not self.get_role(role_name):
                self.create_role(
                    role_name,
                    permissions=self.get_permissions_list(
                        self.get_default_policies(role_name)
                    ),
                    description=description,
                )

        def init_users(
            user_name,
            project_id,
            role_names,
            password,
            user_id=None,
            description="",
        ):
            """Initialize a user if not already exists.

            Creates a new user in the specified project with assigned roles
            if the user doesn't already exist. The user is created with the
            account enabled but not locked, and no password expiry.

            Args:
                user_name: Unique username for the user
                project_id: Project ID (UUID) this user belongs to
                role_names: List of role names to assign to the user
                password: Initial password for the user
                user_id: User ID
                description: Optional description of the user's purpose

            Returns:
                None. Created user is stored internally in users_db.
            """
            if not self.get_user(user_name):
                self.create_user(
                    project_id,
                    user_name,
                    password,
                    role_names,
                    True,
                    False,
                    0,
                    user_id=user_id,
                    description=description,
                )

        # init projects
        init_projects(Constant.ADMIN_PROJECT_ID, Constant.ADMIN_PROJECT_NAME)
        init_projects(
            Constant.DEFAULT_PROJECT_ID, Constant.DEFAULT_PROJECT_NAME
        )

        # init roles
        init_roles(
            Constant.ROLE_ADMIN,
            description="Administrator with full permissions",
        )
        init_roles(
            Constant.ROLE_USER,
            description="Regular user with basic permissions",
        )

        # init users
        init_users(
            Constant.ADMIN_USERNAME,
            Constant.ADMIN_PROJECT_ID,
            [Constant.ROLE_ADMIN],
            DEFAULT_ADMIN_PASSWORD,
            description="Administrator with full permissions",
        )
        init_users(
            Constant.ANONYMOUS_USERNAME,
            Constant.DEFAULT_PROJECT_ID,
            [Constant.ROLE_ADMIN],
            DEFAULT_ADMIN_PASSWORD,
            user_id=Constant.ANONYMOUS_USER_ID,
            description="Anonymous user with full permissions (auth_mode=no)",
        )

    def load_role_permissions(self):
        """Load all role permissions from database.

        This method reads all roles and their permissions from the
        database and adds them to the casbin-based permission manager.
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
                "RoleRepository not available, cannot reload "
                "permissions from database"
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
                f"User name '{user_name}' is invalid. "
                f"Cannot start with underscore"
            )

        # Check if user name contains only allowed characters:
        # Must start with letter, then contain only letters, digits, hyphens,
        # underscores
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", user_name):
            raise ValueError(
                f"User name '{user_name}' is invalid. "
                f"Must start with a letter or digital and contain only "
                f"letters, digits, hyphens, or underscores"
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
        # Must start with letter, then contain only letters, digits, hyphens,
        # underscores
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", role_name):
            raise ValueError(
                f"Role name '{role_name}' is invalid. "
                f"Must start with a letter and contain only "
                f"letters, digits, hyphens, or underscores"
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
        """Create a new role.

        Args:
            role_name: role name
            permissions: permissions
            description: description

        Returns:
            created role

        Raises:
            ValueError: if role name is invalid or already exists
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
            description=description,
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

        # Reload permission policies after creating role with permissions
        if permissions:
            reload_success = self.reload_role_permissions_from_db()
            if reload_success:
                logger.info(
                    f"Successfully reloaded permission policies from "
                    f"database after creating role '{role.role_name}'"
                )
            else:
                logger.warning(
                    f"Failed to reload permission policies from "
                    f"database after creating role '{role.role_name}'"
                )

        return role

    def update_role(
        self,
        role_id: str,
        permissions: list[str] | None = None,
        description: str | None = None,
        role_name: str | None = None,
    ) -> schemas.Role:
        """Update role.

        Args:
            role_id: role ID (primary identifier)
            permissions: permissions
            description: description
            role_name: role name

        Returns:
            updated role

        Raises:
            ValueError: if role not found or validation fails
        """
        # Get role by ID
        role = self.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID '{role_id}' not found")

        # Get role_name from role object if not provided
        if not role_name:
            role_name = role.role_name

        # Validate inputs
        if description is not None:
            self.validate_description(description)
        if permissions is not None:
            self.validate_permissions(permissions)

        # Prepare role_id as UUID for request
        # role.id is UUID from schema, convert to UUID if needed
        role_id_str = str(role.id)
        try:
            role_id_value: uuid.UUID = uuid.UUID(role_id_str)
        except (ValueError, AttributeError):
            role_id_value = uuid.uuid4()

        # Update in database
        update_request = schemas.UpdateRoleRequest(
            role_id=role_id_value,
            permissions=permissions,
            description=description,
        )
        success, error, updated_role = self.roles_repo.update_role(
            str(role.id), update_request
        )
        if not success or not updated_role:
            raise ValueError(f"Failed to update role: {error}")

        # Update policies
        if permissions is not None:
            # Delete existing policies
            self.perms_remove_role(role_name)
            # Add new policies
            for permission in permissions:
                self.perms_add_policy(role_name, permission, "call")

        # Reload permission policies after updating
        reload_success = self.reload_role_permissions_from_db()
        if reload_success:
            logger.info(
                f"Successfully reloaded permission policies from "
                f"database after updating role '{updated_role.role_name}'"
            )
        else:
            logger.warning(
                f"Failed to reload permission policies from "
                f"database after updating role '{updated_role.role_name}'"
            )

        # Retrieve the updated role from database to ensure permissions are
        # reflected
        refreshed_role = self.get_role_by_id(str(role.id))
        if refreshed_role:
            return refreshed_role

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

    def get_role_by_id(self, role_id: str) -> schemas.Role | None:
        """Get role by ID.

        Args:
            role_id: role ID (UUID or role name)

        Returns:
            role
        """
        # First, try to get by ID
        success, _, role = self.roles_repo.get_role_by_id(str(role_id))
        if success and role:
            return role

        # Fallback: try to get by role name if ID lookup fails
        # This allows using role name as an alias for role ID
        if role_id in self._role_name_to_id:
            # Found in mapping, try again with the actual UUID
            actual_id = self._role_name_to_id[role_id]
            success, _, role = self.roles_repo.get_role_by_id(str(actual_id))
            if success and role:
                return role

        # Try direct name lookup as last resort
        success, _, role = self.roles_repo.get_role_by_name(role_id)
        if success and role:
            return role

        return None

    def get_roles(
        self, filters: dict | None = None
    ) -> dict[str, schemas.Role]:
        """Get roles keyed by role ID with optional filtering.

        Args:
            filters: Dictionary with filter conditions
                    (e.g., {'role_name': 'admin'})

        Returns:
            roles keyed by role_id, filtered by criteria
        """
        # Call repository with filters parameter
        success, _, roles = self.roles_repo.get_roles(filters=filters)
        if success:
            return {str(role.id): role for role in roles}
        return {}

    def delete_role(self, role_id: str) -> schemas.Role:
        """Delete role by ID.

        Args:
            role_id: role ID (UUID)

        Returns:
            deleted role

        Raises:
            ValueError: if role not found, is admin role, or is used by users
        """
        # Get role by ID
        role = self.get_role_by_id(role_id)
        if not role:
            raise ValueError(f"Role with ID '{role_id}' not found")

        role_name = role.role_name

        # Don't allow deletion of admin role
        if role_name == Constant.ROLE_ADMIN:
            raise ValueError("Cannot delete admin role")

        # Check if any users are using this role
        users_using_role = []
        if self.users_repo:
            success, _, users = self.users_repo.get_users()
            if success and users:
                for user in users:
                    # Get roles safely from ORM model
                    user_roles = []
                    if hasattr(user, "get_role_names"):
                        user_roles = user.get_role_names()
                    elif hasattr(user, "roles") and isinstance(
                        user.roles, list
                    ):
                        user_roles = user.roles

                    if role_name in user_roles:
                        users_using_role.append(user)

        # Delete from database
        success, error = self.roles_repo.delete_role_by_id(str(role.id))
        if not success:
            raise ValueError(f"Failed to delete role: {error}")

        # Remove role from all users that have it (cascade delete)
        for user in users_using_role:
            try:
                # Remove this role from user's roles
                updated_roles = [r for r in user.roles if r != role_name]
                self.update_user(
                    str(user.id),
                    roles=updated_roles if updated_roles else None,
                )
                logger.info(
                    f"Removed role '{role_name}' from user '{user.user_name}' "
                    f"during role deletion"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to remove role '{role_name}' from user "
                    f"'{user.user_name}': {e}"
                )

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

        # Reload permission policies after role deletion
        reload_success = self.reload_role_permissions_from_db()
        if reload_success:
            logger.info(
                f"Successfully reloaded permission policies after "
                f"deleting role '{role_name}'"
            )
        else:
            logger.warning(
                f"Failed to reload permission policies after "
                f"deleting role '{role_name}'"
            )

        logger.info(f"Deleted role: {role_name} (ID: {role_id})")

        return role

    def create_user(
        self,
        project_id: str,
        user_name: str,
        password: str,
        roles: list[str],
        is_enabled: bool,
        is_locked: bool,
        password_expiry_days: int,
        description: str | None = None,
        user_id: str | None = None,
    ):
        """Create user.

        Args:
            project_id: project id (required, defaults to DEFAULT_PROJECT_ID)
            user_name: user name
            password: password
            roles: roles
            is_enabled: is enabled
            is_locked: is locked
            password_expiry_days: password expiry days
            description: description
            user_id: user id

        Returns:
            created user
        """
        # Enforce default project_id in backend and ensure it's a UUID
        if not project_id:
            project_id = str(Constant.DEFAULT_PROJECT_ID)
        # Convert project_id to UUID if it's a string
        if isinstance(project_id, str):
            try:
                project_id = str(uuid.UUID(project_id))
            except (ValueError, AttributeError):
                project_id = str(Constant.DEFAULT_PROJECT_ID)

        # Convert user_id to UUID if it's a string
        if isinstance(user_id, str):
            try:
                user_id = str(uuid.UUID(user_id))
            except (ValueError, AttributeError):
                raise ValueError(
                    f"Invalid user id: {user_id}, UUID format is required"
                )

        # Validate inputs
        self.validate_user_name(user_name)
        self.validate_password(password)
        self.validate_description(description)
        self.validate_roles(roles)

        # Validate project exists (if projects_repo is available)
        if self.projects_repo:
            success, _, existing_project = (
                self.projects_repo.get_project_by_id(project_id)
            )
            if not (success and existing_project):
                raise ValueError(
                    f"Project with ID '{project_id}' does not exist"
                )

        # Check if user already exists
        success, _, existing_user = self.users_repo.get_user_by_username(
            user_name
        )
        if success and existing_user:
            raise ValueError(f"User '{user_name}' already exists")

        # Create in database
        create_request = schemas.CreateUserRequest(
            user_id=user_id,
            project_id=project_id,
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

        # Reload permission policies after creating new user with roles
        if roles:
            reload_success = self.reload_role_permissions_from_db()
            if reload_success:
                logger.info(
                    f"Successfully reloaded permission policies from "
                    f"database after creating user '{user.user_name}'"
                )
            else:
                logger.warning(
                    f"Failed to reload permission policies from "
                    f"database after creating user '{user.user_name}'"
                )

        return user

    def update_user(
        self,
        user_id: str,
        roles: list[str] | None = None,
        is_enabled: bool | None = None,
        is_locked: bool | None = None,
        password_expiry_days: int | None = None,
        description: str | None = None,
        user_name: str | None = None,
    ):
        """Update user.

        Args:
            user_id: user ID (primary identifier)
            roles: roles
            is_enabled: is enabled
            is_locked: is locked
            password_expiry_days: password expiry days
            description: description
            user_name: user name (for compatibility, optional)

        Returns:
            updated user
        """
        # Get user by ID
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID '{user_id}' not found")

        # Get user_name from user object if not provided
        if not user_name:
            user_name = user.user_name

        # Validate inputs
        if roles is not None:
            self.validate_roles(roles)
        if description is not None:
            self.validate_description(description)

        # Handle special case: unlocking user
        if is_locked is not None and is_locked is False:
            try:
                # For unlocking, use update_user with is_locked=False
                update_request = schemas.UpdateUserRequest(
                    user_id=uuid.UUID(str(user.id)),
                    is_locked=False,
                )
                success, error, updated_user = self.users_repo.update_user(
                    str(user.id), update_request
                )
                if not success or not updated_user:
                    logger.warning(
                        f"Update returned: success={success}, error={error}"
                    )
                else:
                    logger.debug(
                        f"Successfully cleared locked_until and "
                        f"failed_login_attempts for user {user_id}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to clear locked fields via update: {e}",
                    exc_info=True,
                )
                raise ValueError(f"Failed to unlock user: {str(e)}")
        else:
            # Normal update for non-unlock cases
            update_params: dict[str, Any] = {}
            if roles is not None:
                update_params["roles"] = roles
            if is_enabled is not None:
                update_params["is_enabled"] = is_enabled
            if is_locked is not None:
                update_params["is_locked"] = is_locked
            if password_expiry_days is not None:
                update_params["password_expiry_days"] = password_expiry_days
            if description is not None:
                update_params["description"] = description

            update_params["user_id"] = uuid.UUID(str(user.id))
            update_request = schemas.UpdateUserRequest(**update_params)
            success, error, updated_user = self.users_repo.update_user(
                str(user.id), update_request
            )
            if not success or not updated_user:
                raise ValueError(f"Failed to update user: {error}")

        # Update role permissions if roles changed
        if roles is not None:
            # Delete existing roles
            self.perms_delete_role_for_user(user_name)
            # Add new roles
            for role_name in roles:
                self.perms_add_role_for_user(user_name, role_name)

        # Reload permission policies after updating
        reload_success = self.reload_role_permissions_from_db()
        if reload_success:
            logger.info(
                f"Successfully reloaded permission policies after "
                f"updating user '{user_name}'"
            )
        else:
            logger.warning(
                f"Failed to reload permission policies after "
                f"updating user '{user_name}'"
            )

        return updated_user

    def change_password(
        self,
        user_id: str,
        old_password: str | None = None,
        new_password: str | None = None,
    ):
        """Change user password.

        Args:
            user_id: user ID (UUID)
            old_password: current password (required for non-admin users)
            new_password: new password

        Returns:
            updated user

        Raises:
            ValueError: if user not found, password validation fails, etc.
        """
        # Get user by ID
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID '{user_id}' not found")

        user_name = user.user_name

        # Validate new password
        if not new_password:
            raise ValueError("New password is required")

        self.validate_password(new_password)

        # For non-admin users, validate old password
        if user_name != Constant.ADMIN_USERNAME:
            if not old_password:
                raise ValueError(
                    "Old password is required for non-admin users"
                )

            if not UserRepository.verify_password(
                old_password, user.hashed_password
            ):
                raise ValueError("Incorrect old password")

        # Update password in database
        try:
            # Use PasswordChangeRequest which supports password field
            password_change = schemas.PasswordChangeRequest(
                user_id=str(user_id), password=new_password
            )

            success, error, updated_user = self.users_repo.update_user(
                user_id, password_change
            )
            if not success or not updated_user:
                raise ValueError(f"Failed to change password: {error}")

            logger.info(
                f"Password changed successfully for user '{user_name}' "
                f"(ID: {user_id})"
            )

            return updated_user
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            raise ValueError(f"Failed to change password: {str(e)}")

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
            user_id: user ID (UUID or user name)

        Returns:
            user
        """
        # First, try to get by ID
        success, _, user = self.users_repo.get_user_by_id(str(user_id))
        if success and user:
            return user

        # Fallback: try to get by user name if ID lookup fails
        # This allows using user name as an alias for user ID
        if user_id in self._username_to_id:
            # Found in mapping, try again with the actual UUID
            actual_id = self._username_to_id[user_id]
            success, _, user = self.users_repo.get_user_by_id(str(actual_id))
            if success and user:
                return user

        # Try direct name lookup as last resort
        success, _, user = self.users_repo.get_user_by_username(user_id)
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

    def get_users(
        self, filters: dict | None = None
    ) -> dict[str, schemas.User]:
        """Get users with optional filtering.

        Args:
            filters: Dictionary with filter conditions
                    (e.g., {'user_name': 'admin', 'is_enabled': True})

        Returns:
            users keyed by user_id, filtered by criteria
        """
        # Call repository with filters parameter
        success, _, users = self.users_repo.get_users(filters=filters)
        if success:
            return {user.id: user for user in users}
        return {}

    def delete_user(self, user_id: str, force: bool = False) -> schemas.User:
        """Delete user by user_id.

        Args:
            user_id: user ID (primary identifier)
            force: force delete (cascade delete related jobs if True)

        Returns:
            deleted user

        Raises:
            ValueError: if user not found, user is admin, or has related jobs
                        (when force=False)
        """
        # Get user by ID
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID '{user_id}' not found")

        user_name = user.user_name

        # Don't allow deletion of admin user
        if user_name == Constant.ADMIN_USERNAME:
            raise ValueError(f"Cannot delete admin user '{user_name}'")

        # Handle cascading deletion if force=true
        if force:
            logger.info(
                f"Force deleting user '{user_name}' (ID: {user_id}). "
                f"Cleaning up related jobs..."
            )

            # Get all jobs for this user (if job_repo available)
            if self.job_repo:
                filters = {"user_id": user_id}
                success, error, user_jobs = self.job_repo.get_jobs(filters)

                if success and user_jobs:
                    flow_run_ids_to_delete = []
                    job_ids_to_delete = []

                    # Collect job IDs and flow_run_ids for deletion
                    for job_record in user_jobs:
                        if job_record.flow_run_id:
                            flow_run_ids_to_delete.append(
                                job_record.flow_run_id
                            )
                        job_ids_to_delete.append(str(job_record.id))

                    # Delete jobs from Prefect scheduler (cleanup resources)
                    if flow_run_ids_to_delete:
                        try:
                            logger.info(
                                f"Deleting {len(flow_run_ids_to_delete)} "
                                f"jobs from Prefect for user {user_name}"
                            )
                            scheduler.delete_flows(flow_run_ids_to_delete)
                        except Exception as e:
                            logger.warning(
                                f"Failed to delete some Prefect flows "
                                f"for user {user_name}: {str(e)}. "
                                f"Continuing with database cleanup..."
                            )

                    # Delete job records from database
                    for job_id in job_ids_to_delete:
                        try:
                            success, error = self.job_repo.delete_by_uuid(
                                Job, job_id
                            )
                            if not success:
                                logger.warning(
                                    f"Failed to delete job {job_id} "
                                    f"from database: {error}"
                                )
                        except Exception as e:
                            logger.warning(
                                f"Error deleting job {job_id} "
                                f"from database: {str(e)}"
                            )

                    logger.info(
                        f"Deleted {len(job_ids_to_delete)} jobs "
                        f"for user {user_name}"
                    )
                else:
                    logger.info(
                        f"No jobs found for user {user_name} to delete"
                    )
        else:
            # Non-force delete: check if user has associated jobs
            logger.info(
                f"Checking for jobs associated with user '{user_name}' "
                f"(ID: {user_id})"
            )
            if self.job_repo:
                filters = {"user_id": user_id}
                success, error, user_jobs = self.job_repo.get_jobs(filters)

                if success and user_jobs and len(user_jobs) > 0:
                    job_count = len(user_jobs)
                    raise ValueError(
                        f"User '{user_name}' has {job_count} "
                        f"associated job(s). Cannot delete without "
                        f"force=true"
                    )

        # Delete from database
        # Use actual user UUID from retrieved user object,
        # not the input user_id (which might be a user name)
        success, error = self.users_repo.delete_user_by_id(str(user.id))
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

        logger.info(f"User '{user_name}' (ID: {user_id}) deleted successfully")

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
        # Get project_id from user if exists
        project_id = None
        if success:
            # Only query user for successful logins to get project_id
            success_query, _, user = self.users_repo.get_user_by_username(
                user_name
            )
            if success_query and user:
                project_id = user.project_id

        # Create log entry
        log_entry = LoginLog(
            user_name=user_name,
            ip_address=ip_address,
            login_status=success,
            failure_reason=failure_reason,
            user_agent=user_agent,
            login_time=datetime.now(),
        )

        # Add to memory
        self.login_logs.append(log_entry)

        # Save to database directly with user_name
        self.users_repo.create_login_log(
            user_name,
            ip_address,
            success,
            failure_reason,
            user_agent,
            project_id,
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

    def get_login_logs(
        self,
        user_id: str | None = None,
        user_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """Get login logs with optional filtering.

        Args:
            user_id: Filter logs by user_id (UUID, optional)
            user_name: Filter logs by user_name (optional)
            start_time: Filter logs after this time (optional)
            end_time: Filter logs before this time (optional)
            limit: Maximum number of logs to return. Use -1 to get all
                  logs without limit (default: 100)
            offset: Number of logs to skip (default: 0)

        Returns:
            List of login logs with response format

        Raises:
            ValueError: if both user_id and user_name are provided,
                       or if user is not found
        """
        # Validate that only one of user_id or user_name is provided
        if user_id is not None and user_name is not None:
            raise ValueError(
                "Cannot specify both user_id and user_name. "
                "Please provide only one."
            )

        # If user_name provided, convert to user_id
        if user_name:
            user = self.get_user(user_name)
            if not user:
                raise ValueError(f"User '{user_name}' not found")
            user_id = str(user.id)

        # Get login logs from repository
        try:
            success, error, logs = self.users_repo.get_login_logs(
                user_id=str(user_id) if user_id else None,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                offset=offset,
            )
            if not success:
                raise ValueError(f"Failed to get login logs: {error}")
            # Convert to response format
            response_info = []
            for log in logs:
                # When user_id is not specified, need to get it from username
                response_user_id: str | None = user_id
                if response_user_id is None:
                    # Query user by username to get user_id
                    user_obj = self.get_user(log.user_name)
                    if user_obj:
                        response_user_id = str(user_obj.id)
                    else:
                        response_user_id = None
                # Get project_id from user
                response_project_id: str = Constant.DEFAULT_PROJECT_ID
                if response_user_id:
                    user_obj = self.get_user_by_id(str(response_user_id))
                    if user_obj:
                        response_project_id = str(user_obj.project_id)
                log_data = {
                    "user_id": response_user_id,
                    "project_id": response_project_id,
                    "user_name": log.user_name,
                    "login_time": log.login_time.isoformat(),
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "login_status": log.login_status,
                    "failure_reason": log.failure_reason,
                }
                # Convert dict to LoginLogResponse object
                log_response = schemas.LoginLogResponse(**log_data)
                response_info.append(log_response)
            log_count = len(response_info)
            limit_str = "unlimited" if limit == -1 else str(limit)
            logger.info(
                f"Retrieved {log_count} login logs "
                f"(limit={limit_str}, offset={offset})"
            )
            return response_info
        except Exception as e:
            logger.error(f"Failed to get login logs: {e}")
            raise ValueError(f"Failed to get login logs: {str(e)}")

    def clear_login_logs(
        self, user_id: str | None = None, user_name: str | None = None
    ) -> dict:
        """Clear login logs (all or for a specific user).

        Args:
            user_id: User ID (UUID) to clear logs for (optional)
            user_name: User name to clear logs for (optional)

        Returns:
            Dictionary with count of deleted logs

        Raises:
            ValueError: if both user_id and user_name are provided
        """
        # Validate that only one of user_id or user_name is provided
        if user_id is not None and user_name is not None:
            raise ValueError(
                "Cannot specify both user_id and user_name. "
                "Please provide only one."
            )

        try:
            # If user_name provided, convert to user_id
            if user_name:
                user = self.get_user(user_name)
                if user:
                    user_id = str(user.id)
                # If user doesn't exist, let delete_login_logs handle it
                # by passing user_name instead

            # Delete login logs from repository
            success, error, deleted_count = self.users_repo.delete_login_logs(
                user_id=str(user_id) if user_id else None, user_name=user_name
            )

            if not success:
                logger.error(f"Failed to clear login logs: {error}")
                raise ValueError(f"Failed to clear login logs: {error}")

            # Build filter description for logging
            if user_id:
                filter_desc = f"user_id={str(user_id)}"
            elif user_name:
                filter_desc = f"user_name={user_name}"
            else:
                filter_desc = "all"

            logger.info(
                f"Cleared {deleted_count} login log(s) ({filter_desc})"
            )
            return {"count": deleted_count}
        except Exception as e:
            logger.error(f"Failed to clear login logs: {e}")
            raise ValueError(f"Failed to clear login logs: {str(e)}")

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

    def auto_unlock_user(self, user_id: str) -> bool:
        """Auto-unlock user after lockout period expires.

        Args:
            user_id: user ID (UUID)

        Returns:
            True if successful, False otherwise
        """
        try:
            success, error, updated_user = self.users_repo.update(
                UserModel,
                str(user_id),
                is_locked=False,
                locked_until=None,
                failed_login_attempts=0,
            )
            if success and updated_user:
                logger.debug(f"Auto-unlocked user {user_id}")
                return True
            else:
                logger.warning(
                    f"Failed to auto-unlock user {user_id}: {error}"
                )
                return False
        except Exception as e:
            logger.error(f"Error auto-unlocking user {user_id}: {e}")
            return False

    def increment_failed_login_attempts(self, user_id: str) -> bool:
        """Increment failed login attempts for user.

        Args:
            user_id: user ID (UUID)

        Returns:
            True if successful, False otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return False

            new_attempts = (user.failed_login_attempts or 0) + 1
            success, error, updated_user = self.users_repo.update(
                UserModel,
                str(user_id),
                failed_login_attempts=new_attempts,
            )
            if success:
                logger.debug(
                    f"Incremented failed login attempts to {new_attempts} "
                    f"for user {user_id}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to update failed_login_attempts for user "
                    f"{user_id}: {error}"
                )
                return False
        except Exception as e:
            logger.error(
                f"Error incrementing failed login attempts for user "
                f"{user_id}: {e}"
            )
            return False

    def lock_user(self, user_id: str, locked_until: datetime) -> bool:
        """Lock user account until specified time.

        Args:
            user_id: user ID (UUID)
            locked_until: datetime until which user is locked

        Returns:
            True if successful, False otherwise
        """
        try:
            success, error, updated_user = self.users_repo.update(
                UserModel,
                str(user_id),
                is_locked=True,
                locked_until=locked_until,
            )
            if success:
                logger.info(f"Locked user {user_id} until {locked_until}")
                return True
            else:
                logger.error(f"Failed to lock user {user_id}: {error}")
                return False
        except Exception as e:
            logger.error(f"Error locking user {user_id}: {e}")
            return False

    def update_successful_login(self, user_id: str) -> bool:
        """Update user after successful login.

        Resets failed login attempts, updates last login time,
        and unlocks the account if needed.

        Args:
            user_id: user ID (UUID)

        Returns:
            True if successful, False otherwise
        """
        try:
            success, error, updated_user = self.users_repo.update(
                UserModel,
                str(user_id),
                failed_login_attempts=0,
                last_login=datetime.now(),
                is_locked=False,
                locked_until=None,
            )
            if success:
                logger.debug(f"Updated login info for user {user_id}")
                return True
            else:
                logger.warning(
                    f"Failed to update login info for user {user_id}: {error}"
                )
                return False
        except Exception as e:
            logger.error(f"Error updating login info for user {user_id}: {e}")
            return False
