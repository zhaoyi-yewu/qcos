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

import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from prometheus_client import REGISTRY

from wy_qcos.metrics.metrics_collector import (
    APIMetrics,
    JobMetrics,
    MetricsCollector,
    SystemHealthMetrics,
)


def clear_prometheus_registry():
    """Clear all collectors from the default Prometheus registry."""
    collectors = list(REGISTRY._names_to_collectors.values())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass


class TestJobMetricsData(unittest.TestCase):
    """Test cases for JobMetricsData class."""

    @pytest.mark.smoke
    def test_job_metrics_data_creation(self):
        """Test JobMetricsData creation with default values."""
        data = JobMetrics.JobMetricsData()

        assert data.total == 0
        assert data.completed == 0
        assert data.failed == 0
        assert data.running == 0
        assert data.queued == 0
        assert data.cancelling == 0
        assert data.cancelled == 0
        assert data.deleted == 0
        assert data.unknown == 0

    def test_job_metrics_data_with_values(self):
        """Test JobMetricsData creation with custom values."""
        data = JobMetrics.JobMetricsData(
            total=10,
            completed=5,
            failed=2,
            running=1,
            queued=1,
            cancelling=0,
            cancelled=1,
            deleted=0,
            unknown=0,
        )

        assert data.total == 10
        assert data.completed == 5
        assert data.failed == 2
        assert data.running == 1

    def test_job_metrics_data_attributes(self):
        """Test JobMetricsData attributes are correctly set."""
        data = JobMetrics.JobMetricsData(total=5, completed=3, failed=1)

        assert "total=5" in str(data)
        assert "completed=3" in str(data)
        assert "failed=1" in str(data)


class TestJobMetrics(unittest.TestCase):
    """Test cases for JobMetrics class."""

    def setUp(self):
        """Set up test fixtures."""
        clear_prometheus_registry()
        self.job_metrics = JobMetrics()

    def tearDown(self):
        """Clean up after each test."""
        clear_prometheus_registry()

    @pytest.mark.smoke
    def test_update_job_metrics(self):
        """Test updating job metrics."""
        data = JobMetrics.JobMetricsData(
            total=10, completed=5, failed=2, running=1
        )

        self.job_metrics.update(data)

        values = self.job_metrics.get_values()
        assert values.total == 10
        assert values.completed == 5
        assert values.failed == 2
        assert values.running == 1

    def test_get_job_metrics_values(self):
        """Test getting current job metrics values."""
        data = JobMetrics.JobMetricsData(total=7, queued=3)
        self.job_metrics.update(data)

        values = self.job_metrics.get_values()
        assert values.total == 7
        assert values.queued == 3

    def test_update_multiple_times(self):
        """Test updating job metrics multiple times."""
        data1 = JobMetrics.JobMetricsData(total=5, completed=2)
        data2 = JobMetrics.JobMetricsData(total=10, completed=6)

        self.job_metrics.update(data1)
        self.job_metrics.update(data2)

        values = self.job_metrics.get_values()
        assert values.total == 10
        assert values.completed == 6


