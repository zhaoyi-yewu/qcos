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

import logging
import time
from datetime import datetime

from fastapi import Depends

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import job_api_v1
from wy_qcos.db.models import Job
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.db.utils.db_utils import get_db_filters, get_repository
from wy_qcos.common import args_schema, errors
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.task_manager import scheduler
from .dependencies.authentication import (
    auth,
    fill_project_user_id,
    validate_virtual_instance,
)

logger = logging.getLogger(__name__)
module_name = "JOB"


@job_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[
        jsonrpc_errors.BadRequestError,
        jsonrpc_errors.ConflictError,
        jsonrpc_errors.InternalServerError,
    ],
)
def submit_job(
    body: schemas.SubmitJobRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> schemas.SubmitJobResponse:
    """Submit job.

    Args:
        body(schemas.SubmitJobRequest): job info
        auth_data: auth data
        job_repo: job repository

    Returns:
        job info
    """
    func_name = "submit_job"
    logger.info(f"Call {func_name}: {body.job_id}")
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
    qec_options = body.qec_options
    profiling = body.profiling
    callbacks = body.callbacks
    dry_run = body.dry_run
    code_compression_level = body.code_compression_level
    tags = body.tags

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
    elif code_type in Constant.CODE_TYPES_ALL_QASM:
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

    # validate: code_compression_level
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_range(
            code_compression_level,
            "code_compression_level",
            0,
            9,
        ),
    )

    # validate: tags
    if tags is not None:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_schema(tags, args_schema.TAGS_SCHEMA)
            if not isinstance(tags, list)
            else (True, None),
        )

    # set job_status
    job_status = Constant.JOB_STATUS_QUEUED
    body.job_status = job_status

    # get device
    device_manger = scheduler.get_device_manager()
    devices = device_manger.get_devices()

    # validate auth of virtual instance
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        validate_virtual_instance(auth_data, backend=backend),
    )

    # validate: backend
    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_values_enum(backend, "backend", devices),
    )

    # get driver from backend
    device = devices.get(backend)
    driver = device.get_driver()
    device_status = device.get_status()
    enable_device = device.enable

    # check device status
    if not enable_device:
        jsonrpc_errors.handle_error_conflict(
            module_name, func_name, (False, "device is disabled")
        )
    elif device_status not in [
        device.DEVICE_STATUS_ONLINE,
        device.DEVICE_STATUS_BUSY,
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

    # validate: qec_options
    if qec_options:
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_schema(
                qec_options,
                args_schema.QEC_OPTIONS,
                allow_none=True,
            ),
        )
        qec_options_schema = driver.get_qec_options_schema()
        jsonrpc_errors.handle_error_bad_requests(
            module_name,
            func_name,
            Library.validate_schema(
                qec_options,
                qec_options_schema,
                allow_none=True,
            ),
            param_name="qec_options",
        )

    # get supported_code_types
    supported_code_types = transpiler.get_supported_code_types()
    if supported_code_types is None or len(supported_code_types) == 0:
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

    # generate created_at
    created_at = Library.get_current_datetime()
    body.created_at = created_at
    started_at = None
    ended_at = None

    # Extract user_id and project_id from auth_data if available
    fill_project_user_id(body, auth_data)

    # Begin transaction and create job record in database
    job_record = None
    try:
        # check max job count is reached
        all_jobs_count = job_repo.get_jobs_count()
        if all_jobs_count >= Config.DEFAULT.MAX_JOBS:
            jsonrpc_errors.handle_error_internal_server(
                module_name,
                func_name,
                (
                    False,
                    f"Current job count exceeds max job limit: "
                    f"{Config.DEFAULT.MAX_JOBS}",
                ),
            )

        # check max job count is reached per user/virtual instance
        filters = {
            "user_id": body.user_id,
        }
        user_jobs_count = job_repo.get_jobs_count(filters=filters)
        if user_jobs_count >= Config.USERS.MAX_JOBS:
            jsonrpc_errors.handle_error_internal_server(
                module_name,
                func_name,
                (
                    False,
                    f"Current job count exceeds max job limit per user: "
                    f"{Config.USERS.MAX_JOBS}",
                ),
            )

        # Check if job_id already exists
        if body.job_id:
            success, _, existing_job = job_repo.get_job_by_uuid(body.job_id)
            if success and existing_job:
                jsonrpc_errors.handle_error_internal_server(
                    module_name,
                    func_name,
                    (False, f"Job ID already exists: {body.job_id}"),
                )

        # Create job record in database without auto commit
        success, e, job_record = job_repo.create_job(body, auto_commit=False)
        if not success or e:
            jsonrpc_errors.handle_error_internal_server(
                module_name,
                func_name,
                (False, f"Failed to create job record: {str(e)}"),
            )
        # Verify job_record is not None after creation
        if not job_record:
            jsonrpc_errors.handle_error_internal_server(
                module_name,
                func_name,
                (False, "Job record is None after creation"),
            )
    except Exception as db_err:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, f"Database error: {str(db_err)}"),
        )

    # update job id by db if empty
    if not job_id:
        body.job_id = job_record.id

    # auto schedule
    job_scheduling_at = time.time()
    # TODO(zhaoyi): auto schedule
    job_schedule_duration = time.time() - job_scheduling_at
    extra_job_data_info = {"job_schedule_duration": job_schedule_duration}

    # submit job
    res = {}
    err = None
    try:
        res, err = scheduler.submit(
            body, extra_job_data_info=extra_job_data_info
        )
        # Extract flow_run_id from scheduler response and update job record
        if res and "flow_run_id" in res:
            job_record.flow_run_id = res["flow_run_id"]

        # Scheduler succeeded - commit DB transaction
        if not err:
            try:
                job_repo.commit()
                # Refresh to ensure object has latest committed data
                job_repo.refresh(job_record)
                logger.debug(
                    f"Committed job record {job_record.id} "
                    "after scheduler success"
                )
            except Exception as commit_err:
                logger.error(f"Failed to commit transaction: {commit_err}")
                job_repo.rollback()
                jsonrpc_errors.handle_error_internal_server(
                    module_name,
                    func_name,
                    (False, f"Transaction commit failed: {commit_err}"),
                )
    except errors.WorkFlowError as e:
        # Rollback DB transaction if scheduler.submit fails
        try:
            job_repo.rollback()
            if job_record:
                logger.warning(
                    f"Rolled back job record {job_record.id} "
                    f"due to scheduler error: {str(e)}"
                )
            else:
                logger.warning(
                    f"Rolled back transaction due to scheduler error: {str(e)}"
                )
        except Exception as rollback_err:
            logger.error(f"Failed to rollback transaction: {rollback_err}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
    # handle submit response - scheduler returned error
    if err:
        # Rollback DB transaction
        try:
            job_repo.rollback()
            if job_record:
                logger.warning(
                    f"Rolled back job record {job_record.id} "
                    f"due to scheduler error: {err}"
                )
            else:
                logger.warning(
                    f"Rolled back transaction due to scheduler error: {err}"
                )
        except Exception as rollback_err:
            logger.error(f"Failed to rollback transaction: {rollback_err}")
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, err)
        )
    _response_info = {
        "job_id": body.job_id,
        "job_name": job_name,
        "project_id": body.project_id,
        "user_id": body.user_id,
        "job_type": job_type,
        "job_status": job_status,
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
        "code_compression_level": code_compression_level,
        "tags": tags,
        "qec_options": qec_options,
        "created_at": created_at,
        "updated_at": created_at,
        "started_at": started_at,
        "ended_at": ended_at,
    }
    response_info = schemas.SubmitJobResponse.model_validate(_response_info)
    return response_info


