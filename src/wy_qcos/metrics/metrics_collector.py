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

import bisect
import logging
import threading
from datetime import (
    datetime,
    timedelta,
)

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)


class JobMetrics:
    """for job_metrics management."""

    class JobMetricsData:
        """job metrics data."""

        __slots__ = (
            "total",
            "success",
            "failed",
            "running",
            "queued",
            "cancelling",
            "cancelled",
            "deleted",
            "unknown",
        )

        def __init__(
            self,
            total: int = 0,
            success: int = 0,
            failed: int = 0,
            running: int = 0,
            queued: int = 0,
            cancelling: int = 0,
            cancelled: int = 0,
            deleted: int = 0,
            unknown: int = 0,
        ):
            self.total = total
            self.success = success
            self.failed = failed
            self.running = running
            self.queued = queued
            self.cancelling = cancelling
            self.cancelled = cancelled
            self.deleted = deleted
            self.unknown = unknown

        def __repr__(self):
            return (
                f"JobMetricsData(total={self.total}, success={self.success}, "
                f"failed={self.failed}, running={self.running})"
            )

    def __init__(self):
        #  Prometheus metrics for job metrics
        self.job_total = Gauge("jobs_total", "Total number of jobs")
        self.job_completed_total = Gauge(
            "jobs_completed_total", "Total number of completed jobs"
        )
        self.job_failed_total = Gauge(
            "jobs_failed_total", "Total number of failed jobs"
        )
        self.job_running = Gauge(
            "jobs_running", "Number of currently running jobs"
        )
        self.job_queued = Gauge("jobs_queued", "Number of queued jobs")
        self.job_cancelling = Gauge(
            "jobs_cancelling", "Number of cancelling jobs"
        )
        self.job_cancelled = Gauge(
            "jobs_cancelled", "Number of cancelled jobs"
        )
        self.job_deleted = Gauge("jobs_deleted", "Number of deleted jobs")
        self.job_unknown = Gauge("jobs_unknown", "Number of unknown jobs")

        # Lock to ensure atomicity of update operations
        self._lock = threading.Lock()

    def update(self, data: JobMetricsData):
        """Update Prometheus metrics."""
        with self._lock:
            self.job_total.set(data.total)
            self.job_completed_total.set(data.success)
            self.job_failed_total.set(data.failed)
            self.job_running.set(data.running)
            self.job_queued.set(data.queued)
            self.job_cancelling.set(data.cancelling)
            self.job_cancelled.set(data.cancelled)
            self.job_deleted.set(data.deleted)
            self.job_unknown.set(data.unknown)

        logger.debug(f"Job metrics updated: {data}")


