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

import logging
from datetime import datetime
from typing import List

from qcos.api import schemas
from qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from qcos.api.posiq.routes_jsonrpc.routes import job_api_v1
from qcos.common import args_schema
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
    job_id = body.job_id
    job_type = body.job_type
    job_sched_policy = body.job_sched_policy
    job_priority = body.job_priority
    description = body.description
    shots = body.shots
    backend = body.backend
    transpiler_name = body.transpiler
    transpiler_info = body.transpiler_info
    profiling = body.profiling
    callbacks = body.callbacks
    dry_run = body.dry_run

    # validate: source_code
    jsonrpc_errors.handle_invalid_params(Library.validate_values_list(
        source_code, "source_code", str, allow_none=False))

    # validate: code_type
    code_type = code_type.lower()
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        code_type, "code_type", Constant.CODE_TYPES))

    # validate: job_id
    if job_id:
        jsonrpc_errors.handle_invalid_params(Library.validate_values_uuid(
            str(job_id), "job_id"))

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

    # get driver from backend
    driver_manger = scheduler.get_driver_manager()
    driver = driver_manger.get_driver(backend)
    enable_transpiler = driver.enable_transpiler
    driver_status = driver.get_status()
    enable_driver = driver.enable

    # check driver_status
    if not enable_driver:
        jsonrpc_errors.handle_job_error(
            "Can't submit job. reason: driver is disabled")
    elif driver_status == driver.DRIVER_STATUS_OFFLINE:
        jsonrpc_errors.handle_job_error(
            "Can't submit job. reason: driver status is offline")
    elif driver_status == driver.DRIVER_STATUS_UNKNOWN:
        jsonrpc_errors.handle_job_error(
            "Can't submit job. reason: driver status is unknown")

    # if transpiler is not specified, set the default transpiler from driver
    if not transpiler_name:
        transpiler_name = driver.get_transpiler()

    # validate: transpiler_name
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        transpiler_name, "transpiler",
        Constant.TRANSPILER_TYPES, allow_none=True))

    # validate supported_transpiler_list
    if enable_transpiler:
        jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
            transpiler_name, "transpiler",
            driver.supported_transpiler_list,
            allow_none=False))
        body.transpiler = transpiler_name

        # validate: transpiler_info
        if transpiler_name and transpiler_info:
            jsonrpc_errors.handle_invalid_params(Library.validate_schema(
                transpiler_info,
                args_schema.TRANSPILER_INFO,
                allow_none=True))
    else:
        # set transpiler/transpiler_info to None if enable_transpiler=False
        transpiler_name = None
        transpiler_info = None
        body.transpiler = None
        body.transpiler_info = None

    # get supported_code_types
    supported_code_types = []
    if enable_transpiler:
        transpiler_manager = scheduler.get_transpiler_manager()
        transpiler = transpiler_manager.get_transpiler(transpiler_name)
        supported_code_types = transpiler.get_supported_code_types()
    else:
        supported_code_types = driver.get_supported_code_types()

    # validate supported_code_types
    jsonrpc_errors.handle_invalid_params(Library.validate_values_enum(
        code_type, "code_type", supported_code_types,
        allow_none=False))

    # validate: profiling
    if profiling:
        for _profiling in profiling:
            jsonrpc_errors.handle_invalid_params(
                Library.validate_values_enum(_profiling, "profiling",
                                             Constant.PROFILING_TYPES,
                                             allow_none=True))

    # validate: callbacks
    if callbacks:
        jsonrpc_errors.handle_invalid_params(
            Library.validate_schema(callbacks, args_schema.CALLBACKS_SCHEMA))

    # generate creation_date
    creation_date = Library.get_current_datetime()
    body.creation_date = creation_date
    end_date = None

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
        "transpiler": transpiler_name,
        "transpiler_info": transpiler_info,
        "shots": shots,
        "profiling": profiling,
        "callbacks": callbacks,
        "dry_run": dry_run,
        "creation_date": creation_date,
        "end_date": end_date
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
    if response.get("error_message"):
        jsonrpc_errors.handle_get_status_error(response["error_message"])

    # get job_status
    job_status = response.get("job_status")

    # construct response
    response_info = {
        "job_id": job_id,
        "job_status": job_status
    }
    parameters = response.get("parameters", None)
    results = response.get("results", None)
    response_info = merge_results(response_info, parameters, results=results)
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
    if response.get("error_message"):
        jsonrpc_errors.handle_get_status_error(response["error_message"])

    # existing results reported by driver
    job_status = response.get("job_status")
    parameters = response.get("parameters", None)
    results = response.get("results", None)

    # construct response
    response_info = {
        "job_id": job_id,
        "job_status": job_status,
    }
    response_info = merge_results(response_info, parameters, results=results)
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
    responses, err = scheduler.get_jobs()
    if err:
        jsonrpc_errors.handle_get_results_error(err)

    # construct response
    response_list = []
    for response in responses:
        job_status = response.get("job_status")
        response_info = {
            "job_id": response.get("id"),
            "job_status": job_status
        }
        parameters = response.get("parameters", None)
        results = response.get("results", None)
        response_info = merge_results(
            response_info, parameters, results=results)
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


