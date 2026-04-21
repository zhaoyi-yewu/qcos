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
from datetime import datetime, timedelta

from fastapi import Depends, Request
import jwt

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import auth_api_v1
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.user.user_manager import UserManager
from wy_qcos.db.models.user import User as UserModel
from wy_qcos.db.repositories.user import UserRepository
from wy_qcos.db.utils.db_utils import get_repository
from .dependencies.authentication import (
    auth,
    get_user_manager,
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
    users_repo: UserRepository = Depends(get_repository(UserRepository)),
) -> schemas.LoginResponse:
    """Authenticate user and return JWT token.

    This endpoint validates user credentials and generates a JWT access token
    for authenticated users. The token is used for subsequent API requests.

    Args:
        request: HTTP request object
        body: Login request containing username and password
        user_manager: UserManager dependency for user operations
        users_repo: User repository dependency for database operations

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
    is_user_locked_before_password_check = (
        False  # Track if user was locked before password validation
    )

    if not user:
        login_failure_type = "unauthorized"
        login_failure_reason = "Invalid username or password"
    else:
        # Check if user is enabled
        if not user.is_enabled:
            login_failure_type = "forbidden"
            login_failure_reason = "User account is disabled"

        # Check if user is locked
        elif user.is_locked:
            # Check if lock has expired
            if user.locked_until and datetime.now() >= user.locked_until:
                # Auto-unlock the user
                user.is_locked = False
                user.locked_until = None
                user.failed_login_attempts = (
                    0  # Reset failed attempts counter when unlocking
                )
                logger.info(
                    f"User '{username}' auto-unlocked - lockout period "
                    f"({Config.LOCKOUT_DURATION_MINUTES} minutes) has expired"
                )

                # Persist auto-unlock to database immediately
                try:
                    success, error, updated_user = users_repo.update(
                        UserModel,
                        user.id,
                        is_locked=False,
                        locked_until=None,
                        failed_login_attempts=0,
                    )
                    if success:
                        logger.info(
                            f"User '{username}' auto-unlock state "
                            "persisted to database"
                        )
                        # Update in-memory user object if returned
                        if updated_user:
                            user = updated_user
                    else:
                        logger.warning(
                            f"Failed to persist auto-unlock state to "
                            f"database: {error}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to persist auto-unlock state to database: {e}"
                    )

                # Continue with password validation
                # (don't set failure_type, will fall through to checks)
                # Note: Intentionally not returning here to allow
                # password validation below
                # Reset login_failure_type to None so checks proceed
                login_failure_type = None
                login_failure_reason = None
            else:
                # User is still locked - but we still need password check
                # Continue to password validation to check if password is
                # also incorrect. This allows us to track and increment
                # failed_login_attempts for attempts during lockout
                is_user_locked_before_password_check = (
                    True  # Mark that user was locked
                )
                logger.debug(
                    f"User '{username}' is locked until "
                    f"{user.locked_until}. Proceeding to password "
                    "validation to track attempts."
                )
                # Don't set login_failure_type yet
                # let password validation continue below
                # We'll return locked error after password check

        # Check if password has expired (skip if locked)
        if (
            not login_failure_type
            and user
            and UserManager.is_password_expired(user)
        ):
            login_failure_type = "forbidden"
            login_failure_reason = (
                "Password has expired. Please change your password"
            )

        # Validate password (only if no other failure detected)
        if not login_failure_type and not UserManager.check_password(
            password, user.hashed_password
        ):
            # Password is incorrect
            logger.debug(
                f"Password validation failed for user '{username}'. "
                f"is_user_locked_before_password_check="
                f"{is_user_locked_before_password_check}, "
                f"current_failed_attempts={user.failed_login_attempts}, "
                f"is_locked={user.is_locked}"
            )
            if is_user_locked_before_password_check:
                # User was already locked, so continue to count this attempt
                # We'll increment the counter and then return locked error
                user.failed_login_attempts = (
                    user.failed_login_attempts or 0
                ) + 1
                logger.debug(
                    f"Locked user '{username}' attempted login with "
                    "wrong password. Incremented from "
                    f"{user.failed_login_attempts - 1} to "
                    f"{user.failed_login_attempts}"
                )
                # Persist the updated counter
                try:
                    success, error, updated_user = users_repo.update(
                        UserModel,
                        user.id,
                        failed_login_attempts=user.failed_login_attempts,
                    )
                    if success:
                        logger.debug(
                            f"Updated failed_login_attempts to "
                            f"{user.failed_login_attempts} for locked "
                            f"user '{username}'"
                        )
                    else:
                        logger.warning(
                            f"Failed to update failed_login_attempts "
                            f"for locked user: {error}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to update failed_login_attempts for "
                        f"locked user: {e}"
                    )
                # Set login_failure_type to "forbidden"
                # to indicate locked status
                login_failure_type = "forbidden"
                if user.locked_until is not None:
                    time_delta = (
                        user.locked_until - datetime.now()
                    ).total_seconds()
                    remaining_minutes = int(time_delta / 60)
                else:
                    remaining_minutes = 0
                login_failure_reason = (
                    f"User account is locked. Please try again in "
                    f"{remaining_minutes} minutes"
                )
            else:
                # User was not locked before, so this is a regular
                # password failure. Make sure we're not incrementing
                # from a stale value
                logger.debug(
                    f"Regular password failure for user '{username}'. "
                    f"Current failed_login_attempts: "
                    f"{user.failed_login_attempts}"
                )
                login_failure_type = "unauthorized"
                login_failure_reason = "Invalid username or password"
        elif not login_failure_type and UserManager.check_password(
            password, user.hashed_password
        ):
            # Password is correct, but check if user was locked before
            # password validation
            if is_user_locked_before_password_check:
                # User was locked before, deny login even though
                # password is correct
                logger.warning(
                    f"User '{username}' attempted login with correct "
                    f"password while locked. Access denied."
                )
                login_failure_type = "forbidden"
                if user.locked_until is not None:
                    time_delta = (
                        user.locked_until - datetime.now()
                    ).total_seconds()
                    remaining_minutes = int(time_delta / 60)
                else:
                    remaining_minutes = 0
                login_failure_reason = (
                    f"User account is locked. Please try again in "
                    f"{remaining_minutes} minutes"
                )

    # Get client IP address and user agent
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", None)

    if login_failure_type:
        # Log failed login attempt and handle account lockout
        if user and login_failure_type == "unauthorized":
            # Only increment failed attempts for password
            # authentication failures
            # Not for disabled, locked, or expired password cases
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            # Check if max login attempts exceeded
            if user.failed_login_attempts >= Config.MAX_LOGIN_ATTEMPTS:
                # Lock the user account
                user.is_locked = True
                user.locked_until = datetime.now() + timedelta(
                    minutes=Config.LOCKOUT_DURATION_MINUTES
                )
                login_failure_reason = (
                    f"Account locked due to "
                    f"{user.failed_login_attempts} failed login attempts. "
                    f"Please try again after "
                    f"{Config.LOCKOUT_DURATION_MINUTES} minutes."
                )
                logger.warning(
                    f"User '{username}' exceeded max login attempts "
                    f"({user.failed_login_attempts}). Account will be "
                    f"locked until {user.locked_until}."
                )
                # Update database with locked status
                try:
                    success, error, updated_user = users_repo.update(
                        UserModel,
                        user.id,
                        is_locked=True,
                        locked_until=user.locked_until,
                    )
                    if success:
                        logger.info(
                            f"User '{username}' locked in database until "
                            f"{user.locked_until}"
                        )
                    else:
                        logger.error(
                            f"Failed to lock user account in database: {error}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to lock user account in database: {e}"
                    )
            else:
                # Still within limit - update failed attempts in database
                logger.debug(
                    f"Failed login attempt "
                    f"#{user.failed_login_attempts} for "
                    f"user '{username}' - limit is "
                    f"{Config.MAX_LOGIN_ATTEMPTS}"
                )
                # Update failed attempts count in database
                try:
                    # Create a minimal update to persist failed_login_attempts
                    # We need to update through the update method
                    success, error, updated_user = users_repo.update(
                        UserModel,
                        user.id,
                        failed_login_attempts=user.failed_login_attempts,
                    )
                    if success:
                        logger.debug(
                            f"Updated failed_login_attempts to "
                            f"{user.failed_login_attempts} for "
                            f"user '{username}'"
                        )
                    else:
                        logger.warning(
                            f"Failed to update "
                            f"failed_login_attempts in database: {error}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to update "
                        f"failed_login_attempts in database: {e}"
                    )
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

    # Generate JWT tokens using SecurityManager
    security_manager = request.app.state._security_manager

    # Generate access token
    access_token = security_manager.create_access_token({
        "sub": user.user_name,
        "jti": str(uuid.uuid4()),
        "aud": Constant.JWT_AUTH_AUDIENCE,
    })

    # Generate refresh token
    refresh_token = security_manager.create_refresh_token({
        "sub": user.user_name,
        "jti": str(uuid.uuid4()),
        "aud": Constant.JWT_AUTH_AUDIENCE,
    })

    # Update last login time and reset failed attempts on successful login
    user.last_login = datetime.now()
    user.failed_login_attempts = 0

    # Persist successful login to database
    try:
        # Update login info using the repo's update method
        success, error, updated_user = users_repo.update(
            UserModel,
            user.id,
            failed_login_attempts=0,
            last_login=user.last_login,
            is_locked=False,
            locked_until=None,
        )
        if success:
            logger.debug(
                f"Updated user login info for user '{username}' on "
                f"successful login"
            )
        else:
            logger.warning(
                f"Failed to update user login info in database: {error}"
            )
    except Exception as e:
        logger.warning(f"Failed to update user login info in database: {e}")

    # Log successful login attempt
    user_manager.log_login_attempt(
        user_name=username,
        ip_address=client_ip,
        success=True,
        user_agent=user_agent,
    )

    return schemas.LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=_s("bearer"),
        expires_in=Config.ACCESS_TOKEN_EXPIRE_MINUTES
        * 60,  # Convert minutes to seconds
        refresh_expires_in=Config.REFRESH_TOKEN_EXPIRE_DAYS
        * 86400,  # Convert days to seconds
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

            logger.debug(f"Token payload - jti: {token_jti}, exp: {token_exp}")

            if token_jti and token_exp:
                # Convert Unix timestamp to datetime (local time - UTC+8)
                # Note: token_exp is Unix timestamp in seconds
                expires_at = datetime.fromtimestamp(token_exp)

                logger.debug(
                    f"Token exp timestamp: {token_exp}, "
                    f"expires_at (local): {expires_at}"
                )

                # Add to blacklist
                user_manager.add_to_blacklist(token_jti, expires_at)
                logger.info(
                    f"Token {token_jti} added to blacklist, "
                    f"expires_at: {expires_at}"
                )

                # Immediately verify it was blacklisted
                is_bl = user_manager.is_blacklisted(token_jti)
                logger.info(f"Blacklist verification for {token_jti}: {is_bl}")
            else:
                logger.warning(
                    f"Invalid token payload - jti or exp missing. "
                    f"jti={token_jti}, exp={token_exp}"
                )
        except Exception as e:
            logger.warning(f"Failed to blacklist token: {e}", exc_info=True)
    else:
        logger.warning("No Bearer token found in Authorization header")

    # Log the logout event if user is authenticated
    if auth_data and "user_id" in auth_data:
        logger.info(f"User {auth_data['user_id']} logged out")

    return schemas.LogoutResponse(message="Successfully logged out")


@auth_api_v1.method(
    openapi_extra={"no_auth": True},
    errors=[jsonrpc_errors.UnauthorizedError],
)
async def refresh_token(
    request: Request,
    body: schemas.TokenRefreshRequest,
    user_manager: UserManager = Depends(get_user_manager),
) -> schemas.TokenRefreshResponse:
    """Refresh JWT token using refresh_token.

    This endpoint follows the standard JWT refresh token pattern:
    - Client provides a valid refresh_token
    - Server validates the refresh_token
    - Server returns new access_token and refresh_token
    - Old refresh_token is optionally invalidated

    Args:
        request: HTTP request object
        body: Token refresh request containing refresh_token
        user_manager: UserManager dependency for user operations

    Returns:
        TokenRefreshResponse with new JWT access and refresh tokens

    Raises:
        UnauthorizedError: If refresh token is invalid or expired
    """
    func_name = "refresh_token"
    logger.info(f"Call {func_name}")

    # Validate refresh_token is provided
    if not body or not body.refresh_token:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["Refresh token required"]),
        )

    # Verify and decode refresh token
    security_manager = request.app.state._security_manager
    username = None
    payload = None

    try:
        payload = jwt.decode(
            body.refresh_token,
            Config.JWT_AUTH_SECRET_KEY,
            algorithms=[Config.JWT_AUTH_ALGORITHM],
            audience=Constant.JWT_AUTH_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["Refresh token has expired"]),
        )
    except jwt.InvalidTokenError:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["Invalid refresh token"]),
        )

    # Verify it's a refresh token
    if not payload or payload.get("type") != "refresh":
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (
                False,
                ["Invalid token type. Expected refresh token"],
            ),
        )

    username = payload.get("sub")
    if not username:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["Invalid refresh token: missing subject"]),
        )

    # Get user
    user = user_manager.get_user(username)

    # Check if user exists and is enabled
    if not user:
        jsonrpc_errors.handle_error_unauthorized(
            module_name,
            func_name,
            (False, ["User not found"]),
        )

    if not user.is_enabled:
        jsonrpc_errors.handle_error_forbidden(
            module_name,
            func_name,
            (False, ["User account is disabled"]),
        )

    # Check if user is locked during token refresh
    if user.is_locked:
        jsonrpc_errors.handle_error_forbidden(
            module_name,
            func_name,
            (
                False,
                ["User account is locked, cannot refresh token"],
            ),
        )

    # Check if password has expired
    if user and UserManager.is_password_expired(user):
        jsonrpc_errors.handle_error_forbidden(
            module_name,
            func_name,
            (False, ["Password has expired, cannot refresh token"]),
        )

    # Generate new access token
    access_token = security_manager.create_access_token({
        "sub": username,
        "jti": str(uuid.uuid4()),
        "aud": Constant.JWT_AUTH_AUDIENCE,
    })

    # Generate new refresh token
    refresh_token_new = security_manager.create_refresh_token({
        "sub": username,
        "jti": str(uuid.uuid4()),
        "aud": Constant.JWT_AUTH_AUDIENCE,
    })

    logger.info(f"Token refreshed for user: {username}")

    return schemas.TokenRefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token_new,
        token_type=_s("bearer"),
        expires_in=Config.ACCESS_TOKEN_EXPIRE_MINUTES
        * 60,  # Convert minutes to seconds
        refresh_expires_in=Config.REFRESH_TOKEN_EXPIRE_DAYS
        * 86400,  # Convert days to seconds
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

    # Build response - get roles from user_roles association table
    roles = user.get_role_names()

    response_info = {
        "id": user.id,
        "user_name": user.user_name,
        "roles": roles,
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
