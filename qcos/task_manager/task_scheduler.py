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

import logging
from abc import ABC

from prefect import exceptions as prefect_exceptions

from qcos.common import errors
from qcos.common.constant import Constant
from .task_manager import TaskFlowManager

logger = logging.getLogger(__name__)


class TaskScheduler(ABC):
    """
    Task scheduler
    """

    def __init__(self):
        """
        Init TaskScheduler
        """

        self._task_manager = TaskFlowManager()
        self._policy_factory = SchedulerPolicyHandlerFactory(
            self._task_manager
        )
        self.driver_manager = None
        self.transpiler_manager = None
        self.device_manager = None

    def start_taskmanager(self):
        """
        Start TaskManager
        """

        self._task_manager.start()

    def set_driver_manager(self, driver_manager):
        """
        Set driver manager

        :param driver_manager: driver manager
        """

        self.driver_manager = driver_manager
        self._task_manager.set_driver_manager(driver_manager)

    def get_driver_manager(self):
        """
        Get driver manager

        :return: driver manager
        """
        return self.driver_manager

    def set_transpiler_manager(self, transpiler_manager):
        """
        Set transpiler manager

        :param transpiler_manager: transpiler manager
        """

        self.transpiler_manager = transpiler_manager

    def get_transpiler_manager(self):
        """
        Get transpiler manager

        :return: transpiler manager
        """
        return self.transpiler_manager

    def set_device_manager(self, device_manager):
        """
        Set device manager

        :param device_manager: device manager
        """

        self.device_manager = device_manager
        self._task_manager.set_device_manager(device_manager)

    def get_device_manager(self):
        """
        Get device manager

        :return: device manager
        """
        return self.device_manager

    def add(self, policy_type, job_info):
        """
        Add job to scheduler, scheduler will get policy handler by policy_type,
        use handler to execute it.

        :param policy_type: scheduler policy type
        :param job_info: job info
        :return job_id: job uuid
        :return e: exception
        """
        if job_info.job_id:
            exist = self.has_job(job_info.job_id)
            if exist:
                return None, f"Job uuid is already existed: {job_info.job_id}"

        # get driver info
        backend = job_info.backend
        device = self.device_manager.get_device(backend)
        if not device:
            err_msg = f"Backend: '{backend}' is not found"
            logger.error(err_msg)
            return None, f"Execute work flow failed: {err_msg}"
        if not device.enable:
            err_msg = f"Backend driver: {backend} is disabled"
            logger.error(err_msg)
            return None, f"Execute work flow failed: {err_msg}"
        driver = device.get_driver()
        driver_module_name = driver.get_module_name()
        driver_class_name = driver.get_class_name()

        # get transpiler options
        transpiler_module_name = None
        transpiler_class_name = None
        transpiler_name = driver.get_transpiler()
        transpiler = self.transpiler_manager.get_transpiler(transpiler_name)
        if transpiler:
            transpiler_module_name = transpiler.get_module_name()
            transpiler_class_name = transpiler.get_class_name()

        # execute task
        try:
            flow_info = self._task_manager.get_flow_info_by_backend(
                backend)
            policy_handler = self._policy_factory.get_policy_handler_by_name(
                policy_type)
            job_json_info = {}
            job_json_info["data"] = job_info.model_dump()
            job_json_info["driver"] = {
                "module_name": driver_module_name,
                "class_name": driver_class_name
            }
            job_json_info["transpiler"] = {
                "module_name": transpiler_module_name,
                "class_name": transpiler_class_name
            }
            job_json_info["device"] = {
                "configs": device.get_configs()
            }

            job_id = policy_handler.exec_task(flow_info, job_json_info)
            res = {"job_id": job_id}
            return res, None
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
            raise errors.WorkFlowError(e)

    def get_result_by_id(self, job_id):
        """
        Get result by job id

        :param job_id: job id
        :return results: result
        :return parameters: parameters
        :return state: state
        :return error_message: flow error message
        """
        try:
            state, parameters, results, error_message = \
                self._task_manager.get_task_flow_result(job_id)
            state = self._task_manager.transform_to_qcos_state(state)
            job_status = self.get_job_status(state, results, parameters)
            artifact = self._task_manager.get_job_artifact(job_id)
            response = {
                "job_status": job_status,
                "parameters": parameters,
                "results": results,
                "artifact": artifact,
                "error_message": error_message,
            }
            return response, None
        except prefect_exceptions.ObjectNotFound as e:
            err_msg = f"Job: '{job_id}' is not found"
            logger.warning(err_msg)
            raise errors.NotFound(err_msg) from e
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
            raise errors.WorkFlowError(e)

    def has_job(self, job_id):
        """
        Check if flow exists

        :param job_id: job id
        :return if flow exists
        """
        return self._task_manager.has_flow(job_id)

    def get_jobs(self):
        """
        Get job list

        :return flow_list: flow run list
        :return error: error
        """

        try:
            flow_list = self._task_manager.get_task_flow_list()
            for flow in flow_list:
                flow["job_status"] = self.get_job_status(
                    flow["state"], flow["results"], flow["parameters"])
            return flow_list, None
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
            raise errors.WorkFlowError(e)

    def delete_jobs(self, ids):
        """
        Delete jobs

        :param ids: job id list
        :return flow_list: flow list
        :return error: error
        """

        flow_list = self._task_manager.delete_task_flow_run(ids)
        for flow in flow_list:
            flow["job_status"] = self.get_job_status(
                flow["state"], None, None)
        return flow_list

    def cancel_jobs(self, ids):
        """
        Cancel jobs

        :param ids: job id list
        :return flow_list: flow list
        :return error: error
        """

        flow_list = self._task_manager.cancel_task_flow_run(ids)
        for flow in flow_list:
            flow["job_status"] = self.get_job_status(
                flow["state"], None, None)
        return flow_list

    def update_job(self, job_id, name=None, parameters=None, variables=None):
        """
        Update job

        :param job_id: job id
        :param name: job name
        :param parameters: job parameters
        :param variables: job variables
        :return if flow exists
        """
        return self._task_manager.update_flow(
            job_id, name, parameters, variables)

    def run_callbacks(self, data, callbacks):
        """
        Run callbacks for job

        :param data: data to send
        :param callbacks: callbacks
        """
        return self._task_manager.run_callbacks(data, callbacks)

    @staticmethod
    def get_job_status(job_status, flow_results, flow_parameters):
        """
        Get job status by combining flow state and user defined task status

        :param job_status: job status
        :param flow_results: flow results
        :param flow_parameters: parameters
        :return job_status
        """
        job_status = job_status.upper()
        final_job_status = job_status
        flow_results_status = None
        flow_parameters_status = None

        # get job_status from flow_results
        if flow_results:
            for flow_result in flow_results:
                metadata = flow_result.get("metadata", None)
                if metadata:
                    _flow_results_status = metadata.get("status", None)
                    flow_results_status = _flow_results_status

        # get job_status from user-defined parameters
        if flow_parameters:
            updated_job_info = flow_parameters.get("updated_job_info", None)
            if updated_job_info:
                results = updated_job_info.get("results", None)
                if results:
                    for result in results:
                        metadata = result.get("metadata", {})
                        _job_status = metadata.get("status", None)
                        flow_parameters_status = _job_status

        # determine final job_status
        if flow_parameters_status:
            final_job_status = flow_parameters_status
        elif flow_results_status:
            final_job_status = flow_results_status
        return final_job_status


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
        self._type = Constant.JOB_SCHED_POLICY_PRIORITY

    def exec_task(self, flow_info, job_info):
        """
        PriorityPolicy execute task

        :param flow_info: flow info
        :param job_info: job info
        :return job_id: job uuid
        """

        priority = self.calculate_priority(job_info)
        job_deploy_id = self._task_manager.deploy_task_flow(
            flow_info["deploy_name"] + "_" + self._type,
            self._type,
            priority,
            flow_info["deploy_flow_func"],
            flow_info["deploy_flow_path"])
        job_run_id = self._task_manager.run_task_flow(
            job_deploy_id,
            {"job_info": job_info})
        return job_run_id

    def calculate_priority(self, job_info):
        """
        calculate priority

        :param job_info: job info
        :return job_priority: job priority
        """
        return job_info["data"]["job_priority"]


