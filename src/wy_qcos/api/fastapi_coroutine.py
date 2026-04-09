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
import fastapi_jsonrpc as jsonrpc

from wy_qcos.metrics.metrics_server import MetricsServer


logger = logging.getLogger(__name__)


class FastApiCoroutineManager:
    """Controls the lifecycle of FastAPI coroutines."""

    def __init__(self):
        """Init the coros list."""
        self.coros = []

    def add_coro(self, coro):
        """Add a coroutine to the manager.

        Args:
            coro (coroutine): The coroutine to add.
        """
        coro = asyncio.create_task(coro())
        self.coros.append(coro)

    async def stop(self):
        """Stop all background coros."""
        if not self.coros:
            return
        logger.info(f"is stopping {len(self.coros)} background coros...")

        for task in self.coros:
            task.cancel()
        await asyncio.gather(*self.coros, return_exceptions=True)

        logger.info("Background coros stopped")


@asynccontextmanager
async def lifespan(app: jsonrpc.API):
    """FastAPI lifespan manager.

    Args:
        app (jsonrpc.API): FastAPI app

    Returns:
        Asynchronous context manager
    """
    manager = FastApiCoroutineManager()
    logger.info("Starting background coros")

    # add metrics server to run in background
    manager.add_coro(MetricsServer().run)

    # return to FastAPI
    yield

    # stop all background coros
    await manager.stop()
