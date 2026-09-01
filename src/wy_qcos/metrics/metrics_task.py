#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You can obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import partial

import redis.asyncio as async_redis
from prefect.client.schemas.objects import WorkerStatus
from sqlalchemy.orm import Session

from wy_qcos.common.config import Config
from wy_qcos.common.constant import (
    Constant,
    HttpCode,
)
from wy_qcos.db.models import Job
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.metrics import metrics_collector
from wy_qcos.task_manager import scheduler


logger = logging.getLogger(__name__)

PREFECT_CHECK_TIMEOUT = 3.0
WORKER_CHECK_TIMEOUT = 5.0
WORKER_CHECK_RETRY_DELAY = 2.0
REDIS_CHECK_TIMEOUT = 2.0
METRICS_TOTAL_TIMEOUT = 15.0

_redis_client = None
_worker_check_executor = None
_executor_lock = threading.Lock()
_app = None


def set_app(app):
    """Set FastAPI app instance for accessing app.state._db_engine.

    Args:
        app: FastAPI application instance
    """
    global _app
    _app = app
    logger.debug("FastAPI app instance set for metrics task")


def init_metrics():
    """Initialize metrics module (verify app and db engine are available)."""
    logger.debug("Initializing metrics module")
    try:
        if _app is None:
            raise RuntimeError(
                "FastAPI app not initialized. "
                "Call set_app() from metrics_task first."
            )
        db_engine = _app.state._db_engine
        if db_engine is None:
            raise RuntimeError(
                "Database engine not initialized in app.state._db_engine"
            )
        logger.info("Metrics module initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize metrics module: {e}")
        raise


def get_db_session():
    """Create a new database session.

    Creates a fresh session each time to ensure connection resilience.
    If DB connection is lost, the next call will create a new session
    that can establish a fresh connection via the connection pool.

    Returns:
        Database session
    """
    logger.debug("Creating new database session")
    if _app is None:
        raise RuntimeError(
            "FastAPI app not initialized. "
            "Call set_app() from metrics_task first."
        )
    db_engine = _app.state._db_engine
    if db_engine is None:
        raise RuntimeError(
            "Database engine not initialized in app.state._db_engine"
        )
    # Create fresh session each time (not keeping reference)
    session = Session(db_engine, expire_on_commit=False)
    logger.debug("Created new database session")
    return session


def get_job_repo():
    """Create a new job repository with a fresh database session.

    Returns a tuple of (repository, session) so caller can manage
    the session lifecycle.

    Returns:
        Tuple of (JobRepository instance, Session instance)
    """
    session = get_db_session()
    repo = JobRepository(session)
    logger.debug("Created new job repository with fresh session")
    return repo, session


def clear_db_session():
    """No longer needed since sessions are not cached.

    Kept for backward compatibility.
    """
    logger.debug("clear_db_session() called (sessions not cached)")


def _get_worker_check_executor():
    global _worker_check_executor
    if _worker_check_executor is None:
        with _executor_lock:
            if _worker_check_executor is None:
                _worker_check_executor = ThreadPoolExecutor(
                    max_workers=32, thread_name_prefix="worker-check"
                )
    return _worker_check_executor


async def _aclose_worker_check_executor():
    global _worker_check_executor
    if _worker_check_executor is not None:
        _worker_check_executor.shutdown(wait=True)
        _worker_check_executor = None


async def get_redis_client():
    """Get a singleton Redis client for health checks."""
    global _redis_client
    if _redis_client is None:
        _redis_client = async_redis.Redis.from_url(
            Config.REDIS.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=REDIS_CHECK_TIMEOUT,
            socket_timeout=REDIS_CHECK_TIMEOUT,
        )
    return _redis_client


async def clear_redis_client():
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception as e:
            logger.debug(f"Error closing Redis client: {e}")
        finally:
            _redis_client = None
    await _aclose_worker_check_executor()


async def call_sync_with_timeout(
    func, timeout=3.0, executor=None, *args, **kwargs
):
    """Execute a synchronous function in a thread pool with a timeout.

    Args:
        func (callable): The synchronous function to execute.
        timeout (float, optional): Timeout in seconds. Defaults to 3.0.
        executor (ThreadPoolExecutor, optional): Thread pool executor.
            If None, the default executor will be used.
        *args: Arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        Any: The result of the function execution.
    """
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(executor, partial(func, *args, **kwargs)),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Sync call {func.__name__} timed out after {timeout}s"
        )


