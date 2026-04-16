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

import logging
import time
from collections import Counter

import redis.asyncio as async_redis
from prefect.client.schemas.objects import WorkerStatus

from wy_qcos.common.constant import (
    Constant,
    HttpCode,
)
from wy_qcos.metrics import metrics_collector
from wy_qcos.task_manager import scheduler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def update_job_metrics():
    """Update job metrics from task scheduler."""
    logger.debug("Getting jobs asynchronously")

    # used async get_jobs
    responses, err = await scheduler.aget_jobs()

    if responses:
        total = len(responses)

        status_counts = Counter(
            job.get("job_status") or Constant.JOB_STATUS_UNKNOWN
            for job in responses
        )

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


async def check_worker_health():
    """Check worker health status.

    Returns:
        Tuple of (is_healthy, error_message)
    """
    task_manager = scheduler.get_task_manager()
    if not task_manager or not task_manager._sync_client:
        return False, "Task manager or sync client not initialized"

    device_names = list(scheduler.device_manager.get_devices().keys())
    if not device_names:
        return False, "No devices configured"

    all_workers_healthy = True
    error_messages = []

    for device_name in device_names:
        try:
            workers = task_manager._sync_client.read_workers_for_work_pool(
                device_name
            )
            if not workers:
                all_workers_healthy = False
                error_messages.append(
                    f"No workers found for pool: {device_name}"
                )
                continue

            online_workers = [
                w for w in workers if w.status == WorkerStatus.ONLINE
            ]
            if not online_workers:
                all_workers_healthy = False
                error_messages.append(
                    f"No online workers for pool: {device_name}"
                )

        except Exception as e:
            all_workers_healthy = False
            error_messages.append(
                f"Error checking workers for {device_name}: {str(e)}"
            )
            logger.error(
                f"Exception occurred while checking worker health for \
                {device_name}"
            )

    if all_workers_healthy:
        return True, ""
    else:
        return False, "; ".join(error_messages)


async def check_prefect_health():
    """Check Prefect server health status.

    Returns:
        Tuple of (is_healthy, error_message)
    """
    task_manager = scheduler.get_task_manager()
    if not task_manager or not task_manager._sync_client:
        return False, "Prefect client not initialized"

    try:
        hello = task_manager._sync_client.hello()
        if hello and hello.status_code == HttpCode.SUCCESS_OK:
            return True, ""
        else:
            return (
                False,
                f"Prefect API returned status code: "
                f"{hello.status_code if hello else 'None'}",
            )
    except Exception as e:
        logger.error("Prefect API connection failed")
        return False, f"Prefect API connection failed: {str(e)}"


async def check_fastapi_health():
    """Check FastAPI server health status.

    Since this function runs in the same process as FastAPI server,
    when this function is called, the FastAPI server is still running,
    FastAPI server health status is always healthy.


    Returns:
        Tuple of (is_healthy, error_message)
    """
    return True, ""


async def check_redis_health():
    """Check Redis server health status.

    Returns:
        Tuple of (is_healthy, error_message)
    """
    redis_client = None
    try:
        redis_client = async_redis.Redis(
            host=Constant.DEFAULT_REDIS_SERVER_IP,
            port=Constant.DEFAULT_REDIS_SERVER_PORT,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        await redis_client.ping()

        return True, ""
    except Exception as e:
        logger.exception("Redis health check failed")
        return False, f"Redis ping failed: {str(e)}"
    finally:
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception as e:
                logger.error(
                    f"Failed to close Redis connection: {str(e)}",
                )


async def update_system_health_metrics():
    """Update system health metrics from task scheduler."""
    try:
        logger.debug("Checking system component health status")
        timestamp_second = int(time.time())

        worker_healthy, worker_error = await check_worker_health()
        prefect_healthy, prefect_error = await check_prefect_health()
        fastapi_healthy, fastapi_error = await check_fastapi_health()
        redis_healthy, redis_error = await check_redis_health()

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
            f"worker={'✓' if worker_healthy else '✗'}, "
            f"worker_error={worker_error}, "
            f"prefect={'✓' if prefect_healthy else '✗'}, "
            f"prefect_error={prefect_error}, "
            f"fastapi={'✓' if fastapi_healthy else '✗'}, "
            f"fastapi_error={fastapi_error}, "
            f"redis={'✓' if redis_healthy else '✗'}, "
            f"redis_error={redis_error}"
        )

    except Exception:
        logger.error("Error updating system health metrics:{e}")


async def update_metrics_task_async():
    """Asynchronously update task metrics from task scheduler."""
    try:
        logger.debug("update_metrics_task_async() called")
        await update_job_metrics()
        await update_system_health_metrics()
    except Exception:
        logger.error("Error updating task metrics")
