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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from pydantic import BaseModel
from typing import Optional

from common.constant import Constant


class SubmitJobRequest(BaseModel):
    """
    Submit Job Request
    Pydantic Model for Submit Job Request
    """
    # Code types: qasm2, qasm3, qubo
    code_type: str = Constant.CODE_TYPE_QASM3
    # Source code list
    source_code: list[str] = []
    # QC driver name
    backend: str = Constant.QC_DRIVER_DUMMY
    # Transpiler
    transpiler: str = Constant.TRANSPILER_CMSS
    # Optimization level
    optimization_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL
    # Job type
    job_type: str = Constant.JOB_TYPE_ESTIMATION
    # Job scheduling policy
    job_scheduling_policy: str = Constant.DEFAULT_JOB_SCHEDULING_POLICY
    # Job priority
    job_priority: int = Constant.DEFAULT_JOB_PRIORITY
    # Shots
    shots: int = Constant.DEFAULT_SHOTS
    # Qubits
    qubits: Optional[int] = Constant.DEFAULT_QUBITS


class SubmitJobResponse(BaseModel):
    """
    Submit Job Response
    Pydantic Model for Submit Job Response
    """
    # Job ID
    job_id: int = None
    # Job status
    job_status: str = None
    # Job scheduling policy
    job_scheduling_policy: str = None
    # Job priority
    job_priority: int = None
    # QC driver name
    backend: str = None
    # Transpiler
    transpiler: str = None
    # Shots
    shots: int = None
    # Qubits
    qubits: Optional[int] = None


class GetJobStatusRequest(BaseModel):
    """
    Get Job Status Request
    Pydantic Model for Get Job Status Request
    """
    # Job ID
    job_id: int = None


class GetJobStatusResponse(BaseModel):
    """
    Get Job Status Response
    Pydantic Model for Get Job Status Response
    """
    job_id: int = None  # Job ID
    # Job status
    job_status: str = None
    # QC driver name
    backend: str = None
    # Transpiler
    transpiler: str = None
    # Job scheduling policy
    job_scheduling_policy: str = None
    # Job priority
    job_priority: int = None
    # Shots
    shots: int = None
    # Qubits
    qubits: Optional[int] = None
    # Creation Date
    creation_date: str = None


class GetJobResultsRequest(BaseModel):
    """
    Get Job Results Request
    Pydantic Model for Get Job Results Request
    """
    job_id: int = None  # Job ID


class GetJobResultsResponse(BaseModel):
    """
    Get Job Results Response
    Pydantic Model for Get Job Results Response
    """
    # Job ID
    job_id: int = None
    # Job status
    job_status: str = None
    # results
    results: dict = None


class GetJobsRequest(BaseModel):
    """
    Get Jobs Request
    Pydantic Model for Get Jobs Request
    """
    pass


class CancelJobsRequest(BaseModel):
    """
    Cancel Jobs Request
    Pydantic Model for Cancel Jobs Request
    """
    # Job IDs
    job_ids: list[int] = None


class DeleteJobsRequest(BaseModel):
    """
    Delete Jobs Request
    Pydantic Model for Delete Jobs Request
    """
    # Job IDs
    job_ids: list[int] = None


class DeleteJobsResponse(BaseModel):
    """
    Delete Jobs Response
    Pydantic Model for Delete Jobs Response
    """
    # Job ID
    job_id: int = None
    # Job status
    job_status: str = None
