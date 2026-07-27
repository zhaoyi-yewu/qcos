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


class DebugGcRequest(BaseModel):
    """Debug GC Request.

    Pydantic Model for Debug GC Request.
    """

    # gc generations to collect, default 2 (full collection)
    generations: int | None = Field(
        2, description="GC generations to collect (0, 1, 2)"
    )


class DebugGcResponse(BaseModel):
    """Debug GC Response.

    Pydantic Model for Debug GC Response.
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


class DebugTracemallocRequest(BaseModel):
    """Debug Tracemalloc Request.

    Pydantic Model for Debug Tracemalloc Request.
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


class TracemallocStatItem(BaseModel):
    """Tracemalloc Stat Item.

    Pydantic Model for single tracemalloc stat item.
    """

    # filename:lineno of the allocation
    location: str = Field(..., description="Filename:lineno of the allocation")
    # size in bytes
    size: int = Field(..., description="Size in bytes")
    # count of allocations
    count: int = Field(..., description="Count of allocations")


class DebugTracemallocResponse(BaseModel):
    """Debug Tracemalloc Response.

    Pydantic Model for Debug Tracemalloc Response.
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
    top_stats: list[TracemallocStatItem] = Field(
        default_factory=list,
        description="Top memory allocation statistics",
    )
    # leak probes: sizes of suspected unbounded in-memory containers
    leak_probes: dict = Field(
        default_factory=dict,
        description="Sizes of suspected unbounded in-memory containers",
    )
