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

from types import SimpleNamespace
from unittest.mock import patch, Mock

import pytest

from qcos.common.constant import Constant
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
from tests.unit_tests.task_manager.constant_for_test import ConstantForTest

task = TaskScheduler()


class TestTaskScheduler:

    def test_set_driver_manager(self):
        driver_manager = DriverManager()
        task.set_driver_manager(driver_manager)

    def test_get_driver_manager(self):
        task.get_driver_manager()

    def test_set_transpiler_manager(self):
        transpiler_manager = TranspilerManager()
        task.set_transpiler_manager(transpiler_manager)

    def test_get_transpiler_manager(self):
        task.get_transpiler_manager()

    @patch.object(TaskScheduler, "has_job")
    def test_add(self, mock_has_job):
        mock_has_job.return_value = False
        task.driver_manager = Mock()
        task.transpiler_manager = Mock()
        job_info = ConstantForTest.job_info
        job_info = SimpleNamespace(**job_info)

        with pytest.raises(Exception) as context:
            task.add(Constant.JOB_SCHED_POLICY_PRIORITY, job_info)
        assert str(context.value) is not None

    @patch.object(TaskFlowManager, "get_job_artifact")
    @patch.object(TaskScheduler, "get_job_status")
    @patch.object(TaskFlowManager, "transform_to_qcos_state")
    @patch.object(TaskFlowManager, "get_task_flow_result")
    def test_get_result_by_id(self, mock_get_task_flow_result,
                              mock_transform_to_qcos_state,
                              mock_get_job_status,
                              mock_get_job_artifact):
        mock_transform_to_qcos_state.return_value = "state"
        mock_get_job_status.return_value = "job_status"
        mock_get_job_artifact.return_value = "job_artifact"
        mock_get_task_flow_result.return_value = iter(["state",
                                                       "parameters",
                                                       "results",
                                                       "error_message"])
        task.get_result_by_id(ConstantForTest.job_id)

    @patch.object(TaskFlowManager, "has_flow")
    def test_has_job(self, mock_has_flow):
        mock_has_flow.return_value = True
        assert task.has_job(ConstantForTest.job_id) is True

    @patch.object(TaskScheduler, "get_job_status")
    @patch.object(TaskFlowManager, "get_task_flow_list")
    def test_get_jobs(self, mock_get_task_flow_list, mock_get_job_status):
        mock_get_job_status.return_value = 111
        mock_get_task_flow_list.return_value = {"job_status": 111}

        with pytest.raises(Exception) as context:
            task.get_jobs()
        assert str(context.value) is not None

    @patch.object(TaskScheduler, "get_job_status")
    @patch.object(TaskFlowManager, "delete_task_flow_run")
    def test_remove_jobs(self, mock_delete_task_flow_run, mock_get_job_status):
        mock_get_job_status.return_value = 111
        mock_delete_task_flow_run.return_value = [
            {"job_status": 111, "state": 222}, ]
        task.remove_jobs([1, 2, 3])

    @patch.object(TaskFlowManager, "update_flow")
    def test_update_job(self, mock_update_flow):
        mock_update_flow.return_value = True
        result = task.update_job(ConstantForTest.job_id)
        assert result is True

    @patch.object(TaskFlowManager, "run_callbacks")
    def test_run_callbacks(self, mock_callbacks):
        mock_callbacks.return_value = None
        callback = task.run_callbacks("data", "callbacks")
        assert callback is None

    def test_get_job_status(self):
        flow_results = [{"metadata": {
            "status": 1, "statuses": 2}},
            {"data": {
                "data1": 1}}]

        flow_parameters = {"updated_job_info": {
            "results": [{"metadata": {"1": 1}},
                        {"status": {"2": 2}}]
        }, "info": 233}
        task.get_job_status("job_status", flow_results, flow_parameters)


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
