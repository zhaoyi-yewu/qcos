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
import threading
import logging
from abc import ABC
from time import sleep
from pathlib import Path
from typing import Any

from prefect import get_client
from prefect.client.schemas.actions import WorkPoolCreate
from prefect.client.schemas.objects import WorkerStatus, StateType
from prefect.client.schemas.filters import (
    ArtifactFilter,
    ArtifactFilterFlowRunId,
    ArtifactFilterKey,
    FlowRunFilter,
    FlowRunFilterName,
    FlowRunFilterState,
    FlowRunFilterTags,
)
from prefect.exceptions import ObjectNotFound
from prefect.states import State
from prefect.workers import ProcessWorker
from rich.console import Console

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import Library
from wy_qcos.engine.job_engine import job_flow

logger = logging.getLogger(__name__)


class TaskFlowManager(ABC):
    """Task manager based on prefect framework."""

    def __init__(self):
        """Init TaskFlowManager."""
        self._client = None
        self._sync_client = None
        self.loop = None
        self._console = None
        self.worker_status = False
        self.driver_manager = None
        self.device_manager = None
        self.parent_aggregation_jobs = []
        self.aggregation_jobs = {}

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

    def start(self):
        """Create work pools, queues and start workers."""
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
                hello = self._sync_client.hello()
                if hello and hello.status_code == HttpCode.SUCCESS_OK:
                    return True, None, None
                return False, "Connection failed", None
            except Exception as e:
                return False, str(e), None

        success, err_msg, _ = Library.loop_with_timeout(is_connected, 60, 5)
        if not success:
            raise TimeoutError("Connection to prefect server timeout")

    async def create_pools(self):
        """Create all work pools, each device has own work pools."""
        device_names = self.device_manager.get_devices().keys()
        create_workpools = [
            self.create_pool(pool_name) for pool_name in device_names
        ]
        return await asyncio.gather(*create_workpools)

    async def create_pool(self, pool_name):
        """Create work pool by prefect client.

        Args:
            pool_name: work pool name, using device name
        """
        pools = await self._client.read_work_pools()
        if not any(pool.name == pool_name for pool in pools):
            await self._client.create_work_pool(
                work_pool=WorkPoolCreate(
                    name=pool_name,
                    type=Constant.DEFAULT_JOB_POOL_TYPE,
                    concurrency_limit=Constant.DEFAULT_POOL_CONCURRENCY,
                )
            )

    async def create_queues(self):
        """Create all work queues under work pool.

        each priority has own work queue.
        """
        queues = await self._client.read_work_queues()
        device_names = self.device_manager.get_devices().keys()
        for pool_name in device_names:
            for priority in range(1, Constant.MAX_JOB_PRIORITY + 1):
                queue_name = f"{pool_name}_{priority}"
                if not any(queue.name == queue_name for queue in queues):
                    await self._client.create_work_queue(
                        name=queue_name,
                        work_pool_name=pool_name,
                        priority=priority,
                        concurrency_limit=Constant.DEFAULT_POOL_CONCURRENCY,
                    )

    async def start_workers(self):
        """Start all workers for work pool."""
        # start worker
        device_names = self.device_manager.get_devices().keys()
        for pool_name in device_names:
            worker_thread = threading.Thread(
                target=self.start_work, args=(pool_name,), daemon=True
            )
            worker_thread.start()

        # wait for all workers are online
        all_worker_status = {workpool: False for workpool in device_names}
        time = 0
        for workpool in device_names:
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
            time += Constant.DEFAULT_JOB_INTERVAL
            # timeout
            if time > Constant.DEFAULT_JOB_TIMEOUT:
                raise TimeoutError("Workers start timeout")

    def start_work(self, pool_name):
        """Start worker by prefect client.

        Args:
            pool_name: work pool name
        """
        worker = ProcessWorker(
            work_pool_name=pool_name,
            limit=Constant.DEFAULT_POOL_CONCURRENCY,
            work_queues=[
                f"{pool_name}_{str(i)}"
                for i in range(1, Constant.MAX_JOB_PRIORITY + 1)
            ],
        )
        asyncio.run(worker.start(printer=self._console.print))

    def deploy_task_flow(
        self,
        deploy_name: str,
        pool_name: str,
        priority: int,
        deploy_flow,
        path: str,
    ):
        """Deploy flow by prefect client.

        Args:
            deploy_name: deploy name
            pool_name: work pool name
            priority: priority
            deploy_flow: deploy flow function
            path: py path where the flow function relative to current path

        Returns:
            deploy uuid
        """
        # TODO(jidalong) deal exception
        queue_name = f"{pool_name}_{priority}"
        # registry deploy
        flow_name = deploy_flow.__name__
        deploy_id = deploy_flow.from_source(
            source=Path(__file__).parent,
            entrypoint=path + ":" + flow_name,
        ).deploy(
            name=deploy_name,
            work_pool_name=pool_name,
            work_queue_name=queue_name,
            print_next_steps=False,
            ignore_warnings=True,
        )
        return deploy_id

    def run_task_flow(self, deployment_id, args: dict[str, Any], tags=None):
        """Run flow.

        Args:
            deployment_id: deploy uuid
            args: flow function args in dict
            tags: prefect flow tags

        Returns:
            flow run uuid
        """
        flow_run_id = self.loop.run_until_complete(
            self.run_task_flow_by_client(deployment_id, args, tags=tags)
        )

        return flow_run_id

    def get_flow_run_id_by_job_id(self, job_id, tags=None):
        flow_run_filter_kwargs = {}

        if job_id is not None:
            name_filter = FlowRunFilterName(any_=[str(job_id)])
            flow_run_filter_kwargs["name"] = name_filter

        if Config.ENABLE_VIRT and tags is not None:
            tags_filter = FlowRunFilterTags(all_=tags)
            flow_run_filter_kwargs["tags"] = tags_filter
        # create flow run filter with flow_run_filter_kwargs
        flow_run_filter = FlowRunFilter(**flow_run_filter_kwargs)

        # get flow runs with flow_run_filter

        flow_runs = self._sync_client.read_flow_runs(
            flow_run_filter=flow_run_filter
        )
        if len(flow_runs) == 0:
            return None
        return flow_runs[0].id

    async def run_task_flow_by_client(
        self,
        deployment_id,
        args: dict[str, Any],
        tags=None,
    ):
        """Run flow by prefect client.

        Args:
            deployment_id: deploy uuid
            args: flow function args in dict
            tags: prefect flow tags

        Returns:
            job_id: job uuid
        """
        job_id = args["job_info"]["data"].get("job_id")
        if job_id is None:
            job_id = Library.create_uuid()
            args["job_info"]["data"]["job_id"] = job_id
        prefect_tags = None
        if args["job_info"]["data"]["circuit_aggregation"]:
            prefect_tags = [args["job_info"]["data"]["circuit_aggregation"]]
        if tags is not None:
            if prefect_tags is not None:
                prefect_tags.extend(tags)
            else:
                prefect_tags = tags
        # TODO(jidalong) deal exception
        await self._client.create_flow_run_from_deployment(
            name=str(job_id),
            deployment_id=deployment_id,
            parameters=args,
            tags=prefect_tags,
        )

        return job_id

    def get_task_flow_result(self, job_id, tags=None):
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
        state, parameters, result, err_msg = (
            self.get_task_flow_result_by_client(flow_run_id)
        )
        return state, parameters, result, err_msg

    def delete_flow_artifacts(self, flow_run_id):
        """Delete flow artifacts.

        Args:
            flow_run_id: flow run id
        """
        artifacts = self._sync_client.read_artifacts(
            artifact_filter=ArtifactFilter(
                flow_run_id=ArtifactFilterFlowRunId(any_=[flow_run_id])
            )
        )
        for artifact in artifacts:
            self._sync_client.delete_artifact(artifact.id)

    def get_job_artifact(self, job_id):
        """Get job artifact.

        Args:
            job_id: job id

        Returns:
            artifact
        """
        artifact = self.get_job_artifact_by_client(job_id)
        return artifact

    def get_job_artifact_by_client(self, job_id):
        """Get job artifact by client.

        Args:
            job_id: job id

        Returns:
            artifact
        """
        artifact = {}
        artifacts = self._sync_client.read_artifacts(
            artifact_filter=ArtifactFilter(
                key=ArtifactFilterKey(any_=[str(job_id)])
            )
        )
        if artifacts:
            _artifact = artifacts[0]
            if _artifact.type == "progress":
                artifact["artifact_id"] = _artifact.id
                artifact["progress"] = _artifact.data
        return artifact

    def has_flow(self, job_id):
        """Check if flow exists.

        Args:
            job_id: job uuid

        Returns:
            if job exists
        """
        exist = False
        flow_run_id = self.get_flow_run_id_by_job_id(job_id)
        if flow_run_id:
            exist = True
        return exist

    def update_flow(self, job_id, name=None, parameters=None, variables=None):
        """Update flow.

        Args:
            job_id: job uuid
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

        flow_run_id = self.get_flow_run_id_by_job_id(job_id)
        if flow_run_id is None:
            return False

        return self.loop.run_until_complete(
            _update_flow(flow_run_id, name, parameters, variables)
        )

    def get_task_flow_result_by_client(self, flow_run_id):
        """Get flow run state and result by prefect client.

        Args:
            flow_run_id: flow run uuid

        Returns:
            state_name, parameters, result, state_message
        """
        # TODO(jidalong) deal exception
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

            # set profiling
            profiling = parameters["job_info"]["data"].get("profiling", None)
            if profiling:
                if (
                    Constant.PROFILING_TYPE_ALL in profiling
                    or Constant.PROFILING_TYPE_SCHEDULING in profiling
                ):
                    flow_run_states = self._sync_client.read_flow_run_states(
                        flow_run_id
                    )
                    start_time = 0
                    running_time = 0
                    for flow_run_state in flow_run_states:
                        if (
                            flow_run_state.name.upper()
                            == Constant.PREFECT_STATE_SCHEDULED
                        ):
                            start_time = flow_run_state.timestamp
                        if (
                            flow_run_state.name.upper()
                            == Constant.PREFECT_STATE_RUNNING
                        ):
                            running_time = flow_run_state.timestamp
                    job_scheduling_duration = (
                        running_time.timestamp() - start_time.timestamp()
                    )
                    for _result in result:
                        _result["profiling"][
                            Constant.PROFILING_TYPE_SCHEDULING
                        ] = job_scheduling_duration
            return state.name, parameters, result, None
        else:
            return state.name, parameters, None, None

    def get_task_flow_list(self, tags=None):
        """Get flow run list.

        Args:
            tags: prefect flow tags

        Returns:
            flow run list
        """
        results = self.get_task_flow_list_by_client(tags=tags)
        return results

    def get_task_flow_list_by_client(
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

        # get artifacts info, eg: progress
        artifacts_map = {}
        artifacts = self._sync_client.read_artifacts(limit=Constant.FLOW_LIMIT)
        for artifact in artifacts:
            if artifact.key:
                artifacts_map[artifact.key] = {}
                if artifact.type == "progress":
                    artifacts_map[artifact.key]["artifact_id"] = artifact.id
                    artifacts_map[artifact.key]["progress"] = artifact.data

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
            artifact = artifacts_map.get(id, {})
            progress = artifact.get("progress", -1)
            results_list.append({
                "id": id,
                "state": state,
                "parameters": parameters,
                "progress": progress,
                "results": results,
            })
        return results_list

    def get_task_flow_run(self, job_id, tags=None):
        """Get flow run.

        Args:
            job_id: job id
            tags: prefect flow tags
        Returns:
            flow run.
        """
        flow_run_id = self.get_flow_run_id_by_job_id(job_id, tags)
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

    def delete_task_flow_run(self, job_ids, tags=None):
        """Delete flow run.

        Args:
            job_ids: job uuid list
            tags: prefect flow tags

        Returns:
            success list.
        """
        flow_run_ids = []
        for job_id in job_ids:
            flow_run_id = self.get_flow_run_id_by_job_id(job_id, tags=tags)
            if flow_run_id:
                flow_run_ids.append((flow_run_id, job_id))

        success_list = self.delete_task_flow_run_by_client(flow_run_ids)
        return success_list

    def delete_task_flow_run_by_client(self, flow_run_ids):
        """Delete flow run by client.

        Args:
            flow_run_ids: flow run uuid list

        Returns:
            success_list.
        """
        success_list = []
        for flow_run_id, job_id in flow_run_ids:
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
                        "id": job_id,
                        "state": Constant.JOB_STATUS_DELETED,
                    })
                    # delete flow artifact
                    self.delete_flow_artifacts(flow_run_id)
                except Exception as e:
                    logger.error(f"Prefect delete_flow_run error: {str(e)}")
        return success_list

    def cancel_task_flow_run(self, job_ids, tags=None):
        """Cancel flow run.

        Args:
            job_ids: job uuid list
            tags: prefect flow tags

        Returns:
            success list.
        """
        flow_run_ids = []
        for job_id in job_ids:
            flow_run_id = self.get_flow_run_id_by_job_id(job_id, tags=tags)
            if flow_run_id:
                flow_run_ids.append((flow_run_id, job_id))

        success_list = self.cancel_task_flow_run_by_client(flow_run_ids)
        return success_list

    def cancel_task_flow_run_by_client(self, flow_run_ids):
        """Cancel flow run by client.

        Args:
            flow_run_ids: flow run uuid list

        Returns:
            success list.
        """
        success_list = []
        try:
            for flow_run_id, job_id in flow_run_ids:
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
                            "id": job_id,
                            "state": Constant.JOB_STATUS_CANCELLED,
                        })
                        # delete flow artifact
                        self.delete_flow_artifacts(flow_run_id)
                    except Exception as e:
                        logger.error(
                            f"Prefect delete_flow_run error: {str(e)}"
                        )
        except Exception as e:
            logger.error(f"Prefect execute flow error: {str(e)}")

        return success_list

    def get_flow_runs_with_filters(self, states=None, tags=None):
        """Get flow runs with filters.

        Args:
            states: flow states
            tags: prefect flow tags

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
        if Config.ENABLE_VIRT and tags is not None:
            tags_filter = FlowRunFilterTags(all_=tags)
            flow_run_filter_kwargs["tags"] = tags_filter

        # create flow run filter with flow_run_filter_kwargs
        flow_run_filter = FlowRunFilter(**flow_run_filter_kwargs)

        # get flow runs with flow_run_filter
        flow_runs = self._sync_client.read_flow_runs(
            flow_run_filter=flow_run_filter
        )
        return flow_runs

    def get_flow_info_by_backend(self, backend):
        flow_info = {
            "deploy_name": backend,
            "deploy_flow_func": job_flow,
            "deploy_flow_path": "../engine/job_engine.py",
        }
        return flow_info

    def run_callbacks(self, data, callbacks):
        """Run callbacks for job.

        Args:
            data: data to send
            callbacks: callbacks.
        """
        return self.loop.run_until_complete(
            Library.async_run_callbacks(data, callbacks)
        )

    async def process_aggregation_job(self):
        """Process aggregation job."""

        def _update_aggregation_job(parent_id):
            try:
                # update sub jobs results into memory by parent job id
                state, parameters, results, error_message = (
                    self.get_task_flow_result(parent_id)
                )
                if (
                    state.upper() == Constant.PREFECT_STATE_COMPLETED
                    and results is not None
                ):
                    if results[0]["sub_results"] is not None:
                        for job_id, sub_results in results[0][
                            "sub_results"
                        ].items():
                            self.aggregation_jobs[job_id] = [sub_results]
            except Exception as e:
                logger.error(f"Prefect get aggregation job error: {str(e)}")

        def _process_aggregation_job(flow_run):
            # 1.check current job is parent job or sub job
            aggregation_parm = {}
            if self.aggregation_jobs.get(flow_run.name):
                # 2.get sub job results stored in memory
                aggregation_parm["is_parent"] = False
                aggregation_parm["sub_results"] = self.aggregation_jobs.get(
                    flow_run.name
                )
                self.aggregation_jobs.pop(flow_run.name)
            else:
                # 3.get sub jobs which can aggregated with parent job
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
                        == sub_flow_run.parameters["job_info"]["data"][
                            "backend"
                        ]
                        and sub_flow_run.work_pool_name
                        == flow_run.work_pool_name
                    ):
                        if len(sub_jobs) >= Constant.MAX_AGGREGATION_JOBS:
                            break
                        sub_jobs[sub_flow_run.name] = sub_flow_run.parameters

                aggregation_parm["is_parent"] = True
                aggregation_parm["sub_jobs"] = sub_jobs
                # 4.record parent id in order to update related sub jobs result
                self.parent_aggregation_jobs.append(flow_run.name)

            # 5.resume flow run and send sub job info(aggregation_parm)
            self._sync_client.resume_flow_run(
                flow_run.id, run_input=aggregation_parm
            )

        def _process_aggregation_jobs():
            while True:
                # 1.periodic update sub jobs result
                for parent_id in self.parent_aggregation_jobs:
                    _update_aggregation_job(parent_id)

                # 2.periodic get paused flow runs
                # which are aggregation jobs running currently
                states = [StateType.PAUSED]
                tags = [Constant.AGGREGATION_TYPE_EXTERNAL]
                flow_runs = self.get_flow_runs_with_filters(states, tags)

                for flow_run in flow_runs:
                    _process_aggregation_job(flow_run)
                sleep(Constant.DEFAULT_AGGREGATION_JOB_INTERVAL)

        aggregation_thread = threading.Thread(
            target=_process_aggregation_jobs, daemon=True
        )
        aggregation_thread.start()
