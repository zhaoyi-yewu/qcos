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

"""Job results storage backend abstraction.

Provides a unified interface (:class:`JobStorageBackend`) for persisting
and retrieving job records regardless of the underlying store (SQL
database or Redis). Callers obtain a concrete backend through
:func:`get_job_storage_backend` based on the ``results_db_storage``
selection (``"sql"`` or ``"redis"``, see :class:`Constant`).

When ``results_db_storage`` is omitted it defaults to
:attr:`Constant.RESULTS_DB_STORAGE_DEFAULT` (``"sql"``), preserving the
original behaviour.
"""

import json
import logging

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from wy_qcos.api import schemas
from wy_qcos.common.constant import Constant
from wy_qcos.db.repositories.job import JobRepository

logger = logging.getLogger(__name__)


@contextmanager
def _create_sql_session(db_engine):
    """Create a short-lived SQLAlchemy session.

    Mirrors ``db_utils.create_db_session`` so that this module stays
    self-contained (no circular import with ``db_utils``).
    """
    session = Session(db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


@dataclass
class JobRecord:
    """Uniform view of a job record across storage backends.

    job_id: job identifier.
    project_id: project id of the job owner.
    user_id: user id of the job owner.
    backend: backend device name.
    callbacks: callback list configured for the job.
    profiling: expected profiling types list.
    """

    job_id: Any = None
    project_id: Any = None
    user_id: Any = None
    backend: Any = None
    callbacks: list = field(default_factory=list)
    profiling: list = field(default_factory=list)

    @classmethod
    def from_sql_model(cls, job_record):
        """Build a :class:`JobRecord` from a SQLAlchemy Job model."""
        return cls(
            job_id=str(job_record.id),
            project_id=str(job_record.project_id),
            user_id=str(job_record.user_id),
            backend=job_record.backend,
            callbacks=job_record.callbacks,
            profiling=job_record.profiling,
        )

    @classmethod
    def from_redis_dict(cls, job_id, record):
        """Build a :class:`JobRecord` from a redis job dict."""
        return cls(
            job_id=job_id,
            project_id=record.get("project_id", {}),
            user_id=record.get("user_id", {}),
            backend=record.get("backend"),
            callbacks=record.get("callbacks", []),
            profiling=record.get("profiling", []),
        )


class JobStorageBackend(ABC):
    """Abstract base class for job results storage backends."""

    @property
    @abstractmethod
    def storage_type(self) -> str:
        """Return the storage type identifier (``sql`` or ``redis``)."""

    @abstractmethod
    def get_job(self, job_id, flow_run_id=None) -> JobRecord | None:
        """Retrieve a job record by id.

        Args:
            job_id: job id.
            flow_run_id: optional flow run id; when provided the redis
                key includes both ``job_id`` and ``flow_run_id``.

        Returns:
            :class:`JobRecord` or ``None`` when not found.
        """

    @abstractmethod
    def update_job(
        self,
        job_id,
        job_status: str | None = None,
        progress: int | None = None,
        job_results: schemas.SetJobResultsRequest | None = None,
        started_at: str | None = None,
        ended_at=None,
        is_callback_success=None,
        flow_run_id=None,
        ttl=None,
    ) -> bool:
        """Update job fields in the underlying store.

        Only provided (non-``None``) fields are written.

        Args:
            job_id: job id.
            job_status: optional job status.
            progress: optional progress value.
            job_results: optional job results.
            started_at: optional ISO start time.
            ended_at: optional end time.
            is_callback_success: optional callback success flag.
            flow_run_id: optional flow run id; used as the redis key
                for redis storage.
            ttl: optional redis key TTL in seconds; when provided the
                redis key is set to expire after ``ttl`` seconds so
                it is cleaned up automatically.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """

    def store_sub_job_context(
        self,
        job_id,
        flow_run_id,
        backend=None,
        callbacks=None,
        ttl=None,
    ) -> bool:
        """Persist minimal sub-job context used for later lookup.

        For redis storage this records ``flow_run_id`` / ``backend`` /
        ``callbacks`` so that the parent job can later fetch sub-job
        info. SQL storage already persists the full job record in the
        database at submission time, so this is a no-op there.

        Args:
            job_id: job id; used as part of the redis key.
            flow_run_id: flow run id; used as part of the redis key.
            backend: optional backend device name.
            callbacks: optional callback list.
            ttl: optional redis key TTL in seconds; when provided the
                redis key is set to expire after ``ttl`` seconds so
                it is cleaned up automatically.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        return True


class SqlJobStorageBackend(JobStorageBackend):
    """SQL database storage backend.

    Each operation creates a short-lived SQLAlchemy session. Job
    records are read/written via :class:`JobRepository`.
    """

    def __init__(self, db_engine):
        self._db_engine = db_engine

    @property
    def storage_type(self) -> str:
        return Constant.RESULTS_DB_STORAGE_SQL

    @property
    def db_engine(self):
        """Return the database engine (may be ``None``)."""
        return self._db_engine

    def get_job(self, job_id, flow_run_id=None) -> JobRecord | None:
        if self._db_engine is None:
            logger.error(f"Fetch job error {job_id}: db_engine is None")
            return None
        try:
            with _create_sql_session(self._db_engine) as db_session:
                job_repo = JobRepository(db_session)
                success, _error, job_record = job_repo.get_job_by_uuid(job_id)
                if not success or job_record is None:
                    logger.error(
                        f"Fetch agg job error {job_id}: job not found"
                    )
                    return None
                return JobRecord.from_sql_model(job_record)
        except Exception as e:
            logger.error(f"Fetch job error {job_id}: failed to read: {str(e)}")
            return None

    def update_job(
        self,
        job_id,
        job_status: str | None = None,
        progress: int | None = None,
        job_results: schemas.SetJobResultsRequest | None = None,
        started_at: str | None = None,
        ended_at=None,
        is_callback_success=None,
        flow_run_id=None,
        ttl=None,
    ) -> bool:
        if self._db_engine is None:
            logger.error(f"Update job error {job_id}: db_engine is None")
            return False

        try:
            with _create_sql_session(self._db_engine) as db_session:
                job_repo = JobRepository(db_session)

                success, _error, job_record = job_repo.get_job_by_uuid(job_id)
                if not success or job_record is None:
                    logger.error(f"Update job error {job_id}: job not found")
                    return False

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
                        f"job_status={job_status}, "
                        f"progress={progress}, "
                        f"job_results={job_results}, "
                        f"started_at={started_at}, "
                        f"ended_at={ended_at}, "
                        f"is_callback_success="
                        f"{is_callback_success}"
                    )
                    return True
                except Exception as e:
                    job_repo.rollback()
                    logger.error(
                        f"Update job error {job_id}: failed to "
                        f"commit: {str(e)}"
                    )
                    return False
        except Exception as e:
            logger.error(
                f"Update job error {job_id}: failed to create db "
                f"session: {str(e)}"
            )
            return False


class RedisJobStorageBackend(JobStorageBackend):
    """Redis storage backend.

    Stores each job record as a JSON document under the key
    ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}`` when
    ``flow_run_id`` is provided (so sub-jobs can be matched by
    ``poll_job_results``), otherwise
    ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}``.

    On every update the record is also published on the pub/sub
    channel ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}`` so
    subscribers can track progress and terminal status without
    polling.
    """

    def __init__(self, redis_client):
        self._redis_client = redis_client

    @property
    def storage_type(self) -> str:
        return Constant.RESULTS_DB_STORAGE_REDIS

    @staticmethod
    def _redis_job_key(job_id, flow_run_id=None):
        """Build the redis key for a job's results record.

        The key follows the hierarchy
        ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}`` when
        ``flow_run_id`` is provided, otherwise
        ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}``.

        Args:
            job_id: job id.
            flow_run_id: optional flow run id.

        Returns:
            redis key string.
        """
        if "vdev-wirecut-" in job_id:
            job_id = job_id.replace("vdev-wirecut-", "")

        if flow_run_id:
            return (
                f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}"
            )
        return f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/{job_id}"

    def _client_or_log(self, job_id, action):
        """Return the redis client or log an error and ``None``."""
        if self._redis_client is None:
            logger.error(
                f"Redis {action} job error {job_id}: redis client "
                f"not initialized"
            )
            return None
        return self._redis_client

    def _read_record(self, redis_client, redis_key):
        """Read and parse the existing redis record (or ``{}``)."""
        try:
            raw = redis_client.get(redis_key)
            if raw is not None:
                return json.loads(raw)
        except Exception as e:
            logger.error(
                f"Redis update job error: failed to read existing "
                f"record: {str(e)}"
            )
            raise
        return {}

    def get_job(self, job_id, flow_run_id=None) -> JobRecord | None:
        redis_client = self._client_or_log(job_id, "get")
        if redis_client is None:
            return None
        try:
            record = self._read_record(
                redis_client,
                self._redis_job_key(job_id, flow_run_id),
            )
            if not record:
                return None
            return JobRecord.from_redis_dict(job_id, record)
        except Exception as e:
            logger.error(
                f"Redis get job error {job_id}: failed to read: {str(e)}"
            )
            return None

    def update_job(
        self,
        job_id,
        job_status: str | None = None,
        progress: int | None = None,
        job_results: schemas.SetJobResultsRequest | None = None,
        started_at: str | None = None,
        ended_at=None,
        is_callback_success=None,
        flow_run_id=None,
        ttl=None,
    ) -> bool:
        redis_client = self._client_or_log(job_id, "update")
        if redis_client is None:
            return False

        redis_key = self._redis_job_key(job_id, flow_run_id)
        try:
            record = self._read_record(redis_client, redis_key)
        except Exception:
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

        try:
            redis_client.set(redis_key, json.dumps(record))
            if ttl is not None and ttl > 0:
                redis_client.expire(redis_key, ttl)
                logger.debug(
                    "Redis update job %s: set TTL=%ss for key %s",
                    job_id,
                    ttl,
                    redis_key,
                )
            logger.info(
                f"Successfully updated job in redis {job_id}: "
                f"job_status={job_status}, progress={progress}, "
                f"started_at={started_at}, ended_at={ended_at}, "
                f"is_callback_success={is_callback_success}"
            )
            # Publish the updated record on the wirecut sub-job
            # channel so the parent wirecut flow can track sub-job
            # progress and terminal status via pub/sub instead of
            # polling. The channel name embeds the redis key id
            # (flow_run_id when available) so the subscriber can
            # match the notification back to its sub-job. Publishing
            # on every update (not only terminal status) lets the
            # parent compute aggregated progress from sub-job
            # progress values.
            # Publish on the pub/sub channel so the parent wirecut
            # flow can track sub-job progress and terminal status
            # via pub/sub instead of polling. The channel follows the
            # same hierarchy as the redis key
            # ({REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}) so
            # the subscriber can match notifications to sub-jobs.
            if flow_run_id is not None:
                channel = (
                    f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/{job_id}/"
                    f"{flow_run_id}"
                )
                try:
                    redis_client.publish(channel, json.dumps(record))
                    logger.debug(
                        f"Redis update job {job_id}: published "
                        f"notification on channel {channel}"
                    )
                except Exception as pub_err:
                    logger.warning(
                        f"Redis update job {job_id}: failed to "
                        f"publish notification: {str(pub_err)}"
                    )
            return True
        except Exception as e:
            logger.error(
                f"Redis update job error {job_id}: failed to write: {str(e)}"
            )
            return False

    def store_sub_job_context(
        self,
        job_id,
        flow_run_id,
        backend=None,
        callbacks=None,
        ttl=None,
    ) -> bool:
        """Persist minimal sub-job context for later lookup.

        Writes ``flow_run_id``, ``backend`` and ``callbacks`` into the
        redis record keyed by
        ``{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}`` so that
        the parent ``db_job_callback`` can fetch sub-job info via
        :meth:`get_job`.

        When ``ttl`` is provided the redis key is set to expire after
        ``ttl`` seconds so it is cleaned up automatically.
        """
        redis_client = self._client_or_log(job_id, "update")
        if redis_client is None:
            return False

        redis_key = self._redis_job_key(job_id, flow_run_id)
        try:
            record = self._read_record(redis_client, redis_key)
        except Exception as e:
            logger.error(
                f"Redis store flow_run_id error {flow_run_id}: {str(e)}"
            )
            return False

        if flow_run_id is not None:
            record["flow_run_id"] = flow_run_id
        if backend is not None:
            record["backend"] = backend
        if callbacks is not None:
            record["callbacks"] = callbacks

        try:
            redis_client.set(redis_key, json.dumps(record))
            if ttl is not None and ttl > 0:
                redis_client.expire(redis_key, ttl)
                logger.debug(
                    f"Redis store sub-job context {flow_run_id}: "
                    f"set TTL={ttl}s for key {redis_key}"
                )
            return True
        except Exception as e:
            logger.error(
                f"Redis store flow_run_id error {flow_run_id}: {str(e)}"
            )
            return False


def get_job_storage_backend(
    results_db_storage=Constant.RESULTS_DB_STORAGE_DEFAULT,
    db_engine=None,
) -> JobStorageBackend:
    """Factory: return a job storage backend for the given storage type.

    When ``results_db_storage`` is not provided it defaults to
    :attr:`Constant.RESULTS_DB_STORAGE_DEFAULT` (``sql``).

    The ``db_engine`` parameter is overloaded: for the SQL backend it
    is a SQLAlchemy engine; for the redis backend it is a redis client
    instance. This lets the caller pass a single ``db_engine``
    regardless of the storage type.

    Args:
        results_db_storage: ``"sql"`` or ``"redis"``.
        db_engine: SQLAlchemy engine (for SQL) or redis client
            instance (for redis).

    Returns:
        A concrete :class:`JobStorageBackend` instance.
    """
    if results_db_storage == Constant.RESULTS_DB_STORAGE_REDIS:
        return RedisJobStorageBackend(db_engine)
    return SqlJobStorageBackend(db_engine)
