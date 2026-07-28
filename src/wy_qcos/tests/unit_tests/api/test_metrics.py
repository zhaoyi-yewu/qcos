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

from unittest.mock import Mock, patch

import pytest

from wy_qcos.api.posiq.routes_jsonrpc.metrics import (
    get_api_stats,
    get_job_stats,
    get_system_health,
)
from wy_qcos.api.schemas import (
    GetApiStatsResponse,
    GetJobStatsResponse,
    GetSystemHealthResponse,
)
from wy_qcos.common.constant import Constant


class MockSystemHealthMetrics:
    """Mock system health metrics data."""

    overall_healthy = True
    heartbeat_timestamp = 1715000000
    worker_healthy = True
    prefect_healthy = True
    fastapi_healthy = True
    redis_healthy = True


class MockJobMetricsData:
    """Mock job metrics data."""

    total = 100
    completed = 80
    failed = 10
    running = 5
    queued = 3
    cancelling = 1
    cancelled = 1
    deleting = 0
    deleted = 0
    unknown = 0
    submitted_job_rate_min = 2.5
    completed_job_rate_min = 1.0


class MockApiStats:
    """Mock API statistics."""

    total_requests = 1000
    last_hour_requests = 50
    last_day_requests = 500


class TestGetSystemHealth:
    """Test cases for get_system_health function."""

    @pytest.mark.smoke
    def test_get_system_health_all_healthy(self):
        """Test system health response when all components are healthy."""
        mock_health = MockSystemHealthMetrics()
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.system_health_metrics.get_values.return_value = (
                mock_health
            )

            mock_client = Mock()
            response = get_system_health(mock_client)

        assert isinstance(response, GetSystemHealthResponse)
        assert response.system_healthy is True
        assert response.heartbeat_timestamp == 1715000000
        assert response.component_status == {
            Constant.COMPONENT_NAME_FASTAPI: Constant.COMPONENT_STATUS_ONLINE,
            Constant.COMPONENT_NAME_REDIS: Constant.COMPONENT_STATUS_ONLINE,
            Constant.COMPONENT_NAME_PREFECT: Constant.COMPONENT_STATUS_ONLINE,
            Constant.COMPONENT_NAME_WORKER: Constant.COMPONENT_STATUS_ONLINE,
        }

    def test_get_system_health_some_unhealthy(self):
        """Test system health response when some components are unhealthy."""
        mock_health = Mock()
        mock_health.overall_healthy = False
        mock_health.heartbeat_timestamp = 1715000000
        mock_health.worker_healthy = False
        mock_health.prefect_healthy = True
        mock_health.fastapi_healthy = True
        mock_health.redis_healthy = False

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.system_health_metrics.get_values.return_value = (
                mock_health
            )

            mock_client = Mock()
            response = get_system_health(mock_client)

        assert isinstance(response, GetSystemHealthResponse)
        assert response.system_healthy is False
        assert response.component_status == {
            Constant.COMPONENT_NAME_FASTAPI: Constant.COMPONENT_STATUS_ONLINE,
            Constant.COMPONENT_NAME_REDIS: Constant.COMPONENT_STATUS_OFFLINE,
            Constant.COMPONENT_NAME_PREFECT: Constant.COMPONENT_STATUS_ONLINE,
            Constant.COMPONENT_NAME_WORKER: Constant.COMPONENT_STATUS_OFFLINE,
        }

    def test_get_system_health_all_unhealthy(self):
        """Test system health response when all components are unhealthy."""
        mock_health = Mock()
        mock_health.overall_healthy = False
        mock_health.heartbeat_timestamp = 0
        mock_health.worker_healthy = False
        mock_health.prefect_healthy = False
        mock_health.fastapi_healthy = False
        mock_health.redis_healthy = False

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.system_health_metrics.get_values.return_value = (
                mock_health
            )

            mock_client = Mock()
            response = get_system_health(mock_client)

        assert isinstance(response, GetSystemHealthResponse)
        assert response.system_healthy is False
        assert response.component_status == {
            Constant.COMPONENT_NAME_FASTAPI: Constant.COMPONENT_STATUS_OFFLINE,
            Constant.COMPONENT_NAME_REDIS: Constant.COMPONENT_STATUS_OFFLINE,
            Constant.COMPONENT_NAME_PREFECT: Constant.COMPONENT_STATUS_OFFLINE,
            Constant.COMPONENT_NAME_WORKER: Constant.COMPONENT_STATUS_OFFLINE,
        }

    def test_get_system_health_with_none_body(self):
        """Test system health response with None request body."""
        mock_health = MockSystemHealthMetrics()
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.system_health_metrics.get_values.return_value = (
                mock_health
            )

            response = get_system_health(None)

        assert isinstance(response, GetSystemHealthResponse)
        assert response.system_healthy is True


