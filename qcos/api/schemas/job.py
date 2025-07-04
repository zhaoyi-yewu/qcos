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
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel

from qcos.common.constant import Constant


class SubmitJobRequest(BaseModel):
    """
    Submit Job Request
    Pydantic Model for Submit Job Request
    """
    # Code types: qasm, qasm2, qasm3, qubo
    code_type: str = Constant.CODE_TYPE_QASM
    # Source code list
    source_code: list[str] = []
    # description
    description: Optional[str] = None
    # QC driver name
    backend: str = Constant.DRIVER_DUMMY
    # Transpiler
    transpiler: Optional[str] = Constant.TRANSPILER_CMSS
    # Optimization level
    optimization_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL
    # Job type
    job_type: str = Constant.JOB_TYPE_ESTIMATION
    # Job scheduling policy
    job_sched_policy: str = Constant.DEFAULT_JOB_SCHED_POLICY
    # Job priority
    job_priority: int = Constant.DEFAULT_JOB_PRIORITY
    # Profiling
    profiling: Optional[list] = []
    # Shots
    shots: int = Constant.DEFAULT_SHOTS
    # Callbacks
    callbacks: Optional[list] = None
    # Dry-run
    dry_run: Optional[bool] = False
    # Creation date
    creation_date: Optional[datetime] = None


class SubmitJobResponse(BaseModel):
    """
    Submit Job Response
    Pydantic Model for Submit Job Response
    """
    # Job ID
    job_id: UUID = None
    # Job status
    job_status: str = None
    # Job scheduling policy
    job_sched_policy: str = None
    # Job priority
    job_priority: int = None
    # Description
    description: Optional[str] = None
    # QC driver name
    backend: str = None
    # Transpiler
    transpiler: Optional[str] = None
    # Shots
    shots: int = None
    # Profiling
    profiling: Optional[list] = []
    # Dry-run
    dry_run: Optional[bool] = False
    # Callbacks
    callbacks: Optional[list] = None
    # Creation date
    creation_date: Optional[datetime] = None


class GetJobStatusRequest(BaseModel):
    """
    Get Job Status Request
    Pydantic Model for Get Job Status Request
    """
    # Job ID
    job_id: UUID = None


class GetJobStatusResponse(BaseModel):
    """
    Get Job Status Response
    Pydantic Model for Get Job Status Response
    """
    # Job ID
    job_id: UUID = None
    # Job status
    job_status: str = None
    # QC driver name
    backend: Optional[str] = None
    # Transpiler
    transpiler: Optional[str] = None
    # Job scheduling policy
    job_sched_policy: Optional[str] = None
    # Job priority
    job_priority: Optional[int] = None
    # Description
    description: Optional[str] = None
    # Shots
    shots: Optional[int] = None
    # Dry-run
    dry_run: Optional[bool] = False
    # Creation Date
    creation_date: Optional[datetime] = None


class GetJobResultsRequest(BaseModel):
    """
    Get Job Results Request
    Pydantic Model for Get Job Results Request
    """
    # Job ID
    job_id: UUID = None


class GetJobResultsResponse(BaseModel):
    """
    Get Job Results Response
    Pydantic Model for Get Job Results Response
    """
    # Job ID
    job_id: UUID = None
    # Job status
    job_status: str = None
    # Results
    results: Optional[Union[str, int, list, dict]] = None


class GetJobsRequest(BaseModel):
    """
    Get Jobs Request
    Pydantic Model for Get Jobs Request
    """


class CancelJobsRequest(BaseModel):
    """
    Cancel Jobs Request
    Pydantic Model for Cancel Jobs Request
    """
    # Job IDs
    job_ids: list[UUID] = None


class DeleteJobsRequest(BaseModel):
    """
    Delete Jobs Request
    Pydantic Model for Delete Jobs Request
    """
    # Job IDs
    job_ids: list[UUID] = None


class DeleteJobsResponse(BaseModel):
    """
    Delete Jobs Response
    Pydantic Model for Delete Jobs Response
    """
    # Job ID
    job_id: UUID = None
    # Job status
    job_status: str = None


class SetJobResultsRequest(BaseModel):
    """
    Set Job Results Request
    Pydantic Model for Set Job Results Request
    """
    # Job ID
    job_id: UUID = None
    # Results
    results: Union[str, int, list, dict] = None


class SetJobResultsResponse(BaseModel):
    """
    Set Job Results Response
    Pydantic Model for Set Job Results Response
    """
    # Job ID
    job_id: UUID = None
    # QC driver name
    backend: Optional[str] = None
    # Job status
    job_status: str = None
