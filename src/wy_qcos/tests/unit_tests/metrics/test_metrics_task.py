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
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

from wy_qcos.common.constant import Constant


class TestUpdateJobMetrics:
    """Unit Tests for update_job_metrics function."""

    def test_update_job_metrics_with_mixed_statuses(self):
        """Test updating job metrics with various job statuses."""
        mock_jobs = [
            {"job_status": Constant.JOB_STATUS_COMPLETED},
            {"job_status": Constant.JOB_STATUS_COMPLETED},
            {"job_status": Constant.JOB_STATUS_FAILED},
            {"job_status": Constant.JOB_STATUS_RUNNING},
            {"job_status": Constant.JOB_STATUS_RUNNING},
            {"job_status": Constant.JOB_STATUS_RUNNING},
            {"job_status": Constant.JOB_STATUS_QUEUED},
            {"job_status": Constant.JOB_STATUS_CANCELLING},
            {"job_status": Constant.JOB_STATUS_CANCELLED},
            {"job_status": Constant.JOB_STATUS_UNKNOWN},
        ]

        mock_scheduler = AsyncMock()
        mock_scheduler.aget_jobs = AsyncMock(return_value=(mock_jobs, None))

        mock_job_metrics_data = MagicMock()
        mock_update_job_metrics = MagicMock()

        async def _run():
            with (
                patch("wy_qcos.task_manager.scheduler", mock_scheduler),
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.job_metrics.JobMetricsData",
                    return_value=mock_job_metrics_data,
                ) as mock_data_class,
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.update_job_metrics",
                    mock_update_job_metrics,
                ),
            ):
                from wy_qcos.metrics.metrics_task import update_job_metrics

                await update_job_metrics()

                mock_scheduler.aget_jobs.assert_called_once()
                mock_data_class.assert_called_once_with(
                    total=10,
                    success=2,
                    failed=1,
                    running=3,
                    queued=1,
                    cancelling=1,
                    cancelled=1,
                    unknown=1,
                )
                mock_update_job_metrics.assert_called_once_with(
                    data=mock_job_metrics_data
                )

        asyncio.run(_run())

    def test_update_job_metrics_empty_response(self):
        """Test updating job metrics with empty response list."""
        mock_scheduler = AsyncMock()
        mock_scheduler.aget_jobs = AsyncMock(return_value=([], None))
        mock_update_job_metrics = MagicMock()

        async def _run():
            with (
                patch("wy_qcos.task_manager.scheduler", mock_scheduler),
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.update_job_metrics",
                    mock_update_job_metrics,
                ),
            ):
                from wy_qcos.metrics.metrics_task import update_job_metrics

                await update_job_metrics()

                mock_scheduler.aget_jobs.assert_called_once()
                mock_update_job_metrics.assert_not_called()

        asyncio.run(_run())

    def test_update_job_metrics_none_response(self):
        """Test updating job metrics with None response."""
        mock_scheduler = AsyncMock()
        mock_scheduler.aget_jobs = AsyncMock(return_value=(None, None))
        mock_update_job_metrics = MagicMock()

        async def _run():
            with (
                patch("wy_qcos.task_manager.scheduler", mock_scheduler),
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.update_job_metrics",
                    mock_update_job_metrics,
                ),
            ):
                from wy_qcos.metrics.metrics_task import update_job_metrics

                await update_job_metrics()

                mock_scheduler.aget_jobs.assert_called_once()
                mock_update_job_metrics.assert_not_called()

        asyncio.run(_run())

    def test_update_job_metrics_with_missing_status(self):
        """Test updating job metrics when some jobs have missing status."""
        mock_jobs = [
            {"job_status": Constant.JOB_STATUS_COMPLETED},
            {},
            {"other_field": "value"},
        ]

        mock_scheduler = AsyncMock()
        mock_scheduler.aget_jobs = AsyncMock(return_value=(mock_jobs, None))
        mock_job_metrics_data = MagicMock()
        mock_update_job_metrics = MagicMock()

        async def _run():
            with (
                patch("wy_qcos.task_manager.scheduler", mock_scheduler),
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.job_metrics.JobMetricsData",
                    return_value=mock_job_metrics_data,
                ) as mock_data_class,
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.update_job_metrics",
                    mock_update_job_metrics,
                ),
            ):
                from wy_qcos.metrics.metrics_task import update_job_metrics

                await update_job_metrics()

                mock_data_class.assert_called_once_with(
                    total=3,
                    success=1,
                    failed=0,
                    running=0,
                    queued=0,
                    cancelling=0,
                    cancelled=0,
                    unknown=0,
                )

        asyncio.run(_run())


