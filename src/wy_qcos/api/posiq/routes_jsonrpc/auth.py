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
from datetime import datetime, timezone

from fastapi import Depends, Request
import jwt

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import auth_api_v1
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager
from .dependencies.authentication import (
    auth,
    get_user_manager,
    JWT_AUTH_LIFETIME_SECONDS,
)

logger = logging.getLogger(__name__)
module_name = "AUTH"


@auth_api_v1.method(
    openapi_extra={"no_auth": True}, errors=[jsonrpc_errors.UnauthorizedError]
)
async def login(
    request: Request,
    body: schemas.LoginRequest,
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.LoginResponse:
    """Authenticate user and return JWT token.

    This endpoint validates user credentials and generates a JWT access token
    for authenticated users. The token is used for subsequent API requests.

    Args:
        request: HTTP request object
        body: Login request containing username and password
        user_manager: UserManager dependency for user operations

    Returns:
        LoginResponse containing JWT access token and expiration info

    Raises:
        UnauthorizedError: If credentials are invalid or user is disabled
    """
    func_name = "login"
    logger.info(f"Call {func_name}")

    username = body.username
    password = body.password

    # Validate user exists
    user = user_manager.get_user(username)
    login_failure_type = None
    login_failure_reason = None

    if not user:
        login_failure_type = "unauthorized"
        login_failure_reason = "Invalid username or password"
    else:
        # Validate password
        if not UserManager.check_password(password, user.password_hash):
            login_failure_type = "unauthorized"
            login_failure_reason = "Invalid username or password"

        # Check if user is enabled
        if not user.is_enabled:
            login_failure_type = "forbidden"
            login_failure_reason = "User account is disabled"

        # Check if user is locked
        if user.is_locked:
            login_failure_type = "forbidden"
            login_failure_reason = "User account is locked"

    # Get client IP address and user agent
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", None)

    if login_failure_type:
        # Log failed login attempt
        user_manager.log_login_attempt(
            user_name=username,
            ip_address=client_ip,
            success=False,
            failure_reason=login_failure_reason,
            user_agent=user_agent,
        )
        if login_failure_type == "unauthorized":
            jsonrpc_errors.handle_error_unauthorized(
                module_name,
                func_name,
                (False, [login_failure_reason]),
            )
        elif login_failure_type == "forbidden":
            jsonrpc_errors.handle_error_forbidden(
                module_name,
                func_name,
                (False, [login_failure_reason]),
            )

    # Generate JWT token using SecurityManager
    security_manager = request.app.state._security_manager
    access_token = security_manager.create_access_token({
        "sub": user.user_name,
        "jti": str(uuid.uuid4()),
    })

    # Update last login time
    user.last_login = datetime.now()
    user.failed_login_attempts = 0

    # Log successful login attempt
    user_manager.log_login_attempt(
        user_name=username,
        ip_address=client_ip,
        success=True,
        user_agent=user_agent,
    )

    return schemas.LoginResponse(
        access_token=access_token,
        token_type=_s("bearer"),
        expires_in=JWT_AUTH_LIFETIME_SECONDS,
    )


@auth_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES}, errors=[]
)
def logout(
    request: Request,
    body: schemas.LogoutRequest | None = None,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.LogoutResponse:
    """Logout user and invalidate token.

    This endpoint adds the current token to the blacklist, making it
    invalid for subsequent requests. The client should also remove
    the token from local storage.

    Args:
        request: HTTP request object
        body: Optional logout request
        auth_data: Authentication data from current user
        user_manager: UserManager instance for blacklist operations

    Returns:
        LogoutResponse with confirmation message
    """
    func_name = "logout"
    logger.info(f"Call {func_name}")

    # Extract token from Authorization header and add to blacklist
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix

        # Decode token to get jti and exp
        try:
            payload = jwt.decode(
                token,
                Config.JWT_AUTH_SECRET_KEY,
                algorithms=[Config.JWT_AUTH_ALGORITHM],
                audience=Constant.JWT_AUTH_AUDIENCE,
                options={
                    "verify_exp": False
                },  # Don't verify expiration for blacklist
            )

            token_jti = payload.get("jti")
            token_exp = payload.get("exp")

            if token_jti and token_exp:
                expires_at = datetime.fromtimestamp(
                    token_exp, tz=timezone.utc
                ).replace(tzinfo=None)
                user_manager.add_to_blacklist(token_jti, expires_at)
                logger.info(f"Token {token_jti} added to blacklist")
        except Exception as e:
            logger.warning(f"Failed to blacklist token: {e}")

    # Log the logout event if user is authenticated
    if auth_data and "user_id" in auth_data:
        logger.info(f"User {auth_data['user_id']} logged out")

    return schemas.LogoutResponse(message="Successfully logged out")


@auth_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.UnauthorizedError],
)
async def refresh_token(
    request: Request,
    body: schemas.TokenRefreshRequest | None = None,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.TokenRefreshResponse:
    """Refresh JWT token.

    This endpoint generates a new JWT token for the currently
    authenticated user. The current token must be valid to refresh.

    Args:
        request: HTTP request object
        body: Optional token refresh request
        auth_data: Authentication data from current user
        user_manager: UserManager dependency for user operations

    Returns:
        TokenRefreshResponse with new JWT access token

    Raises:
        UnauthorizedError: If current token is invalid or user not found
    """
    func_name = "refresh_token"
    logger.info(f"Call {func_name}")

    # Require authentication
    if not auth_data or "user_id" not in auth_data:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["Authentication required"]),
        )

    # Get current user
    username = auth_data["user_id"]
    user = user_manager.get_user(username)

    if not user or not user.is_enabled:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["User not found or disabled"]),
        )

    # Generate new JWT token using SecurityManager
    security_manager = request.app.state._security_manager
    access_token = security_manager.create_access_token({
        "sub": username,
        "jti": str(uuid.uuid4()),
    })

    return schemas.TokenRefreshResponse(
        access_token=access_token,
        token_type=_s("bearer"),
        expires_in=JWT_AUTH_LIFETIME_SECONDS,
    )


@auth_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.UnauthorizedError],
)
def get_current_user_info(
    body: schemas.GetUserMgmtStatusRequest | None = None,
    auth_data: dict | None = Depends(auth),
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.GetUserResponse:
    """Get current authenticated user information.

    This endpoint returns the profile information of the currently
    authenticated user based on their JWT token.

    Args:
        body: Optional request body
        auth_data: Authentication data from current user
        user_manager: UserManager dependency for user operations

    Returns:
        GetUserResponse with current user's profile information

    Raises:
        UnauthorizedError: If user is not authenticated
    """
    func_name = "get_current_user_info"
    logger.info(f"Call {func_name}")

    # Require authentication
    if not auth_data or "user_id" not in auth_data:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["Authentication required"]),
        )

    # Get current user
    username = auth_data["user_id"]
    user = user_manager.get_user(username)

    if not user:
        jsonrpc_errors.handle_error_not_found(
            module_name,
            func_name,
            (False, f"User '{username}' not found"),
        )

    # Build response
    response_info = {
        "id": user.id,
        "user_name": user.user_name,
        "roles": user.roles,
        "is_enabled": user.is_enabled,
        "is_locked": user.is_locked,
        "password_expiry_days": user.password_expiry_days,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "password_changed_at": user.password_changed_at.isoformat(),
        "locked_until": user.locked_until.isoformat()
        if user.locked_until
        else None,
        "description": user.description,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }

    return schemas.GetUserResponse.model_validate(response_info)
