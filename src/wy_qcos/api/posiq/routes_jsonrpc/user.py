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
from datetime import datetime
from typing import Any

from fastapi import Depends, Request

from wy_qcos.api.schemas import user as schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import user_api_v1
from wy_qcos.common import args_schema
from wy_qcos.common.constant import Constant
from wy_qcos.common.config import Config
from wy_qcos.common.library import Library
from wy_qcos.db.models.user import User as UserModel
from wy_qcos.db.repositories.user import UserRepository
from wy_qcos.db.repositories.role import RoleRepository
from wy_qcos.db.utils.db_utils import get_repository
from .dependencies.authentication import auth, auth_match_user_id


logger = logging.getLogger(__name__)
module_name = "USER"


def get_user_manager(request: Request):
    """Get user manager.

    Args:
        request: request object

    Returns:
        user manager object
    """
    return request.app.state._user_manager


def _mask_hidden_fields(obj: Any) -> Any:
    """Mask fields with hidden=True in json_schema_extra.

    Args:
        obj: The object to process (can be a Pydantic model or dict)

    Returns:
        The object with hidden fields masked
    """
    if hasattr(obj, "model_fields"):
        # It's a Pydantic model
        result = {}
        for field_name, field_info in obj.model_fields.items():
            value = getattr(obj, field_name, None)
            # Check if field has json_schema_extra with hidden=True
            if (
                field_info.json_schema_extra
                and field_info.json_schema_extra.get("is_sensitive") is True
            ):
                result[field_name] = "********"
            else:
                result[field_name] = _mask_hidden_fields(value)
        return result
    elif isinstance(obj, dict):
        # It's a dictionary
        result = {}
        for key, value in obj.items():
            result[key] = _mask_hidden_fields(value)
        return result
    elif isinstance(obj, list):
        # It's a list
        return [_mask_hidden_fields(item) for item in obj]
    else:
        # It's a primitive type, return as is
        return obj


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]}, errors=[]
)
def get_user_mgmt(
    body: schemas.GetUserMgmtRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetUserMgmtResponse:
    """Get user management status.

    Args:
        body: request body
        auth_data: auth data

    Returns:
        User management status response
    """
    func_name = "get_user_mgmt"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    _response_info = {
        "auth_mode": Config.AUTH_MODE,
        "password_expiry_days": Config.PASSWORD_EXPIRY_DAYS
        if Config.PASSWORD_EXPIRY_DAYS
        else 0,
        "max_login_attempts": Config.MAX_LOGIN_ATTEMPTS,
        "lockout_duration_minutes": Config.LOCKOUT_DURATION_MINUTES,
    }
    response_info = schemas.GetUserMgmtResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.BadRequestError],
)
def set_user_mgmt(
    body: schemas.SetUserMgmtRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.SetUserMgmtResponse:
    """Set user management authentication mode.

    Args:
        body: request body with auth_mode
        auth_data: auth data

    Returns:
        SetUserMgmtResponse with updated auth_mode
    """
    func_name = "set_user_mgmt"
    logger.info(f"Call {func_name}: auth_mode={body.auth_mode}")

    auth_mode = body.auth_mode.lower()
    valid_modes = Constant.AUTH_MODES

    if auth_mode not in valid_modes:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Invalid auth_mode '{auth_mode}'. "
                f"Must be one of: {', '.join(valid_modes)}",
            ),
        )

    # Update Config dynamically
    Config.AUTH_MODE = auth_mode
    logger.info(f"Updated Config.AUTH_MODE to '{auth_mode}'")

    _response_info = {
        "auth_mode": Config.AUTH_MODE,
        "message": f"Authentication mode updated to '{auth_mode}'",
    }
    response_info = schemas.SetUserMgmtResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.ConflictError, jsonrpc_errors.BadRequestError],
)
def create_user(
    body: schemas.CreateUserRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
    roles_repo: RoleRepository = Depends(get_repository(RoleRepository)),
) -> schemas.CreateUserResponse:
    """Create a new user.

    Args:
        body: user creation request
        request: request object
        auth_data: auth data
        users_repo: User repository dependency
        roles_repo: Role repository dependency

    Returns:
        Create user response
    """
    func_name = "create_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_name = body.user_name
    password = body.password
    roles = body.roles
    description = body.description

    # Set project_id to default if not provided
    project_id = body.project_id or Constant.DEFAULT_PROJECT_ID
    # Update body with resolved project_id for later use
    body.project_id = project_id

    # Validate user name length
    if len(user_name) < Constant.MIN_USER_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"User name '{user_name}' is too short "
                f"(minimum {Constant.MIN_USER_LENGTH} characters)",
            ),
        )

    if len(user_name) > Constant.MAX_USER_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"User name '{user_name}' is too long "
                f"(maximum {Constant.MAX_USER_LENGTH} characters)",
            ),
        )

    # valid user name schema
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_schema(user_name, args_schema.NAME_SCHEMA),
    )

    # Validate password length
    if len(password) < Constant.MIN_PASSWORD_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Password is too short "
                f"(minimum {Constant.MIN_PASSWORD_LENGTH} characters)",
            ),
        )

    if len(password) > Constant.MAX_PASSWORD_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Password is too long "
                f"(maximum {Constant.MAX_PASSWORD_LENGTH} characters)",
            ),
        )

    # Check if user already exists using database
    success, error, existing_user = users_repo.get_user_by_username(user_name)
    if success and existing_user:
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (False, f"User '{user_name}' already exists"),
        )

    # Validate roles using database
    for role_name in roles:
        success, error, role = roles_repo.get_role_by_name(role_name)
        if not success or not role:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, f"Role '{role_name}' does not exist"),
            )

    if description and len(description) > Constant.MAX_DESCRIPTION_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Description is too long "
                f"(maximum {Constant.MAX_DESCRIPTION_LENGTH} characters)",
            ),
        )

    # Create user using database
    user = None
    try:
        success, error, user = users_repo.create_user(body)
        if not success or not user:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, str(error) if error else "Failed to create user"),
            )

        # Reload permission policies after creating new user with roles
        if user and roles:
            user_manager = get_user_manager(request)
            if user_manager:
                reload_success = user_manager.reload_role_permissions_from_db()
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
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )

    _response_info = get_user_response(user)
    response_info = schemas.CreateUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_user(
    body: schemas.GetUserRequest,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> schemas.GetUserResponse:
    """Get user information by ID.

    Args:
        body: get user request (contains user_id)
        auth_data: auth data
        users_repo: User repository dependency

    Returns:
        Get user response
    """
    func_name = "get_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = body.user_id

    # authentication: match user id
    auth_match_user_id(user_id, auth_data, allow_admin=True)

    success, error, user = users_repo.get_user_by_id(user_id)
    if not success or not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User with ID '{user_id}' not found"),
        )

    _response_info = get_user_response(user)
    response_info = schemas.GetUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]}, errors=[]
)
def get_users(
    body: schemas.GetUsersRequest | None = None,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> dict[str, schemas.GetUserResponse]:
    """Get users with optional filtering.

    Args:
        body: get users request with optional filter dict
        auth_data: auth data
        users_repo: User repository dependency

    Returns:
        Dictionary of users keyed by user_name

    Filter example:
        {"user_name": "admin"} - filter by user_name
    """
    func_name = "get_users"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    users = []
    # Extract filter conditions from request body
    filter_conditions = None
    if body and body.filters:
        filter_conditions = body.filters

    # Apply filtering logic
    if filter_conditions and "user_name" in filter_conditions:
        # Filter by user_name: fetch single user
        user_name = filter_conditions["user_name"]
        success, error, user = users_repo.get_user_by_username(user_name)
        if not success or not user:
            # If user not found with filter, return empty dict
            users = []
        else:
            users = [user]
    else:
        # Get all users when no filter or empty filter
        success, error, users = users_repo.get_users()
        if not success:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, f"Failed to get users: {error}"),
            )

    # Build response
    response_info = {}
    for user in users:
        user_data = get_user_response(user)
        response_info[user.id] = schemas.GetUserResponse.model_validate(
            user_data
        )

    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.BadRequestError],
)
def update_user(
    body: schemas.UpdateUserRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
    roles_repo: RoleRepository = Depends(get_repository(RoleRepository)),
) -> schemas.UpdateUserResponse:
    """Update user information by ID.

    Args:
        body: user update request (contains user_id)
        request: request object
        auth_data: auth data
        users_repo: User repository dependency
        roles_repo: Role repository dependency

    Returns:
        Update user response
    """
    func_name = "update_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = body.user_id
    roles = body.roles
    is_enabled = body.is_enabled
    is_locked = body.is_locked
    password_expiry_days = body.password_expiry_days
    description = body.description

    # Get user from database
    success, error, user = users_repo.get_user_by_id(user_id)
    if not success or not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User with ID '{user_id}' not found"),
        )

    # Validate roles using database
    if roles:
        for role_name in roles:
            success, error, role = roles_repo.get_role_by_name(role_name)
            if not success or not role:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    (False, f"Role '{role_name}' does not exist"),
                )

    # Update user in database
    user = None
    roles_changed = False
    try:
        # If unlocking user, handle it specially to ensure
        # locked_until and failed_login_attempts are cleared
        if is_locked is not None and is_locked is False:
            try:
                success, error, user = users_repo.update(
                    UserModel,
                    user_id,
                    is_locked=False,
                    locked_until=None,
                    failed_login_attempts=0,
                )
                if not success or not user:
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
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    (False, f"Failed to unlock user: {str(e)}"),
                )
        else:
            # Normal update for non-unlock cases
            # Create update request with only provided fields
            update_data: dict[str, Any] = {"user_id": user_id}
            if roles is not None:
                update_data["roles"] = roles
                roles_changed = True
            if is_enabled is not None:
                update_data["is_enabled"] = is_enabled
            if is_locked is not None:
                update_data["is_locked"] = is_locked
            if password_expiry_days is not None:
                update_data["password_expiry_days"] = password_expiry_days
            if description is not None:
                update_data["description"] = description

            update_request = schemas.UpdateUserRequest(**update_data)
            success, error, user = users_repo.update_user(
                user_id, update_request
            )
            if not success or not user:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    (False, str(error) if error else "Failed to update user"),
                )

        # Reload permission policies if user roles were updated
        if roles_changed and user:
            user_manager = get_user_manager(request)
            if user_manager and user_manager.permission_manager:
                # Reload policies from database since role permissions
                # are now updated in DB
                reload_success = user_manager.reload_role_permissions_from_db()
                if reload_success:
                    logger.info(
                        f"Successfully reloaded permission policies after "
                        f"updating roles for user '{user.user_name}'"
                    )
                else:
                    logger.warning(
                        f"Failed to reload permission policies after "
                        f"updating roles for user '{user.user_name}'"
                    )
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )

    _response_info = get_user_response(user)
    response_info = schemas.UpdateUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def delete_user(
    body: schemas.DeleteUserRequest,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> schemas.DeleteUserResponse:
    """Delete user by ID.

    Args:
        body: delete user request (contains user_id and optional force flag)
        auth_data: auth data
        users_repo: User repository dependency

    Returns:
        Delete user response
    """
    func_name = "delete_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = body.user_id
    force = body.force

    # Get user from database
    success, error, user = users_repo.get_user_by_id(user_id)
    if not success or not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User with ID '{user_id}' not found"),
        )

    user_name = user.user_name
    user_project_id = user.project_id

    # Don't allow deletion of admin user
    if user_name == Constant.ADMIN_USERNAME:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "Cannot delete admin user")
        )

    # Delete user from database
    try:
        if force:
            # Force delete: cascade delete all related resources
            # TODO (zhaoyi): to be implemented, delete related jobs
            pass

        success, error = users_repo.delete_user_by_id(user_id)
        if not success:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, str(error) if error else "Failed to delete user"),
            )

        # Invalidate all active tokens for this user
        # Get all active login logs for the user and blacklist their tokens
        try:
            # Retrieve login logs to find active sessions
            success_logs, error_logs, logs = users_repo.get_login_logs(
                user_id=user_id, limit=10000
            )

            if success_logs and logs:
                # Note: We cannot directly get tokens from login logs
                # since they are not stored. However, we can notify
                # the system that this user's tokens are no longer valid
                # by marking all their tokens as invalidated (this would
                # require a separate mechanism)
                logger.warning(
                    f"User '{user_name}' (ID: {user_id}) has been "
                    f"deleted. All their active sessions should be "
                    f"invalidated."
                )

            # Optional: Add a marker in the database to indicate
            # user deletion. This can be used to reject any subsequent
            # token validations for this user
            logger.info(
                f"User '{user_name}' (ID: {user_id}) deletion "
                f"completed. Tokens will be rejected on next "
                f"validation attempt."
            )

        except Exception as e:
            logger.warning(
                f"Could not fully invalidate user tokens during deletion: {e}"
            )

    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )

    _response_info = {
        "id": user_id,
        "project_id": user_project_id,
        "user_name": user_name,
        "deleted_at": datetime.now().isoformat(),
    }
    response_info = schemas.DeleteUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def create_role(
    body: schemas.CreateRoleRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
    roles_repo: RoleRepository = Depends(get_repository(RoleRepository)),
) -> schemas.CreateRoleResponse:
    """Create a new role.

    Args:
        body: role creation request
        request: request object
        auth_data: auth data
        roles_repo: Role repository dependency

    Returns:
        Create role response
    """
    func_name = "create_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_name = body.role_name
    description = body.description

    # Validate role name length
    if len(role_name) < Constant.MIN_ROLE_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Role name '{role_name}' is too short "
                f"(minimum {Constant.MIN_ROLE_LENGTH} characters)",
            ),
        )

    if len(role_name) > Constant.MAX_ROLE_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Role name '{role_name}' is too long "
                f"(maximum {Constant.MAX_ROLE_LENGTH} characters)",
            ),
        )

    # valid role name schema
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_schema(role_name, args_schema.NAME_SCHEMA),
    )

    # Validate description length
    if description and len(description) > Constant.MAX_DESCRIPTION_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"Description is too long "
                f"(maximum {Constant.MAX_DESCRIPTION_LENGTH} characters)",
            ),
        )

    # Check if role already exists using database
    success, error, existing_role = roles_repo.get_role_by_name(role_name)
    if success and existing_role:
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (False, f"Role '{role_name}' already exists"),
        )

    # Create role using database
    role = None
    try:
        success, error, role = roles_repo.create_role(body)
        if not success or not role:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, str(error) if error else "Failed to create role"),
            )

        # Reload permission policies after creating new role with permissions
        if role and body.permissions:
            user_manager = get_user_manager(request)
            if user_manager:
                reload_success = user_manager.reload_role_permissions_from_db()
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
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )

    _response_info = get_role_response(role)
    response_info = schemas.CreateRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_role(
    body: schemas.GetRoleRequest,
    auth_data: dict | None = Depends(auth),
    roles_repo: RoleRepository = Depends(get_repository(RoleRepository)),
) -> schemas.GetRoleResponse:
    """Get role information by ID.

    Args:
        body: get role request (contains role_id)
        auth_data: auth data
        roles_repo: Role repository dependency

    Returns:
        Get role response
    """
    func_name = "get_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = body.role_id

    # Get role from database
    success, error, role = roles_repo.get_role_by_id(role_id)
    if not success or not role:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Role with ID '{role_id}' not found"),
        )

    _response_info = get_role_response(role)
    response_info = schemas.GetRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]}, errors=[]
)
def get_roles(
    body: schemas.GetRolesRequest | None = None,
    auth_data: dict | None = Depends(auth),
    roles_repo: RoleRepository = Depends(get_repository(RoleRepository)),
) -> dict[str, schemas.GetRoleResponse]:
    """Get roles with optional filtering.

    Args:
        body: get roles request with optional filter dict
        auth_data: auth data
        roles_repo: Role repository dependency

    Returns:
        Dictionary of roles keyed by role name

    Filter example:
        {"role_name": "admin"} - filter by role_name
    """
    func_name = "get_roles"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    roles = []
    # Extract filter conditions from request body
    filter_conditions = None
    if body and body.filters:
        filter_conditions = body.filters

    # Apply filtering logic
    if filter_conditions and "role_name" in filter_conditions:
        # Filter by role_name: fetch single role
        role_name = filter_conditions["role_name"]
        success, error, role = roles_repo.get_role_by_name(role_name)
        if not success or not role:
            # If role not found with filter, return empty dict
            roles = []
        else:
            roles = [role]
    else:
        # Get all roles when no filter or empty filter
        success, error, roles = roles_repo.get_roles()
        if not success:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, f"Failed to get roles: {error}"),
            )

    # Build response
    response_info = {}
    for role in roles:
        role_data = get_role_response(role)
        response_info[role.id] = schemas.GetRoleResponse.model_validate(
            role_data
        )

    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def update_role(
    body: schemas.UpdateRoleRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
    roles_repo: RoleRepository = Depends(get_repository(RoleRepository)),
) -> schemas.UpdateRoleResponse:
    """Update role information by ID.

    Args:
        body: role update request (contains role_id)
        request: request object
        auth_data: auth data
        roles_repo: Role repository dependency

    Returns:
        Update role response
    """
    func_name = "update_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = body.role_id
    permissions = body.permissions
    description = body.description

    # Get role from database
    success, error, role = roles_repo.get_role_by_id(role_id)
    if not success or not role:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Role with ID '{role_id}' not found"),
        )

    # Update role in database
    role = None
    try:
        # Create update request with only provided fields
        update_data: dict[str, Any] = {}
        if permissions is not None:
            update_data["permissions"] = permissions
        if description is not None:
            update_data["description"] = description

        update_request = schemas.UpdateRoleRequest(
            role_id=role_id, **update_data
        )
        success, error, role = roles_repo.update_role(role_id, update_request)
        if not success or not role:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, str(error) if error else "Failed to update role"),
            )

        # Reload permission policies if permissions were updated
        if permissions is not None and role:
            user_manager = get_user_manager(request)
            if user_manager:
                reload_success = user_manager.reload_role_permissions_from_db()
                if reload_success:
                    logger.info(
                        f"Successfully reloaded permission policies from "
                        f"database after updating role '{role.role_name}'"
                    )
                else:
                    logger.warning(
                        f"Failed to reload permission policies from "
                        f"database after updating role '{role.role_name}'"
                    )
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )

    _response_info = get_role_response(role)
    response_info = schemas.UpdateRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def delete_role(
    body: schemas.DeleteRoleRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
    roles_repo: RoleRepository = Depends(get_repository(RoleRepository)),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> schemas.DeleteRoleResponse:
    """Delete role by ID.

    Args:
        body: delete role request (contains role_id)
        request: request object
        auth_data: auth data
        roles_repo: Role repository dependency
        users_repo: User repository dependency

    Returns:
        Delete role response
    """
    func_name = "delete_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = body.role_id

    # Get role from database
    success, error, role = roles_repo.get_role_by_id(role_id)
    if not success or not role:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Role with ID '{role_id}' not found"),
        )

    role_name = role.role_name

    # Don't allow deletion of admin role
    if role_name == Constant.ROLE_ADMIN:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "Cannot delete admin role")
        )

    # Check if any users are using this role
    success, error, users = users_repo.get_users()
    if success:
        users_using_role = []
        for user in users:
            # Get roles safely from ORM model
            user_roles = []
            if hasattr(user, "get_role_names"):
                user_roles = user.get_role_names()
            elif hasattr(user, "roles") and isinstance(user.roles, list):
                user_roles = user.roles

            if role_name in user_roles:
                users_using_role.append(user)

        if users_using_role:
            user_names = [user.user_name for user in users_using_role]
            jsonrpc_errors.handle_error_conflict(
                module_name,
                func_name,
                (
                    False,
                    f"Cannot delete role '{role_name}' because it is being "
                    f"used by users: {', '.join(user_names)}",
                ),
            )

    # Delete role from database
    try:
        success, error = roles_repo.delete_role_by_id(role_id)
        if not success:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, str(error) if error else "Failed to delete role"),
            )

        # Reload/clear permission policies after role deletion
        user_manager = get_user_manager(request)
        if user_manager:
            reload_success = user_manager.reload_role_permissions_from_db()
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
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )

    _response_info = {
        "role_name": role_name,
        "deleted_at": datetime.now().isoformat(),
    }
    response_info = schemas.DeleteRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={
        "allowed_roles": Constant.ALL_ROLES,
    },
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def change_password(
    body: schemas.ChangePasswordRequest,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> schemas.ChangePasswordResponse:
    """Change user password by ID.

    Args:
        body: password change request (contains user_id)
        auth_data: auth data
        users_repo: User repository dependency

    Returns:
        Change password response
    """
    func_name = "change_password"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = body.user_id
    old_password = body.old_password
    new_password = body.new_password

    # authentication: match user id
    auth_match_user_id(user_id, auth_data, allow_admin=True)

    # Get user from database
    success, error, user = users_repo.get_user_by_id(user_id)
    if not success or not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User with ID '{user_id}' not found"),
        )

    user_name = user.user_name

    # For non-admin users, validate old password
    if user_name != Constant.ADMIN_USERNAME:
        if not old_password:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, "Old password is required for non-admin users"),
            )
        if not UserRepository.verify_password(
            old_password or "", user.hashed_password
        ):
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, "Incorrect old password")
            )

    # Validate new password length
    if len(new_password) < Constant.MIN_PASSWORD_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"New password is too short "
                f"(minimum {Constant.MIN_PASSWORD_LENGTH} characters)",
            ),
        )

    if len(new_password) > Constant.MAX_PASSWORD_LENGTH:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                f"New password is too long "
                f"(maximum {Constant.MAX_PASSWORD_LENGTH} characters)",
            ),
        )

    # Update password in database
    try:
        # Use PasswordChangeRequest which supports password field
        password_change = schemas.PasswordChangeRequest(
            user_id=user_id, password=new_password
        )

        success, error, updated_user = users_repo.update_user(
            user_id, password_change
        )
        if not success or not updated_user:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, str(error) if error else "Failed to change password"),
            )
        user = updated_user
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
        )

    _response_info = {
        "user_name": user_name,
        "password_changed_at": user.password_changed_at.isoformat(),
        "message": "Password changed successfully",
    }
    response_info = schemas.ChangePasswordResponse.model_validate(
        _response_info
    )
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.BadRequestError],
)
def get_login_logs(
    body: schemas.GetLoginLogsRequest | None = None,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> list[schemas.LoginLogResponse]:
    """Get login logs by user ID or user_name.

    Args:
        body: get login logs request (contains user_id, user_name,
              limit, offset)
        auth_data: auth data
        users_repo: User repository dependency

    Returns:
        List of login logs in descending order by login_time

    Note:
        user_id and user_name are mutually exclusive. Only one can be provided.
        If both are None, all login logs will be returned.
    """
    func_name = "get_login_logs"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    # Parse time filters
    start_time = None
    end_time = None
    user_id = None

    if body:
        # Validate that only one of user_id or user_name is provided
        if body.user_id is not None and body.user_name is not None:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (
                    False,
                    "Cannot specify both user_id and user_name. "
                    "Please provide only one.",
                ),
            )

        if body.user_id:
            user_id = body.user_id
        elif body.user_name:
            # Query user by name to get user_id, raise error if not found
            success, error, user = users_repo.get_user_by_username(
                body.user_name
            )
            if not success or not user:
                jsonrpc_errors.handle_error_not_found(
                    module_name,
                    func_name,
                    (False, f"User '{body.user_name}' not found"),
                )
            user_id = user.id

        if body.start_time:
            start_time = datetime.fromisoformat(body.start_time)
        if body.end_time:
            end_time = datetime.fromisoformat(body.end_time)
        limit = body.limit if body.limit is not None else 100
        offset = body.offset if body.offset is not None else 0
    else:
        limit = 100
        offset = 0

    # Get login logs from database
    success, error, logs = users_repo.get_login_logs(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    if not success:
        # Check if error is due to user not found
        if "not found" in str(error).lower():
            jsonrpc_errors.handle_error_not_found(
                module_name,
                func_name,
                (False, str(error) if error else "User not found"),
            )
        else:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, str(error) if error else "Failed to get login logs"),
            )

    # Convert to response format
    response_info = []
    for log in logs:
        # When user_id is not specified, need to get it from username
        response_user_id = user_id
        if response_user_id is None:
            # Query user by username to get user_id
            success, error, log_user = users_repo.get_user_by_username(
                log.user_name
            )
            if success and log_user:
                response_user_id = log_user.id
            else:
                # If user not found in database
                response_user_id = None

        # Get project_id from user
        response_project_id = Constant.DEFAULT_PROJECT_ID
        if response_user_id:
            success, error, log_user = users_repo.get_user_by_id(
                response_user_id
            )
            if success and log_user:
                response_project_id = log_user.project_id

        log_data = {
            "user_id": response_user_id,
            "project_id": response_project_id,
            "user_name": log.user_name,
            "login_time": log.login_time.isoformat(),
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "success": log.login_status,
            "failure_reason": log.failure_reason,
        }
        response_info.append(schemas.LoginLogResponse.model_validate(log_data))

    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.BadRequestError],
)
def clear_login_logs(
    body: schemas.ClearLoginLogsRequest | None = None,
    auth_data: dict | None = Depends(auth),
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> dict:
    """Clear login logs (all or for a specific user).

    Args:
        body: clear login logs request (contains user_id, user_name)
        auth_data: auth data
        users_repo: User repository dependency

    Returns:
        Dictionary with count of deleted logs

    Note:
        user_id and user_name are mutually exclusive. Only one can be provided.
        If both are None, all login logs will be cleared.
    """
    func_name = "clear_login_logs"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = None
    user_name = None

    if body:
        # Validate that only one of user_id or user_name is provided
        if body.user_id is not None and body.user_name is not None:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (
                    False,
                    "Cannot specify both user_id and user_name. "
                    "Please provide only one.",
                ),
            )

        if body.user_id:
            user_id = body.user_id
        elif body.user_name:
            user_name = body.user_name
            # Query user by name to get user_id if exists
            # If user doesn't exist, user_id will remain None
            # and delete_login_logs will handle it gracefully
            success, error, user = users_repo.get_user_by_username(user_name)
            if success and user:
                user_id = user.id

    # Clear login logs from database
    success, error, deleted_count = users_repo.delete_login_logs(
        user_id=user_id, user_name=user_name
    )

    if not success:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(error) if error else "Failed to clear login logs"),
        )

    logger.info(f"Cleared {deleted_count} login log(s)")
    return {"count": deleted_count}


def get_user_response(user) -> dict:
    """Get user response.

    Args:
        user (schemas.User): User model instance

    Returns:
        schemas.GetUserResponse: Formatted user response
    """
    # Get roles from the user_roles association table
    roles = []
    if hasattr(user, "get_role_names"):
        # ORM model with relationship - get roles from association table
        roles = user.get_role_names()
    elif hasattr(user, "roles") and isinstance(user.roles, list):
        # Schema model with roles field
        roles = user.roles

    response_info = {
        "id": user.id,
        "project_id": user.project_id,
        "user_name": user.user_name,
        "roles": roles,
        "is_enabled": user.is_enabled,
        "is_locked": user.is_locked,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "password_expiry_days": user.password_expiry_days,
        "password_changed_at": user.password_changed_at.isoformat(),
        "locked_until": user.locked_until.isoformat()
        if user.locked_until
        else None,
        "description": user.description,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }
    return response_info


def get_role_response(role) -> dict:
    """Get role response.

    Args:
        role: role info

    Returns:
        role response
    """
    response_info = {
        "id": role.id,
        "role_name": role.role_name,
        "permissions": role.permissions,
        "description": role.description,
    }
    return response_info
