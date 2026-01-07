#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from fastapi import Depends

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import job_api_v1
from wy_qcos.common import args_schema, errors
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.task_manager import scheduler
from .dependencies.authentication import auth

logger = logging.getLogger(__name__)
module_name = "JOB"


@job_api_v1.method(
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.ConflictError,
        jsonrpc_errors.InternalServerError,
    ]
)
def submit_job(
    body: schemas.SubmitJobRequest, auth_data: dict | None = Depends(auth)
) -> schemas.SubmitJobResponse:
    """Submit job.

    Args:
        body(schemas.SubmitJobRequest): job info
        auth_data: auth data

    Returns:
        job info
    """
    func_name = "submit_job"
    logger.debug(f"Call {func_name}: {body}")

    source_code = body.source_code
    code_type = body.code_type
    circuit_aggregation = body.circuit_aggregation
    job_id = body.job_id
    job_name = body.job_name
    job_type = body.job_type
    job_priority = body.job_priority
    description = body.description
    shots = body.shots
    backend = body.backend
    driver_options = body.driver_options
    transpiler_name = body.transpiler
    transpiler_options = body.transpiler_options
    profiling = body.profiling
    callbacks = body.callbacks
    dry_run = body.dry_run

    # validate: code_type
    code_type = code_type.lower()
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_enum(
            code_type, "code_type", Constant.CODE_TYPES
        ),
    )

    # validate: circuit_aggregation
    if circuit_aggregation:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_values_enum(
                circuit_aggregation,
                "circuit_aggregation",
                Constant.AGGREGATION_TYPES,
            ),
        )

    # Validate: source_code
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_schema(source_code, args_schema.SOURCE_CODE_SCHEMA),
    )
    if not source_code:
        jsonrpc_errors.handle_error_bad_requests(
            module_name, func_name, (False, "source_code should not be empty")
        )

    # Validate: source_code by code_type
    if code_type in [Constant.CODE_TYPE_QUBO]:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_qubo_matrices(source_code),
        )
    else:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_schema(
                source_code, args_schema.SOURCE_CODE_TEXT_SCHEMA
            ),
        )

    # Validate: source_code by circuit_aggregation
    if (
        code_type not in [Constant.CODE_TYPE_QUBO]
        and circuit_aggregation == Constant.AGGREGATION_TYPE_INTERNAL
    ):
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_values_length(
                source_code,
                "source_code",
                None,
                Constant.MAX_AGGREGATION_JOBS,
                allow_none=False,
            ),
        )

    # validate: job_id
    if job_id:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_values_uuid(str(job_id), "job_id"),
        )

    # validate: job_name
    if not job_name:
        job_name = None
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_schema(
            job_name, args_schema.NAME_SCHEMA, allow_none=True
        ),
    )

    # validate: job_type
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_enum(job_type, "job_type", Constant.JOB_TYPES),
    )

    # validate: job_priority
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_range(
            job_priority,
            "job_priority",
            Constant.MIN_JOB_PRIORITY,
            Constant.MAX_JOB_PRIORITY,
        ),
    )

    # validate: description
    if not description:
        description = None
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_length(
            description,
            "description",
            Constant.MIN_DESCRIPTION_LENGTH,
            Constant.MAX_DESCRIPTION_LENGTH,
            allow_none=True,
        ),
    )

    # validate: shots
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_range(
            shots, "shots", Constant.MIN_SHOTS, Constant.MAX_SHOTS
        ),
    )

    # get device
    device_manger = scheduler.get_device_manager()
    devices = device_manger.get_devices()

    # validate: backend
    if auth_data is not None:
        if backend not in auth_data["device_names"]:
            jsonrpc_errors.handle_error_bad_requests(
                module_name, func_name, (False, f"no such device: {backend}")
            )
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_enum(backend, "backend", devices),
    )

    # get driver from backend
    device = devices.get(backend)
    driver = device.get_driver()
    enable_transpiler = driver.enable_transpiler
    device_status = device.get_status()
    enable_device = device.enable

    # check device status
    if not enable_device:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "device is disabled")
        )
    elif device_status in [
        device.DEVICE_STATUS_OFFLINE,
        device.DEVICE_STATUS_UNKNOWN,
    ]:
        jsonrpc_errors.handle_error_conflict(
            module_name,
            func_name,
            (False, f"device status is {device_status}"),
        )

    # validate: driver_options
    if driver_options:
        driver_options_schema = driver.get_driver_options_schema()
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_schema(
                driver_options, args_schema.DRIVER_OPTIONS, allow_none=True
            ),
        )
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_schema(
                driver_options, driver_options_schema, allow_none=True
            ),
            param_name="driver_options",
        )

    # if transpiler is not specified, set the default transpiler from driver
    if not transpiler_name:
        transpiler_name = driver.get_transpiler()

    # validate: transpiler_name
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_enum(
            transpiler_name,
            "transpiler",
            Constant.TRANSPILERS,
            allow_none=True,
        ),
    )

    # validate supported_transpilers
    supported_code_types = []
    transpiler_manager = scheduler.get_transpiler_manager()
    if enable_transpiler:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_values_enum(
                transpiler_name,
                "transpiler",
                driver.supported_transpilers,
                allow_none=False,
            ),
        )
        body.transpiler = transpiler_name
        transpiler = transpiler_manager.get_transpiler(transpiler_name)
        transpiler_options_schema = transpiler.get_transpiler_options_schema()

        # validate: transpiler_options
        if transpiler_name and transpiler_options:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                Library.validate_schema(
                    transpiler_options,
                    args_schema.TRANSPILER_OPTIONS,
                    allow_none=True,
                ),
            )
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                Library.validate_schema(
                    transpiler_options,
                    transpiler_options_schema,
                    allow_none=True,
                ),
                param_name="transpiler_options",
            )

        # get supported_code_types
        supported_code_types = transpiler.get_supported_code_types()
    else:
        # set transpiler/transpiler_options to None if enable_transpiler=False
        transpiler_name = None
        transpiler_options = None
        body.transpiler = None
        body.transpiler_options = None
        supported_code_types = driver.get_supported_code_types()

    # validate supported_code_types
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_enum(
            code_type, "code_type", supported_code_types, allow_none=False
        ),
    )

    # validate: profiling
    if profiling:
        for _profiling in profiling:
            jsonrpc_errors.handle_error_bad_requests(
                module_name,
                func_name,
                Library.validate_values_enum(
                    _profiling,
                    "profiling",
                    Constant.PROFILING_TYPES,
                    allow_none=True,
                ),
            )

    # validate: callbacks
    if callbacks:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_schema(callbacks, args_schema.CALLBACKS_SCHEMA),
        )

    # generate creation_date
    creation_date = Library.get_current_datetime()
    body.creation_date = creation_date
    end_date = None

    # submit job
    res = {}
    err = None
    try:
        device_name = device.get_name()
        tags = [f"{device_name}"]
        if auth_data is not None:
            virtual_instance_id = auth_data["instance_id"]
            tags.extend([f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"])
        res, err = scheduler.add(
            body,
            tags=tags,
        )

    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )

    # handle submit response
    if err:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, err)
        )

    _response_info = {
        "job_id": res["job_id"],
        "job_name": job_name,
        "job_type": job_type,
        "job_status": Constant.JOB_STATUS_UNKNOWN,
        "job_priority": job_priority,
        "code_type": code_type,
        "source_code": source_code,
        "description": description,
        "backend": backend,
        "driver_options": driver_options,
        "transpiler": transpiler_name,
        "transpiler_options": transpiler_options,
        "shots": shots,
        "profiling": profiling,
        "callbacks": callbacks,
        "dry_run": dry_run,
        "creation_date": creation_date,
        "end_date": end_date,
    }
    response_info = schemas.SubmitJobResponse.model_validate(_response_info)
    return response_info


