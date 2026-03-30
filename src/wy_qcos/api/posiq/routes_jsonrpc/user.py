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
import hashlib
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends

from wy_qcos.api.schemas import user as schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import user_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.config import Config
from .dependencies.authentication import auth

logger = logging.getLogger(__name__)
module_name = "USER"


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


# Database storage for users and roles (in-memory for now)
# TODO(zhaoyi): Move to database
users_db = {}
roles_db = {}
login_logs = []

# Default admin user
DEFAULT_ADMIN_USERNAME = Constant.DEFAULT_ADMIN_USERNAME
DEFAULT_ADMIN_PASSWORD = (
    Config.ADMIN_PASSWORD
    if Config.ADMIN_PASSWORD
    else Constant.DEFAULT_ADMIN_PASSWORD
)


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password: str, password_hash: str) -> bool:
    """Check if password matches hash."""
    return hash_password(password) == password_hash


def is_password_expired(user: schemas.User) -> bool:
    """Check if password has expired."""
    expiry_days = user.password_expiry_days or 0
    expiry_date = user.password_changed_at + timedelta(days=expiry_days)
    return datetime.now() > expiry_date


def log_login_attempt(
    user_name: str, ip_address: str, status: str, user_agent: str | None = None
):
    """Log login attempt."""
    log_entry = schemas.LoginLog(
        user_name=user_name,
        ip_address=ip_address,
        login_status=status,
        user_agent=user_agent,
    )
    login_logs.append(log_entry)
    # Keep only last 1000 logs
    if len(login_logs) > 1000:
        login_logs.pop(0)


def check_user_management_enabled():
    """Check if user management is enabled."""
    if not Config.ENABLE_USER_MGMT:
        jsonrpc_errors.handle_error_forbidden(
            module_name,
            "user_operation",
            (False, "User management is disabled"),
        )


@user_api_v1.method(errors=[])
def get_user_management_status(
    body: schemas.GetUserManagementStatusRequest | None = None,
) -> schemas.GetUserManagementStatusResponse:
    """Get user management status.

    Args:
        body: request body

    Returns:
        User management status response
    """
    func_name = "get_user_management_status"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    _response_info = {
        "enabled": Config.ENABLE_USER_MGMT,
        "password_expiry_days": Config.PASSWORD_EXPIRY_DAYS
        if Config.PASSWORD_EXPIRY_DAYS
        else 0,
        "max_login_attempts": Config.MAX_LOGIN_ATTEMPTS,
        "lockout_duration_minutes": Config.LOCKOUT_DURATION_MINUTES,
    }
    response_info = schemas.GetUserManagementStatusResponse.model_validate(
        _response_info
    )
    return response_info


