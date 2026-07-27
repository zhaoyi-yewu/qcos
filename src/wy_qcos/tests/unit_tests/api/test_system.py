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

from wy_qcos.api.posiq.routes_jsonrpc.system import (
    debug_gc,
    debug_tracemalloc,
    ping,
    show_mem,
    system_info,
)
from wy_qcos.api.schemas import PingRequest
from wy_qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)


class TestSystem:
    @classmethod
    def setup_class(cls):
        cls.job_id = ConstantForTest.job_id

    def test_ping(self):
        mock_client = Mock(spec=PingRequest)
        mock_client.message = "message"
        response_info = ping(mock_client)
        assert response_info.message == "message"

    def test_system_info(self):
        # system_info uses job_repo.get_jobs_count() which returns an int
        mock_job_repo = Mock()
        mock_job_repo.get_jobs_count.return_value = 1
        response_info = system_info(None, None, job_repo=mock_job_repo)
        assert response_info.total_jobs_count == 1

    def test_show_mem(self):
        # mock psutil.Process to avoid real process introspection
        mock_process = Mock()
        mock_process.pid = 1234
        mock_process.num_threads.return_value = 10
        mock_process.cpu_percent.return_value = 5.5
        mock_mem_info = Mock()
        mock_mem_info.rss = 100 * 1024 * 1024
        mock_mem_info.vms = 200 * 1024 * 1024
        mock_process.memory_info.return_value = mock_mem_info

        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.psutil.Process",
                return_value=mock_process,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.gc.get_objects",
                return_value=list(range(50)),
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.os.getpid",
                return_value=1234,
            ),
        ):
            response_info = show_mem(None)
        assert response_info.pid == 1234
        assert response_info.rss_mb == 100.0
        assert response_info.vms_mb == 200.0
        assert response_info.thread_count == 10
        assert response_info.num_objects == 50
        assert response_info.cpu_percent == 5.5

    def test_debug_gc_default_generations(self):
        # gc.collect returns number of collected objects (int) in 3.8+
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.gc.collect",
                return_value=30,
            ) as mock_collect,
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.gc.get_objects"
            ) as mock_get_objects,
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.gc.garbage",
                [1, 2],
            ),
        ):
            mock_get_objects.side_effect = [
                list(range(100)),
                list(range(70)),
            ]
            response_info = debug_gc(None)
        assert mock_collect.call_args.args[0] == 2
        assert response_info.collected == 30
        assert response_info.uncollectable == 2
        assert response_info.count_before == 100
        assert response_info.count_after == 70

    def test_debug_gc_custom_generations(self):
        # test with explicit generations parameter
        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.gc.collect",
                return_value=10,
            ) as mock_collect,
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.gc.get_objects"
            ) as mock_get_objects,
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.gc.garbage",
                [],
            ),
        ):
            mock_get_objects.side_effect = [
                list(range(100)),
                list(range(90)),
            ]
            mock_request = Mock()
            mock_request.generations = 0
            response_info = debug_gc(mock_request)
        assert mock_collect.call_args.args[0] == 0
        assert response_info.collected == 10
        assert response_info.uncollectable == 0
        assert response_info.count_before == 100
        assert response_info.count_after == 90

    def test_debug_tracemalloc_default(self):
        # mock tracemalloc to test debug_tracemalloc snapshot action
        mock_snapshot = Mock()
        mock_stat = Mock()
        mock_frame = Mock()
        mock_frame.filename = "/path/to/file.py"
        mock_frame.lineno = 42
        mock_stat.traceback = [mock_frame]
        mock_stat.size = 1024
        mock_stat.count = 5
        mock_snapshot.statistics.return_value = [mock_stat]

        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "is_tracing",
                return_value=False,
            ),
            patch("wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc.start"),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "get_traced_memory",
                return_value=(2048, 4096),
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "take_snapshot",
                return_value=mock_snapshot,
            ),
        ):
            response_info = debug_tracemalloc(None)
        assert response_info.tracing is False
        assert response_info.traced_blocks == 5
        assert response_info.current == 2048
        assert response_info.peak == 4096
        assert len(response_info.top_stats) == 1
        assert response_info.top_stats[0].location == "/path/to/file.py:42"
        assert response_info.top_stats[0].size == 1024
        assert response_info.top_stats[0].count == 5

    def test_debug_tracemalloc_custom_nframe(self):
        # test with custom nframe parameter
        mock_snapshot = Mock()
        mock_snapshot.statistics.return_value = []

        mock_request = Mock()
        mock_request.action = "snapshot"
        mock_request.nframe = 10

        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "is_tracing",
                return_value=True,
            ),
            patch("wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc.start"),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "get_traced_memory",
                return_value=(1024, 2048),
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "take_snapshot",
                return_value=mock_snapshot,
            ),
        ):
            response_info = debug_tracemalloc(mock_request)
        assert response_info.tracing is True
        assert response_info.traced_blocks == 0
        assert response_info.current == 1024
        assert response_info.peak == 2048
        assert response_info.top_stats == []

    def test_debug_tracemalloc_stop(self):
        # test stop action: stops tracing and releases traces
        mock_request = Mock()
        mock_request.action = "stop"
        mock_request.nframe = 25

        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "get_traced_memory",
                return_value=(1024, 4096),
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc.stop"
            ) as mock_stop,
        ):
            response_info = debug_tracemalloc(mock_request)
        mock_stop.assert_called_once()
        assert response_info.tracing is False
        assert response_info.traced_blocks == 0
        assert response_info.current == 0
        assert response_info.peak == 4096
        assert response_info.top_stats == []

    def test_debug_tracemalloc_clear(self):
        # test clear action: clears traces but keeps tracing
        mock_request = Mock()
        mock_request.action = "clear"
        mock_request.nframe = 25

        with (
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "clear_traces"
            ) as mock_clear,
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "is_tracing",
                return_value=True,
            ),
            patch(
                "wy_qcos.api.posiq.routes_jsonrpc.system.tracemalloc."
                "get_traced_memory",
                return_value=(0, 2048),
            ),
        ):
            response_info = debug_tracemalloc(mock_request)
        mock_clear.assert_called_once()
        assert response_info.tracing is True
        assert response_info.traced_blocks == 0
        assert response_info.current == 0
        assert response_info.peak == 2048
        assert response_info.top_stats == []