class APIMetrics:
    """API metrics."""

    class APIMetricsData:
        """API metrics data."""

        __slots__ = (
            "module",
            "method",
            "endpoint",
            "status_code",
            "duration",
        )

        def __init__(
            self,
            module: str,
            method: str,
            endpoint: str,
            status_code: int,
            duration: float,
        ):
            self.module = module
            self.method = method
            self.endpoint = endpoint
            self.status_code = status_code
            self.duration = duration

    def __init__(self) -> None:
        self.api_requests_total = Counter(
            "api_requests_total",
            "Total API requests",
            ["module", "method", "endpoint", "status_code"],
        )
        self.api_requests_in_progress = Gauge(
            "api_requests_in_progress",
            "API requests currently being processed",
        )
        self.api_request_duration = Histogram(
            "api_request_duration_seconds",
            "API request duration in seconds",
            ["module", "method", "endpoint"],
            buckets=(
                0.001,
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
            ),
        )

        # Time-windowed API statistics
        self._api_stats_lock = threading.Lock()
        self._api_request_timestamps: list[datetime] = []

    def record_api_request(self, data: APIMetricsData):
        """Record an API request.

        Args:
            data (APIMetricsData): API request data
            {
                module: Module name
                method: HTTP method
                endpoint: API endpoint
                status_code: HTTP status code
                duration: Request duration in seconds
            }
        """
        self.api_requests_total.labels(
            module=data.module,
            method=data.method,
            endpoint=data.endpoint,
            status_code=data.status_code,
        ).inc()

        self.api_request_duration.labels(
            module=data.module, method=data.method, endpoint=data.endpoint
        ).observe(data.duration)

        # Record timestamp for time-windowed statistics
        with self._api_stats_lock:
            current_time = datetime.now()
            self._api_request_timestamps.append(current_time)

            # Clean up old timestamps (keep last 24 hours)
            cutoff = current_time - timedelta(hours=24)
            idx = bisect.bisect_left(self._api_request_timestamps, cutoff)
            self._api_request_timestamps = self._api_request_timestamps[idx:]

    def increment_api_requests_in_progress(self):
        """Increment the counter of in-progress API requests."""
        self.api_requests_in_progress.inc()

    def decrement_api_requests_in_progress(self):
        """Decrement the counter of in-progress API requests."""
        self.api_requests_in_progress.dec()

    def get_api_stats(self) -> dict[str, int]:
        """Get API statistics for different time windows.

        Returns:
            Dictionary containing:
            - total_requests: Total API requests
            - last_hour_requests: Requests in the last hour
            - last_day_requests: Requests in the last day
        """
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(hours=24)

        with self._api_stats_lock:
            idx_hour = bisect.bisect_right(
                self._api_request_timestamps, one_hour_ago
            )
            idx_day = bisect.bisect_right(
                self._api_request_timestamps, one_day_ago
            )

            last_hour_count = len(self._api_request_timestamps) - idx_hour
            last_day_count = len(self._api_request_timestamps) - idx_day

        # Get total from counter
        total_counter = self.api_requests_total._metrics
        total_requests = sum(
            metric.value() for metric in total_counter.values()
        )

        return {
            "total_requests": total_requests,
            "last_hour_requests": last_hour_count,
            "last_day_requests": last_day_count,
        }


class MetricsCollector:
    """Singleton class for collecting and exposing Prometheus metrics."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Global lock for thread-safe operations across all metrics
        self._global_lock = threading.Lock()

        # System health metrics
        self.system_online = Gauge(
            "system_online", "System online status (1=online, 0=offline)"
        )
        # job metrics
        self.job_metrics = JobMetrics()

        # API access metrics
        self.api_metrics = APIMetrics()

        # Initialize system as offline
        self.set_system_online(False)

        logger.info("MetricsCollector initialized")

    def set_system_online(self, online: bool):
        """Set system online status.

        Args:
            online: True if system is online, False otherwise
        """
        with self._global_lock:
            self.system_online.set(1 if online else 0)
        logger.debug(f"System online status set to: {online}")

    def update_job_metrics(self, data: JobMetrics.JobMetricsData):
        """Update job-related metrics.

        Args:
            data: JobMetrics.JobMetricsData
            {
                job_id: Job ID
                job_status: Job status
                job_priority: Job priority
                job_duration: Job duration in seconds
                job_start_time: Job start time
                job_end_time: Job end time
            }
        """
        self.job_metrics.update(data)

    def record_api_request(self, data: APIMetrics.APIMetricsData):
        """Record an API request.

        Args:
            data: APIMetrics.APIMetricsData
            {
                module: Module name
                method: HTTP method
                endpoint: API endpoint
                status_code: HTTP status code
                duration: Request duration in seconds
            }
        """
        self.api_metrics.record_api_request(data)
        logger.debug(
            f"API request recorded: {data.method} \
             {data.endpoint} {data.status_code} {data.duration:.3f}s"
        )

    def record_api_requests_in_progress(self, is_increment: bool):
        """Record the counter of in-progress API requests."""
        with self._global_lock:
            if is_increment:
                self.api_metrics.increment_api_requests_in_progress()
            else:
                self.api_metrics.decrement_api_requests_in_progress()

    def get_metrics(self) -> bytes:
        """Generate Prometheus metrics output.

        Returns:
            Prometheus metrics in text format
        """
        with self._global_lock:
            return generate_latest()

    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics.

        Returns:
            Content type string
        """
        return CONTENT_TYPE_LATEST
