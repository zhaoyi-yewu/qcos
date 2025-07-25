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
import logging
import uuid
from abc import ABC
from time import sleep
from pathlib import Path
from typing import Any

from prefect import get_client
from prefect.client.schemas.actions import WorkPoolCreate
from prefect.client.schemas.objects import WorkerStatus, StateType
from prefect.client.schemas.filters import FlowRunFilter, FlowRunFilterName, \
    FlowRunFilterState, FlowRunFilterTags
from prefect.exceptions import ObjectNotFound
from prefect.workers import ProcessWorker
from rich.console import Console

from qcos.common.constant import Constant, HttpCode
from qcos.common.library import Library
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
        self._sync_client = None
        self.loop = None
        self._console = None
        self.worker_status = False
        self.driver_manager = None
        self.parent_aggregation_jobs = []
        self.aggregation_jobs = {}

    def transform_to_qcos_state(self, state):
        _state = state.upper()
        if _state == Constant.PREFECT_STATE_CRASHED:
            return Constant.JOB_STATUS_FAILED
        elif _state in [Constant.PREFECT_STATE_SCHEDULED,
                        Constant.PREFECT_STATE_PENDING,
                        Constant.PREFECT_STATE_LATE]:
            return Constant.JOB_STATUS_QUEUED
        else:
            return _state

    def start(self):
        """
        Create work pools, queues and start workers
        """

        self._client = get_client()
        self._sync_client = get_client(sync_client=True)
        self._console = Console(quiet=True)
        self.loop = asyncio.new_event_loop()

        self.check_connection()
        self.loop.run_until_complete(self.create_pools())
        self.loop.run_until_complete(self.create_queues())
        self.loop.run_until_complete(self.start_workers())
        self.loop.run_until_complete(self.process_aggregation_job())

    def set_driver_manager(self, driver_manager):
        """
        Set driver manager

        :param driver_manager: driver manager
        """

        self.driver_manager = driver_manager

    def check_connection(self):
        """
        Check connection to prefect server
        """

        def is_connected():
            try:
                hello = self._sync_client.hello()
                if hello and hello.status_code == HttpCode.SUCCESS_OK:
                    return True
                return False
            except Exception as e:
                return False

        success, err_msg, results = Library.loop_with_timeout(
            is_connected, 60, 5)
        if not success or not results:
            raise TimeoutError("Connection to prefect server timeout")

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
            self.run_task_flow_by_client(deployment_id, args))

        return flow_run_id

    def get_flow_run_id_by_job_id(self, job_id):
        name = {"any_": [str(job_id)]}
        flow_run_filter = FlowRunFilter(name=FlowRunFilterName(**name))

        flow_runs = self._sync_client.read_flow_runs(
            flow_run_filter=flow_run_filter)
        if len(flow_runs) == 0:
            return None
        return flow_runs[0].id

    async def run_task_flow_by_client(self, deployment_id,
                                      args: dict[str, Any]):
        """
        Run flow by prefect client.

        :param deployment_id: deploy uuid
        :param args: flow function args in dict
        :return job_id: job uuid
        """

        job_id = args["job_info"]["data"].get("job_id")
        if job_id is None:
            job_id = uuid.uuid4()
            args["job_info"]["data"]["job_id"] = job_id
        tags = None
        if args["job_info"]["data"]["enable_circuit_aggregation"]:
            tags = ["enable_circuit_aggregation"]
        # TODO(jidalong) deal exception
        flow_run = await self._client.create_flow_run_from_deployment(
            name=str(job_id),
            deployment_id=deployment_id,
            parameters=args,
            tags=tags, )

        return job_id

    def get_task_flow_result(self, job_id):
        """
        Get flow run state and result.

        :param job_id: job uuid
        :return state: flow state
        :return parameters: flow parameters
        :return result: flow result
        :return err_msg: flow error message
        """
        flow_run_id = self.get_flow_run_id_by_job_id(job_id)
        if flow_run_id == None:
            raise ObjectNotFound(Exception("Job not found"))
        state, parameters, result, err_msg = self.loop.run_until_complete(
            self.get_task_flow_result_by_client(flow_run_id))
        return state, parameters, result, err_msg

    def has_flow(self, job_id):
        """
        Check if flow exists

        :param job_id: job uuid
        :return if job exists
        """

        exist = False
        flow_run_id = self.get_flow_run_id_by_job_id(job_id)
        if flow_run_id:
            exist = True
        return exist

    def update_flow(self, job_id, name=None, parameters=None,
                    variables=None):
        """
        Update flow

        :param job_id: job uuid
        :param name: flow name
        :param parameters: flow parameters
        :param variables: flow variables
        :return if flow exists
        """

        async def _update_flow(_flow_run_id,
                               _name=None,
                               _parameters=None,
                               _variables=None):
            success = True
            try:
                await self._client.update_flow_run(
                    _flow_run_id,
                    name=_name,
                    parameters=_parameters,
                    job_variables=_variables)
            except Exception:
                success = False
            return success

        flow_run_id = self.get_flow_run_id_by_job_id(job_id)
        if flow_run_id == None:
            return False

        return self.loop.run_until_complete(
            _update_flow(flow_run_id, name, parameters, variables))

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
        parameters = flow_run.parameters
        if state.is_final():
            if state.name.upper() == Constant.PREFECT_STATE_FAILED:
                return state.name, parameters, None, state.message
            elif state.name.upper() != Constant.PREFECT_STATE_COMPLETED:
                return state.name, parameters, None, None
            result = await state.result()
            return state.name, parameters, result, None
        else:
            return state.name, parameters, None, None

    def get_task_flow_list(self):
        """
        Get flow run list.

        :return result: flow run list
        """

        results = self.loop.run_until_complete(
            self.get_task_flow_list_by_client())
        return results

    async def get_task_flow_list_by_client(
            self,
            sort_fields=['-created'],
            reverse=False,
    ):
        """
        Get flow run list by prefect client.

        :param sort_fields: sort fields
        :param reverse: reverse order
        :return result: flow run list
        """

        # TODO(jidalong) deal exception
        results_list = []
        flow_runs = await self._client.read_flow_runs()
        sorted_flows = sorted(
            flow_runs,
            key=lambda sort_obj: Library.get_sorted_keys(
                sort_obj, sort_fields),
            reverse=reverse)
        for flow_run in sorted_flows:
            id = flow_run.name
            is_uuid, _ = Library.validate_values_uuid(
                id, "job_id")
            if not is_uuid:
                continue
            flow_state = flow_run.state.name.upper()
            state = self.transform_to_qcos_state(flow_state)
            parameters = flow_run.parameters
            results = None
            if flow_state == Constant.PREFECT_STATE_COMPLETED:
                results = await flow_run.state.result()
            results_list.append(
                {"id": id, "state": state, "parameters": parameters,
                 "results": results})
        return results_list

    def delete_task_flow_run(self, job_ids):
        """
        Delete flow run.

        :param job_ids: job uuid list
        :return success_list: success list
        """

        flow_run_ids = []
        for job_id in job_ids:
            flow_run_id = self.get_flow_run_id_by_job_id(job_id)
            if flow_run_id:
                flow_run_ids.append(flow_run_id)

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

    def list_flow_runs_by_filter(self, state, tags):
        s = {"type": {"any_": state}}
        t = {"all_": tags}

        flow_run_filter = FlowRunFilter(
            state=FlowRunFilterState(**s),
            tags=FlowRunFilterTags(**t))
        flow_runs = self._sync_client.read_flow_runs(
            flow_run_filter=flow_run_filter)
        return flow_runs

    def get_flow_info_by_backend(self, backend):
        flow_info = {
            "deploy_name": backend,
            "deploy_flow_func": job_flow,
            "deploy_flow_path": "../engine/job_engine.py"
        }
        return flow_info

    def run_callbacks(self, job_id, data, callbacks):
        """
        Run callbacks for job
        :param job_id: job id
        :param data: data to send
        :param callbacks: callbacks
        """
        return self.loop.run_until_complete(
            Library.async_run_callbacks(job_id, data, callbacks))

    async def process_aggregation_job(self):
        """
        Process aggregation job
        """

        def _update_aggregation_job(parent_id):
            try:
                # update sub jobs results into memory by parent job id
                state, parameters, results, error_message = (
                    self.get_task_flow_result(parent_id))
                if (state.upper() == Constant.PREFECT_STATE_COMPLETED
                        and results != None):
                    for job_id, sub_results in results["sub_results"].items():
                        self.aggregation_jobs[job_id] = sub_results
            except Exception as e:
                logger.error(f"Prefect get aggregation job error: {str(e)}")

        def _process_aggregation_job(flow_run):
            # 1.check current job is parent job or sub job
            aggregation_parm = {}
            if self.aggregation_jobs.get(flow_run.name):
                # 2.get sub job results stored in memory
                aggregation_parm["is_parent"] = False
                aggregation_parm["sub_results"] = self.aggregation_jobs.get(
                    flow_run.name)
                self.aggregation_jobs.pop(flow_run.name)
            else:
                # 3.get sub jobs which can aggregated with parent job
                sub_jobs = []

                state = [StateType.SCHEDULED]
                tags = ["enable_circuit_aggregation"]
                flow_runs = self.list_flow_runs_by_filter(state, tags)
                for sub_flow_run in flow_runs:
                    if sub_flow_run.parameters["job_info"]["data"][
                        "enable_circuit_aggregation"] and \
                            flow_run.parameters["job_info"]["data"][
                                "backend"] == \
                            sub_flow_run.parameters["job_info"]["data"][
                                "backend"] and \
                            sub_flow_run.work_pool_name == \
                            flow_run.work_pool_name:
                        if len(sub_jobs) >= Constant.MAX_AGGREGATION_JOBS:
                            break
                        sub_jobs.append(
                            {sub_flow_run.name: sub_flow_run.parameters})

                aggregation_parm["is_parent"] = True
                aggregation_parm["sub_jobs"] = sub_jobs
                # 4.record parent id in order to update related sub jobs result
                self.parent_aggregation_jobs.append(flow_run.name)

            # 5.resume flow run and send sub job info(aggregation_parm)
            self._sync_client.resume_flow_run(flow_run.id,
                                              run_input=aggregation_parm)

        def _process_aggregation_jobs():
            while True:
                # 1.periodic update sub jobs result
                for parent_id in self.parent_aggregation_jobs:
                    _update_aggregation_job(parent_id)

                # 2.periodic get paused flow runs
                # which are aggregation jobs running currently
                state = [StateType.PAUSED]
                tags = ["enable_circuit_aggregation"]
                flow_runs = self.list_flow_runs_by_filter(state, tags)

                for flow_run in flow_runs:
                    _process_aggregation_job(flow_run)
                sleep(Constant.DEFAULT_AGGREGATION_JOB_INTERVAL)

        aggregation_thread = threading.Thread(target=_process_aggregation_jobs,
                                              daemon=True)
        aggregation_thread.start()
