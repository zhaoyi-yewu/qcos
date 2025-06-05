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
    code_type: str = Constant.code_type_qasm3  # Code types: QASM2, QASM3, QUBO
    code_content: list[str] = []  # Source code list
    backend: str = Constant.qc_driver_dummy  # QC driver name
    job_type: str = Constant.job_type_estimation   # Job type
    shots: int = None  # Shots
    qubits: Optional[int] = None  # Qubits


class SubmitJobResponse(BaseModel):
    """
    Submit Job Response
    Pydantic Model for Submit Job Response
    """
    job_id: int = None  # Job ID
    status: str = Constant.job_status_unknown  # Job status
    backend: str = Constant.qc_driver_dummy  # QC driver name
    shots: int = None  # Shots
    qubits: Optional[int] = None  # Qubits


class GetJobStatusRequest(BaseModel):
    """
    Get Job Status Request
    Pydantic Model for Get Job Status Request
    """
    job_id: int = None


class GetJobStatusResponse(BaseModel):
    """
    Get Job Status Response
    Pydantic Model for Get Job Status Response
    """
    job_id: int = None  # Job ID
    status: str = Constant.job_status_unknown  # Job status
    backend: str = Constant.qc_driver_dummy  # QC driver name
    job_type: str = Constant.job_type_estimation  # Job type
    shots: int = None  # Shots
    qubits: Optional[int] = None  # Qubits
    creationDate: str = None  # Creation Date


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
    job_id: int = None  # Job ID
    results: dict = None  # results


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
    job_id: int = None  # Job ID


class DeleteJobsRequest(BaseModel):
    """
    Delete Jobs Request
    Pydantic Model for Delete Jobs Request
    """
    job_id: int = None  # Job ID


class DeleteJobsResponse(BaseModel):
    """
    Delete Jobs Response
    Pydantic Model for Delete Jobs Response
    """
    job_id: int = None  # Job ID
    status: str = Constant.job_status_unknown  # Job status