class HighResponseRatioPolicy(BaseSchedulerPolicy):
    """
    High Response Ratio Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHED_POLICY_HIGH_RESPONSE_RATIO

    # TODO(jidalong) HighResponseRatioPolicy
    def exec_task(self):
        return


class ShortestJobFirstPolicy(BaseSchedulerPolicy):
    """
    Shortest Job First Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHED_POLICY_HIGH_RESPONSE_RATIO

    # TODO(jidalong) ShortestJobFirstPolicy
    def exec_task(self):
        return


class TimePrecedencePolicy(BaseSchedulerPolicy):
    """
    Time Precedence Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHED_POLICY_TIME_PRECEDENCE

    def exec_task(self, flow_info, job_info):
        """
        TimePrecedencePolicy execute task

        :param flow_info: flow info
        :param job_info: job info
        :return job_id: job uuid
        """

        priority = self.calculate_priority(job_info)
        job_deploy_id = self._task_manager.deploy_task_flow(
            flow_info["deploy_name"] + "_" + self._type,
            self._type,
            priority,
            flow_info["deploy_flow_func"],
            flow_info["deploy_flow_path"])
        job_run_id = self._task_manager.run_task_flow(
            job_deploy_id,
            {"job_info": job_info})
        return job_run_id

    def calculate_priority(self, job_info):
        """
        calculate priority

        :param job_info: job info
        :return job_priority: job priority
        """
        return job_info["data"]["job_priority"]


class PeriodicPolicy(BaseSchedulerPolicy):
    """
    Periodic Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHED_POLICY_PERIODIC

    # TODO(jidalong) PeriodicPolicy
    def exec_task(self):
        return