@job_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.InternalServerError],
)
def get_job_status(
    body: schemas.GetJobStatusRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> schemas.GetJobStatusResponse:
    """Get job status.

    Args:
        body(schemas.GetJobStatusRequest): job_id: job ID
        auth_data: auth data
        job_repo: job repository

    Returns:
        job status
    """
    func_name = "get_job_status"
    logger.info(f"Call {func_name}: {body}")

    job_id = body.job_id

    # query job record from database with user filters
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )
    success, error, job_record = job_repo.get_job_by_uuid(
        job_id, filters=db_filters
    )
    if not success or job_record is None:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )

    # construct response from database record
    _response_info = job_record.asdict()
    _response_info["job_id"] = _response_info.pop("id", job_id)

    response_info = schemas.GetJobStatusResponse.model_validate(_response_info)
    return response_info


@job_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.InternalServerError],
)
def get_job_results(
    body: schemas.GetJobResultsRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> schemas.GetJobResultsResponse:
    """Get job results.

    Args:
        body(schemas.GetJobResultsRequest): job_id: job ID
        auth_data: auth data
        job_repo: job repository

    Returns:
        job results
    """
    func_name = "get_job_results"
    logger.info(f"Call {func_name}: {body}")

    job_id = body.job_id

    # query job record from database with user filters
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )
    success, error, job_record = job_repo.get_job_by_uuid(
        job_id, filters=db_filters
    )
    if not success or job_record is None:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )

    # construct response from database record
    _response_info = job_record.asdict()
    _response_info["job_id"] = _response_info.pop("id", job_id)

    response_info = schemas.GetJobResultsResponse.model_validate(
        _response_info
    )
    return response_info


