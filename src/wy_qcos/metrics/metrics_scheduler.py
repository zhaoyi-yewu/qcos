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

import redis.asyncio as redis

from wy_qcos.common.constant import Constant
from wy_qcos.metrics.metrics_task import update_metrics_task_async

logger = logging.getLogger(__name__)


class MetricsScheduler:
    """Redis Pub/Sub driven metrics scheduler with rate limiting."""

    REDIS_CONNECT_TIMEOUT = 5
    REDIS_SOCKET_TIMEOUT = 5

    def __init__(self):
        self._redis_client: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._running = False
        self._update_lock = asyncio.Lock()
        self._last_update_time = 0.0
        self._short_interval = (
            Constant.DEFAULT_MIN_UPDATE_METRICS_INTERVAL_SECONDS
        )
        self._long_interval = (
            Constant.DEFAULT_MAX_UPDATE_METRICS_INTERVAL_SECONDS
        )
        self._scheduler_task: asyncio.Task | None = None
        self._start_lock = asyncio.Lock()

    def create_redis_client(self):
        """Create a Redis client instance."""
        if self._redis_client is not None:
            logger.warning("Redis client already exists, skipping creation")
            return
        self._redis_client = redis.Redis(
            host=Constant.DEFAULT_REDIS_SERVER_IP,
            port=Constant.DEFAULT_REDIS_SERVER_PORT,
            decode_responses=True,
            socket_connect_timeout=MetricsScheduler.REDIS_CONNECT_TIMEOUT,
            socket_timeout=MetricsScheduler.REDIS_SOCKET_TIMEOUT,
        )

    async def start_redis_client(self):
        """Start the Redis client and create a Pub/Sub instance."""
        self.create_redis_client()
        if self._pubsub is None:
            self._pubsub = self._redis_client.pubsub()
            await self._pubsub.subscribe(
                Constant.DEFAULT_METRICS_UPDATE_CHANNEL
            )
            logger.info(
                f"Subscribed to Redis channel: \
                {Constant.DEFAULT_METRICS_UPDATE_CHANNEL}"
            )
        else:
            logger.debug("PubSub instance already exists")

    async def _execute_update(self, source: str = "scheduled"):
        """Execute metrics update with concurrency control and rate limiting.

        Args:
            source: Identifies the trigger source (for logging).
        """
        # Quick check to avoid unnecessary lock attempts
        if not self._running and source != "initial":
            logger.debug(
                f"Skipping {source} update: scheduler is stopping/stopped"
            )
            return

        async with self._update_lock:
            # Re-check running state after acquiring lock
            if not self._running and source != "initial":
                logger.debug(
                    f"Skipping {source} update: \
                    scheduler stopped during lock wait"
                )
                return

            # Rate limiting: enforce minimum interval between updates
            now = time.time()
            if now - self._last_update_time < self._short_interval:
                logger.debug(
                    f"Skipping {source} update: last update was\
                    {now - self._last_update_time:.2f}s ago "
                    f"(min interval {self._short_interval}s)"
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

    async def _ensure_redis_connection(self) -> bool:
        """Ensure Redis connection is alive, reconnect if necessary.

        Returns:
            bool: True if connection is alive, False otherwise.
        """
        if self._redis_client is None or self._pubsub is None:
            logger.warning(
                "Redis client or pubsub is None, attempting reconnection"
            )
            try:
                await self.start_redis_client()
                return True
            except Exception as e:
                logger.error(
                    f"Failed to reconnect to Redis: {e}", exc_info=True
                )
                return False

        try:
            await self._redis_client.ping()
            return True
        except Exception as e:
            logger.warning(
                f"Redis connection lost: {e}, attempting reconnection"
            )
            try:
                await self._cleanup()
                await self.start_redis_client()
                return True
            except Exception as reconnect_error:
                logger.error(
                    f"Failed to reconnect to Redis: {reconnect_error}",
                    exc_info=True,
                )
                return False

    async def start(self):
        """Main scheduler loop subscribes to Redis and processes events."""
        # Set running state before starting logic to allow stop() to work
        async with self._start_lock:
            if self._running:
                logger.debug("Metrics scheduler is already running")
                return
            self._running = True

        logger.info(
            "Starting metrics scheduler (Redis Pub/Sub event-driven mode)"
        )

        try:
            await self.start_redis_client()

            # Initial update on startup after subscription
            await self._execute_update(source="initial")

            # Main event loop
            while self._running:
                try:
                    # Check Redis connection health
                    if not await self._ensure_redis_connection():
                        logger.warning(
                            "Redis connection unavailable, waiting..."
                        )
                        await asyncio.sleep(self._long_interval)
                        continue

                    # Wait for a message with a timeout
                    # get_message returns None if timeout is reached
                    message = await self._pubsub.get_message(
                        timeout=self._long_interval,
                        ignore_subscribe_messages=True,
                    )

                    if message is not None and message["type"] == "message":
                        # Event-driven update triggered by external signal
                        trigger_timestamp = message["data"]
                        logger.debug(
                            f"Metrics update event received \
                            via Redis (timestamp: {trigger_timestamp})"
                        )
                        await self._execute_update(source="event")
                    else:
                        # Timeout occurred – perform periodic fallback update
                        logger.debug(
                            "Performing periodic fallback metrics update"
                        )
                        await self._execute_update(source="fallback")

                except asyncio.CancelledError:
                    logger.debug("Scheduler loop cancelled")
                    break
                except Exception as e:
                    logger.error(
                        f"Unexpected error in scheduler loop: {e}",
                        exc_info=True,
                    )
                    if self._running:
                        # Avoid tight loop on persistent errors
                        await asyncio.sleep(self._long_interval)

        except Exception as e:
            logger.error(
                f"Failed to initialize metrics scheduler: {e}", exc_info=True
            )
            raise
        finally:
            await self._cleanup()

    async def stop(self) -> None:
        """Stop the metrics scheduler and wait for clean shutdown."""
        async with self._start_lock:
            if not self._running:
                logger.debug("Metrics scheduler already stopped")
                return

            logger.info("Stopping metrics scheduler...")
            self._running = False

        # Cancel the main scheduler task to interrupt any blocking calls
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                logger.debug("Scheduler task cancelled successfully")
            except Exception as e:
                logger.warning(f"Error while waiting for scheduler task: {e}")

        self._scheduler_task = None
        logger.info("Metrics scheduler stopped")

    async def _cleanup(self) -> None:
        """Release Redis connections and pubsub resources."""
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(
                    Constant.DEFAULT_METRICS_UPDATE_CHANNEL
                )
            except Exception as e:
                logger.debug(f"Error during unsubscribe: {e}")

            try:
                await self._pubsub.close()
            except Exception as e:
                logger.debug(f"Error closing pubsub: {e}")

            self._pubsub = None

        if self._redis_client:
            try:
                await self._redis_client.close()
            except Exception as e:
                logger.debug(f"Error closing Redis client: {e}")

            self._redis_client = None

        logger.info("Metrics scheduler cleanup completed")