class TestUpdateMetricsTaskAsync:
    """Tests for update_metrics_task_async function."""

    def test_update_metrics_task_async_success(self):
        """Test successful execution of update_metrics_task_async."""
        mock_update_job_metrics = AsyncMock()

        async def _run():
            with patch(
                "wy_qcos.metrics.metrics_task.update_job_metrics",
                mock_update_job_metrics,
            ):
                from wy_qcos.metrics.metrics_task import (
                    update_metrics_task_async,
                )

                await update_metrics_task_async()
                mock_update_job_metrics.assert_called_once()

        asyncio.run(_run())

    def test_update_metrics_task_async_exception_handling(self):
        """Test exception handling in update_metrics_task_async."""
        mock_update_job_metrics = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_logger_error = MagicMock()

        async def _run():
            with (
                patch(
                    "wy_qcos.metrics.metrics_task.update_job_metrics",
                    mock_update_job_metrics,
                ),
                patch(
                    "wy_qcos.metrics.metrics_task.logger.error",
                    mock_logger_error,
                ),
            ):
                from wy_qcos.metrics.metrics_task import (
                    update_metrics_task_async,
                )

                await update_metrics_task_async()

                mock_update_job_metrics.assert_called_once()
                assert mock_logger_error.call_count == 2

        asyncio.run(_run())


class TestIntegration:
    """Integration tests for metrics task functions."""

    @pytest.mark.smoke
    def test_full_workflow_with_realistic_data(self):
        """Test full workflow with realistic job data."""
        realistic_jobs = [
            {"job_status": Constant.JOB_STATUS_COMPLETED},
            {"job_status": Constant.JOB_STATUS_RUNNING},
            {"job_status": Constant.JOB_STATUS_QUEUED},
            {"job_status": Constant.JOB_STATUS_FAILED},
            {"job_status": Constant.JOB_STATUS_COMPLETED},
        ]

        mock_scheduler = AsyncMock()
        mock_scheduler.aget_jobs = AsyncMock(
            return_value=(realistic_jobs, None)
        )
        mock_job_metrics_data = MagicMock()
        mock_update_job_metrics = MagicMock()

        async def _run():
            with (
                patch("wy_qcos.task_manager.scheduler", mock_scheduler),
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.job_metrics.JobMetricsData",
                    return_value=mock_job_metrics_data,
                ) as mock_data_class,
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.update_job_metrics",
                    mock_update_job_metrics,
                ),
            ):
                from wy_qcos.metrics.metrics_task import (
                    update_metrics_task_async,
                )

                await update_metrics_task_async()

                mock_data_class.assert_called_once_with(
                    total=5,
                    success=2,
                    failed=1,
                    running=1,
                    queued=1,
                    cancelling=0,
                    cancelled=0,
                    unknown=0,
                )
                mock_update_job_metrics.assert_called_once_with(
                    data=mock_job_metrics_data
                )

        asyncio.run(_run())

    @pytest.mark.smoke
    def test_concurrent_calls(self):
        """Test that concurrent calls don't cause issues."""
        mock_jobs = [
            {"job_status": Constant.JOB_STATUS_COMPLETED},
            {"job_status": Constant.JOB_STATUS_RUNNING},
        ]

        mock_scheduler = AsyncMock()
        mock_scheduler.aget_jobs = AsyncMock(return_value=(mock_jobs, None))
        mock_job_metrics_data = MagicMock()
        mock_update_job_metrics = MagicMock()

        async def _run():
            with (
                patch("wy_qcos.task_manager.scheduler", mock_scheduler),
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.job_metrics.JobMetricsData",
                    return_value=mock_job_metrics_data,
                ),
                patch(
                    "wy_qcos.metrics.metrics_task.metrics_collector.update_job_metrics",
                    mock_update_job_metrics,
                ),
            ):
                from wy_qcos.metrics.metrics_task import update_job_metrics

                tasks = [update_job_metrics() for _ in range(3)]
                await asyncio.gather(*tasks)

                assert mock_scheduler.aget_jobs.call_count == 3
                assert mock_update_job_metrics.call_count == 3

        asyncio.run(_run())
