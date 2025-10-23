#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.api.posiq.routes_jsonrpc.system import ping, system_info
from qcos.api.schemas import PingRequest
from qcos.common.constant import Constant
from qcos.task_manager import TaskScheduler
from qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)


class TestSystem:
    @classmethod
    def setup_class(cls):
        cls.job_id = ConstantForTest.job_id

    def test_ping(self):
        mock_client = Mock(spec=PingRequest)
        mock_client.message = "message"
        ping(mock_client)

    @patch.object(TaskScheduler, "get_jobs")
    def test_system_info(self, mock_get_jobs):
        mock_get_jobs.return_value = iter(
            [
                [
                    {
                        "job_status": Constant.JOB_STATUS_RUNNING,
                        "id": self.job_id,
                        "progress": 100,
                    }
                ],
                None,
            ]
        )
        response_info = system_info()
        assert response_info.total_jobs_count == 1
