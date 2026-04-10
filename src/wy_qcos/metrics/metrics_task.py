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
import traceback

from wy_qcos.common.constant import Constant
from wy_qcos.metrics import metrics_collector

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def update_job_metrics():
    """Update job metrics from task scheduler."""
    # Lazy import to avoid circular dependency
    from wy_qcos.task_manager import scheduler

    logger.debug("Getting jobs asynchronously")

    # used async get_jobs
    responses, err = await scheduler.aget_jobs()

    if responses:
        total = len(responses)

        success = sum(
            1
            for job in responses
            if job.get("job_status") == Constant.JOB_STATUS_COMPLETED
        )
        failed = sum(
            1
            for job in responses
            if job.get("job_status") == Constant.JOB_STATUS_FAILED
        )
        running = sum(
            1
            for job in responses
            if job.get("job_status") == Constant.JOB_STATUS_RUNNING
        )
        queued = sum(
            1
            for job in responses
            if job.get("job_status") == Constant.JOB_STATUS_QUEUED
        )

        cancelling = sum(
            1
            for job in responses
            if job.get("job_status") == Constant.JOB_STATUS_CANCELLING
        )
        cancelled = sum(
            1
            for job in responses
            if job.get("job_status") == Constant.JOB_STATUS_CANCELLED
        )
        unknown = sum(
            1
            for job in responses
            if job.get("job_status") == Constant.JOB_STATUS_UNKNOWN
        )

        data = metrics_collector.job_metrics.JobMetricsData(
            total=total,
            success=success,
            failed=failed,
            running=running,
            queued=queued,
            cancelling=cancelling,
            cancelled=cancelled,
            unknown=unknown,
        )

        metrics_collector.update_job_metrics(data=data)
        logger.debug(
            f"Metrics updated: total={total}, success={success}, "
            f"failed={failed}, running={running}, queued={queued}"
        )


async def update_metrics_task_async():
    """Asynchronously update task metrics from task scheduler."""
    try:
        logger.debug("update_metrics_task_async() called")
        await update_job_metrics()
    except Exception as e:
        logger.error(f"Error updating task metrics: {e}")
        logger.error(traceback.format_exc())
