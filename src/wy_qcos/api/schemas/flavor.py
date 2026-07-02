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

from pydantic import BaseModel, Field, ConfigDict

from .base import UuidMixin


class CreateFlavorRequest(BaseModel):
    """Create Flavor Request."""

    name: str = Field(description="Flavor name")
    description: str | None = Field(default=None, description="Description")
    is_public: bool = Field(default=True, description="Is public flavor")
    specs: dict = Field(default_factory=dict, description="Flavor specs")


class FlavorResponse(UuidMixin):
    """Flavor Response."""

    _uuid_fields = ["id"]
    _uuid_convert_mode = "to_uuid"

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Flavor ID")
    name: str = Field(description="Flavor name")
    description: str | None = Field(default=None, description="Description")
    is_public: bool = Field(default=True, description="Is public flavor")
    specs: dict = Field(default_factory=dict, description="Flavor specs")
    created_at: datetime | None = Field(default=None, description="Created at")
    updated_at: datetime | None = Field(default=None, description="Updated at")


class GetFlavorRequest(BaseModel):
    """Get Flavor Request."""

    flavor_id: UUID = Field(description="Flavor ID")


class DeleteFlavorRequest(BaseModel):
    """Delete Flavor Request."""

    flavor_id: UUID = Field(description="Flavor ID")


class DeleteFlavorResponse(UuidMixin):
    """Delete Flavor Response."""

    _uuid_fields = ["flavor_id"]

    model_config = ConfigDict(from_attributes=True)

    flavor_id: UUID = Field(description="Flavor ID")
