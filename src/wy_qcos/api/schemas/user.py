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

import uuid
from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_serializer,
    model_validator,
)

from wy_qcos.common.constant import Constant


class UserRead(BaseModel):
    """User read schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="User ID (UUID)")
    user_name: str = Field(..., description="User name")
    roles: list[str] = Field(default=[], description="User roles")
    is_enabled: bool = Field(default=True, description="Is user enabled")
    is_locked: bool = Field(default=False, description="Is user locked")
    last_login: str | None = Field(default=None, description="Last login time")
    password_changed_at: str = Field(
        ..., description="Password last changed timestamp"
    )
    locked_until: str | None = Field(
        default=None, description="Locked until timestamp"
    )
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days"
    )
    failed_login_attempts: int = Field(
        default=0, description="Failed login attempts count"
    )
    description: str | None = Field(
        default=None,
        min_length=Constant.MIN_DESCRIPTION_LENGTH,
        max_length=Constant.MAX_DESCRIPTION_LENGTH,
        description="User description",
    )
    created_at: str = Field(..., description="User creation timestamp")
    updated_at: str = Field(..., description="User last updated timestamp")


class UserCreate(BaseModel):
    """User create schema."""

    user_name: str = Field(
        ...,
        min_length=Constant.MIN_USER_LENGTH,
        max_length=Constant.MAX_USER_LENGTH,
        description="User name",
    )
    password: str = Field(
        ...,
        min_length=Constant.MIN_PASSWORD_LENGTH,
        max_length=Constant.MAX_PASSWORD_LENGTH,
        description="Password",
    )
    roles: list[str] = Field(
        default=[Constant.ROLE_USER], description="User roles"
    )
    is_locked: bool = Field(default=False, description="Is user locked")
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days"
    )
    description: str | None = Field(
        default=None,
        min_length=Constant.MIN_DESCRIPTION_LENGTH,
        max_length=Constant.MAX_DESCRIPTION_LENGTH,
        description="User description",
    )


class UserUpdate(BaseModel):
    """User update schema."""

    user_name: str | None = Field(
        default=None,
        min_length=Constant.MIN_USER_LENGTH,
        max_length=Constant.MAX_USER_LENGTH,
        description="User name",
    )
    roles: list[str] | None = Field(default=None, description="User roles")
    is_locked: bool | None = Field(default=None, description="Is user locked")
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days"
    )
    description: str | None = Field(
        default=None,
        min_length=Constant.MIN_DESCRIPTION_LENGTH,
        max_length=Constant.MAX_DESCRIPTION_LENGTH,
        description="User description",
    )


# Internal models for routes_jsonrpc/user.py
class User(BaseModel):
    """User model.

    Note: roles are stored in user_roles association table, not in
    users table. The get_role_names() method on the User ORM model
    retrieves them dynamically.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="User ID (UUID)"
    )
    project_id: str = Field(
        default_factory=lambda: Constant.DEFAULT_PROJECT_ID,
        description="Project ID (UUID)",
    )
    user_name: str = Field(..., description="User name")
    hashed_password: str = Field(
        ...,
        description="Password hash",
        json_schema_extra={"is_sensitive": True},
    )
    roles: list[str] = Field(
        default=[], description="User roles (from user_roles table)"
    )
    password_expiry_days: int | None = Field(
        description="Password expiry days"
    )
    is_enabled: bool = Field(default=True, description="Is user enabled")
    is_locked: bool = Field(default=False, description="Is user locked")
    failed_login_attempts: int = Field(
        default=0, description="Failed login attempts"
    )
    last_login: datetime | None = Field(
        default=None, description="Last login time"
    )
    password_changed_at: datetime = Field(
        default_factory=datetime.now, description="Password last changed"
    )
    locked_until: datetime | None = Field(
        default=None, description="Locked until"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="User creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="User last updated time"
    )
    description: str | None = Field(
        default=None, description="User description"
    )

    @model_validator(mode="after")
    def populate_roles_from_orm(self):
        """Populate roles from ORM user_roles relationship.

        When loading from ORM, if the user object has
        get_role_names method, call it to populate the roles list
        from the user_roles association table.
        """
        # This will be called after the model is created from ORM
        # The __pydantic_validator__ will have already populated
        # fields from ORM. If we got an ORM object with user_roles,
        # extract role names
        return self

    @field_serializer("roles", when_used="json")
    def serialize_roles(self, value) -> list[str]:
        """Serialize roles from ORM user_roles relationship."""
        # If value is already a list of strings, return it
        if isinstance(value, list) and all(isinstance(r, str) for r in value):
            return value
        # Otherwise, this should have been populated from ORM model
        return value


