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

"""Unit tests for fastapi_coroutine module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wy_qcos.api.fastapi_coroutine import (
    BackgroundServiceManager,
    StoppableService,
    app_lifespan,
)


class TestBackgroundServiceManager:
    """Test BackgroundServiceManager class."""

    def test_init(self):
        manager = BackgroundServiceManager()
        assert manager._services == []
        assert manager._tasks == []

    def test_add_service(self):
        manager = BackgroundServiceManager()
        service = MagicMock(spec=StoppableService)
        manager.add_service(service)
        assert len(manager._services) == 1
        assert manager._services[0] is service

    @pytest.mark.asyncio
    async def test_start_all_no_services(self):
        manager = BackgroundServiceManager()
        await manager.start_all()
        assert manager._tasks == []

    @pytest.mark.asyncio
    async def test_start_all(self):
        manager = BackgroundServiceManager()
        service1 = MagicMock(spec=StoppableService)
        service1.start = AsyncMock()
        service2 = MagicMock(spec=StoppableService)
        service2.start = AsyncMock()

        manager.add_service(service1)
        manager.add_service(service2)

        await manager.start_all()
        assert len(manager._tasks) == 2
        service1.start.assert_called_once()
        service2.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_all_no_services(self):
        manager = BackgroundServiceManager()
        await manager.stop_all()

    @pytest.mark.asyncio
    async def test_stop_all(self):
        manager = BackgroundServiceManager()
        service1 = MagicMock(spec=StoppableService)
        service1.start = AsyncMock()
        service1.stop = AsyncMock()
        service2 = MagicMock(spec=StoppableService)
        service2.start = AsyncMock()
        service2.stop = AsyncMock()

        manager.add_service(service1)
        manager.add_service(service2)

        await manager.start_all()
        await manager.stop_all()

        service1.stop.assert_called_once()
        service2.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_all_handles_exception(self):
        manager = BackgroundServiceManager()
        service = MagicMock(spec=StoppableService)
        service.start = AsyncMock()
        service.stop = AsyncMock(side_effect=Exception("stop error"))

        manager.add_service(service)
        await manager.start_all()
        # Should not raise
        await manager.stop_all()


class TestAppLifespan:
    """Test app_lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_yields(self):
        mock_app = MagicMock()

        with (
            patch("wy_qcos.api.fastapi_coroutine.set_app") as mock_set_app,
            patch(
                "wy_qcos.api.fastapi_coroutine.set_availability_app"
            ) as mock_set_avail,
            patch("wy_qcos.api.fastapi_coroutine.init_metrics"),
            patch(
                "wy_qcos.api.fastapi_coroutine.MetricsServer"
            ) as mock_metrics_server,
            patch(
                "wy_qcos.api.fastapi_coroutine.MetricsScheduler"
            ) as mock_metrics_sched,
            patch(
                "wy_qcos.api.fastapi_coroutine.DeviceAvailabilityCollector"
            ) as mock_collector,
            patch(
                "wy_qcos.api.fastapi_coroutine.DeviceAvailabilityScheduler"
            ) as mock_avail_sched,
            patch("wy_qcos.api.fastapi_coroutine.set_availability_collector"),
            patch(
                "wy_qcos.api.fastapi_coroutine.GcCleaner"
            ) as mock_gc_cleaner,
            patch(
                "wy_qcos.api.fastapi_coroutine.JobCleaner"
            ) as mock_job_cleaner,
            patch("wy_qcos.api.fastapi_coroutine.Config") as mock_config,
        ):
            # Setup config mocks
            mock_config.METRICS_SERVER.METRICS_SERVER_LISTEN_IP = "0.0.0.0"
            mock_config.METRICS_SERVER.METRICS_SERVER_LISTEN_PORT = 19400
            mock_config.DEFAULT.GC_INTERVAL = 1
            mock_config.DEFAULT.JOB_SCAN_INTERVAL = 60
            mock_config.DEFAULT.JOB_EXPIRE_DAYS = -1
            mock_config.DEFAULT.FLOW_EXPIRE_DAYS = 1

            # Setup service mocks
            mock_metrics_server_instance = MagicMock()
            mock_metrics_server_instance.start = AsyncMock()
            mock_metrics_server_instance.stop = AsyncMock()
            mock_metrics_server.return_value = mock_metrics_server_instance

            mock_metrics_sched_instance = MagicMock()
            mock_metrics_sched_instance.start = AsyncMock()
            mock_metrics_sched_instance.stop = AsyncMock()
            mock_metrics_sched.return_value = mock_metrics_sched_instance

            mock_collector_instance = MagicMock()
            mock_collector.return_value = mock_collector_instance

            mock_avail_sched_instance = MagicMock()
            mock_avail_sched_instance.start = AsyncMock()
            mock_avail_sched_instance.stop = AsyncMock()
            mock_avail_sched.return_value = mock_avail_sched_instance

            mock_gc_instance = MagicMock()
            mock_gc_instance.start = AsyncMock()
            mock_gc_instance.stop = AsyncMock()
            mock_gc_cleaner.return_value = mock_gc_instance

            mock_job_instance = MagicMock()
            mock_job_instance.start = AsyncMock()
            mock_job_instance.stop = AsyncMock()
            mock_job_cleaner.return_value = mock_job_instance

            async with app_lifespan(mock_app):
                pass

            mock_set_app.assert_called_once_with(mock_app)
            mock_set_avail.assert_called_once_with(mock_app)
