#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from wy_qcos.common import errors
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.db.utils.db_utils import create_db_session
from .task_manager import TaskFlowManager

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Task scheduler."""

    def __init__(self):
        """Init TaskScheduler."""
        self._task_manager = TaskFlowManager()
        self._policy_handler = PrioritySchedulingPolicy(self._task_manager)
        self._transpiler_manager = None
        self._driver_manager = None
        self._device_manager = None
        self._db_engine = None
        self._auto_scheduler = None
        self._flavor_manager = None
        self._device_group_manager = None

    def start_taskmanager(self):
        """Start TaskManager."""
        self._task_manager.start()

    def set_driver_manager(self, driver_manager):
        """Set driver manager.

        Args:
            driver_manager: driver manager
        """
        self._driver_manager = driver_manager
        self._task_manager.set_driver_manager(driver_manager)

    def get_task_manager(self):
        """Get task manager.

        Returns:
            task manager
        """
        return self._task_manager

    def get_driver_manager(self):
        """Get driver manager.

        Returns:
            driver manager
        """
        return self._driver_manager

    def set_transpiler_manager(self, transpiler_manager):
        """Set transpiler manager.

        Args:
            transpiler_manager: transpiler manager
        """
        self._transpiler_manager = transpiler_manager

    def get_transpiler_manager(self):
        """Get transpiler manager.

        Returns:
            transpiler manager
        """
        return self._transpiler_manager

    def set_device_manager(self, device_manager):
        """Set device manager.

        Args:
            device_manager: device manager
        """
        self._device_manager = device_manager
        self._task_manager.set_device_manager(device_manager)

    def set_db_engine(self, db_engine):
        """Set database engine.

        Args:
            db_engine: database engine
        """
        self._db_engine = db_engine

    def init_flavor_manager(self):
        """Initialize flavor manager (independent component).

        Must be called after set_db_engine. FlavorManager is a
        standalone component (parallel to UserManager), not part
        of the scheduler.
        """
        from wy_qcos.flavor.flavor_manager import FlavorManager

        self._flavor_manager = FlavorManager(self._db_engine)
        logger.info("Flavor manager initialized")

    def init_device_group_manager(self):
        """Initialize device group manager (independent component).

        Must be called after set_db_engine. DeviceGroupManager is
        a standalone component, not part of the scheduler.
        """
        from wy_qcos.device.device_group_manager import (
            DeviceGroupManager,
        )

        self._device_group_manager = DeviceGroupManager(self._db_engine)
        logger.info("Device group manager initialized")

    def init_auto_scheduler(self):
        """Initialize auto scheduler.

        Must be called after init_device_group_manager,
        init_flavor_manager, set_device_manager
        and set_db_engine. Reuses the standalone flavor_manager
        and device_group_manager instances.
        """
        from wy_qcos.scheduler import AutoScheduler

        self._auto_scheduler = AutoScheduler(
            device_manager=self._device_manager,
            task_manager=self._task_manager,
            flavor_manager=self._flavor_manager,
            device_group_manager=self._device_group_manager,
        )
        logger.info("Auto scheduler initialized")

    def get_auto_scheduler(self):
        """Get auto scheduler.

        Returns:
            auto scheduler instance
        """
        return self._auto_scheduler

    def get_flavor_manager(self):
        """Get flavor manager.

        Returns:
            flavor manager instance
        """
        return self._flavor_manager

    def get_device_group_manager(self):
        """Get device group manager.

        Returns:
            device group manager instance
        """
        return self._device_group_manager

    def get_device_manager(self):
        """Get device manager.

        Returns:
            device manager
        """
        return self._device_manager

    def submit(self, job_info, tags=None, extra_job_data_info={}):
        """Submit job to scheduler.

        Args:
            job_info: job info
            tags: prefect flow tags
            extra_job_data_info: extra job data info

        Returns:
            submitted job info, error messages
        """
        # check current all flows count exceed MAX_JOBS
        all_flows = self._task_manager.get_flow_runs_with_filters()
        all_flow_count = len(all_flows)
        if all_flow_count >= Constant.FLOW_LIMIT:
            return None, (
                f"Current flow count exceeds max flow limit: "
                f"{Constant.FLOW_LIMIT}"
            )

        # check current queued+running flows count exceed MAX_QUEUED_JOBS
        wait_states = self._task_manager.convert_to_prefect_states(
            Constant.PREFECT_WAIT_STATES
        )
        wait_states_flows = self._task_manager.get_flow_runs_with_filters(
            states=wait_states
        )
        wait_states_flow_count = len(wait_states_flows)
        # -1 means unlimited
        if (
            Config.DEFAULT.MAX_QUEUED_JOBS != -1
            and wait_states_flow_count >= Config.DEFAULT.MAX_QUEUED_JOBS
        ):
            return None, (
                f"Current queued job count exceeds "
                f"max queued job limit: {Config.DEFAULT.MAX_QUEUED_JOBS}"
            )

        # get driver info
        backend = job_info.backend
        device = self._device_manager.get_device(backend)
        if not device:
            err_msg = f"Backend: '{backend}' is not found"
            logger.error(err_msg)
            return None, f"Execute work flow failed: {err_msg}"
        if not device.enable:
            err_msg = f"Backend driver: {backend} is disabled"
            logger.error(err_msg)
            return None, f"Execute work flow failed: {err_msg}"

        pool_wait_states_flows_count = len(
            self._task_manager.get_flow_runs_with_filters(
                states=wait_states,
                pool_name=f"{Constant.WORK_POOL_DEVICE_PREFIX}{backend}",
            )
        )
        device_max_queued_jobs = device.get_max_queued_jobs()

        # Check device queue limit (only if max_queued_jobs is set to >= 0)
        if device_max_queued_jobs == 0:
            if pool_wait_states_flows_count > 0:
                return None, "Device does not allow queued jobs"
        elif (
            device_max_queued_jobs > 0
            and pool_wait_states_flows_count >= device_max_queued_jobs
        ):
            return None, (
                f"Current queued job count exceeds "
                f"max queued job limit: {device_max_queued_jobs}"
            )

        driver = device.get_driver()
        driver_module_name = driver.get_module_name()
        driver_class_name = driver.get_class_name()
        driver_package_paths = driver.get_package_paths()

        # get transpiler options
        transpiler_module_name = None
        transpiler_class_name = None
        transpiler_name = driver.get_transpiler()
        transpiler = self._transpiler_manager.get_transpiler(transpiler_name)
        if transpiler:
            transpiler_module_name = transpiler.get_module_name()
            transpiler_class_name = transpiler.get_class_name()

        # execute task
        try:
            deployment_name = backend
            deployment = self._task_manager.get_deployment(deployment_name)
            job_json_info = {}
            job_json_info["data"] = job_info.model_dump()
            job_json_info["data"].update(extra_job_data_info)
            job_json_info["driver"] = {
                "module_name": driver_module_name,
                "class_name": driver_class_name,
                "package_paths": driver_package_paths,
            }
            job_json_info["transpiler"] = {
                "module_name": transpiler_module_name,
                "class_name": transpiler_class_name,
            }
            job_json_info["device"] = {"configs": device.get_configs()}
            job_json_info["global"] = {"configs": Config.get_configs()}

            flow_run_id = self._policy_handler.exec_task(
                deployment, job_json_info, tags=tags
            )
            res = {"flow_run_id": flow_run_id}
            return res, None
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
            raise errors.WorkFlowError(e)

    def submit_manage_job(self, job_info):
        """Submit manage job to scheduler.

        Args:
            job_info: job info

        Returns:
            submitted job info, error messages
        """
        # check current all flows count exceed MAX_JOBS
        all_flows = self._task_manager.get_flow_runs_with_filters()
        all_flow_count = len(all_flows)
        if all_flow_count >= Constant.FLOW_LIMIT:
            return None, (
                f"Current job count exceeds max flow limit: "
                f"{Constant.FLOW_LIMIT}"
            )

        # check current queued+running flows count exceed MAX_QUEUED_JOBS
        wait_states = self._task_manager.convert_to_prefect_states(
            Constant.PREFECT_WAIT_STATES
        )
        wait_states_flows = self._task_manager.get_flow_runs_with_filters(
            states=wait_states
        )
        wait_states_flow_count = len(wait_states_flows)
        # -1 means unlimited
        if (
            Config.DEFAULT.MAX_QUEUED_JOBS != -1
            and wait_states_flow_count >= Config.DEFAULT.MAX_QUEUED_JOBS
        ):
            return None, (
                f"Current running+queued job count exceeds "
                f"max queued job limit: {Config.DEFAULT.MAX_QUEUED_JOBS}"
            )

        # get driver info
        backend = job_info.device_name
        device = self._device_manager.get_device(backend)
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
        driver_package_paths = driver.get_package_paths()

        # execute task
        try:
            deployment_name = f"{Constant.WORK_POOL_MGR_PREFIX}{backend}"
            deployment = self._task_manager.get_deployment(deployment_name)
            device_mgr_info = {}
            device_mgr_info["device_name"] = job_info.device_name
            device_mgr_info["method"] = job_info.method
            device_mgr_info["data"] = job_info.model_dump()
            device_mgr_info["driver"] = {
                "module_name": driver_module_name,
                "class_name": driver_class_name,
                "package_paths": driver_package_paths,
            }
            device_mgr_info["device"] = {"configs": device.get_configs()}
            device_mgr_info["redis"] = {
                "ip": self._device_manager.config.REDIS.REDIS_SERVER_IP,
                "port": self._device_manager.config.REDIS.REDIS_SERVER_PORT,
            }
            device_mgr_info["global"] = {"configs": Config.get_configs()}
            success, details = self._policy_handler.exec_manage_task(
                deployment, device_mgr_info
            )
            if success:
                return details
            else:
                logger.error(f"exec manage task error details: {details}")
                raise errors.WorkFlowError(f"exec error details: {details}")
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
            raise errors.WorkFlowError(e)

    def delete_flows(self, flow_run_ids):
        """Delete flows.

        Args:
            flow_run_ids: flow run id list

        Returns:
            flow list
        """
        flow_list = self._task_manager.delete_flow_runs(flow_run_ids)
        return flow_list

    def cancel_flows(self, flow_run_ids, tags=None):
        """Cancel jobs.

        Args:
            flow_run_ids: flow run id list
            tags: prefect flow tags

        Returns:
            flow list
        """
        flow_list = self._task_manager.cancel_flow_runs(
            flow_run_ids, tags=tags
        )
        return flow_list

    def update_flow(
        self,
        flow_run_id,
        name=None,
        parameters=None,
        variables=None,
    ):
        """Update job.

        Args:
            flow_run_id: flow run id
            name: job name (Default value = None)
            parameters: job parameters (Default value = None)
            variables: job variables

        Returns:
            if flow exists
        """
        res = None
        err_msg = None
        # 1. Get flow run
        flow_run = self._task_manager.get_flow_run(flow_run_id)
        if flow_run is None:
            err_msg = f"Flow: '{flow_run_id}' is not found"
            return None, f"Execute update job failed: {err_msg}"
        job_priority = parameters.get("job_priority")
        # 2. Get flow parameters
        flow_parameters = flow_run.parameters
        job_json_info = flow_parameters["job_info"]
        if job_json_info["data"]["job_priority"] == job_priority:
            res, err_msg = self._task_manager.update_flow(
                flow_run_id, name, parameters, variables
            )
            if res is False:
                return res, err_msg
        else:
            # 3. Delete task
            self._task_manager.delete_flow_runs([flow_run_id])
            # 4. Update parameters and resubmit the task
            job_json_info["data"]["job_priority"] = job_priority
            backend = job_json_info["data"]["backend"]
            try:
                deployment_name = backend
                deployment = self._task_manager.get_deployment(deployment_name)
                device = self._device_manager.get_device(backend)
                device_name = device.get_name()
                tags = [f"{device_name}"]
                flow_run_id = self._policy_handler.exec_task(
                    deployment, job_json_info, tags
                )
            except errors.WorkFlowError as e:
                logger.error(f"Prefect execute update flow error: {str(e)}")
                raise errors.WorkFlowError(e)
        # 5. Get flow run again
        flow_run = self._task_manager.get_flow_run(flow_run_id, tags)
        if flow_run is None:
            err_msg = f"Flow: '{flow_run_id}' not found after update"
            return None, f"Execute update flow_run failed: {err_msg}"
        if flow_run.parameters is None:
            err_msg = f"Flow: '{flow_run_id}' parameters are None"
            return None, f"Execute update flow_run failed: {err_msg}"
        response_info = flow_run.parameters["job_info"]["data"]
        response_info["job_status"] = Constant.JOB_STATUS_QUEUED
        response_info["flow_run_id"] = flow_run_id
        return response_info, None

    def process_unfinished_jobs(self):
        """Process unfinished jobs in database.

        Checks all jobs in database. This handles jobs that may have been
        interrupted or left in intermediate states during system restart.
        """
        if self._db_engine is None:
            logger.warning(
                "Database engine not initialized, skipping unfinished jobs"
            )
            return

        try:
            with create_db_session(self._db_engine) as db_session:
                job_repo = JobRepository(db_session)
                success, error, job_records = job_repo.get_jobs()

                if not success or not job_records:
                    if error:
                        logger.warning(f"Failed to fetch jobs: {error}")
                    return

                # Define intermediate job states that will be set to FAILED
                set_to_failed_states = {
                    Constant.JOB_STATUS_UNKNOWN,
                    Constant.JOB_STATUS_CANCELLING,
                }

                # Process unfinished jobs
                unfinished_count = 0
                for job_record in job_records:
                    if job_record.job_status in set_to_failed_states:
                        logger.info(
                            f"Setting unfinished job {job_record.id} "
                            f"(status: {job_record.job_status}) to FAILED"
                        )
                        job_record.job_status = Constant.JOB_STATUS_FAILED
                        flow_run_id = job_record.flow_run_id
                        if flow_run_id:
                            self._task_manager.cancel_flow_runs([flow_run_id])
                        unfinished_count += 1

                # Commit changes if any jobs were updated
                if unfinished_count > 0:
                    try:
                        db_session.commit()
                        logger.info(
                            f"Processed {unfinished_count} unfinished jobs, "
                            f"set status to FAILED"
                        )
                    except Exception as commit_err:
                        db_session.rollback()
                        logger.error(
                            f"Failed to commit unfinished jobs update: "
                            f"{str(commit_err)}"
                        )
        except Exception as e:
            logger.error(f"Error processing unfinished jobs: {str(e)}")

    def process_callbacks(self):
        """Process unfinished callbacks from database.

        Reads job records where callbacks are not empty and
        is_callback_success is False, then executes the callbacks.
        Updates is_callback_success to True on successful execution.
        """
        if self._db_engine is None:
            logger.warning(
                "Database engine not initialized, skipping callbacks"
            )
            return

        try:
            with create_db_session(self._db_engine) as db_session:
                job_repo = JobRepository(db_session)
                success, error, job_records = job_repo.get_jobs()

                if not success or not job_records:
                    if error:
                        logger.warning(f"Failed to fetch jobs: {error}")
                    return

                # Filter jobs with callbacks and failed callback success
                for job_record in job_records:
                    job_status = job_record.job_status
                    backend = job_record.backend
                    callbacks = job_record.callbacks
                    is_callback_success = job_record.is_callback_success
                    results = job_record.results

                    # Skip if no callbacks configured
                    if not callbacks:
                        continue

                    # Execute callbacks if needed
                    if not is_callback_success:
                        logger.info(
                            f"Processing callbacks for job: {job_record.id}"
                        )
                        user = {
                            "project_id": str(job_record.project_id),
                            "user_id": str(job_record.user_id),
                        }
                        try:
                            callback_success = Library.job_callback(
                                str(job_record.id),
                                job_status,
                                backend,
                                results,
                                callbacks,
                                user=user,
                            )
                            # Update is_callback_success
                            job_record.is_callback_success = callback_success
                            db_session.commit()
                            db_session.refresh(job_record)
                        except Exception as e:
                            logger.error(
                                f"Error processing callbacks for "
                                f"job {job_record.id}: {str(e)}"
                            )
        except Exception as e:
            logger.error(f"Error processing callbacks: {str(e)}")


class PrioritySchedulingPolicy:
    """Priority Scheduling Policy."""

    def __init__(self, task_manager: TaskFlowManager):
        self._task_manager = task_manager

    def exec_task(self, deployment, job_info, tags=None):
        """Execute task.

        Args:
            deployment: deployment info
            job_info: job info
            tags: prefect flow tags

        Returns:
            flow run id
        """
        priority = job_info["data"]["job_priority"]
        backend = job_info["data"]["backend"]

        deployment_id = deployment["deploy_id"]
        work_queue_name = (
            f"{Constant.WORK_POOL_DEVICE_PREFIX}{backend}_{priority}"
        )
        flow_run_id = self._task_manager.run_flow(
            deployment_id,
            {"job_info": job_info},
            tags=tags,
            work_queue_name=work_queue_name,
        )
        return flow_run_id

    def exec_manage_task(self, deployment, device_mgr_info):
        """Execute task.

        Args:
            deployment: deployment info
            device_mgr_info: device_mgr_info

        Returns:
            job uuid
        """
        deployment_id = deployment["deploy_id"]
        work_queue_name = "default"
        success, details = self._task_manager.run_manage_task_flow(
            deployment_id,
            {"device_mgr_info": device_mgr_info},
            work_queue_name=work_queue_name,
        )
        return success, details
