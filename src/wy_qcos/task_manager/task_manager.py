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
import re
import setproctitle
import threading
import time
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
from prefect.exceptions import ObjectAlreadyExists, ObjectNotFound
from prefect.states import State
from prefect.workers import ProcessWorker

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import Library
from wy_qcos.engine.job_engine import job_flow
from wy_qcos.engine.wirecut_engine import wirecut_flow
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
        self.flows = {}
        self.redis_instance = None

    @staticmethod
    def _is_device_monitor_enabled(device):
        config_enable = device.get_enable_device_monitor()
        driver_enable = device.get_driver().enable_device_monitor
        if config_enable is False:
            return False
        if config_enable is True and driver_enable is False:
            logger.warning(
                f"Device '{device.get_name()}': enable_device_monitor is set "
                f"to true in config file, but driver "
                f"'{device.get_driver().get_name()}' does not support "
                f"device monitor (driver enable_device_monitor is false). "
                f"Device monitor will be disabled."
            )
            return False
        return driver_enable

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
        default_python_bin, default_python_path_env = Library.get_driver_venv(
            "", Config.DEFAULT.VENV_DIR, add_default_env=True
        )
        for device_name in device_names:
            driver_name = None
            device = devices.get(device_name, None)
            if device:
                driver_name = device.get_driver().get_name()
            python_bin, python_path_env = Library.get_driver_venv(
                driver_name, Config.DEFAULT.VENV_DIR, add_default_env=True
            )

            device_key = f"{Constant.WORK_POOL_DEV}|{device_name}"
            deployment_configs[device_key] = {
                "python_bin": python_bin,
                "pool_name": device_key,
                "queue_name": f"{device_key}_{default_priority}",
                "path": "../engine/job_engine.py",
                "flow_name": job_flow.__name__,
                "command": f"{python_bin} -m prefect.engine",
                "env": python_path_env,
            }

            device = self.device_manager.get_devices().get(device_name)
            enable_device_monitor = self._is_device_monitor_enabled(device)
            if enable_device_monitor:
                monitor_key = f"{Constant.WORK_POOL_MON}|{device_name}"
                deployment_configs[monitor_key] = {
                    "python_bin": python_bin,
                    "pool_name": monitor_key,
                    "queue_name": "default",
                    "path": "../engine/device_monitor_engine.py",
                    "flow_name": device_monitor_flow.__name__,
                    "command": f"{python_bin} -m prefect.engine",
                    "env": python_path_env,
                }
            enable_device_mgr = device.get_driver().enable_device_mgr
            if enable_device_mgr:
                mgr_key = f"{Constant.WORK_POOL_MGR}|{device_name}"
                deployment_configs[mgr_key] = {
                    "python_bin": python_bin,
                    "pool_name": mgr_key,
                    "queue_name": "default",
                    "path": "../engine/device_mgr_engine.py",
                    "flow_name": device_manager_flow.__name__,
                    "command": f"{python_bin} -m prefect.engine",
                    "env": python_path_env,
                }

        # add virtual device deployments, eg. wirecut
        virtual_device_key = (
            f"{Constant.WORK_POOL_VDEV}|{Constant.VIRT_DEIVCE_WIRECUT}"
        )
        deployment_configs[virtual_device_key] = {
            "python_bin": default_python_bin,
            "pool_name": virtual_device_key,
            "queue_name": "default",
            "path": "../engine/wirecut_engine.py",
            "flow_name": wirecut_flow.__name__,
            "command": f"{python_bin} -m prefect.engine",
            "env": default_python_path_env,
        }
        return deployment_configs

    def start(self):
        """Create work pools, queues and start workers."""
        self.redis_instance = redis.Redis.from_url(
            Config.REDIS.REDIS_URL,
            decode_responses=True,
            protocol=2,
        )
        prefect_configs = TaskFlowManager.get_prefect_configs()
        with prefect_settings.temporary_settings(updates=prefect_configs):
            self._client = get_client()
            self._sync_client = get_client(sync_client=True)
            self.loop = asyncio.new_event_loop()

            self.check_connection()
            device_names = self.device_manager.get_devices().keys()

            # delete stale pools: any pool name that does NOT start
            # with one of the known work pool prefixes (dev|mon|mgr|vdev)
            stale_pool_pattern = (
                r"^(?!"
                + r"|".join(
                    re.escape(p) + r"\|" for p in Constant.WORK_POOL_TYPES
                )
                + r")"
            )
            self.loop.run_until_complete(
                self.delete_pools(name_patterns=[stale_pool_pattern])
            )

            # create resources: device work pools (one per device).
            # Monitor and manager pools are created only for devices
            # that have those features enabled. The virtual device
            # (wirecut) pool is created lazily by generate_deployment_configs
            # / create_deployments, so it is not included here.
            device_pool_names = [
                f"{Constant.WORK_POOL_DEV}|{name}" for name in device_names
            ]
            if device_pool_names:
                self.loop.run_until_complete(
                    self.create_pools(pool_names=device_pool_names)
                )

            monitor_devices = [
                f"{Constant.WORK_POOL_MON}|{device.get_name()}"
                for device in self.device_manager.get_devices().values()
                if self._is_device_monitor_enabled(device)
            ]
            if monitor_devices:
                self.loop.run_until_complete(
                    self.create_pools(pool_names=monitor_devices)
                )

            manager_devices = [
                f"{Constant.WORK_POOL_MGR}|{device.get_name()}"
                for device in self.device_manager.get_devices().values()
                if device.get_driver().enable_device_mgr
            ]
            if manager_devices:
                self.loop.run_until_complete(
                    self.create_pools(pool_names=manager_devices)
                )

            if device_pool_names:
                self.loop.run_until_complete(
                    self.create_queues(queue_names=device_pool_names)
                )
            # delete old monitor flow
            self.delete_task_flow_by_name("device-monitor-flow")

            # delete stale deployments: any deployment name that does
            # NOT start with one of the known work pool prefixes
            # (dev|mon|mgr|vdev)
            self.loop.run_until_complete(
                self.delete_deployments(name_patterns=[stale_pool_pattern])
            )

            deployment_configs = self.generate_deployment_configs(device_names)
            self.deployments = self.loop.run_until_complete(
                self.create_deployments(deployment_configs)
            )
            # get flows
            for _, deployment_info in self.deployments.items():
                flow_id = deployment_info["flow_id"]
                flow_name = deployment_info["flow_name"]
                self.flows[flow_name] = {
                    "flow_id": flow_id,
                }

            # delete workers whose name does not match their pool name
            self.loop.run_until_complete(self.delete_stale_workers())

            # start workers
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
            try:
                await self._client.create_work_pool(
                    work_pool=WorkPoolCreate(
                        name=pool_name,
                        type=Constant.DEFAULT_JOB_POOL_TYPE,
                        concurrency_limit=concurrency_limit,
                    )
                )
            except ObjectAlreadyExists:
                logger.debug(
                    f"Work pool '{pool_name}' already exists, skipping"
                )

    async def delete_pools(self, name_patterns=None):
        """Delete work pools matching the given regex patterns.

        Args:
            name_patterns: list of regex patterns; a pool is deleted when
                its name matches ANY pattern. When None, no filtering is
                applied and all work pools are deleted.

        Returns:
            list of deleted work pool names.
        """
        deleted = []
        try:
            pools = await self._client.read_work_pools()
        except Exception as e:
            logger.error(f"Failed to read work pools: {e}")
            return deleted

        compiled_patterns = None
        if name_patterns is not None:
            compiled_patterns = [
                re.compile(pattern) for pattern in name_patterns
            ]

        for pool in pools:
            name = pool.name
            if compiled_patterns is not None:
                if not any(p.search(name) for p in compiled_patterns):
                    continue
            try:
                await self._client.delete_work_pool(name)
                deleted.append(name)
            except Exception as e:
                logger.error(f"Delete work pool '{name}' error: {e}")
        logger.info(f"Deleted work pools: {', '.join(deleted)}")
        return deleted

    async def create_queues(self, queue_names):
        """Create all work queues under work pool.

        each priority has own work queue.

        Args:
            queue_names: queue names
        """
        logger.info(f"create_queues: {', '.join(queue_names)}")
        # Prefect read_work_queues limits limit to 100 and is bounded by
        # PREFECT_API_DEFAULT_LIMIT. Use pagination to fetch all queues so
        # the existence check does not miss entries beyond the first page,
        # which would otherwise trigger a 409 Conflict on duplicate
        # creation.
        queues = await self._read_all_work_queues()
        existing_names = {queue.name for queue in queues}
        for pool_name in queue_names:
            for priority in range(1, Constant.MAX_JOB_PRIORITY + 1):
                queue_name = f"{pool_name}_{priority}"
                if queue_name in existing_names:
                    continue
                try:
                    await self._client.create_work_queue(
                        name=queue_name,
                        work_pool_name=pool_name,
                        priority=priority,
                        concurrency_limit=Constant.DEFAULT_POOL_CONCURRENCY,
                    )
                except ObjectAlreadyExists:
                    logger.debug(
                        f"Work queue '{queue_name}' already exists "
                        f"in pool '{pool_name}', skipping"
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
            # get default flow id
            flow_name = flow.name
            flow_filter = FlowFilter(name=FlowFilterName(any_=[flow_name]))
            flows = self._sync_client.read_flows(flow_filter=flow_filter)
            flow_id = flows[0].id if flows else None
            deployments[deployment_name] = {
                "deploy_id": str(deploy_id),
                "flow_id": str(flow_id),
                "flow_name": flow_name,
                "env": env,
            }
        return deployments

    def get_deployments(self):
        """Get all deployments."""
        return self.deployments

    def get_deployment(self, deployment_name):
        """Get deployment.

        Lookup first tries the exact deployment name, then falls back
        to resolving ``{pool_prefix}|{deployment_name}`` for each work
        pool prefix so callers may pass either the full pool-qualified
        name or just the device name.

        Args:
            deployment_name: deployment name (pool-qualified or device
                name)

        Returns:
            deployment info dict or None
        """
        deployment = self.deployments.get(deployment_name, None)
        if deployment is not None:
            return deployment
        for pool_prefix in (
            Constant.WORK_POOL_DEV,
            Constant.WORK_POOL_MON,
            Constant.WORK_POOL_MGR,
            Constant.WORK_POOL_VDEV,
        ):
            key = f"{pool_prefix}|{deployment_name}"
            deployment = self.deployments.get(key, None)
            if deployment is not None:
                return deployment
        return None

    async def delete_deployments(self, name_patterns=None):
        """Delete deployments matching the given regex patterns.

        Args:
            name_patterns: list of regex patterns; a deployment is deleted
                when its name matches ANY pattern. When None, no filtering
                is applied and all deployments are deleted.

        Returns:
            list of deleted deployment names.
        """
        deleted = []
        try:
            deployments = await self._client.read_deployments(limit=None)
        except Exception as e:
            logger.error(f"Failed to read deployments: {e}")
            return deleted

        compiled_patterns = None
        if name_patterns is not None:
            compiled_patterns = [
                re.compile(pattern) for pattern in name_patterns
            ]

        for dep in deployments:
            name = dep.name
            if compiled_patterns is not None:
                if not any(p.search(name) for p in compiled_patterns):
                    continue
            try:
                await self._client.delete_deployment(dep.id)
                deleted.append(name)
            except Exception as e:
                logger.error(f"Delete deployment '{name}' error: {e}")
        logger.info(f"Deleted deployments: {', '.join(deleted)}")
        return deleted

    async def delete_worker(self, work_pool_name, worker_name):
        """Delete a single worker from a work pool via Prefect API.

        Calls the Prefect server DELETE endpoint
        ``/work_pools/{work_pool_name}/workers/{name}`` to remove the
        worker registration.

        Args:
            work_pool_name: name of the work pool the worker belongs to
            worker_name: name of the worker to delete

        Returns:
            bool: True if the worker was deleted, False on error
        """
        try:
            await self._client.request(
                "DELETE",
                "/work_pools/{work_pool_name}/workers/{name}",
                path_params={
                    "work_pool_name": work_pool_name,
                    "name": worker_name,
                },
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to delete worker '{worker_name}' "
                f"from pool '{work_pool_name}': {e}"
            )
            return False

    async def delete_stale_workers(self):
        """Delete workers whose name does not match their work pool.

        For each work pool, the expected worker name is
        ``proc|{pool_name}``. Any worker registered under a pool whose
        name deviates from this pattern is considered stale and is
        removed via delete_worker. Stale workers typically arise from
        renamed pools or leftover registrations after pool re-creation.

        Returns:
            list of deleted worker names.
        """
        deleted = []
        try:
            pools = await self._client.read_work_pools()
        except Exception as e:
            logger.error(f"Failed to read work pools: {e}")
            return deleted

        for pool in pools:
            pool_name = pool.name
            expected_worker_name = f"{Constant.PROCESS_PREFIX}|{pool_name}"
            try:
                workers = await self._client.read_workers_for_work_pool(
                    pool_name
                )
            except Exception as e:
                logger.error(
                    f"Failed to read workers for pool {pool_name}: {e}"
                )
                continue

            for worker in workers:
                worker_name = worker.name
                if worker_name == expected_worker_name:
                    continue
                success = await self.delete_worker(pool_name, worker_name)
                if success:
                    deleted.append(worker_name)
                    logger.info(
                        f"Deleted stale worker '{worker_name}' from pool "
                        f"'{pool_name}' (expected '{expected_worker_name}')"
                    )
        if deleted:
            logger.info(f"Deleted stale workers: {', '.join(deleted)}")
        return deleted

    @staticmethod
    def _kill_workers_by_regex(regex_list, ppid=None):
        """Kill prefect worker processes matching the given regex list.

        Args:
            regex_list: list of regex patterns to match process cmdlines
            ppid: parent pid of processes

        Returns:
            tuple(success_pids, failed_pids)
        """
        _process_list = Library.get_processes(regex_list)
        process_list = []
        if _process_list:
            for process in _process_list:
                _ppid = process.ppid()
                if ppid is None or _ppid == ppid:
                    process_list.append(process)
        else:
            return [], []
        return Library.kill(process_list, force=True)

    def kill_workers(self):
        """Kill workers."""
        logger.info("Kill existing prefect workers")
        # proctitle equals worker name ([qcos] / [prefectc
        # ]); also
        # kill stale prefect.engine processes
        regex_list = [
            re.escape("[qcos] "),
            re.escape("[prefect] "),
            r"prefect.engine",
        ]
        self._kill_workers_by_regex(regex_list)

    def list_workers(self):
        """List all prefect workers with name and status.

        The prefect Worker object does not carry a process pid, so the
        pid is resolved by matching the worker proctitle (which equals
        the worker name) against running processes.

        Returns:
            list of dict, each item contains worker_name, work_pool,
            worker_status and pid.
        """
        if not self._sync_client:
            logger.warning("Prefect sync client is not initialized")
            return []

        results = []
        try:
            pools = self._sync_client.read_work_pools()
        except Exception as e:
            logger.error(f"Failed to read work pools: {e}")
            return results

        for pool in pools:
            pool_name = pool.name
            try:
                workers = self._sync_client.read_workers_for_work_pool(
                    pool_name
                )
            except Exception as e:
                logger.error(
                    f"Failed to read workers for pool {pool_name}: {e}"
                )
                continue

            if not workers:
                device_name = self._parse_device_name_from_pool(pool_name)
                results.append({
                    "worker_name": "",
                    "work_pool": pool_name,
                    "device_name": device_name,
                    "worker_status": "no_workers",
                    "pid": None,
                })
                continue

            for worker in workers:
                status_value = (
                    worker.status.value
                    if hasattr(worker.status, "value")
                    else str(worker.status)
                )
                # normalize to lowercase for consistent output
                status_value = status_value.lower()
                pid = self._get_worker_pid(worker.name)
                # Prefect may still report ONLINE for a short period
                # after the process is killed. If no matching process
                # is found, correct the status to OFFLINE.
                if (
                    status_value == WorkerStatus.ONLINE.value.lower()
                    and pid is None
                ):
                    status_value = WorkerStatus.OFFLINE.value.lower()
                device_name, _ = self._parse_worker_name(worker.name)
                results.append({
                    "worker_name": worker.name,
                    "work_pool": pool_name,
                    "device_name": device_name or "",
                    "worker_status": status_value,
                    "pid": pid,
                })

        # sort by work_pool name for stable output
        results.sort(key=lambda item: item["work_pool"])
        return results

    @staticmethod
    def _worker_name_to_proctitle(worker_name):
        """Convert a prefect worker name to its process proctitle.

        The proctitle is prefixed with ``[qcos] `` so it can be
        matched against running worker processes (see kill_workers).
        The worker name is used unchanged because the worker type
        is encoded in the pool prefix segment.

        Args:
            worker_name: prefect worker name

        Returns:
            str: the proctitle used to identify the worker process
        """
        if not worker_name:
            return ""
        return f"[qcos] {worker_name}"

    @staticmethod
    def _build_proctitle_regex(worker_name):
        """Build a regex that matches the exact worker proctitle.

        The proctitle equals the worker name and is embedded in the
        full process cmdline. The pattern escapes special characters
        (notably ``|``) and anchors the end so that a short worker
        name does not match longer ones.

        Args:
            worker_name: prefect worker name

        Returns:
            str: regex pattern for exact proctitle matching
        """
        proctitle = TaskFlowManager._worker_name_to_proctitle(worker_name)
        return re.escape(proctitle)

    @staticmethod
    def _get_worker_pid(worker_name):
        """Resolve the process pid of a prefect worker by its name.

        The worker process proctitle is derived from the worker name via
        _worker_name_to_proctitle. We match running processes against the
        proctitle pattern to find the pid.

        Args:
            worker_name: worker name

        Returns:
            int or None: the pid of the worker process, None if not found
        """
        if not worker_name:
            return None

        regex_list = [TaskFlowManager._build_proctitle_regex(worker_name)]
        try:
            process_list = Library.get_processes(regex_list)
        except Exception as e:
            logger.debug(f"Failed to get process for {worker_name}: {e}")
            return None

        if not process_list:
            return None

        return process_list[0].pid

    def restart_worker(self, worker_name):
        """Restart a single prefect worker by worker name.

        The worker process is identified by its proctitle which is set to
        ``{worker_name}`` when started (the worker name itself, e.g.
        ``proc|dev|{device}``). The worker name follows the pattern
        ``proc|{pool_prefix}|{device_name}``.

        Args:
            worker_name: worker name to restart

        Returns:
            tuple(success: bool, message: str)
        """
        if not worker_name:
            return False, "worker_name must not be empty"

        logger.info(f"Restart worker: {worker_name}")

        # kill the target worker process by matching its proctitle exactly.
        # _build_proctitle_regex anchors the proctitle end to avoid partial
        # matches (e.g. "pro" must not match "proc|dev|x").
        # NOTE: if no process is found, the worker may already be dead
        # (OFFLINE). In that case we skip the kill step and proceed to
        # start a fresh worker process directly.
        regex_list = [self._build_proctitle_regex(worker_name)]
        current_pid = Library.get_current_pid()
        success_pids, failed_pids = self._kill_workers_by_regex(
            regex_list, ppid=current_pid
        )
        if not success_pids:
            logger.info(
                f"No running process found for {worker_name}, "
                f"proceeding to start a new worker"
            )
        if failed_pids:
            logger.warning(f"Failed to kill some processes: {failed_pids}")

        # resolve device name and worker type from worker name, then
        # start a new worker process for the corresponding pool.
        # worker name patterns:
        #   proc|dev|{device}   -> job worker
        #   proc|mon|{device}   -> device monitor worker
        #   proc|mgr|{device}   -> device manager worker
        #   proc|vdev|{device}  -> virtual device (wirecut) worker
        device_name, worker_type = self._parse_worker_name(worker_name)
        if not device_name:
            msg = (
                f"worker {worker_name} killed but could not be restarted "
                f"(worker name unrecognized)"
            )
            logger.warning(msg)
            return True, msg

        started = self._start_worker_process(device_name, worker_type)
        if not started:
            msg = (
                f"worker {worker_name} killed but could not be restarted "
                f"(device not found or worker type disabled)"
            )
            logger.warning(msg)
            return True, msg

        return True, f"worker {worker_name} restarted successfully"

    def watchdog_restart_dead_workers(self):
        """Check for dead workers and restart them automatically.

        Called periodically from the health-check flow. For each
        worker that is OFFLINE and has no running process, restart it
        via _start_worker_process. Workers whose device is disabled
        or whose worker type is disabled are skipped.
        """
        if not self._sync_client:
            logger.warning(
                "Prefect sync client is not initialized, skip watchdog"
            )
            return

        if not self.device_manager:
            logger.warning("Device manager is not initialized, skip watchdog")
            return

        # get current worker status from prefect
        workers = self.list_workers()
        restarted = 0
        for worker_info in workers:
            status = worker_info.get("worker_status", "")
            worker_name = worker_info.get("worker_name", "")
            device_name = worker_info.get("device_name", "")

            # only restart workers that are offline (process dead)
            if status != "offline":
                continue
            if not worker_name or not device_name:
                continue

            # parse worker type from worker name
            _, worker_type = self._parse_worker_name(worker_name)
            if worker_type is None:
                continue

            # restart the dead worker
            logger.warning(
                f"Watchdog: worker {worker_name} is offline, restarting..."
            )
            started = self._start_worker_process(device_name, worker_type)
            if started:
                logger.info(f"Watchdog: worker {worker_name} restarted")
                restarted += 1
            else:
                logger.warning(
                    f"Watchdog: worker {worker_name} restart failed"
                )

        if restarted > 0:
            logger.info(f"Watchdog: restarted {restarted} dead worker(s)")

    @staticmethod
    def _parse_device_name_from_pool(pool_name):
        """Resolve the device name from a work pool name.

        Pool name patterns:
            dev|{device}   -> "{device}"
            mon|{device}   -> "{device}"
            mgr|{device}   -> "{device}"
            vdev|{device}  -> "{device}"

        The prefix is separated from the device name by a ``|``
        delimiter, which is stripped from the result.

        Args:
            pool_name: prefect work pool name

        Returns:
            device name string, or empty string if unrecognized
        """
        for pool_prefix in (
            Constant.WORK_POOL_DEV,
            Constant.WORK_POOL_MON,
            Constant.WORK_POOL_MGR,
            Constant.WORK_POOL_VDEV,
        ):
            if pool_name.startswith(f"{pool_prefix}|"):
                return pool_name[len(pool_prefix) + 1 :]
        return ""

    # Map work pool prefix constant -> semantic worker type name.
    # The worker type is determined solely by the pool prefix in the
    # worker name (e.g. "proc|dev|dummy" -> job, "proc|mon|dummy" ->
    # monitor); no device-name suffix is involved.
    _POOL_PREFIX_TO_WORKER_TYPE = {
        Constant.WORK_POOL_DEV: Constant.WORKER_TYPE_DEV,
        Constant.WORK_POOL_MON: Constant.WORKER_TYPE_MON,
        Constant.WORK_POOL_MGR: Constant.WORKER_TYPE_MGR,
        Constant.WORK_POOL_VDEV: Constant.WORKER_TYPE_VDEV,
    }

    @staticmethod
    def _parse_worker_name(worker_name):
        """Parse worker name into device name and worker type.

        Worker name is constructed by _start_worker_process as:
            {PROCESS_PREFIX}|{worker_type}|{device_name}

        e.g. ``proc|dev|dummy``, ``proc|mon|dummy``. The worker
        type is derived from the pool prefix segment.

        Args:
            worker_name: worker name ({PROCESS_PREFIX}|{worker_type}|{dev})

        Returns:
            tuple(device_name, worker_type) where worker_type is one
            of Constant.WORKER_TYPE_*; (None, None) if unrecognized
        """
        prefix = f"{Constant.PROCESS_PREFIX}|"
        if not worker_name.startswith(prefix):
            return None, None
        remainder = worker_name[len(prefix) :]

        # split remainder into type_segment and device_name
        parts = remainder.split("|", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return None, None

        worker_type, device_name = parts
        return device_name, worker_type

    # Reverse map: semantic worker type -> work pool prefix constant.
    _WORKER_TYPE_TO_POOL_PREFIX = {
        Constant.WORKER_TYPE_DEV: Constant.WORK_POOL_DEV,
        Constant.WORKER_TYPE_MON: Constant.WORK_POOL_MON,
        Constant.WORKER_TYPE_MGR: Constant.WORK_POOL_MGR,
        Constant.WORKER_TYPE_VDEV: Constant.WORK_POOL_VDEV,
    }

    def _start_worker_process(self, device_name, worker_type):
        """Start a single worker process for a device.

        Shared by start_workers (batch startup) and restart_worker
        (single worker restart). The ``worker_type`` argument accepts
        either a semantic worker type
        (Constant.WORKER_TYPE_DEV/MON/MGR/VDEV) or a work pool
        prefix constant (Constant.WORK_POOL_*); both are normalized
        internally to the pool prefix.

        Args:
            device_name: device name
            worker_type: semantic worker type or work pool prefix
                constant

        Returns:
            bool: True if a worker process was started
        """
        concurrency_limit = Constant.DEFAULT_POOL_CONCURRENCY
        device = None
        device_pool_name = None
        dev_prefix = Constant.WORK_POOL_DEV
        mon_prefix = Constant.WORK_POOL_MON
        mgr_prefix = Constant.WORK_POOL_MGR
        vdev_prefix = Constant.WORK_POOL_VDEV

        # normalize semantic worker type -> pool prefix
        pool_prefix = self._WORKER_TYPE_TO_POOL_PREFIX.get(worker_type)
        if pool_prefix is not None:
            worker_type = pool_prefix

        if worker_type in [dev_prefix, mon_prefix, mgr_prefix]:
            device = self.device_manager.get_devices().get(device_name)
            if not device:
                return False

            # skip starting any worker for disabled devices
            if not device.enable:
                logger.warning(
                    f"Device '{device_name}' is disabled (enable=False), "
                    f"skip starting {worker_type} worker"
                )
                return False

        # validate worker type is enabled for the device
        if worker_type == mon_prefix:
            if not self._is_device_monitor_enabled(device):
                return False
            device_pool_name = f"{mon_prefix}|{device_name}"
        elif worker_type == mgr_prefix:
            if not device.get_driver().enable_device_mgr:
                return False
            device_pool_name = f"{mgr_prefix}|{device_name}"
        elif worker_type == vdev_prefix:
            device_pool_name = f"{vdev_prefix}|{device_name}"
            concurrency_limit = Constant.VIRTUAL_DEVICE_POOL_CONCURRENCY
        else:
            device_pool_name = f"{dev_prefix}|{device_name}"
        target = self.start_worker

        # process name
        process_name = f"{Constant.PROCESS_PREFIX}|{worker_type}|{device_name}"

        # load deployment env (PYTHONPATH) if available
        deployment = self.get_deployment(device_pool_name)
        if deployment:
            env = deployment.get("env", {})
            pythonpath = env.get("PYTHONPATH", None)
            if pythonpath:
                os.environ["PYTHONPATH"] = pythonpath

        worker_process = multiprocessing.Process(
            target=target,
            args=(
                process_name,
                device_pool_name,
                worker_type,
                concurrency_limit,
            ),
            name=process_name,
        )
        worker_process.daemon = True
        worker_process.start()
        logger.info(
            f"Started worker process: {process_name} "
            f"(type={worker_type}, device={device_name}, "
            f"pool_name={device_pool_name}, "
            f"concurrency_limit={concurrency_limit}, "
            f"pid: {worker_process.pid})"
        )
        return True

    def start_workers(self):
        """Start workers using multiprocessing.

        For each device, start the job worker and (if enabled) the device
        monitor worker and device manager worker. Each worker process is
        started via _start_worker_process so that batch startup and single
        worker restart share the same code path.
        """
        logger.info("Start prefect workers")
        device_names = self.device_manager.get_devices().keys()
        for device_name in device_names:
            # start device worker process
            self._start_worker_process(device_name, Constant.WORK_POOL_DEV)
            # start device monitor process if enabled
            self._start_worker_process(device_name, Constant.WORK_POOL_MON)
            # start device manager process if enabled
            self._start_worker_process(device_name, Constant.WORK_POOL_MGR)
        # start virtual devices
        device_name = Constant.VIRT_DEIVCE_WIRECUT
        self._start_worker_process(device_name, Constant.WORK_POOL_VDEV)

    def run_device_monitor(self):
        """Run device monitor by prefect."""
        devices = self.device_manager.get_devices().values()

        for device in devices:
            # registry deploy
            deployment = self.deployments.get(
                f"{Constant.WORK_POOL_MON}|{device.get_name()}"
            )
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
                    "url": self.device_manager.config.REDIS.REDIS_URL,
                }

                args = {"device_monitor_info": device_monitor_info}
                self._sync_client.create_flow_run_from_deployment(
                    name=f"{Constant.WORK_POOL_MON}|{str(device.get_name())}",
                    deployment_id=deploy_id,
                    parameters=args,
                )

    async def _read_all_work_queues(self):
        """Fetch all work queues with pagination.

        Prefect read_work_queues limits limit to 200 and is bounded by
        PREFECT_API_DEFAULT_LIMIT. This helper loops over offset/page_size
        to fetch all work queues so the existence check in create_queues
        does not miss entries beyond the first page.

        Returns:
            list of work queue objects
        """
        all_queues = []
        offset = 0
        page_size = 200
        while True:
            page = await self._client.read_work_queues(
                limit=page_size, offset=offset
            )
            all_queues.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return all_queues

    @staticmethod
    def read_all_flow_runs(sync_client, flow_run_filter=None, page_size=200):
        """Fetch all flow runs with pagination.

        Prefect read_flow_runs is bounded by
        PREFECT_API_DEFAULT_LIMIT (default 200). This helper loops over
        offset/page_size to fetch all matching flow runs so that cleanup
        and listing logic does not silently miss entries beyond the
        first page.

        Args:
            sync_client: prefect SyncPrefectClient instance
            flow_run_filter: optional FlowRunFilter to narrow results
            page_size: number of flow runs per request page (default 200)

        Returns:
            list of FlowRun objects
        """
        all_flow_runs = []
        offset = 0
        while True:
            page = sync_client.read_flow_runs(
                flow_run_filter=flow_run_filter,
                limit=page_size,
                offset=offset,
            )
            all_flow_runs.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return all_flow_runs

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
    def start_worker(process_name, pool_name, worker_type, concurrency_limit):
        """Start worker by prefect client.

        Args:
            process_name: process name (also used as proctitle)
            pool_name: work pool name
            worker_type: work pool prefix constant (dev/mon/mgr/vdev)
            concurrency_limit: max num of jobs running at the same time
        """
        # get prefect configs
        prefect_configs = TaskFlowManager.get_prefect_configs()

        # start process worker
        work_queues = None
        if worker_type == Constant.WORK_POOL_DEV:
            work_queues = [
                f"{pool_name}_{str(i)}"
                for i in range(1, Constant.MAX_JOB_PRIORITY + 1)
            ]
        with prefect_settings.temporary_settings(updates=prefect_configs):
            worker = ProcessWorker(
                name=process_name,
                work_pool_name=pool_name,
                work_queues=work_queues,
                limit=concurrency_limit,
            )
            setproctitle.setproctitle(f"[qcos] {process_name}")
            asyncio.run(worker.start())

    async def wait_workers(self):
        """Start all workers for work pool."""
        device_names = self.device_manager.get_devices().keys()
        pool_names = [
            f"{Constant.WORK_POOL_DEV}|{name}" for name in device_names
        ]

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
            time.sleep(Constant.DEFAULT_JOB_INTERVAL)
            elapsed_time += Constant.DEFAULT_JOB_INTERVAL
            # timeout
            if elapsed_time > Constant.DEFAULT_JOB_TIMEOUT:
                raise TimeoutError("Workers start timeout")

        elapsed_time = 0
        monitor_devices = [
            f"{Constant.WORK_POOL_MON}|{device.get_name()}"
            for device in self.device_manager.get_devices().values()
            if self._is_device_monitor_enabled(device)
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
            time.sleep(Constant.DEFAULT_JOB_INTERVAL)
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

        flow_runs = self.read_all_flow_runs(
            self._sync_client, flow_run_filter=flow_run_filter
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
        args["job_info"]["data"]["job_enqueue_at"] = time.time()
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
            delete_results.
        """
        delete_results = {}
        for flow_run_id in flow_run_ids:
            try:
                flow_run = self._sync_client.read_flow_run(flow_run_id)
            except ObjectNotFound:
                logger.debug(
                    f"Prefect execute flow error: "
                    f"can't find flow_run_id: {flow_run_id}"
                )
                delete_results[flow_run_id] = {
                    "state": Constant.JOB_STATUS_DELETED,
                }
                continue
            except Exception as e:
                logger.error(f"Prefect execute flow error: {str(e)}")
                continue
            state = flow_run.state
            if state.name.upper() == Constant.PREFECT_STATE_RUNNING:
                delete_results[flow_run_id] = {
                    "state": Constant.JOB_STATUS_RUNNING,
                }
            else:
                try:
                    # delete flow
                    self._sync_client.delete_flow_run(flow_run_id)
                except Exception as e:
                    logger.error(f"Prefect delete_flow_run error: {str(e)}")
                delete_results[flow_run_id] = {
                    "state": Constant.JOB_STATUS_DELETED,
                }
        return delete_results

    def cancel_flow_runs(self, flow_run_ids, tags=None):
        """Cancel flow runs.

        Args:
            flow_run_ids: flow run is list
            tags: prefect flow tags

        Returns:
            canceled_results.
        """
        canceled_results = {}
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
                    canceled_results[flow_run_id] = {
                        "state": Constant.JOB_STATUS_CANCELLED,
                    }
                except Exception as e:
                    logger.error(f"Prefect delete_flow_run error: {str(e)}")

        return canceled_results

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
        flow_runs = self.read_all_flow_runs(
            self._sync_client, flow_run_filter=flow_run_filter
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

        def _delete_aggregation_job(flow_run_ids):
            """Delete aggregation job."""
            for flow_run_id in flow_run_ids:
                try:
                    self._sync_client.delete_flow_run(flow_run_id)
                except Exception as e:
                    logger.warning(f"Prefect delete flow run error: {str(e)}")

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
                time.sleep(1)

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
                    need_delete = jobs_agg_info.get("delete", False)
                    if need_cancel:
                        # cancel all agg jobs
                        # results will be handled in job_engine:db_job_callback
                        sub_flow_run_ids = jobs_agg_info.get(
                            "sub_flow_list", []
                        )
                        if sub_flow_run_ids:
                            _cancel_aggregation_job(sub_flow_run_ids)
                    elif need_delete:
                        # delete all agg jobs
                        # results will be handled in job_engine:db_job_callback
                        sub_flow_run_ids = jobs_agg_info.get(
                            "sub_flow_list", []
                        )
                        if sub_flow_run_ids:
                            _delete_aggregation_job(sub_flow_run_ids)
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
