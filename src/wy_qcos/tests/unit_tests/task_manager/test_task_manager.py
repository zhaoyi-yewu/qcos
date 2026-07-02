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
import pytest
import threading
import time
import unittest
from unittest import mock
from unittest.mock import patch, Mock, AsyncMock

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.drivers.device_manager import DeviceManager
from wy_qcos.drivers.driver_manager import DriverManager
from wy_qcos.task_manager.task_manager import TaskFlowManager
from wy_qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)

driver_manager = DriverManager()
device_manager = DeviceManager(Config, driver_manager)


class TestTaskFlowManager(unittest.TestCase):
    @patch.object(TaskFlowManager, "check_connection")
    def setUp(self, mock_check_connection):
        self.task_manager = TaskFlowManager()

    def test_convert_to_qcos_state(self):
        # case 1: JOB_STATUS_FAILED
        state = Constant.PREFECT_STATE_CRASHED
        v = self.task_manager.convert_to_qcos_state(state)
        self.assertEqual(v, Constant.JOB_STATUS_FAILED)

        # case 2: JOB_STATUS_QUEUED
        state = Constant.PREFECT_STATE_SCHEDULED
        v = self.task_manager.convert_to_qcos_state(state)
        self.assertEqual(v, Constant.JOB_STATUS_QUEUED)

        # case 3: unknown status
        state = "unknown"
        v = self.task_manager.convert_to_qcos_state(state)
        self.assertEqual(v, state.upper())

    def test_check_connection(self):
        mock_prefect_client = mock.Mock()
        mock_hello_return = mock.Mock()
        mock_prefect_client.hello.return_value = mock_hello_return

        # case1: success
        mock_hello_return.status_code = HttpCode.SUCCESS_OK
        self.task_manager._sync_client = mock_prefect_client
        self.task_manager.check_connection()

    def test_set_driver_manager(self):
        self.task_manager.set_driver_manager("driver_manager")
        self.assertEqual(self.task_manager.driver_manager, "driver_manager")

    def test_set_device_manager(self):
        self.task_manager.set_device_manager("device_manager")
        self.assertEqual(self.task_manager.device_manager, "device_manager")

    def test_create_pools(self):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client
        self.task_manager.set_device_manager(device_manager)
        results = asyncio.run(self.task_manager.create_pools(["pool"]))
        assert results is not None

    def test_create_pool(self):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client
        mock_client.read_work_pools.return_value = []
        mock_client.create_work_pool.return_value = []
        results = asyncio.run(self.task_manager.create_pool("1", 1))
        assert results is None

    def test_create_queues(self):
        mock_client = AsyncMock()
        mock_client.read_work_queues.return_value = []
        mock_client.create_work_queue.return_value = []
        self.task_manager._client = mock_client
        self.task_manager.set_device_manager(device_manager)
        results = asyncio.run(self.task_manager.create_queues(["queue"]))
        assert results is None

    @patch("wy_qcos.task_manager.task_manager.job_flow")
    def test_create_deployments(self, mock_job_flow):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client

        device_name = "dummy"
        device_names = [device_name]
        # mock devices
        mock_device_manager = Mock()
        mock_dummy_device = Mock()
        mock_qutip_sim_device = Mock()
        mock_dummy_driver = Mock()
        mock_qutip_sim_driver = Mock()
        mock_devices = {
            "dummy": mock_dummy_device,
            "qutip_sim": mock_qutip_sim_device,
        }
        mock_device_manager.get_devices.return_value = mock_devices
        self.task_manager.set_device_manager(mock_device_manager)
        mock_dummy_driver.get_name.return_name = "dummy"
        mock_qutip_sim_driver.get_name.return_name = "qutip_sim"
        mock_dummy_device.get_driver.return_value = mock_dummy_driver
        mock_qutip_sim_device.get_driver.return_value = mock_qutip_sim_driver
        mock_job_flow.__name__ = "test_flow"
        deployment_configs = self.task_manager.generate_deployment_configs(
            device_names
        )

        # Mock flow object from job_flow.from_source
        mock_flow = Mock()
        mock_deployment = Mock()
        mock_flow.deploy = AsyncMock(return_value=mock_deployment)

        # Mock job_flow.from_source
        mock_job_flow.from_source = AsyncMock(return_value=mock_flow)
        # run async method
        self.task_manager.deployments = asyncio.run(
            self.task_manager.create_deployments(deployment_configs)
        )
        # verify job_flow.from_source is called
        assert mock_job_flow.from_source.called
        # verify flow.deploy is called
        assert mock_flow.deploy.called
        # verify deployments is not None
        assert self.task_manager.deployments is not None

        # verify deployment info
        deployment = self.task_manager.get_deployment(device_name)
        assert deployment is not None

    @patch("multiprocessing.Process")
    def test_start_workers(self, mock_process_class):
        # mock processes
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.is_alive.return_value = True
        mock_process_class.return_value = mock_process

        # mock devices
        mock_device_manager = Mock()
        mock_dummy_device = Mock()
        mock_qutip_sim_device = Mock()
        mock_dummy_driver = Mock()
        mock_qutip_sim_driver = Mock()
        mock_devices = {
            "dummy": mock_dummy_device,
            "qutip_sim": mock_qutip_sim_device,
        }
        mock_device_manager.get_devices.return_value = mock_devices
        self.task_manager.set_device_manager(mock_device_manager)
        mock_dummy_driver.get_name.return_name = "dummy"
        mock_qutip_sim_driver.get_name.return_name = "qutip_sim"
        mock_dummy_device.get_driver.return_value = mock_dummy_driver
        mock_qutip_sim_device.get_driver.return_value = mock_qutip_sim_driver
        # start workers
        self.task_manager.start_workers()

        # verify results
        assert mock_process.daemon is True
        mock_process.start.assert_called()
        mock_process.start.call_count == len(mock_devices)

    def test_run_task_flow(self):
        async def mock_run_flow_by_client_impl(*args, **kwargs):
            return "test_flow_run_id"

        with patch.object(
            TaskFlowManager,
            "run_flow_by_client",
            side_effect=mock_run_flow_by_client_impl,
        ):
            mock_loop = Mock()
            mock_loop.is_running.return_value = False
            mock_loop.run_until_complete.side_effect = (
                lambda coro: asyncio.run(coro)
            )
            self.task_manager.loop = mock_loop

            deployment_id = ConstantForTest.deployment_id
            flow_run_id = self.task_manager.run_flow(
                deployment_id,
                ConstantForTest.args,
                tags=None,
                work_queue_name=None,
            )
            assert flow_run_id is not None

    def test_get_flow_run_id_by_job_id(self):
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        mock_client.read_flow_runs.return_value = []
        ans = self.task_manager.get_flow_run_id_by_job_id(
            ConstantForTest.job_id
        )
        assert ans is None

    def test_run_task_flow_by_client(self):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client
        mock_run = AsyncMock()
        mock_client.create_flow_run_from_deployment.return_value = mock_run
        flow_run_id = asyncio.run(
            self.task_manager.run_flow_by_client(
                ConstantForTest.job_id, ConstantForTest.args, None
            )
        )
        assert flow_run_id is not None

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_get_task_flow_result(self, mock_get_flow_run_id_by_job_id):
        mock_client = Mock()
        mock_run = Mock()
        mock_run.get_task_flow_result_by_client.return_value = mock_client
        mock_get_flow_run_id_by_job_id.return_value = None
        with pytest.raises(Exception) as context:
            self.task_manager.get_flow_result(ConstantForTest.job_id)
        assert str(context.value) == "None"

    def test_update_flow(self):
        mock_client = Mock()
        mock_client.update_flow_run = AsyncMock(return_value=None)
        self.task_manager._client = mock_client

        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.side_effect = lambda coro: asyncio.run(
            coro
        )
        self.task_manager.loop = mock_loop

        # Test successful update
        flow_run_id = "test_flow_run_id"
        success, err_msg = self.task_manager.update_flow(flow_run_id)
        assert success is True
        assert err_msg is None
        mock_client.update_flow_run.assert_called()

    def test_get_task_flow_result_by_client(self):
        mock_client = Mock()
        mock_run = Mock()
        self.task_manager._sync_client = mock_client
        mock_run.read_flow_run.return_value = {}
        results = self.task_manager.get_flow_result_by_client(
            ConstantForTest.job_id
        )
        assert results is not None

    def test_get_task_flow_list(self):
        mock_client = Mock()
        self.task_manager.get_flow_list_by_client = mock_client
        mock_client.get_task_flow_list_by_client.return_value = []
        results = self.task_manager.get_flow_list(None)
        assert results is not None

    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    def test_get_task_flow_list_by_client(
        self,
        mock_get_flow_runs_with_filters,
    ):
        mock_client = Mock()
        mock_get_flow_runs_with_filters.return_value = []
        self.task_manager._sync_client = mock_client
        mock_client.read_artifacts.return_value = []
        results = self.task_manager.get_flow_list_by_client(tags=None)
        assert results is not None

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_get_task_flow_run(self, mock_get_flow_run_id_by_job_id):
        mock_get_flow_run_id_by_job_id.return_value = 1
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        mock_client.read_artifacts.return_value = []
        mock_client.read_flow_runs.return_value = []
        results = self.task_manager.get_flow_run(1)
        assert results is not None

    @patch.object(TaskFlowManager, "delete_flow_runs")
    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_delete_task_flow_run(
        self,
        mock_get_flow_run_id_by_job_id,
        mock_delete,
    ):
        mock_get_flow_run_id_by_job_id.return_value = ConstantForTest.job_id
        mock_run = Mock()
        mock_client = Mock()
        mock_delete.return_value = ConstantForTest.job_id
        mock_client.delete_task_flow_run_by_client.return_value = mock_run
        self.task_manager.loop = mock_client
        success_list = self.task_manager.delete_flow_runs(
            ConstantForTest.job_ids
        )
        assert success_list

    def test_delete_task_flow_run_by_client(self):
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        mock_server = Mock()
        mock_server.state = Mock()
        mock_server.state.name = "running"
        mock_client.read_flow_run.return_value = mock_server
        results = self.task_manager.delete_flow_runs(
            ConstantForTest.flow_run_ids
        )
        assert results is not None

    def test_process_aggregation_job(self):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client
        results = asyncio.run(self.task_manager.process_aggregation_job())
        assert results is None

    @patch.object(TaskFlowManager, "cancel_flow_runs")
    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_cancel_task_flow_run(
        self,
        mock_get_flow_run_id_by_job_id,
        mock_cancel_flow_runs,
    ):
        mock_get_flow_run_id_by_job_id.return_value = "1234"
        mock_cancel_flow_runs.return_value = None
        success_list = self.task_manager.cancel_flow_runs(
            ConstantForTest.job_ids, None
        )
        assert success_list is None

    def test_convert_to_prefect_states(self):
        states = [
            Constant.PREFECT_STATE_RUNNING,
            Constant.PREFECT_STATE_SCHEDULED,
            Constant.PREFECT_STATE_PENDING,
            Constant.PREFECT_STATE_FAILED,
            Constant.PREFECT_STATE_COMPLETED,
            Constant.PREFECT_STATE_CRASHED,
            Constant.PREFECT_STATE_CANCELLING,
            Constant.PREFECT_STATE_CANCELLED,
            Constant.PREFECT_STATE_PAUSED,
        ]
        prefect_states = self.task_manager.convert_to_prefect_states(states)
        assert len(prefect_states) == 9

    def test_cancel_task_flow_run_by_client(self):
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        mock_server = Mock()
        mock_server.state = Mock()
        mock_server.state.name = "run"
        mock_client.read_flow_run.return_value = mock_server
        mock_client.set_flow_run_state.return_value = Mock()
        success_list = self.task_manager.cancel_flow_runs(
            ConstantForTest.flow_run_ids
        )
        assert not success_list

    def test_run_manage_task_flow(self):
        async def run_manage_task_flow_by_client(*args, **kwargs):
            return True, None

        with patch.object(
            TaskFlowManager,
            "run_manage_task_flow_by_client",
            side_effect=run_manage_task_flow_by_client,
        ):
            mock_loop = Mock()
            mock_loop.is_running.return_value = False
            mock_loop.run_until_complete.side_effect = (
                lambda coro: asyncio.run(coro)
            )
            self.task_manager.loop = mock_loop

            deployment_id = ConstantForTest.deployment_id
            args = {
                "device_mgr_info": {
                    "method": "set_device_options",
                    "device_name": "dummy",
                }
            }
            succ, details = self.task_manager.run_manage_task_flow(
                deployment_id,
                args,
                work_queue_name=None,
            )
            assert succ
            assert details is None

    def test_run_manage_task_flow_by_client(self):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client
        mock_run = AsyncMock()
        mock_client.create_flow_run_from_deployment.return_value = mock_run
        deployment_id = ConstantForTest.deployment_id
        args = {
            "device_mgr_info": {
                "method": "set_device_options",
                "device_name": "dummy",
            }
        }
        succ, details = asyncio.run(
            self.task_manager.run_manage_task_flow_by_client(
                deployment_id,
                args,
                work_queue_name=None,
            )
        )
        assert succ
        assert details is None

    def test_create_pool_existing(self):
        mock_client = AsyncMock()
        existing_pool = Mock()
        existing_pool.name = "pool1"
        mock_client.read_work_pools.return_value = [existing_pool]
        self.task_manager._client = mock_client

        asyncio.run(self.task_manager.create_pool("pool1", 1))

        mock_client.create_work_pool.assert_not_called()

    def test_create_queues_existing(self):
        mock_client = AsyncMock()
        existing_queue = Mock()
        existing_queue.name = "queue_1"
        mock_client.read_work_queues.return_value = [existing_queue]
        self.task_manager._client = mock_client

        asyncio.run(self.task_manager.create_queues(["queue"]))

        assert mock_client.create_work_queue.call_count == (
            Constant.MAX_JOB_PRIORITY - 1
        )

    def test_run_flow_when_loop_running(self):
        self.task_manager.loop = Mock()
        self.task_manager.loop.is_running.return_value = True
        future = Mock()
        future.result.return_value = "flow-id"

        with patch(
            "wy_qcos.task_manager.task_manager."
            "asyncio.run_coroutine_threadsafe",
            return_value=future,
        ):
            result = self.task_manager.run_flow(
                "deploy-id",
                {"job_info": {"data": {"job_id": "job-id"}}},
            )

        assert result == "flow-id"

    def test_run_manage_task_flow_when_loop_running(self):
        self.task_manager.loop = Mock()
        self.task_manager.loop.is_running.return_value = True
        future = Mock()
        future.result.return_value = (True, {"a": 1})

        with patch(
            "wy_qcos.task_manager.task_manager."
            "asyncio.run_coroutine_threadsafe",
            return_value=future,
        ):
            success, details = self.task_manager.run_manage_task_flow(
                "deploy-id",
                {"device_mgr_info": {"method": "x"}},
            )

        assert success is True
        assert details == {"a": 1}

    def test_get_flow_run_id_by_job_id_found(self):
        mock_client = Mock()
        mock_flow = Mock(id="flow-id")
        mock_client.read_flow_runs.return_value = [mock_flow]
        self.task_manager._sync_client = mock_client

        assert (
            self.task_manager.get_flow_run_id_by_job_id("job-id") == "flow-id"
        )

    def test_run_flow_by_client_with_tags_and_aggregation(self):
        mock_client = AsyncMock()
        mock_flow = Mock(id="flow-id")
        mock_client.create_flow_run_from_deployment.return_value = mock_flow
        self.task_manager._client = mock_client
        args = {
            "job_info": {
                "data": {
                    "job_id": "job-id",
                    "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
                }
            }
        }

        result = asyncio.run(
            self.task_manager.run_flow_by_client(
                "deploy-id",
                args,
                tags=["extra"],
                work_queue_name="queue-1",
            )
        )

        assert result == "flow-id"
        kwargs = mock_client.create_flow_run_from_deployment.call_args.kwargs
        assert kwargs["tags"] == [Constant.AGGREGATION_TYPE_EXTERNAL, "extra"]

    def test_run_manage_task_flow_by_client_get_device_options(self):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client
        mock_device = Mock()
        mock_device.get_device_options_info.return_value = {"opt": 1}
        mock_dm = Mock()
        mock_dm.get_devices.return_value = {"dummy": mock_device}
        self.task_manager.device_manager = mock_dm
        args = {
            "device_mgr_info": {
                "method": "get_device_options",
                "device_name": "dummy",
            }
        }

        succ, details = asyncio.run(
            self.task_manager.run_manage_task_flow_by_client(
                ConstantForTest.deployment_id,
                args,
                work_queue_name=None,
            )
        )

        assert succ is True
        assert details == {"opt": 1}

    def test_get_flow_result_by_client_completed(self):
        mock_client = Mock()
        mock_state = Mock()
        mock_state.is_final.return_value = True
        mock_state.name = Constant.PREFECT_STATE_COMPLETED
        mock_state.result.return_value = {"ok": True}
        mock_flow = Mock(state=mock_state, parameters={"a": 1})
        mock_client.read_flow_run.return_value = mock_flow
        self.task_manager._sync_client = mock_client

        state, parameters, result, err = (
            self.task_manager.get_flow_result_by_client("flow-id")
        )
        assert state == Constant.PREFECT_STATE_COMPLETED
        assert parameters == {"a": 1}
        assert result == {"ok": True}
        assert err is None

    def test_get_flow_list_by_client_filters_invalid_and_monitor(self):
        monitor_flow = Mock()
        monitor_flow.name = Constant.DEVICE_MONITOR_PREFIX + "abc"
        invalid_flow = Mock()
        invalid_flow.name = "not-uuid"
        completed_flow = Mock()
        completed_flow.name = ConstantForTest.job_id
        completed_flow.state = Mock()
        completed_flow.state.name = Constant.PREFECT_STATE_COMPLETED
        completed_flow.state.result.return_value = {"done": True}
        completed_flow.parameters = {"x": 1}

        with patch.object(
            self.task_manager,
            "get_flow_runs_with_filters",
            return_value=[monitor_flow, invalid_flow, completed_flow],
        ):
            result = self.task_manager.get_flow_list_by_client(tags=None)

        assert len(result) == 1
        assert result[0]["id"] == ConstantForTest.job_id
        assert result[0]["results"] == {"done": True}

    def test_get_flow_run_object_not_found(self):
        mock_client = Mock()
        mock_client.read_flow_run.side_effect = Exception("boom")
        self.task_manager._sync_client = mock_client

        assert self.task_manager.get_flow_run("flow-id") is None

    def test_delete_flow_runs_success_and_skip_running(self):
        mock_client = Mock()
        running_flow = Mock()
        running_flow.state = Mock(name="state")
        running_flow.state.name = Constant.PREFECT_STATE_RUNNING
        done_flow = Mock()
        done_flow.state = Mock(name="state")
        done_flow.state.name = Constant.PREFECT_STATE_COMPLETED
        mock_client.read_flow_run.side_effect = [running_flow, done_flow]
        self.task_manager._sync_client = mock_client

        result = self.task_manager.delete_flow_runs(["run", "done"])

        assert result == [
            {"flow_run_id": "done", "state": Constant.JOB_STATUS_DELETED}
        ]

    def test_delete_task_flow_by_name_not_found(self):
        mock_client = Mock()
        mock_client.read_flows.return_value = []
        self.task_manager._sync_client = mock_client

        assert self.task_manager.delete_task_flow_by_name("missing") is None

    def test_get_flow_runs_with_filters_pool_name(self):
        mock_client = Mock()
        mock_client.read_flow_runs.return_value = ["flow"]
        self.task_manager._sync_client = mock_client

        result = self.task_manager.get_flow_runs_with_filters(
            states=["RUNNING"],
            tags=["tag1"],
            pool_name="pool1",
        )

        assert result == ["flow"]
        mock_client.read_flow_runs.assert_called_once()

    # --- Aggregation-related test cases ---

    def test_run_flow_by_client_with_internal_aggregation(self):
        """Test run_flow_by_client sets internal aggregation tag."""
        mock_client = AsyncMock()
        mock_flow = Mock(id="flow-id")
        mock_client.create_flow_run_from_deployment.return_value = mock_flow
        self.task_manager._client = mock_client
        args = {
            "job_info": {
                "data": {
                    "job_id": "job-id",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_INTERNAL
                    ),
                }
            }
        }

        result = asyncio.run(
            self.task_manager.run_flow_by_client(
                "deploy-id",
                args,
                tags=None,
                work_queue_name="queue-1",
            )
        )

        assert result == "flow-id"
        kwargs = mock_client.create_flow_run_from_deployment.call_args.kwargs
        assert kwargs["tags"] == [Constant.AGGREGATION_TYPE_INTERNAL]

    def test_run_flow_by_client_with_external_aggregation_no_extra_tags(
        self,
    ):
        """Test sets external aggregation tag without extra tags."""
        mock_client = AsyncMock()
        mock_flow = Mock(id="flow-id")
        mock_client.create_flow_run_from_deployment.return_value = mock_flow
        self.task_manager._client = mock_client
        args = {
            "job_info": {
                "data": {
                    "job_id": "job-id",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_EXTERNAL
                    ),
                }
            }
        }

        result = asyncio.run(
            self.task_manager.run_flow_by_client(
                "deploy-id",
                args,
                tags=None,
                work_queue_name="queue-1",
            )
        )

        assert result == "flow-id"
        kwargs = mock_client.create_flow_run_from_deployment.call_args.kwargs
        assert kwargs["tags"] == [Constant.AGGREGATION_TYPE_EXTERNAL]

    def test_run_flow_by_client_with_none_aggregation(self):
        """Test sets no aggregation tag when aggregation is None."""
        mock_client = AsyncMock()
        mock_flow = Mock(id="flow-id")
        mock_client.create_flow_run_from_deployment.return_value = mock_flow
        self.task_manager._client = mock_client
        args = {
            "job_info": {
                "data": {
                    "job_id": "job-id",
                    "circuit_aggregation": None,
                }
            }
        }

        result = asyncio.run(
            self.task_manager.run_flow_by_client(
                "deploy-id",
                args,
                tags=None,
                work_queue_name="queue-1",
            )
        )

        assert result == "flow-id"
        kwargs = mock_client.create_flow_run_from_deployment.call_args.kwargs
        assert kwargs["tags"] is None

    def test_run_flow_by_client_with_internal_agg_and_extra_tags(self):
        """Test merges internal aggregation tag with extra tags."""
        mock_client = AsyncMock()
        mock_flow = Mock(id="flow-id")
        mock_client.create_flow_run_from_deployment.return_value = mock_flow
        self.task_manager._client = mock_client
        args = {
            "job_info": {
                "data": {
                    "job_id": "job-id",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_INTERNAL
                    ),
                }
            }
        }

        result = asyncio.run(
            self.task_manager.run_flow_by_client(
                "deploy-id",
                args,
                tags=["extra_tag"],
                work_queue_name="queue-1",
            )
        )

        assert result == "flow-id"
        kwargs = mock_client.create_flow_run_from_deployment.call_args.kwargs
        assert kwargs["tags"] == [
            Constant.AGGREGATION_TYPE_INTERNAL,
            "extra_tag",
        ]

    def test_run_flow_by_client_sets_job_enqueue_at(self):
        """Test run_flow_by_client sets job_enqueue_at timestamp."""
        mock_client = AsyncMock()
        mock_flow = Mock(id="flow-id")
        mock_client.create_flow_run_from_deployment.return_value = mock_flow
        self.task_manager._client = mock_client
        args = {
            "job_info": {
                "data": {
                    "job_id": "job-id",
                    "circuit_aggregation": None,
                }
            }
        }

        asyncio.run(
            self.task_manager.run_flow_by_client(
                "deploy-id",
                args,
                tags=None,
                work_queue_name="queue-1",
            )
        )

        kwargs = mock_client.create_flow_run_from_deployment.call_args.kwargs
        assert "job_enqueue_at" in kwargs["parameters"]["job_info"]["data"]

    @patch.object(TaskFlowManager, "get_flow_run")
    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    def test_process_aggregation_job_subscribes_and_processes(
        self, mock_get_flow_runs, mock_get_flow_run
    ):
        """Test starts subscription thread and processes agg messages."""
        mock_redis = Mock()
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub

        # Simulate one aggregation message then stop

        def mock_listen_side_effect():
            yield {"type": "psubscribe", "pattern": None, "data": None}
            yield {
                "type": "pmessage",
                "pattern": "qcos/job_agg/*",
                "channel": "qcos/job_agg/flow-1",
                "data": json.dumps({
                    "flow_run_id": "flow-run-id-1",
                    "aggregation_type": Constant.AGGREGATION_TYPE_EXTERNAL,
                    "cancel": False,
                }),
            }
            # Stop the thread after processing
            raise StopIteration()

        mock_pubsub.listen.side_effect = mock_listen_side_effect
        mock_pubsub.psubscribe.return_value = None

        mock_flow_run = Mock()
        mock_flow_run.id = "flow-run-id-1"
        mock_flow_run.state_name = "Paused"
        mock_flow_run.work_pool_name = "device|dummy"
        mock_flow_run.parameters = {
            "job_info": {
                "data": {
                    "backend": "dummy",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_EXTERNAL
                    ),
                }
            }
        }
        mock_get_flow_run.return_value = mock_flow_run
        mock_get_flow_runs.return_value = []

        mock_sync_client = Mock()
        self.task_manager._sync_client = mock_sync_client
        mock_sync_client.resume_flow_run.return_value = None

        # Replace redis_instance temporarily
        original_redis = self.task_manager.redis_instance
        self.task_manager.redis_instance = mock_redis

        try:
            asyncio.run(self.task_manager.process_aggregation_job())
        except StopIteration:
            pass
        finally:
            self.task_manager.redis_instance = original_redis

        mock_redis.pubsub.assert_called_once()
        mock_pubsub.psubscribe.assert_called_once()

    def test_process_aggregation_job_cancel_message(self):
        """Test process_aggregation_job handles cancel messages."""
        mock_redis = Mock()
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub

        cancel_event = threading.Event()

        def mock_listen_side_effect():
            yield {"type": "psubscribe", "pattern": None, "data": None}
            yield {
                "type": "pmessage",
                "pattern": "qcos/job_agg/*",
                "channel": "qcos/job_agg/flow-1",
                "data": json.dumps({
                    "flow_run_id": "flow-run-id-1",
                    "cancel": True,
                    "sub_flow_list": ["sub-flow-1", "sub-flow-2"],
                }),
            }
            cancel_event.wait(timeout=5)
            raise StopIteration()

        mock_pubsub.listen.side_effect = mock_listen_side_effect
        mock_pubsub.psubscribe.return_value = None

        mock_sync_client = Mock()
        self.task_manager._sync_client = mock_sync_client

        original_redis = self.task_manager.redis_instance
        self.task_manager.redis_instance = mock_redis

        try:
            asyncio.run(self.task_manager.process_aggregation_job())
            # Wait for the aggregation thread to process the cancel message
            for _ in range(50):
                if mock_sync_client.set_flow_run_state.call_count >= 2:
                    break
                time.sleep(0.1)
            cancel_event.set()
        except StopIteration:
            pass
        finally:
            self.task_manager.redis_instance = original_redis

        # Cancel should call set_flow_run_state for each sub flow
        assert mock_sync_client.set_flow_run_state.call_count == 2

    @patch.object(TaskFlowManager, "get_flow_run")
    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    def test_process_aggregation_job_filters_sub_jobs_by_backend(
        self, mock_get_flow_runs, mock_get_flow_run
    ):
        """Test only aggregates sub jobs with same backend and pool."""
        mock_redis = Mock()
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub

        def mock_listen_side_effect():
            yield {"type": "psubscribe", "pattern": None, "data": None}
            yield {
                "type": "pmessage",
                "pattern": "qcos/job_agg/*",
                "channel": "qcos/job_agg/flow-1",
                "data": json.dumps({
                    "flow_run_id": "flow-run-id-1",
                    "aggregation_type": Constant.AGGREGATION_TYPE_EXTERNAL,
                    "cancel": False,
                }),
            }
            raise StopIteration()

        mock_pubsub.listen.side_effect = mock_listen_side_effect
        mock_pubsub.psubscribe.return_value = None

        # Parent flow on backend "dummy", pool "dummy"
        mock_parent_flow = Mock()
        mock_parent_flow.id = "flow-run-id-1"
        mock_parent_flow.state_name = "Paused"
        mock_parent_flow.work_pool_name = "device|dummy"
        mock_parent_flow.parameters = {
            "job_info": {
                "data": {
                    "backend": "dummy",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_EXTERNAL
                    ),
                }
            }
        }
        mock_get_flow_run.return_value = mock_parent_flow

        # Sub flow on same backend (should be included)
        mock_sub_flow_1 = Mock()
        mock_sub_flow_1.name = "sub-job-1"
        mock_sub_flow_1.id = "sub-flow-id-1"
        mock_sub_flow_1.work_pool_name = "device|dummy"
        mock_sub_flow_1.parameters = {
            "job_info": {
                "data": {
                    "backend": "dummy",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_EXTERNAL
                    ),
                }
            }
        }

        # Sub flow on different backend (should be excluded)
        mock_sub_flow_2 = Mock()
        mock_sub_flow_2.name = "sub-job-2"
        mock_sub_flow_2.id = "sub-flow-id-2"
        mock_sub_flow_2.work_pool_name = "device|other_pool"
        mock_sub_flow_2.parameters = {
            "job_info": {
                "data": {
                    "backend": "other_backend",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_EXTERNAL
                    ),
                }
            }
        }
        mock_get_flow_runs.return_value = [mock_sub_flow_1, mock_sub_flow_2]

        mock_sync_client = Mock()
        self.task_manager._sync_client = mock_sync_client
        mock_sync_client.resume_flow_run.return_value = None

        original_redis = self.task_manager.redis_instance
        self.task_manager.redis_instance = mock_redis

        try:
            asyncio.run(self.task_manager.process_aggregation_job())
        except StopIteration:
            pass
        finally:
            self.task_manager.redis_instance = original_redis

        # Verify resume_flow_run was called with is_parent=True
        # and only matching sub jobs
        if mock_sync_client.resume_flow_run.called:
            call_kwargs = mock_sync_client.resume_flow_run.call_args.kwargs
            run_input = call_kwargs.get("run_input", {})
            assert run_input.get("is_parent") is True
            # Only sub-job-1 should be in sub_jobs (same backend/pool)
            sub_jobs = run_input.get("sub_jobs", {})
            assert "sub-job-1" in sub_jobs
            assert "sub-job-2" not in sub_jobs

    @patch.object(TaskFlowManager, "get_flow_run")
    def test_process_aggregation_job_max_aggregation_limit(
        self, mock_get_flow_run
    ):
        """Test respects MAX_AGGREGATION_JOBS limit when selecting sub jobs."""
        mock_redis = Mock()
        mock_pubsub = Mock()
        mock_redis.pubsub.return_value = mock_pubsub

        def mock_listen_side_effect():
            yield {"type": "psubscribe", "pattern": None, "data": None}
            yield {
                "type": "pmessage",
                "pattern": "qcos/job_agg/*",
                "channel": "qcos/job_agg/flow-1",
                "data": json.dumps({
                    "flow_run_id": "flow-run-id-1",
                    "aggregation_type": Constant.AGGREGATION_TYPE_EXTERNAL,
                    "cancel": False,
                }),
            }
            raise StopIteration()

        mock_pubsub.listen.side_effect = mock_listen_side_effect
        mock_pubsub.psubscribe.return_value = None

        mock_parent_flow = Mock()
        mock_parent_flow.id = "flow-run-id-1"
        mock_parent_flow.state_name = "Paused"
        mock_parent_flow.work_pool_name = "device|dummy"
        mock_parent_flow.parameters = {
            "job_info": {
                "data": {
                    "backend": "dummy",
                    "circuit_aggregation": (
                        Constant.AGGREGATION_TYPE_EXTERNAL
                    ),
                }
            }
        }
        mock_get_flow_run.return_value = mock_parent_flow

        # Create more sub jobs than MAX_AGGREGATION_JOBS
        sub_flows = []
        for i in range(Constant.MAX_AGGREGATION_JOBS + 3):
            mock_sub = Mock()
            mock_sub.name = f"sub-job-{i}"
            mock_sub.id = f"sub-flow-id-{i}"
            mock_sub.work_pool_name = "device|dummy"
            mock_sub.parameters = {
                "job_info": {
                    "data": {
                        "backend": "dummy",
                        "circuit_aggregation": (
                            Constant.AGGREGATION_TYPE_EXTERNAL
                        ),
                    }
                }
            }
            sub_flows.append(mock_sub)

        with patch.object(
            TaskFlowManager,
            "get_flow_runs_with_filters",
            return_value=sub_flows,
        ):
            mock_sync_client = Mock()
            self.task_manager._sync_client = mock_sync_client
            mock_sync_client.resume_flow_run.return_value = None

            original_redis = self.task_manager.redis_instance
            self.task_manager.redis_instance = mock_redis

            try:
                asyncio.run(self.task_manager.process_aggregation_job())
            except StopIteration:
                pass
            finally:
                self.task_manager.redis_instance = original_redis

            if mock_sync_client.resume_flow_run.called:
                call_kwargs = mock_sync_client.resume_flow_run.call_args.kwargs
                run_input = call_kwargs.get("run_input", {})
                sub_jobs = run_input.get("sub_jobs", {})
                assert len(sub_jobs) <= Constant.MAX_AGGREGATION_JOBS

    @patch.object(TaskFlowManager, "get_prefect_configs")
    @patch(
        "wy_qcos.task_manager.task_manager.prefect_settings.temporary_settings"
    )
    @patch("wy_qcos.task_manager.task_manager.get_client")
    @patch("asyncio.new_event_loop")
    @patch.object(TaskFlowManager, "check_connection")
    def test_start_happy_path(
        self,
        mock_check_connection,
        mock_new_event_loop,
        mock_get_client,
        mock_temp_settings,
        mock_get_prefect_configs,
    ):
        """Test start() with normal flow."""
        # Configure mock event loop
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_new_event_loop.return_value = mock_loop

        # Configure mock clients
        mock_sync_client = Mock()
        mock_async_client = AsyncMock()
        mock_get_client.side_effect = [mock_async_client, mock_sync_client]

        # Configure mock temp settings context manager
        mock_temp_settings.return_value.__enter__ = Mock(return_value=None)
        mock_temp_settings.return_value.__exit__ = Mock(return_value=None)

        # Configure mock prefect configs
        mock_get_prefect_configs.return_value = {}

        # Configure mock devices
        mock_device = Mock()
        mock_device.get_name.return_value = "test_device"
        mock_driver = Mock()
        mock_driver.enable_device_monitor = True
        mock_driver.enable_device_mgr = True
        mock_device.get_driver.return_value = mock_driver

        mock_device_manager = Mock()
        mock_device_manager.get_devices.return_value = {
            "test_device": mock_device
        }
        self.task_manager.set_device_manager(mock_device_manager)

        # Mock all methods called within start()
        with patch.object(
            self.task_manager, "create_pools", new=AsyncMock()
        ) as mock_create_pools:
            with patch.object(
                self.task_manager, "create_queues", new=AsyncMock()
            ) as mock_create_queues:
                with patch.object(
                    self.task_manager,
                    "delete_task_flow_by_name",
                ) as mock_delete_flow:
                    with patch.object(
                        self.task_manager,
                        "generate_deployment_configs",
                        return_value={"test_device": {"pool_name": "p"}},
                    ) as mock_gen_deploy:
                        with patch.object(
                            self.task_manager,
                            "create_deployments",
                            new=AsyncMock(
                                return_value={
                                    "test_device": {"deploy_id": "123"}
                                }
                            ),
                        ) as mock_create_deploy:
                            with patch.object(
                                self.task_manager, "kill_workers"
                            ) as mock_kill:
                                with patch.object(
                                    self.task_manager, "start_workers"
                                ) as mock_start_w:
                                    with patch.object(
                                        self.task_manager,
                                        "wait_workers",
                                        new=AsyncMock(),
                                    ) as mock_wait:
                                        with patch.object(
                                            self.task_manager,
                                            "process_aggregation_job",
                                            new=AsyncMock(),
                                        ) as mock_proc_agg:
                                            with patch.object(
                                                self.task_manager,
                                                "run_device_monitor",
                                            ) as mock_run_monitor:
                                                # Execute start
                                                self.task_manager.start()

        # Verify calls
        assert mock_get_prefect_configs.called
        mock_temp_settings.assert_called_once()
        mock_get_client.assert_has_calls([
            mock.call(),
            mock.call(sync_client=True),
        ])
        mock_new_event_loop.assert_called_once()
        assert self.task_manager._client == mock_async_client
        assert self.task_manager._sync_client == mock_sync_client
        assert self.task_manager.loop == mock_loop

        # Verify create_pools called with device pool names
        mock_create_pools.assert_any_call(pool_names=["device|test_device"])
        # Verify create_pools called with monitor device names
        mock_create_pools.assert_any_call(pool_names=["monitor|test_device"])
        # Verify create_pools called with manager device names
        mock_create_pools.assert_any_call(pool_names=["mgr|test_device"])
        # Verify create_queues called
        mock_create_queues.assert_called_once_with(
            queue_names=["device|test_device"]
        )
        # Verify delete_task_flow_by_name called
        mock_delete_flow.assert_called_once_with("device-monitor-flow")
        # Verify generate_deployment_configs called
        mock_gen_deploy.assert_called_once_with(
            mock_device_manager.get_devices().keys()
        )
        # Verify create_deployments called
        mock_create_deploy.assert_called_once()
        # Verify kill_workers called
        mock_kill.assert_called_once()
        # Verify start_workers called
        mock_start_w.assert_called_once()
        # Verify wait_workers called
        mock_wait.assert_called_once()
        # Verify process_aggregation_job called
        mock_proc_agg.assert_called_once()
        # Verify run_device_monitor called
        mock_run_monitor.assert_called_once()

        # Verify loop.run_until_complete was called appropriately
        assert mock_loop.run_until_complete.call_count >= 5

    @patch.object(TaskFlowManager, "get_prefect_configs")
    @patch(
        "wy_qcos.task_manager.task_manager.prefect_settings.temporary_settings"
    )
    @patch("wy_qcos.task_manager.task_manager.get_client")
    @patch("asyncio.new_event_loop")
    @patch.object(TaskFlowManager, "check_connection")
    def test_start_no_devices(
        self,
        mock_check_connection,
        mock_new_event_loop,
        mock_get_client,
        mock_temp_settings,
        mock_get_prefect_configs,
    ):
        """Test start() with no devices."""
        # Configure mock event loop
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_new_event_loop.return_value = mock_loop

        # Configure mock clients
        mock_sync_client = Mock()
        mock_async_client = AsyncMock()
        mock_get_client.side_effect = [mock_async_client, mock_sync_client]

        # Configure mock temp settings context manager
        mock_temp_settings.return_value.__enter__ = Mock(return_value=None)
        mock_temp_settings.return_value.__exit__ = Mock(return_value=None)

        # Configure mock prefect configs
        mock_get_prefect_configs.return_value = {}

        # Configure mock device manager with no devices
        mock_device_manager = Mock()
        mock_device_manager.get_devices.return_value = {}
        self.task_manager.set_device_manager(mock_device_manager)

        with patch.object(self.task_manager, "create_pools", new=AsyncMock()):
            with patch.object(
                self.task_manager, "create_queues", new=AsyncMock()
            ) as mock_create_queues:
                with patch.object(
                    self.task_manager,
                    "generate_deployment_configs",
                    return_value={},
                ) as mock_gen_deploy:
                    with patch.object(
                        self.task_manager,
                        "create_deployments",
                        new=AsyncMock(return_value={}),
                    ) as mock_create_deploy:
                        with patch.object(
                            self.task_manager, "kill_workers"
                        ) as mock_kill:
                            with patch.object(
                                self.task_manager, "start_workers"
                            ) as mock_start_w:
                                with patch.object(
                                    self.task_manager,
                                    "wait_workers",
                                    new=AsyncMock(),
                                ) as mock_wait:
                                    with patch.object(
                                        self.task_manager,
                                        "process_aggregation_job",
                                        new=AsyncMock(),
                                    ) as mock_proc_agg:
                                        with patch.object(
                                            self.task_manager,
                                            "run_device_monitor",
                                        ) as mock_run_monitor:
                                            self.task_manager.start()

        # With no devices, create_pools should not be called for device pools
        # (but may be called for empty monitor/mgr lists)
        mock_create_queues.assert_not_called()
        mock_gen_deploy.assert_called_once_with(set())
        mock_create_deploy.assert_called_once_with({})
        mock_kill.assert_called_once()
        mock_start_w.assert_called_once()
        mock_wait.assert_called_once()
        mock_proc_agg.assert_called_once()
        mock_run_monitor.assert_called_once()

    @patch.object(TaskFlowManager, "get_prefect_configs")
    @patch(
        "wy_qcos.task_manager.task_manager.prefect_settings.temporary_settings"
    )
    @patch("wy_qcos.task_manager.task_manager.get_client")
    @patch("asyncio.new_event_loop")
    @patch.object(TaskFlowManager, "check_connection")
    def test_start_with_devices_no_monitor(
        self,
        mock_check_connection,
        mock_new_event_loop,
        mock_get_client,
        mock_temp_settings,
        mock_get_prefect_configs,
    ):
        """Test start() with devices that have monitor and mgr disabled."""
        # Configure mock event loop
        mock_loop = Mock()
        mock_new_event_loop.return_value = mock_loop

        # Configure mock clients
        mock_sync_client = Mock()
        mock_async_client = AsyncMock()
        mock_get_client.side_effect = [mock_async_client, mock_sync_client]

        # Configure mock temp settings context manager
        mock_temp_settings.return_value.__enter__ = Mock(return_value=None)
        mock_temp_settings.return_value.__exit__ = Mock(return_value=None)

        # Configure mock prefect configs
        mock_get_prefect_configs.return_value = {}

        # Configure mock devices with monitor and mgr disabled
        mock_device = Mock()
        mock_device.get_name.return_value = "test_device"
        mock_driver = Mock()
        mock_driver.enable_device_monitor = False
        mock_driver.enable_device_mgr = False
        mock_device.get_driver.return_value = mock_driver

        mock_device_manager = Mock()
        mock_device_manager.get_devices.return_value = {
            "test_device": mock_device
        }
        self.task_manager.set_device_manager(mock_device_manager)

        with patch.object(
            self.task_manager, "create_pools", new=AsyncMock()
        ) as mock_create_pools:
            with patch.object(
                self.task_manager, "create_queues", new=AsyncMock()
            ) as mock_create_queues:
                with patch.object(
                    self.task_manager,
                    "generate_deployment_configs",
                    return_value={"test_device": {"pool_name": "p"}},
                ) as mock_gen_deploy:
                    with patch.object(
                        self.task_manager,
                        "create_deployments",
                        new=AsyncMock(
                            return_value={"test_device": {"deploy_id": "123"}}
                        ),
                    ) as mock_create_deploy:
                        with patch.object(
                            self.task_manager, "kill_workers"
                        ) as mock_kill:
                            with patch.object(
                                self.task_manager, "start_workers"
                            ) as mock_start_w:
                                with patch.object(
                                    self.task_manager,
                                    "wait_workers",
                                    new=AsyncMock(),
                                ) as mock_wait:
                                    with patch.object(
                                        self.task_manager,
                                        "process_aggregation_job",
                                        new=AsyncMock(),
                                    ) as mock_proc_agg:
                                        with patch.object(
                                            self.task_manager,
                                            "run_device_monitor",
                                        ) as mock_run_monitor:
                                            self.task_manager.start()

        # Verify create_pools for device pool names only (no monitor/mgr pools)
        mock_create_pools.assert_called_once_with(
            pool_names=["device|test_device"]
        )
        mock_create_queues.assert_called_once_with(
            queue_names=["device|test_device"]
        )
        mock_gen_deploy.assert_called_once()
        mock_create_deploy.assert_called_once()
        mock_kill.assert_called_once()
        mock_start_w.assert_called_once()
        mock_wait.assert_called_once()
        mock_proc_agg.assert_called_once()
        mock_run_monitor.assert_called_once()

    @patch.object(TaskFlowManager, "get_prefect_configs")
    @patch(
        "wy_qcos.task_manager.task_manager.prefect_settings.temporary_settings"
    )
    @patch("wy_qcos.task_manager.task_manager.get_client")
    @patch("asyncio.new_event_loop")
    @patch.object(TaskFlowManager, "check_connection")
    def test_start_with_multiple_devices(
        self,
        mock_check_connection,
        mock_new_event_loop,
        mock_get_client,
        mock_temp_settings,
        mock_get_prefect_configs,
    ):
        """Test start() with multiple devices."""
        mock_loop = Mock()
        mock_new_event_loop.return_value = mock_loop

        mock_sync_client = Mock()
        mock_async_client = AsyncMock()
        mock_get_client.side_effect = [mock_async_client, mock_sync_client]

        mock_temp_settings.return_value.__enter__ = Mock(return_value=None)
        mock_temp_settings.return_value.__exit__ = Mock(return_value=None)

        mock_get_prefect_configs.return_value = {}

        # Device 1: has both monitor and mgr
        device1 = Mock()
        device1.get_name.return_value = "device_a"
        driver1 = Mock()
        driver1.enable_device_monitor = True
        driver1.enable_device_mgr = True
        device1.get_driver.return_value = driver1

        # Device 2: has only monitor
        device2 = Mock()
        device2.get_name.return_value = "device_b"
        driver2 = Mock()
        driver2.enable_device_monitor = True
        driver2.enable_device_mgr = False
        device2.get_driver.return_value = driver2

        # Device 3: has neither
        device3 = Mock()
        device3.get_name.return_value = "device_c"
        driver3 = Mock()
        driver3.enable_device_monitor = False
        driver3.enable_device_mgr = False
        device3.get_driver.return_value = driver3

        mock_device_manager = Mock()
        mock_device_manager.get_devices.return_value = {
            "device_a": device1,
            "device_b": device2,
            "device_c": device3,
        }
        self.task_manager.set_device_manager(mock_device_manager)

        with patch.object(
            self.task_manager, "create_pools", new=AsyncMock()
        ) as mock_create_pools:
            with patch.object(
                self.task_manager, "create_queues", new=AsyncMock()
            ) as mock_create_queues:
                with patch.object(
                    self.task_manager,
                    "generate_deployment_configs",
                    return_value={
                        "device_a": {"pool_name": "a"},
                        "device_b": {"pool_name": "b"},
                        "device_c": {"pool_name": "c"},
                    },
                ):
                    with patch.object(
                        self.task_manager,
                        "create_deployments",
                        new=AsyncMock(
                            return_value={
                                "device_a": {"deploy_id": "1"},
                                "device_b": {"deploy_id": "2"},
                                "device_c": {"deploy_id": "3"},
                            }
                        ),
                    ):
                        with patch.object(self.task_manager, "kill_workers"):
                            with patch.object(
                                self.task_manager, "start_workers"
                            ):
                                with patch.object(
                                    self.task_manager,
                                    "wait_workers",
                                    new=AsyncMock(),
                                ):
                                    with patch.object(
                                        self.task_manager,
                                        "process_aggregation_job",
                                        new=AsyncMock(),
                                    ):
                                        with patch.object(
                                            self.task_manager,
                                            "run_device_monitor",
                                        ):
                                            self.task_manager.start()

        # Verify create_pools calls
        mock_create_pools.assert_any_call(
            pool_names=[
                "device|device_a",
                "device|device_b",
                "device|device_c",
            ]
        )
        mock_create_pools.assert_any_call(
            pool_names=["monitor|device_a", "monitor|device_b"]
        )
        mock_create_pools.assert_any_call(pool_names=["mgr|device_a"])

        mock_create_queues.assert_called_once_with(
            queue_names=[
                "device|device_a",
                "device|device_b",
                "device|device_c",
            ]
        )