@job_api_v1.method(errors=[jsonrpc_errors.UnknownError,
                           jsonrpc_errors.InvalidParams])
def set_job_results(
        body: schemas.SetJobResultsRequest
) -> schemas.SetJobResultsResponse:
    """
    Set job results for existing job

    :param body: job_id: job ID
    :type body: schemas.SetJobResultsRequest
    """
    logger.info(f"Call set_job_results: {body}")
    job_id = body.job_id
    new_results = body.results

    # check if job exists
    success = scheduler.has_job(job_id)
    if not success:
        jsonrpc_errors.handle_job_error(f"Job {job_id} is not found")

    # set job results
    response, err = scheduler.get_result_by_id(job_id)
    # handle job status errors
    if err:
        jsonrpc_errors.handle_get_status_error(err)
    if response.get("error_message"):
        jsonrpc_errors.handle_get_status_error(response["error_message"])

    # copy existing results and updated using new_results
    existing_result = [{'metadata': {}, 'profiling': {}, 'results': {},
                        'status': Constant.JOB_STATUS_COMPLETED}]
    existing_results = response.get("results", None)
    if not existing_results:
        existing_results = existing_result

    # get end_date
    end_date = Library.get_current_datetime()

    for result in existing_results:
        result["results"] = new_results
        result["metadata"]["status"] = Constant.JOB_STATUS_COMPLETED

    updated_parameters = {
        "updated_job_info": {
            "end_date": end_date,
            "results": existing_results
        }
    }

    # updated parameters
    parameters = response.get("parameters", None)
    if parameters:
        parameters.update(updated_parameters)

    # update job using updated_parameters
    success = scheduler.update_job(job_id, parameters=parameters)
    if not success:
        jsonrpc_errors.handle_job_error(
            f"Failed to update job results: {job_id}")

    # run callbacks
    callbacks = Library.get_nested_dict_value(
        parameters, "job_info", "data", "callbacks", default=None)
    success, err_msg = scheduler.run_callbacks(
        job_id, existing_results, callbacks)
    if not success:
        jsonrpc_errors.handle_job_error(
            f"Failed to run callbacks in job: {job_id}. error_msg: {err_msg}")

    # construct response
    backend = Library.get_nested_dict_value(
        parameters, "job_info", "data", "backend", default=None)
    response_info = {
        "job_id": job_id,
        "backend": backend,
        "job_status": Constant.JOB_STATUS_COMPLETED
    }
    return response_info


def merge_results(response_info, parameters, results=None):
    """
    Merge results

    :param response_info: response info
    :param parameters: parameters from prefect
    :param results: results from prefect
    :return: new response info
    """
    end_date = None
    if parameters:
        job_info = parameters.get("job_info", None)
        if job_info:
            response_info.update(job_info.get("data", {}))
        updated_job_info = parameters.get("updated_job_info", None)
        if updated_job_info:
            # get end_date
            _end_date = updated_job_info.get("end_date", None)
            if _end_date:
                if isinstance(_end_date, str):
                    _end_date = datetime.fromisoformat(_end_date)
                end_date = _end_date
            # update results if new results exists in updated_job_info
            updated_results = updated_job_info.get("results", None)
            if updated_results:
                results = updated_results
        response_info["results"] = results
        if response_info["results"]:
            for result in response_info["results"]:
                _end_date = Library.get_nested_dict_value(
                    result, "metadata", "end_date", default=None)
                if isinstance(_end_date, str):
                    _end_date = datetime.fromisoformat(_end_date)
                if _end_date and end_date:
                    end_date = max(end_date, _end_date)
                elif _end_date:
                    end_date = _end_date
    if end_date:
        response_info["end_date"] = end_date.isoformat()
    return response_info
