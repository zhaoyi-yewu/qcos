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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from abc import ABC

from common.constant import Constant
from task_manager import TaskFlowManager


class TaskScheduler(ABC):
    """
    Task scheduler
    """

    def __init__(self):
        """
        Init TaskScheduler
        """

        self._task_manager = TaskFlowManager()
        self._policy_factory = SchedulerPolicyHandlerFactory(self._task_manager)

        self._task_manager.start()

    def add(self, policy_type, job_info):
        """
        Add job to scheduler, scheduler will get policy handler by policy_type,
        use handler to execute it.

        :param policy_type: scheduler policy type
        :param job_info: job info
        :return job_id: job uuid
        :return e: exception
        """

        try:
            policy_handler = self._policy_factory.get_policy_handler_by_name(
                policy_type)
            job_id = policy_handler.exec_task(job_info)
            return job_id, None
        except Exception as e:
            return None, e

    def get_result_by_id(self, id):
        """
        Get result by job id

        :param id: job id
        :return result: result
        :return state: state
        """

        result, state = self._task_manager.get_task_flow_result(id)
        return result, state


class BaseSchedulerPolicy(ABC):
    """
    Base Scheduler Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        self._task_manager = task_manager


class PriorityPolicy(BaseSchedulerPolicy):
    """
    Priority Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_PRIORITY

    def exec_task(self, job_info):
        """
        PriorityPolicy execute task

        :param job_info: job info
        :return job_id: job uuid
        """

        priority = self.calculate_priority(job_info)
        job_deploy_id = self._task_manager.deploy_task_flow(
            job_info["deploy_name"] + "_" + self._type,
            self._type,
            priority,
            job_info["deploy_flow_func"],
            job_info["deploy_flow_path"])
        job_run_id = self._task_manager.run_task_flow(
            job_deploy_id,
            job_info["flow_args"])
        return job_run_id

    def calculate_priority(self, job_info):
        """
        calculate priority

        :param job_info: job info
        :return job_priority: job priority
        """

        return job_info["job_priority"]


class HighResponseRatioPolicy(BaseSchedulerPolicy):
    """
    High Response Ratio Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_HIGH_RESPONSE_RATIO

    # TODO(jidalong) HighResponseRatioPolicy
    def exec_task(self):
        return


class ShortestJobFirstPolicy(BaseSchedulerPolicy):
    """
    Shortest Job First Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_HIGH_RESPONSE_RATIO

    # TODO(jidalong) ShortestJobFirstPolicy
    def exec_task(self):
        return


class TimePrecedencePolicy(BaseSchedulerPolicy):
    """
    Time Precedence Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_TIME_PRECEDENCE

    def exec_task(self, job_info):
        """
        TimePrecedencePolicy execute task

        :param job_info: job info
        :return job_id: job uuid
        """

        priority = self.calculate_priority()
        job_deploy_id = self._task_manager.deploy_task_flow(
            job_info["deploy_name"] + "_" + self._type,
            self._type,
            priority,
            job_info["deploy_flow_func"],
            job_info["deploy_flow_path"])
        job_run_id = self._task_manager.run_task_flow(
            job_deploy_id,
            job_info["flow_args"])
        return job_run_id

    def calculate_priority(self):
        """
        calculate priority

        :return job_priority: default job priority
        """

        return Constant.DEFAULT_JOB_PRIORITY


class PeriodicPolicy(BaseSchedulerPolicy):
    """
    Periodic Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_PERIODIC

    # TODO(jidalong) PeriodicPolicy
    def exec_task(self):
        return


class DependentPolicy(BaseSchedulerPolicy):
    """
    Dependent Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_DEPENDENT

    # TODO(jidalong) DependentPolicy
    def exec_task(self):
        return


class BatchPolicy(BaseSchedulerPolicy):
    """
    Batch Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_BATCH

    # TODO(jidalong) BatchPolicy
    def exec_task(self):
        return


class RealtimePolicy(BaseSchedulerPolicy):
    """
    Realtime Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHEDULING_POLICY_REALTIME

    # TODO(jidalong) RealtimePolicy
    def exec_task(self):
        return


class SchedulerPolicyHandlerFactory(ABC):
    """
    Scheduler Policy Handler Factory
    """

    def __init__(self, task_manager):
        self._policy_mapping = {
            Constant.JOB_SCHEDULING_POLICY_PRIORITY:
                PriorityPolicy(task_manager),
            Constant.JOB_SCHEDULING_POLICY_HIGH_RESPONSE_RATIO:
                HighResponseRatioPolicy(task_manager),
            Constant.JOB_SCHEDULING_POLICY_SHORTEST_JOB_FIRST:
                ShortestJobFirstPolicy(task_manager),
            Constant.JOB_SCHEDULING_POLICY_TIME_PRECEDENCE:
                TimePrecedencePolicy(task_manager),
            Constant.JOB_SCHEDULING_POLICY_PERIODIC:
                PeriodicPolicy(task_manager),
            Constant.JOB_SCHEDULING_POLICY_DEPENDENT:
                DependentPolicy(task_manager),
            Constant.JOB_SCHEDULING_POLICY_BATCH:
                BatchPolicy(task_manager),
            Constant.JOB_SCHEDULING_POLICY_REALTIME:
                RealtimePolicy(task_manager),
        }

    def get_policy_handler_by_name(self, name: str):
        """
        Get policy handler by name

        :param name: policy name
        :return policy_handler: policy handler
        """

        policy_handler = self._policy_mapping.get(name)
        if policy_handler:
            return policy_handler
        raise ValueError(f"{name} is not a valid policy type")