def require_sync_client(func):
    """Decorator for synchronous task functions.

    Ensure task_manager and _sync_client exist,
    and inject sync_client as keyword argument.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The decorated function.
    """

    async def wrapper(*args, **kwargs):
        task_manager = scheduler.get_task_manager()
        if not task_manager or not task_manager._sync_client:
            return False, "Task manager or sync client not initialized"
        kwargs["sync_client"] = task_manager._sync_client
        return await func(*args, **kwargs)

    return wrapper


async def update_job_metrics():
    """Update job metrics from database using fresh session per call."""
    logger.debug("Querying job metrics from database")

    repo = None
    session = None
    try:
        # Create fresh job repository and session for this operation
        repo, session = get_job_repo()

        # Count jobs by status using database queries (more efficient)
        total = repo.count(Job)
        completed = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_COMPLETED
        )
        failed = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_FAILED
        )
        running = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_RUNNING
        )
        queued = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_QUEUED
        )
        cancelling = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_CANCELLING
        )
        cancelled = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_CANCELLED
        )
        deleting = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_DELETING
        )
        deleted = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_DELETED
        )
        unknown = repo.count_by_attr(
            Job, "job_status", Constant.JOB_STATUS_UNKNOWN
        )

        # Count jobs created in the last minute to compute submission
        # rate (jobs per minute). Uses a sliding 1-minute window over
        # created_at so no persistent snapshot is needed.
        recent_cutoff = datetime.now() - timedelta(minutes=1)
        submitted_job_count = repo.count_recent(recent_cutoff)
        # Count jobs ended in the last minute to compute completion rate.
        # Uses ended_at so the rate reflects actual job completions rather
        # than creations.
        completed_job_count = repo.count_recent(
            recent_cutoff,
            time_field="ended_at",
            job_status=Constant.JOB_STATUS_COMPLETED,
        )

        data = metrics_collector.job_metrics.JobMetricsData(
            total=total,
            completed=completed,
            failed=failed,
            running=running,
            queued=queued,
            cancelling=cancelling,
            cancelled=cancelled,
            deleting=deleting,
            deleted=deleted,
            unknown=unknown,
            submitted_job_rate_min=float(submitted_job_count),
            completed_job_rate_min=float(completed_job_count),
        )

        metrics_collector.update_job_metrics(data=data)
    except Exception as e:
        logger.error(f"Error updating job metrics from database: {e}")
    finally:
        # Always close session
        if session is not None:
            try:
                session.close()
                logger.debug("Closed database session after metrics update")
            except Exception as e:
                logger.debug(f"Error closing database session: {e}")


@require_sync_client
async def check_worker_health(sync_client=None) -> tuple[bool, str]:
    """Check worker health.

    Check if there is at least one online worker in all work pools,
    execute concurrently with timeout.
    """
    device_names = list(scheduler.get_device_manager().get_devices().keys())
    if not device_names:
        return False, "No devices configured"

    async def check_single_device(device_name):
        """Check single device with retry on timeout.

        Args:
            device_name (str): Device name

        Returns:
            (device_name, status_str)
        """
        worker_executor = _get_worker_check_executor()

        for attempt in range(2):
            try:
                pool_name = f"{Constant.WORK_POOL_DEVICE_PREFIX}{device_name}"
                workers = await call_sync_with_timeout(
                    sync_client.read_workers_for_work_pool,
                    timeout=WORKER_CHECK_TIMEOUT,
                    executor=worker_executor,
                    work_pool_name=pool_name,
                )

                if not workers:
                    return device_name, "no_workers"
                online_workers = [
                    w for w in workers if w.status == WorkerStatus.ONLINE
                ]
                if not online_workers:
                    return device_name, "no_online"
                return device_name, "ok"
            except TimeoutError:
                if attempt == 0:
                    logger.warning(
                        f"First timeout checking workers for {device_name}, "
                        f"retrying after {WORKER_CHECK_RETRY_DELAY}s"
                    )
                    await asyncio.sleep(WORKER_CHECK_RETRY_DELAY)
                    continue

                logger.warning(f"All retries timeout for {device_name}")
                return device_name, "timeout"
            except Exception as e:
                logger.warning(
                    f"Error checking workers for {device_name}: {e}"
                )
                return device_name, f"error:{str(e)}"

    results = await asyncio.gather(*[
        check_single_device(d) for d in device_names
    ])

    all_healthy = True
    errors = []
    for device, status in results:
        if status == "ok":
            continue
        all_healthy = False
        errors.append(f"{device}: {status}")

    if all_healthy:
        return True, ""
    else:
        return False, "; ".join(errors)


