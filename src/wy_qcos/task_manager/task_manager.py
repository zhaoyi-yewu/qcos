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

import asyncio
import json
import logging
import multiprocessing
import os
import setproctitle
import threading
from time import sleep
from pathlib import Path
from typing import Any

import redis
from prefect import get_client, settings as prefect_settings
from prefect.client.schemas.actions import WorkPoolCreate
from prefect.client.schemas.objects import WorkerStatus, StateType
from prefect.client.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterName,
    FlowRunFilterState,
    FlowRunFilterTags,
    FlowFilter,
    FlowFilterName,
)
from prefect.exceptions import ObjectNotFound
from prefect.states import State
from prefect.workers import ProcessWorker

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import Library
from wy_qcos.engine.job_engine import job_flow
from wy_qcos.engine.device_mgr_engine import device_manager_flow
from wy_qcos.engine.device_monitor_engine import device_monitor_flow

logger = logging.getLogger(__name__)


class TaskFlowManager:
    """Task manager based on prefect framework."""

    def __init__(self):
        """Init TaskFlowManager."""
        self._client = None
        self._sync_client = None
        self.loop = None
        self.worker_status = False
        self.driver_manager = None
        self.device_manager = None
        self.deployments = {}
        self.redis_instance = redis.Redis(
            host=Config.REDIS.REDIS_SERVER_IP,
            port=Config.REDIS.REDIS_SERVER_PORT,
            decode_responses=True,
        )

    @staticmethod
    def convert_to_qcos_state(state):
        """Convert to qcos state.

        Args:
            state: prefect state

        Returns:
            qcos state.
        """
        _state = state.upper()
        if _state == Constant.PREFECT_STATE_CRASHED:
            return Constant.JOB_STATUS_FAILED
        elif _state in [
            Constant.PREFECT_STATE_SCHEDULED,
            Constant.PREFECT_STATE_PENDING,
            Constant.PREFECT_STATE_LATE,
        ]:
            return Constant.JOB_STATUS_QUEUED
        else:
            return _state

    @staticmethod
    def convert_to_prefect_states(states):
        """Convert qcos states to prefect states.

        Args:
            states: qcos states list

        Returns:
            prefect states list.
        """
        prefect_states = []
        for state in states:
            state = state.upper()
            new_state = None
            if state == Constant.PREFECT_STATE_RUNNING:
                new_state = StateType.RUNNING
            elif state == Constant.PREFECT_STATE_SCHEDULED:
                new_state = StateType.SCHEDULED
            elif state == Constant.PREFECT_STATE_PENDING:
                new_state = StateType.PENDING
            elif state == Constant.PREFECT_STATE_FAILED:
                new_state = StateType.FAILED
            elif state == Constant.PREFECT_STATE_COMPLETED:
                new_state = StateType.COMPLETED
            elif state == Constant.PREFECT_STATE_CRASHED:
                new_state = StateType.CRASHED
            elif state == Constant.PREFECT_STATE_CANCELLING:
                new_state = StateType.CANCELLING
            elif state == Constant.PREFECT_STATE_CANCELLED:
                new_state = StateType.CANCELLED
            elif state == Constant.PREFECT_STATE_PAUSED:
                new_state = StateType.PAUSED
            prefect_states.append(new_state)
        return prefect_states

    def generate_deployment_configs(self, device_names):
        """Generate deployment configs.

        Args:
            device_names: device names

        Returns:
            deployment configs
        """
        default_priority = Constant.DEFAULT_JOB_PRIORITY
        deployment_configs = {}
        devices = self.device_manager.get_devices()
        default_python_bin = "python3"
        python_bin = default_python_bin
        os.environ.get("PYTHONPATH", None)
        for device_name in device_names:
            driver_name = None
            device = devices.get(device_name, None)
            if device:
                driver_name = device.get_driver().get_name()
            python_bin, python_path_env = Library.get_driver_venv(
                driver_name, Config.DEFAULT.VENV_DIR, add_default_env=True
            )

            deployment_configs[device_name] = {
                "python_bin": python_bin,
                "pool_name": device_name,
                "queue_name": f"{device_name}_{default_priority}",
                "path": "../engine/job_engine.py",
                "flow_name": job_flow.__name__,
                "command": f"{python_bin} -m prefect.engine",
                "env": python_path_env,
            }

            device = self.device_manager.get_devices().get(device_name)
            enable_device_monitor = device.get_driver().enable_device_monitor
            if enable_device_monitor:
                deployment_configs[f"{device_name}_monitor"] = {
                    "python_bin": python_bin,
                    "pool_name": f"{device_name}_monitor",
                    "queue_name": "default",
                    "path": "../engine/device_monitor_engine.py",
                    "flow_name": device_monitor_flow.__name__,
                    "command": f"{python_bin} -m prefect.engine",
                    "env": python_path_env,
                }
            enable_device_mgr = device.get_driver().enable_device_mgr
            if enable_device_mgr:
                deployment_configs[f"{device_name}_mgr"] = {
                    "python_bin": python_bin,
                    "pool_name": f"{device_name}_mgr",
                    "queue_name": "default",
                    "path": "../engine/device_mgr_engine.py",
                    "flow_name": device_manager_flow.__name__,
                    "command": f"{python_bin} -m prefect.engine",
                    "env": python_path_env,
                }

        return deployment_configs

    def start(self):
        """Create work pools, queues and start workers."""
        prefect_configs = TaskFlowManager.get_prefect_configs()
        with prefect_settings.temporary_settings(updates=prefect_configs):
            self._client = get_client()
            self._sync_client = get_client(sync_client=True)
            self.loop = asyncio.new_event_loop()

            self.check_connection()
            device_names = self.device_manager.get_devices().keys()

            # create resources
            if device_names:
                self.loop.run_until_complete(
                    self.create_pools(pool_names=device_names)
                )

            monitor_devices = [
                device.get_name() + "_monitor"
                for device in self.device_manager.get_devices().values()
                if device.get_driver().enable_device_monitor
            ]
            if monitor_devices:
                self.loop.run_until_complete(
                    self.create_pools(pool_names=monitor_devices)
                )

            manager_devices = [
                device.get_name() + "_mgr"
                for device in self.device_manager.get_devices().values()
                if device.get_driver().enable_device_monitor
            ]
            if manager_devices:
                self.loop.run_until_complete(
                    self.create_pools(pool_names=manager_devices)
                )

            if device_names:
                self.loop.run_until_complete(
                    self.create_queues(queue_names=device_names)
                )
            # delete old monitor flow
            self.delete_task_flow_by_name("device-monitor-flow")

            deployment_configs = self.generate_deployment_configs(device_names)
            self.deployments = self.loop.run_until_complete(
                self.create_deployments(deployment_configs)
            )
            self.kill_workers()
            self.start_workers()
            self.loop.run_until_complete(self.wait_workers())
            self.loop.run_until_complete(self.process_aggregation_job())
            self.run_device_monitor()

    def set_driver_manager(self, driver_manager):
        """Set driver manager.

        Args:
            driver_manager: driver manager
        """
        self.driver_manager = driver_manager

    def set_device_manager(self, device_manager):
        """Set device manager.

        Args:
            device_manager: device manager
        """
        self.device_manager = device_manager

    def check_connection(self):
        """Check connection to prefect server."""

        def is_connected():
            try:
                print(
                    f"Check connection to prefect api: "
                    f"{Config.PREFECT.PREFECT_API_URL} ... "
                )
                hello = self._sync_client.hello()
                if hello and hello.status_code == HttpCode.SUCCESS_OK:
                    return True, None, None
                return False, "Connection failed", None
            except Exception as e:
                return False, str(e), None

        success, err_msg, _ = Library.loop_with_timeout(is_connected, 60, 5)
        if not success:
            raise TimeoutError("Connection to prefect server timeout")

    async def create_pools(self, pool_names):
        """Create all work pools, each device has own work pools.

        Args:
            pool_names: pool names
        """
        logger.info(f"create_pools: {', '.join(pool_names)}")
        create_workpools = [
            self.create_pool(pool_name, Constant.DEFAULT_POOL_CONCURRENCY)
            for pool_name in pool_names
        ]
        return await asyncio.gather(*create_workpools)

    async def create_pool(self, pool_name, concurrency_limit=None):
        """Create work pool by prefect client.

        Args:
            pool_name: work pool name, using device name
            concurrency_limit: concurrency limit
        """
        pools = await self._client.read_work_pools()
        if not any(pool.name == pool_name for pool in pools):
            await self._client.create_work_pool(
                work_pool=WorkPoolCreate(
                    name=pool_name,
                    type=Constant.DEFAULT_JOB_POOL_TYPE,
                    concurrency_limit=concurrency_limit,
                )
            )

    async def create_queues(self, queue_names):
        """Create all work queues under work pool.

        each priority has own work queue.

        Args:
            queue_names: queue names
        """
        logger.info(f"create_queues: {', '.join(queue_names)}")
        queues = await self._client.read_work_queues()
        for pool_name in queue_names:
            for priority in range(1, Constant.MAX_JOB_PRIORITY + 1):
                queue_name = f"{pool_name}_{priority}"
                if not any(queue.name == queue_name for queue in queues):
                    await self._client.create_work_queue(
                        name=queue_name,
                        work_pool_name=pool_name,
                        priority=priority,
                        concurrency_limit=Constant.DEFAULT_POOL_CONCURRENCY,
                    )

    async def create_deployments(self, deployment_configs):
        """Create deployment by prefect client.

        Args:
            deployment_configs: deployment configs
        """
        logger.info(
            f"create_deployments: {', '.join(deployment_configs.keys())}"
        )
        deployments = {}
        for deployment_name, deployment_config in deployment_configs.items():
            flow_name = deployment_config["flow_name"]
            path = deployment_config["path"]
            pool_name = deployment_config["pool_name"]
            queue_name = deployment_config["queue_name"]
            command = deployment_config["command"]
            env = deployment_config["env"]
            flow = await job_flow.from_source(
                source=Path(__file__).parent,
                entrypoint=f"{path}:{flow_name}",
            )
            deploy_id = await flow.deploy(
                name=deployment_name,
                work_pool_name=pool_name,
                work_queue_name=queue_name,
                job_variables={"command": command},
                ignore_warnings=True,
                print_next_steps=False,
            )
            deployments[deployment_name] = {
                "deploy_id": str(deploy_id),
                "env": env,
            }
        return deployments

    def get_deployment(self, deployment_name):
        """Get deployment.

        Args:
            deployment_name: deployment name
        """
        return self.deployments.get(deployment_name, None)

    def kill_workers(self):
        """Kill workers."""
        logger.info("Kill existing prefect workers")
        regex_list = [r"\[prefect\]", r"prefect.engine"]
        process_list = Library.get_processes(regex_list)
        Library.kill(process_list, force=True)

    def start_workers(self):
        """Start workers using multiprocessing."""
        logger.info("Start prefect workers")
        device_names = self.device_manager.get_devices().keys()
        for device_name in device_names:
            pool_name = device_name
            deployment_name = device_name
            process_name = f"process-{pool_name}"
            concurrency_limit = Constant.DEFAULT_POOL_CONCURRENCY
            deployment = self.get_deployment(deployment_name)
            if deployment:
                env = deployment["env"]
                pythonpath = env.get("PYTHONPATH", None)
                if pythonpath:
                    os.environ["PYTHONPATH"] = pythonpath

            # start job worker process
            job_worker_process = multiprocessing.Process(
                target=self.start_work,
                args=(process_name, pool_name, concurrency_limit),
                name=process_name,
            )
            job_worker_process.daemon = True
            job_worker_process.start()
            logger.info(
                f"Started Prefect Worker process: {process_name} "
                f"for pool: {pool_name}"
            )
            # start device monitor process
            device = self.device_manager.get_devices().get(pool_name)
            enable_device_monitor = device.get_driver().enable_device_monitor
            if enable_device_monitor:
                device_monitor_process = multiprocessing.Process(
                    target=self.start_device_monitor_work,
                    args=(process_name, pool_name, concurrency_limit),
                    name=process_name,
                )
                device_monitor_process.daemon = True
                device_monitor_process.start()
                logger.info(
                    f"Started Prefect Worker process: {process_name}_monitor "
                    f"for pool: {pool_name}_monitor"
                )

            enable_device_mgr = device.get_driver().enable_device_mgr
            if enable_device_mgr:
                device_mgr_process = multiprocessing.Process(
                    target=self.start_device_mgr_work,
                    args=(process_name, pool_name, concurrency_limit),
                    name=process_name,
                )
                device_mgr_process.daemon = True
                device_mgr_process.start()
                logger.info(
                    f"Started Prefect Worker process: {process_name}_mgr "
                    f"for pool: {pool_name}_mgr"
                )

    def run_device_monitor(self):
        """Run device monitor by prefect."""
        devices = self.device_manager.get_devices().values()

        for device in devices:
            # registry deploy
            deployment = self.deployments.get(f"{device.get_name()}_monitor")
            if deployment:
                deploy_id = deployment.get("deploy_id")
                # create flow run by deploy
                device_monitor_info = {}
                driver = device.get_driver()
                driver_module_name = driver.get_module_name()
                driver_class_name = driver.get_class_name()
                driver_package_paths = driver.get_package_paths()
                device_monitor_info["driver"] = {
                    "module_name": driver_module_name,
                    "class_name": driver_class_name,
                    "package_paths": driver_package_paths,
                }
                device_monitor_info["device"] = {
                    "configs": device.get_configs()
                }
                device_monitor_info["global"] = {
                    "configs": Config.get_configs()
                }
                device_monitor_info["name"] = device.get_name()
                device_monitor_info["redis"] = {
                    "ip": self.device_manager.config.REDIS.REDIS_SERVER_IP,
                    "port": self.device_manager.config.REDIS.REDIS_SERVER_PORT,
                }

                args = {"device_monitor_info": device_monitor_info}
                self._sync_client.create_flow_run_from_deployment(
                    name=Constant.DEVICE_MONITOR_PREFIX
                    + str(device.get_name()),
                    deployment_id=deploy_id,
                    parameters=args,
                )

    @staticmethod
    def get_prefect_configs():
        """Set prefect configs."""
        prefect_configs = {}
        settings = [
            "PREFECT_SERVER_DATABASE_CONNECTION_URL",
            "PREFECT_API_URL",
            "PREFECT_WORKER_HEARTBEAT_SECONDS",
            "PREFECT_WORKER_QUERY_SECONDS",
            "PREFECT_WORKER_PREFETCH_SECONDS",
            "PREFECT_LOCAL_STORAGE_PATH",
            "PREFECT_LOGGING_LEVEL",
        ]

        for setting in settings:
            prefect_configs[getattr(prefect_settings, setting)] = getattr(
                Config.PREFECT, setting
            )
        prefect_settings.PREFECT_WORKER_ENABLE_CANCELLATION = True

        return prefect_configs

    @staticmethod
    def start_work(process_name, pool_name, concurrency_limit):
        """Start worker by prefect client.

        Args:
            process_name: process name
            pool_name: work pool name
            concurrency_limit: max num of jobs running at the same time
        """
        # get prefect configs
        prefect_configs = TaskFlowManager.get_prefect_configs()

        # start process worker
        with prefect_settings.temporary_settings(updates=prefect_configs):
            worker = ProcessWorker(
                name=process_name,
                work_pool_name=pool_name,
                work_queues=[
                    f"{pool_name}_{str(i)}"
                    for i in range(1, Constant.MAX_JOB_PRIORITY + 1)
                ],
                limit=concurrency_limit,
            )
            setproctitle.setproctitle(f"[prefect] {process_name}")
            asyncio.run(worker.start())

    @staticmethod
    def start_device_monitor_work(process_name, pool_name, concurrency_limit):
        """Start device monitor worker by prefect client.

        Args:
            process_name: process name
            pool_name: work pool name
            concurrency_limit: max num of jobs running at the same time
        """
        # get prefect configs
        prefect_configs = TaskFlowManager.get_prefect_configs()

        # start process worker
        with prefect_settings.temporary_settings(updates=prefect_configs):
            worker = ProcessWorker(
                name=process_name + "_monitor",
                work_pool_name=pool_name + "_monitor",
                limit=concurrency_limit,
            )
            setproctitle.setproctitle(
                f"[prefect] {process_name}_device_monitor"
            )
            asyncio.run(worker.start())

    @staticmethod
    def start_device_mgr_work(process_name, pool_name, concurrency_limit):
        """Start device mgr worker by prefect client.

        Args:
            process_name: process name
            pool_name: work pool name
            concurrency_limit: max num of jobs running at the same time
        """
        # get prefect configs
        prefect_configs = TaskFlowManager.get_prefect_configs()
        # start process worker
        with prefect_settings.temporary_settings(updates=prefect_configs):
            worker = ProcessWorker(
                name=process_name + "_mgr",
                work_pool_name=pool_name + "_mgr",
                limit=concurrency_limit,
            )
            setproctitle.setproctitle(f"[prefect] {process_name}_device_mgr")
            asyncio.run(worker.start())

    async def wait_workers(self):
        """Start all workers for work pool."""
        device_names = self.device_manager.get_devices().keys()
        pool_names = device_names

        # wait for all workers are online
        all_worker_status = {workpool: False for workpool in pool_names}
        elapsed_time = 0
        for workpool in pool_names:
            workers = await self._client.read_workers_for_work_pool(workpool)
            work_status = [
                worker.status == WorkerStatus.ONLINE for worker in workers
            ]
            if (
                all(work_status)
                and len(work_status) == Constant.MAX_JOB_WORKER
            ):
                all_worker_status[workpool] = True
            if all_worker_status.values():
                self.worker_status = True
                break
            sleep(Constant.DEFAULT_JOB_INTERVAL)
            elapsed_time += Constant.DEFAULT_JOB_INTERVAL
            # timeout
            if elapsed_time > Constant.DEFAULT_JOB_TIMEOUT:
                raise TimeoutError("Workers start timeout")

        elapsed_time = 0
        monitor_devices = [
            device.get_name() + "_monitor"
            for device in self.device_manager.get_devices().values()
            if device.get_driver().enable_device_monitor
        ]
        all_worker_status = {workpool: False for workpool in monitor_devices}

        while True:
            for workpool in monitor_devices:
                workers = await self._client.read_workers_for_work_pool(
                    workpool,
                )
                work_status = [
                    worker.status == WorkerStatus.ONLINE for worker in workers
                ]
                if work_status.count(True) == 1:
                    all_worker_status[workpool] = True

            if all(all_worker_status.values()):
                break
            sleep(Constant.DEFAULT_JOB_INTERVAL)
            elapsed_time += Constant.DEFAULT_JOB_INTERVAL
            # timeout
            if elapsed_time > Constant.DEFAULT_JOB_TIMEOUT:
                raise TimeoutError("Workers for device monitor start timeout")

    def run_flow(
        self,
        deployment_id,
        args: dict[str, Any],
        tags=None,
        work_queue_name=None,
    ):
        """Run flow.

        Args:
            deployment_id: deploy uuid
            args: flow function args in dict
            tags: prefect flow tags
            work_queue_name: work queue name

        Returns:
            flow run uuid
        """
        if self.loop.is_running():
            flow_run_id = asyncio.run_coroutine_threadsafe(
                self.run_flow_by_client(
                    deployment_id,
                    args,
                    tags=tags,
                    work_queue_name=work_queue_name,
                ),
                self.loop,
            ).result()
        else:
            flow_run_id = self.loop.run_until_complete(
                self.run_flow_by_client(
                    deployment_id,
                    args,
                    tags=tags,
                    work_queue_name=work_queue_name,
                )
            )

        return flow_run_id

    def run_manage_task_flow(
        self,
        deployment_id,
        args: dict[str, Any],
        work_queue_name=None,
    ):
        """Run flow.

        Args:
            deployment_id: deploy uuid
            args: flow function args in dict
            tags: prefect flow tags
            work_queue_name: work queue name

        Returns:
            flow run uuid
        """
        if self.loop.is_running():
            success, details = asyncio.run_coroutine_threadsafe(
                self.run_manage_task_flow_by_client(
                    deployment_id,
                    args,
                    work_queue_name=work_queue_name,
                ),
                self.loop,
            ).result()
        else:
            success, details = self.loop.run_until_complete(
                self.run_manage_task_flow_by_client(
                    deployment_id,
                    args,
                    work_queue_name=work_queue_name,
                )
            )
        return success, details

    def get_flow_run_id_by_job_id(self, job_id, tags=None):
        flow_run_filter_kwargs = {}

        if job_id is not None:
            name_filter = FlowRunFilterName(any_=[str(job_id)])
            flow_run_filter_kwargs["name"] = name_filter

        # create flow run filter with flow_run_filter_kwargs
        flow_run_filter = FlowRunFilter(**flow_run_filter_kwargs)

        # get flow runs with flow_run_filter

        flow_runs = self._sync_client.read_flow_runs(
            flow_run_filter=flow_run_filter
        )
        if len(flow_runs) == 0:
            return None
        return flow_runs[0].id

    async def run_flow_by_client(
        self,
        deployment_id,
        args: dict[str, Any],
        tags=None,
        work_queue_name=None,
    ):
        """Run flow by prefect client.

        Args:
            deployment_id: deploy uuid
            args: flow function args in dict
            tags: prefect flow tags
            work_queue_name: work queue name

        Returns:
            flow run ids: flow run ids
        """
        job_id = str(args["job_info"]["data"].get("job_id", "Unknown"))
        prefect_tags = None
        circuit_aggregation = args["job_info"]["data"].get(
            "circuit_aggregation", Constant.AGGREGATION_TYPE_NONE
        )
        if circuit_aggregation:
            if circuit_aggregation == Constant.AGGREGATION_TYPE_INTERNAL:
                prefect_tags = [Constant.AGGREGATION_TYPE_INTERNAL]
            elif circuit_aggregation == Constant.AGGREGATION_TYPE_EXTERNAL:
                prefect_tags = [Constant.AGGREGATION_TYPE_EXTERNAL]
        if tags is not None:
            if prefect_tags is not None:
                prefect_tags.extend(tags)
            else:
                prefect_tags = tags
        args["job_info"]["data"]["job_enqueue_at"] = (
            Library.get_current_datetime()
        )
        flow_run = await self._client.create_flow_run_from_deployment(
            name=job_id,
            deployment_id=deployment_id,
            work_queue_name=work_queue_name,
            parameters=args,
            tags=prefect_tags,
        )

        return flow_run.id

    async def run_manage_task_flow_by_client(
        self,
        deployment_id,
        args: dict[str, Any],
        work_queue_name=None,
    ):
        """Run flow by prefect client.

        Args:
            deployment_id: deploy uuid
            args: flow function args in dict
            work_queue_name: work queue name
        """
        details = None
        await self._client.create_flow_run_from_deployment(
            deployment_id=deployment_id,
            work_queue_name=work_queue_name,
            parameters=args,
        )
        if args["device_mgr_info"]["method"] == "get_device_options":
            # TODO xudong need sleep or not?
            device_name = args["device_mgr_info"]["device_name"]
            device = self.device_manager.get_devices().get(device_name)
            details = device.get_device_options_info()
        return True, details

    def get_flow_result(self, job_id, tags=None):
        """Get flow run state and result.

        Args:
            job_id: job uuid
            tags: prefect flow tags

        Returns:
            state, parameters, result, err_msg
        """
        flow_run_id = self.get_flow_run_id_by_job_id(job_id, tags)
        if flow_run_id is None:
            raise ObjectNotFound(Exception("Job not found"))
        state, parameters, result, err_msg = self.get_flow_result_by_client(
            flow_run_id
        )
        return state, parameters, result, err_msg

    def update_flow(
        self, flow_run_id, name=None, parameters=None, variables=None
    ):
        """Update flow.

        Args:
            flow_run_id: flow run id
            name: flow name (Default value = None)
            parameters: flow parameters (Default value = None)
            variables: flow variables

        Returns:
            if flow exists (Default value = None)
        """

        async def _update_flow(
            _flow_run_id, _name=None, _parameters=None, _variables=None
        ):
            success = True
            err_msg = None
            try:
                await self._client.update_flow_run(
                    _flow_run_id,
                    name=_name,
                    parameters=_parameters,
                    job_variables=_variables,
                )
            except Exception as e:
                success = False
                err_msg = str(e)
            return success, err_msg

        if self.loop.is_running():
            return asyncio.run_coroutine_threadsafe(
                _update_flow(flow_run_id, name, parameters, variables),
                self.loop,
            ).result()
        else:
            return self.loop.run_until_complete(
                _update_flow(flow_run_id, name, parameters, variables)
            )

    def get_flow_result_by_client(self, flow_run_id):
        """Get flow run state and result by prefect client.

        Args:
            flow_run_id: flow run uuid

        Returns:
            state_name, parameters, result, state_message
        """
        # get flow info
        flow_run = self._sync_client.read_flow_run(flow_run_id)
        state = flow_run.state
        parameters = flow_run.parameters
        if state.is_final():
            if state.name.upper() == Constant.PREFECT_STATE_FAILED:
                return state.name, parameters, None, state.message
            elif state.name.upper() != Constant.PREFECT_STATE_COMPLETED:
                return state.name, parameters, None, None
            result = state.result()
            return state.name, parameters, result, None
        else:
            return state.name, parameters, None, None

    def get_flow_list(self, tags=None):
        """Get flow run list.

        Args:
            tags: prefect flow tags

        Returns:
            flow run list
        """
        results = self.get_flow_list_by_client(tags=tags)
        return results

    def get_flow_list_by_client(
        self,
        tags=None,
        sort_fields=["-created"],
        reverse=False,
    ):
        """Get flow run list by prefect client.

        Args:
            sort_fields: sort fields (Default value = ['-created'])
            reverse: reverse order
            tags: prefect flow tags

        Returns:
            flow run list
        """
        # TODO(jidalong) deal exception
        results_list = []

        # get flows info
        flow_runs = self.get_flow_runs_with_filters(tags=tags)

        sorted_flows = sorted(
            flow_runs,
            key=lambda sort_obj: Library.get_sorted_keys(
                sort_obj, sort_fields
            ),
            reverse=reverse,
        )
        for flow_run in sorted_flows:
            id = flow_run.name
            if id.startswith(Constant.DEVICE_MONITOR_PREFIX):
                continue
            is_uuid, _ = Library.validate_values_uuid(id, "job_id")
            if not is_uuid:
                logger.error(f"wrong: {id}")
                continue
            flow_state = flow_run.state.name.upper()
            state = self.convert_to_qcos_state(flow_state)
            parameters = flow_run.parameters
            results = None
            if flow_state == Constant.PREFECT_STATE_COMPLETED:
                results = flow_run.state.result()
            results_list.append({
                "id": id,
                "state": state,
                "parameters": parameters,
                "results": results,
            })
        return results_list

    def get_flow_run(self, flow_run_id, tags=None):
        """Get flow run.

        Args:
            flow_run_id: flow run id
            tags: flow tags
        Returns:
            flow run.
        """
        flow_run = None
        try:
            flow_run = self._sync_client.read_flow_run(flow_run_id)
        except ObjectNotFound:
            logger.error(
                f"Prefect execute flow error: "
                f"can't find flow_run_id: {flow_run_id}"
            )
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")
        return flow_run

    def delete_flow_runs(self, flow_run_ids):
        """Delete flow runs by client.

        Args:
            flow_run_ids: flow run uuid list

        Returns:
            success_list.
        """
        success_list = []
        for flow_run_id in flow_run_ids:
            try:
                flow_run = self._sync_client.read_flow_run(flow_run_id)
            except ObjectNotFound:
                logger.error(
                    f"Prefect execute flow error: "
                    f"can't find flow_run_id: {flow_run_id}"
                )
                continue
            except Exception as e:
                logger.error(f"Prefect execute flow error: {str(e)}")
                continue
            state = flow_run.state
            if state.name.upper() != Constant.PREFECT_STATE_RUNNING:
                try:
                    # delete flow
                    self._sync_client.delete_flow_run(flow_run_id)
                    success_list.append({
                        "flow_run_id": flow_run_id,
                        "state": Constant.JOB_STATUS_DELETED,
                    })
                except Exception as e:
                    logger.error(f"Prefect delete_flow_run error: {str(e)}")
        return success_list

    def cancel_flow_runs(self, flow_run_ids, tags=None):
        """Cancel flow runs.

        Args:
            flow_run_ids: flow run is list
            tags: prefect flow tags

        Returns:
            success list.
        """
        success_list = []
        for flow_run_id in flow_run_ids:
            try:
                flow_run = self._sync_client.read_flow_run(flow_run_id)
            except ObjectNotFound:
                logger.error(
                    f"Prefect execute flow error: "
                    f"can't find flow_run_id: {flow_run_id}"
                )
                continue
            except Exception as e:
                logger.error(f"Prefect execute flow error: {str(e)}")
                continue
            flow_state_name = flow_run.state.name.upper()
            if flow_state_name in Constant.PREFECT_CANCEL_REQUIRED_STATES:
                # cancel flow
                try:
                    cancelling_state = State(type=StateType.CANCELLING)
                    self._sync_client.set_flow_run_state(
                        flow_run_id, state=cancelling_state, force=True
                    )
                    success_list.append({
                        "flow_run_id": flow_run_id,
                        "state": Constant.JOB_STATUS_CANCELLED,
                    })
                except Exception as e:
                    logger.error(f"Prefect delete_flow_run error: {str(e)}")

        return success_list

    def delete_task_flow_by_name(self, flow_name):
        """Delete flow .

        Args:
            flow_name: flow name

        Returns:
            success flow_id.
        """
        try:
            flow_filter_kwargs = {}
            name_filter = FlowFilterName(any_=[flow_name])
            flow_filter_kwargs["name"] = name_filter
            flow_filter = FlowFilter(**flow_filter_kwargs)

            # get flow with flow_filter
            flows = self._sync_client.read_flows(flow_filter=flow_filter)
            if len(flows) == 0:
                return None
            flow_id = flows[0].id
            # delete flow
            self._sync_client.delete_flow(flow_id)
            return flow_id
        except Exception as e:
            logger.error(f"Prefect execute error: {str(e)}")
            return None

    def get_flow_runs_with_filters(
        self, states=None, tags=None, pool_name=None
    ):
        """Get flow runs with filters.

        Args:
            states: flow states
            tags: prefect flow tags
            pool_name: pool name

        Returns:
            flow runs.
        """
        # init filter dict
        flow_run_filter_kwargs = {}

        # assign state_filter if state is not None
        if states is not None:
            state_filter = FlowRunFilterState(type={"any_": states})
            flow_run_filter_kwargs["state"] = state_filter

        # assign tags_filter if tags is not None
        if tags:
            tags_filter = FlowRunFilterTags(all_=tags)
            flow_run_filter_kwargs["tags"] = tags_filter

        if pool_name is not None:
            flow_run_filter_kwargs["work_pool_name"] = {"eq_": pool_name}

        # create flow run filter with flow_run_filter_kwargs
        flow_run_filter = FlowRunFilter(**flow_run_filter_kwargs)

        # get flow runs with flow_run_filter
        flow_runs = self._sync_client.read_flow_runs(
            flow_run_filter=flow_run_filter
        )
        return flow_runs

    async def process_aggregation_job(self):
        """Process aggregation job."""

        def _cancel_aggregation_job(flow_run_ids):
            """Cancel aggregation job."""
            cancelling_state = State(type=StateType.CANCELLING)
            for flow_run_id in flow_run_ids:
                try:
                    self._sync_client.set_flow_run_state(
                        flow_run_id, state=cancelling_state, force=True
                    )
                except Exception as e:
                    logger.error(f"Prefect cancel flow run error: {str(e)}")

        def _process_aggregation_job(flow_run):
            """Process aggregation job."""
            aggregation_params = {}
            # 1. get sub jobs which can aggregated with parent job
            sub_jobs = {}
            states = [StateType.SCHEDULED]
            tags = [Constant.AGGREGATION_TYPE_EXTERNAL]
            flow_runs = self.get_flow_runs_with_filters(states, tags)
            for sub_flow_run in flow_runs:
                if (
                    sub_flow_run.parameters["job_info"]["data"][
                        "circuit_aggregation"
                    ]
                    == Constant.AGGREGATION_TYPE_EXTERNAL
                    and flow_run.parameters["job_info"]["data"]["backend"]
                    == sub_flow_run.parameters["job_info"]["data"]["backend"]
                    and sub_flow_run.work_pool_name == flow_run.work_pool_name
                    and len(sub_jobs) < Constant.MAX_AGGREGATION_JOBS
                ):
                    sub_jobs[sub_flow_run.name] = sub_flow_run.parameters
                    sub_jobs[sub_flow_run.name]["job_info"]["data"][
                        "flow_run_id"
                    ] = str(sub_flow_run.id)
            aggregation_params["is_parent"] = True
            aggregation_params["sub_jobs"] = sub_jobs

            # 2. make sure flow is in PAUSED state, not in RUNNING state
            is_flow_run_paused = False
            for i in range(Constant.JOB_AGG_FLOW_PAUSE_WAIT_TIMEOUT):
                flow_run_state = flow_run.state_name.lower()
                if flow_run_state == Constant.PREFECT_STATE_PAUSED.lower():
                    is_flow_run_paused = True
                    break
                flow_run = self.get_flow_run(flow_run.id)
                sleep(1)

            # 3. resume flow run and send sub job info(aggregation_parm)
            if is_flow_run_paused:
                self._sync_client.resume_flow_run(
                    flow_run.id, run_input=aggregation_params
                )

        def _subscribe_aggregation_jobs(redis_instance):
            """Subscribe aggregation jobs by redis."""
            pubsub = redis_instance.pubsub()
            job_agg_channel = f"{Constant.REDIS_CHANNEL_JOB_AGG_PREFIX}/*"
            pubsub.psubscribe(job_agg_channel)
            for message in pubsub.listen():
                if message.get("type") == "pmessage":
                    jobs_agg_info = json.loads(message.get("data"))
                    flow_run_id = jobs_agg_info["flow_run_id"]
                    need_cancel = jobs_agg_info.get("cancel", False)
                    if need_cancel:
                        # cancel all agg jobs
                        # results will be handled in job_engine:db_job_callback
                        sub_flow_run_ids = jobs_agg_info.get(
                            "sub_flow_list", []
                        )
                        if sub_flow_run_ids:
                            _cancel_aggregation_job(sub_flow_run_ids)
                    else:
                        flow_run = self.get_flow_run(flow_run_id)
                        if flow_run:
                            _process_aggregation_job(flow_run)

        aggregation_thread = threading.Thread(
            target=_subscribe_aggregation_jobs,
            args=(self.redis_instance,),
            daemon=True,
        )
        aggregation_thread.start()