class GetUserMgmtRequest(BaseModel):
    """Get user management status request."""


class GetUserMgmtResponse(BaseModel):
    """Get user management status response."""

    auth_mode: str = Field(
        ..., description="User authentication mode"
    )
    password_expiry_days: int = Field(
        default=0, description="Password expiry days"
    )
    max_login_attempts: int = Field(
        default=5, description="Maximum login attempts"
    )
    lockout_duration_minutes: int = Field(
        default=30, description="Lockout duration in minutes"
    )


class SetUserMgmtRequest(BaseModel):
    """Set user management request."""

    auth_mode: str = Field(
        ...,
        description="Authentication mode: 'no', 'jwt', or 'virtual_instance'"
    )


class SetUserMgmtResponse(BaseModel):
    """Set user management response."""

    auth_mode: str = Field(
        ..., description="Updated authentication mode"
    )
    message: str = Field(..., description="Success message")


class CreateUserRequest(BaseModel):
    """Create user request."""

    project_id: str | None = Field(
        default=None,
        description="Project ID (UUID) - optional, "
        "defaults to DEFAULT_PROJECT_ID",
    )
    user_name: str = Field(
        ...,
        min_length=Constant.MIN_USER_LENGTH,
        max_length=Constant.MAX_USER_LENGTH,
        description="User name",
    )
    password: str = Field(
        ...,
        min_length=Constant.MIN_PASSWORD_LENGTH,
        max_length=Constant.MAX_PASSWORD_LENGTH,
        description="Password",
        json_schema_extra={"is_sensitive": True},
    )
    roles: list[str] = Field(
        default=[Constant.ROLE_USER], description="User roles"
    )
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days (optional)"
    )
    is_enabled: bool = Field(
        default=True, description="Whether user is enabled"
    )
    is_locked: bool = Field(
        default=False, description="Whether user is locked"
    )
    description: str | None = Field(
        default=None, description="User description"
    )


class CreateUserResponse(BaseModel):
    """Create user response."""

    id: str = Field(..., description="User ID (UUID)")
    project_id: str = Field(..., description="Project ID (UUID)")
    user_name: str = Field(..., description="User name")
    roles: list[str] | None = Field(..., description="User roles")
    is_enabled: bool | None = Field(..., description="Whether user is enabled")
    is_locked: bool | None = Field(..., description="Whether user is locked")
    description: str | None = Field(
        default=None, description="User description"
    )
    created_at: str | None = Field(..., description="Creation timestamp")


class GetUserRequest(BaseModel):
    """Get user request by ID."""

    user_id: str = Field(..., description="User ID (UUID)")


class GetUserResponse(BaseModel):
    """Get user response."""

    id: str = Field(..., description="User ID (UUID)")
    project_id: str = Field(..., description="Project ID (UUID)")
    user_name: str = Field(..., description="User name")
    roles: list[str] = Field(..., description="User roles")
    is_enabled: bool = Field(..., description="Whether user is enabled")
    is_locked: bool = Field(..., description="Whether user is locked")
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days"
    )
    last_login: str | None = Field(
        default=None, description="Last login timestamp"
    )
    password_changed_at: str = Field(
        ..., description="Password last changed timestamp"
    )
    locked_until: str | None = Field(
        default=None, description="Locked until timestamp"
    )
    description: str | None = Field(
        default=None, description="User description"
    )
    created_at: str = Field(..., description="User creation timestamp")
    updated_at: str = Field(..., description="User last updated timestamp")


