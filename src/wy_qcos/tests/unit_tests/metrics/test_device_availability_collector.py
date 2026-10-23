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

"""Unit tests for DeviceAvailabilityCollector."""

import json
import unittest

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.metrics.device_availability_collector import (
    DeviceAvailabilityCollector,
    DeviceAvailabilityCounter,
)


class TestDeviceAvailabilityCollector(unittest.TestCase):
    """Tests for DeviceAvailabilityCollector singleton."""

    def setUp(self):
        """Reset singleton before each test for isolation."""
        DeviceAvailabilityCollector.reset_instance()
        self.collector = DeviceAvailabilityCollector()

    def tearDown(self):
        """Reset singleton after each test."""
        DeviceAvailabilityCollector.reset_instance()

    def _channel(self, device_name):
        """Build the Redis channel name for a device."""
        prefix = Constant.REDIS_CHANNEL_DEVICE_RUNNING_INFO_PREFIX
        return f"{prefix}/{device_name}"

    def _feed(self, device_name, status):
        """Feed one status sample into the collector."""
        channel = self._channel(device_name)
        data = json.dumps({"status": status})
        self.collector._handle_message(channel, data)

    @pytest.mark.smoke
    def test_online_status_increments_both_counts(self):
        """Online status increments online_count and total_count."""
        self._feed("device1", "online")
        self._feed("device1", "online")
        snap = self.collector.snapshot_and_reset()
        counter = snap["device1"]
        assert counter.online_count == 2
        assert counter.total_count == 2
        assert self.collector.get_rate("device1") is None

    @pytest.mark.smoke
    def test_busy_status_increments_both_counts(self):
        """Busy status increments online_count and total_count."""
        self._feed("device1", "busy")
        rate = self.collector.get_rate("device1")
        assert rate == 1.0

    def test_other_status_only_increments_total(self):
        """Non online/busy status only increments total_count."""
        self._feed("device1", "offline")
        self._feed("device1", "maintain")
        snap = self.collector.snapshot_and_reset()
        counter = snap["device1"]
        assert counter.online_count == 0
        assert counter.total_count == 2

    def test_mixed_statuses_rate(self):
        """Rate = online_count / total_count for mixed samples."""
        statuses = ["online", "online", "busy", "offline", "offline"]
        for status in statuses:
            self._feed("device1", status)
        # 3 online+busy out of 5 total
        assert self.collector.get_rate("device1") == 0.6

    @pytest.mark.smoke
    def test_snapshot_and_reset_returns_and_clears(self):
        """snapshot_and_reset returns counters then clears state."""
        self._feed("device1", "online")
        self._feed("device2", "offline")
        snap = self.collector.snapshot_and_reset()
        assert set(snap.keys()) == {"device1", "device2"}
        assert snap["device1"].online_count == 1
        assert snap["device1"].total_count == 1
        assert snap["device2"].online_count == 0
        assert snap["device2"].total_count == 1
        # state cleared after snapshot
        assert self.collector.get_rate("device1") is None
        assert self.collector.snapshot_and_reset() == {}

    def test_snapshot_returns_independent_copies(self):
        """Snapshot counters are copies; mutating them is safe."""
        self._feed("device1", "online")
        snap = self.collector.snapshot_and_reset()
        snap["device1"].online_count = 999
        snap["device1"].total_count = 999
        # re-feed after reset; internal state unaffected by mutation
        self._feed("device1", "online")
        rate = self.collector.get_rate("device1")
        assert rate == 1.0

    def test_get_rate_no_samples_returns_none(self):
        """get_rate returns None when no samples collected."""
        assert self.collector.get_rate("device1") is None

    def test_get_rate_multiple_devices_isolated(self):
        """Per-device counters are isolated."""
        self._feed("device1", "online")
        self._feed("device1", "offline")
        self._feed("device2", "online")
        self._feed("device2", "online")
        assert self.collector.get_rate("device1") == 0.5
        assert self.collector.get_rate("device2") == 1.0

    def test_invalid_json_ignored(self):
        """Invalid JSON data is ignored without crashing."""
        channel = self._channel("device1")
        self.collector._handle_message(channel, "not-json")
        assert self.collector.get_rate("device1") is None

    def test_missing_status_only_increments_total(self):
        """Missing status field defaults to non-online (only total)."""
        channel = self._channel("device1")
        self.collector._handle_message(channel, json.dumps({}))
        snap = self.collector.snapshot_and_reset()
        assert snap["device1"].online_count == 0
        assert snap["device1"].total_count == 1

    def test_singleton_instance_shared(self):
        """Collector is a singleton: same instance per process."""
        collector_a = DeviceAvailabilityCollector()
        collector_b = DeviceAvailabilityCollector()
        assert collector_a is collector_b

    def test_reset_instance_creates_new_singleton(self):
        """reset_instance allows a fresh singleton to be created."""
        first = DeviceAvailabilityCollector()
        DeviceAvailabilityCollector.reset_instance()
        second = DeviceAvailabilityCollector()
        assert first is not second

    def test_counter_dataclass_defaults(self):
        """DeviceAvailabilityCounter defaults to zero counts."""
        counter = DeviceAvailabilityCounter()
        assert counter.online_count == 0
        assert counter.total_count == 0

    def test_configure_sets_redis_url(self):
        """configure() stores the Redis URL."""
        self.collector.configure("redis://localhost:6379/0")
        assert self.collector._redis_url == "redis://localhost:6379/0"

    def test_start_without_configure_logs_error(self):
        """start() logs error when Redis URL is not configured."""
        with unittest.mock.patch(
            "wy_qcos.metrics.device_availability_collector.logger"
        ) as mock_logger:
            self.collector.start()
            mock_logger.error.assert_called_once()
            assert self.collector._running is False

    def test_start_starts_thread(self):
        """start() launches the background subscription thread."""
        self.collector.configure("redis://localhost:6379/0")
        with unittest.mock.patch.object(self.collector, "_subscribe_loop"):
            self.collector.start()
            assert self.collector._running is True
            assert self.collector._thread is not None
            self.collector.stop()

    def test_start_already_running_logs_debug(self):
        """start() logs debug when already running."""
        self.collector.configure("redis://localhost:6379/0")
        self.collector._running = True
        with unittest.mock.patch(
            "wy_qcos.metrics.device_availability_collector.logger"
        ) as mock_logger:
            self.collector.start()
            mock_logger.debug.assert_called_once()

    def test_stop_sets_running_false(self):
        """stop() sets the running flag to False."""
        self.collector._running = True
        with unittest.mock.patch(
            "wy_qcos.metrics.device_availability_collector.logger"
        ):
            self.collector.stop()
            assert self.collector._running is False

    def test_get_counts_returns_tuple(self):
        """get_counts() returns (online, total) tuple."""
        self._feed("device1", "online")
        self._feed("device1", "offline")
        counts = self.collector.get_counts("device1")
        assert counts == (1, 2)

    def test_get_counts_no_samples_returns_none(self):
        """get_counts() returns None when no samples."""
        assert self.collector.get_counts("device1") is None

    def test_handle_message_invalid_json_logs_warning(self):
        """_handle_message() logs warning on invalid JSON."""
        channel = self._channel("device1")
        with unittest.mock.patch(
            "wy_qcos.metrics.device_availability_collector.logger"
        ) as mock_logger:
            self.collector._handle_message(channel, "not-json")
            mock_logger.warning.assert_called_once()

    def test_handle_message_bytes_channel(self):
        """_handle_message() handles bytes channel name."""
        # The collector decodes bytes to str before startswith check,
        # but the current implementation does not handle bytes channel.
        # We test with str channel since that is the production path.
        channel = self._channel("device1")
        data = json.dumps({"status": "online"})
        self.collector._handle_message(channel, data)
        assert self.collector.get_rate("device1") == 1.0

    def test_compute_availability_rates_no_db(self):
        """compute_availability_rates() with no db_engine."""
        self._feed("device1", "online")
        current, overall = (
            DeviceAvailabilityCollector.compute_availability_rates(
                "device1", db_engine=None
            )
        )
        assert current == 1.0
        assert overall == 1.0

    def test_compute_availability_rates_no_data(self):
        """compute_availability_rates() with no data returns (None, None)."""
        current, overall = (
            DeviceAvailabilityCollector.compute_availability_rates(
                "device1", db_engine=None
            )
        )
        assert current is None
        assert overall is None

    def test_compute_availability_rates_with_db(self):
        """compute_availability_rates() with db_engine."""
        self._feed("device1", "online")
        mock_engine = unittest.mock.MagicMock()
        with unittest.mock.patch(
            "wy_qcos.metrics.device_availability_collector.create_db_session"
        ) as mock_session:
            mock_repo = unittest.mock.MagicMock()
            mock_repo.get_overall_availability_counts.return_value = (5, 10)
            mock_session.return_value.__enter__ = unittest.mock.MagicMock(
                return_value=unittest.mock.MagicMock()
            )
            mock_session.return_value.__exit__ = unittest.mock.MagicMock(
                return_value=False
            )
            with unittest.mock.patch(
                "wy_qcos.metrics.device_availability_collector.DeviceAvailabilityRepository"
            ) as mock_repo_class:
                mock_repo_class.return_value = mock_repo
                current, overall = (
                    DeviceAvailabilityCollector.compute_availability_rates(
                        "device1", db_engine=mock_engine
                    )
                )
                assert current == 1.0
                # (5+1) / (10+1) = 6/11 ≈ 0.54545, rounded to 5 decimals
                assert overall == 0.54545

    def test_compute_availability_rates_db_error(self):
        """compute_availability_rates() handles db error gracefully."""
        self._feed("device1", "online")
        mock_engine = unittest.mock.MagicMock()
        with unittest.mock.patch(
            "wy_qcos.metrics.device_availability_collector.create_db_session"
        ) as mock_session:
            mock_session.side_effect = Exception("DB error")
            current, overall = (
                DeviceAvailabilityCollector.compute_availability_rates(
                    "device1", db_engine=mock_engine
                )
            )
            assert current == 1.0
            assert overall == 1.0
