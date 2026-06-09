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

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    model_validator,
    field_serializer,
)

from wy_qcos.common.constant import Constant


class SubmitJobRequest(BaseModel):
    """Submit Job Request.

    Pydantic Model for Submit Job Request.
    """

    # Project ID (optional, from auth_data)
    project_id: UUID | None = Field(default=None, description="Project ID")
    # User ID (optional, from auth_data)
    user_id: UUID | None = Field(default=None, description="User ID")
    # Code types: qasm, qasm2, qasm3, qubo
    code_type: str = Field(
        default=Constant.CODE_TYPE_QASM,
        description="Code types: qasm, qasm2, qasm3, qubo",
    )
    # Source code list
    source_code: list = Field(default=[], description="Source code list")
    # description
    description: str | None = Field(
        default=None, description="Job description"
    )
    # device name
    backend: str = Field(
        default=Constant.DRIVER_DUMMY, description="Backend device name"
    )
    # Driver options
    driver_options: dict | None = Field(
        default=None, description="Driver options"
    )
    # Transpiler
    transpiler: str | None = Field(default=None, description="Transpiler")
    # Transpiler options
    transpiler_options: dict | None = Field(
        default=None, description="Transpiler options"
    )
    # Circuit aggregation: internal multi
    circuit_aggregation: str | None = Field(
        default=None, description="Circuit aggregation: internal, multi"
    )
    # QEC options
    qec_options: dict | None = Field(
        default=None, description="QEC (Quantum Error Correction) options"
    )
    # Job ID
    job_id: UUID | None = Field(default=None, description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Job type
    job_type: str = Field(
        default=Constant.JOB_TYPE_SAMPLING, description="Job type"
    )
    # Job status
    job_status: str | None = Field(default=None, description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        ge=Constant.MIN_JOB_PRIORITY,
        le=Constant.MAX_JOB_PRIORITY,
        description="Job priority. range: 1-10, Default: 5. "
        "Highest priority: 1, Lowest Priority: 10",
    )
    # Profiling
    profiling: list | None = Field(default=None, description="Profiling")
    # Shots
    shots: int = Field(default=Constant.DEFAULT_SHOTS, description="Shots")
    # Callbacks
    callbacks: list | None = Field(default=None, description="Callbacks")
    # Dry-run
    dry_run: bool = Field(default=False, description="Dry-run flag")
    # Code compression level
    code_compression_level: int = Field(
        default=Constant.DEFAULT_CODE_COMPRESSION_LEVEL,
        ge=Constant.MIN_CODE_COMPRESSION_LEVEL,
        le=Constant.MAX_CODE_COMPRESSION_LEVEL,
        description="Code compression level. range: 0-9, Default: 0. "
        "Max compression level: 9, Min compression level: 1, "
        "No compression: 0",
    )
    # Tags
    tags: list | None = Field(default=None, description="Tags list")
    # Creation date
    created_at: datetime | None = Field(
        default=None, description="Creation date"
    )
    # Updated date
    updated_at: datetime | None = Field(
        default=None, description="Updated date"
    )

    # ...existing code...

    @model_validator(mode="before")
    @classmethod
    def convert_uuid_strings(cls, data):
        """Convert UUID string fields to UUID objects."""
        if isinstance(data, dict):
            for field_name in ["job_id", "project_id", "user_id"]:
                if field_name in data and data[field_name] is not None:
                    value = data[field_name]
                    if isinstance(value, str):
                        try:
                            data[field_name] = UUID(value)
                        except (ValueError, TypeError):
                            pass
        return data

    @field_serializer("job_id", "project_id", "user_id", when_used="json")
    def serialize_uuids(self, value) -> str | None:
        """Serialize UUID to string for JSON output."""
        if isinstance(value, UUID):
            return str(value)
        return value


class SubmitJobResponse(BaseModel):
    """Submit Job Response.

    Pydantic Model for Submit Job Response.
    """

    model_config = ConfigDict(from_attributes=True)

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Project ID
    project_id: UUID | None = Field(default=None, description="Project ID")
    # User ID
    user_id: UUID | None = Field(default=None, description="User ID")
    # Job type
    job_type: str = Field(description="Job type")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Highest priority: 1, Lowest Priority: 10",
    )
    # Code type
    code_type: str = Field(description="Code type")
    # Source code list
    source_code: list = Field(description="Source code list")
    # Description
    description: str | None = Field(default=None, description="Description")
    # Backend device name
    backend: str = Field(description="Backend device name")
    # Driver options
    driver_options: dict | None = Field(
        default=None, description="Driver options"
    )
    # Transpiler
    transpiler: str | None = Field(default=None, description="Transpiler")
    # Transpiler options
    transpiler_options: dict | None = Field(
        default=None, description="Transpiler options"
    )
    # Circuit aggregation: internal, multi
    circuit_aggregation: str | None = Field(
        default=None, description="Circuit aggregation: internal, multi"
    )
    # QEC options
    qec_options: dict | None = Field(
        default=None, description="QEC (Quantum Error Correction) options"
    )
    # Profiling
    profiling: list | None = Field(default=None, description="Profiling")
    # Shots
    shots: int = Field(description="Shots")
    # Callbacks
    callbacks: list | None = Field(default=None, description="Callbacks")
    # Dry-run flag
    dry_run: bool = Field(default=False, description="Dry-run flag")
    # Code compression level
    code_compression_level: int = Field(
        default=0, ge=0, le=9, description="Code compression level, range 0-9"
    )
    # Tags
    tags: list | None = Field(default=None, description="Tags list")
    # Created at
    created_at: datetime | None = Field(default=None, description="Created at")
    # Updated at
    updated_at: datetime | None = Field(default=None, description="Updated at")
    # Started at
    started_at: datetime | None = Field(default=None, description="Started at")
    # Ended at
    ended_at: datetime | None = Field(default=None, description="Ended at")

    @model_validator(mode="before")
    @classmethod
    def convert_uuid_strings(cls, data):
        """Convert UUID string fields to UUID objects."""
        if isinstance(data, dict):
            for field_name in ["job_id", "project_id", "user_id"]:
                if field_name in data and data[field_name] is not None:
                    value = data[field_name]
                    if isinstance(value, str):
                        try:
                            data[field_name] = UUID(value)
                        except (ValueError, TypeError):
                            pass
        return data

    @field_serializer("job_id", "project_id", "user_id", when_used="json")
    def serialize_uuids(self, value) -> str | None:
        """Serialize UUID to string for JSON output."""
        if isinstance(value, UUID):
            return str(value)
        return value