class TestGetApiStats:
    """Test cases for get_api_stats function."""

    @pytest.mark.smoke
    def test_get_api_stats(self):
        """Test API stats response."""
        mock_stats = MockApiStats()

        def mock_get_api_stats():
            return {
                Constant.API_TOTAL_REQUESTS: mock_stats.total_requests,
                Constant.API_LAST_HOUR_REQUESTS: mock_stats.last_hour_requests,
                Constant.API_LAST_DAY_REQUESTS: mock_stats.last_day_requests,
            }

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.api_metrics.get_api_stats = mock_get_api_stats

            mock_client = Mock()
            response = get_api_stats(mock_client)

        assert isinstance(response, GetApiStatsResponse)
        assert response.total_requests == 1000
        assert response.last_hour_requests == 50
        assert response.last_day_requests == 500

    def test_get_api_stats_zero_requests(self):
        """Test API stats response when there are zero requests."""

        def mock_get_api_stats():
            return {
                Constant.API_TOTAL_REQUESTS: 0,
                Constant.API_LAST_HOUR_REQUESTS: 0,
                Constant.API_LAST_DAY_REQUESTS: 0,
            }

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.api_metrics.get_api_stats = mock_get_api_stats

            mock_client = Mock()
            response = get_api_stats(mock_client)

        assert isinstance(response, GetApiStatsResponse)
        assert response.total_requests == 0
        assert response.last_hour_requests == 0
        assert response.last_day_requests == 0

    def test_get_api_stats_with_none_body(self):
        """Test API stats response with None request body."""
        mock_stats = MockApiStats()

        def mock_get_api_stats():
            return {
                Constant.API_TOTAL_REQUESTS: mock_stats.total_requests,
                Constant.API_LAST_HOUR_REQUESTS: mock_stats.last_hour_requests,
                Constant.API_LAST_DAY_REQUESTS: mock_stats.last_day_requests,
            }

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.api_metrics.get_api_stats = mock_get_api_stats

            response = get_api_stats(None)

        assert isinstance(response, GetApiStatsResponse)
        assert response.total_requests == 1000


class TestGetJobStats:
    """Test cases for get_job_stats function."""

    @pytest.mark.smoke
    def test_get_job_stats(self):
        """Test job stats response."""
        mock_job_data = MockJobMetricsData()
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.job_metrics.get_values.return_value = mock_job_data

            mock_client = Mock()
            response = get_job_stats(mock_client)

        assert isinstance(response, GetJobStatsResponse)
        assert response.total == 100
        assert response.completed == 80
        assert response.failed == 10
        assert response.running == 5
        assert response.queued == 3
        assert response.cancelling == 1
        assert response.cancelled == 1
        assert response.deleting == 0
        assert response.deleted == 0
        assert response.unknown == 0
        assert response.submitted_job_rate_min == 2.5
        assert response.completed_job_rate_min == 1.0

    def test_get_job_stats_empty_jobs(self):
        """Test job stats response when there are no jobs."""
        mock_job_data = Mock()
        mock_job_data.total = 0
        mock_job_data.completed = 0
        mock_job_data.failed = 0
        mock_job_data.running = 0
        mock_job_data.queued = 0
        mock_job_data.cancelling = 0
        mock_job_data.cancelled = 0
        mock_job_data.deleting = 0
        mock_job_data.deleted = 0
        mock_job_data.unknown = 0
        mock_job_data.submitted_job_rate_min = 0.0
        mock_job_data.completed_job_rate_min = 0.0

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.job_metrics.get_values.return_value = mock_job_data

            mock_client = Mock()
            response = get_job_stats(mock_client)

        assert isinstance(response, GetJobStatsResponse)
        assert response.total == 0
        assert response.completed == 0
        assert response.failed == 0

    def test_get_job_stats_all_completed(self):
        """Test job stats response when all jobs are completed."""
        mock_job_data = Mock()
        mock_job_data.total = 50
        mock_job_data.completed = 50
        mock_job_data.failed = 0
        mock_job_data.running = 0
        mock_job_data.queued = 0
        mock_job_data.cancelling = 0
        mock_job_data.cancelled = 0
        mock_job_data.deleting = 0
        mock_job_data.deleted = 0
        mock_job_data.unknown = 0
        mock_job_data.submitted_job_rate_min = 5.0
        mock_job_data.completed_job_rate_min = 3.0

        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.job_metrics.get_values.return_value = mock_job_data

            mock_client = Mock()
            response = get_job_stats(mock_client)

        assert isinstance(response, GetJobStatsResponse)
        assert response.total == 50
        assert response.completed == 50
        assert response.completed == response.total

    def test_get_job_stats_with_none_body(self):
        """Test job stats response with None request body."""
        mock_job_data = MockJobMetricsData()
        with patch(
            "wy_qcos.api.posiq.routes_jsonrpc.metrics.metrics_collector"
        ) as mock_collector:
            mock_collector.job_metrics.get_values.return_value = mock_job_data

            response = get_job_stats(None)

        assert isinstance(response, GetJobStatsResponse)
        assert response.total == 100
