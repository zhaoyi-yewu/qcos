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

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from wy_qcos.common.constant import Constant

logger = logging.getLogger(__name__)


class DeviceAvailabilityScheduler:
    """Periodic device availability aggregation scheduler.

    Uses APScheduler with a cron trigger firing at the top of every
    hour (minute=0) to run the hourly availability aggregation task.
    """

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler = AsyncIOScheduler(daemon=True)
        self._running = False
        self._cron_minute = Constant.DEFAULT_AVAILABILITY_AGGREGATE_CRON_MINUTE

    async def start(self):
        """Start the scheduler and register the hourly aggregation job."""
        if self._running:
            logger.debug("DeviceAvailabilityScheduler already running")
            return
        self._running = True
        logger.info("Starting DeviceAvailabilityScheduler (cron minute=0)")
        self._scheduler.start()
        trigger = CronTrigger(minute=self._cron_minute)
        self._scheduler.add_job(
            self._job,
            trigger=trigger,
            id="device_availability_aggregate",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        logger.info("DeviceAvailabilityScheduler started")

    async def stop(self):
        """Shutdown the scheduler gracefully."""
        if not self._running:
            logger.debug("DeviceAvailabilityScheduler already stopped")
            return
        logger.info("Stopping DeviceAvailabilityScheduler...")
        self._running = False
        try:
            self._scheduler.shutdown(wait=True)
        except Exception as e:
            logger.warning(
                f"Error during DeviceAvailabilityScheduler shutdown: {e}"
            )
        logger.info("DeviceAvailabilityScheduler stopped")

    async def _job(self):
        """Triggers this coroutine at the top of every hour."""
        if not self._running:
            return
        try:
            # lazy import to avoid circular dependency at module load
            from wy_qcos.metrics.device_availability_task import (
                aggregate_availability_hourly,
            )

            await aggregate_availability_hourly()
        except Exception:
            logger.error(
                "Error during device availability aggregation (periodic)",
                exc_info=True,
            )
