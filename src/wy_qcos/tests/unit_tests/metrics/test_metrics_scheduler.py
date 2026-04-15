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
import time
from unittest.mock import (
    AsyncMock,
    patch,
)

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.metrics.metrics_scheduler import MetricsScheduler


class TestMetricsScheduler:
    """Unit tests for MetricsScheduler."""

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
        assert scheduler._last_update_time == 0.0
        assert isinstance(scheduler._update_lock, asyncio.Lock)
        assert isinstance(scheduler._start_lock, asyncio.Lock)

    def test_execute_update_when_not_running(self, mock_logger):
        """Test _execute_update skips when scheduler is not running."""
        scheduler = MetricsScheduler()
        scheduler._running = False

        async def run():
            await scheduler._execute_update("test")

        asyncio.run(run())
        mock_logger.debug.assert_called_once()
        assert (
            "Skipping test update: scheduler is stopping/stopped"
            in mock_logger.debug.call_args[0][0]
        )

    def test_execute_update_rate_limited(self, mock_logger):
        """Test rate limiting skips update if called too soon."""
        scheduler = MetricsScheduler()
        scheduler._running = True
        interval = Constant.DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS
        scheduler._interval = interval

        scheduler._last_update_time = time.time() - interval - 10

        async def run():
            with patch(
                "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
                new_callable=AsyncMock,
            ) as mock_update:
                # First update – should run
                await scheduler._execute_update("first")
                assert mock_update.called
                # Second update – called immediately, should be rate limited
                await scheduler._execute_update("second")
                assert mock_update.call_count == 1

        asyncio.run(run())

        # Verify skip log
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("Skipping second update" in msg for msg in debug_calls)

    def test_execute_update_success(self, mock_logger):
        """Test successful metrics update."""
        scheduler = MetricsScheduler()
        scheduler._running = True
        scheduler._last_update_time = 0.0

        async def run():
            with patch(
                "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
                new_callable=AsyncMock,
            ) as mock_update:
                await scheduler._execute_update("test")
                mock_update.assert_awaited_once()
                assert scheduler._last_update_time > 0

        asyncio.run(run())
        assert mock_logger.debug.call_count >= 2

    def test_execute_update_exception(self, mock_logger):
        """Test exception during update is caught and logged."""
        scheduler = MetricsScheduler()
        scheduler._running = True
        scheduler._last_update_time = 0.0

        async def run():
            with patch(
                "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
                new_callable=AsyncMock,
                side_effect=RuntimeError("update failed"),
            ) as mock_update:
                await scheduler._execute_update("test")
                mock_update.assert_awaited_once()
                assert scheduler._last_update_time > 0

        asyncio.run(run())
        mock_logger.error.assert_called_once()
        assert (
            "Error during metrics update (test): update failed"
            in mock_logger.error.call_args[0][0]
        )

    def test_start_already_running(self, mock_logger):
        """Test start returns early if scheduler already running."""
        scheduler = MetricsScheduler()
        scheduler._running = True

        async def run():
            await scheduler.start()

        asyncio.run(run())
        mock_logger.debug.assert_called_with(
            "Metrics scheduler is already running"
        )
        assert scheduler._running is True

    def test_start_stop_normal_flow(self, mock_logger):
        """Test normal start and stop flow with periodic updates."""
        scheduler = MetricsScheduler()
        scheduler._interval = 0.05

        mock_update = AsyncMock()
        with patch(
            "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
            mock_update,
        ):

            async def run():
                task = asyncio.create_task(scheduler.start())
                await asyncio.sleep(0.15)
                await scheduler.stop()
                await task

            asyncio.run(run())

        assert mock_update.await_count >= 3
        mock_logger.info.assert_any_call(
            f"Starting periodic metrics scheduler \
            (interval: {scheduler._interval}s)"
        )
        mock_logger.info.assert_any_call("Metrics scheduler stopped")
        mock_logger.info.assert_any_call("Stopping metrics scheduler...")
        assert scheduler._running is False

    def test_start_handles_cancelled_error(self, mock_logger):
        """Test CancelledError is caught and stops the scheduler cleanly."""
        scheduler = MetricsScheduler()
        scheduler._interval = 0.05

        with patch(
            "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
            new_callable=AsyncMock,
        ):

            async def run():
                task = asyncio.create_task(scheduler.start())
                await asyncio.sleep(0.1)
                task.cancel()
                await asyncio.sleep(0.05)
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                assert scheduler._running is False

            asyncio.run(run())

        mock_logger.debug.assert_any_call("Scheduler loop cancelled")

    def test_start_loop_exception_continues(self, mock_logger):
        """Test that exception in loop does not crash, but continues."""
        scheduler = MetricsScheduler()
        scheduler._interval = 0.05

        mock_update = AsyncMock()
        mock_update.side_effect = [RuntimeError("init fail"), None, None]

        with patch(
            "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
            mock_update,
        ):

            async def run():
                task = asyncio.create_task(scheduler.start())
                await asyncio.sleep(0.15)
                await scheduler.stop()
                await task

            asyncio.run(run())

        mock_logger.error.assert_any_call(
            "Error during metrics update (initial): init fail", exc_info=True
        )
        assert mock_update.await_count >= 2
        assert scheduler._running is False

    def test_stop_when_not_running(self, mock_logger):
        """Test stop does nothing if scheduler already stopped."""
        scheduler = MetricsScheduler()
        scheduler._running = False

        async def run():
            await scheduler.stop()

        asyncio.run(run())
        mock_logger.debug.assert_called_with(
            "Metrics scheduler already stopped"
        )

    def test_concurrent_execute_update_locks(self, mock_logger):
        """Test that _execute_update respects the lock and rate limiting."""
        scheduler = MetricsScheduler()
        scheduler._running = True
        scheduler._interval = 0.2

        async def slow_update():
            await asyncio.sleep(0.1)
            return

        with patch(
            "wy_qcos.metrics.metrics_scheduler.update_metrics_task_async",
            new_callable=AsyncMock,
            side_effect=slow_update,
        ):

            async def run():
                task1 = asyncio.create_task(scheduler._execute_update("first"))
                await asyncio.sleep(0.02)
                task2 = asyncio.create_task(
                    scheduler._execute_update("second")
                )
                await asyncio.gather(task1, task2)

            asyncio.run(run())

        debug_msgs = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("Skipping second update" in msg for msg in debug_msgs)
