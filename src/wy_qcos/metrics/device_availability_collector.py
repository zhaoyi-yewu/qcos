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

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

import redis

from wy_qcos.common.constant import Constant
from wy_qcos.db.repositories.device_availability import (
    DeviceAvailabilityRepository,
)
from wy_qcos.db.utils.db_utils import create_db_session

logger = logging.getLogger(__name__)


@dataclass
class DeviceAvailabilityCounter:
    """In-memory availability counters for one device in the current hour."""

    online_count: int = 0
    total_count: int = 0


@dataclass
class _Snapshot:
    """Snapshot of counters for all devices."""

    counters: dict = field(default_factory=dict)


class DeviceAvailabilityCollector:
    """Collect device availability samples from Redis into in-memory counters.

    A background thread subscribes (pattern) to the device running
    info Redis channel for all devices. Each published status sample
    increments the per-device counter. ``online``/``busy`` statuses
    increment ``online_count``; every sample increments
    ``total_count``.

    ``snapshot_and_reset`` atomically returns the current counters
    and resets them, so the hourly aggregation task can persist the
    counts and start fresh for the next hour.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton: one collector per process."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # avoid re-init for singleton
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._lock = threading.Lock()
        self._counters: dict[str, DeviceAvailabilityCounter] = {}
        self._thread: threading.Thread | None = None
        self._running = False
        self._redis_url = None
        self._pattern = (
            f"{Constant.REDIS_CHANNEL_DEVICE_RUNNING_INFO_PREFIX}/*"
        )

    @classmethod
    def reset_instance(cls):
        """Reset the singleton (mainly for tests)."""
        with cls._instance_lock:
            cls._instance = None

    def configure(self, redis_url):
        """Configure Redis connection parameters.

        Args:
            redis_url: Redis server URL (e.g. redis://127.0.0.1:6379/0)
        """
        self._redis_url = redis_url

    def start(self):
        """Start the background subscription thread."""
        if self._running:
            logger.debug("DeviceAvailabilityCollector already running")
            return
        if self._redis_url is None:
            logger.error(
                "DeviceAvailabilityCollector not configured, skip start"
            )
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._subscribe_loop, daemon=True
        )
        self._thread.start()
        logger.info("DeviceAvailabilityCollector started")

    def stop(self):
        """Stop the background subscription thread."""
        self._running = False
        logger.info("DeviceAvailabilityCollector stopped")

    def _subscribe_loop(self):
        """Subscribe to the device running info pattern channel.

        Increments counters for each received status sample and
        reconnects on error.
        """
        while self._running:
            try:
                client = redis.Redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    protocol=2,
                )
                pubsub = client.pubsub()
                pubsub.psubscribe(self._pattern)
                logger.info(
                    f"DeviceAvailabilityCollector subscribed to "
                    f"{self._pattern}"
                )
                for message in pubsub.listen():
                    if not self._running:
                        break
                    if message.get("type") != "pmessage":
                        continue
                    channel = message.get("channel", "")
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")
                    data = message.get("data")
                    if not data:
                        continue
                    self._handle_message(channel, data)
            except Exception as e:
                logger.error(
                    f"DeviceAvailabilityCollector subscribe error: {e}"
                )
                # brief sleep before reconnect
                time.sleep(1)

    def _handle_message(self, channel, data):
        """Parse a Redis message and increment counters.

        Args:
            channel: the channel name
                (qcos/device_running_info/<device_name>)
            data: the message data (JSON string)
        """
        try:
            info = json.loads(data)
        except (TypeError, ValueError) as e:
            logger.warning(
                f"DeviceAvailabilityCollector: invalid data on {channel}: {e}"
            )
            return
        # extract device name from the channel suffix
        prefix = Constant.REDIS_CHANNEL_DEVICE_RUNNING_INFO_PREFIX + "/"
        device_name = channel
        if channel.startswith(prefix):
            device_name = channel[len(prefix) :]
        status = info.get("status", "")
        with self._lock:
            counter = self._counters.get(device_name)
            if counter is None:
                counter = DeviceAvailabilityCounter()
                self._counters[device_name] = counter
            counter.total_count += 1
            if status in Constant.DEVICE_AVAILABILITY_STATUS_ONLINE_BUSY:
                counter.online_count += 1

    def snapshot_and_reset(self) -> dict:
        """Atomically snapshot current counters and reset them.

        Returns:
            dict mapping device_name to DeviceAvailabilityCounter copy
        """
        with self._lock:
            snap = {
                name: DeviceAvailabilityCounter(
                    online_count=c.online_count,
                    total_count=c.total_count,
                )
                for name, c in self._counters.items()
            }
            self._counters.clear()
        return snap

    def get_rate(self, device_name) -> float | None:
        """Get the current-hour real-time availability rate for a device.

        Args:
            device_name: device name

        Returns:
            availability rate (0.0-1.0), or None when no samples yet
        """
        with self._lock:
            counter = self._counters.get(device_name)
            if counter is None or counter.total_count == 0:
                return None
            return counter.online_count / counter.total_count

    def get_counts(self, device_name) -> tuple[int, int] | None:
        """Get current-hour raw (online_count, total_count).

        Args:
            device_name: device name

        Returns:
            (online_count, total_count) tuple, or None when no
            samples yet
        """
        with self._lock:
            counter = self._counters.get(device_name)
            if counter is None or counter.total_count == 0:
                return None
            return (counter.online_count, counter.total_count)

    @staticmethod
    def compute_availability_rates(
        device_name: str,
        db_engine=None,
    ) -> tuple[float | None, float | None]:
        """Compute current-hour and overall availability rates.

        Aggregates all historical hourly records (from the
        device_availability_hourly table, before the current hour) with
        the current-hour real-time counts from the in-memory
        DeviceAvailabilityCollector singleton.

        Args:
            device_name: device name
            db_engine: SQLAlchemy database engine for historical
                records. When None, only current-hour data is used.

        Returns:
            (current_hour_rate, overall_rate) tuple. Each value is
            0.0-1.0 (rounded to 2 decimals) or None when no data.
        """
        log = logging.getLogger(__name__)

        cur_online = 0
        cur_total = 0
        current_rate = None
        try:
            collector = DeviceAvailabilityCollector()
            current_rate = collector.get_rate(device_name)
            counts = collector.get_counts(device_name)
            if counts is not None:
                cur_online, cur_total = counts
        except Exception as e:
            log.debug(
                f"Failed to get current-hour availability for "
                f"{device_name}: {e}"
            )
        if current_rate is not None:
            current_rate = round(current_rate, 5)

        hist_online = 0
        hist_total = 0
        if db_engine is not None:
            try:
                now = datetime.now()
                current_hour = now.replace(minute=0, second=0, microsecond=0)
                with create_db_session(db_engine) as db_session:
                    repo = DeviceAvailabilityRepository(db_session)
                    counts = repo.get_overall_availability_counts(
                        device_name, before_hour=current_hour
                    )
                    if counts is not None:
                        hist_online, hist_total = counts
            except Exception as e:
                log.debug(
                    f"Failed to get historical availability for "
                    f"{device_name}: {e}"
                )

        merged_online = hist_online + cur_online
        merged_total = hist_total + cur_total
        if merged_total > 0:
            overall = round(merged_online / merged_total, 5)
        elif current_rate is not None:
            overall = current_rate
        else:
            overall = None
        return (current_rate, overall)
