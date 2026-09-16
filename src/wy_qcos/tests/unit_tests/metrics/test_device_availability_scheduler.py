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

"""Unit tests for DeviceAvailabilityScheduler."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.metrics.device_availability_scheduler import (
    DeviceAvailabilityScheduler,
)


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestDeviceAvailabilityScheduler:
    """Unit tests for DeviceAvailabilityScheduler (APScheduler-based)."""

    @pytest.fixture(autouse=True)
    def mock_logger(self):
        """Mock logger to avoid actual logging during tests."""
        with patch(
            "wy_qcos.metrics.device_availability_scheduler.logger"
        ) as mock_log:
            yield mock_log

    @pytest.mark.smoke
    def test_init(self):
        """Test initial state and cron minute configuration."""
        scheduler = DeviceAvailabilityScheduler()
        assert not scheduler._running
        assert scheduler._cron_minute == (
            Constant.DEFAULT_AVAILABILITY_AGGREGATE_CRON_MINUTE
        )
        assert scheduler._cron_minute == 0

    def test_start_already_running(self, mock_logger):
        """Test start returns early if scheduler already running."""
        scheduler = DeviceAvailabilityScheduler()
        scheduler._running = True

        run_async(scheduler.start())
        mock_logger.debug.assert_called_with(
            "DeviceAvailabilityScheduler already running"
        )
        assert scheduler._running is True

    @pytest.mark.smoke
    def test_start_stop_normal_flow(self, mock_logger):
        """Test normal start and stop flow registers hourly job."""
        with (
            patch(
                "wy_qcos.metrics.device_availability_scheduler.AsyncIOScheduler"
            ) as mock_sched_class,
            patch(
                "wy_qcos.metrics.device_availability_scheduler.CronTrigger"
            ) as mock_trigger_class,
        ):
            mock_instance = MagicMock()
            mock_sched_class.return_value = mock_instance

            scheduler = DeviceAvailabilityScheduler()
            run_async(scheduler.start())

            mock_instance.start.assert_called_once()
            # job registered with cron trigger (minute=0)
            mock_trigger_class.assert_called_with(minute=0)
            mock_instance.add_job.assert_called_once()
            add_kwargs = mock_instance.add_job.call_args.kwargs
            assert add_kwargs["id"] == "device_availability_aggregate"
            assert add_kwargs["replace_existing"] is True
            assert add_kwargs["coalesce"] is True
            assert add_kwargs["max_instances"] == 1

            run_async(scheduler.stop())
            mock_instance.shutdown.assert_called_with(wait=True)

        start_called = any(
            "Starting DeviceAvailabilityScheduler" in c[0][0]
            for c in mock_logger.info.call_args_list
        )
        assert start_called
        stop_called = any(
            "DeviceAvailabilityScheduler stopped" in c[0][0]
            for c in mock_logger.info.call_args_list
        )
        assert stop_called

    def test_start_registers_hourly_cron_trigger(self, mock_logger):
        """CronTrigger must fire at the top of every hour (minute=0)."""
        with (
            patch(
                "wy_qcos.metrics.device_availability_scheduler.AsyncIOScheduler"
            ) as mock_sched_class,
            patch(
                "wy_qcos.metrics.device_availability_scheduler.CronTrigger"
            ) as mock_trigger_class,
        ):
            mock_instance = MagicMock()
            mock_sched_class.return_value = mock_instance

            scheduler = DeviceAvailabilityScheduler()
            run_async(scheduler.start())

            mock_trigger_class.assert_called_once_with(minute=0)

    def test_stop_when_not_running(self, mock_logger):
        """Test stop does nothing if scheduler already stopped."""
        scheduler = DeviceAvailabilityScheduler()
        scheduler._running = False

        run_async(scheduler.stop())
        mock_logger.debug.assert_called_with(
            "DeviceAvailabilityScheduler already stopped"
        )

    def test_scheduler_shutdown_error_handled(self, mock_logger):
        """Test scheduler shutdown doesn't crash on errors."""
        scheduler = DeviceAvailabilityScheduler()
        scheduler._running = True

        with patch(
            "wy_qcos.metrics.device_availability_scheduler.AsyncIOScheduler"
        ) as mock_sched_class:
            mock_instance = MagicMock()
            mock_sched_class.return_value = mock_instance
            mock_instance.shutdown.side_effect = RuntimeError("crash")

            run_async(scheduler.stop())

        mock_logger.warning.assert_called()
        assert "shutdown" in mock_logger.warning.call_args[0][0].lower()

    @pytest.mark.smoke
    def test_job_calls_aggregate_when_running(self, mock_logger):
        """Test _job invokes aggregate_availability_hourly when running."""
        scheduler = DeviceAvailabilityScheduler()
        scheduler._running = True

        mock_aggregate = AsyncMock()
        with patch(
            "wy_qcos.metrics.device_availability_task.aggregate_availability_hourly",
            mock_aggregate,
        ):
            run_async(scheduler._job())

        assert mock_aggregate.await_count == 1

    def test_job_ignores_when_not_running(self, mock_logger):
        """Test _job skips aggregation when scheduler is stopping."""
        scheduler = DeviceAvailabilityScheduler()
        scheduler._running = False

        mock_aggregate = AsyncMock()
        with patch(
            "wy_qcos.metrics.device_availability_task.aggregate_availability_hourly",
            mock_aggregate,
        ):
            run_async(scheduler._job())

        assert not mock_aggregate.called

    def test_job_logs_exception(self, mock_logger):
        """Test _job logs error but does not crash on failure."""
        scheduler = DeviceAvailabilityScheduler()
        scheduler._running = True

        mock_aggregate = AsyncMock(side_effect=RuntimeError("job error"))
        with patch(
            "wy_qcos.metrics.device_availability_task.aggregate_availability_hourly",
            mock_aggregate,
        ):
            run_async(scheduler._job())

        assert mock_aggregate.await_count == 1
        mock_logger.error.assert_called_once()
        assert (
            "Error during device availability aggregation (periodic)"
            in mock_logger.error.call_args[0][0]
        )