class GetJobStatusRequest(BaseModel):
    """Get Job Status Request.

    Pydantic Model for Get Job Status Request.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")


class GetJobStatusResponse(BaseModel):
    """Get Job Status Response.

    Pydantic Model for Get Job Status Response.
    """

    model_config = ConfigDict(from_attributes=True)

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Project ID
    project_id: UUID | None = Field(default=None, description="Project ID")
    # User ID
    user_id: UUID | None = Field(default=None, description="User ID")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Highest priority: 1, Lowest Priority: 10",
    )
    # Description
    description: str | None = Field(default=None, description="Description")
    # Backend device name
    backend: str = Field(description="Backend device name")
    # Driver options
    driver_options: dict | None = Field(
        default=None, description="Driver options"
    )
    # Transpiler
    transpiler: str | None = Field(default=None, description="Transpiler")
    # Transpiler options
    transpiler_options: dict | None = Field(
        default=None, description="Transpiler options"
    )
    # Circuit aggregation: internal, multi
    circuit_aggregation: str | None = Field(
        default=None, description="Circuit aggregation: internal, multi"
    )
    # QEC options
    qec_options: dict | None = Field(
        default=None, description="QEC (Quantum Error Correction) options"
    )
    # Shots
    shots: int = Field(description="Shots")
    # Dry-run
    dry_run: bool = Field(description="Dry-run flag")
    # Code compression level
    code_compression_level: int = Field(
        default=0, ge=0, le=9, description="Code compression level, range 0-9"
    )
    # Tags
    tags: list | None = Field(default=None, description="Tags list")
    # Progress
    progress: int | None = Field(default=-1, description="Progress")
    # Creation date
    created_at: datetime = Field(description="Creation date")
    # Updated date
    updated_at: datetime | None = Field(
        default=None, description="Updated date"
    )
    # Started date
    started_at: datetime | None = Field(
        default=None, description="Started date"
    )
    # Ended date
    ended_at: datetime | None = Field(default=None, description="Ended date")

    @model_validator(mode="before")
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID objects to strings."""
        if isinstance(data, dict):
            for field in ["job_id", "project_id", "user_id"]:
                if field in data and isinstance(data[field], UUID):
                    data[field] = str(data[field])
        return data

    @field_serializer("job_id", "project_id", "user_id", when_used="json")
    def serialize_uuids(self, value) -> str | None:
        """Serialize UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value


class GetJobResultsRequest(BaseModel):
    """Get Job Results Request.

    Pydantic Model for Get Job Results Request.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")


