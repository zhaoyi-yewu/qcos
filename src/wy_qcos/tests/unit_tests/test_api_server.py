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

from unittest.mock import patch, Mock

from wy_qcos.api_server import main
from wy_qcos.common.library import Library
from wy_qcos.server import Server
from wy_qcos.task_manager import TaskScheduler


class TestApiServer:
    @patch.object(TaskScheduler, "start_taskmanager")
    @patch.object(Server, "run")
    @patch("wy_qcos.api_server.asyncio.get_event_loop")
    @patch.object(Library, "create_pid_file")
    @patch.object(Library, "mkdir")
    @patch.object(Library, "kill_pid")
    def test_main(
        self,
        mock_kill_pid,
        mock_mkdir,
        mock_create_pid_file,
        mock_get_event_loop,
        mock_run,
        mock_start_taskmanager,
    ):
        mock_start_taskmanager.return_value = None
        mock_run.return_value = None
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = "Mocked task done"
        mock_get_event_loop.return_value = mock_loop
        mock_kill_pid.return_value = None
        mock_mkdir.return_value = None
        mock_create_pid_file.return_value = None
        main()

    def test_main_daemon_writes_final_process_id(self):
        call_order = []
        with (
            patch.object(Library, "kill_pid"),
            patch.object(Library, "mkdir"),
            patch.object(Library, "create_pid_file") as mock_create_pid,
            patch("wy_qcos.api_server.daemonize") as mock_daemonize,
            patch("wy_qcos.api_server.asyncio.get_event_loop"),
            patch.object(Server, "run"),
            patch.object(TaskScheduler, "start_taskmanager"),
            patch("wy_qcos.api_server.sys.argv", ["qcos-api", "--daemon"]),
        ):
            mock_daemonize.side_effect = lambda: call_order.append("daemon")
            mock_create_pid.side_effect = lambda path: call_order.append("pid")
            main()

        assert call_order == ["daemon", "pid"]