class DependentPolicy(BaseSchedulerPolicy):
    """
    Dependent Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHED_POLICY_DEPENDENT

    # TODO(jidalong) DependentPolicy
    def exec_task(self):
        return


class BatchPolicy(BaseSchedulerPolicy):
    """
    Batch Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHED_POLICY_BATCH

    # TODO(jidalong) BatchPolicy
    def exec_task(self):
        return


class RealtimePolicy(BaseSchedulerPolicy):
    """
    Realtime Policy
    """

    def __init__(self, task_manager: TaskFlowManager):
        super().__init__(task_manager)
        self._type = Constant.JOB_SCHED_POLICY_REALTIME

    # TODO(jidalong) RealtimePolicy
    def exec_task(self):
        return


class SchedulerPolicyHandlerFactory(ABC):
    """
    Scheduler Policy Handler Factory
    """

    def __init__(self, task_manager):
        self._policy_mapping = {
            Constant.JOB_SCHED_POLICY_PRIORITY:
                PriorityPolicy(task_manager),
            Constant.JOB_SCHED_POLICY_HIGH_RESPONSE_RATIO:
                HighResponseRatioPolicy(task_manager),
            Constant.JOB_SCHED_POLICY_SHORTEST_JOB_FIRST:
                ShortestJobFirstPolicy(task_manager),
            Constant.JOB_SCHED_POLICY_TIME_PRECEDENCE:
                TimePrecedencePolicy(task_manager),
            Constant.JOB_SCHED_POLICY_PERIODIC:
                PeriodicPolicy(task_manager),
            Constant.JOB_SCHED_POLICY_DEPENDENT:
                DependentPolicy(task_manager),
            Constant.JOB_SCHED_POLICY_BATCH:
                BatchPolicy(task_manager),
            Constant.JOB_SCHED_POLICY_REALTIME:
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
        else:
            raise ValueError(f"{name} is not a valid policy type")
