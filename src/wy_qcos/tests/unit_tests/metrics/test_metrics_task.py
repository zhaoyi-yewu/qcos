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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prefect.client.schemas.objects import WorkerStatus

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.metrics import metrics_collector, metrics_task
from wy_qcos.metrics.metrics_task import (
    call_sync_with_timeout,
    check_fastapi_health,
    check_prefect_health,
    check_redis_health,
    check_worker_health,
    clear_redis_client,
    get_redis_client,
    require_sync_client,
    update_job_metrics,
    update_metrics_task_async,
    update_system_health_metrics,
)


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestRedisClient:
    """Redis client management tests."""

    @pytest.mark.smoke
    def test_singleton(self):
        mock_redis = AsyncMock()
        with patch.object(
            metrics_task.async_redis, "Redis", return_value=mock_redis
        ):
            with patch.object(metrics_task, "_redis_client", None):
                c1 = run_async(get_redis_client())
                c2 = run_async(get_redis_client())
                assert c1 is c2

    def test_clear(self):
        mock_redis = AsyncMock()
        metrics_task._redis_client = mock_redis
        run_async(clear_redis_client())
        assert metrics_task._redis_client is None
        mock_redis.aclose.assert_called_once()

    def test_clear_error(self):
        mock_redis = AsyncMock()
        mock_redis.aclose.side_effect = Exception("Error")
        metrics_task._redis_client = mock_redis
        run_async(clear_redis_client())
        assert metrics_task._redis_client is None


class TestCallSyncWithTimeout:
    """Sync call with timeout tests."""

    @pytest.mark.smoke
    def test_success(self):
        result = run_async(
            call_sync_with_timeout(lambda x, y: x + y, timeout=1.0, x=5, y=3)
        )
        assert result == 8

    @pytest.mark.slow
    def test_timeout(self):
        def slow():
            import time

            time.sleep(5)

        with pytest.raises(TimeoutError):
            run_async(call_sync_with_timeout(slow, timeout=0.1))

    def test_exception(self):
        def fail():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            run_async(call_sync_with_timeout(fail, timeout=1.0))


class TestRequireSyncClient:
    """Decorator tests."""

    @pytest.mark.smoke
    def test_success(self):
        mock_tm = MagicMock()
        mock_tm._sync_client = MagicMock()

        @require_sync_client
        async def func(sync_client=None):
            return sync_client is not None

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            assert run_async(func()) is True

    def test_not_initialized(self):
        @require_sync_client
        async def func(sync_client=None):
            return True

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = None
            result = run_async(func())
            assert result[0] is False


class TestUpdateJobMetrics:
    """Job metrics update tests."""

    @pytest.mark.smoke
    def test_success(self):
        responses = [
            {"job_status": s}
            for s in [
                Constant.JOB_STATUS_COMPLETED,
                Constant.JOB_STATUS_COMPLETED,
                Constant.JOB_STATUS_FAILED,
                Constant.JOB_STATUS_RUNNING,
                Constant.JOB_STATUS_QUEUED,
                Constant.JOB_STATUS_CANCELLING,
                Constant.JOB_STATUS_CANCELLED,
                Constant.JOB_STATUS_DELETING,
                Constant.JOB_STATUS_DELETED,
                Constant.JOB_STATUS_UNKNOWN,
            ]
        ]

        # Mock job repository
        mock_job_repo = MagicMock()
        mock_job_repo.count.return_value = 10
        mock_job_repo.count_by_attr.side_effect = [
            2,  # completed
            1,  # failed
            1,  # running
            1,  # queued
            1,  # cancelling
            1,  # cancelled
            1,  # deleting
            1,  # deleted
            1,  # unknown
        ]
        mock_job_repo.count_recent.side_effect = [3, 2]
        mock_session = MagicMock()

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.aget_jobs = AsyncMock(return_value=(responses, None))
            with patch.object(metrics_collector, "update_job_metrics") as mu:
                with patch(
                    "wy_qcos.metrics.metrics_task.get_job_repo",
                    return_value=(mock_job_repo, mock_session),
                ):
                    run_async(update_job_metrics())
                    data = mu.call_args.kwargs["data"]
                    assert data.total == 10
                    assert data.completed == 2
                    assert data.deleting == 1
                    assert data.submitted_job_rate_min == 3.0
                    assert data.completed_job_rate_min == 2.0
                    assert mock_job_repo.count_recent.call_count == 2

    def test_empty(self):
        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.aget_jobs = AsyncMock(return_value=([], None))
            with patch.object(metrics_collector, "update_job_metrics") as mu:
                run_async(update_job_metrics())
                mu.assert_not_called()

    def test_exception(self):
        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.aget_jobs = AsyncMock(side_effect=Exception("Error"))
            with patch.object(metrics_collector, "update_job_metrics") as mu:
                run_async(update_job_metrics())
                mu.assert_not_called()