@job_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.InternalServerError]
)
def get_job_status(
    body: schemas.GetJobStatusRequest, auth_data: dict | None = Depends(auth)
) -> schemas.GetJobStatusResponse:
    """Get job status.

    Args:
        body(schemas.GetJobStatusRequest): job_id: job ID
        auth_data: auth data

    Returns:
        job status
    """
    func_name = "get_job_status"
    logger.info(f"Call {func_name}: {body}")

    job_id = body.job_id

    # query job status
    response = {}
    try:
        tags = None
        if auth_data is not None:
            virtual_instance_id = auth_data["instance_id"]
            tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
        response, _ = scheduler.get_result_by_id(job_id, tags=tags)
    except errors.NotFound:
        # check if job exists
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )
    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )

    # handle job results errors
    if response.get("error_message"):
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, response["error_message"])
        )

    # get job_status
    job_status = response.get("job_status")
    progress = response.get("artifact", {}).get("progress", -1)

    # construct response
    _response_info = {
        "job_id": job_id,
        "job_status": job_status,
        "progress": progress,
    }
    parameters = response.get("parameters", None)
    results = response.get("results", None)
    _response_info = merge_results(_response_info, parameters, results=results)
    response_info = schemas.GetJobStatusResponse.model_validate(_response_info)
    return response_info


