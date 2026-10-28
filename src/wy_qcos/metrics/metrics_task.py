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
import gc
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import partial

import psutil
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

    Check if there is at least one online worker in all relevant work
    pools (device, monitor, manager, virtual device), execute
    concurrently with timeout.
    """
    device_manager = scheduler.get_device_manager()
    devices = device_manager.get_devices()
    device_names = list(devices.keys())
    if not device_names:
        return False, "No devices configured"

    # Build the list of pool names to check:
    #   - dev|{device} for every device (required)
    #   - mon|{device} when device monitor is enabled
    #   - mgr|{device} when device manager is enabled
    #   - vdev|wirecut for the virtual device (always)
    pool_names_to_check = []
    for device_name in device_names:
        device = devices.get(device_name)
        pool_names_to_check.append(f"{Constant.WORK_POOL_DEV}|{device_name}")
        if device:
            # monitor enabled?
            # device monitor is enabled only when both the config flag
            # (device.get_enable_device_monitor) and the driver flag
            # (driver.enable_device_monitor) are True
            config_enable = device.get_enable_device_monitor()
            driver_enable = device.get_driver().enable_device_monitor
            if config_enable is not False and driver_enable:
                pool_names_to_check.append(
                    f"{Constant.WORK_POOL_MON}|{device_name}"
                )
            # manager enabled?
            if device.get_driver().enable_device_mgr:
                pool_names_to_check.append(
                    f"{Constant.WORK_POOL_MGR}|{device_name}"
                )

    # virtual device (wirecut) pool
    pool_names_to_check.append(
        f"{Constant.WORK_POOL_VDEV}|{Constant.VIRT_DEVICE_WIRECUT}"
    )

    async def check_single_pool(pool_name):
        """Check a single work pool with retry on timeout.

        Args:
            pool_name (str): work pool name

        Returns:
            (pool_name, status_str)
        """
        worker_executor = _get_worker_check_executor()

        for attempt in range(2):
            try:
                workers = await call_sync_with_timeout(
                    sync_client.read_workers_for_work_pool,
                    timeout=WORKER_CHECK_TIMEOUT,
                    executor=worker_executor,
                    work_pool_name=pool_name,
                )

                if not workers:
                    return pool_name, "no_workers"
                online_workers = [
                    w for w in workers if w.status == WorkerStatus.ONLINE
                ]
                if not online_workers:
                    return pool_name, "no_online"
                return pool_name, "ok"
            except TimeoutError:
                if attempt == 0:
                    logger.warning(
                        f"First timeout checking workers for "
                        f"{pool_name}, "
                        f"retrying after {WORKER_CHECK_RETRY_DELAY}s"
                    )
                    await asyncio.sleep(WORKER_CHECK_RETRY_DELAY)
                    continue

                logger.warning(f"All retries timeout for {pool_name}")
                return pool_name, "timeout"
            except Exception as e:
                logger.warning(f"Error checking workers for {pool_name}: {e}")
                return pool_name, f"error:{str(e)}"

    results = await asyncio.gather(*[
        check_single_pool(p) for p in pool_names_to_check
    ])

    all_healthy = True
    errors = []
    for pool_name, status in results:
        if status == "ok":
            continue
        all_healthy = False
        errors.append(f"{pool_name}: {status}")

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


def _collect_system_stats_sync():
    """Synchronously collect all psutil metrics (blocking).

    ``psutil.cpu_percent(interval=...)`` and
    ``process.cpu_percent(interval=...)`` each block for the given
    interval (~0.1s each). Running them directly
    inside an async coroutine freezes the event loop, so this helper is
    intended to be scheduled on the default executor via
    :func:`asyncio.AbstractEventLoop.run_in_executor`. All blocking calls
    are batched here so the async wrapper pays the executor overhead
    only once per cycle.

    Returns:
        Tuple of ``(rss_mb, vms_mb, thread_count, num_objects, cpu_percent,
        cpu_count, host_cpu_percent, mem_total_mb, mem_percent,
        disk_total_mb, disk_free_mb, disk_percent)``.
    """
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    # cpu_percent(interval=...) blocks for the given interval; use a
    # small non-zero interval to get a meaningful reading without
    # noticeably delaying the periodic task. Two calls total ~0.2s,
    # offloaded to a worker thread so the event loop is not stalled.
    host_cpu_percent = psutil.cpu_percent(interval=0.1)
    process_cpu_percent = process.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count(logical=True) or 0
    virtual_mem = psutil.virtual_memory()
    disk = psutil.disk_usage(os.getcwd())

    return (
        round(mem_info.rss / 1024 / 1024, 2),
        round(mem_info.vms / 1024 / 1024, 2),
        process.num_threads(),
        len(gc.get_objects()),
        process_cpu_percent,
        cpu_count,
        host_cpu_percent,
        round(virtual_mem.total / 1024 / 1024, 2),
        virtual_mem.percent,
        round(disk.total / 1024 / 1024, 2),
        round(disk.free / 1024 / 1024, 2),
        disk.percent,
    )


async def update_system_stats_metrics():
    """Update system stats metrics (process + host CPU/memory/disk).

    Reads process-level metrics via psutil for the current PID, and
    host-level metrics (CPU count/usage, memory, disk) for the machine
    hosting the API server. Updates the ``qcos_system_*`` Prometheus
    gauges so the WebUI monitor center and Grafana can render trends.

    The blocking psutil calls are offloaded to the default executor so
    the event loop is not stalled; see :func:`_collect_system_stats_sync`.
    """
    try:
        loop = asyncio.get_running_loop()
        (
            rss_mb,
            vms_mb,
            thread_count,
            num_objects,
            process_cpu_percent,
            cpu_count,
            host_cpu_percent,
            mem_total_mb,
            mem_percent,
            disk_total_mb,
            disk_free_mb,
            disk_percent,
        ) = await loop.run_in_executor(None, _collect_system_stats_sync)

        data = metrics_collector.system_stats_metrics.SystemStatsData(
            rss_mb=rss_mb,
            vms_mb=vms_mb,
            thread_count=thread_count,
            num_objects=num_objects,
            cpu_percent=process_cpu_percent,
            cpu_count=cpu_count,
            host_cpu_percent=host_cpu_percent,
            mem_total_mb=mem_total_mb,
            mem_percent=mem_percent,
            disk_total_mb=disk_total_mb,
            disk_free_mb=disk_free_mb,
            disk_percent=disk_percent,
        )
        metrics_collector.update_system_stats(data)
    except Exception as e:
        logger.error(
            f"Error updating system stats metrics: {e}", exc_info=True
        )


async def update_metrics_task_async():
    """Asynchronously update task metrics from task scheduler."""
    try:
        logger.debug("update_metrics_task_async() called")
        await asyncio.wait_for(
            asyncio.gather(
                update_job_metrics(),
                update_system_health_metrics(),
                update_system_stats_metrics(),
            ),
            timeout=METRICS_TOTAL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.error(
            f"Metrics update timed out after {METRICS_TOTAL_TIMEOUT} seconds"
        )
    except Exception as e:
        logger.error(f"Error updating task metrics: {e}", exc_info=True)
