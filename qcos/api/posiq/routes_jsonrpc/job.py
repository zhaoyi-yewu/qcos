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
from common.library import Library
from typing import List


logger = logging.getLogger(__name__)


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams,
                           jsonrpc_errors.JobSubmitError])
def submit_job(
        body: schemas.SubmitJobRequest
) -> schemas.SubmitJobResponse:
    """
    Submit job

    :param body: job info
    :type body: schemas.SubmitJobRequest
    :return: job info
    """
    logger.info(f"Call submit_job: {body}")

    source_code = body.source_code
    code_type = body.code_type
    job_type = body.job_type
    job_scheduling_policy = body.job_scheduling_policy
    job_priority = body.job_priority
    shots = body.shots
    qubits = body.qubits
    backend = body.backend
    transpiler = body.transpiler
    optimization_level = body.optimization_level

    # validate: source_code
    jsonrpc_errors.handle_invalid_params(Library.validate_values_list(
        source_code, "source_code", str))

    # validate: code_type
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        code_type, "code_type", Constant.CODE_TYPES))

    # validate: job_type
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        job_type, "job_type", Constant.JOB_TYPES))

    # validate: job_scheduling_policy
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        job_scheduling_policy, "job_scheduling_policy",
        Constant.JOB_SCHEDULING_POLICIES))

    # validate: job_priority
    jsonrpc_errors.handle_invalid_params(Library.validate_values_range(
        job_priority, "job_priority",
        Constant.MIN_JOB_PRIORITY, Constant.MAX_JOB_PRIORITY))

    # validate: shots
    jsonrpc_errors.handle_invalid_params(Library.validate_values_range(
        shots, "shots",
        Constant.MIN_SHOTS, Constant.MAX_SHOTS))

    # validate: qubits
    jsonrpc_errors.handle_invalid_params(Library.validate_values_range(
        qubits, "qubits",
        Constant.MIN_QUBITS, Constant.MAX_QUBITS))

    # validate: backend
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        backend, "backend", Constant.DRIVERS))

    # validate: transpiler
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        transpiler, "transpiler", Constant.TRANSPILER_TYPES))

    # validate: optimization_level
    jsonrpc_errors.handle_invalid_params(Library.validate_values_range(
        optimization_level, "optimization_level",
        Constant.MIN_OPTIMIZATION_LEVEL, Constant.MAX_OPTIMIZATION_LEVEL))

    response_info = {
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.DRIVER_DUMMY,
        "transpiler": Constant.TRANSPILER_CMSS,
        "shots": 1,
        "qubits": 1024
    }
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def get_job_status(
        body: schemas.GetJobStatusRequest
) -> schemas.GetJobStatusResponse:
    """
    Get job status

    :param body: job_id: job ID
    :type body: schemas.GetJobStatusRequest
    :return: job status
    """
    logger.info(f"Call get_job_status: {body}")

    job_id = body.job_id

    response_info = {
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.DRIVER_DUMMY,
        "transpiler": Constant.TRANSPILER_CMSS,
        "shots": 1,
        "qubits": 1,
        "creation_date": Library.get_current_datetime()
    }
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def get_job_results(
        body: schemas.GetJobResultsRequest
) -> schemas.GetJobResultsResponse:
    """
    Get job results

    :param body: job_id: job ID
    :type body: schemas.GetJobResultsRequest
    :return: job results
    """
    logger.info(f"Call get_job_results: {body}")

    job_id = body.job_id

    response_info = {
        "job_id": job_id,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "results": {"123": 123}
    }
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def get_jobs(
        body: schemas.GetJobsRequest = None
) -> List[schemas.GetJobStatusResponse]:
    """
    Get job list

    :param body: job_id: job ID
    :type body: schemas.GetJobsRequest
    :return: job list
    """
    logger.info(f"Call get_jobs: {body}")

    response_info = [{
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.DRIVER_DUMMY,
        "shots": 1,
        "qubits": 1,
        "creation_date": Library.get_current_datetime()
    }]
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def cancel_job(
        body: schemas.CancelJobsRequest
) -> List[schemas.GetJobStatusResponse]:
    """
    Cancel job

    :param body: job_ids: job IDs
    :type body: schemas.CancelJobsRequest
    :return: cancelled jobs info
    """
    logger.info(f"Call cancel_job: {body}")

    job_ids = body.job_ids

    # validate: source_code
    jsonrpc_errors.handle_invalid_params(Library.validate_values_list(
        job_ids, "job_ids", int))

    response_info = [{
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_scheduling_policy": Constant.DEFAULT_JOB_SCHEDULING_POLICY,
        "job_priority": 100,
        "backend": Constant.DRIVER_DUMMY,
        "shots": 1,
        "qubits": 1,
        "creation_date": Library.get_current_datetime()
    }]
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def delete_job(
        body: schemas.DeleteJobsRequest
) -> List[schemas.DeleteJobsResponse]:
    """
    Delete job

    :param body: job_ids: job IDs
    :type body: schemas.DeleteJobsRequest
    :return: deleted jobs info
    """
    logger.info(f"Call delete_job: {body}")

    job_ids = body.job_ids

    # validate: source_code
    jsonrpc_errors.handle_invalid_params(Library.validate_values_list(
        job_ids, "job_ids", int))

    response_info = [{
        "job_id": 1,
        "job_status": Constant.JOB_STATUS_UNKNOWN
    }]
    return response_info
