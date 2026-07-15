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
    project_id: UUID | None = Field(
        default=None,
        description=(
            "Project ID (optional, defaults to current user's project)"
        ),
    )
    description: str | None = Field(default=None, description="Description")
    is_public: bool = Field(default=True, description="Is public flavor")
    min_qubits: int | None = Field(default=None, description="Minimum qubits")
    max_qubits: int | None = Field(default=None, description="Maximum qubits")
    gate_fidelity_1q_min: float | None = Field(
        default=None, description="Min 1q gate fidelity"
    )
    gate_fidelity_2q_min: float | None = Field(
        default=None, description="Min 2q gate fidelity"
    )
    extra_properties: dict | None = Field(
        default=None,
        description="Extra properties (merged from --property key=value)",
    )
    device_groups: list[UUID] = Field(
        description="Device group IDs (at least one required)",
    )


class FlavorResponse(UuidMixin):
    """Flavor Response."""

    _uuid_fields = ["id", "project_id"]
    _uuid_convert_mode = "to_uuid"

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Flavor ID")
    project_id: UUID = Field(description="Project ID")
    name: str = Field(description="Flavor name")
    description: str | None = Field(default=None, description="Description")
    is_public: bool = Field(default=True, description="Is public flavor")
    min_qubits: int | None = Field(default=None, description="Minimum qubits")
    max_qubits: int | None = Field(default=None, description="Maximum qubits")
    gate_fidelity_1q_min: float | None = Field(
        default=None, description="Min 1q gate fidelity"
    )
    gate_fidelity_2q_min: float | None = Field(
        default=None, description="Min 2q gate fidelity"
    )
    extra_properties: dict | None = Field(
        default=None, description="Extra properties"
    )
    device_groups: list[UUID] = Field(
        default_factory=list,
        description="Device group IDs",
    )
    created_at: datetime | None = Field(default=None, description="Created at")
    updated_at: datetime | None = Field(default=None, description="Updated at")


class GetFlavorRequest(BaseModel):
    """Get Flavor Request."""

    flavor_id: UUID = Field(description="Flavor ID")


class GetFlavorsRequest(BaseModel):
    """Get Flavors Request with optional filtering."""

    filters: dict | None = Field(
        default=None,
        description=(
            "Filter conditions. Supported keys: "
            "'flavor_name' (exact match), "
            "'flavor_ids' (list of UUIDs, DB-level IN query)"
        ),
    )


class UpdateFlavorRequest(BaseModel):
    """Update Flavor Request."""

    flavor_id: UUID = Field(description="Flavor ID")
    project_id: UUID | None = Field(default=None, description="Project ID")
    name: str | None = Field(default=None, description="Flavor name")
    description: str | None = Field(default=None, description="Description")
    is_public: bool | None = Field(
        default=None, description="Is public flavor"
    )
    min_qubits: int | None = Field(default=None, description="Minimum qubits")
    max_qubits: int | None = Field(default=None, description="Maximum qubits")
    gate_fidelity_1q_min: float | None = Field(
        default=None, description="Min 1q gate fidelity"
    )
    gate_fidelity_2q_min: float | None = Field(
        default=None, description="Min 2q gate fidelity"
    )
    extra_properties: dict | None = Field(
        default=None,
        description="Extra properties to merge into existing extra_properties",
    )
    device_groups: list[UUID] | None = Field(
        default=None,
        description="Device group IDs. If provided, replaces existing "
        "device group mappings. If None, keeps existing mappings.",
    )


class DeleteFlavorsRequest(BaseModel):
    """Delete Flavors Request (batch)."""

    flavor_ids: list[UUID] = Field(description="Flavor IDs to delete")


class DeleteFlavorResponseItem(UuidMixin):
    """Delete Flavor Response Item (per-flavor result)."""

    _uuid_fields = ["flavor_id"]

    model_config = ConfigDict(from_attributes=True)

    flavor_id: UUID = Field(description="Flavor ID")
    success: bool = Field(description="Whether deletion succeeded")
    error: str | None = Field(
        default=None, description="Error message if deletion failed"
    )


class DeleteFlavorsResponse(BaseModel):
    """Delete Flavors Response (batch results)."""

    results: list[DeleteFlavorResponseItem] = Field(
        default_factory=list,
        description="Per-flavor deletion results",
    )
