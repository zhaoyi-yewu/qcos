#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from pydantic import BaseModel

from qcos.common.constant import Constant


class SubmitJobRequest(BaseModel):
    """Submit Job Request
    Pydantic Model for Submit Job Request
    """

    # Code types: qasm, qasm2, qasm3, qubo
    code_type: str = Constant.CODE_TYPE_QASM
    # Source code list
    source_code: list = []
    # description
    description: str | None = None
    # device name
    backend: str = Constant.DRIVER_DUMMY
    # Driver options
    driver_options: dict | None = None
    # Transpiler
    transpiler: str | None = None
    # Transpiler options
    transpiler_options: dict | None = None
    # Circuit aggregation: internal multi
    circuit_aggregation: str | None = None
    # Job ID
    job_id: UUID | None = None
    # Job name
    job_name: str | None = None
    # Job type
    job_type: str = Constant.JOB_TYPE_SAMPLING
    # Job priority
    job_priority: int = Constant.DEFAULT_JOB_PRIORITY
    # Profiling
    profiling: list | None = None
    # Shots
    shots: int = Constant.DEFAULT_SHOTS
    # Callbacks
    callbacks: list | None = None
    # Dry-run
    dry_run: bool = False
    # Creation date
    creation_date: datetime | None = None


class SubmitJobResponse(BaseModel):
    """Submit Job Response
    Pydantic Model for Submit Job Response
    """

    # Job ID
    job_id: UUID
    # Job name
    job_name: str | None = None
    # Job type
    job_type: str
    # Job status
    job_status: str
    # Job priority
    job_priority: int
    # Code type
    code_type: str
    # Source code list
    source_code: list
    # Description
    description: str | None = None
    # Backend device name
    backend: str
    # Driver options
    driver_options: dict | None = None
    # Transpiler
    transpiler: str | None = None
    # Transpiler options
    transpiler_options: dict | None = None
    # Circuit aggregation: internal, multi
    circuit_aggregation: str | None = None
    # Shots
    shots: int
    # Profiling
    profiling: list | None = None
    # Dry-run
    dry_run: bool
    # Callbacks
    callbacks: list | None = None
    # Creation date
    creation_date: datetime
    # End date
    end_date: datetime | None = None


class GetJobStatusRequest(BaseModel):
    """Get Job Status Request
    Pydantic Model for Get Job Status Request
    """

    # Job ID
    job_id: UUID


class GetJobStatusResponse(BaseModel):
    """Get Job Status Response
    Pydantic Model for Get Job Status Response
    """

    # Job ID
    job_id: UUID
    # Job name
    job_name: str | None = None
    # Job status
    job_status: str
    # Job priority
    job_priority: int
    # Description
    description: str | None = None
    # Backend device name
    backend: str
    # Driver options
    driver_options: dict | None = None
    # Transpiler
    transpiler: str | None = None
    # Transpiler options
    transpiler_options: dict | None = None
    # Circuit aggregation: internal, multi
    circuit_aggregation: str | None = None
    # Shots
    shots: int
    # Dry-run
    dry_run: bool
    # Progress
    progress: int | None = -1
    # Creation date
    creation_date: datetime
    # End date
    end_date: datetime | None = None


class GetJobResultsRequest(BaseModel):
    """Get Job Results Request
    Pydantic Model for Get Job Results Request
    """

    # Job ID
    job_id: UUID


class GetJobResultsResponse(BaseModel):
    """Get Job Results Response
    Pydantic Model for Get Job Results Response
    """

    # Job ID
    job_id: UUID
    # Job name
    job_name: str | None = None
    # Job status
    job_status: str
    # Job priority
    job_priority: int
    # Code type
    code_type: str
    # Description
    description: str | None = None
    # Source code list
    source_code: list
    # Backend device name
    backend: str
    # Driver options
    driver_options: dict | None = None
    # Transpiler
    transpiler: str | None = None
    # Transpiler options
    transpiler_options: dict | None = None
    # Circuit aggregation: internal, multi
    circuit_aggregation: str | None = None
    # Shots
    shots: int
    # Dry-run
    dry_run: bool
    # Progress
    progress: int | None = -1
    # Results
    results: str | int | list | dict | None = None
    # Creation date
    creation_date: datetime
    # End date
    end_date: datetime | None = None


class GetJobsRequest(BaseModel):
    """Get Jobs Request
    Pydantic Model for Get Jobs Request
    """


class CancelJobsRequest(BaseModel):
    """Cancel Jobs Request
    Pydantic Model for Cancel Jobs Request
    """

    # Job IDs
    job_ids: list[UUID]


class CancelJobsResponse(BaseModel):
    """Cancel Jobs Response
    Pydantic Model for Cancel Jobs Response
    """

    # Job ID
    job_id: UUID
    # Job status
    job_status: str


class DeleteJobsRequest(BaseModel):
    """Delete Jobs Request
    Pydantic Model for Delete Jobs Request
    """

    # Job IDs
    job_ids: list[UUID]


class DeleteJobsResponse(BaseModel):
    """Delete Jobs Response
    Pydantic Model for Delete Jobs Response
    """

    # Job ID
    job_id: UUID
    # Job status
    job_status: str


class SetJobResultsRequest(BaseModel):
    """Set Job Results Request
    Pydantic Model for Set Job Results Request
    """

    # Job ID
    job_id: UUID
    # Results
    results: list
    # Errors
    errors: str | int | list | dict | None = None


class SetJobResultsResponse(BaseModel):
    """Set Job Results Response
    Pydantic Model for Set Job Results Response
    """

    # Job ID
    job_id: UUID
    # QC driver name
    backend: str
    # Job status
    job_status: str