class TestCheckWorkerHealth:
    """Worker health check tests."""

    @pytest.mark.smoke
    def test_healthy(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()
        mock_dm = MagicMock()

        worker = MagicMock()
        worker.status = WorkerStatus.ONLINE
        mock_sc.read_workers_for_work_pool.return_value = [worker]
        mock_tm._sync_client = mock_sc
        mock_dm.get_devices.return_value = {"d1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            ms.get_device_manager.return_value = mock_dm
            healthy, msg = run_async(check_worker_health())
            assert healthy and msg == ""

    @pytest.mark.smoke
    def test_not_initialized(self):
        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = None
            healthy, msg = run_async(check_worker_health())
            assert not healthy and "not initialized" in msg

    def test_no_devices(self):
        mock_tm = MagicMock()
        mock_tm._sync_client = MagicMock()
        mock_dm = MagicMock()
        mock_dm.get_devices.return_value = {}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            ms.device_manager = mock_dm
            healthy, msg = run_async(check_worker_health())
            assert not healthy and "No devices" in msg

    def test_no_workers(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()
        mock_dm = MagicMock()

        mock_sc.read_workers_for_work_pool.return_value = []
        mock_tm._sync_client = mock_sc
        mock_dm.get_devices.return_value = {"d1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            ms.get_device_manager.return_value = mock_dm
            healthy, msg = run_async(check_worker_health())
            assert not healthy and "no_workers" in msg

    def test_offline(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()
        mock_dm = MagicMock()

        worker = MagicMock()
        worker.status = WorkerStatus.OFFLINE
        mock_sc.read_workers_for_work_pool.return_value = [worker]
        mock_tm._sync_client = mock_sc
        mock_dm.get_devices.return_value = {"d1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            ms.get_device_manager.return_value = mock_dm
            healthy, msg = run_async(check_worker_health())
            assert not healthy and "no_online" in msg

    def test_timeout_after_retry(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()
        mock_dm = MagicMock()

        def timeout_func(*args, **kwargs):
            raise TimeoutError("Timeout")

        mock_sc.read_workers_for_work_pool = timeout_func
        mock_tm._sync_client = mock_sc
        mock_dm.get_devices.return_value = {"d1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            ms.get_device_manager.return_value = mock_dm
            healthy, msg = run_async(check_worker_health())
            assert not healthy and "timeout" in msg

    @pytest.mark.slow
    def test_retry_succeeds(self):
        """Test that timeout on first attempt is tolerated with retry."""
        mock_tm = MagicMock()
        mock_sc = MagicMock()
        mock_dm = MagicMock()

        call_count = 0

        def flaky_func(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Transient timeout")
            worker = MagicMock()
            worker.status = WorkerStatus.ONLINE
            return [worker]

        mock_sc.read_workers_for_work_pool = flaky_func
        mock_tm._sync_client = mock_sc
        mock_dm.get_devices.return_value = {"d1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            ms.get_device_manager.return_value = mock_dm
            healthy, msg = run_async(check_worker_health())
            assert healthy and msg == ""

    def test_error(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()
        mock_dm = MagicMock()

        mock_sc.read_workers_for_work_pool.side_effect = Exception(
            "Conn error"
        )
        mock_tm._sync_client = mock_sc
        mock_dm.get_devices.return_value = {"d1": {}}

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            ms.get_device_manager.return_value = mock_dm
            healthy, msg = run_async(check_worker_health())
            assert not healthy and "error:" in msg


class TestCheckPrefectHealth:
    """Prefect health check tests."""

    @pytest.mark.smoke
    def test_healthy(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()

        resp = MagicMock()
        resp.status_code = HttpCode.SUCCESS_OK
        mock_sc.hello.return_value = resp
        mock_tm._sync_client = mock_sc

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            healthy, msg = run_async(check_prefect_health())
            assert healthy and msg == ""

    @pytest.mark.smoke
    def test_no_client(self):
        mock_tm = MagicMock()
        mock_tm._sync_client = None

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            healthy, msg = run_async(check_prefect_health())
            assert not healthy and "not initialized" in msg

    def test_unhealthy(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()

        resp = MagicMock()
        resp.status_code = HttpCode.INTERNAL_SERVER_ERROR
        mock_sc.hello.return_value = resp
        mock_tm._sync_client = mock_sc

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            healthy, msg = run_async(check_prefect_health())
            assert not healthy and "status code" in msg

    def test_timeout(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()

        def timeout_func(*args, **kwargs):
            raise TimeoutError("Timeout")

        mock_sc.hello = timeout_func
        mock_tm._sync_client = mock_sc

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            healthy, msg = run_async(check_prefect_health())
            assert not healthy and "timed out" in msg

    def test_error(self):
        mock_tm = MagicMock()
        mock_sc = MagicMock()

        def error_func(*args, **kwargs):
            raise Exception("Failed")

        mock_sc.hello = error_func
        mock_tm._sync_client = mock_sc

        with patch("wy_qcos.metrics.metrics_task.scheduler") as ms:
            ms.get_task_manager.return_value = mock_tm
            healthy, msg = run_async(check_prefect_health())
            assert not healthy and "connection failed" in msg


class TestCheckFastapiHealth:
    """FastAPI health check tests."""

    @pytest.mark.smoke
    def test_healthy(self):
        healthy, msg = run_async(check_fastapi_health())
        assert healthy and msg == ""


class TestCheckRedisHealth:
    """Redis health check tests."""

    @pytest.mark.smoke
    def test_healthy(self):
        mock_rc = AsyncMock()
        mock_rc.ping = AsyncMock(return_value=True)

        with patch("wy_qcos.metrics.metrics_task.async_redis") as mar:
            mar.Redis.return_value = mock_rc
            with patch("wy_qcos.metrics.metrics_task._redis_client", None):
                healthy, msg = run_async(check_redis_health())
                run_async(clear_redis_client())
                assert healthy and msg == ""

    def test_timeout(self):
        mock_rc = AsyncMock()
        mock_rc.ping = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("wy_qcos.metrics.metrics_task.async_redis") as mar:
            mar.Redis.return_value = mock_rc
            with patch("wy_qcos.metrics.metrics_task._redis_client", None):
                healthy, msg = run_async(check_redis_health())
                run_async(clear_redis_client())
                assert not healthy and "timed out" in msg

    def test_error(self):
        mock_rc = AsyncMock()
        mock_rc.ping = AsyncMock(side_effect=Exception("Refused"))

        with patch("wy_qcos.metrics.metrics_task.async_redis") as mar:
            mar.Redis.return_value = mock_rc
            with patch("wy_qcos.metrics.metrics_task._redis_client", None):
                healthy, msg = run_async(check_redis_health())
                run_async(clear_redis_client())
                assert not healthy and "failed" in msg


class TestUpdateSystemHealth:
    """System health metrics tests."""

    @pytest.mark.smoke
    def test_all_healthy(self):
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
                        ) as mu:
                            run_async(update_system_health_metrics())
                            data = mu.call_args.args[0]
                            assert all([
                                data.worker_healthy,
                                data.prefect_healthy,
                                data.fastapi_healthy,
                                data.redis_healthy,
                            ])

    def test_some_unhealthy(self):
        with patch(
            "wy_qcos.metrics.metrics_task.check_worker_health",
            return_value=(False, "Err"),
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
                        return_value=(False, "Err"),
                    ):
                        with patch.object(
                            metrics_collector, "update_system_health"
                        ) as mu:
                            run_async(update_system_health_metrics())
                            data = mu.call_args.args[0]
                            assert (
                                not data.worker_healthy
                                and not data.redis_healthy
                            )

    def test_exception(self):
        with patch(
            "wy_qcos.metrics.metrics_task.check_worker_health",
            side_effect=Exception("Err"),
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
                        ) as mu:
                            run_async(update_system_health_metrics())
                            data = mu.call_args.args[0]
                            assert not data.worker_healthy


class TestUpdateMetricsTaskAsync:
    """Main metrics task tests."""

    @pytest.mark.smoke
    def test_success(self):
        with patch("wy_qcos.metrics.metrics_task.update_job_metrics") as mj:
            with patch(
                "wy_qcos.metrics.metrics_task.update_system_health_metrics"
            ) as mh:
                run_async(update_metrics_task_async())
                mj.assert_called_once()
                mh.assert_called_once()

    def test_job_error(self):
        with patch(
            "wy_qcos.metrics.metrics_task.update_job_metrics",
            side_effect=Exception("Err"),
        ):
            with patch(
                "wy_qcos.metrics.metrics_task.update_system_health_metrics"
            ) as mh:
                run_async(update_metrics_task_async())
                mh.assert_called_once()

    @pytest.mark.slow
    def test_health_error(self):
        with patch("wy_qcos.metrics.metrics_task.update_job_metrics"):
            with patch(
                "wy_qcos.metrics.metrics_task.update_system_health_metrics",
                side_effect=Exception("Err"),
            ):
                run_async(update_metrics_task_async())

    @pytest.mark.slow
    def test_timeout(self):
        async def slow():
            await asyncio.sleep(15)

        with patch(
            "wy_qcos.metrics.metrics_task.update_job_metrics",
            side_effect=slow,
        ):
            with patch(
                "wy_qcos.metrics.metrics_task.update_system_health_metrics",
                side_effect=slow,
            ):
                run_async(update_metrics_task_async())

    def test_system_health_timeout_only(self):
        async def slow():
            await asyncio.sleep(16)

        with patch("wy_qcos.metrics.metrics_task.update_job_metrics"):
            with patch(
                "wy_qcos.metrics.metrics_task.update_system_health_metrics",
                side_effect=slow,
            ):
                run_async(update_metrics_task_async())