@job_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.InternalServerError]
)
def get_job_results(
    body: schemas.GetJobResultsRequest, auth_data: dict | None = Depends(auth)
) -> schemas.GetJobResultsResponse:
    """Get job results.

    Args:
        body(schemas.GetJobResultsRequest): job_id: job ID
        auth_data: auth data

    Returns:
        job results
    """
    func_name = "get_job_results"
    logger.info(f"Call {func_name}: {body}")

    job_id = body.job_id

    # query job results
    response = {}
    try:
        tags = None
        if auth_data is not None:
            virtual_instance_id = auth_data["instance_id"]
            tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
        response, _ = scheduler.get_result_by_id(job_id, tags=tags)
    except errors.NotFound:
        # check if job exists
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )
    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )

    # handle job results errors
    if response.get("error_message"):
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, response["error_message"])
        )

    # existing results reported by driver
    job_status = response.get("job_status")
    parameters = response.get("parameters", None)
    results = response.get("results", None)
    progress = response.get("artifact", {}).get("progress", -1)

    # construct response
    _response_info = {
        "job_id": job_id,
        "job_status": job_status,
        "progress": progress,
    }
    _response_info = merge_results(_response_info, parameters, results=results)
    response_info = schemas.GetJobResultsResponse.model_validate(
        _response_info
    )
    return response_info


@job_api_v1.method(errors=[jsonrpc_errors.InternalServerError])
def get_jobs(
    body: schemas.GetJobsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> list[schemas.GetJobStatusResponse]:
    """Get job list.

    Args:
        body(schemas.GetJobsRequest): job_id: job ID
        auth_data: auth data

    Returns:
        job list
    """
    func_name = "get_jobs"
    logger.info(f"Call {func_name}: {body}")

    # query jobs' results
    responses = []
    try:
        tags = None
        if auth_data is not None:
            virtual_instance_id = auth_data["instance_id"]
            tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
        responses, err = scheduler.get_jobs(tags=tags)
    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )

    # construct response
    response_list = []
    for response in responses:
        job_status = response.get("job_status")
        _response_info = {
            "job_id": response.get("id"),
            "job_status": job_status,
            "progress": response.get("progress"),
        }
        parameters = response.get("parameters", None)
        results = response.get("results", None)
        _response_info = merge_results(
            _response_info, parameters, results=results
        )
        response_info = schemas.GetJobStatusResponse.model_validate(
            _response_info
        )
        response_list.append(response_info)
    return response_list


