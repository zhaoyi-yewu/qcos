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


obj = TaskScheduler()


class TestTaskScheduler:
    @classmethod
    def setup_method(cls):
        cls.job_info = {
            "job_id": '00000000-0000-4000-8000-000000000001',
            "job_name": 'job_name',
            "job_status": Constant.JOB_STATUS_UNKNOWN,
            "job_sched_policy": Constant.DEFAULT_JOB_SCHED_POLICY,
            "job_priority": 1,
            "description": 'description',
            "backend": Constant.DRIVER_DUMMY,
            "transpiler": Constant.TRANSPILER_TYPES,
            "transpiler_info": {},
            "shots": 10,
            "profiling": Constant.PROFILING_TYPES,
            "callbacks": [],
            "dry_run": True,
            "creation_date": Library.get_current_datetime(),
            "end_date": Library.get_current_datetime()
        }
        cls.flow_info = {
            "deploy_name": Constant.DRIVER_DUMMY,
            "deploy_flow_func": "",
            "deploy_flow_path": "../engine/job_engine.py"
        }
        cls.job_id = "00000000-0000-4000-8000-000000000001"

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
        obj.get_result_by_id(self.job_id)

    def test_has_job(self):
        obj.has_job(self.job_id)

    def test_get_jobs(self):
        obj.get_jobs()

    def test_remove_jobs(self):
        job_ids = ['00000000-0000-4000-8000-000000000001',
                   '00000000-0000-4000-8000-000000000002',
                   '00000000-0000-4000-8000-000000000003']
        obj.remove_jobs(job_ids)

    def test_update_job(self):
        obj.update_job(self.job_id)



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
    @classmethod
    def setup_method(cls):
        cls.job_info = {
            "job_id": '00000000-0000-4000-8000-000000000001',
            "job_name": 'job_name',
            "job_status": Constant.JOB_STATUS_UNKNOWN,
            "job_sched_policy": Constant.DEFAULT_JOB_SCHED_POLICY,
            "job_priority": 10,
            "description": 'description',
            "backend": Constant.DRIVER_DUMMY,
            "transpiler": Constant.TRANSPILER_TYPES,
            "transpiler_info": {},
            "shots": 10,
            "profiling": Constant.PROFILING_TYPES,
            "callbacks": [],
            "dry_run": True,
            "creation_date": Library.get_current_datetime(),
            "end_date": Library.get_current_datetime()
        }
        cls.flow_info = {
            "deploy_name": Constant.DRIVER_DUMMY,
            "deploy_flow_func": "",
            "deploy_flow_path": "../engine/job_engine.py"
        }
        cls.job_id = "00000000-0000-4000-8000-000000000001"

    @patch.object(TaskFlowManager, "deploy_task_flow")
    @patch.object(TaskFlowManager, "run_task_flow")
    def test_exec_task(self, mock_run_task_flow, mock_deploy_task_flow):
        mock_deploy_task_flow.return_value = 114
        mock_run_task_flow.return_value = 514

        result = priority_policy.exec_task(self.flow_info, self.job_info)
        assert result == 514


class TestHighResponseRatioPolicy:
    def test_exec_task(self):
        high_response_ratio_policy.exec_task()


class TestShortestJobFirstPolicy:
    def test_exec_task(self):
        shortest_job_first_policy.exec_task()


class TestTimePrecedencePolicy:
    @classmethod
    def setup_method(cls):
        cls.job_info = {
            "job_id": '00000000-0000-4000-8000-000000000001',
            "job_name": 'job_name',
            "job_status": Constant.JOB_STATUS_UNKNOWN,
            "job_sched_policy": Constant.DEFAULT_JOB_SCHED_POLICY,
            "job_priority": 10,
            "description": 'description',
            "backend": Constant.DRIVER_DUMMY,
            "transpiler": Constant.TRANSPILER_TYPES,
            "transpiler_info": {},
            "shots": 10,
            "profiling": Constant.PROFILING_TYPES,
            "callbacks": [],
            "dry_run": True,
            "creation_date": Library.get_current_datetime(),
            "end_date": Library.get_current_datetime()
        }
        cls.flow_info = {
            "deploy_name": Constant.DRIVER_DUMMY,
            "deploy_flow_func": "",
            "deploy_flow_path": "../engine/job_engine.py"
        }

    @patch.object(TaskFlowManager, "deploy_task_flow")
    @patch.object(TaskFlowManager, "run_task_flow")
    def test_exec_task(self, mock_run_task_flow, mock_deploy_task_flow):
        mock_deploy_task_flow.return_value = 114
        mock_run_task_flow.return_value = 514

        result = time_precedence_policy.exec_task(
            self.flow_info, self.job_info)
        assert result == 514


class TestPeriodicPolicy:
    def test_exec_task(self):
        periodic_policy.exec_task()


class TestDependentPolicy:
    def test_exec_task(self):
        dependent_policy.exec_task()


class TestBatchPolicy:
    def test_exec_task(self):
        batch_policy.exec_task()


class TestRealtimePolicy:
    def test_exec_task(self):
        realtime_policy.exec_task()


class TestSchedulerPolicyHandlerFactory:
    def test_get_policy_handler_by_name(self):
        factory.get_policy_handler_by_name(Constant.JOB_SCHED_POLICY_PRIORITY)
