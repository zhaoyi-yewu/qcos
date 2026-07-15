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
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .base import UuidMixin


class CreateDeviceGroupRequest(BaseModel):
    """Create Device Group Request."""

    name: str = Field(description="Device group name")
    project_id: UUID | None = Field(
        default=None,
        description=(
            "Project ID (optional, defaults to current user's project)"
        ),
    )
    description: str | None = Field(default=None, description="Description")
    device_names: list[str] = Field(
        description="List of device names in this group (required)",
    )
    is_public: bool = Field(default=True, description="Is public group")


class UpdateDeviceGroupRequest(BaseModel):
    """Update Device Group Request."""

    group_id: UUID = Field(description="Device group ID")
    project_id: UUID | None = Field(default=None, description="Project ID")
    name: str | None = Field(default=None, description="Device group name")
    description: str | None = Field(default=None, description="Description")
    device_names: list[str] | None = Field(
        default=None,
        description="List of device names in this group",
    )
    is_public: bool | None = Field(default=None, description="Is public group")


class GetDeviceGroupRequest(BaseModel):
    """Get Device Group Request."""

    group_id: UUID = Field(description="Device group ID")


class GetDeviceGroupsRequest(BaseModel):
    """Get Device Groups Request with optional filtering."""

    filters: dict | None = Field(
        default=None,
        description=(
            "Filter conditions. Supported keys: "
            "'group_name' (exact match), "
            "'group_ids' (list of UUIDs, DB-level IN query)"
        ),
    )


class DeleteDeviceGroupsRequest(BaseModel):
    """Delete Device Groups Request (batch)."""

    group_ids: list[UUID] = Field(description="Device group IDs to delete")


class DeviceGroupResponse(UuidMixin):
    """Device Group Response."""

    _uuid_fields = ["id", "project_id"]
    _uuid_convert_mode = "to_uuid"

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Device group ID")
    project_id: UUID = Field(description="Project ID")
    name: str = Field(description="Device group name")
    description: str | None = Field(default=None, description="Description")
    device_names: list[str] | None = Field(
        default=None, description="Device names in this group"
    )
    is_public: bool = Field(default=True, description="Is public group")
    created_at: datetime | None = Field(default=None, description="Created at")
    updated_at: datetime | None = Field(default=None, description="Updated at")


class DeleteDeviceGroupResponseItem(UuidMixin):
    """Delete Device Group Response Item (per-group result)."""

    _uuid_fields = ["group_id"]

    model_config = ConfigDict(from_attributes=True)

    group_id: UUID = Field(description="Device group ID")
    success: bool = Field(description="Whether deletion succeeded")
    error: str | None = Field(
        default=None, description="Error message if deletion failed"
    )


class DeleteDeviceGroupsResponse(BaseModel):
    """Delete Device Groups Response (batch results)."""

    results: list[DeleteDeviceGroupResponseItem] = Field(
        default_factory=list,
        description="Per-group deletion results",
    )
