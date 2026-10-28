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

from pydantic import (
    BaseModel,
    Field,
)


class GetMetricsRequest(BaseModel):
    """Get metrics request."""

    pass


class GetMetricsResponse(BaseModel):
    """Get metrics response."""

    metrics: str = Field(..., description="Metrics data")
    pass


class GetSystemHealthRequest(BaseModel):
    """Get system health request."""

    pass


class GetSystemHealthResponse(BaseModel):
    """Get system health response."""

    system_healthy: bool = Field(
        ..., description="Overall system health status", examples=[True, False]
    )
    heartbeat_timestamp: float | None = Field(
        None, description="Last heartbeat timestamp", examples=[1234567890.123]
    )
    component_status: dict[str, str] = Field(
        ...,
        description="Status of individual system components",
        examples=[{"fastapi": "online", "redis": "online"}],
    )


class GetApiStatsRequest(BaseModel):
    """Get API statistics request."""

    pass


class GetApiStatsResponse(BaseModel):
    """Get API statistics response."""

    total_requests: int = Field(..., description="Total API requests")
    last_hour_requests: int = Field(
        ..., description="API requests in the last hour"
    )
    last_day_requests: int = Field(
        ..., description="API requests in the last day"
    )


class GetJobStatsRequest(BaseModel):
    """Get job statistics request."""

    pass


class GetJobStatsResponse(BaseModel):
    """Get job statistics response."""

    total: int = Field(..., description="Total number of jobs")
    completed: int = Field(..., description="Number of completed jobs")
    failed: int = Field(..., description="Number of failed jobs")
    running: int = Field(..., description="Number of running jobs")
    queued: int = Field(..., description="Number of queued jobs")
    cancelling: int = Field(..., description="Number of cancelling jobs")
    cancelled: int = Field(..., description="Number of cancelled jobs")
    deleting: int = Field(..., description="Number of deleting jobs")
    deleted: int = Field(..., description="Number of deleted jobs")
    unknown: int = Field(..., description="Number of unknown jobs")
    submitted_job_rate_min: float = Field(
        0.0,
        description="Job submission rate in the last minute "
        "(jobs per minute), based on created_at",
    )
    completed_job_rate_min: float = Field(
        0.0,
        description="Completed job rate in the last minute "
        "(completed jobs per minute), based on created_at",
    )


class GetSystemStatsRequest(BaseModel):
    """Get system stats request."""


class GetSystemStatsResponse(BaseModel):
    """Get system stats response.

    Reports resource usage of the API server process and the host
    machine. Similar to ``show_mem`` but additionally exposes the
    host-level CPU count and disk free space so the WebUI monitor
    center can render usage percentages.
    """

    # process id
    pid: int = Field(..., description="Process id of the API server")
    # resident set size in MB
    rss_mb: float = Field(..., description="Resident set size memory in MB")
    # virtual memory size in MB
    vms_mb: float = Field(..., description="Virtual memory size in MB")
    # number of threads
    thread_count: int = Field(
        ..., description="Number of threads in the process"
    )
    # number of gc tracked objects
    num_objects: int = Field(..., description="Number of gc tracked objects")
    # process-level cpu percent (0-100 * num_cores, as per psutil)
    cpu_percent: float = Field(
        ..., description="CPU usage percentage of the process"
    )
    # host-level total logical CPU count
    cpu_count: int = Field(
        ..., description="Total number of logical CPUs on the host"
    )
    # host-level CPU usage percent (0-100)
    host_cpu_percent: float = Field(
        ..., description="Host CPU usage percentage (0-100)"
    )
    # host-level total physical memory in MB
    mem_total_mb: float = Field(
        ..., description="Total physical memory of the host in MB"
    )
    # host-level memory usage percent (0-100)
    mem_percent: float = Field(
        ..., description="Host memory usage percentage (0-100)"
    )
    # disk total / free in MB for the partition hosting the working dir
    disk_total_mb: float = Field(
        ..., description="Total disk space of the working partition in MB"
    )
    disk_free_mb: float = Field(
        ..., description="Free disk space of the working partition in MB"
    )
    disk_percent: float = Field(
        ..., description="Disk usage percentage of the working partition"
    )
