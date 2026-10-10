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

import copy
import inspect
import json
import logging

from contextlib import contextmanager
from fastapi import Depends
from starlette.requests import HTTPConnection
from sqlalchemy.orm import Session

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.api import schemas
from wy_qcos.db.database import init_database
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.db.utils.job_storage_backend import (
    get_job_storage_backend,
)

logger = logging.getLogger(__name__)


_db_engine = None
_redis_client = None


def set_redis_client(redis_client):
    """Set redis client."""
    global _redis_client
    _redis_client = redis_client


def get_redis_client():
    """Get redis client.

    Returns:
        Redis client or None if not initialized
    """
    global _redis_client
    return _redis_client


def set_db_engine(engine):
    """Set db engine."""
    global _db_engine
    _db_engine = engine


def get_db_engine():
    """Get db engine.

    Returns:
        Database engine instance or None if not initialized
    """
    global _db_engine
    return _db_engine


def get_db_session(request: HTTPConnection) -> Session:
    """Get db session."""
    db_engine = request.app.state._db_engine

    session = Session(db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


def get_repository(repo: type[BaseRepository]):
    """Return database repository object, which contains operation function."""

    def get_repo(
        db_session: Session = Depends(get_db_session),
    ) -> BaseRepository:
        return repo(db_session)

    return get_repo


@contextmanager
def create_db_session(db_engine):
    session = Session(db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


def get_db_filters(
    auth_data, filters={}, allow_super_admin=False, allow_project_admin=False
):
    """Get db filters.

    Args:
        auth_data: auth data
        filters: jsonrpc filters
        allow_super_admin: allow super admin to query all resources
        allow_project_admin: allow project admin to query resources in project

    Returns:
        db filters
    """
    db_filters = {}
    all_projects = False
    all_users = False
    if not auth_data:
        return db_filters

    # init and assign admins
    is_super_admin = auth_data.get("is_super_admin", False)
    is_project_admin = auth_data.get("is_project_admin", False)
    if filters:
        if is_super_admin:
            all_projects = filters.get("all_projects", False)
        if is_project_admin:
            all_users = filters.get("all_users", False)
        if "all_projects" in filters:
            del filters["all_projects"]
        if "all_users" in filters:
            del filters["all_users"]

    # handle db filters
    if filters:
        db_filters = copy.deepcopy(filters)
    filter_project_id = db_filters.get("project_id", None)
    filter_user_id = db_filters.get("user_id", None)
    current_project_id = auth_data.get("project_id", None)
    current_user_id = auth_data.get("user_id", None)
    if not all_projects:
        if filter_project_id:
            if is_super_admin:
                db_filters["project_id"] = filter_project_id
            else:
                if filter_project_id != current_project_id:
                    db_filters["project_id"] = Constant.INVALID_PROJECT_ID
        else:
            db_filters["project_id"] = current_project_id
    if not all_users:
        if filter_user_id:
            if is_super_admin:
                db_filters["user_id"] = filter_user_id
            else:
                if filter_user_id != current_user_id:
                    db_filters["user_id"] = Constant.INVALID_USER_ID
        else:
            db_filters["user_id"] = current_user_id

    # filter job ids
    job_ids = db_filters.pop("job_ids", None)
    if job_ids:
        db_filters["id"] = job_ids

    # filter flavor ids
    flavor_ids = db_filters.pop("flavor_ids", None)
    if flavor_ids:
        db_filters["id"] = flavor_ids

    # filter device group ids
    group_ids = db_filters.pop("group_ids", None)
    if group_ids:
        db_filters["id"] = group_ids

    if is_super_admin and allow_super_admin:
        if "project_id" in db_filters:
            del db_filters["project_id"]
        if "user_id" in db_filters:
            del db_filters["user_id"]
    if is_project_admin and allow_project_admin:
        if "user_id" in db_filters:
            del db_filters["user_id"]

    return db_filters


def _redis_job_key(job_id, flow_run_id=None):
    """Build the redis key for a job's results record.

    The key follows the hierarchy
    ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}`` when
    ``flow_run_id`` is provided, otherwise
    ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}``.

    Args:
        job_id: job id
        flow_run_id: optional flow run id

    Returns:
        redis key string
    """
    if flow_run_id:
        return f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}"
    return f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/{job_id}"


def redis_get_job(job_id):
    """Get job record from redis.

    Returns the stored job dict or None when the key does not
    exist or redis is unavailable.

    Args:
        job_id: job id

    Returns:
        job dict or None
    """
    redis_client = get_redis_client()
    if redis_client is None:
        logger.error(
            f"Redis get job error {job_id}: redis client not initialized"
        )
        return None
    try:
        raw = redis_client.get(_redis_job_key(job_id))
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Redis get job error {job_id}: failed to read: {str(e)}")
        return None


def redis_update_job(
    job_id,
    job_status=None,
    progress=None,
    job_results=None,
    started_at=None,
    ended_at=None,
    is_callback_success=None,
    flow_run_id=None,
    backend=None,
    callbacks=None,
):
    """Update job fields in redis.

    Reads the existing record (if any), merges the provided fields
    and writes it back. When the key does not exist yet, a new
    record is created.

    Args:
        job_id: job id
        job_status: optional, job status to set
        progress: optional, job progress
        job_results: optional, job results to set
        started_at: optional, job start time in ISO format
        ended_at: optional, job end time or None
        is_callback_success: optional, callback success flag
        flow_run_id: optional, prefect flow run id (for sub-job
            matching by poll_job_results)
        backend: optional, backend device name
        callbacks: optional, callback list

    Returns:
        True if successful, False otherwise
    """
    redis_client = get_redis_client()
    if redis_client is None:
        logger.error(
            f"Redis update job error {job_id}: redis client not initialized"
        )
        return False

    key = _redis_job_key(job_id, flow_run_id)
    record = {}
    try:
        raw = redis_client.get(key)
        if raw is not None:
            record = json.loads(raw)
    except Exception as e:
        logger.error(
            f"Redis update job error {job_id}: failed to read "
            f"existing record: {str(e)}"
        )
        return False

    if job_status is not None:
        record["job_status"] = job_status
    if started_at is not None:
        record["started_at"] = started_at
    if progress is not None:
        record["progress"] = progress
    if job_results is not None:
        record["results"] = job_results
    if ended_at is not None:
        record["ended_at"] = ended_at
    if is_callback_success is not None:
        record["is_callback_success"] = is_callback_success
    if flow_run_id is not None:
        record["flow_run_id"] = flow_run_id
    if backend is not None:
        record["backend"] = backend
    if callbacks is not None:
        record["callbacks"] = callbacks

    try:
        redis_client.set(key, json.dumps(record))
        logger.info(
            f"Successfully updated job in redis {job_id}: "
            f"job_status={job_status}, progress={progress}, "
            f"started_at={started_at}, ended_at={ended_at}, "
            f"is_callback_success={is_callback_success}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Redis update job error {job_id}: failed to write: {str(e)}"
        )
        return False


def run_callbacks(
    job_id,
    db_engine,
    job_status,
    backend,
    results,
    callbacks,
    user={},
    results_db_storage=Constant.RESULTS_DB_STORAGE_DEFAULT,
    flow_run_id=None,
    ttl=None,
):
    """Run callbacks.

    Args:
        job_id: job id
        db_engine: db_engine
        job_status: job status
        backend: backend
        results: results
        callbacks: callbacks
        user: user related info
        results_db_storage: storage backend ("sql" or "redis")
        flow_run_id: optional, flow run id used as redis key
        ttl: optional, redis key TTL in seconds
    """
    success = Library.job_callback(
        job_id, job_status, backend, results, callbacks, user=user
    )
    try:
        db_update_job(
            job_id,
            db_engine,
            is_callback_success=success,
            results_db_storage=results_db_storage,
            flow_run_id=flow_run_id,
            ttl=ttl,
        )
    except Exception as e:
        logger.error(
            f"Update job is_callback_success error {job_id}: "
            f"failed to update job is_callback_success: {str(e)}"
        )


async def db_job_callback(
    flow, flow_run, state, results=None, is_run_callbacks=True
):
    """Job callback.

    Args:
        flow: flow
        flow_run: flow run
        state: flow state
        results: flow results
        is_run_callbacks: whether run callbacks or not
    """
    job_id = flow_run.name
    flow_run_id = str(flow_run.id)
    parameters = flow_run.parameters
    data = Library.get_nested_dict_value(
        parameters,
        "job_info",
        "data",
        default={},
    )
    profiling_types = data.get("profiling", [])
    callbacks = data.get("callbacks", [])
    backend = data.get("backend", None)
    db_config = data.get("db_config", {})
    results_db_storage = db_config.get(
        "results_db_storage",
        data.get("results_db_storage", Constant.RESULTS_DB_STORAGE_DEFAULT),
    )
    ttl = db_config.get("ttl")

    # Persist minimal sub-job context (flow_run_id/backend/callbacks)
    # so the parent job can later fetch sub-job info via the storage
    # backend. For SQL storage this is a no-op (the full job record is
    # already persisted at submission time).
    storage_backend = get_job_storage_backend(
        results_db_storage=results_db_storage,
        db_engine=get_redis_client()
        if results_db_storage == Constant.RESULTS_DB_STORAGE_REDIS
        else None,
    )
    try:
        storage_backend.store_sub_job_context(
            job_id,
            flow_run_id,
            backend=backend,
            callbacks=callbacks,
            ttl=ttl,
        )
    except Exception as e:
        logger.error(f"Store sub-job context error {job_id}: {str(e)}")

    # Get db_engine from global state
    db_engine = get_db_engine()
    if db_engine is None:
        # Try to initialize from flow_run parameters
        try:
            db_url = Library.get_nested_dict_value(
                parameters,
                "job_info",
                "global",
                "configs",
                "DATABASE",
                "QCOS_DATABASE_CONNECTION_URL",
                default=None,
            )
            if db_url is None:
                logger.error(
                    f"Update flow result into db error {job_id}: "
                    f"db_engine not initialized and DATABASE url not found"
                )
                return
            db_engine = init_database(db_url)
        except Exception as e:
            logger.error(
                f"Update flow result into db error {job_id}: "
                f"failed to initialize db_engine: {str(e)}"
            )
            return

    # Determine job_status based on flow state
    state_name = state.name.upper() if state.name else ""
    db_job_status = Constant.JOB_STATUS_UNKNOWN

    if state_name == Constant.PREFECT_STATE_COMPLETED:
        db_job_status = Constant.JOB_STATUS_COMPLETED
    elif state_name == Constant.PREFECT_STATE_FAILED:
        db_job_status = Constant.JOB_STATUS_FAILED
    elif state_name == Constant.PREFECT_STATE_CRASHED:
        db_job_status = Constant.JOB_STATUS_FAILED
    elif state_name == Constant.PREFECT_STATE_CANCELLING:
        db_job_status = Constant.JOB_STATUS_CANCELLED
    elif state_name == Constant.PREFECT_STATE_CANCELLED:
        db_job_status = Constant.JOB_STATUS_CANCELLED

    # Get results from parameter or state
    if results is None:
        if state_name not in [Constant.PREFECT_STATE_CANCELLING]:
            try:
                result_obj = state.result()
                # Check if result is a coroutine and await it
                if inspect.iscoroutine(result_obj):
                    results = await result_obj
                else:
                    results = result_obj
            except Exception as e:
                logger.error(
                    f"Update flow result into db error {job_id}: "
                    f"cannot get result from state: {str(e)}"
                )

    # Determine overall job_status from individual results,
    overall_job_status = db_job_status
    progress = None
    if overall_job_status in [Constant.JOB_STATUS_COMPLETED]:
        progress = 100
        for result in results:
            meta_data = result.get("metadata", {})
            result_status = meta_data.get(
                "status", Constant.JOB_STATUS_COMPLETED
            )
            if result_status == Constant.JOB_STATUS_FAILED:
                overall_job_status = Constant.JOB_STATUS_FAILED

    # Retrieve results from agg sub-jobs
    all_results = {job_id: []}
    if results:
        for result in results:
            sub_results = result.pop("sub_results", {})
            if sub_results:
                for sub_job_id, sub_result in sub_results.items():
                    if not isinstance(sub_result, list):
                        sub_result = [sub_result]
                    all_results[sub_job_id] = sub_result
            all_results[job_id].append(result)

    # build the storage backend once for all sub-jobs
    storage_backend = get_job_storage_backend(
        results_db_storage=results_db_storage,
        db_engine=get_redis_client()
        if results_db_storage == Constant.RESULTS_DB_STORAGE_REDIS
        else db_engine,
    )

    for _job_id, _results in all_results.items():
        _profiling_types = []
        if job_id == _job_id:
            # parent agg job or single job
            user = {
                "project_id": data.get("project_id", {}),
                "user_id": data.get("user_id", {}),
            }
            callbacks_info = {
                "is_run_callbacks": is_run_callbacks,
                "callbacks": callbacks,
                "backend": backend,
                "user": user,
            }
            _profiling_types = profiling_types
        else:
            # sub agg job: fetch job record via the storage backend
            job_record = storage_backend.get_job(_job_id)
            if job_record is None:
                continue
            user = {
                "project_id": job_record.project_id,
                "user_id": job_record.user_id,
            }
            callbacks_info = {
                "is_run_callbacks": is_run_callbacks,
                "callbacks": job_record.callbacks,
                "backend": job_record.backend or backend,
                "user": user,
            }
            _profiling_types = job_record.profiling

        # handle profiling types
        for _result in _results:
            if _profiling_types:  # expected profiling types in job submission
                if Constant.PROFILING_TYPE_ALL in _profiling_types:
                    continue
                for _profiling_type in Constant.PROFILING_TYPES:
                    if _profiling_type == Constant.PROFILING_TYPE_ALL:
                        continue
                    if _profiling_type not in _profiling_types:
                        if _profiling_type in _result["profiling"]:
                            del _result["profiling"][_profiling_type]
                            del _result["profiling"][
                                f"{_profiling_type}_started_at"
                            ]
                            del _result["profiling"][
                                f"{_profiling_type}_ended_at"
                            ]
            else:
                _result["profiling"] = {}

        # update database for job
        _db_update_job(
            db_engine,
            _job_id,
            overall_job_status,
            _results,
            progress=progress,
            callbacks_info=callbacks_info,
            results_db_storage=results_db_storage,
            flow_run_id=flow_run_id,
            ttl=ttl,
        )


def _db_update_job(
    db_engine,
    job_id,
    job_status,
    results,
    progress=None,
    callbacks_info=None,
    results_db_storage=Constant.RESULTS_DB_STORAGE_DEFAULT,
    flow_run_id=None,
    ttl=None,
):
    """Update job status and results.

    Dispatches to redis or sql backend based on
    results_db_storage. For redis storage, flow_run_id
    is used as the redis key.
    """
    try:
        db_update_job(
            job_id,
            db_engine,
            job_status=job_status,
            job_results=results,
            progress=progress,
            ended_at=Library.get_current_datetime().isoformat(),
            results_db_storage=results_db_storage,
            flow_run_id=flow_run_id,
            ttl=ttl,
        )
    except Exception as e:
        logger.error(
            f"Update job status error {job_id}: "
            f"failed to update job status: {str(e)}"
        )

    is_run_callbacks = callbacks_info.get("is_run_callbacks", False)
    backend = callbacks_info.get("backend", None)
    callbacks = callbacks_info.get("callbacks", [])
    user = callbacks_info.get("user", {})

    if is_run_callbacks:
        run_callbacks(
            job_id,
            db_engine,
            job_status,
            backend,
            results,
            callbacks,
            user=user,
            results_db_storage=results_db_storage,
            flow_run_id=flow_run_id,
            ttl=ttl,
        )


def db_update_job(
    job_id,
    db_engine,
    job_status: str | None = None,
    progress: int | None = None,
    job_results: schemas.SetJobResultsRequest | None = None,
    started_at: str | None = None,
    ended_at=None,
    is_callback_success=None,
    results_db_storage=Constant.RESULTS_DB_STORAGE_DEFAULT,
    flow_run_id=None,
    ttl=None,
):
    """Update job fields in the configured storage backend.

    Dispatches to a SQL or Redis backend based on
    ``results_db_storage``. For redis storage, ``flow_run_id`` is
    used as the redis key when provided; otherwise ``job_id`` is
    used.

    Args:
        job_id: job ID
        db_engine: database engine instance
        job_status: optional, job status to set (e.g., RUNNING)
        progress: optional, job progress (-1, 0-100) or None if not set
        job_results: optional, job_results or None if not set
        started_at: optional, job start time in ISO format or None
        ended_at: optional, job end time or None if not set
        is_callback_success: optional, is_callback_success or None
        results_db_storage: storage backend ("sql" or "redis")
        flow_run_id: optional, flow run id used as redis key
        ttl: optional, redis key TTL in seconds

    Returns:
        True if successful, False otherwise
    """
    storage_backend = get_job_storage_backend(
        results_db_storage=results_db_storage,
        db_engine=get_redis_client()
        if results_db_storage == Constant.RESULTS_DB_STORAGE_REDIS
        else db_engine,
    )
    return storage_backend.update_job(
        job_id,
        job_status=job_status,
        progress=progress,
        job_results=job_results,
        started_at=started_at,
        ended_at=ended_at,
        is_callback_success=is_callback_success,
        flow_run_id=flow_run_id,
        ttl=ttl,
    )
