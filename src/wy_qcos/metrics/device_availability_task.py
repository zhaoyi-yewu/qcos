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

import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from wy_qcos.db.repositories.device_availability import (
    DeviceAvailabilityRepository,
)
from wy_qcos.metrics.device_availability_collector import (
    DeviceAvailabilityCollector,
)

logger = logging.getLogger(__name__)

# Reference to the FastAPI app for accessing app.state._db_engine.
# Set via set_app() from the app lifespan.
_app = None


def set_app(app):
    """Set FastAPI app instance for accessing app.state._db_engine.

    Args:
        app: FastAPI application instance
    """
    global _app
    _app = app
    logger.debug("FastAPI app instance set for device_availability_task")


def _get_db_engine():
    """Get the database engine from the app state.

    Returns:
        db engine or None when not available
    """
    if _app is None:
        return None
    return getattr(_app.state, "_db_engine", None)


def aggregate_availability_hourly_sync():
    """Synchronous hourly availability aggregation.

    Snapshots the in-memory counters, upserts them into the
    device_availability_hourly table for the current whole hour, and
    resets the counters. Safe to call from sync or async context.
    """
    collector = DeviceAvailabilityCollector()
    snapshot = collector.snapshot_and_reset()
    if not snapshot:
        logger.debug("aggregate_availability_hourly: no samples, skip")
        return

    # whole-hour: current hour truncated to minute=0, second=0
    # Use local time (datetime.now) so hour/created_at/updated_at
    # are stored as local time in device_availability_hourly.
    now = datetime.now()
    hour = now.replace(minute=0, second=0, microsecond=0)

    items = [
        {
            "device_name": name,
            "online_count": c.online_count,
            "total_count": c.total_count,
        }
        for name, c in snapshot.items()
    ]

    db_engine = _get_db_engine()
    if db_engine is None:
        logger.error(
            "aggregate_availability_hourly: db engine not available, "
            "counts discarded"
        )
        return

    session = Session(db_engine, expire_on_commit=False)
    try:
        repo = DeviceAvailabilityRepository(session)
        success, err = repo.upsert_hourly(hour, items)
        if not success:
            logger.error(f"aggregate_availability_hourly upsert failed: {err}")
        else:
            logger.info(
                f"aggregate_availability_hourly: persisted "
                f"{len(items)} devices for hour {hour.isoformat()}"
            )
    finally:
        session.close()


async def aggregate_availability_hourly():
    """Async hourly availability aggregation (APScheduler entrypoint).

    Runs the sync aggregation in a thread so the event loop is not
    blocked by DB I/O.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, aggregate_availability_hourly_sync)
