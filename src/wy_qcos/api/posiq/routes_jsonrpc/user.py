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
import uuid
from datetime import datetime
from typing import Any, Literal, cast

from fastapi import Depends, Request

from wy_qcos.api.schemas import user as schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import user_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.config import Config
from wy_qcos.common.library import Library
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
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[],
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
        "auth_mode": Config.DEFAULT.AUTH_MODE,
        "password_expiry_days": Config.USERS.PASSWORD_EXPIRY_DAYS
        if Config.USERS.PASSWORD_EXPIRY_DAYS
        else 0,
        "max_login_attempts": Config.USERS.MAX_LOGIN_ATTEMPTS,
        "lockout_duration_minutes": Config.USERS.LOCKOUT_DURATION_MINUTES,
    }
    response_info = schemas.GetUserMgmtResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
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
    Config.DEFAULT.AUTH_MODE = cast(
        Literal["no", "jwt", "virtual_instance"], auth_mode
    )
    logger.info(f"Updated AUTH_MODE to '{auth_mode}'")

    _response_info = {
        "auth_mode": Config.DEFAULT.AUTH_MODE,
        "message": f"Authentication mode updated to '{auth_mode}'",
    }
    response_info = schemas.SetUserMgmtResponse.model_validate(_response_info)
    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.ConflictError, jsonrpc_errors.BadRequestError],
)
def create_user(
    body: schemas.CreateUserRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.CreateUserResponse:
    """Create a new user.

    Args:
        body: user creation request
        request: request object
        auth_data: auth data

    Returns:
        Create user response
    """
    func_name = "create_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_name = body.user_name
    password = body.password

    # validate user_name
    success, err_msg = Library.validate_name(user_name)
    if not success:
        jsonrpc_errors.handle_error_bad_requests(
            "USER",
            "create_user",
            (False, err_msg),
        )
    roles = body.roles
    description = body.description

    # Ensure project_id is set to proper UUID type
    # If None, convert to DEFAULT_PROJECT_ID as UUID object
    if body.project_id is None:
        body.project_id = uuid.UUID(Constant.DEFAULT_PROJECT_ID)

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Create user using UserManager (which handles all validations
    # and permission reloading)
    user = None
    try:
        user = user_manager.create_user(
            project_id=str(body.project_id),
            user_name=user_name,
            password=password,
            roles=roles,
            is_enabled=body.is_enabled,
            is_locked=body.is_locked,
            password_expiry_days=body.password_expiry_days,
            description=description,
            user_id=str(body.user_id) if body.user_id else None,
        )
    except ValueError as e:
        # UserManager validation errors
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
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
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_user(
    body: schemas.GetUserRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetUserResponse:
    """Get user information by ID.

    Args:
        body: get user request (contains user_id)
        request: request object
        auth_data: auth data

    Returns:
        Get user response
    """
    func_name = "get_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = str(body.user_id)

    # Authentication: match user id
    auth_match_user_id(user_id, auth_data, allow_admin=True)

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Get user using UserManager
    try:
        user = user_manager.get_user_by_id(user_id)
        if not user:
            jsonrpc_errors.handle_error_not_found(
                module_name,
                func_name,
                (False, f"User with ID '{user_id}' not found"),
            )

        _response_info = get_user_response(user)
        response_info = schemas.GetUserResponse.model_validate(_response_info)
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error getting user {user_id}: {error_msg}")
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, error_msg)
        )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error getting user {user_id}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[],
)
def get_users(
    request: Request,
    body: schemas.GetUsersRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.GetUserResponse]:
    """Get users with optional filtering.

    Args:
        request: request object
        body: get users request with optional filter dict
        auth_data: auth data

    Returns:
        Dictionary of users keyed by user_id

    Filter example:
        {"user_name": "admin"} - filter by user_name
    """
    func_name = "get_users"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Extract filter conditions from request body
    filter_conditions = None
    if body:
        filter_conditions = body.filters

    # Get users from UserManager with optional filtering
    users_dict = user_manager.get_users(filters=filter_conditions)
    users = list(users_dict.values()) if users_dict else []

    # Build response
    response_info = {}
    for user in users:
        user_data = get_user_response(user)
        response_info[str(user.id)] = schemas.GetUserResponse.model_validate(
            user_data
        )

    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.BadRequestError],
)
def update_user(
    body: schemas.UpdateUserRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.UpdateUserResponse:
    """Update user information by ID.

    Args:
        body: user update request (contains user_id)
        request: request object
        auth_data: auth data

    Returns:
        Update user response
    """
    func_name = "update_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = str(body.user_id)
    roles = body.roles
    is_enabled = body.is_enabled
    is_locked = body.is_locked
    password_expiry_days = body.password_expiry_days
    description = body.description

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Update user using UserManager (which handles all validations,
    # unlocking, permission reloading, and database updates)
    user = None
    try:
        user = user_manager.update_user(
            user_id=user_id,
            roles=roles,
            is_enabled=is_enabled,
            is_locked=is_locked,
            password_expiry_days=password_expiry_days,
            description=description,
        )
    except ValueError as e:
        # UserManager validation errors
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            (False, str(e)),
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
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def delete_user(
    body: schemas.DeleteUserRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.DeleteUserResponse:
    """Delete user by ID.

    Args:
        body: delete user request (contains user_id and optional force flag)
        request: FastAPI request object
        auth_data: auth data

    Returns:
        Delete user response

    Note:
        Non-force delete: fails if user has associated jobs
        Force delete: cascades deletion of jobs (from Prefect and database)
    """
    func_name = "delete_user"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = str(body.user_id)
    force = body.force

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Delete user using UserManager
    try:
        deleted_user = user_manager.delete_user(user_id=user_id, force=force)
        user_name = deleted_user.user_name
        user_project_id = deleted_user.project_id

        _response_info = {
            "id": user_id,
            "project_id": user_project_id,
            "user_name": user_name,
            "deleted_at": datetime.now().isoformat(),
        }
        response_info = schemas.DeleteUserResponse.model_validate(
            _response_info
        )
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error deleting user {user_id}: {error_msg}")
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, error_msg)
        )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error deleting user {user_id}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
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
) -> schemas.CreateRoleResponse:
    """Create a new role.

    Args:
        body: role creation request
        request: request object
        auth_data: auth data

    Returns:
        Create role response
    """
    func_name = "create_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_name = body.role_name
    permissions = body.permissions

    # validate role_name
    success, err_msg = Library.validate_name(role_name)
    if not success:
        jsonrpc_errors.handle_error_bad_requests(
            "USER",
            "create_role",
            (False, err_msg),
        )
    description = body.description

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Create role using UserManager
    try:
        role = user_manager.create_role(
            role_name=role_name,
            permissions=permissions,
            description=description,
        )

        _response_info = get_role_response(role)
        response_info = schemas.CreateRoleResponse.model_validate(
            _response_info
        )
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error creating role {role_name}: {error_msg}")
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, error_msg)
        )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error creating role {role_name}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError],
)
def get_role(
    body: schemas.GetRoleRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetRoleResponse:
    """Get role information by ID.

    Args:
        body: get role request (contains role_id)
        request: FastAPI request object
        auth_data: auth data

    Returns:
        Get role response
    """
    func_name = "get_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = str(body.role_id)

    # Get user manager from request state
    user_manager = get_user_manager(request)

    try:
        # Get role using UserManager
        role = user_manager.get_role_by_id(role_id)
        if not role:
            jsonrpc_errors.handle_error_not_found(
                module_name,
                func_name,
                (False, f"Role with ID '{role_id}' not found"),
            )

        _response_info = get_role_response(role)
        response_info = schemas.GetRoleResponse.model_validate(_response_info)
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error getting role {role_id}: {error_msg}")
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, error_msg)
        )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error getting role {role_id}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[],
)
def get_roles(
    request: Request,
    body: schemas.GetRolesRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict[str, schemas.GetRoleResponse]:
    """Get roles with optional filtering.

    Args:
        request: request object
        body: get roles request with optional filter dict
        auth_data: auth data

    Returns:
        Dictionary of roles keyed by role ID

    Filter example:
        {"role_name": "admin"} - filter by role_name
    """
    func_name = "get_roles"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Extract filter conditions from request body
    filter_conditions = None
    if body:
        filter_conditions = body.filters

    # Get roles from UserManager with optional filtering
    roles_dict = user_manager.get_roles(filters=filter_conditions)
    roles = list(roles_dict.values()) if roles_dict else []

    # Build response
    response_info = {}
    for role in roles:
        role_data = get_role_response(role)
        response_info[str(role.id)] = schemas.GetRoleResponse.model_validate(
            role_data
        )

    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
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
) -> schemas.UpdateRoleResponse:
    """Update role information by ID.

    Args:
        body: role update request (contains role_id)
        request: request object
        auth_data: auth data

    Returns:
        Update role response
    """
    func_name = "update_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = str(body.role_id)
    permissions = body.permissions
    description = body.description

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Update role using UserManager
    try:
        role = user_manager.update_role(
            role_id=role_id,
            permissions=permissions,
            description=description,
        )

        _response_info = get_role_response(role)
        response_info = schemas.UpdateRoleResponse.model_validate(
            _response_info
        )
        return response_info
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error updating role {role_id}: {error_msg}")
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, error_msg)
        )
        raise
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error updating role {role_id}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
        raise