class TestSystemHealthMetricsData(unittest.TestCase):
    """Test cases for SystemHealthMetricsData class."""

    @pytest.mark.smoke
    def test_system_health_data_all_healthy(self):
        """Test SystemHealthMetricsData when all components healthy."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            heartbeat_timestamp=1234567890,
            worker_healthy=True,
            prefect_healthy=True,
            fastapi_healthy=True,
            redis_healthy=True,
        )

        assert data.overall_healthy is True
        assert data.heartbeat_timestamp == 1234567890
        assert data.worker_healthy is True

    def test_system_health_data_some_unhealthy(self):
        """Test SystemHealthMetricsData when some components unhealthy."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            worker_healthy=False,
            prefect_healthy=True,
            fastapi_healthy=True,
            redis_healthy=False,
        )

        assert data.overall_healthy is False
        assert data.worker_healthy is False
        assert data.redis_healthy is False

    def test_system_health_data_default_values(self):
        """Test SystemHealthMetricsData with default values."""
        data = SystemHealthMetrics.SystemHealthMetricsData()

        assert data.overall_healthy is False
        assert data.heartbeat_timestamp == 0
        assert data.worker_healthy is False

    def test_system_health_data_repr(self):
        """Test SystemHealthMetricsData __repr__ method."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            heartbeat_timestamp=100, worker_healthy=True
        )
        repr_str = str(data)

        assert "heartbeat_timestamp=100" in repr_str
        assert "worker_healthy=True" in repr_str


class TestSystemHealthMetrics(unittest.TestCase):
    """Test cases for SystemHealthMetrics class."""

    def setUp(self):
        """Set up test fixtures."""
        clear_prometheus_registry()
        self.health_metrics = SystemHealthMetrics()

    def tearDown(self):
        """Clean up after each test."""
        clear_prometheus_registry()

    @pytest.mark.smoke
    def test_update_health_metrics_all_healthy(self):
        """Test updating health metrics when all healthy."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            heartbeat_timestamp=int(time.time()),
            worker_healthy=True,
            prefect_healthy=True,
            fastapi_healthy=True,
            redis_healthy=True,
        )

        self.health_metrics.update(data)

        values = self.health_metrics.get_values()
        assert values.overall_healthy is True

    def test_update_health_metrics_unhealthy(self):
        """Test updating health metrics when unhealthy."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            worker_healthy=False,
            prefect_healthy=True,
            fastapi_healthy=True,
            redis_healthy=True,
        )

        self.health_metrics.update(data)

        values = self.health_metrics.get_values()
        assert values.overall_healthy is False
        assert values.worker_healthy is False

    def test_get_health_values(self):
        """Test getting current health values."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            heartbeat_timestamp=999, worker_healthy=True
        )
        self.health_metrics.update(data)

        values = self.health_metrics.get_values()
        assert values.heartbeat_timestamp == 999


class TestAPIMetricsData(unittest.TestCase):
    """Test cases for APIMetricsData class."""

    @pytest.mark.smoke
    def test_api_metrics_data_creation(self):
        """Test APIMetricsData creation."""
        data = APIMetrics.APIMetricsData(
            module="test_module",
            method="GET",
            endpoint="/api/test",
            status_code=200,
            duration=0.5,
        )

        assert data.module == "test_module"
        assert data.method == "GET"
        assert data.endpoint == "/api/test"
        assert data.status_code == 200
        assert data.duration == 0.5


class TestAPIMetrics(unittest.TestCase):
    """Test cases for APIMetrics class."""

    def setUp(self):
        """Set up test fixtures."""
        clear_prometheus_registry()
        self.api_metrics = APIMetrics()

    def tearDown(self):
        """Clean up after each test."""
        clear_prometheus_registry()

    @pytest.mark.smoke
    def test_record_api_request(self):
        """Test recording an API request."""
        data = APIMetrics.APIMetricsData(
            module="test",
            method="GET",
            endpoint="/test",
            status_code=200,
            duration=0.1,
        )

        self.api_metrics.record_api_request(data)

        stats = self.api_metrics.get_api_stats()
        assert stats["total_requests"] >= 1

    def test_increment_decrement_in_progress(self):
        """Test incrementing and decrementing in-progress requests."""
        self.api_metrics.increment_api_requests_in_progress()
        self.api_metrics.increment_api_requests_in_progress()
        self.api_metrics.decrement_api_requests_in_progress()

        assert True

    def test_get_api_stats(self):
        """Test getting API statistics."""
        data = APIMetrics.APIMetricsData(
            module="test",
            method="POST",
            endpoint="/api",
            status_code=201,
            duration=0.2,
        )

        self.api_metrics.record_api_request(data)

        stats = self.api_metrics.get_api_stats()

        assert "total_requests" in stats
        assert "last_hour_requests" in stats
        assert "last_day_requests" in stats
        assert stats["total_requests"] >= 1

    def test_api_request_gauge_updated(self):
        """Test that api_request gauge is updated with correct values."""
        from prometheus_client import generate_latest

        data = APIMetrics.APIMetricsData(
            module="test",
            method="GET",
            endpoint="/gauge",
            status_code=200,
            duration=0.05,
        )
        self.api_metrics.record_api_request(data)

        stats = self.api_metrics.get_api_stats()

        # The gauge should have been updated in both record_api_request
        # and get_api_stats, so generate_latest should reflect the
        # current values.
        output = generate_latest().decode("utf-8")
        for gauge_type, expected_value in [
            ("total_requests", stats["total_requests"]),
            ("last_hour_requests", stats["last_hour_requests"]),
            ("last_day_requests", stats["last_day_requests"]),
        ]:
            expected_line = (
                f'api_request{{type="{gauge_type}"}} {expected_value}'
            )
            assert expected_line in output, (
                f"Expected '{expected_line}' in metrics output, "
                f"but not found. Output:\n{output}"
            )

    @pytest.mark.slow
    def test_api_stats_time_windows(self):
        """Test API statistics time window calculations."""
        now = datetime.now()

        with patch.object(
            self.api_metrics,
            "_api_request_timestamps",
            [
                now - timedelta(hours=2),
                now - timedelta(minutes=30),
                now - timedelta(minutes=10),
            ],
        ):
            self.api_metrics._total_requests_count = 3

            stats = self.api_metrics.get_api_stats()

            assert stats["last_hour_requests"] == 2
            assert stats["last_day_requests"] == 3


