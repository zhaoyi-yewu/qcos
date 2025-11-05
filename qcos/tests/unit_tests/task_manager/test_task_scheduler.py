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

import pytest
from types import SimpleNamespace
from unittest.mock import patch, Mock

from qcos.common.constant import Constant
from qcos.task_manager.task_manager import TaskFlowManager
from qcos.task_manager.task_scheduler import (
    TaskScheduler,
    PriorityPolicy,
    SchedulerPolicyHandlerFactory,
    RealtimePolicy,
    BatchPolicy,
    DependentPolicy,
    PeriodicPolicy,
)
from qcos.task_manager.task_scheduler import TimePrecedencePolicy
from qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)

task = TaskScheduler()


class TestTaskScheduler:
    @patch.object(TaskFlowManager, "start")
    def test_start_taskmanager(self, mock_start):
        mock_start.return_value = None
        assert task.start_taskmanager() is None

    @patch.object(TaskFlowManager, "set_driver_manager")
    def test_set_driver_manager(self, mock_set_driver_manager):
        mock_set_driver_manager.return_value = None
        driver_manager = None
        assert task.set_driver_manager(driver_manager) is None

    def test_get_driver_manager(self):
        driver_manager = task.get_driver_manager()
        assert driver_manager is None

    def test_set_transpiler_manager(self):
        transpiler_manager = None
        assert task.set_transpiler_manager(transpiler_manager) is None

    def test_get_transpiler_manager(self):
        transpiler_manager = task.get_transpiler_manager()
        assert transpiler_manager is None

    @patch.object(TaskFlowManager, "set_device_manager")
    def test_set_device_manager(self, mock_set_device_manager):
        mock_set_device_manager.return_value = None
        device_manager = None
        assert task.set_device_manager(device_manager) is None

    def test_get_device_manager(self):
        device_manager = task.get_device_manager()
        assert device_manager is None

    @patch.object(TaskScheduler, "has_job")
    def test_add(self, mock_has_job):
        mock_has_job.return_value = False
        task.driver_manager = Mock()
        task.transpiler_manager = Mock()
        job_info = ConstantForTest.job_info
        job_info = SimpleNamespace(**job_info)

        with pytest.raises(Exception) as context:
            task.add(Constant.JOB_SCHED_POLICY_TIME_PRECEDENCE, job_info, None)
        assert str(context.value) is not None

    @patch.object(TaskFlowManager, "get_job_artifact")
    @patch.object(TaskScheduler, "get_job_status")
    @patch.object(TaskFlowManager, "convert_to_qcos_state")
    @patch.object(TaskFlowManager, "get_task_flow_result")
    def test_get_result_by_id(
        self,
        mock_get_task_flow_result,
        mock_convert_to_qcos_state,
        mock_get_job_status,
        mock_get_job_artifact,
    ):
        mock_convert_to_qcos_state.return_value = "state"
        mock_get_job_status.return_value = "job_status"
        mock_get_job_artifact.return_value = "job_artifact"
        mock_get_task_flow_result.return_value = iter([
            "state",
            "parameters",
            "results",
            "error_message",
        ])
        response, _ = task.get_result_by_id(ConstantForTest.job_id)
        assert response["results"] == "results"

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
            task.get_jobs(None)
        assert str(context.value) is not None

    @patch.object(TaskScheduler, "get_job_status")
    @patch.object(TaskFlowManager, "delete_task_flow_run")
    def test_delete_jobs(self, mock_delete_task_flow_run, mock_get_job_status):
        mock_get_job_status.return_value = 111
        mock_delete_task_flow_run.return_value = [
            {"job_status": 111, "state": 222},
        ]
        flow_list = task.delete_jobs([1, 2, 3], None)
        assert flow_list[0]["state"] == 222

    @patch.object(TaskScheduler, "get_job_status")
    @patch.object(TaskFlowManager, "cancel_task_flow_run")
    def test_cancel_jobs(self, mock_cancel_task_flow_run, mock_get_job_status):
        mock_cancel_task_flow_run.return_value = []
        mock_get_job_status.return_value = None
        flow_list = task.cancel_jobs(ConstantForTest.job_ids, None)
        assert not flow_list

    @patch.object(TaskFlowManager, "update_flow")
    @patch.object(TaskFlowManager, "get_task_flow_run")
    @patch.object(TaskFlowManager, "delete_task_flow_run")
    @patch.object(TaskFlowManager, "get_flow_info_by_backend")
    @patch.object(SchedulerPolicyHandlerFactory, "get_policy_handler_by_name")
    def test_update_job(
        self,
        mock_get_policy_handler_by_name,
        mock_get_flow_info_by_backend,
        mock_delete_task_flow_run,
        mock_get_task_flow_run,
        mock_update_flow,
    ):
        mock_flow_run = Mock()
        mock_state = Mock()
        mock_state.name = "QUEUED"
        mock_flow_run.state = mock_state
        mock_flow_run.parameters = {
            "job_info": {
                "data": {
                    "job_priority": 2,
                    "backend": "tiangong100",
                    "code_type": "qubo",
                }
            }
        }
        mock_update_flow.return_value = True
        mock_get_task_flow_run.return_value = mock_flow_run
        mock_delete_task_flow_run.return_value = [
            {"job_status": 111, "state": 222},
        ]
        mock_get_flow_info_by_backend.return_value = {
            "deploy_name": "tiangong100"
        }
        mock_policy_handler = Mock()
        mock_get_policy_handler_by_name.return_value = mock_policy_handler
        mock_policy_handler.exec_task.return_value = "mock_job_id_123"
        task.update_job(ConstantForTest.job_id, parameters={"job_priority": 1})
        mock_get_policy_handler_by_name.assert_called_once_with(
            Constant.JOB_SCHED_POLICY_TIME_PRECEDENCE
        )
        mock_policy_handler.exec_task.assert_called_once()

    @patch.object(TaskFlowManager, "run_callbacks")
    def test_run_callbacks(self, mock_callbacks):
        mock_callbacks.return_value = None
        callback = task.run_callbacks("data", "callbacks")
        assert callback is None

    def test_get_job_status(self):
        flow_results = [
            {"metadata": {"status": 1, "statuses": 2}},
            {"data": {"data1": 1}},
        ]

        flow_parameters = {
            "updated_job_info": {
                "results": [{"metadata": {"1": 1}}, {"status": {"2": 2}}]
            },
            "info": 233,
        }
        final_job_status = task.get_job_status(
            "job_status", flow_results, flow_parameters
        )
        assert final_job_status == 1

    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    def test_process_callbacks(self, mock_get_flow_runs_with_filters):
        mock_get_flow_runs_with_filters.return_value = []
        assert task.process_callbacks() is None