@require_sync_client
async def check_prefect_health(sync_client=None):
    """Check Prefect API availability with timeout."""
    if sync_client is None:
        return False, "Sync client not provided by decorator"

    try:
        hello = await call_sync_with_timeout(
            sync_client.hello, timeout=PREFECT_CHECK_TIMEOUT
        )
        if hello and hello.status_code == HttpCode.SUCCESS_OK:
            return True, ""
        else:
            return (
                False,
                f"Prefect API returned status code: \
                {hello.status_code if hello else 'None'}",
            )
    except TimeoutError:
        return (
            False,
            f"Prefect API hello() timed out after {PREFECT_CHECK_TIMEOUT}s",
        )
    except Exception as e:
        return False, f"Prefect API connection failed: {str(e)}"


async def check_fastapi_health():
    """Check FastAPI service health.

    FastAPI service is in the same process, default healthy
    """
    return True, ""


async def check_redis_health():
    """Check Redis connectivity with short timeout."""
    client = None
    try:
        client = await get_redis_client()
        await client.ping()
        return True, ""
    except (asyncio.TimeoutError, TimeoutError):
        return False, "Redis ping timed out"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        await clear_redis_client()
        return False, f"Redis ping failed: {str(e)}"


async def update_system_health_metrics():
    """Update system health metrics.

    Execute all component health checks in parallel and update metrics
    """
    try:
        logger.debug("Checking system component health status")
        timestamp_second = int(time.time())

        results = await asyncio.gather(
            check_worker_health(),
            check_prefect_health(),
            check_fastapi_health(),
            check_redis_health(),
            return_exceptions=True,
        )

        def unpack_result(result):
            if isinstance(result, Exception):
                return False, str(result)
            return result

        worker_healthy, worker_error = unpack_result(results[0])
        prefect_healthy, prefect_error = unpack_result(results[1])
        fastapi_healthy, fastapi_error = unpack_result(results[2])
        redis_healthy, redis_error = unpack_result(results[3])

        data = metrics_collector.system_health_metrics.SystemHealthMetricsData(
            heartbeat_timestamp=timestamp_second,
            worker_healthy=worker_healthy,
            prefect_healthy=prefect_healthy,
            fastapi_healthy=fastapi_healthy,
            redis_healthy=redis_healthy,
        )
        metrics_collector.update_system_health(data)

        logger.debug(
            f"System health component status: "
            f"worker={worker_healthy}, "
            f"worker_error={worker_error}, "
            f"prefect={prefect_healthy}, "
            f"prefect_error={prefect_error}, "
            f"fastapi={fastapi_healthy}, "
            f"fastapi_error={fastapi_error}, "
            f"redis={redis_healthy}, "
            f"redis_error={redis_error}"
        )

        # Auto-restart dead workers when prefect is healthy but workers
        # are not. Skip if prefect itself is down (restarts would fail
        # anyway because worker registration requires prefect API).
        if (
            fastapi_healthy
            and prefect_healthy
            and redis_healthy
            and not worker_healthy
        ):
            task_manager = scheduler.get_task_manager()
            if task_manager:
                try:
                    await call_sync_with_timeout(
                        task_manager.watchdog_restart_dead_workers,
                        timeout=30.0,
                    )
                except TimeoutError:
                    logger.warning("Watchdog restart timed out")
                except Exception as e:
                    logger.warning(f"Watchdog restart error: {e}")

    except Exception as e:
        logger.error(
            f"Error updating system health metrics: {e}", exc_info=True
        )


async def update_metrics_task_async():
    """Asynchronously update task metrics from task scheduler."""
    try:
        logger.debug("update_metrics_task_async() called")
        await asyncio.wait_for(
            asyncio.gather(
                update_job_metrics(), update_system_health_metrics()
            ),
            timeout=METRICS_TOTAL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            f"Metrics update timed out after {METRICS_TOTAL_TIMEOUT} seconds"
        )
    except Exception as e:
        logger.error(f"Error updating task metrics: {e}", exc_info=True)
