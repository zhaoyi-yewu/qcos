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

from pydantic import BaseModel, Field


class PingRequest(BaseModel):
    """Ping Request.

    Pydantic Model for Ping Request.
    """

    # message
    message: str | None = Field(None, description="Ping message")


class PongResponse(BaseModel):
    """Pong Response.

    Pydantic Model for Pong Response.
    """

    # message
    message: str | None = Field(None, description="Pong message")


class SystemInfoRequest(BaseModel):
    """System Info Request.

    Pydantic Model for System Info Request.
    """


class SystemInfoResponse(BaseModel):
    """System Info Response.

    Pydantic Model for System Info Response.
    """

    # total jobs count
    total_jobs_count: int = Field(
        ..., description="Total number of jobs in the system"
    )


class ShowMemRequest(BaseModel):
    """Show Memory Request.

    Pydantic Model for Show Memory Request.
    """


class ShowMemResponse(BaseModel):
    """Show Memory Response.

    Pydantic Model for Show Memory Response.
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
    # cpu percent
    cpu_percent: float = Field(
        ..., description="CPU usage percentage of the process"
    )


class GcMemRequest(BaseModel):
    """GC Memory Request.

    Pydantic Model for GC Memory Request.
    """

    # gc generations to collect, default 2 (full collection)
    generations: int | None = Field(
        2, description="GC generations to collect (0, 1, 2)"
    )


class GcMemResponse(BaseModel):
    """GC Memory Response.

    Pydantic Model for GC Memory Response.
    """

    # number of collected objects
    collected: int = Field(..., description="Number of collected objects")
    # number of uncollectable objects
    uncollectable: int = Field(
        ..., description="Number of uncollectable objects"
    )
    # object count before collection
    count_before: int = Field(
        ..., description="Number of gc tracked objects before collection"
    )
    # object count after collection
    count_after: int = Field(
        ..., description="Number of gc tracked objects after collection"
    )
    # malloc_trim return value (1 success, 0 failure); None when
    # malloc_trim is not available on the current platform
    malloc_trim_ret: int | None = Field(
        None,
        description=(
            "malloc_trim(0) return value: 1 success, 0 failure; "
            "None when malloc_trim is not available"
        ),
    )


class TraceMemRequest(BaseModel):
    """Trace Mem Request.

    Pydantic Model for Trace Mem Request.
    """

    # action: snapshot (take snapshot), stop (stop tracing),
    # clear (clear traces)
    action: str = Field(
        "snapshot", description="Action: snapshot, stop, or clear"
    )
    # number of top memory allocations to show
    nframe: int = Field(
        25, description="Number of top memory allocations to show"
    )
    # sort top memory allocations by count (descending) instead of by size
    sort_count: bool = Field(
        False,
        description="Sort top memory allocations by count (descending) "
        "instead of by size. Sorting is applied before limiting "
        "to nframe.",
    )


class TraceMemStatItem(BaseModel):
    """Trace Mem Stat Item.

    Pydantic Model for single tracemalloc stat item.
    """

    # filename:lineno of the allocation
    location: str = Field(..., description="Filename:lineno of the allocation")
    # size in bytes
    size: int = Field(..., description="Size in bytes")
    # count of allocations
    count: int = Field(..., description="Count of allocations")


class TraceMemResponse(BaseModel):
    """Trace Mem Response.

    Pydantic Model for Trace Mem Response.
    """

    # whether tracemalloc is currently tracing
    tracing: bool = Field(
        ..., description="Whether tracemalloc is currently tracing"
    )
    # traced memory blocks count
    traced_blocks: int = Field(
        ..., description="Number of traced memory blocks"
    )
    # current traced memory in bytes
    current: int = Field(..., description="Current traced memory in bytes")
    # peak traced memory in bytes
    peak: int = Field(..., description="Peak traced memory in bytes")
    # top memory allocation statistics
    top_stats: list[TraceMemStatItem] = Field(
        default_factory=list,
        description="Top memory allocation statistics",
    )


class ListWorkersRequest(BaseModel):
    """List Workers Request.

    Pydantic Model for List Workers Request.
    """


class WorkerInfo(BaseModel):
    """Worker Info.

    Pydantic Model for single prefect worker info.
    """

    # worker name
    worker_name: str = Field(..., description="Worker name")
    # work pool name
    work_pool: str = Field(..., description="Work pool name")
    # worker status (e.g. ONLINE, OFFLINE)
    worker_status: str = Field(..., description="Worker status")
    # worker process pid, may be None
    pid: int | None = Field(None, description="Worker process pid")


class ListWorkersResponse(BaseModel):
    """List Workers Response.

    Pydantic Model for List Workers Response.
    """

    # list of workers
    workers: list[WorkerInfo] = Field(
        default_factory=list,
        description="List of prefect workers",
    )


class RestartWorkerRequest(BaseModel):
    """Restart Worker Request.

    Pydantic Model for Restart Worker Request.
    """

    # worker name to restart
    worker_name: str = Field(..., description="Worker name to restart")


class RestartWorkerResponse(BaseModel):
    """Restart Worker Response.

    Pydantic Model for Restart Worker Response.
    """

    # whether the restart operation succeeded
    success: bool = Field(..., description="Whether restart succeeded")
    # detail message
    message: str = Field(..., description="Detail message")
    # worker name
    worker_name: str = Field(..., description="Worker name")
