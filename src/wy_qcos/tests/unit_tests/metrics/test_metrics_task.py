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
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest
from prefect.client.schemas.objects import WorkerStatus

from wy_qcos.common.constant import (
    Constant,
    HttpCode,
)
from wy_qcos.metrics import metrics_collector
from wy_qcos.metrics.metrics_task import (
    check_fastapi_health,
    check_prefect_health,
    check_redis_health,
    check_worker_health,
    update_job_metrics,
    update_metrics_task_async,
    update_system_health_metrics,
)


def run_async(coro):
    """Helper function to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestUpdateJobMetrics:
    """Test cases for update_job_metrics function."""

    def test_update_job_metrics_success(self):
        """Test update_job_metrics with various job statuses."""
        mock_responses = [
            {"job_status": Constant.JOB_STATUS_COMPLETED},
            {"job_status": Constant.JOB_STATUS_COMPLETED},
            {"job_status": Constant.JOB_STATUS_FAILED},
            {"job_status": Constant.JOB_STATUS_RUNNING},
            {"job_status": Constant.JOB_STATUS_UNKNOWN},
        ]

        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.aget_jobs = AsyncMock(
                return_value=(mock_responses, None)
            )

            with patch.object(
                metrics_collector, "update_job_metrics"
            ) as mock_update:
                run_async(update_job_metrics())

                assert mock_update.called
                data = mock_update.call_args.kwargs["data"]

                assert data.total == 5
                assert data.completed == 2
                assert data.failed == 1
                assert data.running == 1
                assert data.unknown == 1

    def test_update_job_metrics_empty_response(self):
        """Test update_job_metrics with empty or None responses."""
        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.aget_jobs = AsyncMock(return_value=([], None))

            with patch.object(
                metrics_collector, "update_job_metrics"
            ) as mock_update:
                run_async(update_job_metrics())
                mock_update.assert_not_called()

    def test_update_job_metrics_exception(self):
        """Test update_job_metrics when scheduler raises exception."""
        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.aget_jobs = AsyncMock(
                side_effect=Exception("Scheduler error")
            )

            with pytest.raises(Exception, match="Scheduler error"):
                run_async(update_job_metrics())


class TestCheckWorkerHealth:
    """Test cases for check_worker_health function."""

    @pytest.mark.smoke
    def test_check_worker_health_healthy(self):
        """Test check_worker_health when all workers are healthy."""
        mock_task_manager = MagicMock()
        mock_sync_client = MagicMock()
        mock_device_manager = MagicMock()

        mock_worker = MagicMock()
        mock_worker.status = WorkerStatus.ONLINE
        mock_sync_client.read_workers_for_work_pool.return_value = [
            mock_worker
        ]
        mock_task_manager._sync_client = mock_sync_client
        mock_device_manager.get_devices.return_value = {"device1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.get_task_manager.return_value = mock_task_manager
            mock_scheduler.device_manager = mock_device_manager

            is_healthy, error_msg = run_async(check_worker_health())

            assert is_healthy is True
            assert error_msg == ""

    @pytest.mark.smoke
    def test_check_worker_health_not_initialized(self):
        """Test check_worker_health when not initialized."""
        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.get_task_manager.return_value = None

            is_healthy, error_msg = run_async(check_worker_health())

            assert is_healthy is False
            assert "Task manager or sync client not initialized" in error_msg

    def test_check_worker_health_unhealthy(self):
        """Test check_worker_health when workers are unhealthy."""
        mock_task_manager = MagicMock()
        mock_sync_client = MagicMock()
        mock_device_manager = MagicMock()

        mock_worker = MagicMock()
        mock_worker.status = WorkerStatus.OFFLINE
        mock_sync_client.read_workers_for_work_pool.return_value = [
            mock_worker
        ]
        mock_task_manager._sync_client = mock_sync_client
        mock_device_manager.get_devices.return_value = {"device1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.get_task_manager.return_value = mock_task_manager
            mock_scheduler.device_manager = mock_device_manager

            is_healthy, error_msg = run_async(check_worker_health())

            assert is_healthy is False
            assert "No online workers" in error_msg

    def test_check_worker_health_exception(self):
        """Test check_worker_health when exception occurs."""
        mock_task_manager = MagicMock()
        mock_sync_client = MagicMock()
        mock_device_manager = MagicMock()

        mock_sync_client.read_workers_for_work_pool.side_effect = Exception(
            "Connection error"
        )
        mock_task_manager._sync_client = mock_sync_client
        mock_device_manager.get_devices.return_value = {"device1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.get_task_manager.return_value = mock_task_manager
            mock_scheduler.device_manager = mock_device_manager

            is_healthy, error_msg = run_async(check_worker_health())

            assert is_healthy is False
            assert "Error checking workers" in error_msg


class TestCheckPrefectHealth:
    """Test cases for check_prefect_health function."""

    @pytest.mark.smoke
    def test_check_prefect_health_healthy(self):
        """Test check_prefect_health when Prefect is healthy."""
        mock_task_manager = MagicMock()
        mock_sync_client = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = HttpCode.SUCCESS_OK
        mock_sync_client.hello.return_value = mock_response
        mock_task_manager._sync_client = mock_sync_client

        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.get_task_manager.return_value = mock_task_manager

            is_healthy, error_msg = run_async(check_prefect_health())

            assert is_healthy is True
            assert error_msg == ""

    def test_check_prefect_health_unhealthy(self):
        """Test check_prefect_health when Prefect is unhealthy."""
        mock_task_manager = MagicMock()
        mock_sync_client = MagicMock()

        mock_response = MagicMock()
        mock_response.status_code = HttpCode.INTERNAL_SERVER_ERROR
        mock_sync_client.hello.return_value = mock_response
        mock_task_manager._sync_client = mock_sync_client

        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.get_task_manager.return_value = mock_task_manager

            is_healthy, error_msg = run_async(check_prefect_health())

            assert is_healthy is False
            assert "Prefect API returned status code" in error_msg

    def test_check_prefect_health_exception(self):
        """Test check_prefect_health when exception occurs."""
        mock_task_manager = MagicMock()
        mock_sync_client = MagicMock()
        mock_sync_client.hello.side_effect = Exception("Connection failed")
        mock_task_manager._sync_client = mock_sync_client

        with patch("wy_qcos.metrics.metrics_task.scheduler") as mock_scheduler:
            mock_scheduler.get_task_manager.return_value = mock_task_manager

            is_healthy, error_msg = run_async(check_prefect_health())

            assert is_healthy is False
            assert "Prefect API connection failed" in error_msg


class TestCheckFastapiHealth:
    """Test cases for check_fastapi_health function."""

    @pytest.mark.smoke
    def test_check_fastapi_health(self):
        """Test check_fastapi_health always returns healthy."""
        is_healthy, error_msg = run_async(check_fastapi_health())

        assert is_healthy is True
        assert error_msg == ""


class TestCheckRedisHealth:
    """Test cases for check_redis_health function."""

    @pytest.mark.smoke
    def test_check_redis_health_healthy(self):
        """Test check_redis_health when Redis is healthy."""
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis_client.aclose = AsyncMock()

        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis_client

            is_healthy, error_msg = run_async(check_redis_health())

            assert is_healthy is True
            assert error_msg == ""

    def test_check_redis_health_unhealthy(self):
        """Test check_redis_health when Redis ping fails."""
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        mock_redis_client.aclose = AsyncMock()

        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_class.return_value = mock_redis_client

            is_healthy, error_msg = run_async(check_redis_health())

            assert is_healthy is False
            assert "Redis ping failed" in error_msg


class TestUpdateSystemHealthMetrics:
    """Test cases for update_system_health_metrics function."""

    @pytest.mark.smoke
    def test_update_system_health_metrics_all_healthy(self):
        """Test update_system_health_metrics when all components healthy."""
        with patch(
            "wy_qcos.metrics.metrics_task.check_worker_health",
            return_value=(True, ""),
        ):
            with patch(
                "wy_qcos.metrics.metrics_task.check_prefect_health",
                return_value=(True, ""),
            ):
                with patch(
                    "wy_qcos.metrics.metrics_task.check_fastapi_health",
                    return_value=(True, ""),
                ):
                    with patch(
                        "wy_qcos.metrics.metrics_task.check_redis_health",
                        return_value=(True, ""),
                    ):
                        with patch.object(
                            metrics_collector, "update_system_health"
                        ) as mock_update:
                            run_async(update_system_health_metrics())

                            assert mock_update.called
                            data = mock_update.call_args.args[0]

                            assert data.overall_healthy is True
                            assert data.heartbeat_timestamp > 0

    def test_update_system_health_metrics_unhealthy(self):
        """Test update_system_health_metrics when some components unhealthy."""
        with patch(
            "wy_qcos.metrics.metrics_task.check_worker_health",
            return_value=(False, "Worker error"),
        ):
            with patch(
                "wy_qcos.metrics.metrics_task.check_prefect_health",
                return_value=(True, ""),
            ):
                with patch(
                    "wy_qcos.metrics.metrics_task.check_fastapi_health",
                    return_value=(True, ""),
                ):
                    with patch(
                        "wy_qcos.metrics.metrics_task.check_redis_health",
                        return_value=(False, "Redis error"),
                    ):
                        with patch.object(
                            metrics_collector, "update_system_health"
                        ) as mock_update:
                            run_async(update_system_health_metrics())

                            data = mock_update.call_args.args[0]
                            assert data.overall_healthy is False
                            assert data.worker_healthy is False
                            assert data.redis_healthy is False

    def test_update_system_health_metrics_exception(self):
        """Test update_system_health_metrics handles exceptions gracefully."""
        with patch(
            "wy_qcos.metrics.metrics_task.check_worker_health",
            side_effect=Exception("Unexpected error"),
        ):
            with patch.object(
                metrics_collector, "update_system_health"
            ) as mock_update:
                run_async(update_system_health_metrics())
                mock_update.assert_not_called()


class TestUpdateMetricsTaskAsync:
    """Test cases for update_metrics_task_async function."""

    @pytest.mark.smoke
    def test_update_metrics_task_async_success(self):
        """Test update_metrics_task_async executes successfully."""
        with patch(
            "wy_qcos.metrics.metrics_task.update_job_metrics"
        ) as mock_job:
            with patch(
                "wy_qcos.metrics.metrics_task.update_system_health_metrics"
            ) as mock_health:
                run_async(update_metrics_task_async())

                mock_job.assert_called_once()
                mock_health.assert_called_once()

    def test_update_metrics_task_async_error(self):
        """Test update_metrics_task_async handles errors."""
        with patch(
            "wy_qcos.metrics.metrics_task.update_job_metrics",
            side_effect=Exception("Job metrics error"),
        ):
            with patch(
                "wy_qcos.metrics.metrics_task.update_system_health_metrics"
            ) as mock_health:
                run_async(update_metrics_task_async())
                mock_health.assert_not_called()