task_manager = TaskFlowManager()
priority_policy = PriorityPolicy(task_manager)
time_precedence_policy = TimePrecedencePolicy(task_manager)
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

        result = priority_policy.exec_task(
            ConstantForTest.flow_info,
            ConstantForTest.args["job_info"],
            None,
        )
        assert result == 514

    def test_calculate_priority(self):
        job_info = priority_policy.calculate_priority(
            ConstantForTest.args["job_info"]
        )
        assert job_info == 1


class TestTimePrecedencePolicy:
    @patch.object(TaskFlowManager, "deploy_task_flow")
    @patch.object(TaskFlowManager, "run_task_flow")
    def test_exec_task(self, mock_run_task_flow, mock_deploy_task_flow):
        mock_deploy_task_flow.return_value = 114
        mock_run_task_flow.return_value = 514

        result = time_precedence_policy.exec_task(
            ConstantForTest.flow_info,
            ConstantForTest.args["job_info"],
            None,
        )
        assert result == 514

    def test_calculate_priority(self):
        job_info = time_precedence_policy.calculate_priority(
            ConstantForTest.args["job_info"]
        )
        assert job_info == 1


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
        policy_handler = factory.get_policy_handler_by_name(
            Constant.JOB_SCHED_POLICY_TIME_PRECEDENCE
        )
        assert policy_handler is not None
