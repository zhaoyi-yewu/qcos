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
import uuid
from unittest import mock
from unittest.mock import patch, Mock

import pytest

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
        flow_info = (self.task_manager.
                     get_flow_info_by_backend(Constant.DRIVER_DUMMY))
        self.assertEqual(flow_info['deploy_flow_path'],
                         '../engine/job_engine.py')
        self.assertEqual(flow_info['deploy_name'], 'dummy')
        flow_info = (self.task_manager.deploy_task_flow
                     (Constant.DRIVER_DUMMY + "_"
                      + Constant.JOB_SCHED_POLICY_PRIORITY,
                      Constant.JOB_SCHED_POLICY_PRIORITY,
                      1, flow_info["deploy_flow_func"],
                      '../engine/job_engine.py'))
        self.assertIsInstance(flow_info, uuid.UUID)
        flow_info = (self.task_manager.
                     run_task_flow(flow_info, ConstantForTest.args))
        self.assertEqual(flow_info, ConstantForTest.job_id)

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_get_task_flow_result(self, mock_get_flow_run_id_by_job_id):
        mock_get_flow_run_id_by_job_id.return_value = None
        with pytest.raises(Exception) as context:
            self.task_manager.get_task_flow_result(ConstantForTest.job_id)
        assert str(context.value) == 'None'

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_has_flow(self, mock_get_flow_run_id_by_job_id):
        mock_get_flow_run_id_by_job_id.return_value = '1234'
        exist = self.task_manager.has_flow(ConstantForTest.job_id)
        assert exist is True

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_update_flow(self, mock_get_flow_run_id_by_job_id):
        mock_get_flow_run_id_by_job_id.return_value = None
        success = self.task_manager.update_flow(
            ConstantForTest.job_id)
        assert success is False

    def test_delete_task_flow_run(self):
        success_list = (self.task_manager.
                        delete_task_flow_run(ConstantForTest.job_ids))
        assert success_list is not None
