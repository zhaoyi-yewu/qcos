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

from unittest.mock import patch

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.driver_manager import DriverManager
from qcos.task_manager.task_manager import TaskFlowManager
from qcos.task_manager.task_scheduler import (TaskScheduler, PriorityPolicy,
                                              SchedulerPolicyHandlerFactory,
                                              RealtimePolicy, BatchPolicy,
                                              DependentPolicy, PeriodicPolicy,
                                              ShortestJobFirstPolicy,
                                              HighResponseRatioPolicy)
from qcos.task_manager.task_scheduler import TimePrecedencePolicy
from qcos.transpiler.transpiler_manager import TranspilerManager
from tests.unittest.task_manager.constant_for_test import ConstantForTest

obj = TaskScheduler()


class TestTaskScheduler:
    def test_start_taskmanager(self):
        obj.start_taskmanager()

    def test_set_driver_manager(self):
        driver_manager = DriverManager()
        obj.set_driver_manager(driver_manager)
        assert isinstance(obj.driver_manager, driver_manager.__class__)

    def test_get_driver_manager(self):
        assert isinstance(obj.get_driver_manager(),
                          DriverManager().__class__)

    def test_set_transpiler_manager(self):
        transpiler_manager = TranspilerManager()
        obj.set_transpiler_manager(transpiler_manager)
        assert isinstance(obj.transpiler_manager,
                          transpiler_manager.__class__)

    def test_get_transpiler_manager(self):
        assert isinstance(
            obj.get_transpiler_manager(),
            TranspilerManager().__class__)

    def test_get_result_by_id(self):
        obj.get_result_by_id(ConstantForTest.job_id)

    def test_has_job(self):
        obj.has_job(ConstantForTest.job_id)

    def test_get_jobs(self):
        obj.get_jobs()

    def test_remove_jobs(self):
        obj.remove_jobs(ConstantForTest.job_ids)

    def test_update_job(self):
        obj.update_job(ConstantForTest.job_id)



task_manager = TaskFlowManager()
priority_policy = PriorityPolicy(task_manager)
time_precedence_policy = TimePrecedencePolicy(task_manager)
high_response_ratio_policy = HighResponseRatioPolicy(task_manager)
shortest_job_first_policy = ShortestJobFirstPolicy(task_manager)
periodic_policy = PeriodicPolicy(task_manager)
dependent_policy = DependentPolicy(task_manager)
batch_policy = BatchPolicy(task_manager)
realtime_policy = RealtimePolicy(task_manager)
factory = SchedulerPolicyHandlerFactory(task_manager)


class TestPriorityPolicy:

    @patch.object(TaskFlowManager, "deploy_task_flow")
    @patch.object(TaskFlowManager, "run_task_flow")
    def test_exec_task(self, mock_run_task_flow, mock_deploy_task_flow):
        mock_deploy_task_flow.return_value = 114
        mock_run_task_flow.return_value = 514

        result = priority_policy.exec_task(ConstantForTest.flow_info,
                                           ConstantForTest.job_info)
        assert result == 514


class TestHighResponseRatioPolicy:
    def test_exec_task(self):
        high_response_ratio_policy.exec_task()


class TestShortestJobFirstPolicy:
    def test_exec_task(self):
        shortest_job_first_policy.exec_task()


class TestTimePrecedencePolicy:

    @patch.object(TaskFlowManager, "deploy_task_flow")
    @patch.object(TaskFlowManager, "run_task_flow")
    def test_exec_task(self, mock_run_task_flow, mock_deploy_task_flow):
        mock_deploy_task_flow.return_value = 114
        mock_run_task_flow.return_value = 514

        result = time_precedence_policy.exec_task(
            ConstantForTest.flow_info, ConstantForTest.job_info)
        assert result == 514


class TestPeriodicPolicy:
    def test_exec_task(self):
        assert periodic_policy.exec_task() is None



class TestDependentPolicy:
    def test_exec_task(self):
        assert dependent_policy.exec_task() is None


class TestBatchPolicy:
    def test_exec_task(self):
        assert batch_policy.exec_task() is None


class TestRealtimePolicy:
    def test_exec_task(self):
        assert realtime_policy.exec_task() is None


class TestSchedulerPolicyHandlerFactory:
    def test_get_policy_handler_by_name(self):
        factory.get_policy_handler_by_name(Constant.JOB_SCHED_POLICY_PRIORITY)
