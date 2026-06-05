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

from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_serializer,
)

from wy_qcos.common.constant import Constant


class CreateProjectRequest(BaseModel):
    """Create project request schema."""

    project_name: str = Field(
        ...,
        min_length=Constant.MIN_PROJECT_LENGTH,
        max_length=Constant.MAX_PROJECT_LENGTH,
        description="Project name",
    )
    description: str | None = Field(
        default=None,
        max_length=Constant.MAX_DESCRIPTION_LENGTH,
        description="Project description",
    )


class CreateProjectResponse(BaseModel):
    """Create project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Project ID (UUID)")
    name: str = Field(..., description="Project name")
    description: str | None = Field(
        default=None, description="Project description"
    )
    created_at: str = Field(..., description="Project creation timestamp")
    updated_at: str = Field(..., description="Project last updated timestamp")

    @field_serializer("id", when_used="json")
    def serialize_id(self, value) -> str:
        """Serialize UUID to string."""
        if isinstance(value, UUID):
            return str(value)
        return value


class UpdateProjectRequest(BaseModel):
    """Update project request schema."""

    project_id: UUID = Field(..., description="Project ID (UUID)")
    project_name: str | None = Field(
        default=None,
        min_length=Constant.MIN_PROJECT_LENGTH,
        max_length=Constant.MAX_PROJECT_LENGTH,
        description="Project name",
    )
    description: str | None = Field(
        default=None,
        max_length=Constant.MAX_DESCRIPTION_LENGTH,
        description="Project description",
    )


class UpdateProjectResponse(BaseModel):
    """Update project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Project ID (UUID)")
    name: str = Field(..., description="Project name")
    description: str | None = Field(
        default=None, description="Project description"
    )
    created_at: str = Field(..., description="Project creation timestamp")
    updated_at: str = Field(..., description="Project last updated timestamp")

    @field_serializer("id", when_used="json")
    def serialize_id(self, value) -> str:
        """Serialize UUID to string."""
        if isinstance(value, UUID):
            return str(value)
        return value


class GetProjectRequest(BaseModel):
    """Get project request schema."""

    project_id: UUID = Field(..., description="Project ID (UUID)")


class GetProjectResponse(BaseModel):
    """Get project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Project ID (UUID)")
    name: str = Field(..., description="Project name")
    description: str | None = Field(
        default=None, description="Project description"
    )
    created_at: str = Field(..., description="Project creation timestamp")
    updated_at: str = Field(..., description="Project last updated timestamp")

    @field_serializer("id", when_used="json")
    def serialize_id(self, value) -> str:
        """Serialize UUID to string."""
        if isinstance(value, UUID):
            return str(value)
        return value


class GetProjectsRequest(BaseModel):
    """Get projects request schema."""

    filters: dict[str, Any] | None = Field(
        default=None, description="Filter conditions"
    )


class DeleteProjectRequest(BaseModel):
    """Delete project request schema."""

    project_id: UUID = Field(..., description="Project ID (UUID)")


class DeleteProjectResponse(BaseModel):
    """Delete project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Deleted project ID (UUID)")
    name: str = Field(..., description="Deleted project name")
    deleted_at: str = Field(..., description="Deletion timestamp")

    @field_serializer("id", when_used="json")
    def serialize_id(self, value) -> str:
        """Serialize UUID to string."""
        if isinstance(value, UUID):
            return str(value)
        return value


class GetProjectsResponse(BaseModel):
    """Get projects response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Project ID (UUID)")
    name: str = Field(..., description="Project name")
    description: str | None = Field(
        default=None, description="Project description"
    )
    created_at: str = Field(..., description="Project creation timestamp")
    updated_at: str = Field(..., description="Project last updated timestamp")

    @field_serializer("id", when_used="json")
    def serialize_id(self, value) -> str:
        """Serialize UUID to string."""
        if isinstance(value, UUID):
            return str(value)
        return value
