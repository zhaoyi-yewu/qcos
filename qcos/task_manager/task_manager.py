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

import asyncio
import threading
from abc import ABC
from time import sleep
from pathlib import Path
from typing import Any
import logging

from prefect import get_client
from prefect.client.schemas.actions import WorkPoolCreate
from prefect.client.schemas.objects import WorkerStatus
from prefect.exceptions import ObjectNotFound
from prefect.workers import ProcessWorker
from rich.console import Console

from qcos.common.constant import Constant
from qcos.engine.job_engine import job_flow

logger = logging.getLogger(__name__)


class TaskFlowManager(ABC):
    """
    task manager based on prefect framework
    """

    def __init__(self):
        """
        Init TaskFlowManager
        """

        self._client = None
        self.loop = None
        self._console = None
        self.worker_status = False
        self.driver_manager = None

    def transform_to_qcos_state(self, state):
        if state.upper() == "CRASHED":
            return Constant.JOB_STATUS_FAILED
        elif state.upper() == "SCHEDULED":
            return Constant.JOB_STATUS_QUEUED
        elif state.upper() == "PENDING" or state.upper() == "LATE":
            return Constant.JOB_STATUS_QUEUED
        else:
            return state.upper()

    def start(self):
        """
        Create work pools, queues and start workers
        """

        self._client = get_client()
        self._console = Console(quiet=True)
        self.loop = asyncio.new_event_loop()

        self.loop.run_until_complete(self.create_pools())
        self.loop.run_until_complete(self.create_queues())
        self.loop.run_until_complete(self.start_workers())

    def set_driver_manager(self, driver_manager):
        """
        Set driver manager

        :param driver_manager: driver manager
        """

        self.driver_manager = driver_manager

    async def create_pools(self):
        """
        Create all work pools, each policy has own work pools.
        """

        create_workpools = [self.create_pool(pool_name) for pool_name in
                            Constant.JOB_SCHED_POLICIES]
        return await asyncio.gather(*create_workpools)

    async def create_pool(self, pool_name):
        """
        Create work pool by prefect client.

        :param pool_name: work pool name, using policy name
        """

        pools = await self._client.read_work_pools()
        if not any(pool.name == pool_name for pool in pools):
            work_pool = await self._client.create_work_pool(
                work_pool=WorkPoolCreate(
                    name=pool_name,
                    type=Constant.DEFAULT_JOB_POOL_TYPE,
                    concurrency_limit=Constant.DEFAULT_POOL_CONCURRENCY))

    async def create_queues(self):
        """
        Create all work queues under work pool,
        each priority has own work queue.
        """

        queues = await self._client.read_work_queues()
        for pool_name in Constant.JOB_SCHED_POLICIES:
            for priority in range(1, Constant.MAX_JOB_PRIORITY + 1):
                queue_name = f"{pool_name}_{priority}"
                if not any(queue.name == queue_name for queue in queues):
                    work_queue = await self._client.create_work_queue(
                        name=queue_name,
                        work_pool_name=pool_name,
                        priority=priority,
                        concurrency_limit=Constant.DEFAULT_POOL_CONCURRENCY)

    async def start_workers(self):
        """
        Start all workers for work pool
        """

        # start worker
        for policy in range(len(Constant.JOB_SCHED_POLICIES)):
            pool_name = str(policy)
            worker_thread = threading.Thread(target=self.start_work,
                                             args=(pool_name),
                                             daemon=True)
            worker_thread.start()

        # wait for all workers are online
        all_worker_status = {workpool: False for workpool in
                             Constant.JOB_SCHED_POLICIES}
        time = 0
        for policy in Constant.JOB_SCHED_POLICIES:
            workers = await self._client.read_workers_for_work_pool(
                policy)
            work_status = [worker.status == WorkerStatus.ONLINE for
                           worker in workers]
            if all(work_status) and len(
                    work_status) == Constant.MAX_JOB_WORKER:
                all_worker_status[policy] = True
            if all_worker_status.values():
                self.worker_status = True
                break
            sleep(Constant.DEFAULT_JOB_INTERVAL)
            time += Constant.DEFAULT_JOB_INTERVAL
            # timeout
            if time > Constant.DEFAULT_JOB_TIMEOUT:
                raise TimeoutError("Workers start timeout")

    def start_work(self, pool_name):
        """
        Start worker by prefect client.

        :param pool_name: work pool name
        """
        pool_name = Constant.JOB_SCHED_POLICIES[int(pool_name)]
        worker = ProcessWorker(
            work_pool_name=pool_name,
            limit=Constant.DEFAULT_POOL_CONCURRENCY,
            work_queues=[f'{pool_name}_{str(i)}' for i in
                         range(1, Constant.MAX_JOB_PRIORITY + 1)]
        )
        asyncio.run(worker.start(printer=self._console.print))

    def deploy_task_flow(
            self, deploy_name: str,
            policy_type: str, priority: int,
            deploy_flow, path: str):
        """
        Deploy flow by prefect client.

        :param deploy_name: deploy name
        :param policy_type: policy type
        :param priority: priority
        :param deploy_flow: deploy flow function
        :param path: .py path where the flow function relative to current path
        :return deploy_id: deploy uuid
        """

        # TODO(jidalong) deal exception
        queue_name = f"{policy_type}_{priority}"
        # registry deploy
        flow_name = deploy_flow.__name__
        deploy_id = deploy_flow.from_source(
            source=Path(__file__).parent,
            entrypoint=path + ":" + flow_name,
        ).deploy(
            name=deploy_name,
            work_pool_name=policy_type,
            work_queue_name=queue_name,
            print_next_steps=False,
            ignore_warnings=True
        )
        return deploy_id

    def run_task_flow(self, deployment_id, args: dict[str, Any]):
        """
        Run flow.

        :param deployment_id: deploy uuid
        :param args: flow function args in dict
        :return flow_run_id: flow run uuid
        """

        flow_run_id = self.loop.run_until_complete(
            self.run_task_flow_by_client(deployment_id, args))  # 强制等待

        return flow_run_id

    async def run_task_flow_by_client(self, deployment_id,
                                      args: dict[str, Any]):
        """
        Run flow by prefect client.

        :param deployment_id: deploy uuid
        :param args: flow function args in dict
        :return flow_run_id: flow run uuid
        """

        # TODO(jidalong) deal exception
        flow_run = await self._client.create_flow_run_from_deployment(
            deployment_id=deployment_id,
            parameters=args)
        return flow_run.id

    def get_task_flow_result(self, flow_run_id):
        """
        Get flow run state and result.

        :param flow_run_id: flow run uuid
        :return state: flow state
        :return parameters: flow parameters
        :return result: flow result
        :return err_msg: flow error message
        """

        state, parameters, result, err_mas = self.loop.run_until_complete(
            self.get_task_flow_result_by_client(flow_run_id))
        return state, parameters, result, err_mas

    async def get_task_flow_result_by_client(self, flow_run_id):
        """
        Get flow run state and result by prefect client.

        :param flow_run_id: flow run uuid
        :return state: flow state
        :return parameters: flow parameters
        :return result: flow result
        :return err_msg: flow error message
        """

        # TODO(jidalong) deal exception
        flow_run = await self._client.read_flow_run(flow_run_id)
        state = flow_run.state
        parameters = flow_run.parameters.get("job_info", None)
        if state.is_final():
            if state.name.upper() == "FAILED":
                return state.name, parameters, None, state.message
            elif state.name.upper() != "COMPLETED":
                return state.name, parameters, None, None
            result = await state.result()
            return state.name, parameters, result, None
        else:
            return state.name, parameters, None

    def get_task_flow_list(self):
        """
        Get flow run list.

        :return result: flow run list
        """

        results = self.loop.run_until_complete(
            self.get_task_flow_list_by_client())
        return results

    async def get_task_flow_list_by_client(self):
        """
        Get flow run list by prefect client.

        :return result: flow run list
        """

        # TODO(jidalong) deal exception
        result = []
        flow_runs = await self._client.read_flow_runs()
        for flow_run in flow_runs:
            state = self.transform_to_qcos_state(flow_run.state.name)
            parameters = flow_run.parameters.get("job_info", None)
            id = flow_run.id
            result.append({"id": id, "state": state, "parameters": parameters})
        return result

    def delete_task_flow_run(self, flow_run_ids):
        """
        Delete flow run.

        :param flow_run_ids: flow run uuid list
        :return success_list: success list
        """

        success_list = self.loop.run_until_complete(
            self.delete_task_flow_run_by_client(flow_run_ids))
        return success_list

    async def delete_task_flow_run_by_client(self, flow_run_ids):
        """
        Delete flow run by client.

        :param flow_run_ids: flow run uuid list
        :return success_list: success_list
        """

        success_list = []
        try:
            for id in flow_run_ids:
                try:
                    flow_run = await self._client.read_flow_run(id)
                except ObjectNotFound:
                    logger.error(f"Prefect execute flow error: "
                                 f"can't find flow_run_id: {id}")
                    continue
                except Exception as e:
                    logger.error(f"Prefect execute flow error: {str(e)}")
                    continue
                state = flow_run.state
                if state.name.upper() != "RUNNING":
                    await self._client.delete_flow_run(id)
                    success_list.append(
                        {"id": id, "state": Constant.JOB_STATUS_DELETED})
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")

        return success_list

    def get_flow_info_by_backend(self, backend, transpiler_name):
        flow_info = {
            "deploy_name": None,
            "deploy_flow_func": None,
            "deploy_flow_path": None
        }
        if transpiler_name:
            # TODO(jidalong) update later
            flow_info["deploy_name"] = backend
            flow_info["deploy_flow_func"] = job_flow
            flow_info["deploy_flow_path"] = "../engine/job_engine.py"
        return flow_info