@job_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES},
    errors=[jsonrpc_errors.InternalServerError],
)
def get_jobs(
    body: schemas.GetJobsRequest | None = None,
    filters: dict | None = None,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> list[schemas.GetJobStatusResponse]:
    """Get job list with optional filtering.

    Args:
        body(schemas.GetJobsRequest): job requests body
        filters: filters
        auth_data: auth data
        job_repo: job repository

    Returns:
        job list sorted by created_at in descending order
    """
    func_name = "get_jobs"
    logger.info(f"Call {func_name}: body={body}, filters: {filters}")

    # Query job record from database with user filters
    db_filters = get_db_filters(auth_data, filters=filters)
    success, error, job_records = job_repo.get_jobs(db_filters)
    if not success or job_records is None:
        return []

    # Sort by created_at in descending order
    job_records = sorted(
        job_records,
        key=lambda x: x.created_at if x.created_at else "",
        reverse=True,
    )

    # Construct response
    response_list = []
    for job_record in job_records:
        _response_info = job_record.asdict()
        _response_info["job_id"] = _response_info.pop("id")
        response_info = schemas.GetJobStatusResponse.model_validate(
            _response_info
        )
        response_list.append(response_info)
    return response_list


@job_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES}, errors=[]
)
def update_job(
    body: schemas.UpdateJobRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> schemas.UpdateJobResponse:
    """Update job.

    Args:
        body(schemas.UpdateJobsRequest): job info
        auth_data: auth data
        job_repo: job repository

    Returns:
        update job param
    """
    func_name = "update_job"
    logger.info(f"Call {func_name}: {body}")

    job_id = body.job_id
    updated = False

    # query job record from database with user filters
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )
    success, error, job_record = job_repo.get_job_by_uuid(
        job_id, filters=db_filters
    )
    if not success or job_record is None:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )

    try:
        # Validate job_priority with scheduler before modifying database
        if body.job_priority is not None:
            # check job status
            if job_record.job_status != Constant.JOB_STATUS_QUEUED:
                err_msg = (
                    f"Job: '{job_id}' is not in QUEUED state. Can't update_job"
                )
                jsonrpc_errors.handle_error_internal_server(
                    module_name, func_name, (False, err_msg)
                )

            # Call scheduler first to validate before modifying DB
            parameters = {
                "job_priority": body.job_priority,
            }
            try:
                flow_run, err = scheduler.update_flow(
                    flow_run_id=job_record.flow_run_id, parameters=parameters
                )
            except errors.WorkFlowError as e:
                jsonrpc_errors.handle_error_internal_server(
                    module_name, func_name, (False, str(e))
                )
            if err is not None:
                jsonrpc_errors.handle_error_internal_server(
                    module_name, func_name, (False, err)
                )
            job_record.flow_run_id = flow_run["flow_run_id"]
            updated = True

        # Only update database after scheduler succeeded
        # (or for fields that don't depend on scheduler)
        if body.job_name is not None:
            job_record.job_name = body.job_name
            updated = True
        if body.description is not None:
            job_record.description = body.description
            updated = True
        if body.job_priority is not None:
            job_record.job_priority = body.job_priority
            updated = True

        if updated:
            job_record.updated_at = Library.get_current_datetime()

        # Commit database changes
        job_repo.commit()
        job_repo.refresh(job_record)

    except Exception as e:
        # Rollback transaction on any error
        job_repo.rollback()
        logger.error(f"Failed to update job {job_id}: {str(e)}")
        # Re-raise the exception
        raise

    # construct response from database record
    _response_info = job_record.asdict()
    _response_info["job_id"] = _response_info.pop("id")

    response_info = schemas.UpdateJobResponse.model_validate(_response_info)
    return response_info


