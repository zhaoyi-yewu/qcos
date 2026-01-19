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

from pydantic import BaseModel, Field

from wy_qcos.common.constant import Constant


class SubmitJobRequest(BaseModel):
    """Submit Job Request.

    Pydantic Model for Submit Job Request.
    """

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
    # Job ID
    job_id: UUID | None = Field(default=None, description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Job type
    job_type: str = Field(
        default=Constant.JOB_TYPE_SAMPLING, description="Job type"
    )
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Higest priority: 1, Lowest Priority: 10",
    )
    # Profiling
    profiling: list | None = Field(default=None, description="Profiling")
    # Shots
    shots: int = Field(default=Constant.DEFAULT_SHOTS, description="Shots")
    # Callbacks
    callbacks: list | None = Field(default=None, description="Callbacks")
    # Dry-run
    dry_run: bool = Field(default=False, description="Dry-run flag")
    # Creation date
    creation_date: datetime | None = Field(
        default=None, description="Creation date"
    )


class SubmitJobResponse(BaseModel):
    """Submit Job Response.

    Pydantic Model for Submit Job Response.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Job type
    job_type: str = Field(description="Job type")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Higest priority: 1, Lowest Priority: 10",
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
    # Shots
    shots: int = Field(description="Shots")
    # Profiling
    profiling: list | None = Field(default=None, description="Profiling")
    # Dry-run
    dry_run: bool = Field(description="Dry-run flag")
    # Callbacks
    callbacks: list | None = Field(default=None, description="Callbacks")
    # Creation date
    creation_date: datetime = Field(description="Creation date")
    # End date
    end_date: datetime | None = Field(default=None, description="End date")


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

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Higest priority: 1, Lowest Priority: 10",
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
    # Shots
    shots: int = Field(description="Shots")
    # Dry-run
    dry_run: bool = Field(description="Dry-run flag")
    # Progress
    progress: int | None = Field(default=-1, description="Progress")
    # Creation date
    creation_date: datetime = Field(description="Creation date")
    # End date
    end_date: datetime | None = Field(default=None, description="End date")


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

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Higest priority: 1, Lowest Priority: 10",
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
    creation_date: datetime = Field(description="Creation date")
    # End date
    end_date: datetime | None = Field(default=None, description="End date")


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

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job status
    job_status: str = Field(description="Job status")


class DeleteJobsRequest(BaseModel):
    """Delete Jobs Request.

    Pydantic Model for Delete Jobs Request.
    """

    # Job IDs
    job_ids: list[UUID] = Field(description="Job IDs to delete")


class DeleteJobsResponse(BaseModel):
    """Delete Jobs Response.

    Pydantic Model for Delete Jobs Response.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job status
    job_status: str = Field(description="Job status")


class SetJobResultsRequest(BaseModel):
    """Set Job Results Request.

    Pydantic Model for Set Job Results Request.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Results
    results: list = Field(description="Job results")
    # Errors
    errors: str | int | list | dict | None = Field(
        default=None, description="Errors"
    )


class SetJobResultsResponse(BaseModel):
    """Set Job Results Response.

    Pydantic Model for Set Job Results Response.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # QC driver name
    backend: str = Field(description="Backend device name")
    # Job status
    job_status: str = Field(description="Job status")


class UpdateJobRequest(BaseModel):
    """Update Job Request.

    Pydantic Model for Update Job Request.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job priority
    job_priority: int | None = Field(
        default=None,
        description="Job priority. Values: 1-10, Default: 5. "
        "Higest priority: 1, Lowest Priority: 10",
    )


class UpdateJobResponse(BaseModel):
    """Update Job Response.

    Pydantic Model for Update Job Response.
    """

    # Job ID
    job_id: UUID = Field(description="Job ID")
    # Job name
    job_name: str | None = Field(default=None, description="Job name")
    # Job type
    job_type: str = Field(description="Job type")
    # Job status
    job_status: str = Field(description="Job status")
    # Job priority
    job_priority: int = Field(
        default=Constant.DEFAULT_JOB_PRIORITY,
        description="Job priority. Values: 1-10, Default: 5. "
        "Higest priority: 1, Lowest Priority: 10",
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
    # Shots
    shots: int = Field(description="Shots")
    # Profiling
    profiling: list | None = Field(default=None, description="Profiling")
    # Dry-run
    dry_run: bool = Field(description="Dry-run flag")
    # Callbacks
    callbacks: list | None = Field(default=None, description="Callbacks")
    # Creation date
    creation_date: datetime = Field(description="Creation date")
    # End date
    end_date: datetime | None = Field(default=None, description="End date")
