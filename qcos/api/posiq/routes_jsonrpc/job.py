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
import asyncio
import logging
from typing import List

from qcos.api import schemas
from qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from qcos.api.posiq.routes_jsonrpc.routes import job_api_v1
from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.task_manager import scheduler

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
    job_sched_policy = body.job_sched_policy
    job_priority = body.job_priority
    description = body.description
    shots = body.shots
    backend = body.backend
    transpiler = body.transpiler
    optimization_level = body.optimization_level
    benchmark = body.benchmark
    dry_run = body.dry_run

    # validate: source_code
    jsonrpc_errors.handle_invalid_params(Library.validate_values_list(
        source_code, "source_code", str))

    # validate: code_type
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        code_type, "code_type", Constant.CODE_TYPES))

    # validate: job_type
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        job_type, "job_type", Constant.JOB_TYPES))

    # validate: job_sched_policy
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        job_sched_policy, "job_sched_policy",
        Constant.JOB_SCHED_POLICIES))

    # validate: job_priority
    jsonrpc_errors.handle_invalid_params(Library.validate_values_range(
        job_priority, "job_priority",
        Constant.MIN_JOB_PRIORITY, Constant.MAX_JOB_PRIORITY))

    # validate: description
    jsonrpc_errors.handle_invalid_params(Library.validate_values_length(
        description, "description",
        Constant.MIN_DESCRIPTION_LENGTH, Constant.MAX_DESCRIPTION_LENGTH,
        allow_none=True))

    # validate: shots
    jsonrpc_errors.handle_invalid_params(Library.validate_values_range(
        shots, "shots",
        Constant.MIN_SHOTS, Constant.MAX_SHOTS))

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

    # validate: benchmark
    if benchmark:
        for _benchmark in benchmark:
            jsonrpc_errors.handle_invalid_params(
                Library.validate_values_enum(_benchmark, "benchmark",
                                             Constant.BENCHMARK_TYPES,
                                             allow_none=True))

    # generate creation_date
    creation_date = Library.get_current_datetime()
    body.creation_date = creation_date

    # submit job
    res, err = scheduler.add(body.job_sched_policy, body)

    # handle submit response
    if err:
        jsonrpc_errors.handle_submit_error(err)

    response_info = {
        "job_id": res["job_id"],
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_sched_policy": job_sched_policy,
        "job_priority": job_priority,
        "description": description,
        "backend": backend,
        "transpiler": transpiler,
        "shots": shots,
        "benchmark": benchmark,
        "dry_run": dry_run,
        "creation_date": creation_date
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

    # query job status
    response, err = scheduler.get_result_by_id(job_id)

    # handle job status errors
    if err:
        jsonrpc_errors.handle_get_status_error(err)

    # construct response
    response_info = {
        "job_id": job_id,
        "job_status": response["state"]
    }
    if response.get("error_message"):
        response_info["error_message"] = response["error_message"]
    parameters = response.get("parameters", {})
    if parameters:
        response_info.update(parameters.get("data", {}))
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams,
                           jsonrpc_errors.JobGetResultsError])
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

    # query job results
    response, err = scheduler.get_result_by_id(job_id)

    # handle job results errors
    if err:
        jsonrpc_errors.handle_get_results_error(err)

    # construct response
    response_info = {
        "job_id": job_id,
        "job_status": response["state"],
        "results": response["results"],
    }
    if response.get("error_message"):
        response_info["error_message"] = response["error_message"]
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

    # query jobs' results
    response, err = scheduler.get_jobs()
    if err:
        jsonrpc_errors.handle_get_results_error(err)

    # construct response
    response_list = []
    for job_info in response:
        data = job_info["parameters"]["data"]
        response_info = {
            "job_id": job_info.get("id"),
            "job_status": job_info.get("state"),
            "backend": data.get("backend", None),
            "shots": data.get("shots", None),
            "description": data.get("description", None),
            "dry_run": data.get("dry_run", None),
            "creation_date": data.get("creation_date")
        }
        response_list.append(response_info)
    return response_list


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def cancel_jobs(
        body: schemas.CancelJobsRequest
) -> List[schemas.GetJobStatusResponse]:
    """
    Cancel job

    :param body: job_ids: job IDs
    :type body: schemas.CancelJobsRequest
    :return: cancelled jobs info
    """
    logger.info(f"Call cancel_jobs: {body}")

    job_ids = body.job_ids

    # get unique job_ids
    job_ids = list(dict.fromkeys(job_ids))

    # cancel jobs
    jsonrpc_errors.handle_cancel_error("cancel operation not support")

    # construct response
    response_list = [{
        "job_id": str(job_id),
        "job_status": Constant.JOB_STATUS_CANCELLED,
        "job_sched_policy": Constant.DEFAULT_JOB_SCHED_POLICY,
        "job_priority": 100,
        "backend": Constant.DRIVER_DUMMY,
        "shots": 1,
    } for job_id in job_ids]
    return response_list


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def delete_jobs(
        body: schemas.DeleteJobsRequest
) -> List[schemas.DeleteJobsResponse]:
    """
    Delete job

    :param body: job_ids: job IDs
    :type body: schemas.DeleteJobsRequest
    :return: deleted jobs info
    """
    logger.info(f"Call delete_jobs: {body}")

    job_ids = body.job_ids

    # get unique job_ids
    job_ids = list(dict.fromkeys(job_ids))

    # delete jobs
    success_list = scheduler.remove_jobs(job_ids)

    # construct response
    response_info = [{
        "job_id": job.get("id"),
        "job_status": job.get("state")
    } for job in success_list]
    return response_info
