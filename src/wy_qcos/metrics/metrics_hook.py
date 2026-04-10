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
from typing import Any

import redis.asyncio as async_redis

from wy_qcos.common.constant import Constant

logger = logging.getLogger(__name__)


class MetricsStateHook:
    """state hook that triggers metrics update via Redis Pub."""

    REDIS_CONNECT_TIMEOUT = 5
    REDIS_SOCKET_TIMEOUT = 5

    _last_trigger_time: float = 0
    _trigger_lock: asyncio.Lock = asyncio.Lock()
    _redis_client: async_redis.Redis = None

    @staticmethod
    async def _get_redis_client() -> async_redis.Redis:
        """Lazy initialize async Redis client with connection pool.

        Returns:
            async_redis.Redis: Async Redis client instance
        """
        if MetricsStateHook._redis_client is None:
            try:
                pool = async_redis.ConnectionPool(
                    host=Constant.DEFAULT_REDIS_SERVER_IP,
                    port=Constant.DEFAULT_REDIS_SERVER_PORT,
                    decode_responses=True,
                    socket_connect_timeout=MetricsStateHook.REDIS_CONNECT_TIMEOUT,
                    socket_timeout=MetricsStateHook.REDIS_SOCKET_TIMEOUT,
                )
                MetricsStateHook._redis_client = async_redis.Redis(
                    connection_pool=pool
                )
                await MetricsStateHook._redis_client.ping()
            except Exception as e:
                logger.error(f"Failed to initialize async Redis client: {e}")
                MetricsStateHook._redis_client = None
                raise
        return MetricsStateHook._redis_client

    @staticmethod
    async def _publish_metrics_event():
        """Publish metrics update event to Redis channel."""
        try:
            redis_client = await MetricsStateHook._get_redis_client()
            if redis_client:
                message = f"{time.time()}"
                await redis_client.publish(
                    Constant.DEFAULT_METRICS_UPDATE_CHANNEL, message
                )
                logger.debug(
                    f"Triggered immediate metrics update via Redis: {message}"
                )
        except Exception as e:
            logger.error(
                f"Failed to publish metrics update event: {e}", exc_info=True
            )

    @staticmethod
    async def callback(flow_or_task_run: Any, from_state: Any, to_state: Any):
        """Prefect state hook entry point.

        Args:
            flow_or_task_run: Flow or task run object
            from_state: state before transition
            to_state: state after transition
        """
        logger.info("Metrics state hook triggered")
        min_interval = Constant.DEFAULT_MIN_UPDATE_METRICS_INTERVAL_SECONDS

        # Rate limiting check (async lock)
        async with MetricsStateHook._trigger_lock:
            now = time.time()
            if now - MetricsStateHook._last_trigger_time < min_interval:
                logger.debug(
                    f"Skipping trigger: last trigger was \
                    {now - MetricsStateHook._last_trigger_time:.2f}s ago "
                    f"(min interval {min_interval}s)"
                )
                return
            MetricsStateHook._last_trigger_time = now

        name = getattr(flow_or_task_run, "name", str(flow_or_task_run))
        logger.debug(
            f"Triggering metrics update for \
            {from_state.name} -> {to_state.name} on {name}"
        )

        # Publish Redis event trigger_metrics_update
        await MetricsStateHook._publish_metrics_event()

        # Publish Redis event trigger_metrics_update
        await MetricsStateHook._publish_metrics_event()
