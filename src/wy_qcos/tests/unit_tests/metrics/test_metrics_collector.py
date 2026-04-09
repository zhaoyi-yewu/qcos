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

import threading
from datetime import (
    datetime,
    timedelta,
)
from unittest.mock import (
    Mock,
    patch,
)

import pytest
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

from wy_qcos.metrics.metrics_collector import (
    APIMetrics,
    JobMetrics,
    MetricsCollector,
)


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    """Reset the global Prometheus registry and singleton before each test."""
    # Unregister all collectors
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
    # Reset MetricsCollector singleton
    MetricsCollector._instance = None
    yield
    # Cleanup after test
    MetricsCollector._instance = None
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)


# ---------- JobMetrics 测试 ----------
class TestJobMetrics:
    @pytest.mark.smoke
    def test_init(self):
        job_metrics = JobMetrics()
        assert hasattr(job_metrics, "_lock")
        assert isinstance(job_metrics._lock, type(threading.Lock()))
        assert job_metrics.job_total is not None
        assert job_metrics.job_completed_total is not None
        assert job_metrics.job_failed_total is not None
        assert job_metrics.job_running is not None
        assert job_metrics.job_queued is not None
        assert job_metrics.job_cancelling is not None
        assert job_metrics.job_cancelled is not None
        assert job_metrics.job_deleted is not None
        assert job_metrics.job_unknown is not None

    @pytest.mark.smoke
    def test_update(self):
        job_metrics = JobMetrics()
        # mock all Gauge objects
        for attr in [
            "job_total",
            "job_completed_total",
            "job_failed_total",
            "job_running",
            "job_queued",
            "job_cancelling",
            "job_cancelled",
            "job_deleted",
            "job_unknown",
        ]:
            setattr(job_metrics, attr, Mock())

        data = JobMetrics.JobMetricsData(
            total=10,
            success=5,
            failed=2,
            running=3,
            queued=1,
            cancelling=0,
            cancelled=0,
            deleted=0,
            unknown=0,
        )
        job_metrics.update(data)

        job_metrics.job_total.set.assert_called_once_with(10)
        job_metrics.job_completed_total.set.assert_called_once_with(5)
        job_metrics.job_failed_total.set.assert_called_once_with(2)
        job_metrics.job_running.set.assert_called_once_with(3)
        job_metrics.job_queued.set.assert_called_once_with(1)
        job_metrics.job_cancelling.set.assert_called_once_with(0)
        job_metrics.job_cancelled.set.assert_called_once_with(0)
        job_metrics.job_deleted.set.assert_called_once_with(0)
        job_metrics.job_unknown.set.assert_called_once_with(0)


