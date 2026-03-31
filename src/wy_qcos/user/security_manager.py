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
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from wy_qcos.api.schemas import user as schemas
from wy_qcos.common.config import Config
from wy_qcos.user.user_manager import UserManager

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# Token configuration
SECRET_KEY = Config.SECRET_KEY or secrets.token_urlsafe(32)
ALGORITHM = Config.ALGORITHM or "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = Config.ACCESS_TOKEN_EXPIRE_MINUTES or 30
REFRESH_TOKEN_EXPIRE_DAYS = Config.REFRESH_TOKEN_EXPIRE_DAYS or 7

# Rate limiting configuration
MAX_LOGIN_ATTEMPTS = Config.MAX_LOGIN_ATTEMPTS or 5
LOCKOUT_DURATION_MINUTES = Config.LOCKOUT_DURATION_MINUTES or 15


class SecurityManager:
    """Enhanced security manager with advanced authentication features."""

    def __init__(self, user_manager: UserManager):
        """Initialize security manager.

        Args:
            user_manager: user manager instance
        """
        self.user_manager = user_manager
        self.failed_attempts = {}  # Track failed login attempts
        self.active_sessions = {}  # Track active sessions

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash.

        Args:
            plain_password: plain text password
            hashed_password: hashed password

        Returns:
            True if password matches
        """
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
            if isinstance(hashed_password, str)
            else hashed_password,
        )

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password.

        Args:
            password: plain text password

        Returns:
            hashed password
        """
        return bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_account_lockout(self, user_name: str) -> bool:
        """Check if account is locked due to failed login attempts.

        Args:
            user_name: user name

        Returns:
            True if account is locked
        """
        if user_name not in self.failed_attempts:
            return False

        attempts = self.failed_attempts[user_name]
        if len(attempts) < MAX_LOGIN_ATTEMPTS:
            return False

        last_attempt = attempts[-1]
        lockout_until = last_attempt + timedelta(
            minutes=LOCKOUT_DURATION_MINUTES
        )

        if datetime.now() < lockout_until:
            return True
        else:
            # Reset failed attempts after lockout period
            self.failed_attempts[user_name] = []
            return False

    def record_failed_attempt(self, user_name: str) -> None:
        """Record a failed login attempt.

        Args:
            user_name: user name
        """
        if user_name not in self.failed_attempts:
            self.failed_attempts[user_name] = []

        self.failed_attempts[user_name].append(datetime.now())
        logger.warning(f"Failed login attempt for user: {user_name}")

    def record_successful_login(
        self, user_name: str, ip_address: str, user_agent: str
    ) -> None:
        """Record a successful login.

        Args:
            user_name: user name
            ip_address: IP address
            user_agent: user agent string
        """
        # Clear failed attempts on successful login
        if user_name in self.failed_attempts:
            self.failed_attempts[user_name] = []

        # Log the successful login
        self.user_manager.log_login_attempt(
            user_name, ip_address, "success", user_agent
        )

        logger.info(
            f"Successful login for user: {user_name} from {ip_address}"
        )

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """Create JWT access token.

        Args:
            data: data to encode in token
            expires_delta: token expiration time

        Returns:
            JWT token string
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token.

        Args:
            data: data to encode in token

        Returns:
            JWT refresh token string
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> dict:
        """Verify JWT token.

        Args:
            token: JWT token string

        Returns:
            decoded token data

        Raises:
            HTTPException: if token is invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def authenticate_user(
        self, user_name: str, password: str, ip_address: str, user_agent: str
    ) -> schemas.User:
        """Authenticate user with enhanced security.

        Args:
            user_name: user name
            password: password
            ip_address: IP address
            user_agent: user agent string

        Returns:
            authenticated user

        Raises:
            HTTPException: if authentication fails
        """
        # Check if account is locked
        if self.check_account_lockout(user_name):
            self.user_manager.log_login_attempt(
                user_name, ip_address, "locked", user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=(
                    "Account is temporarily locked due to "
                    "too many failed login attempts"
                ),
            )

        # Get user
        user = self.user_manager.get_user(user_name)
        if not user:
            self.record_failed_attempt(user_name)
            self.user_manager.log_login_attempt(
                user_name, ip_address, "user_not_found", user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is enabled
        if not user.is_enabled:
            self.record_failed_attempt(user_name)
            self.user_manager.log_login_attempt(
                user_name, ip_address, "disabled", user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Check if user is locked
        if (
            user.is_locked
            and user.locked_until
            and datetime.now() < user.locked_until
        ):
            self.record_failed_attempt(user_name)
            self.user_manager.log_login_attempt(
                user_name, ip_address, "locked", user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked",
            )

        # Check password
        if not self.verify_password(password, user.password_hash):
            self.record_failed_attempt(user_name)
            self.user_manager.log_login_attempt(
                user_name, ip_address, "invalid_password", user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check password expiration
        if UserManager.is_password_expired(user):
            self.user_manager.log_login_attempt(
                user_name, ip_address, "password_expired", user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password has expired. Please change your password.",
            )

        # Record successful login
        self.record_successful_login(user_name, ip_address, user_agent)

        # Update last login time
        user.last_login = datetime.now()
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None

        return user

    def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> schemas.User:
        """Get current authenticated user.

        Args:
            credentials: HTTP authorization credentials

        Returns:
            current user

        Raises:
            HTTPException: if authentication fails
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = self.verify_token(credentials.credentials)
            user_name: str | None = payload.get("sub")
            if user_name is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self.user_manager.get_user(user_name)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    def get_current_active_user(
        self, current_user: schemas.User = Depends(get_current_user)
    ) -> schemas.User:
        """Get current active user.

        Args:
            current_user: current user

        Returns:
            active user

        Raises:
            HTTPException: if user is inactive
        """
        if not current_user.is_enabled:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user

    def check_permissions(
        self, user: schemas.User, resource: str, action: str = "call"
    ) -> bool:
        """Check if user has permission for resource.

        Args:
            user: user
            resource: resource to check
            action: action to check (default: "call")

        Returns:
            True if user has permission
        """
        # Check if user has direct permissions
        if self.user_manager.perms_check_enforce(
            user.user_name, resource, action
        ):
            return True

        # Check if user has role-based permissions
        for role_name in user.roles:
            if self.user_manager.perms_check_enforce(
                role_name, resource, action
            ):
                return True

        return False


def get_security_manager(request) -> SecurityManager:
    """Get security manager from request state.

    Args:
        request: FastAPI request

    Returns:
        security manager
    """
    return request.app.state._security_manager


# Dependency annotations
CurrentUser = Annotated[schemas.User, Depends(get_security_manager)]
CurrentActiveUser = Annotated[schemas.User, Depends(get_security_manager)]