@user_api_v1.method(
    errors=[jsonrpc_errors.ConflictError, jsonrpc_errors.BadRequestError]
)
def create_user(
    body: schemas.CreateUserRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.CreateUserResponse:
    """Create a new user.

    Args:
        body: user creation request
        auth_data: auth data

    Returns:
        Create user response
    """
    func_name = "create_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

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
    if user_name in users_db:
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (False, f"User '{user_name}' already exists"),
        )

    # Validate roles
    for role_name in roles:
        if role_name not in roles_db:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, f"Role '{role_name}' does not exist"),
            )

    # Create user
    is_enabled = body.is_enabled
    is_locked = body.is_locked
    password_expiry_days = body.password_expiry_days
    if password_expiry_days is None:
        password_expiry_days = Config.PASSWORD_EXPIRY_DAYS

    user = schemas.User(
        user_name=user_name,
        password_hash=hash_password(password),
        roles=roles,
        password_expiry_days=password_expiry_days,
        is_enabled=is_enabled,
        is_locked=is_locked,
        description=description,
    )
    users_db[user_name] = user

    _response_info = get_user_response(user)
    response_info = schemas.CreateUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def get_user(
    body: schemas.GetUserRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetUserResponse:
    """Get user information.

    Args:
        body: get user request
        auth_data: auth data

    Returns:
        Get user response
    """
    func_name = "get_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    user_name = body.user_name

    if user_name not in users_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"User '{user_name}' not found")
        )

    user = users_db[user_name]

    _response_info = get_user_response(user)
    response_info = schemas.GetUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.ConflictError]
)
def update_user(
    body: schemas.UpdateUserRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.UpdateUserResponse:
    """Update user information.

    Args:
        body: user update request
        auth_data: auth data

    Returns:
        Update user response
    """
    func_name = "update_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    user_name = body.user_name
    roles = body.roles
    is_enabled = body.is_enabled
    is_locked = body.is_locked
    password_expiry_days = body.password_expiry_days
    description = body.description

    if user_name not in users_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"User '{user_name}' not found")
        )

    # Validate roles
    if roles:
        for role_name in roles:
            if role_name not in roles_db:
                jsonrpc_errors.handle_error_bad_requests(
                    module_name,
                    func_name,
                    (False, f"Role '{role_name}' does not exist"),
                )

    user = users_db[user_name]
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

    _response_info = get_user_response(user)
    response_info = schemas.UpdateUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def delete_user(
    body: schemas.DeleteUserRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeleteUserResponse:
    """Delete user.

    Args:
        body: delete user request
        auth_data: auth data

    Returns:
        Delete user response
    """
    func_name = "delete_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    user_name = body.user_name

    if user_name not in users_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"User '{user_name}' not found")
        )

    # Don't allow deletion of admin user
    if user_name == DEFAULT_ADMIN_USERNAME:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "Cannot delete admin user")
        )

    del users_db[user_name]

    _response_info = {
        "user_name": user_name,
        "deleted_at": datetime.now().isoformat(),
    }
    response_info = schemas.DeleteUserResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.ConflictError]
)
def create_role(
    body: schemas.CreateRoleRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.CreateRoleResponse:
    """Create a new role.

    Args:
        body: role creation request
        auth_data: auth data

    Returns:
        Create role response
    """
    func_name = "create_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

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
            (False, "Description is too long"),
        )

    if role_name in roles_db:
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (False, f"Role '{role_name}' already exists"),
        )

    role = schemas.Role(
        role_name=role_name, permissions=permissions, description=description
    )
    roles_db[role_name] = role

    _response_info = get_role_response(role)
    response_info = schemas.CreateRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(errors=[jsonrpc_errors.NotFoundError])
def get_role(
    body: schemas.GetRoleRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetRoleResponse:
    """Get role information.

    Args:
        body: get role request
        auth_data: auth data

    Returns:
        Get role response
    """
    func_name = "get_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    role_name = body.role_name

    if role_name not in roles_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Role '{role_name}' not found")
        )

    role = roles_db[role_name]

    _response_info = get_role_response(role)
    response_info = schemas.GetRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.ConflictError]
)
def update_role(
    body: schemas.UpdateRoleRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.UpdateRoleResponse:
    """Update role information.

    Args:
        body: role update request
        auth_data: auth data

    Returns:
        Update role response
    """
    func_name = "update_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    role_name = body.role_name
    permissions = body.permissions
    description = body.description

    if role_name not in roles_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Role '{role_name}' not found")
        )

    role = roles_db[role_name]
    if permissions is not None:
        role.permissions = permissions
    if description is not None:
        role.description = description

    _response_info = get_role_response(role)
    response_info = schemas.UpdateRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.ConflictError]
)
def delete_role(
    body: schemas.DeleteRoleRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeleteRoleResponse:
    """Delete role.

    Args:
        body: delete role request
        auth_data: auth data

    Returns:
        Delete role response
    """
    func_name = "delete_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    role_name = body.role_name

    if role_name not in roles_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Role '{role_name}' not found")
        )

    # Don't allow deletion of admin role
    if role_name == Constant.ROLE_ADMIN:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "Cannot delete admin role")
        )

    # Check if any users are using this role
    users_using_role = [
        user_name
        for user_name, user in users_db.items()
        if role_name in user.roles
    ]
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

    del roles_db[role_name]

    _response_info = {
        "role_name": role_name,
        "deleted_at": datetime.now().isoformat(),
    }
    response_info = schemas.DeleteRoleResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.ConflictError]
)
def lock_user(
    body: schemas.LockUserRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.LockUserResponse:
    """Lock or unlock user.

    Args:
        body: user lock request
        auth_data: auth data

    Returns:
        Lock user response
    """
    func_name = "lock_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    user_name = body.user_name
    action = body.action

    if user_name not in users_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"User '{user_name}' not found")
        )

    # Don't allow locking of admin user
    if user_name == DEFAULT_ADMIN_USERNAME:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "Cannot lock admin user")
        )

    user = users_db[user_name]

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
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.ConflictError]
)
def change_password(
    body: schemas.ChangePasswordRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.ChangePasswordResponse:
    """Change user password.

    Args:
        body: password change request
        auth_data: auth data

    Returns:
        Change password response
    """
    func_name = "change_password"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    user_name = body.user_name
    old_password = body.old_password
    new_password = body.new_password

    if user_name not in users_db:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"User '{user_name}' not found")
        )

    user = users_db[user_name]

    # For non-admin users, validate old password
    if user_name != DEFAULT_ADMIN_USERNAME:
        if not old_password:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                (False, "Old password is required for non-admin users"),
            )
        if not check_password(old_password or "", user.password_hash):
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
    user.password_hash = hash_password(new_password)
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


