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
import logging

from contextlib import contextmanager
from fastapi import Depends
from starlette.requests import HTTPConnection
from sqlalchemy.orm import Session

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.api import schemas
from wy_qcos.db.database import init_database
from wy_qcos.db.repositories import BaseRepository

logger = logging.getLogger(__name__)


_db_engine = None


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

    if is_super_admin and allow_super_admin:
        if "project_id" not in db_filters:
            del db_filters["project_id"]
        if "user_id" in db_filters:
            del db_filters["user_id"]
    if is_project_admin and allow_project_admin:
        if "user_id" in db_filters:
            del db_filters["user_id"]

    return db_filters


def run_callbacks(
    job_id, db_engine, job_status, backend, results, callbacks, user={}
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
    """
    success = Library.job_callback(
        job_id, job_status, backend, results, callbacks, user=user
    )
    try:
        db_update_job(job_id, db_engine, is_callback_success=success)
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
        if state_name != Constant.PREFECT_STATE_CANCELLING:
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
                return

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
    all_results = {}
    for result in results:
        sub_results = result.pop("sub_results", {})
        if sub_results:
            for sub_job_id, sub_result in sub_results.items():
                if not isinstance(sub_result, list):
                    sub_result = [sub_result]
                all_results[sub_job_id] = sub_result
        if job_id not in all_results:
            all_results[job_id] = []
        all_results[job_id].append(result)

    job_repo = None
    # create db session for agg jobs
    if len(all_results) > 1:
        with create_db_session(db_engine) as db_session:
            job_repo = JobRepository(db_session)

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
            # sub agg job
            # fetch agg job from database
            if job_repo:
                # Get the job record
                success, error, job_record = job_repo.get_job_by_uuid(_job_id)
                if not success or job_record is None:
                    logger.error(
                        f"Fetch agg job error {_job_id}: job not found"
                    )
                    continue
                user = {
                    "project_id": str(job_record.project_id),
                    "user_id": str(job_record.user_id),
                }
                callbacks_info = {
                    "is_run_callbacks": is_run_callbacks,
                    "callbacks": job_record.callbacks,
                    "backend": job_record.backend,
                    "user": user,
                }
                _profiling_types = job_record.profiling

        # handle profiling types
        for _result in _results:
            if _profiling_types:
                if Constant.PROFILING_TYPE_ALL in _profiling_types:
                    continue
                for _profiling_type in Constant.PROFILING_TYPES:
                    if _profiling_type == Constant.PROFILING_TYPE_ALL:
                        continue
                    if _profiling_type not in _profiling_types:
                        if _profiling_type in _result["profiling"]:
                            del _result["profiling"][_profiling_type]
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
        )


def _db_update_job(
    db_engine, job_id, job_status, results, progress=None, callbacks_info=None
):
    try:
        db_update_job(
            job_id,
            db_engine,
            job_status=job_status,
            job_results=results,
            progress=progress,
            ended_at=Library.get_current_datetime().isoformat(),
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
):
    """Update job fields in database.

    Args:
        job_id: job ID
        db_engine: database engine instance
        job_status: optional, job status to set (e.g., RUNNING)
        progress: optional, job progress (-1, 0-100) or None if not set
        job_results: optional, job_results or None if not set
        started_at: optional, job start time in ISO format or None if not set
        ended_at: optional, job end time or None if not set
        is_callback_success: optional, is_callback_success or None if not set

    Returns:
        True if successful, False otherwise
    """
    if db_engine is None:
        logger.error(f"Update job error {job_id}: db_engine is None")
        return False

    try:
        with create_db_session(db_engine) as db_session:
            job_repo = JobRepository(db_session)

            # Get the job record
            success, error, job_record = job_repo.get_job_by_uuid(job_id)
            if not success or job_record is None:
                logger.error(f"Update job error {job_id}: job not found")
                return False

            # Update job fields (only if provided)
            if job_status is not None:
                job_record.job_status = job_status
            if started_at is not None:
                job_record.started_at = started_at
            if progress is not None:
                job_record.progress = progress
            if job_results is not None:
                job_record.results = job_results
            if ended_at is not None:
                job_record.ended_at = ended_at
            if is_callback_success is not None:
                job_record.is_callback_success = is_callback_success

            try:
                job_repo.commit()
                job_repo.refresh(job_record)
                logger.info(
                    f"Successfully updated job {job_id}: "
                    f"job_status={job_status}, progress={progress}, "
                    f"job_results={job_results}, "
                    f"started_at={started_at}, ended_at={ended_at}, "
                    f"is_callback_success={is_callback_success}"
                )
                return True
            except Exception as e:
                job_repo.rollback()
                logger.error(
                    f"Update job error {job_id}: failed to commit: {str(e)}"
                )
                return False
    except Exception as e:
        logger.error(
            f"Update job error {job_id}: failed to create db session: {str(e)}"
        )
        return False
