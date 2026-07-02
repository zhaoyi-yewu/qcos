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
import asyncio
from contextlib import asynccontextmanager
from typing import Protocol

import fastapi_jsonrpc as jsonrpc

from wy_qcos.metrics.metrics_server import MetricsServer
from wy_qcos.metrics.metrics_scheduler import MetricsScheduler
from wy_qcos.metrics.metrics_task import set_app, init_metrics
from wy_qcos.task_manager.job_cleaner import JobCleaner

logger = logging.getLogger(__name__)


class StoppableService(Protocol):
    """Protocol for services that can be started and stopped."""

    async def start(self) -> None:
        """Start the service."""
        ...

    async def stop(self) -> None:
        """Stop the service gracefully."""
        ...


class BackgroundServiceManager:
    """Manages the lifecycle of background services."""

    def __init__(self) -> None:
        """Initialize the service manager."""
        self._services: list[StoppableService] = []
        self._tasks: list[asyncio.Task] = []

    def add_service(self, service: StoppableService) -> None:
        """Add a background service to the manager.

        Args:
            service: A service object with start() and stop() methods.
        """
        self._services.append(service)

    async def start_all(self) -> None:
        """Start all registered background services."""
        if not self._services:
            return

        logger.info(f"Starting {len(self._services)} background service(s)...")

        for service in self._services:
            task = asyncio.create_task(service.start())
            self._tasks.append(task)

        logger.info("All background services started")

    async def stop_all(self) -> None:
        """Stop all background services gracefully."""
        if not self._services:
            return

        logger.info(f"Stopping {len(self._services)} background service(s)...")

        # Call stop() on all services
        stop_coroutines = [service.stop() for service in self._services]
        await asyncio.gather(*stop_coroutines, return_exceptions=True)

        # Wait for all tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("All background services stopped")


@asynccontextmanager
async def app_lifespan(app: jsonrpc.API):
    """FastAPI lifespan manager for background services.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Pass app instance to metrics_task for accessing app.state._db_engine
    set_app(app)

    # Initialize metrics module (verify app and db engine available)
    init_metrics()

    manager = BackgroundServiceManager()

    # Register metrics schedule
    metrics_schedule = MetricsScheduler()
    manager.add_service(metrics_schedule)

    # Register metrics server
    metrics_server = MetricsServer()
    manager.add_service(metrics_server)

    # Register job cleaner
    job_cleaner = JobCleaner(app_db_engine=app.state._db_engine)
    manager.add_service(job_cleaner)

    # Start all background services
    await manager.start_all()

    try:
        yield
    finally:
        # Stop all background services
        await manager.stop_all()
