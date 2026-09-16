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
import time
from datetime import datetime, timedelta
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


class SecurityManager:
    """Enhanced security manager with advanced authentication features."""

    def __init__(self, user_manager: UserManager):
        """Initialize security manager.

        Args:
            user_manager: user manager instance
        """
        self.user_manager = user_manager
        # Track failed login attempts per user_name. Each value is a list of
        # datetime timestamps. Entries are only cleared on successful login
        # (record_successful_login), so usernames that never log in
        # successfully (brute-force probes, scanners, disabled accounts) would
        # accumulate keys and timestamps forever. Eviction is applied on each
        # record/check to bound memory.
        self.failed_attempts = {}
        # Retain failed-attempt timestamps for at least twice the lockout
        # window so lockout checks remain accurate while bounding memory.
        self._failed_attempts_ttl = timedelta(
            minutes=max(Config.USERS.LOCKOUT_DURATION_MINUTES * 2, 60)
        )

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
        # Opportunistically evict expired entries to bound memory for
        # usernames that never succeed (brute-force probes, scanners,
        # disabled accounts).
        self._evict_expired_failed_attempts()
        if user_name not in self.failed_attempts:
            return False

        attempts = self.failed_attempts[user_name]
        if len(attempts) < Config.USERS.MAX_LOGIN_ATTEMPTS:
            return False

        last_attempt = attempts[-1]
        lockout_until = last_attempt + timedelta(
            minutes=Config.USERS.LOCKOUT_DURATION_MINUTES
        )

        if datetime.now() < lockout_until:
            return True
        else:
            # Reset failed attempts after lockout period; delete the key
            # entirely instead of keeping an empty list so the dict does
            # not retain growing keys for never-succeeding usernames.
            del self.failed_attempts[user_name]
            return False

    def _evict_expired_failed_attempts(self) -> None:
        """Drop failed-attempt timestamps older than the TTL.

        Also removes usernames whose attempt lists become empty so that
        keys for usernames that never succeed (brute-force probes,
        scanners, disabled accounts) do not accumulate forever.
        """
        cutoff = datetime.now() - self._failed_attempts_ttl
        expired_users = []
        for user_name, attempts in self.failed_attempts.items():
            # attempts are appended chronologically; keep the tail.
            idx = 0
            while idx < len(attempts) and attempts[idx] < cutoff:
                idx += 1
            if idx:
                del attempts[:idx]
            if not attempts:
                expired_users.append(user_name)
        for user_name in expired_users:
            del self.failed_attempts[user_name]

    def record_failed_attempt(self, user_name: str) -> None:
        """Record a failed login attempt.

        Args:
            user_name: user name
        """
        # Evict expired entries first to bound memory for usernames that
        # never succeed (brute-force probes, scanners, disabled accounts).
        self._evict_expired_failed_attempts()
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
        # Clear failed attempts on successful login; delete the key entirely
        # instead of keeping an empty list so the dict does not retain keys
        # for usernames that previously failed but later succeeded.
        self.failed_attempts.pop(user_name, None)

        # Log the successful login
        self.user_manager.log_login_attempt(
            user_name, ip_address, True, user_agent=user_agent
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
        # Use Unix timestamp (seconds since epoch) to avoid
        # datetime timezone issues. This ensures compatibility
        # with PyJWT's token expiration handling. Read from Config
        # at runtime to support dynamic configuration changes
        current_timestamp = int(time.time())
        if expires_delta:
            expire_timestamp = current_timestamp + int(
                expires_delta.total_seconds()
            )
        else:
            expire_timestamp = current_timestamp + (
                Config.USERS.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        to_encode.update({"exp": expire_timestamp})
        encoded_jwt = jwt.encode(
            to_encode,
            Config.USERS.JWT_AUTH_SECRET_KEY,
            algorithm=Config.USERS.JWT_AUTH_ALGORITHM,
        )
        return encoded_jwt

    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token.

        Args:
            data: data to encode in token

        Returns:
            JWT refresh token string
        """
        to_encode = data.copy()
        # Use Unix timestamp (seconds since epoch) to avoid
        # datetime timezone issues. Read from Config at runtime
        # to support dynamic configuration changes
        current_timestamp = int(time.time())
        expire_timestamp = current_timestamp + (
            Config.USERS.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
        to_encode.update({"exp": expire_timestamp, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode,
            Config.USERS.JWT_AUTH_SECRET_KEY,
            algorithm=Config.USERS.JWT_AUTH_ALGORITHM,
        )
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
            payload = jwt.decode(
                token,
                Config.USERS.JWT_AUTH_SECRET_KEY,
                algorithms=[Config.USERS.JWT_AUTH_ALGORITHM],
            )
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
                user_name,
                ip_address,
                False,
                failure_reason="Account is locked due to too "
                "many failed attempts",
                user_agent=user_agent,
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
                user_name,
                ip_address,
                False,
                failure_reason="User not found",
                user_agent=user_agent,
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
                user_name,
                ip_address,
                False,
                failure_reason="Account is disabled",
                user_agent=user_agent,
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
                user_name,
                ip_address,
                False,
                failure_reason="Account is locked",
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked",
            )

        # Check password
        if not self.verify_password(password, user.hashed_password):
            self.record_failed_attempt(user_name)
            self.user_manager.log_login_attempt(
                user_name,
                ip_address,
                False,
                failure_reason="Invalid password",
                user_agent=user_agent,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check password expiration
        if UserManager.is_password_expired(user):
            self.user_manager.log_login_attempt(
                user_name,
                ip_address,
                False,
                failure_reason="Password expired",
                user_agent=user_agent,
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
        if self.user_manager.perms_enforce(user.user_name, resource, action):
            return True

        # Check if user has role-based permissions
        for role_name in user.roles:
            if self.user_manager.perms_enforce(role_name, resource, action):
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