@user_api_v1.method(errors=[])
def get_login_logs(
    body: schemas.GetLoginLogsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.LoginLogResponse]:
    """Get login logs.

    Args:
        body: get login logs request
        auth_data: auth data

    Returns:
        Dictionary of login logs keyed by timestamp
    """
    func_name = "get_login_logs"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    # Filter logs based on request parameters
    filtered_logs = login_logs.copy()

    if body and body.user_name:
        filtered_logs = [
            log for log in filtered_logs if log.user_name == body.user_name
        ]

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

    # Convert to response format
    response_info = {}
    for log in filtered_logs:
        log_data = {
            "user_name": log.user_name,
            "login_time": log.login_time.isoformat(),
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "success": log.login_status == "success",
            "failure_reason": None
            if log.login_status == "success"
            else log.login_status,
        }
        # Use timestamp as key to ensure uniqueness
        key = log.login_time.isoformat()
        response_info[key] = schemas.LoginLogResponse.model_validate(log_data)

    return response_info


@user_api_v1.method(errors=[])
def get_users(
    body: schemas.GetUsersRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.GetUserResponse]:
    """Get all users.

    Args:
        body: get users request
        auth_data: auth data

    Returns:
        Dictionary of users keyed by user_name
    """
    func_name = "get_users"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    response_info = {}
    for user_name, user in users_db.items():
        user_data = get_user_response(user)
        response_info[user_name] = schemas.GetUserResponse.model_validate(
            user_data
        )

    return response_info


@user_api_v1.method(errors=[])
def get_roles(
    body: schemas.GetRolesRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.GetRoleResponse]:
    """Get all roles.

    Args:
        body: get roles request
        auth_data: auth data

    Returns:
        Dictionary of roles keyed by role name
    """
    func_name = "get_roles"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    check_user_management_enabled()

    response_info = {}
    for role_name, role in roles_db.items():
        role_data = get_role_response(role)
        response_info[role_name] = schemas.GetRoleResponse.model_validate(
            role_data
        )

    return response_info


# Initialize default admin user and roles
def initialize_user_management():
    """Initialize user management with default admin user and roles."""
    global users_db, roles_db

    # Create admin role
    admin_role = schemas.Role(
        role_name=Constant.ROLE_ADMIN,
        permissions=["*"],
        description="Administrator with full permissions",
    )
    roles_db[Constant.ROLE_ADMIN] = admin_role

    # Create user role
    user_role = schemas.Role(
        role_name=Constant.ROLE_USER,
        permissions=["job:submit", "job:get", "job:list"],
        description="Regular user with basic permissions",
    )
    roles_db[Constant.ROLE_USER] = user_role

    # Create default admin user
    admin_user = schemas.User(
        user_name=DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        roles=[Constant.ROLE_ADMIN],
        password_expiry_days=0,
        is_enabled=True,
        description="Administrator with full permissions",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    users_db[DEFAULT_ADMIN_USERNAME] = admin_user

    logger.info("User management initialized with default admin user")


def get_user_response(user) -> dict:
    """Get user response.

    Args:
        user (schemas.User): User model instance

    Returns:
        schemas.GetUserResponse: Formatted user response
    """
    response_info = {
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
        "role_name": role.role_name,
        "permissions": role.permissions,
        "description": role.description,
    }
    return response_info


# Initialize on import
initialize_user_management()
