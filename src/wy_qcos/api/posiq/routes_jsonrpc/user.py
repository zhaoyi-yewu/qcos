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
from typing import Any

from fastapi import Depends, Request

from wy_qcos.api.schemas import user as schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import user_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.config import Config
from wy_qcos.user.user_manager import UserManager
from .dependencies.authentication import auth


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
def get_user_mgmt_status(
    body: schemas.GetUserMgmtStatusRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetUserMgmtStatusResponse:
    """Get user management status.

    Args:
        body: request body
        auth_data: auth data

    Returns:
        User management status response
    """
    func_name = "get_user_mgmt_status"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    _response_info = {
        "enabled": Config.ENABLE_USER_MGMT,
        "password_expiry_days": Config.PASSWORD_EXPIRY_DAYS
        if Config.PASSWORD_EXPIRY_DAYS
        else 0,
        "max_login_attempts": Config.MAX_LOGIN_ATTEMPTS,
        "lockout_duration_minutes": Config.LOCKOUT_DURATION_MINUTES,
    }
    response_info = schemas.GetUserMgmtStatusResponse.model_validate(
        _response_info
    )
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.ConflictError, jsonrpc_errors.BadRequestError],
)
def create_user(
    body: schemas.CreateUserRequest,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.CreateUserResponse:
    """Create a new user.

    Args:
        body: user creation request
        auth_data: auth data
        user_manager: user manager

    Returns:
        Create user response
    """
    func_name = "create_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_name = body.user_name
    password = body.password
    roles = body.roles
    description = body.description

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

    # Check if user already exists
    if user_manager.get_user(user_name):
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (False, f"User '{user_name}' already exists"),
        )

    # Validate roles
    for role_name in roles:
        if not user_manager.get_role(role_name):
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

    # Create user
    is_enabled = body.is_enabled
    is_locked = body.is_locked
    password_expiry_days = body.password_expiry_days
    if password_expiry_days is None:
        password_expiry_days = Config.PASSWORD_EXPIRY_DAYS

    user = None
    try:
        user = user_manager.create_user(
            user_name,
            password,
            roles,
            is_enabled,
            is_locked,
            password_expiry_days,
            description,
        )
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                str(e),
            ),
        )

    _response_info = get_user_response(user)
    response_info = schemas.CreateUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_user(
    body: schemas.GetUserRequest,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.GetUserResponse:
    """Get user information by ID.

    Args:
        body: get user request (contains user_id)
        auth_data: auth data
        user_manager: user manager

    Returns:
        Get user response
    """
    func_name = "get_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = body.user_id

    user = user_manager.get_user_by_id(user_id)
    if not user:
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
    user_manager: UserManager = Depends(get_user_manager),
) -> dict[str, schemas.GetUserResponse]:
    """Get all users.

    Args:
        body: get users request
        auth_data: auth data
        user_manager: user manager

    Returns:
        Dictionary of users keyed by user_name
    """
    func_name = "get_users"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    response_info = {}
    for user_name, user in user_manager.get_users().items():
        user_data = get_user_response(user)
        response_info[user_name] = schemas.GetUserResponse.model_validate(
            user_data
        )

    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.BadRequestError],
)
def update_user(
    body: schemas.UpdateUserRequest,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.UpdateUserResponse:
    """Update user information by ID.

    Args:
        body: user update request (contains user_id)
        auth_data: auth data
        user_manager: user manager

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

    user = user_manager.get_user_by_id(user_id)

    if not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User with ID '{user_id}' not found"),
        )

    user_name = user.user_name

    # Validate roles
    existing_roles = user_manager.get_roles()
    if roles:
        for role_name in roles:
            if role_name not in existing_roles:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    (False, f"Role '{role_name}' does not exist"),
                )

    user = None
    try:
        user = user_manager.update_user(
            user_name,
            roles,
            is_enabled,
            is_locked,
            password_expiry_days,
            description,
        )
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                str(e),
            ),
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
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.DeleteUserResponse:
    """Delete user by ID.

    Args:
        body: delete user request (contains user_id)
        auth_data: auth data
        user_manager: user manager

    Returns:
        Delete user response
    """
    func_name = "delete_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = body.user_id

    user = user_manager.get_user_by_id(user_id)
    if not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User with ID '{user_id}' not found"),
        )

    user_name = user.user_name

    # Don't allow deletion of admin user
    if user_name == Constant.DEFAULT_ADMIN_USERNAME:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "Cannot delete admin user")
        )

    try:
        user_manager.delete_user(user_name)
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                str(e),
            ),
        )

    _response_info = {
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
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.CreateRoleResponse:
    """Create a new role.

    Args:
        body: role creation request
        auth_data: auth data
        user_manager: user manager

    Returns:
        Create role response
    """
    func_name = "create_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_name = body.role_name
    permissions = body.permissions
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

    role = user_manager.get_role(role_name)
    if role:
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (False, f"Role '{role_name}' already exists"),
        )

    if permissions:
        invalid_permissions = []
        for permission in permissions:
            if permission not in user_manager.get_default_policies(
                role=Constant.ROLE_USER, simple=True
            ):
                invalid_permissions.append(permission)
        if invalid_permissions:
            err_msgs = f"Invalid permission: {', '.join(invalid_permissions)}"
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, err_msgs),
            )

    role = None
    try:
        role = user_manager.create_role(role_name, permissions, description)
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                str(e),
            ),
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
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.GetRoleResponse:
    """Get role information by ID.

    Args:
        body: get role request (contains role_id)
        auth_data: auth data
        user_manager: user manager

    Returns:
        Get role response
    """
    func_name = "get_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = body.role_id
    role = user_manager.get_roles().get(role_id)
    if not role:
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
    user_manager: UserManager = Depends(get_user_manager),
) -> dict[str, schemas.GetRoleResponse]:
    """Get all roles.

    Args:
        body: get roles request
        auth_data: auth data
        user_manager: user manager

    Returns:
        Dictionary of roles keyed by role name
    """
    func_name = "get_roles"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    response_info = {}
    for role_name, role in user_manager.get_roles().items():
        role_data = get_role_response(role)
        response_info[role_name] = schemas.GetRoleResponse.model_validate(
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
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.UpdateRoleResponse:
    """Update role information by ID.

    Args:
        body: role update request (contains role_id)
        auth_data: auth data
        user_manager: user manager

    Returns:
        Update role response
    """
    func_name = "update_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = body.role_id
    permissions = body.permissions
    description = body.description

    role = user_manager.get_roles().get(role_id)
    if not role:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"Role with ID '{role_id}' not found"),
        )

    role_name = role.role_name

    # validate permissions
    if permissions:
        invalid_permissions = []
        for permission in permissions:
            if permission not in user_manager.get_default_policies(
                role=Constant.ROLE_USER, simple=True
            ):
                invalid_permissions.append(permission)
        if invalid_permissions:
            err_msgs = f"Invalid permission: {', '.join(invalid_permissions)}"
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, err_msgs)
            )

    role = None
    try:
        role = user_manager.update_role(role_name, permissions, description)
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                str(e),
            ),
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
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.DeleteRoleResponse:
    """Delete role by ID.

    Args:
        body: delete role request (contains role_id)
        auth_data: auth data
        user_manager: user manager

    Returns:
        Delete role response
    """
    func_name = "delete_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = body.role_id

    role = user_manager.get_roles().get(role_id)
    if not role:
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
    users_using_role = user_manager.find_users_by_role(role_name)
    if users_using_role:
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (
                False,
                f"Cannot delete role '{role_name}' because it is being "
                f"used by users: {', '.join(users_using_role)}",
            ),
        )

    try:
        user_manager.delete_role(role_name)
    except Exception as e:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (
                False,
                str(e),
            ),
        )

    _response_info = {
        "role_name": role_name,
        "deleted_at": datetime.now().isoformat(),
    }
    response_info = schemas.DeleteRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def lock_user(
    body: schemas.LockUserRequest,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.LockUserResponse:
    """Lock or unlock user.

    Args:
        body: user lock request
        auth_data: auth data
        user_manager: user manager

    Returns:
        Lock user response
    """
    func_name = "lock_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_name = body.user_name
    action = body.action

    user = user_manager.get_user(user_name)
    if not user:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"User '{user_name}' not found")
        )

    # Don't allow locking of admin user
    if user_name == Constant.DEFAULT_ADMIN_USERNAME:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "Cannot lock admin user")
        )

    if action == "lock":
        user.is_locked = True
        user.locked_until = datetime.now() + timedelta(
            minutes=Config.LOCKOUT_DURATION_MINUTES
        )
        message = f"User '{user_name}' has been locked"
    elif action == "unlock":
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        message = f"User '{user_name}' has been unlocked"
    else:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, "Invalid action. Use 'lock' or 'unlock'"),
        )

    _response_info = {
        "user_name": user_name,
        "is_locked": user.is_locked,
        "locked_until": user.locked_until.isoformat()
        if user.locked_until
        else None,
        "message": message,
    }
    response_info = schemas.LockUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def change_password(
    body: schemas.ChangePasswordRequest,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.ChangePasswordResponse:
    """Change user password by ID.

    Args:
        body: password change request (contains user_id)
        auth_data: auth data
        user_manager: user manager

    Returns:
        Change password response
    """
    func_name = "change_password"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = body.user_id
    old_password = body.old_password
    new_password = body.new_password

    user = user_manager.get_user_by_id(user_id)
    if not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User with ID '{user_id}' not found"),
        )

    user_name = user.user_name

    # For non-admin users, validate old password
    if user_name != Constant.DEFAULT_ADMIN_USERNAME:
        if not old_password:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, "Old password is required for non-admin users"),
            )
        if not UserManager.check_password(
            old_password or "", user.password_hash
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

    # Update password
    user.password_hash = UserManager.hash_password(new_password)
    user.password_changed_at = datetime.now()
    user.failed_login_attempts = 0
    user.is_locked = False
    user.locked_until = None

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
    errors=[jsonrpc_errors.NotFoundError],
)
def get_login_logs(
    body: schemas.GetLoginLogsRequest | None = None,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> list[schemas.LoginLogResponse]:
    """Get login logs by user ID.

    Args:
        body: get login logs request (contains user_id, limit, offset)
        auth_data: auth data
        user_manager: user manager

    Returns:
        List of login logs in descending order by login_time
    """
    func_name = "get_login_logs"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    # Filter logs based on request parameters
    filtered_logs = user_manager.get_login_logs().copy()

    if body and body.user_id:
        # Get user name from user_id
        user = user_manager.get_user_by_id(body.user_id)
        if user:
            filtered_logs = [
                log for log in filtered_logs if log.user_name == user.user_name
            ]
        else:
            # User not found, raise error
            jsonrpc_errors.handle_error_not_found(
                module_name,
                func_name,
                (False, f"User with ID '{body.user_id}' not found"),
            )

    if body and body.start_time:
        start_dt = datetime.fromisoformat(body.start_time)
        filtered_logs = [
            log for log in filtered_logs if log.login_time >= start_dt
        ]

    if body and body.end_time:
        end_dt = datetime.fromisoformat(body.end_time)
        filtered_logs = [
            log for log in filtered_logs if log.login_time <= end_dt
        ]

    # Sort by login_time in descending order (newest first)
    filtered_logs.sort(key=lambda x: x.login_time, reverse=True)

    # Apply pagination (offset and limit)
    if body:
        offset = body.offset if body.offset is not None else 0
        limit = body.limit if body.limit is not None else 100
        filtered_logs = filtered_logs[offset : offset + limit]

    # Convert to response format
    response_info = []
    for log in filtered_logs:
        log_data = {
            "user_name": log.user_name,
            "login_time": log.login_time.isoformat(),
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "success": log.success,
            "failure_reason": log.failure_reason,
        }
        response_info.append(schemas.LoginLogResponse.model_validate(log_data))

    return response_info


def get_user_response(user) -> dict:
    """Get user response.

    Args:
        user (schemas.User): User model instance

    Returns:
        schemas.GetUserResponse: Formatted user response
    """
    response_info = {
        "id": user.id,
        "user_name": user.user_name,
        "roles": user.roles,
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
