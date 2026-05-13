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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.metrics.metrics_scheduler import MetricsScheduler


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestMetricsScheduler:
    """Unit tests for MetricsScheduler (APScheduler-based)."""

    @pytest.fixture(autouse=True)
    def mock_logger(self):
        """Mock logger to avoid actual logging during tests."""
        with patch("wy_qcos.metrics.metrics_scheduler.logger") as mock_log:
            yield mock_log

    def test_init(self):
        """Test initial state."""
        scheduler = MetricsScheduler()
        assert not scheduler._running
        assert (
            scheduler._interval
            == Constant.DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS
        )

    def test_start_already_running(self, mock_logger):
        """Test start returns early if scheduler already running."""
        scheduler = MetricsScheduler()
        scheduler._running = True

        run_async(scheduler.start())
        mock_logger.debug.assert_called_with(
            "Metrics scheduler is already running"
        )
        assert scheduler._running is True

    def test_start_stop_normal_flow(self, mock_logger):
        """Test normal start and stop flow with periodic updates."""
        with (
            patch(
                "wy_qcos.metrics.metrics_scheduler.AsyncIOScheduler"
            ) as mock_sched_class,
            patch(
                "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async"
            ) as mock_update,
        ):
            mock_instance = MagicMock()
            mock_sched_class.return_value = mock_instance

            scheduler = MetricsScheduler()
            scheduler._interval = 0.05

            run_async(scheduler.start())
            mock_instance.start.assert_called_once()
            mock_instance.add_job.assert_called_once()

            # Simulate APScheduler triggering the _job coroutine n times
            mock_update.side_effect = [None, None, None]
            for _ in range(3):
                run_async(scheduler._job())

            run_async(scheduler.stop())
            mock_instance.shutdown.assert_called_with(wait=True)

        # start() calls update_metrics_task_async once for initial
        assert mock_update.await_count >= 1

        start_called = any(
            "Starting periodic metrics scheduler" in c[0][0]
            for c in mock_logger.info.call_args_list
        )
        assert start_called
        stop_called = any(
            "Metrics scheduler stopped" in c[0][0]
            for c in mock_logger.info.call_args_list
        )
        assert stop_called

    def test_scheduler_shutdown_error_handled(self, mock_logger):
        """Test scheduler shutdown doesn't crash on errors."""
        scheduler = MetricsScheduler()
        scheduler._running = True

        with patch(
            "wy_qcos.metrics.metrics_scheduler.AsyncIOScheduler"
        ) as mock_sched_class:
            mock_instance = MagicMock()
            mock_sched_class.return_value = mock_instance
            mock_instance.shutdown.side_effect = RuntimeError("crash")

            run_async(scheduler.stop())

        mock_logger.warning.assert_called()
        assert "shutdown" in mock_logger.warning.call_args[0][0].lower()

    def test_stop_when_not_running(self, mock_logger):
        """Test stop does nothing if scheduler already stopped."""
        scheduler = MetricsScheduler()
        scheduler._running = False

        run_async(scheduler.stop())
        mock_logger.debug.assert_called_with(
            "Metrics scheduler already stopped"
        )

    def test_job_ignores_when_not_running(self, mock_logger):
        """Test _job skips update when scheduler is stopping."""
        scheduler = MetricsScheduler()
        scheduler._running = False

        mock_update = AsyncMock()
        with patch(
            "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
            mock_update,
        ):
            run_async(scheduler._job())

        assert not mock_update.called

    def test_job_success(self, mock_logger):
        """Test _job calls update_metrics_task_async successfully."""
        scheduler = MetricsScheduler()
        scheduler._running = True

        mock_update = AsyncMock()
        with patch(
            "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
            mock_update,
        ):
            run_async(scheduler._job())

        assert mock_update.await_count == 1

    def test_job_logs_exception(self, mock_logger):
        """Test _job logs error but does not crash on failure."""
        scheduler = MetricsScheduler()
        scheduler._running = True

        mock_update = AsyncMock(side_effect=RuntimeError("job error"))
        with patch(
            "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
            mock_update,
        ):
            run_async(scheduler._job())

        assert mock_update.await_count == 1
        mock_logger.error.assert_called_once()
        assert (
            "Error during metrics update (periodic)"
            in mock_logger.error.call_args[0][0]
        )
