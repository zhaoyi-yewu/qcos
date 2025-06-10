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

import logging

from api import schemas
from api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from api.posiq.routes_jsonrpc.routes import job_api_v1
from common.constant import Constant
from libs.library import Library
from typing import List


logger = logging.getLogger(__name__)


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.JobSubmitError])
def submit_job(
        body: schemas.SubmitJobRequest
) -> schemas.SubmitJobResponse:
    logger.info(f"Call submit_job: {body}")
    response_info = {
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.QC_DRIVER_DUMMY,
        "transpiler": Constant.TRANSPILER_CMSS,
        "shots": 1,
        "qubits": 1024
    }
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError])
def get_job_status(
        body: schemas.GetJobStatusRequest
) -> schemas.GetJobStatusResponse:
    logger.info(f"Call get_job_status: {body}")
    response_info = {
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.QC_DRIVER_DUMMY,
        "transpiler": Constant.TRANSPILER_CMSS,
        "shots": 1,
        "qubits": 1,
        "creation_date": Library.get_current_datetime()
    }
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError])
def get_job_results(
        body: schemas.GetJobResultsRequest
) -> schemas.GetJobResultsResponse:
    logger.info(f"Call get_job_results: {body}")
    response_info = {
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "results": {"123": 123}
    }
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError])
def get_jobs(
        body: schemas.GetJobsRequest = None
) -> List[schemas.GetJobStatusResponse]:
    logger.info(f"Call get_jobs: {body}")
    response_info = [{
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.QC_DRIVER_DUMMY,
        "shots": 1,
        "qubits": 1,
        "creation_date": Library.get_current_datetime()
    }]
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError])
def cancel_job(
        body: schemas.CancelJobsRequest
) -> List[schemas.GetJobStatusResponse]:
    logger.info(f"Call cancel_job: {body}")
    response_info = [{
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.QC_DRIVER_DUMMY,
        "shots": 1,
        "qubits": 1,
        "creation_date": Library.get_current_datetime()
    }]
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError])
def delete_job(
        body: schemas.DeleteJobsRequest
) -> List[schemas.DeleteJobsResponse]:
    logger.info(f"Call delete_job: {body}")
    response_info = [{
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN
    }]
    return response_info