class GetJobResultsResponse(BaseModel):
    """Get Job Results Response.

    Pydantic Model for Get Job Results Response.
    """

    model_config = ConfigDict(from_attributes=True)

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Project ID
    project_id: UUID | None = Field(default=None, description="Project ID")
    # User ID
    user_id: UUID | None = Field(default=None, description="User ID")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Highest priority: 1, Lowest Priority: 10",
    )
    # Code type
    code_type: str = Field(description="Code type")
    # Description
    description: str | None = Field(default=None, description="Description")
    # Source code list
    source_code: list = Field(description="Source code list")
    # Backend device name
    backend: str = Field(description="Backend device name")
    # Driver options
    driver_options: dict | None = Field(
        default=None, description="Driver options"
    )
    # Transpiler
    transpiler: str | None = Field(default=None, description="Transpiler")
    # Transpiler options
    transpiler_options: dict | None = Field(
        default=None, description="Transpiler options"
    )
    # Circuit aggregation: internal, multi
    circuit_aggregation: str | None = Field(
        default=None, description="Circuit aggregation: internal, multi"
    )
    # QEC options
    qec_options: dict | None = Field(
        default=None, description="QEC (Quantum Error Correction) options"
    )
    # Shots
    shots: int = Field(description="Shots")
    # Dry-run
    dry_run: bool = Field(description="Dry-run flag")
    # Progress
    progress: int | None = Field(default=-1, description="Progress")
    # Results
    results: str | int | list | dict | None = Field(
        default=None, description="Results"
    )
    # Creation date
    created_at: datetime = Field(description="Creation date")
    # Updated date
    updated_at: datetime | None = Field(
        default=None, description="Updated date"
    )
    # Started date
    started_at: datetime | None = Field(
        default=None, description="Started date"
    )
    # Ended date
    ended_at: datetime | None = Field(default=None, description="Ended date")

    @model_validator(mode="before")
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID objects to strings."""
        if isinstance(data, dict):
            for field in ["job_id", "project_id", "user_id"]:
                if field in data and isinstance(data[field], UUID):
                    data[field] = str(data[field])
        return data

    @field_serializer("job_id", "project_id", "user_id", when_used="json")
    def serialize_uuids(self, value) -> str | None:
        """Serialize UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value


class GetJobsRequest(BaseModel):
    """Get Jobs Request.

    Pydantic Model for Get Jobs Request.
    """


class CancelJobsRequest(BaseModel):
    """Cancel Jobs Request.

    Pydantic Model for Cancel Jobs Request.
    """

    # Job IDs
    job_ids: list[UUID] = Field(description="Job IDs to cancel")


class CancelJobsResponse(BaseModel):
    """Cancel Jobs Response.

    Pydantic Model for Cancel Jobs Response.
    """

    model_config = ConfigDict(from_attributes=True)

    # Job ID
    job_id: UUID = Field(description="Job ID")

    @model_validator(mode="before")
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID objects to strings."""
        if isinstance(data, dict):
            if "job_id" in data and isinstance(data["job_id"], UUID):
                data["job_id"] = str(data["job_id"])
        return data

    @field_serializer("job_id", when_used="json")
    def serialize_uuid(self, value) -> str:
        """Serialize UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value


class DeleteJobsRequest(BaseModel):
    """Delete Jobs Request.

    Pydantic Model for Delete Jobs Request.
    """

    # Job IDs
    job_ids: list[UUID] = Field(description="Job IDs to delete")
    # Force delete flag
    force: bool = Field(
        default=False, description="Force delete jobs regardless of status"
    )