class TestAPIMetrics:
    @pytest.mark.smoke
    def test_init(self):
        api_metrics = APIMetrics()
        assert hasattr(api_metrics, "_api_stats_lock")
        assert isinstance(api_metrics._api_stats_lock, type(threading.Lock()))
        assert api_metrics._api_request_timestamps == []
        assert api_metrics.api_requests_total is not None
        assert api_metrics.api_requests_in_progress is not None
        assert api_metrics.api_request_duration is not None

    @pytest.mark.smoke
    def test_record_api_request(self):
        api_metrics = APIMetrics()
        # mock to avoid actual Prometheus calls
        api_metrics.api_requests_total = Mock()
        api_metrics.api_request_duration = Mock()
        mock_counter = Mock()
        api_metrics.api_requests_total.labels.return_value = mock_counter
        mock_histogram = Mock()
        api_metrics.api_request_duration.labels.return_value = mock_histogram

        data = APIMetrics.APIMetricsData(
            module="test_module",
            method="GET",
            endpoint="/api/test",
            status_code=200,
            duration=0.5,
        )

        with patch(
            "wy_qcos.metrics.metrics_collector.datetime"
        ) as mock_datetime:
            now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = now
            api_metrics.record_api_request(data)

        api_metrics.api_requests_total.labels.assert_called_once_with(
            module="test_module",
            method="GET",
            endpoint="/api/test",
            status_code=200,
        )
        mock_counter.inc.assert_called_once()
        api_metrics.api_request_duration.labels.assert_called_once_with(
            module="test_module", method="GET", endpoint="/api/test"
        )
        mock_histogram.observe.assert_called_once_with(0.5)
        assert len(api_metrics._api_request_timestamps) == 1
        assert api_metrics._api_request_timestamps[0] == now

    @pytest.mark.smoke
    def test_record_api_request_cleanup_old_timestamps(self):
        api_metrics = APIMetrics()
        api_metrics.api_requests_total = Mock()
        api_metrics.api_request_duration = Mock()
        api_metrics.api_requests_total.labels.return_value = Mock()
        api_metrics.api_request_duration.labels.return_value = Mock()

        now = datetime(2026, 4, 7, 12, 0, 0)
        old_time = now - timedelta(hours=25)
        recent_time = now - timedelta(hours=1)

        with patch(
            "wy_qcos.metrics.metrics_collector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = now
            api_metrics._api_request_timestamps = [old_time, recent_time]
            data = APIMetrics.APIMetricsData(
                module="test",
                method="GET",
                endpoint="/test",
                status_code=200,
                duration=0.1,
            )
            api_metrics.record_api_request(data)

        assert len(api_metrics._api_request_timestamps) == 2
        assert api_metrics._api_request_timestamps[0] == recent_time
        assert api_metrics._api_request_timestamps[1] == now

    @pytest.mark.smoke
    def test_increment_decrement_api_requests_in_progress(self):
        api_metrics = APIMetrics()
        api_metrics.api_requests_in_progress = Mock()
        api_metrics.increment_api_requests_in_progress()
        api_metrics.api_requests_in_progress.inc.assert_called_once()
        api_metrics.decrement_api_requests_in_progress()
        api_metrics.api_requests_in_progress.dec.assert_called_once()

    @pytest.mark.smoke
    def test_get_api_stats_empty(self):
        api_metrics = APIMetrics()
        api_metrics._api_request_timestamps = []
        api_metrics.api_requests_total = Mock()
        api_metrics.api_requests_total._metrics = {}
        with patch(
            "wy_qcos.metrics.metrics_collector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
            stats = api_metrics.get_api_stats()
        assert stats["total_requests"] == 0
        assert stats["last_hour_requests"] == 0
        assert stats["last_day_requests"] == 0

    @pytest.mark.smoke
    def test_get_api_stats_with_data(self):
        api_metrics = APIMetrics()
        now = datetime(2024, 1, 1, 12, 0, 0)

        timestamps = [
            now - timedelta(hours=48),  # outside last day
            now
            - timedelta(hours=24)
            + timedelta(seconds=1),  # inside last day (boundary+1s)
            now - timedelta(hours=2) + timedelta(seconds=1),  # inside last day
            now
            - timedelta(hours=1)
            + timedelta(seconds=30),  # inside last hour
        ]
        api_metrics._api_request_timestamps = timestamps

        mock_metric1 = Mock()
        mock_metric1.value.return_value = 10
        mock_metric2 = Mock()
        mock_metric2.value.return_value = 20
        api_metrics.api_requests_total = Mock()
        api_metrics.api_requests_total._metrics = {
            "a": mock_metric1,
            "b": mock_metric2,
        }

        with patch(
            "wy_qcos.metrics.metrics_collector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = now
            stats = api_metrics.get_api_stats()
        print(stats)
        assert stats["total_requests"] == 30
        assert stats["last_hour_requests"] == 1  # first timestamp
        assert stats["last_day_requests"] == 3  # first three timestamps

    @pytest.mark.smoke
    def test_get_api_stats_bisect_boundaries(self):
        api_metrics = APIMetrics()
        now = datetime(2024, 1, 1, 12, 0, 0)
        # Use timestamps that are slightly after the cutoff to be included
        one_hour_ago = now - timedelta(hours=1) + timedelta(seconds=1)
        one_day_ago = now - timedelta(hours=24) + timedelta(seconds=1)
        api_metrics._api_request_timestamps = [one_day_ago, one_hour_ago]
        api_metrics.api_requests_total = Mock()
        api_metrics.api_requests_total._metrics = {}

        with patch(
            "wy_qcos.metrics.metrics_collector.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = now
            stats = api_metrics.get_api_stats()

        assert stats["last_hour_requests"] == 1
        assert stats["last_day_requests"] == 2


class TestMetricsCollector:
    @pytest.mark.smoke
    def test_singleton(self):
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        assert collector1 is collector2
        assert collector1._initialized is True

    @pytest.mark.smoke
    def test_init(self):
        collector = MetricsCollector()
        assert collector._initialized is True
        assert hasattr(collector, "_global_lock")
        assert hasattr(collector._global_lock, "acquire")
        # system_online initial value should be 0
        assert collector.system_online._value.get() == 0

    @pytest.mark.smoke
    def test_set_system_online(self):
        collector = MetricsCollector()
        collector.set_system_online(True)
        assert collector.system_online._value.get() == 1
        collector.set_system_online(False)
        assert collector.system_online._value.get() == 0

    @pytest.mark.smoke
    def test_update_job_metrics(self):
        collector = MetricsCollector()
        collector.job_metrics = Mock()
        data = JobMetrics.JobMetricsData(total=5)
        collector.update_job_metrics(data)
        collector.job_metrics.update.assert_called_once_with(data)

    @pytest.mark.smoke
    def test_record_api_request(self):
        collector = MetricsCollector()
        collector.api_metrics = Mock()
        data = APIMetrics.APIMetricsData(
            module="mod",
            method="POST",
            endpoint="/api",
            status_code=201,
            duration=0.2,
        )
        collector.record_api_request(data)
        collector.api_metrics.record_api_request.assert_called_once_with(data)

    @pytest.mark.smoke
    def test_record_api_requests_in_progress(self):
        collector = MetricsCollector()
        collector.api_metrics = Mock()
        collector.record_api_requests_in_progress(True)
        collector.api_metrics.increment_api_requests_in_progress.assert_called_once()
        collector.record_api_requests_in_progress(False)
        collector.api_metrics.decrement_api_requests_in_progress.assert_called_once()

    @pytest.mark.smoke
    @patch("wy_qcos.metrics.metrics_collector.generate_latest")
    def test_get_metrics(self, mock_generate):
        mock_generate.return_value = b"metrics data"
        collector = MetricsCollector()
        result = collector.get_metrics()
        assert result == b"metrics data"
        mock_generate.assert_called_once()

    @pytest.mark.smoke
    def test_get_content_type(self):
        collector = MetricsCollector()
        assert collector.get_content_type() == CONTENT_TYPE_LATEST

    @pytest.mark.smoke
    def test_initialized_only_once(self):
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        assert collector1 is collector2
        assert MetricsCollector._instance is collector1

    @pytest.mark.smoke
    def test_concurrent_record_api_requests_in_progress(self):
        collector = MetricsCollector()
        collector.api_metrics.api_requests_in_progress = Mock()

        def worker():
            for _ in range(100):
                collector.record_api_requests_in_progress(True)
                collector.record_api_requests_in_progress(False)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert (
            collector.api_metrics.api_requests_in_progress.inc.call_count
            == 500
        )
        assert (
            collector.api_metrics.api_requests_in_progress.dec.call_count
            == 500
        )


def test_job_metrics_data_repr():
    data = JobMetrics.JobMetricsData(total=10, success=3, failed=1, running=2)
    repr_str = repr(data)
    assert "JobMetricsData" in repr_str
    assert "total=10" in repr_str


def test_api_metrics_data_creation():
    data = APIMetrics.APIMetricsData(
        module="m", method="GET", endpoint="/e", status_code=200, duration=0.1
    )
    assert data.module == "m"
    assert data.method == "GET"
    assert data.endpoint == "/e"
    assert data.status_code == 200
    assert data.duration == 0.1
