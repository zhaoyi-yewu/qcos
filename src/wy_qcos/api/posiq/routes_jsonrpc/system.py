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

import gc
import logging
import os
import tracemalloc

import psutil
from fastapi import Depends

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc.routes import system_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.utils.db_utils import get_repository
from wy_qcos.db.repositories.job import JobRepository
from .dependencies.authentication import auth

logger = logging.getLogger(__name__)
module_name = "SYSTEM"


@system_api_v1.method(
    openapi_extra={"no_auth": True},
)
def ping(
    body: schemas.PingRequest,
    auth_data: dict | None = Depends(auth),
) -> schemas.PongResponse:
    """Ping-pong to verify the availability of the system.

    Args:
        body(schemas.PingRequest): message
        auth_data: auth data

    Returns:
        pong response
    """
    func_name = "ping"
    logger.info(f"Call {func_name}: {body}")

    message = body.message

    _response_info = {"message": message}
    response_info = schemas.PongResponse.model_validate(_response_info)
    return response_info


@system_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
def system_info(
    body: schemas.SystemInfoRequest | None = None,
    auth_data: dict | None = Depends(auth),
    job_repo: JobRepository = Depends(get_repository(JobRepository)),
) -> schemas.SystemInfoResponse:
    """Get system info.

    Args:
        body(schemas.SystemInfoRequest): System Info Request
        auth_data: auth data
        job_repo: Job repository dependency

    Returns:
        system info response
    """
    func_name = "system_info"
    logger.info(f"Call {func_name}: {body}")

    # Query total jobs count from database
    total_jobs_count = job_repo.get_jobs_count()

    _response_info = {"total_jobs_count": total_jobs_count}
    response_info = schemas.SystemInfoResponse.model_validate(_response_info)
    return response_info


@system_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
def show_mem(
    body: schemas.ShowMemRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.ShowMemResponse:
    """Show memory usage of the API server process.

    Args:
        body(schemas.ShowMemRequest): Show Memory Request
        auth_data: auth data

    Returns:
        memory usage response
    """
    func_name = "show_mem"
    logger.info(f"Call {func_name}: {body}")

    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()

    _response_info = {
        "pid": process.pid,
        "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
        "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
        "thread_count": process.num_threads(),
        "num_objects": len(gc.get_objects()),
        "cpu_percent": process.cpu_percent(interval=0.1),
    }
    response_info = schemas.ShowMemResponse.model_validate(_response_info)
    return response_info


@system_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
def debug_gc(
    body: schemas.DebugGcRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.DebugGcResponse:
    """Manually trigger garbage collection.

    Args:
        body(schemas.DebugGcRequest): Debug GC Request
        auth_data: auth data

    Returns:
        gc collection result response
    """
    func_name = "debug_gc"
    logger.info(f"Call {func_name}: {body}")

    generations = 2
    if body is not None and body.generations is not None:
        generations = body.generations

    count_before = len(gc.get_objects())
    # gc.collect() returns the number of collected objects in
    # Python 3.8+; uncollectable count is derived from the garbage
    # list length after collection.
    collected = gc.collect(generations)
    uncollectable = len(gc.garbage)
    count_after = len(gc.get_objects())

    # malloc_trim(0) asks glibc to return free heap pages to the OS.
    # Only available on Linux with glibc; None on other platforms.
    malloc_trim_ret = Library.malloc_trim(0)
    if malloc_trim_ret is None:
        logger.debug("malloc_trim skipped (not available)")
    else:
        logger.debug(f"malloc_trim(0) returned {malloc_trim_ret}")

    _response_info = {
        "collected": collected,
        "uncollectable": uncollectable,
        "count_before": count_before,
        "count_after": count_after,
        "malloc_trim_ret": malloc_trim_ret,
    }
    response_info = schemas.DebugGcResponse.model_validate(_response_info)
    return response_info


@system_api_v1.method(
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
def debug_tracemalloc(
    body: schemas.DebugTracemallocRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.DebugTracemallocResponse:
    """Debug memory allocations via tracemalloc.

    Actions:
        - snapshot: start tracing (if not active) and take a snapshot
          of current allocations
        - stop: stop tracemalloc tracing and release all traces
        - clear: clear traces but keep tracing

    Args:
        body(schemas.DebugTracemallocRequest): Debug Tracemalloc Request
        auth_data: auth data

    Returns:
        tracemalloc statistics response
    """
    func_name = "debug_tracemalloc"
    logger.info(f"Call {func_name}: {body}")

    action = "snapshot"
    nframe = 25
    sort_count = False
    if body is not None:
        if body.action is not None:
            action = body.action
        if body.nframe is not None:
            nframe = body.nframe
        if body.sort_count is not None:
            sort_count = body.sort_count

    stat_items = []

    if action == "stop":
        # stop tracing and release all traces
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        _response_info = {
            "tracing": False,
            "traced_blocks": 0,
            "current": 0,
            "peak": peak,
            "top_stats": [],
        }
    elif action == "clear":
        # clear traces but keep tracing
        tracemalloc.clear_traces()
        current, peak = tracemalloc.get_traced_memory()
        _response_info = {
            "tracing": tracemalloc.is_tracing(),
            "traced_blocks": 0,
            "current": current,
            "peak": peak,
            "top_stats": [],
        }
    else:
        # default: snapshot action
        # start tracing if not already tracing
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        current, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()
        # snapshot.statistics() returns stats sorted by size (descending)
        # by default. When sort_count is requested, re-sort by count
        # (descending) BEFORE applying the nframe limit so that the top
        # entries by count are returned instead of the top entries by
        # size truncated to nframe.
        top_stats = snapshot.statistics("lineno", cumulative=True)
        if sort_count:
            top_stats = sorted(top_stats, key=lambda s: s.count, reverse=True)

        # total traced blocks is the sum of all allocation counts
        traced_blocks = sum(stat.count for stat in top_stats)

        for stat in top_stats[:nframe]:
            frame = stat.traceback[0]
            location = f"{frame.filename}:{frame.lineno}"
            stat_items.append({
                "location": location,
                "size": stat.size,
                "count": stat.count,
            })

        _response_info = {
            "tracing": tracemalloc.is_tracing(),
            "traced_blocks": traced_blocks,
            "current": current,
            "peak": peak,
            "top_stats": stat_items,
        }

    response_info = schemas.DebugTracemallocResponse.model_validate(
        _response_info
    )
    return response_info
