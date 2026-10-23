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

"""Unit tests for device_availability_task module."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from wy_qcos.metrics.device_availability_task import (
    _get_db_engine,
    aggregate_availability_hourly,
    aggregate_availability_hourly_sync,
    set_app,
)


class TestSetApp:
    """Test set_app function."""

    def test_set_app_stores_app(self):
        """Test set_app stores the app instance globally."""
        mock_app = MagicMock()
        with patch(
            "wy_qcos.metrics.device_availability_task.logger"
        ) as mock_logger:
            set_app(mock_app)
            mock_logger.debug.assert_called_once()
        # Verify _app is set (indirectly via _get_db_engine)
        assert _get_db_engine() is not None

    def test_get_db_engine_no_app(self):
        """Test _get_db_engine returns None when no app set."""
        # Reset global _app
        import wy_qcos.metrics.device_availability_task as task_module

        original_app = task_module._app
        task_module._app = None
        assert _get_db_engine() is None
        task_module._app = original_app


class TestAggregateAvailabilityHourlySync:
    """Test aggregate_availability_hourly_sync function."""

    def test_no_samples_skips(self):
        """Test aggregation skips when no samples in collector."""
        with patch(
            "wy_qcos.metrics.device_availability_task.DeviceAvailabilityCollector"
        ) as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.snapshot_and_reset.return_value = {}
            mock_collector_class.return_value = mock_collector

            with patch(
                "wy_qcos.metrics.device_availability_task.logger"
            ) as mock_logger:
                aggregate_availability_hourly_sync()
                mock_logger.debug.assert_called_once()

    def test_no_db_engine_logs_error(self):
        """Test aggregation logs error when db engine not available."""
        with patch(
            "wy_qcos.metrics.device_availability_task.DeviceAvailabilityCollector"
        ) as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.snapshot_and_reset.return_value = {
                "dev1": MagicMock(online_count=1, total_count=2)
            }
            mock_collector_class.return_value = mock_collector

            with patch(
                "wy_qcos.metrics.device_availability_task._get_db_engine"
            ) as mock_get_engine:
                mock_get_engine.return_value = None

                with patch(
                    "wy_qcos.metrics.device_availability_task.logger"
                ) as mock_logger:
                    aggregate_availability_hourly_sync()
                    mock_logger.error.assert_called_once()

    def test_upsert_success(self):
        """Test successful aggregation and upsert."""
        with patch(
            "wy_qcos.metrics.device_availability_task.DeviceAvailabilityCollector"
        ) as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.snapshot_and_reset.return_value = {
                "dev1": MagicMock(online_count=1, total_count=2)
            }
            mock_collector_class.return_value = mock_collector

            mock_engine = MagicMock()
            with patch(
                "wy_qcos.metrics.device_availability_task._get_db_engine"
            ) as mock_get_engine:
                mock_get_engine.return_value = mock_engine

                with patch(
                    "wy_qcos.metrics.device_availability_task.Session"
                ) as mock_session_class:
                    mock_session = MagicMock()
                    mock_session_class.return_value = mock_session

                    with patch(
                        "wy_qcos.metrics.device_availability_task.DeviceAvailabilityRepository"
                    ) as mock_repo_class:
                        mock_repo = MagicMock()
                        mock_repo.upsert_hourly.return_value = (True, None)
                        mock_repo_class.return_value = mock_repo

                        with patch(
                            "wy_qcos.metrics.device_availability_task.logger"
                        ) as mock_logger:
                            aggregate_availability_hourly_sync()
                            mock_logger.info.assert_called_once()

    def test_upsert_failure_logs_error(self):
        """Test aggregation logs error when upsert fails."""
        with patch(
            "wy_qcos.metrics.device_availability_task.DeviceAvailabilityCollector"
        ) as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.snapshot_and_reset.return_value = {
                "dev1": MagicMock(online_count=1, total_count=2)
            }
            mock_collector_class.return_value = mock_collector

            mock_engine = MagicMock()
            with patch(
                "wy_qcos.metrics.device_availability_task._get_db_engine"
            ) as mock_get_engine:
                mock_get_engine.return_value = mock_engine

                with patch(
                    "wy_qcos.metrics.device_availability_task.Session"
                ) as mock_session_class:
                    mock_session = MagicMock()
                    mock_session_class.return_value = mock_session

                    with patch(
                        "wy_qcos.metrics.device_availability_task.DeviceAvailabilityRepository"
                    ) as mock_repo_class:
                        mock_repo = MagicMock()
                        mock_repo.upsert_hourly.return_value = (
                            False,
                            "DB error",
                        )
                        mock_repo_class.return_value = mock_repo

                        with patch(
                            "wy_qcos.metrics.device_availability_task.logger"
                        ) as mock_logger:
                            aggregate_availability_hourly_sync()
                            mock_logger.error.assert_called_once()


class TestAggregateAvailabilityHourlyAsync:
    """Test aggregate_availability_hourly async function."""

    @pytest.mark.asyncio
    async def test_async_wrapper_calls_sync(self):
        """Test async wrapper calls sync version in executor."""
        with patch(
            "wy_qcos.metrics.device_availability_task.aggregate_availability_hourly_sync"
        ) as mock_sync:
            mock_sync.return_value = None

            # Get the running loop and patch run_in_executor
            loop = asyncio.get_event_loop()
            with patch.object(loop, "run_in_executor") as mock_executor:
                mock_executor.return_value = asyncio.Future()
                mock_executor.return_value.set_result(None)

                await aggregate_availability_hourly()
                mock_executor.assert_called_once()