class GetUsersRequest(BaseModel):
    """Get users request with optional filtering."""

    filters: dict | None = Field(
        default=None,
        description="Filter conditions dict, e.g. {'user_name': 'admin'}",
    )


class UpdateUserRequest(BaseModel):
    """Update user request by ID."""

    user_id: str = Field(..., description="User ID (UUID)")
    roles: list[str] | None = Field(default=None, description="User roles")
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days"
    )
    is_enabled: bool | None = Field(
        default=None, description="Whether user is enabled"
    )
    is_locked: bool | None = Field(
        default=None, description="Whether user is locked"
    )
    description: str | None = Field(
        default=None, description="User description"
    )


class PasswordChangeRequest(UpdateUserRequest):
    """Password change request with password field support."""

    password: str | None = Field(default=None, description="New password")


class UpdateUserResponse(BaseModel):
    """Update user response."""

    id: str = Field(..., description="User ID (UUID)")
    project_id: str = Field(..., description="Project ID (UUID)")
    user_name: str = Field(..., description="User name")
    roles: list[str] = Field(..., description="User roles")
    is_enabled: bool = Field(..., description="Whether user is enabled")
    is_locked: bool = Field(..., description="Whether user is locked")
    description: str | None = Field(
        default=None, description="User description"
    )
    updated_at: str = Field(..., description="Update timestamp")


class DeleteUserRequest(BaseModel):
    """Delete user request by ID."""

    user_id: str = Field(..., description="User ID (UUID)")
    force: bool = Field(
        default=False,
        description="Force delete user and cascade delete related resources",
    )


class DeleteUserResponse(BaseModel):
    """Delete user response."""

    id: str = Field(..., description="User ID (UUID)")
    project_id: str = Field(..., description="Project ID (UUID)")
    user_name: str = Field(..., description="User name")
    deleted_at: str = Field(..., description="Deletion timestamp")


class LockUserRequest(BaseModel):
    """Lock user request."""

    user_name: str = Field(..., description="User name")
    action: str = Field(..., description="Action: lock or unlock")


class LockUserResponse(BaseModel):
    """Lock user response."""

    user_name: str = Field(..., description="User name")
    is_locked: bool = Field(..., description="Whether user is locked")
    locked_until: str | None = Field(
        default=None, description="Locked until timestamp"
    )
    message: str = Field(..., description="Action message")


class ChangePasswordRequest(BaseModel):
    """Change password request by user ID."""

    user_id: str = Field(..., description="User ID (UUID)")
    old_password: str | None = Field(
        default=None,
        description="Old password (for non-admin changes)",
        json_schema_extra={"is_sensitive": True},
    )
    new_password: str = Field(
        ...,
        min_length=Constant.MIN_PASSWORD_LENGTH,
        max_length=Constant.MAX_PASSWORD_LENGTH,
        description="New password",
        json_schema_extra={"is_sensitive": True},
    )


class ChangePasswordResponse(BaseModel):
    """Change password response."""

    user_name: str = Field(..., description="User name")
    password_changed_at: str = Field(
        ..., description="Password changed timestamp"
    )
    message: str = Field(..., description="Success message")


class LoginLog(BaseModel):
    """Login log model."""

    user_name: str = Field(..., description="User name")
    ip_address: str = Field(..., description="IP address")
    login_time: datetime = Field(
        default_factory=datetime.now, description="Login time"
    )
    success: bool = Field(..., description="Whether login was successful")
    user_agent: str | None = Field(default=None, description="User agent")
    failure_reason: str | None = Field(
        default=None,
        description="Reason for login failure if success is False",
    )


class GetLoginLogsRequest(BaseModel):
    """Get login logs request by user ID or user_name."""

    user_id: str | None = Field(
        default=None, description="Filter by user ID (UUID)"
    )
    user_name: str | None = Field(
        default=None, description="Filter by user name"
    )
    start_time: str | None = Field(
        default=None, description="Filter by start time (ISO format)"
    )
    end_time: str | None = Field(
        default=None, description="Filter by end time (ISO format)"
    )
    limit: int | None = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of logs to return",
    )
    offset: int | None = Field(
        default=0, ge=0, description="Number of logs to skip"
    )

    @model_validator(mode="after")
    def validate_user_filter(self):
        """Ensure user_id and user_name are mutually exclusive."""
        if self.user_id is not None and self.user_name is not None:
            raise ValueError(
                "Cannot specify both user_id and user_name. "
                "Please provide only one."
            )
        return self


