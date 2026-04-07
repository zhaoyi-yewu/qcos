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
import jwt
from jwt.exceptions import PyJWTError

from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer

from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.user.user_manager import UserManager

logger = logging.getLogger(__name__)


# OAuth2 scheme for JWT token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/{Constant.API_VERSION}/auth/login", auto_error=False
)


# JWT Authentication Configuration
JWT_AUTH_SECRET_KEY = Config.JWT_AUTH_SECRET_KEY
JWT_AUTH_LIFETIME_SECONDS = Config.JWT_AUTH_LIFE_SECONDS
JWT_AUTH_ALGORITHM = Config.JWT_AUTH_ALGORITHM


def get_user_manager(request: Request) -> UserManager:
    """Get user manager from request state.

    This function retrieves the UserManager instance from the FastAPI
    application state. It is used as a dependency in routes that need
    to perform user management operations.

    Args:
        request: FastAPI request object containing app state

    Returns:
        UserManager instance from application state
    """
    return request.app.state._user_manager


def decode_jwt_token(token: str) -> dict | None:
    """Decode JWT token manually.

    This function decodes a JWT token using the SECRET key.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload as dictionary, or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            JWT_AUTH_SECRET_KEY,
            algorithms=[JWT_AUTH_ALGORITHM],
            audience=Constant.JWT_AUTH_AUDIENCE,
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except PyJWTError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


def get_current_user_from_token(
    token: str | None, user_manager: UserManager
) -> user_schemas.User | None:
    """Extract and validate current user from JWT token.

    This function decodes the JWT token and retrieves the corresponding user.
    It also checks if the token has been blacklisted.

    Args:
        token: JWT token string
        user_manager: UserManager instance for user lookup

    Returns:
        User object if token is valid and user exists, None otherwise
    """
    if not token:
        return None

    try:
        # Decode JWT token manually
        user_data = decode_jwt_token(token)

        if not user_data or "sub" not in user_data:
            return None

        # Check if token is blacklisted
        token_jti = user_data.get("jti")
        if token_jti and user_manager.is_blacklisted(token_jti):
            logger.warning(f"Token {token_jti} is blacklisted")
            return None

        # Retrieve user from manager using user ID (UUID) from token
        user = user_manager.get_user_by_id(user_data["sub"])

        if not user or not user.is_enabled:
            return None

        return user
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        return None


async def auth(
    request: Request,
    x_qcos_virtual_instance_id: str | None = Header(
        None, alias="x-qcos-virtual-instance-id"
    ),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Main authentication dependency for API endpoints.

    This function handles authentication for both virtual instance mode
    and user management mode.

    Args:
        request: HTTP request object for path-based permission checking
        x_qcos_virtual_instance_id: Virtual instance ID from header
            (for virt mode)
        user_manager: UserManager instance for user operations

    Returns:
        Authentication data dictionary containing user info and roles

    Raises:
        Various JSON-RPC errors based on authentication failures
    """
    auth_data: dict[str, list[str] | str | None] | None = None

    # Virtual instance authentication
    if Config.ENABLE_VIRT:
        auth_data = auth_virt(x_qcos_virtual_instance_id)
        return auth_data

    # JWT authentication (when user management is enabled)
    if Config.ENABLE_USER_MGMT:
        # Extract token from Authorization header
        access_token = await oauth2_scheme(request)

        # Get current user from token
        current_user = get_current_user_from_token(access_token, user_manager)

        auth_data = None
        if current_user:
            auth_data = {
                "user_id": current_user.user_name,
                "roles": current_user.roles,
                "auth_method": "jwt",
            }

        # Perform permission check
        return auth_user(request, auth_data, user_manager)

    return auth_data


def auth_virt(x_qcos_virtual_instance_id):
    """Authenticate using virtual instance ID.

    This function validates the virtual instance ID header and returns
    authentication data containing device names and instance ID.

    Args:
        x_qcos_virtual_instance_id: Virtual instance ID from request header

    Returns:
        Authentication data dictionary or None for admin users

    Raises:
        JSON-RPC unauthorized error if validation fails
    """
    success = True
    device_names = []
    instance_id = None

    if x_qcos_virtual_instance_id is None:
        success = False

    if success:
        success, err_msg, device_names, instance_id = (
            Library.decrypt_virtual_instance_id(
                x_qcos_virtual_instance_id,
                salt=Config.PASSWORD_SALT,
                encode=True,
            )
        )

    if not success:
        jsonrpc_errors.handle_error_unauthorized(
            "authentication",
            "auth",
            (False, ["Unauthorized access to the instance"]),
        )

    if "all" in device_names and instance_id == "all":  # admin user
        auth_data = None
    else:
        auth_data = {
            "device_names": device_names,
            "instance_id": instance_id,
        }
    return auth_data


def auth_user(
    request: Request, auth_data: dict | None, user_manager: UserManager
) -> dict | None:
    """Check user permissions using Casbin RBAC.

    This function validates that the authenticated user has sufficient
    permissions to access the requested resource based on their roles.

    Args:
        request: HTTP request object containing URL path
        auth_data: Authentication data containing user roles
        user_manager: UserManager instance for permission checking

    Returns:
        Updated auth_data if permissions are sufficient

    Raises:
        UnauthorizedError: If no authentication data provided
        ForbiddenError: If user has no roles or insufficient permissions
    """
    obj = request.url.path
    act = "call"

    # Reject access if no authentication data
    if not auth_data:
        jsonrpc_errors.handle_error_unauthorized(
            "authentication",
            "require_permission",
            (False, ["Authentication required"]),
        )

    # Get user roles
    user_roles = auth_data.get("roles", [])
    if not user_roles:
        jsonrpc_errors.handle_error_forbidden(
            "authentication",
            "require_permission",
            (False, ["No roles assigned to user"]),
        )

    # Check permissions
    has_permission = False
    for role in user_roles:
        if user_manager.perms_check_enforce(role, obj, act):
            has_permission = True
            break

    if not has_permission:
        jsonrpc_errors.handle_error_forbidden(
            "authentication",
            "require_permission",
            (False, [f"Insufficient permissions for {obj}:{act}"]),
        )
    return auth_data