class TestMetricsCollector(unittest.TestCase):
    """Test cases for MetricsCollector singleton class."""

    def setUp(self):
        """Set up test fixtures."""
        clear_prometheus_registry()
        MetricsCollector._instance = None
        self.collector = MetricsCollector()

    def tearDown(self):
        """Clean up after each test."""
        clear_prometheus_registry()
        MetricsCollector._instance = None

    @pytest.mark.smoke
    def test_singleton_pattern(self):
        """Test that MetricsCollector follows singleton pattern."""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        assert collector1 is collector2

    @pytest.mark.smoke
    def test_update_job_metrics_via_collector(self):
        """Test updating job metrics via collector."""
        data = JobMetrics.JobMetricsData(total=15, completed=10)

        self.collector.update_job_metrics(data)

        values = self.collector.job_metrics.get_values()
        assert values.total == 15
        assert values.completed == 10

    def test_record_api_request_via_collector(self):
        """Test recording API request via collector."""
        data = APIMetrics.APIMetricsData(
            module="job",
            method="POST",
            endpoint="/api/v1/jobs",
            status_code=201,
            duration=0.3,
        )

        self.collector.record_api_request(data)

        stats = self.collector.api_metrics.get_api_stats()
        assert stats["total_requests"] >= 1

    def test_record_api_requests_in_progress(self):
        """Test recording in-progress API requests."""
        self.collector.record_api_requests_in_progress(is_increment=True)
        self.collector.record_api_requests_in_progress(is_increment=True)
        self.collector.record_api_requests_in_progress(is_increment=False)

        assert True

    @pytest.mark.smoke
    def test_update_system_health_via_collector(self):
        """Test updating system health via collector."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            heartbeat_timestamp=int(time.time()),
            worker_healthy=True,
            prefect_healthy=True,
            fastapi_healthy=True,
            redis_healthy=True,
        )

        self.collector.update_system_health(data)

        health_status = self.collector.get_system_health_status()
        assert health_status.overall_healthy is True

    def test_get_system_health_status(self):
        """Test getting system health status."""
        data = SystemHealthMetrics.SystemHealthMetricsData(
            worker_healthy=False,
            prefect_healthy=True,
            fastapi_healthy=True,
            redis_healthy=True,
        )

        self.collector.update_system_health(data)

        health_status = self.collector.get_system_health_status()
        assert health_status.overall_healthy is False
        assert health_status.worker_healthy is False

    def test_get_metrics(self):
        """Test getting Prometheus metrics output."""
        metrics_output = self.collector.get_metrics()

        assert isinstance(metrics_output, bytes)
        assert len(metrics_output) > 0

    def test_get_content_type(self):
        """Test getting content type for metrics."""
        content_type = self.collector.get_content_type()

        assert isinstance(content_type, str)
        assert (
            "text/plain" in content_type
            or "application/openmetrics" in content_type
        )

    @pytest.mark.slow
    def test_multiple_updates(self):
        """Test multiple metric updates."""
        job_data = JobMetrics.JobMetricsData(total=20, completed=15)
        health_data = SystemHealthMetrics.SystemHealthMetricsData(
            worker_healthy=True,
            prefect_healthy=True,
            fastapi_healthy=True,
            redis_healthy=True,
        )
        api_data = APIMetrics.APIMetricsData(
            module="test",
            method="GET",
            endpoint="/test",
            status_code=200,
            duration=0.1,
        )

        self.collector.update_job_metrics(job_data)
        self.collector.update_system_health(health_data)
        self.collector.record_api_request(api_data)

        job_values = self.collector.job_metrics.get_values()
        health_values = self.collector.get_system_health_status()
        api_stats = self.collector.api_metrics.get_api_stats()

        assert job_values.total == 20
        assert health_values.overall_healthy is True
        assert api_stats["total_requests"] >= 1