class DeleteJobsResponse(BaseModel):
    """Delete Jobs Response.

    Pydantic Model for Delete Jobs Response.
    """

    model_config = ConfigDict(from_attributes=True)

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job status
    job_status: str = Field(description="Job status")

    @model_validator(mode="before")
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID objects to strings."""
        if isinstance(data, dict):
            if "job_id" in data and isinstance(data["job_id"], UUID):
                data["job_id"] = str(data["job_id"])
        return data

    @field_serializer("job_id", when_used="json")
    def serialize_uuid(self, value) -> str:
        """Serialize UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value


class SetJobResultsRequest(BaseModel):
    """Set Job Results Request.

    Pydantic Model for Set Job Results Request.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Results
    results: list = Field(description="Job results")
    # Job status
    job_status: str = Field(default="COMPLETED", description="Job status")
    # Started date
    started_at: datetime | None = Field(
        default=None, description="Started date"
    )
    # Ended date
    ended_at: datetime | None = Field(default=None, description="Ended date")
    # Errors
    errors: str | int | list | dict | None = Field(
        default=None, description="Errors"
    )


class SetJobResultsResponse(BaseModel):
    """Set Job Results Response.

    Pydantic Model for Set Job Results Response.
    """

    model_config = ConfigDict(from_attributes=True)

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # QC driver name
    backend: str = Field(description="Backend device name")
    # Job status
    job_status: str = Field(description="Job status")

    @model_validator(mode="before")
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID objects to strings."""
        if isinstance(data, dict):
            if "job_id" in data and isinstance(data["job_id"], UUID):
                data["job_id"] = str(data["job_id"])
        return data

    @field_serializer("job_id", when_used="json")
    def serialize_uuid(self, value) -> str:
        """Serialize UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value


class UpdateJobRequest(BaseModel):
    """Update Job Request.

    Pydantic Model for Update Job Request.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Job description
    description: str | None = Field(
        default=None, description="Job description"
    )
    # Job priority
    job_priority: int | None = Field(
        default=None,
        description="Job priority. Values: 1-10, Default: 5. "
        "Highest priority: 1, Lowest Priority: 10",
    )


class UpdateJobResponse(BaseModel):
    """Update Job Response.

    Pydantic Model for Update Job Response.
    """

    model_config = ConfigDict(from_attributes=True)

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Project ID
    project_id: UUID | None = Field(default=None, description="Project ID")
    # User ID
    user_id: UUID | None = Field(default=None, description="User ID")
    # Job type
    job_type: str = Field(description="Job type")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Highest priority: 1, Lowest Priority: 10",
    )
    # Code type
    code_type: str = Field(description="Code type")
    # Source code list
    source_code: list = Field(description="Source code list")
    # Description
    description: str | None = Field(default=None, description="Description")
    # Backend device name
    backend: str = Field(description="Backend device name")
    # Driver options
    driver_options: dict | None = Field(
        default=None, description="Driver options"
    )
    # Transpiler
    transpiler: str | None = Field(default=None, description="Transpiler")
    # Transpiler options
    transpiler_options: dict | None = Field(
        default=None, description="Transpiler options"
    )
    # Circuit aggregation: internal, multi
    circuit_aggregation: str | None = Field(
        default=None, description="Circuit aggregation: internal, multi"
    )
    # QEC options
    qec_options: dict | None = Field(
        default=None, description="QEC (Quantum Error Correction) options"
    )
    # Shots
    shots: int = Field(description="Shots")
    # Profiling
    profiling: list | None = Field(default=None, description="Profiling")
    # Dry-run
    dry_run: bool = Field(description="Dry-run flag")
    # Callbacks
    callbacks: list | None = Field(default=None, description="Callbacks")
    # Creation date
    created_at: datetime = Field(description="Creation date")
    # Updated date
    updated_at: datetime | None = Field(
        default=None, description="Updated date"
    )
    # Started date
    started_at: datetime | None = Field(
        default=None, description="Started date"
    )
    # Ended date
    ended_at: datetime | None = Field(default=None, description="Ended date")

    @model_validator(mode="before")
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID objects to strings."""
        if isinstance(data, dict):
            for field in ["job_id", "project_id", "user_id"]:
                if field in data and isinstance(data[field], UUID):
                    data[field] = str(data[field])
        return data

    @field_serializer("job_id", "project_id", "user_id", when_used="json")
    def serialize_uuids(self, value) -> str | None:
        """Serialize UUID objects to strings."""
        if isinstance(value, UUID):
            return str(value)
        return value
