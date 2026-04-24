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
import time
from collections import Counter
from functools import partial

import redis.asyncio as async_redis
from prefect.client.schemas.objects import WorkerStatus

from wy_qcos.common.constant import (
    Constant,
    HttpCode,
)
from wy_qcos.metrics import metrics_collector
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)

PREFECT_CHECK_TIMEOUT = 3.0
WORKER_CHECK_TIMEOUT = 3.0
REDIS_CHECK_TIMEOUT = 2.0
METRICS_TOTAL_TIMEOUT = 10.0

_redis_client = None


async def get_redis_client():
    """Get a singleton Redis client for health checks."""
    global _redis_client
    if _redis_client is None:
        _redis_client = async_redis.Redis(
            host=Constant.DEFAULT_REDIS_SERVER_IP,
            port=Constant.DEFAULT_REDIS_SERVER_PORT,
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


async def call_sync_with_timeout(func, timeout=3.0, *args, **kwargs):
    """Execute a synchronous function in a thread pool with a timeout.

    Args:
        func (callable): The synchronous function to execute.
        timeout (float, optional): Timeout in seconds. Defaults to 3.0.
        *args: Arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        Any: The result of the function execution.
    """
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, partial(func, *args, **kwargs)),
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
    """Update job metrics from task scheduler."""
    logger.debug("Getting jobs asynchronously")

    try:
        # used async get_jobs
        responses, err = await scheduler.aget_jobs()

        if responses:
            total = len(responses)

            status_counts = Counter(job.get("job_status") for job in responses)

            completed = status_counts.get(Constant.JOB_STATUS_COMPLETED, 0)
            failed = status_counts.get(Constant.JOB_STATUS_FAILED, 0)
            running = status_counts.get(Constant.JOB_STATUS_RUNNING, 0)
            queued = status_counts.get(Constant.JOB_STATUS_QUEUED, 0)
            cancelling = status_counts.get(Constant.JOB_STATUS_CANCELLING, 0)
            cancelled = status_counts.get(Constant.JOB_STATUS_CANCELLED, 0)
            deleted = status_counts.get(Constant.JOB_STATUS_DELETED, 0)
            unknown = status_counts.get(Constant.JOB_STATUS_UNKNOWN, 0)

            data = metrics_collector.job_metrics.JobMetricsData(
                total=total,
                completed=completed,
                failed=failed,
                running=running,
                queued=queued,
                cancelling=cancelling,
                cancelled=cancelled,
                deleted=deleted,
                unknown=unknown,
            )

            metrics_collector.update_job_metrics(data=data)
    except Exception as e:
        logger.error(f"Error updating job metrics: {e}", exc_info=True)


@require_sync_client
async def check_worker_health(sync_client=None) -> tuple[bool, str]:
    """Check worker health.

    Check if there is at least one online worker in all work pools,
    execute concurrently with timeout
    """
    device_names = list(scheduler.device_manager.get_devices().keys())
    if not device_names:
        return False, "No devices configured"

    async def check_single_device(device_name):
        """Check single device.

        Args:
            device_name (str): Device name
        Returns:
            (device_name, status_str)

        """
        try:
            workers = await call_sync_with_timeout(
                sync_client.read_workers_for_work_pool,
                timeout=WORKER_CHECK_TIMEOUT,
                work_pool_name=device_name,
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
            logger.warning(f"Timeout checking workers for {device_name}")
            return device_name, "timeout"
        except Exception as e:
            logger.warning(f"Error checking workers for {device_name}: {e}")
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
