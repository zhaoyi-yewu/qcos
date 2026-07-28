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

"""Periodic garbage collection service.

Runs gc.collect() on all 3 generations and malloc_trim(0) at a
configurable interval (GC_INTERVAL days) to release freed memory
back to the OS. This mitigates memory fragmentation and slow leaks
that are not visible to Python's cyclic garbage collector.
"""

import gc
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library


logger = logging.getLogger(__name__)


class GcCleaner:
    """Periodic garbage collection service.

    Runs gc.collect() on all 3 generations followed by malloc_trim(0)
    to return freed heap memory to the OS. The interval is controlled
    by Config.DEFAULT.GC_INTERVAL (in days). A value of -1 disables
    the service.
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(daemon=True)
        self._running = False
        self._interval_days = Config.DEFAULT.GC_INTERVAL

    async def start(self) -> None:
        """Start the periodic GC scheduler."""
        if self._running:
            return
        self._running = True

        if self._interval_days == -1:
            logger.info(
                "GC cleaner disabled (GC_INTERVAL=-1), skipping startup"
            )
            return

        interval_minutes = int(self._interval_days * 24 * 60)

        logger.info(
            f"Starting GC cleaner "
            f"(interval: {self._interval_days} days / "
            f"{interval_minutes} minutes)"
        )

        self._scheduler.start()
        self._scheduler.add_job(
            self._do_gc,
            trigger="interval",
            minutes=interval_minutes,
            coalesce=True,
            max_instances=1,
            id="gc_clean",
            replace_existing=True,
        )
        logger.info("GC cleaner started")

    async def stop(self) -> None:
        """Stop the periodic GC scheduler gracefully."""
        if not self._running:
            return
        logger.info("Stopping GC cleaner...")
        self._running = False
        try:
            self._scheduler.shutdown(wait=True)
        except Exception as e:
            logger.warning(f"Error shutting down GC cleaner: {e}")
        logger.info("GC cleaner stopped")

    def _do_gc(self):
        """Run gc.collect on all 3 generations + malloc_trim(0).

        This is a synchronous method invoked by APScheduler. It runs in
        the scheduler's thread (daemon=True), so it does not block the
        asyncio event loop.
        """
        if not self._running:
            return

        try:
            # Collect all 3 generations (full collection).
            collected = gc.collect(2)
            logger.info(f"gc.collect(2) freed {collected} objects")

            # malloc_trim(0) asks glibc to return free heap pages to the
            # OS. Only available on Linux with glibc. The libc handle is
            # cached by Library.load_libc() on first use.
            ret = Library.malloc_trim(0)
            if ret is None:
                logger.debug("malloc_trim skipped (not available)")
            else:
                logger.debug(f"malloc_trim(0) returned {ret}")
        except Exception:
            logger.error("GC cleaner failed", exc_info=True)