@user_api_v1.method(
    tags=[module_name.lower()],
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
) -> schemas.DeleteRoleResponse:
    """Delete role by ID.

    Args:
        body: delete role request (contains role_id)
        request: request object
        auth_data: auth data

    Returns:
        Delete role response
    """
    func_name = "delete_role"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    role_id = str(body.role_id)

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Delete role using UserManager
    try:
        role = user_manager.delete_role(role_id=role_id)
        _response_info = {
            "role_name": role.role_name,
            "deleted_at": datetime.now().isoformat(),
        }
        response_info = schemas.DeleteRoleResponse.model_validate(
            _response_info
        )
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error deleting role {role_id}: {error_msg}")
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, error_msg)
        )
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error deleting role {role_id}: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    return response_info


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.NotFoundError,
        jsonrpc_errors.ConflictError,
    ],
)
def change_password(
    body: schemas.ChangePasswordRequest,
    request: Request,
    auth_data: dict | None = Depends(auth),
) -> schemas.ChangePasswordResponse:
    """Change user password by ID.

    Args:
        body: password change request (contains user_id)
        request: request object
        auth_data: auth data

    Returns:
        Change password response
    """
    func_name = "change_password"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    user_id = str(body.user_id)
    old_password = body.old_password
    new_password = body.new_password

    # Authentication: match user id
    auth_match_user_id(user_id, auth_data, allow_admin=True)

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Change password using UserManager
    try:
        user = user_manager.change_password(
            user_id=user_id,
            old_password=old_password,
            new_password=new_password,
        )
        _response_info = {
            "user_name": user.user_name,
            "password_changed_at": user.password_changed_at.isoformat(),
            "message": "Password changed successfully",
        }
        response_info = schemas.ChangePasswordResponse.model_validate(
            _response_info
        )
        return response_info
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(
            f"Error changing password for user {user_id}: {error_msg}"
        )
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, error_msg)
        )
        raise
    except Exception as e:
        # Handle other unexpected errors
        logger.error(
            f"Unexpected error changing password for user {user_id}: {str(e)}"
        )
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
        raise


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.BadRequestError],
)
def get_login_logs(
    request: Request,
    body: schemas.GetLoginLogsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> list[schemas.LoginLogResponse]:
    """Get login logs by user ID or user_name.

    Args:
        request: request object
        body: get login logs request (contains user_id, user_name,
              limit, offset)
        auth_data: auth data

    Returns:
        List of login logs in descending order by login_time

    Note:
        user_id and user_name are mutually exclusive. Only one can be provided.
        If both are None, all login logs will be returned.
        Use limit=-1 to retrieve all logs without any limit restriction.
    """
    func_name = "get_login_logs"
    logger.info(f"Call {func_name}: {_mask_hidden_fields(body)}")

    # Parse parameters
    user_id = None
    user_name = None
    start_time = None
    end_time = None
    limit = 100
    offset = 0

    if body:
        if body.user_id:
            user_id = str(body.user_id)
        if body.user_name:
            user_name = body.user_name
        if body.start_time:
            start_time = datetime.fromisoformat(body.start_time)
        if body.end_time:
            end_time = datetime.fromisoformat(body.end_time)
        if body.limit is not None:
            limit = body.limit
        if body.offset is not None:
            offset = body.offset

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Get login logs using UserManager
    try:
        logs_data = user_manager.get_login_logs(
            user_id=user_id,
            user_name=user_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        # Convert to response format
        response_info = [
            schemas.LoginLogResponse.model_validate(log_data)
            for log_data in logs_data
        ]
        return response_info
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error getting login logs: {error_msg}")
        # Check if error is due to user not found
        if "not found" in error_msg.lower():
            jsonrpc_errors.handle_error_not_found(
                module_name, func_name, (False, error_msg)
            )
        else:
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, error_msg)
            )
        raise
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error getting login logs: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
        raise


