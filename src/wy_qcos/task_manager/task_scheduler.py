#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import asyncio
import logging
from abc import ABC

from prefect import exceptions as prefect_exceptions

from wy_qcos.common import errors
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from .task_manager import TaskFlowManager

logger = logging.getLogger(__name__)


class TaskScheduler(ABC):
    """Task scheduler."""

    def __init__(self):
        """Init TaskScheduler."""
        self._task_manager = TaskFlowManager()
        self._policy_handler = TimePrecedencePolicy(self._task_manager)
        self.driver_manager = None
        self.transpiler_manager = None
        self.device_manager = None

    def start_taskmanager(self):
        """Start TaskManager."""
        self._task_manager.start()

    def set_driver_manager(self, driver_manager):
        """Set driver manager.

        Args:
            driver_manager: driver manager
        """
        self.driver_manager = driver_manager
        self._task_manager.set_driver_manager(driver_manager)

    def get_driver_manager(self):
        """Get driver manager.

        Returns:
            driver manager
        """
        return self.driver_manager

    def set_transpiler_manager(self, transpiler_manager):
        """Set transpiler manager.

        Args:
            transpiler_manager: transpiler manager
        """
        self.transpiler_manager = transpiler_manager

    def get_transpiler_manager(self):
        """Get transpiler manager.

        Returns:
            transpiler manager
        """
        return self.transpiler_manager

    def set_device_manager(self, device_manager):
        """Set device manager.

        Args:
            device_manager: device manager
        """
        self.device_manager = device_manager
        self._task_manager.set_device_manager(device_manager)

    def get_device_manager(self):
        """Get device manager.

        Returns:
            device manager
        """
        return self.device_manager

    def add(self, job_info, tags=None):
        """Add job to scheduler.

        Args:
            job_info: job info
            tags: prefect flow tags

        Returns:
            added job info, error messages
        """
        # check Job UUID
        if job_info.job_id:
            exist = self.has_job(job_info.job_id)
            if exist:
                return None, f"Job uuid is already existed: {job_info.job_id}"

        # check current all flows count exceed MAX_JOBS
        all_flows = self._task_manager.get_flow_runs_with_filters()
        all_flow_count = len(all_flows)
        if all_flow_count >= Config.MAX_JOBS:
            return None, (
                f"Current job count exceeds max job limit: {Config.MAX_JOBS}"
            )
        if all_flow_count >= Constant.FLOW_LIMIT:
            return None, (
                f"Current job count exceeds max flow limit: "
                f"{Constant.FLOW_LIMIT}"
            )
        # check max jobs of virtual_instance when ENABLE_VIRT is True
        if Config.ENABLE_VIRT and tags is not None:
            virtual_instance_flows = (
                self._task_manager.get_flow_runs_with_filters(tags=tags)
            )
            virtual_instance_flows_count = len(virtual_instance_flows)
            if (
                virtual_instance_flows_count
                >= Config.MAX_JOBS_PER_VIRTUAL_INSTANCE
            ):
                return (
                    None,
                    "The number of current jobs "
                    f"({virtual_instance_flows_count}) has exceeded the "
                    "maximum quota limit "
                    f"({Config.MAX_JOBS_PER_VIRTUAL_INSTANCE}) for this "
                    "instance. "
                    "Please delete some existing jobs before creating "
                    "new ones",
                )

        # check current queued+running flows count exceed MAX_QUEUED_JOBS
        wait_states = self._task_manager.convert_to_prefect_states(
            Constant.PREFECT_WAIT_STATES
        )
        wait_states_flows = self._task_manager.get_flow_runs_with_filters(
            states=wait_states
        )
        wait_states_flow_count = len(wait_states_flows)
        if wait_states_flow_count >= Config.MAX_QUEUED_JOBS:
            return None, (
                f"Current running+queued job count exceeds "
                f"max queued job limit: {Config.MAX_QUEUED_JOBS}"
            )

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
            flow_info = self._task_manager.get_flow_info_by_backend(backend)
            job_json_info = {}
            job_json_info["data"] = job_info.model_dump()
            job_json_info["driver"] = {
                "module_name": driver_module_name,
                "class_name": driver_class_name,
            }
            job_json_info["transpiler"] = {
                "module_name": transpiler_module_name,
                "class_name": transpiler_class_name,
            }
            job_json_info["device"] = {"configs": device.get_configs()}

            job_id = self._policy_handler.exec_task(
                flow_info, job_json_info, tags=tags
            )
            res = {"job_id": job_id}
            return res, None
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
            raise errors.WorkFlowError(e)

    def get_result_by_id(self, job_id, tags=None):
        """Get result by job id.

        Args:
            job_id: job id
            tags: prefect flow tags

        Returns:
            flow info
        """
        try:
            state, parameters, results, error_message = (
                self._task_manager.get_task_flow_result(job_id, tags)
            )
            state = self._task_manager.convert_to_qcos_state(state)
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
        """Check if flow exists.

        Args:
            job_id: job id

        Returns:
            if flow exists
        """
        return self._task_manager.has_flow(job_id)

    def get_jobs(self, tags=None):
        """Get job list.

        Args:
            tags: prefect flow tags

        Returns:
            job list
        """
        try:
            flow_list = self._task_manager.get_task_flow_list(tags=tags)
            for flow in flow_list:
                flow["job_status"] = self.get_job_status(
                    flow["state"], flow["results"], flow["parameters"]
                )
            return flow_list, None
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
            raise errors.WorkFlowError(e)

    def delete_jobs(self, ids, tags=None):
        """Delete jobs.

        Args:
            ids: job id list
            tags: prefect flow tags

        Returns:
            flow list
        """
        flow_list = self._task_manager.delete_task_flow_run(ids, tags=tags)
        for flow in flow_list:
            flow["job_status"] = self.get_job_status(flow["state"], None, None)
        return flow_list

    def cancel_jobs(self, ids, tags=None):
        """Cancel jobs.

        Args:
            ids: job id list
            tags: prefect flow tags

        Returns:
            flow list
        """
        flow_list = self._task_manager.cancel_task_flow_run(ids, tags=tags)
        for flow in flow_list:
            flow["job_status"] = self.get_job_status(flow["state"], None, None)
        return flow_list

    def update_job(
        self,
        job_id,
        name=None,
        parameters=None,
        variables=None,
        tags=None,
    ):
        """Update job.

        Args:
            job_id: job id
            name: job name (Default value = None)
            parameters: job parameters (Default value = None)
            variables: job variables
            tags: prefect flow tags

        Returns:
            if flow exists
        """
        res = None
        err_msg = None
        # 1 Get flow run
        flow_run = self._task_manager.get_task_flow_run(job_id, tags)
        if flow_run is None:
            err_msg = f"Job: '{job_id}' is not found"
            return None, f"Execute update job failed: {err_msg}"
        job_priority = parameters.get("job_priority")
        # 2 Get flow parameters
        flow_parameters = flow_run.parameters
        job_json_info = flow_parameters["job_info"]
        if job_json_info["data"]["job_priority"] == job_priority:
            res, err_msg = self._task_manager.update_flow(
                job_id, name, parameters, variables
            )
            if res is False:
                return res, err_msg
        else:
            # 3 Delete task
            self._task_manager.delete_task_flow_run([job_id], tags)
            # 4 Update parameters and resubmit the task
            job_json_info["data"]["job_priority"] = job_priority
            backend = job_json_info["data"]["backend"]
            try:
                flow_info = self._task_manager.get_flow_info_by_backend(
                    backend
                )
                device = self.device_manager.get_device(backend)
                device_name = device.get_name()
                tags = [f"{device_name}"]
                job_id = self._policy_handler.exec_task(
                    flow_info, job_json_info, tags
                )
            except errors.WorkFlowError as e:
                logger.error(f"Prefect execute update flow error: {str(e)}")
                raise errors.WorkFlowError(e)
        # 5 Get flow run again
        flow_run = self._task_manager.get_task_flow_run(job_id)
        response_info = flow_run.parameters["job_info"]["data"]
        response_info["job_status"] = Constant.JOB_STATUS_QUEUED
        return response_info, None

    def run_callbacks(self, data, callbacks):
        """Run callbacks for job.

        Args:
            data: data to send
            callbacks: callbacks
        """
        return self._task_manager.run_callbacks(data, callbacks)

    def process_callbacks(self):
        """Process unfinished callbacks."""
        flow_runs = self._task_manager.get_flow_runs_with_filters()
        for flow_run in flow_runs:
            # TODO (zhaoyi): improve callback when restart
            asyncio.run(
                Library.job_callback(
                    None, flow_run, flow_run.state, results=None
                )
            )

    @staticmethod
    def get_job_status(job_status, flow_results, flow_parameters):
        """Get job status by combining flow state and user defined task status.

        Args:
            job_status: job status
            flow_results: flow results
            flow_parameters: parameters

        Returns:
            job status
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
                    if _flow_results_status == Constant.JOB_STATUS_RUNNING:
                        flow_results_status = _flow_results_status
                        break
                    if _flow_results_status == Constant.JOB_STATUS_FAILED:
                        flow_results_status = _flow_results_status
                        break

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


class TimePrecedencePolicy(ABC):
    """Time Precedence Policy."""

    def __init__(self, task_manager: TaskFlowManager):
        self._task_manager = task_manager

    def exec_task(self, flow_info, job_info, tags=None):
        """TimePrecedencePolicy execute task.

        Args:
            flow_info: flow info
            job_info: job info
            tags: prefect flow tags

        Returns:
            job uuid
        """
        priority = self.calculate_priority(job_info)
        pool_name = None
        if tags is not None:
            pool_name = tags[0]

        job_deploy_id = self._task_manager.deploy_task_flow(
            flow_info["deploy_name"],
            pool_name,
            priority,
            flow_info["deploy_flow_func"],
            flow_info["deploy_flow_path"],
        )
        job_run_id = self._task_manager.run_task_flow(
            job_deploy_id, {"job_info": job_info}, tags=tags
        )
        return job_run_id

    def calculate_priority(self, job_info):
        """Calculate priority.

        Args:
            job_info: job info

        Returns:
            job priority
        """
        return job_info["data"]["job_priority"]
