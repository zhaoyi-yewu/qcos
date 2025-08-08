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

import unittest
from unittest import mock
from unittest.mock import patch
from uuid import UUID

from qcos.common.constant import Constant, HttpCode
from tests.unittest.task_manager.constant_for_test import ConstantForTest
from qcos.task_manager.task_manager import TaskFlowManager


class TestTaskFlowManager(unittest.TestCase):
    @patch.object(TaskFlowManager, 'check_connection')
    def setUp(self, mock_check_connection):
        self.task_manager = TaskFlowManager()
        self.task_manager.start()

    def test_transform_to_qcos_state(self):
        # case 1: JOB_STATUS_FAILED
        state = Constant.PREFECT_STATE_CRASHED
        v = self.task_manager.transform_to_qcos_state(state)
        self.assertEqual(v, Constant.JOB_STATUS_FAILED)

        # case 2: JOB_STATUS_QUEUED
        state = Constant.PREFECT_STATE_SCHEDULED
        v = self.task_manager.transform_to_qcos_state(state)
        self.assertEqual(v, Constant.JOB_STATUS_QUEUED)

        # case 3: unknown status
        state = "unknown"
        v = self.task_manager.transform_to_qcos_state(state)
        self.assertEqual(v, state.upper())

    def test_check_connection(self):
        mock_prefect_client = mock.Mock()
        mock_hello_return = mock.Mock()
        mock_prefect_client.hello.return_value = mock_hello_return

        # case1: success
        mock_hello_return.status_code = HttpCode.SUCCESS_OK
        self.task_manager._sync_client = mock_prefect_client
        self.task_manager.check_connection()

        # case2: false
        mock_hello_return.status_code = HttpCode.TIMEOUT_ERROR
        self.task_manager._sync_client = mock_prefect_client
        with self.assertRaises(TimeoutError) as e:
            self.task_manager.check_connection()
        self.assertEqual(str(e.exception),
                         "Connection to prefect server timeout")

    def test_set_driver_manager(self):
        self.task_manager.set_driver_manager('driver_manager')
        self.assertEqual(self.task_manager.driver_manager, 'driver_manager')

    def test_deploy_task_flow(self):
        v = self.task_manager.get_flow_info_by_backend(Constant.DRIVER_DUMMY)
        self.assertEqual(v['deploy_flow_path'], '../engine/job_engine.py')
        self.assertEqual(v['deploy_name'], 'dummy')
        v = (self.task_manager.deploy_task_flow
             (Constant.DRIVER_DUMMY + "_"
              + Constant.JOB_SCHED_POLICY_PRIORITY,
              Constant.JOB_SCHED_POLICY_PRIORITY,
              1, v["deploy_flow_func"],
              '../engine/job_engine.py'))
        self.assertEqual(v, UUID('a0f06528-abf5-4418-8815-78097b14a299'))
        v = self.task_manager.run_task_flow(v, ConstantForTest.args)
        self.assertEqual(v, ConstantForTest.job_id)

    def test_get_task_flow_result(self):
        self.task_manager.get_task_flow_result(ConstantForTest.job_id)

    def test_has_flow(self):
        v = self.task_manager.has_flow(ConstantForTest.job_id)
        self.assertEqual(v, True)

    def test_update_flow(self):
        v = self.task_manager.update_flow(ConstantForTest.job_id)
        self.assertEqual(v, (True, None))

    def test_get_task_flow_list(self):
        v = self.task_manager.get_task_flow_list()

    def test_delete_task_flow_run(self):
        self.task_manager.delete_task_flow_run(ConstantForTest.job_ids)