@user_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.BadRequestError],
)
def clear_login_logs(
    request: Request,
    body: schemas.ClearLoginLogsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> dict:
    """Clear login logs (all or for a specific user).

    Args:
        request: request object
        body: clear login logs request (contains user_id, user_name)
        auth_data: auth data

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
        if body.user_id:
            user_id = str(body.user_id)
        if body.user_name:
            user_name = body.user_name

    # Get user manager from request state
    user_manager = get_user_manager(request)

    # Clear login logs using UserManager
    try:
        result = user_manager.clear_login_logs(
            user_id=user_id, user_name=user_name
        )
        logger.info(f"Cleared {result['count']} login log(s)")
        return result
    except ValueError as e:
        # UserManager validation errors
        error_msg = str(e)
        logger.warning(f"Error clearing login logs: {error_msg}")
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, error_msg)
        )
        raise
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error clearing login logs: {str(e)}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
        raise


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
        "id": str(user.id) if isinstance(user.id, uuid.UUID) else user.id,
        "project_id": str(user.project_id)
        if isinstance(user.project_id, uuid.UUID)
        else user.project_id,
        "user_name": user.user_name,
        "roles": roles,
        "is_enabled": user.is_enabled
        if user.is_enabled is not None
        else False,
        "is_locked": user.is_locked if user.is_locked is not None else False,
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
        "id": str(role.id) if isinstance(role.id, uuid.UUID) else role.id,
        "role_name": role.role_name,
        "permissions": role.permissions,
        "description": role.description,
    }
    return response_info