class LoginLogResponse(BaseModel):
    """Login log response."""

    user_id: str | None = Field(..., description="User ID (UUID)")
    project_id: str = Field(..., description="Project ID (UUID)")
    user_name: str = Field(..., description="User name")
    login_time: str = Field(..., description="Login timestamp")
    ip_address: str = Field(..., description="IP address")
    user_agent: str | None = Field(default=None, description="User agent")
    success: bool = Field(..., description="Whether login was successful")
    failure_reason: str | None = Field(
        default=None, description="Failed reason if login failed"
    )


class Role(BaseModel):
    """Role model."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Role ID (UUID)"
    )
    role_name: str = Field(..., description="Role name")
    permissions: list[str] = Field(default=[], description="Role permissions")
    description: str | None = Field(
        default=None, description="Role description"
    )


class CreateRoleRequest(BaseModel):
    """Create role request."""

    role_name: str = Field(
        ...,
        min_length=Constant.MIN_ROLE_LENGTH,
        max_length=Constant.MAX_ROLE_LENGTH,
        description="Role name",
    )
    permissions: list[str] = Field(default=[], description="Role permissions")
    description: str | None = Field(
        default=None,
        min_length=Constant.MIN_DESCRIPTION_LENGTH,
        max_length=Constant.MAX_DESCRIPTION_LENGTH,
        description="Role description",
    )


class CreateRoleResponse(BaseModel):
    """Create role response."""

    id: str = Field(..., description="Role ID (UUID)")
    role_name: str = Field(..., description="Role name")
    permissions: list[str] = Field(..., description="Role permissions")
    description: str | None = Field(
        default=None, description="Role description"
    )


class GetRoleRequest(BaseModel):
    """Get role request by ID."""

    role_id: str = Field(..., description="Role ID (UUID)")


class GetRoleResponse(BaseModel):
    """Get role response."""

    id: str = Field(..., description="Role ID (UUID)")
    role_name: str = Field(..., description="Role name")
    permissions: list[str] = Field(..., description="Role permissions")
    description: str | None = Field(
        default=None, description="Role description"
    )


class GetRolesRequest(BaseModel):
    """Get roles request with optional filtering."""

    filters: dict | None = Field(
        default=None,
        description="Filter conditions dict, e.g. {'role_name': 'admin'}",
    )


class UpdateRoleRequest(BaseModel):
    """Update role request by ID."""

    role_id: str = Field(..., description="Role ID (UUID)")
    permissions: list[str] | None = Field(
        default=None, description="Role permissions"
    )
    description: str | None = Field(
        default=None, description="Role description"
    )


class UpdateRoleResponse(BaseModel):
    """Update role response."""

    role_name: str = Field(..., description="Role name")
    permissions: list[str] = Field(..., description="Role permissions")
    description: str = Field(..., description="Role description")


class DeleteRoleRequest(BaseModel):
    """Delete role request by ID."""

    role_id: str = Field(..., description="Role ID (UUID)")


class DeleteRoleResponse(BaseModel):
    """Delete role response."""

    role_name: str = Field(..., description="Role name")


class ClearLoginLogsRequest(BaseModel):
    """Clear login logs request."""

    user_id: str | None = Field(
        default=None, description="Clear logs for specific user ID (UUID)"
    )
    user_name: str | None = Field(
        default=None, description="Clear logs for specific user name"
    )

    @model_validator(mode="after")
    def validate_user_filter(self):
        """Ensure user_id and user_name are mutually exclusive."""
        if self.user_id is not None and self.user_name is not None:
            raise ValueError(
                "Cannot specify both user_id and user_name. "
                "Please provide only one."
            )
        return self