@job_api_v1.method(errors=[])
def cancel_jobs(
    body: schemas.CancelJobsRequest,
    auth_data: dict | None = Depends(auth),
) -> list[schemas.CancelJobsResponse]:
    """Cancel job.

    Args:
        body(schemas.CancelJobsRequest): job_ids: job IDs
        auth_data: auth data

    Returns:
        cancelled jobs info
    """
    func_name = "cancel_jobs"
    logger.info(f"Call {func_name}: {body}")

    job_ids = body.job_ids

    # get unique job_ids
    job_ids = list(dict.fromkeys(job_ids))

    tags = None
    if auth_data is not None:
        virtual_instance_id = auth_data["instance_id"]
        tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
    # cancel jobs
    success_list = scheduler.cancel_jobs(job_ids, tags=tags)
    # construct response
    response_info = [
        schemas.CancelJobsResponse(
            job_id=job.get("id"), job_status=job.get("state")
        )
        for job in success_list
    ]
    return response_info


@job_api_v1.method(errors=[])
def delete_jobs(
    body: schemas.DeleteJobsRequest,
    auth_data: dict | None = Depends(auth),
) -> list[schemas.DeleteJobsResponse]:
    """Delete job.

    Args:
        body(schemas.DeleteJobsRequest): job_ids: job IDs
        auth_data: auth data

    Returns:
        deleted jobs info
    """
    func_name = "delete_jobs"
    logger.info(f"Call {func_name}: {body}")

    job_ids = body.job_ids

    # get unique job_ids
    job_ids = list(dict.fromkeys(job_ids))
    tags = None
    if auth_data is not None:
        virtual_instance_id = auth_data["instance_id"]
        tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
    # delete jobs
    success_list = scheduler.delete_jobs(job_ids, tags=tags)
    # construct response
    response_info = [
        schemas.DeleteJobsResponse(
            job_id=job.get("id"), job_status=job.get("state")
        )
        for job in success_list
    ]
    return response_info


@job_api_v1.method(
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.InternalServerError]
)
def set_job_results(
    body: schemas.SetJobResultsRequest, auth_data: dict | None = Depends(auth)
) -> schemas.SetJobResultsResponse:
    """Set job results for existing job.

    Args:
        body(schemas.SetJobResultsRequest): job_id: job ID
        auth_data: auth data
    """
    func_name = "set_job_results"
    logger.info(f"Call {func_name}: {body}")

    job_id = body.job_id
    new_results = body.results

    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_schema(new_results, args_schema.SOURCE_SET_RESULTS),
    )

    # get existing job results
    response = {}
    try:
        tags = None
        if auth_data is not None:
            virtual_instance_id = auth_data["instance_id"]
            tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
        response, err = scheduler.get_result_by_id(job_id, tags)
    except errors.NotFound:
        # check if job exists
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )
    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )

    job_status = response["job_status"]
    if job_status not in [
        Constant.JOB_STATUS_RUNNING,
        Constant.JOB_STATUS_COMPLETED,
    ]:
        err_msg = (
            f"Job: '{job_id}' is not in RUNNING or COMPLETED state. "
            f"Can't {func_name}"
        )
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, err_msg)
        )

    # handle job status errors
    if response.get("error_message"):
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, response["error_message"])
        )

    parameters = response.get("parameters", None)
    source_code = Library.get_nested_dict_value(
        parameters, "job_info", "data", "source_code", default=[]
    )

    # copy existing results and updated using new_results
    existing_results = response.get("results", None)
    if not existing_results:
        existing_results = []
        for _ in range(len(source_code)):
            existing_results.append({
                "metadata": {},
                "profiling": {},
                "results": {},
                "status": Constant.JOB_STATUS_UNKNOWN,
            })

    # get end_date
    end_date = Library.get_current_datetime()

    # check length of new results/errors
    if new_results and len(new_results) != len(existing_results):
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (
                False,
                "Length of new results should be the same as "
                "the length of the existing results",
            ),
        )

    # update results/errors
    i = 0
    is_failed = False
    for result in existing_results:
        new_result = new_results[i]
        if "code" in new_result:
            # failed and set error message
            result["error"] = new_result
            result["metadata"]["status"] = Constant.JOB_STATUS_FAILED
            is_failed = True
        else:
            # success and set new results
            result.update(new_result)
            result["metadata"]["status"] = Constant.JOB_STATUS_COMPLETED
        result["metadata"]["end_date"] = end_date
        i += 1
    job_status = (
        Constant.JOB_STATUS_FAILED
        if is_failed
        else Constant.JOB_STATUS_COMPLETED
    )

    updated_parameters = {
        "updated_job_info": {"results": existing_results, "end_date": end_date}
    }

    # updated parameters
    if parameters:
        parameters.update(updated_parameters)

    # update job using updated_parameters
    success, err_msg = scheduler.update_job(job_id, parameters=parameters)
    if not success:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, err_msg)
        )

    # run callbacks
    callbacks = Library.get_nested_dict_value(
        parameters, "job_info", "data", "callbacks", default=None
    )

    # construct response
    backend = Library.get_nested_dict_value(
        parameters, "job_info", "data", "backend", default=None
    )

    _response_info = {
        "job_id": job_id,
        "job_status": job_status,
        "backend": backend,
        "results": existing_results,
    }

    success, err_msg = scheduler.run_callbacks(_response_info, callbacks)
    if not success:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, err_msg)
        )

    response_info = schemas.SetJobResultsResponse.model_validate(
        _response_info
    )
    return response_info