@job_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES}, errors=[]
)
def cancel_jobs(
    body: schemas.CancelJobsRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> list[schemas.CancelJobsResponse]:
    """Cancel job.

    Args:
        body(schemas.CancelJobsRequest): job_ids: job IDs
        auth_data: auth data
        job_repo: job repository

    Returns:
        cancelled jobs info
    """
    func_name = "cancel_jobs"
    logger.info(f"Call {func_name}: {body}")

    job_ids = body.job_ids

    # get unique job_ids
    job_ids = list(dict.fromkeys(job_ids))
    flow_run_id_dict = {}
    flow_run_id_list = []

    # Get job run ids
    for job_id in job_ids:
        # query job record from database with user filters
        db_filters = get_db_filters(
            auth_data, allow_super_admin=True, allow_project_admin=True
        )
        success, error, job_record = job_repo.get_job_by_uuid(
            job_id, filters=db_filters
        )
        if success and job_record:
            flow_run_id_dict[job_record.flow_run_id] = job_id
            flow_run_id_list.append(job_record.flow_run_id)

    # cancel jobs
    cancelled_flow_run_list = scheduler.cancel_flows(flow_run_id_list)

    # construct response using flow_run_id_dict to map back to job_ids
    response_info = [
        schemas.CancelJobsResponse(
            job_id=flow_run_id_dict.get(flow_run_info.get("flow_run_id"))
        )
        for flow_run_info in cancelled_flow_run_list
    ]
    return response_info


@job_api_v1.method(
    openapi_extra={"allowed_roles": Constant.ALL_ROLES}, errors=[]
)
def delete_jobs(
    body: schemas.DeleteJobsRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> list[schemas.DeleteJobsResponse]:
    """Delete job.

    Args:
        body(schemas.DeleteJobsRequest): job_ids: job IDs, force: force delete
        auth_data: auth data
        job_repo: job repository

    Returns:
        deleted jobs info
    """
    func_name = "delete_jobs"
    logger.info(f"Call {func_name}: {body}")

    job_ids = body.job_ids
    force = body.force

    # get unique job_ids
    job_ids = list(dict.fromkeys(job_ids))
    flow_run_id_dict = {}
    flow_run_id_list = []

    # Update job status to DELETING in database
    for job_id in job_ids:
        # query job record from database with user filters
        db_filters = get_db_filters(
            auth_data, allow_super_admin=True, allow_project_admin=True
        )
        success, error, job_record = job_repo.get_job_by_uuid(
            job_id, filters=db_filters
        )
        if success and job_record:
            flow_run_id_dict[job_record.flow_run_id] = job_id
            flow_run_id_list.append(job_record.flow_run_id)
            job_record.job_status = Constant.JOB_STATUS_DELETING
            try:
                job_repo.commit()
                job_repo.refresh(job_record)
            except Exception as e:
                job_repo.rollback()
                logger.warning(
                    f"Failed to update job {job_id} status to DELETING: {e}"
                )

    # delete jobs from scheduler
    try:
        if force:
            # Force delete: directly delete without waiting for scheduler
            logger.info(f"Force deleting {len(flow_run_id_list)} jobs")
        deleted_flow_run_list = scheduler.delete_flows(flow_run_id_list)
    except Exception as e:
        # If scheduler delete fails, rollback database changes
        if not force:
            jsonrpc_errors.handle_error_internal_server(
                module_name,
                func_name,
                (False, f"Failed to delete jobs: {str(e)}"),
            )
        else:
            logger.warning(f"Force delete failed (non-critical): {str(e)}")
            deleted_flow_run_list = []

    # Handle scheduler returned error
    if not deleted_flow_run_list and not force:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (False, "No jobs are deleted, jobs may in RUNNING state"),
        )

    # If force delete and no jobs returned from scheduler, construct response
    # from remaining flow_run_ids and delete from database anyway
    if force and not deleted_flow_run_list:
        deleted_flow_run_list = [
            {"flow_run_id": fid, "state": Constant.JOB_STATUS_DELETED}
            for fid in flow_run_id_list
        ]
        logger.info(
            f"Force delete: scheduler returned empty, "
            f"deleting {len(deleted_flow_run_list)} jobs from database anyway"
        )

    # Delete jobs from database
    for flow_run_info in deleted_flow_run_list:
        flow_run_id = flow_run_info["flow_run_id"]
        job_id = flow_run_id_dict[flow_run_id]
        if job_id is not None:
            try:
                success, error = job_repo.delete_by_uuid(Job, str(job_id))
                if not success or error:
                    logger.warning(
                        f"Failed to delete job {job_id} from database: {error}"
                    )
                else:
                    logger.info(
                        f"Successfully deleted job {job_id} from database"
                    )
            except Exception as e:
                logger.error(
                    f"Error deleting job {job_id} from database: {str(e)}"
                )

    # construct response using flow_run_id_dict to map back to job_ids
    response_info = [
        schemas.DeleteJobsResponse(
            job_id=flow_run_id_dict.get(flow_run_info.get("flow_run_id")),
            job_status=flow_run_info.get("state"),
        )
        for flow_run_info in deleted_flow_run_list
    ]
    return response_info


@job_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
    errors=[jsonrpc_errors.NotFoundError, jsonrpc_errors.InternalServerError],
)
def set_job_results(
    body: schemas.SetJobResultsRequest,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> schemas.SetJobResultsResponse:
    """Set job results for existing job.

    Args:
        body(schemas.SetJobResultsRequest): job_id: job ID
        auth_data: auth data
        job_repo: job repository
    """
    func_name = "set_job_results"
    logger.info(f"Call {func_name}: {body}")

    job_id = body.job_id
    new_results = body.results
    db_new_results = []

    jsonrpc_errors.handle_error_bad_requests(
        module_name,
        func_name,
        Library.validate_schema(new_results, args_schema.SOURCE_SET_RESULTS),
    )

    # query job record from database with user filters
    db_filters = get_db_filters(
        auth_data, allow_super_admin=True, allow_project_admin=True
    )
    success, error, job_record = job_repo.get_job_by_uuid(
        job_id, filters=db_filters
    )
    if not success or job_record is None:
        jsonrpc_errors.handle_error_not_found(
            module_name, func_name, (False, f"Job: '{job_id}' is not found")
        )

    # get source_code list from job_record
    source_code_list = job_record.source_code or []

    # get count in source code list
    source_code_list_count = len(source_code_list)

    # get ended_at
    ended_at = Library.get_current_datetime()
    ended_at_str = (
        ended_at.isoformat() if isinstance(ended_at, datetime) else ended_at
    )

    # check length of new results/errors
    if new_results and len(new_results) != source_code_list_count:
        jsonrpc_errors.handle_error_internal_server(
            module_name,
            func_name,
            (
                False,
                "Length of new results should be the same as "
                "the length of the source code list",
            ),
        )

    # update results/errors
    is_failed = False
    for i in range(source_code_list_count):
        new_result = new_results[i]
        # Extract callback_success if present
        callback_success = new_result.pop("is_callback_success", True)
        db_new_result = {
            "metadata": {
                "results_fetch_mode": Constant.RESULTS_FETCH_MODE_SET,
                "status": Constant.JOB_STATUS_UNKNOWN,
                "ended_at": ended_at_str,
                "is_callback_success": callback_success,
            },
        }
        if "code" in new_result:
            # failed and set error message
            db_new_result["error"] = new_result
            db_new_result["metadata"]["status"] = Constant.JOB_STATUS_FAILED
            is_failed = True
        else:
            # success and set new results
            db_new_result.update(new_result)
            db_new_result["metadata"]["status"] = Constant.JOB_STATUS_COMPLETED
        db_new_results.append(db_new_result)
    job_status = (
        Constant.JOB_STATUS_FAILED
        if is_failed
        else Constant.JOB_STATUS_COMPLETED
    )

    # update job record in database
    job_record.job_status = job_status
    job_record.results = db_new_results
    job_record.ended_at = ended_at
    job_record.updated_at = Library.get_current_datetime()
    try:
        job_repo.commit()
        job_repo.refresh(job_record)
    except Exception as e:
        job_repo.rollback()
        jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )

    # get backend from job_record
    backend = job_record.backend

    # run callbacks
    callbacks = job_record.callbacks

    # Run callbacks using Library.job_callback
    if callbacks:
        # user info
        user = {
            "project_id": str(job_record.project_id),
            "user_id": str(job_record.user_id),
        }
        success = Library.job_callback(
            str(job_id),
            job_status,
            backend,
            db_new_results,
            callbacks,
            user=user,
        )
        if not success:
            logger.warning(f"Job callback execution failed for job {job_id}")

    _response_info = {
        "job_id": job_id,
        "job_status": job_status,
        "backend": backend,
    }

    response_info = schemas.SetJobResultsResponse.model_validate(
        _response_info
    )
    return response_info
