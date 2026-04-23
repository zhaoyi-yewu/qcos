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

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username for authentication",
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Password for authentication",
        json_schema_extra={"is_sensitive": True},
    )


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(
        ..., description="Access token expiration time in seconds"
    )
    refresh_expires_in: int = Field(
        ..., description="Refresh token expiration time in seconds"
    )


class LogoutRequest(BaseModel):
    """Logout request schema."""

    pass


class LogoutResponse(BaseModel):
    """Logout response schema."""

    message: str = Field(..., description="Logout confirmation message")


class TokenRefreshRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        json_schema_extra={"is_sensitive": True},
    )


class TokenRefreshResponse(BaseModel):
    """Token refresh response schema."""

    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(
        ..., description="Access token expiration time in seconds"
    )
    refresh_expires_in: int = Field(
        ..., description="Refresh token expiration time in seconds"
    )
