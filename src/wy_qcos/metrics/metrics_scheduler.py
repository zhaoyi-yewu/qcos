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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from wy_qcos.common.constant import Constant
from wy_qcos.metrics.metrics_task import update_metrics_task_async


logger = logging.getLogger(__name__)


class MetricsScheduler:
    """Periodic metrics scheduler powered by APScheduler.

    APScheduler guarantees serial execution and minimum interval via
    ``triggers="interval"`` with ``coalesce=True, max_instances=1``
    and ``seconds=self._interval``.
    """

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler = AsyncIOScheduler(daemon=True)
        self._running = False
        self._interval = Constant.DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS

    async def start(self):
        """Start the APScheduler and register the metrics job."""
        if self._running:
            logger.debug("Metrics scheduler is already running")
            return
        self._running = True

        logger.info(
            f"Starting periodic metrics scheduler "
            f"(interval: {self._interval}s)"
        )

        self._scheduler.start()

        # Register job APScheduler handles interval + serialisation.
        self._scheduler.add_job(
            self._job,
            trigger="interval",
            seconds=self._interval,
            coalesce=True,
            max_instances=1,
            id="metrics_update",
            replace_existing=True,
        )

        # Run once on startup
        try:
            await update_metrics_task_async()
        except Exception:
            logger.debug("Initial metrics update failed (non-fatal)")

        logger.info("Metrics scheduler started (job_id: metrics_update)")

    async def stop(self):
        """Shutdown the APScheduler gracefully."""
        if not self._running:
            logger.debug("Metrics scheduler already stopped")
            return

        logger.info("Stopping metrics scheduler...")
        self._running = False

        try:
            self._scheduler.shutdown(wait=True)
        except Exception as e:
            logger.warning(f"Error during scheduler shutdown: {e}")

        logger.info("Metrics scheduler stopped")

    async def _job(self):
        """Triggers this coroutine every interval."""
        if not self._running:
            return
        try:
            await update_metrics_task_async()
        except Exception:
            logger.error(
                "Error during metrics update (periodic)", exc_info=True
            )
