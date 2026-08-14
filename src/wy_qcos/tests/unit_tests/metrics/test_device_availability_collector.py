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
