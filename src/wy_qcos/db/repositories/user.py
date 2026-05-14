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
import uuid as uuid_lib
from datetime import datetime

import pwdlib
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from wy_qcos.db.models import User, LoginLog, TokenBlacklist, UserRole, Role
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.api.schemas.user import CreateUserRequest, UpdateUserRequest
from wy_qcos.common.config import Config

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = pwdlib.PasswordHash(hashers=[BcryptHasher()])


class UserRepository(BaseRepository):
    """Database operation function library related to Users."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    # ==================== Password Utilities ====================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        # pwdlib automatically handles bcrypt 72 byte limit
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        try:
            valid, new_hash = pwd_context.verify_and_update(
                plain_password, hashed_password
            )
            return valid
        except Exception:
            return False

    # ==================== User CRUD Operations ====================

    def create_user(self, user_create: CreateUserRequest):
        """Create a new user."""
        try:
            user_data = user_create.model_dump()
            # Hash password and remove plain password
            user_data["hashed_password"] = self.hash_password(
                user_create.password
            )
            del user_data["password"]

            # Extract roles to handle them separately
            roles = user_data.pop("roles", [])

            success, error, user = self.create(User, **user_data)
            if success:
                logger.info(f"User created successfully: {user.user_name}")
                # Assign roles to the user
                if roles:
                    for role_name in roles:
                        self.assign_role(user.id, role_name)
                return success, None, user
            else:
                logger.error(f"Failed to create user: {error}")
                return success, error, None
        except Exception as e:
            logger.error(f"Exception while creating user: {e}")
            self.rollback()
            return False, e, None

    def get_user_by_username(self, user_name: str):
        """Get a user by username."""
        try:
            # Fix: Use 'user_name' instead of 'username' to match model field
            success, error, user = self.get_by_attr(
                User, "user_name", user_name
            )
            if success and user:
                # Auto-cleanup: If user is marked as locked but lockout
                # period has expired, automatically unlock them before
                # returning
                if (
                    user.is_locked
                    and user.locked_until
                    and datetime.now() >= user.locked_until
                ):
                    logger.info(
                        f"Auto-unlocking user '{user_name}' - lockout "
                        f"period has expired (locked_until: "
                        f"{user.locked_until})"
                    )
                    # Update the user record
                    user.is_locked = False
                    user.locked_until = None
                    user.failed_login_attempts = 0
                    self._db_session.commit()
                    self._db_session.refresh(user)
                    logger.info(
                        f"User '{user_name}' auto-unlocked and "
                        f"persisted to database"
                    )
                return True, None, user
            else:
                return False, f"User with name {user_name} not found", None
        except Exception as e:
            logger.error(f"Exception while getting user by username: {e}")
            return False, e, None

    def get_user_by_id(self, user_id: str):
        """Get a user by UUID string ID."""
        try:
            success, error, user = self.get_by_uuid(User, user_id)
            if success and user:
                # Auto-cleanup: If user is marked as locked but lockout
                # period has expired, automatically unlock them before
                # returning
                if (
                    user.is_locked
                    and user.locked_until
                    and datetime.now() >= user.locked_until
                ):
                    logger.info(
                        f"Auto-unlocking user ID '{user_id}' - lockout "
                        f"period has expired (locked_until: "
                        f"{user.locked_until})"
                    )
                    # Update the user record
                    user.is_locked = False
                    user.locked_until = None
                    user.failed_login_attempts = 0
                    self._db_session.commit()
                    self._db_session.refresh(user)
                    logger.info(
                        f"User ID '{user_id}' auto-unlocked and "
                        f"persisted to database"
                    )
                return True, None, user
            return False, f"User with id {user_id} not found", None
        except Exception as e:
            logger.error(f"Exception while getting user by id: {e}")
            return False, e, None

    def get_users(self):
        """Get all users."""
        try:
            success, error, users = self.get_all(User)
            if success:
                return True, None, users
            else:
                logger.error(f"Failed to get users: {error}")
                return False, error, None
        except Exception as e:
            logger.error(f"Exception while getting all users: {e}")
            return False, e, None

    def update_user(self, user_id: str, user_update: UpdateUserRequest):
        """Update a user."""
        try:
            # First check if user exists
            success, error, existing_user = self.get_by_uuid(User, user_id)
            if not success or not existing_user:
                return False, f"User with id {user_id} not found", None

            # Update only provided fields
            update_data = user_update.model_dump(exclude_unset=True)

            # Extract roles to handle them separately
            roles = update_data.pop("roles", None)

            # Handle password if provided
            password_changed = False
            if update_data.get("password"):
                update_data["hashed_password"] = self.hash_password(
                    update_data["password"]
                )
                del update_data["password"]
                password_changed = True
                # Update password_changed_at timestamp when password is changed
                update_data["password_changed_at"] = datetime.now()

            # Filter out keys that were not provided
            # (model_dump with exclude_unset=True) but keep None values
            # to allow clearing/nullifying fields
            if update_data:
                success, error, updated_user = self.update(
                    User, user_id, **update_data
                )
                if not success:
                    logger.error(f"Failed to update user: {error}")
                    return False, error, None
            else:
                # If no update_data but password changed, still need to reload
                if password_changed:
                    success, error, updated_user = self.get_by_uuid(
                        User, user_id
                    )
                    if not success:
                        logger.error(
                            f"Failed to reload user after password "
                            f"change: {error}"
                        )
                        return False, error, None
                else:
                    updated_user = existing_user

            # Update roles if provided
            if roles is not None:
                role_success, role_error = self.update_user_roles(
                    user_id, roles
                )
                if not role_success:
                    logger.error(f"Failed to update user roles: {role_error}")
                    return False, role_error, None
                # Reload user to get the updated state with new roles
                success, error, updated_user = self.get_by_uuid(User, user_id)
                if not success:
                    return False, error, None

            logger.info(f"User updated successfully: {updated_user.user_name}")
            return True, None, updated_user
        except Exception as e:
            logger.error(f"Exception while updating user: {e}")
            self.rollback()
            return False, e, None

    def delete_user_by_id(self, user_id: str):
        """Delete a user by UUID string.

        This method first deletes all user-role associations before
        deleting the user to avoid foreign key constraint violations.
        """
        try:
            # First, delete all role associations for this user
            delete_roles_query = delete(UserRole).where(
                UserRole.user_id == user_id
            )
            result = self._db_session.execute(delete_roles_query)
            self._db_session.flush()
            logger.debug(
                f"Deleted {result.rowcount} role associations for "
                f"user {user_id}"
            )

            # Then delete the user itself
            success, error = self.delete_by_uuid(User, user_id)
            if success:
                logger.info(f"User deleted successfully: {user_id}")
                return True, None
            else:
                logger.error(f"Failed to delete user: {error}")
                return False, error
        except Exception as e:
            logger.error(f"Exception while deleting user: {e}")
            self.rollback()
            return False, e

    def delete_user_by_username(self, user_name: str):
        """Delete a user by username.

        This method first deletes all user-role associations before
        deleting the user to avoid foreign key constraint violations.
        """
        try:
            # Get the user first to get their ID
            success, error, user = self.get_user_by_username(user_name)
            if not success or not user:
                logger.error(f"User '{user_name}' not found")
                return False, f"User '{user_name}' not found"

            # Delete all role associations for this user
            delete_roles_query = delete(UserRole).where(
                UserRole.user_id == user.id
            )
            result = self._db_session.execute(delete_roles_query)
            self._db_session.flush()
            logger.debug(
                f"Deleted {result.rowcount} role associations for "
                f"user {user_name}"
            )

            # Then delete the user itself
            success, error = self.delete_by_attr(User, "user_name", user_name)
            if success:
                logger.info(f"User deleted successfully: {user_name}")
                return True, None
            else:
                logger.error(f"Failed to delete user: {error}")
                return False, error
        except Exception as e:
            logger.error(f"Exception while deleting user: {e}")
            self.rollback()
            return False, e

    # ==================== Login Log Operations ====================

    def create_login_log(
        self,
        user_name: str,
        ip_address: str,
        success: bool,
        failure_reason: str | None = None,
        user_agent: str | None = None,
        project_id: str | None = None,
    ):
        """Create a login log entry with auto cleanup when logs exceeded."""
        try:
            log_data = {
                "user_name": user_name,
                "ip_address": ip_address,
                "login_time": datetime.now(),
                "login_status": success,
                "failure_reason": failure_reason,
                "user_agent": user_agent,
                "project_id": project_id,
            }
            log_success, error, log = self.create(LoginLog, **log_data)
            if log_success:
                # Cleanup old logs if needed
                self._cleanup_old_login_logs()
                return True, None, log
            else:
                logger.error(f"Failed to create login log: {error}")
                return log_success, error, None
        except Exception as e:
            logger.error(f"Exception while creating login log: {e}")
            self.rollback()
            return False, e, None

    def _cleanup_old_login_logs(self):
        """Remove oldest login logs when exceeding MAX_LOGIN_LOGS."""
        try:
            # Count existing logs
            count_query = select(func.count(LoginLog.id))
            count_result = self._db_session.execute(count_query).scalar()

            if count_result and count_result > Config.MAX_LOGIN_LOGS:
                # Calculate how many to delete
                to_delete = count_result - Config.MAX_LOGIN_LOGS

                # Delete oldest records
                delete_query = delete(LoginLog).where(
                    LoginLog.id.in_(
                        select(LoginLog.id)
                        .order_by(LoginLog.login_time.asc())
                        .limit(to_delete)
                    )
                )
                result = self._db_session.execute(delete_query)
                self._db_session.commit()
                logger.info(f"Cleaned up {result.rowcount} old login log(s)")
        except Exception as e:
            logger.warning(f"Exception while cleaning up login logs: {e}")

    def get_login_logs(
        self,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        """Get login logs with optional filters."""
        try:
            query = select(LoginLog)

            # Apply filters
            if user_id:
                # Get user by ID first to get username
                success, error, user = self.get_by_uuid(User, user_id)
                if success and user:
                    query = query.where(LoginLog.user_name == user.user_name)
                else:
                    # User not found, return error
                    error_msg = f"User with ID '{user_id}' not found"
                    return False, error_msg, None

            if start_time:
                query = query.where(LoginLog.login_time >= start_time)

            if end_time:
                query = query.where(LoginLog.login_time <= end_time)

            # Order by login_time descending (most recent first)
            query = query.order_by(LoginLog.login_time.desc())

            # Apply pagination
            query = query.offset(offset).limit(limit)

            result = self._db_session.execute(query)
            logs = result.scalars().all()

            return True, None, logs
        except Exception as e:
            logger.error(f"Exception while getting login logs: {e}")
            return False, e, None

    def delete_login_logs(
        self, user_id: str | None = None, user_name: str | None = None
    ):
        """Delete login logs (all or for a specific user).

        Args:
            user_id: User ID (UUID) to delete logs for (optional)
            user_name: User name to delete logs for (optional)

        Returns:
            Tuple (success, error, count) where count is number of deleted logs
        """
        try:
            query = select(LoginLog)

            # Apply filters
            if user_id:
                # Get user by ID first
                success, error, user = self.get_by_uuid(User, user_id)
                if success and user:
                    query = query.where(LoginLog.user_name == user.user_name)
                else:
                    # User not found, return success with count 0
                    return True, None, 0

            elif user_name:
                # Check if user exists first
                success, error, user = self.get_user_by_username(user_name)
                if not success or not user:
                    # User not found, return success with count 0
                    return True, None, 0
                query = query.where(LoginLog.user_name == user_name)

            # First count how many logs will be deleted
            count_query = select(func.count(LoginLog.id))

            # Apply same filters to count query
            if user_id:
                success, error, user = self.get_by_uuid(User, user_id)
                if success and user:
                    count_query = count_query.where(
                        LoginLog.user_name == user.user_name
                    )

            elif user_name:
                count_query = count_query.where(
                    LoginLog.user_name == user_name
                )

            # Get the count
            count_result = self._db_session.execute(count_query)
            deleted_count = count_result.scalar() or 0

            # Delete the logs
            delete_query = delete(LoginLog)

            # Apply same filters to delete query
            if user_id:
                success, error, user = self.get_by_uuid(User, user_id)
                if success and user:
                    delete_query = delete_query.where(
                        LoginLog.user_name == user.user_name
                    )

            elif user_name:
                delete_query = delete_query.where(
                    LoginLog.user_name == user_name
                )

            self._db_session.execute(delete_query)
            self._db_session.commit()

            logger.info(f"Deleted {deleted_count} login log(s)")
            return True, None, deleted_count

        except Exception as e:
            logger.error(f"Exception while deleting login logs: {e}")
            self.rollback()
            return False, e, 0

    # ==================== Token Blacklist Operations ====================

    def add_to_blacklist(self, token_jti: str, expires_at: datetime):
        """Add a token to the blacklist."""
        try:
            logger.debug(
                f"Adding token to blacklist - jti: {token_jti}, "
                f"expires_at: {expires_at}"
            )
            token_data = {
                "token_jti": token_jti,
                "expires_at": expires_at,
            }
            success, error, token = self.create(TokenBlacklist, **token_data)
            if success:
                logger.info(
                    f"Token {token_jti} successfully added to blacklist "
                    f"with ID: {token.id}"
                )
                # Verify it was actually persisted
                verify_query = select(TokenBlacklist).where(
                    TokenBlacklist.token_jti == token_jti
                )
                verify_result = self._db_session.execute(verify_query)
                verify_token = verify_result.scalars().first()
                if verify_token:
                    logger.debug(
                        f"Blacklist entry verified in database: "
                        f"{verify_token.id}"
                    )
                else:
                    logger.warning(
                        f"Failed to verify blacklist entry for "
                        f"token {token_jti}"
                    )
                return True, None
            else:
                logger.error(f"Failed to add token to blacklist: {error}")
                return success, error
        except Exception as e:
            logger.error(
                f"Exception while adding token to blacklist: {e}",
                exc_info=True,
            )
            self.rollback()
            return False, e

    def is_blacklisted(self, token_jti: str) -> bool:
        """Check if a token is blacklisted."""
        try:
            logger.debug(
                f"Checking if token is blacklisted - jti: {token_jti}"
            )

            query = select(TokenBlacklist).where(
                TokenBlacklist.token_jti == token_jti
            )
            result = self._db_session.execute(query)
            token = result.scalars().first()

            if token:
                logger.debug(
                    f"Token {token_jti} found in blacklist, "
                    f"expires_at: {token.expires_at}"
                )
                # Check if the blacklist entry has expired
                # (using local time - UTC+8)
                now = datetime.now()
                if now > token.expires_at:
                    # Entry has expired, remove it
                    logger.info(
                        f"Blacklist entry for token {token_jti} has "
                        f"expired ({now} > {token.expires_at}), removing"
                    )
                    self.delete_by_uuid(TokenBlacklist, token.id)
                    return False
                logger.info(
                    f"Token {token_jti} is still in blacklist "
                    f"(valid until {token.expires_at})"
                )
                return True
            else:
                logger.debug(f"Token {token_jti} not found in blacklist")
            return False
        except Exception as e:
            logger.error(
                f"Exception while checking token blacklist: {e}", exc_info=True
            )
            return False

    def cleanup_blacklist(self):
        """Remove expired entries from the blacklist."""
        try:
            # Use local time (UTC+8) for cleanup
            now = datetime.now()
            query = delete(TokenBlacklist).where(
                TokenBlacklist.expires_at < now
            )
            result = self._db_session.execute(query)
            self._db_session.commit()
            if result.rowcount > 0:
                logger.info(
                    f"Cleaned up {result.rowcount} expired token(s) "
                    f"from blacklist"
                )
            return True, None
        except Exception as e:
            logger.error(f"Exception while cleaning up blacklist: {e}")
            self.rollback()
            return False, e

    # ==================== User-Role Association Operations ==

    def assign_role(
        self, user_id: str, role_name: str
    ) -> tuple[bool, str | None]:
        """Assign a role to a user.

        Args:
            user_id: User ID
            role_name: Role name to assign

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get role by name
            query = select(Role).where(Role.role_name == role_name)
            result = self._db_session.execute(query)
            role = result.scalars().first()

            if not role:
                logger.error(f"Role '{role_name}' not found")
                return False, f"Role '{role_name}' not found"

            # Check if user already has this role
            query = select(UserRole).where(
                (UserRole.user_id == user_id) & (UserRole.role_id == role.id)
            )
            result = self._db_session.execute(query)
            existing = result.scalars().first()

            if existing:
                logger.info(f"User {user_id} already has role {role_name}")
                return True, None

            # Create user-role association
            user_role_data = {
                "id": str(uuid_lib.uuid4()),
                "user_id": user_id,
                "role_id": role.id,
                "created_at": datetime.now(),
            }
            success, error, _ = self.create(UserRole, **user_role_data)
            if success:
                logger.info(f"Role '{role_name}' assigned to user {user_id}")
                return True, None
            else:
                logger.error(f"Failed to assign role: {error}")
                return False, str(error)
        except Exception as e:
            logger.error(f"Exception while assigning role: {e}")
            self.rollback()
            return False, str(e)

    def remove_role(
        self, user_id: str, role_name: str
    ) -> tuple[bool, str | None]:
        """Remove a role from a user.

        Args:
            user_id: User ID
            role_name: Role name to remove

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get role by name
            query = select(Role).where(Role.role_name == role_name)
            result = self._db_session.execute(query)
            role = result.scalars().first()

            if not role:
                logger.error(f"Role '{role_name}' not found")
                return False, f"Role '{role_name}' not found"

            # Delete user-role association
            query = delete(UserRole).where(
                (UserRole.user_id == user_id) & (UserRole.role_id == role.id)
            )
            result = self._db_session.execute(query)
            self._db_session.commit()

            logger.info(f"Role '{role_name}' removed from user {user_id}")
            return True, None
        except Exception as e:
            logger.error(f"Exception while removing role: {e}")
            self.rollback()
            return False, str(e)

    def revoke_role(
        self, user_id: str, role_name: str
    ) -> tuple[bool, str | None]:
        """Revoke a role from a user (alias for remove_role).

        Args:
            user_id: User ID
            role_name: Role name to revoke

        Returns:
            Tuple of (success, error_message)
        """
        return self.remove_role(user_id, role_name)

    def update_user_roles(
        self, user_id: str, role_names: list[str]
    ) -> tuple[bool, str | None]:
        """Update all roles for a user (replace existing roles).

        Args:
            user_id: User ID
            role_names: List of role names to assign

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Delete all existing roles for this user
            query = delete(UserRole).where(UserRole.user_id == user_id)
            self._db_session.execute(query)
            self._db_session.flush()

            # Assign new roles
            for role_name in role_names:
                success, error = self.assign_role(user_id, role_name)
                if not success:
                    logger.error(
                        f"Failed to assign role '{role_name}': {error}"
                    )
                    self.rollback()
                    return False, str(error)

            self._db_session.commit()
            logger.info(f"User roles updated successfully: {user_id}")
            return True, None
        except Exception as e:
            logger.error(f"Exception while updating user roles: {e}")
            self.rollback()
            return False, str(e)

    def get_user_roles(
        self, user_id: str
    ) -> tuple[bool, str | None, list[str]]:
        """Get all roles for a user.

        Args:
            user_id: User ID

        Returns:
            Tuple of (success, error_message, role_names_list)
        """
        try:
            query = select(UserRole).where(UserRole.user_id == user_id)
            result = self._db_session.execute(query)
            user_roles = result.scalars().all()

            role_names = [ur.role.role_name for ur in user_roles if ur.role]
            return True, None, role_names
        except Exception as e:
            logger.error(f"Exception while getting user roles: {e}")
            return False, str(e), []
