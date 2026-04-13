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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import asyncio
import logging
import time

from wy_qcos.common.constant import Constant
from wy_qcos.metrics.metrics_task import update_metrics_task_async

logger = logging.getLogger(__name__)


class MetricsScheduler:
    """Periodic metrics scheduler with rate limiting."""

    def __init__(self):
        self._running = False
        self._update_lock = asyncio.Lock()
        self._last_update_time = 0.0
        # Use the max interval as the standard periodic interval
        self._interval = Constant.DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS
        self._start_lock = asyncio.Lock()

    async def _execute_update(self, source: str = "periodic"):
        """Execute metrics update with concurrency control and rate limiting.

        Args:
            source: Identifies the trigger source (for logging).
        """
        # Quick check to avoid unnecessary lock attempts
        if not self._running:
            logger.debug(
                f"Skipping {source} update: scheduler is stopping/stopped"
            )
            return

        async with self._update_lock:
            # Re-check running state after acquiring lock
            if not self._running:
                logger.debug(
                    f"Skipping {source} update: \
                    scheduler stopped during lock wait"
                )
                return

            # Rate limiting: enforce minimum interval between updates
            now = time.time()
            if now - self._last_update_time < self._interval:
                # Calculate remaining sleep time if needed, or just skip
                logger.debug(
                    f"Skipping {source} update: \
                    last update was {now - self._last_update_time:.2f}s ago "
                    f"(min interval {self._interval}s)"
                )
                return

            self._last_update_time = now
            logger.debug(f"Executing metrics update (trigger: {source})")

            try:
                await update_metrics_task_async()
                logger.debug(f"Metrics update completed (trigger: {source})")
            except Exception as e:
                logger.error(
                    f"Error during metrics update ({source}): {e}",
                    exc_info=True,
                )

    async def start(self):
        """Main scheduler loop – runs periodically."""
        async with self._start_lock:
            if self._running:
                logger.debug("Metrics scheduler is already running")
                return
            self._running = True

        logger.info(
            f"Starting periodic metrics scheduler \
            (interval: {self._interval}s)"
        )

        try:
            # Initial update on startup
            await self._execute_update(source="initial")

            # Main event loop
            while self._running:
                try:
                    # Wait for the next interval
                    await asyncio.sleep(self._interval)

                    # Check again after sleep in case stop()
                    # was called during sleep
                    if not self._running:
                        break

                    await self._execute_update(source="periodic")

                except asyncio.CancelledError:
                    logger.debug("Scheduler loop cancelled")
                    break
                except Exception as e:
                    logger.error(
                        f"Unexpected error in scheduler loop: {e}",
                        exc_info=True,
                    )
                    await asyncio.sleep(self._interval)

        except Exception as e:
            logger.error(
                f"Failed to initialize metrics scheduler: {e}", exc_info=True
            )
            raise
        finally:
            self._running = False
            logger.info("Metrics scheduler stopped")

    async def stop(self):
        """Stop the metrics scheduler."""
        async with self._start_lock:
            if not self._running:
                logger.debug("Metrics scheduler already stopped")
                return

            logger.info("Stopping metrics scheduler...")
            self._running = False

        logger.info("Metrics scheduler stop signal sent")