@job_api_v1.method(errors=[])
def update_job(
    body: schemas.UpdateJobRequest, auth_data: dict | None = Depends(auth)
) -> schemas.UpdateJobResponse:
    """Update job.

    Args:
        body(schemas.UpdateJobsRequest): job info
        auth_data: auth data

    Returns:
        update job param
    """
    func_name = "update_job"
    logger.info(f"Call {func_name}: {body}")

    parameters = {"job_id": body.job_id, "job_priority": body.job_priority}

    job_id = body.job_id

    tags = None
    if auth_data is not None:
        virtual_instance_id = auth_data["instance_id"]
        tags = [f"{Constant.VID_TAGS_PREFIX}:{virtual_instance_id}"]
    try:
        response, err = scheduler.get_result_by_id(job_id, tags)
    except errors.NotFound:
        # check if job exists
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )
    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )

    job_status = response["job_status"]
    if job_status != Constant.JOB_STATUS_QUEUED:
        err_msg = f"Job: '{job_id}' is not in QUEUED state. Can't {func_name}"
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, err_msg)
        )

    # update job
    try:
        job, err = scheduler.update_job(
            job_id=job_id,
            parameters=parameters,
            tags=tags,
        )
    except errors.WorkFlowError as e:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    if err is not None:
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, err)
        )

    # construct response
    _response_info = {
        "job_id": job.get("job_id"),
        "job_name": job.get("job_status"),
        "job_type": job.get("job_type"),
        "job_status": job.get("job_status"),
        "job_priority": job.get("job_priority"),
        "code_type": job.get("code_type"),
        "source_code": job.get("source_code"),
        "description": job.get("description"),
        "backend": job.get("backend"),
        "driver_options": job.get("driver_options"),
        "transpiler": job.get("transpiler"),
        "transpiler_options": job.get("transpiler_options"),
        "shots": job.get("shots"),
        "profiling": job.get("profiling"),
        "callbacks": job.get("callbacks"),
        "dry_run": job.get("dry_run"),
        "creation_date": job.get("creation_date"),
        "end_date": job.get("end_date"),
    }
    response_info = schemas.UpdateJobResponse.model_validate(_response_info)
    return response_info


def merge_results(response_info, parameters, results=None):
    """Merge results.

    Args:
        response_info: response info
        parameters: parameters from prefect
        results: results from prefect (Default value = None)

    Returns:
        new response info
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
                    result, "metadata", "end_date", default=None
                )
                if isinstance(_end_date, str):
                    _end_date = datetime.fromisoformat(_end_date)
                if _end_date and end_date:
                    end_date = max(end_date, _end_date)
                elif _end_date:
                    end_date = _end_date
    if end_date:
        response_info["end_date"] = end_date.isoformat()
    return response_info
