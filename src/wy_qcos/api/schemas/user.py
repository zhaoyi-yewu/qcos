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

from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from fastapi_users import schemas as fastapi_users_schemas


# FastAPI-Users compatible models
class UserRead(fastapi_users_schemas.BaseUser[int]):
    """User read schema."""

    user_name: str = Field(..., description="User name")
    roles: list[str] = Field(default=[], description="User roles")
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
        default=None, description="User description"
    )
    created_at: str = Field(..., description="User creation timestamp")
    updated_at: str = Field(..., description="User last updated timestamp")


class UserCreate(fastapi_users_schemas.BaseUserCreate):
    """User create schema."""

    user_name: str = Field(
        ..., min_length=3, max_length=50, description="User name"
    )
    roles: list[str] = Field(default=["user"], description="User roles")
    is_locked: bool = Field(default=False, description="Is user locked")
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days"
    )
    description: str | None = Field(
        default=None, description="User description"
    )


class UserUpdate(fastapi_users_schemas.BaseUserUpdate):
    """User update schema."""

    user_name: str | None = Field(
        default=None, min_length=3, max_length=50, description="User name"
    )
    roles: list[str] | None = Field(default=None, description="User roles")
    is_locked: bool | None = Field(default=None, description="Is user locked")
    password_expiry_days: int | None = Field(
        default=None, description="Password expiry days"
    )
    description: str | None = Field(
        default=None, description="User description"
    )


# Internal models for routes_jsonrpc/user.py
class User(BaseModel):
    """User model."""

    user_name: str = Field(..., description="User name")
    password_hash: str = Field(
        ...,
        description="Password hash",
        json_schema_extra={"is_sensitive": True},
    )
    roles: list[str] = Field(default=[], description="User roles")
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


class GetUserManagementStatusRequest(BaseModel):
    """Get user management status request."""


class GetUserManagementStatusResponse(BaseModel):
    """Get user management status response."""

    enabled: bool = Field(
        ..., description="Whether user management is enabled"
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


class CreateUserRequest(BaseModel):
    """Create user request."""

    user_name: str = Field(
        ..., min_length=3, max_length=50, description="User name"
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Password",
        json_schema_extra={"is_sensitive": True},
    )
    roles: list[str] = Field(default=["user"], description="User roles")
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

    @field_validator("user_name")
    @classmethod
    def validate_user_name(cls, v):
        if not v.isalnum():
            raise ValueError("User name must be alphanumeric")
        return v


class CreateUserResponse(BaseModel):
    """Create user response."""

    user_name: str = Field(..., description="User name")
    roles: list[str] | None = Field(..., description="User roles")
    is_enabled: bool | None = Field(..., description="Whether user is enabled")
    is_locked: bool | None = Field(..., description="Whether user is locked")
    created_at: str | None = Field(..., description="Creation timestamp")


class GetUserRequest(BaseModel):
    """Get user request."""

    user_name: str = Field(..., description="User name")


class GetUserResponse(BaseModel):
    """Get user response."""

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
    """Get users request."""


class UpdateUserRequest(BaseModel):
    """Update user request."""

    user_name: str = Field(..., description="User name")
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


class UpdateUserResponse(BaseModel):
    """Update user response."""

    user_name: str = Field(..., description="User name")
    roles: list[str] = Field(..., description="User roles")
    is_enabled: bool = Field(..., description="Whether user is enabled")
    is_locked: bool = Field(..., description="Whether user is locked")
    description: str | None = Field(
        default=None, description="User description"
    )
    updated_at: str = Field(..., description="Update timestamp")


class DeleteUserRequest(BaseModel):
    """Delete user request."""

    user_name: str = Field(..., description="User name")


class DeleteUserResponse(BaseModel):
    """Delete user response."""

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
    """Change password request."""

    user_name: str = Field(..., description="User name")
    old_password: str | None = Field(
        default=None,
        description="Old password (for non-admin changes)",
        json_schema_extra={"is_sensitive": True},
    )
    new_password: str = Field(
        ...,
        min_length=6,
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
    login_status: str = Field(
        ..., description="Login status: success or failed"
    )
    user_agent: str | None = Field(default=None, description="User agent")


class GetLoginLogsRequest(BaseModel):
    """Get login logs request."""

    user_name: str | None = Field(
        default=None, description="Filter by user name"
    )
    start_time: str | None = Field(
        default=None, description="Filter by start time (ISO format)"
    )
    end_time: str | None = Field(
        default=None, description="Filter by end time (ISO format)"
    )


class LoginLogResponse(BaseModel):
    """Login log response."""

    user_name: str = Field(..., description="User name")
    login_time: str = Field(..., description="Login timestamp")
    ip_address: str = Field(..., description="IP address")
    user_agent: str | None = Field(default=None, description="User agent")
    success: bool = Field(..., description="Whether login was successful")
    failure_reason: str | None = Field(
        default=None, description="Failure reason if login failed"
    )


class Role(BaseModel):
    """Role model."""

    role_name: str = Field(..., description="Role name")
    permissions: list[str] = Field(default=[], description="Role permissions")
    description: str | None = Field(
        default=None, description="Role description"
    )


class CreateRoleRequest(BaseModel):
    """Create role request."""

    role_name: str = Field(
        ..., min_length=2, max_length=50, description="Role name"
    )
    permissions: list[str] = Field(default=[], description="Role permissions")
    description: str = Field(
        default="", max_length=200, description="Role description"
    )

    @field_validator("role_name")
    @classmethod
    def validate_role_name(cls, v):
        if not v.isalnum():
            raise ValueError("Role name must be alphanumeric")
        return v


class CreateRoleResponse(BaseModel):
    """Create role response."""

    role_name: str = Field(..., description="Role name")
    permissions: list[str] = Field(..., description="Role permissions")
    description: str = Field(..., description="Role description")


class GetRoleRequest(BaseModel):
    """Get role request."""

    role_name: str = Field(..., description="Role name")


class GetRoleResponse(BaseModel):
    """Get role response."""

    role_name: str = Field(..., description="Role name")
    permissions: list[str] = Field(..., description="Role permissions")
    description: str = Field(..., description="Role description")


class GetRolesRequest(BaseModel):
    """Get roles request."""


class UpdateRoleRequest(BaseModel):
    """Update role request."""

    role_name: str = Field(..., description="Role name")
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
    """Delete role request."""

    role_name: str = Field(..., description="Role name")


class DeleteRoleResponse(BaseModel):
    """Delete role response."""

    role_name: str = Field(..., description="Role name")
