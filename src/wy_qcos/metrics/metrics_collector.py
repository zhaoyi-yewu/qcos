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
            "completed",
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
            completed: int = 0,
            failed: int = 0,
            running: int = 0,
            queued: int = 0,
            cancelling: int = 0,
            cancelled: int = 0,
            deleted: int = 0,
            unknown: int = 0,
        ):
            self.total = total
            self.completed = completed
            self.failed = failed
            self.running = running
            self.queued = queued
            self.cancelling = cancelling
            self.cancelled = cancelled
            self.deleted = deleted
            self.unknown = unknown

        def __repr__(self):
            return (
                f"JobMetricsData(total={self.total}, "
                f"completed={self.completed}, "
                f"failed={self.failed}, "
                f"running={self.running}, "
                f"queued={self.queued}, "
                f"cancelled={self.cancelled}, "
                f"deleted={self.deleted}, "
                f"unknown={self.unknown})"
            )

    def __init__(self) -> None:
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

        # Internal tracking of current values for quick access
        self._current_values = self.JobMetricsData()

    def update(self, data: JobMetricsData):
        """Update Prometheus metrics."""
        with self._lock:
            self._current_values = data

            self.job_total.set(data.total)
            self.job_completed_total.set(data.completed)
            self.job_failed_total.set(data.failed)
            self.job_running.set(data.running)
            self.job_queued.set(data.queued)
            self.job_cancelling.set(data.cancelling)
            self.job_cancelled.set(data.cancelled)
            self.job_deleted.set(data.deleted)
            self.job_unknown.set(data.unknown)

        logger.debug(f"Job metrics updated: {data}")

    def get_values(self) -> JobMetricsData:
        """Get current values of all job metrics.

        This method returns the internally tracked values, which is faster
        than collecting from Prometheus metrics.

        Returns:
            JobMetricsData object with current metric values
        """
        with self._lock:
            return self._current_values


class SystemHealthMetrics:
    """System health metrics."""

    class SystemHealthMetricsData:
        """System health metrics data."""

        __slots__ = (
            "overall_healthy",
            "heartbeat_timestamp",
            "worker_healthy",
            "prefect_healthy",
            "fastapi_healthy",
            "redis_healthy",
        )

        def __init__(
            self,
            heartbeat_timestamp: int = 0,
            worker_healthy: bool = False,
            prefect_healthy: bool = False,
            fastapi_healthy: bool = False,
            redis_healthy: bool = False,
        ) -> None:
            self.heartbeat_timestamp = heartbeat_timestamp or 0
            self.worker_healthy = worker_healthy
            self.prefect_healthy = prefect_healthy
            self.fastapi_healthy = fastapi_healthy
            self.redis_healthy = redis_healthy
            self.overall_healthy = all([
                self.worker_healthy,
                self.prefect_healthy,
                self.fastapi_healthy,
                self.redis_healthy,
            ])

        def __repr__(self):
            return (
                f"SystemHealthMetricsData( "
                f"heartbeat_timestamp={self.heartbeat_timestamp}, "
                f"worker_healthy={self.worker_healthy}, "
                f"prefect_healthy={self.prefect_healthy}, "
                f"fastapi_healthy={self.fastapi_healthy},  "
                f"redis_healthy={self.redis_healthy})"
            )

    def __init__(self) -> None:
        self.system_online = Gauge(
            "system_online", "System online status (1=online, 0=offline)"
        )
        self.heartbeat_timestamp_gauge = Gauge(
            "system_heartbeat_timestamp",
            "System heartbeat timestamp (Unix timestamp)",
        )
        self.component_health_gauge = Gauge(
            "component_health_status",
            "Component health status (1=healthy, 0=unhealthy)",
            ["component"],
        )

        # Lock to ensure atomicity of update operations
        self._lock = threading.Lock()

        self._current_values = self.SystemHealthMetricsData()

    def update(self, data: SystemHealthMetricsData):
        """Update system health metrics.

        Args:
            data: SystemHealthMetricsData object with system health status
        """
        with self._lock:
            self._current_values = data
            self.system_online.set(1 if data.overall_healthy else 0)
            self.heartbeat_timestamp_gauge.set(data.heartbeat_timestamp)

            # Update component metrics
            self.component_health_gauge.labels(component="worker").set(
                1 if data.worker_healthy else 0
            )
            self.component_health_gauge.labels(component="prefect").set(
                1 if data.prefect_healthy else 0
            )
            self.component_health_gauge.labels(component="fastapi").set(
                1 if data.fastapi_healthy else 0
            )
            self.component_health_gauge.labels(component="redis").set(
                1 if data.redis_healthy else 0
            )

        logger.debug(f"System health metrics updated: {data}")

    def get_values(self) -> SystemHealthMetricsData:
        """Get current system health status.

        This method returns the internally tracked values, which is faster
        than collecting from Prometheus metrics.

        Returns:
            SystemHealthMetricsData object with current health status
        """
        with self._lock:
            return self._current_values


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
        ) -> None:
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

        # Internal tracking for quick access to total requests
        self._total_requests_count = 0

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
            self._total_requests_count += 1
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
            total_requests = self._total_requests_count

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

        # job metrics
        self.job_metrics = JobMetrics()

        # API access metrics
        self.api_metrics = APIMetrics()

        # System health metrics
        self.system_health_metrics = SystemHealthMetrics()

        logger.info("MetricsCollector initialized")

    def update_job_metrics(self, data: JobMetrics.JobMetricsData):
        """Update job-related metrics.

        Args:
            data: JobMetrics.JobMetricsData
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

    def update_system_health(
        self, data: SystemHealthMetrics.SystemHealthMetricsData
    ):
        """Update system health metrics.

        Args:
            data: SystemHealthMetrics.SystemHealthMetricsData
            {
                heartbeat_timestamp: Timestamp of the last heartbeat
                workers_healthy: Whether all workers are healthy
                prefect_healthy: Whether Prefect is healthy
                fastapi_healthy: Whether FastAPI is healthy
                redis_healthy: Whether Redis is healthy
            }

        """
        self.system_health_metrics.update(data)

    def get_system_health_status(
        self,
    ) -> SystemHealthMetrics.SystemHealthMetricsData:
        """Get system health status.

        Returns:
            System health status
        """
        return self.system_health_metrics.get_values()

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
