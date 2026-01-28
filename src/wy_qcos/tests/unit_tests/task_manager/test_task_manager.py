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
import pytest
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

        device_name = "test_device"
        device_names = [device_name]
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
        mock_devices = {
            "dummy": {},
            "qutip_sim": {},
        }
        mock_device_manager.get_devices.return_value = mock_devices
        self.task_manager.set_device_manager(mock_device_manager)

        # start workers
        self.task_manager.start_workers()

        # verify results
        assert mock_process.daemon is True
        mock_process.start.assert_called()
        mock_process.start.call_count == len(mock_devices)

    def test_run_task_flow(self):
        mock_client = Mock()
        mock_run = Mock()
        mock_run.run_task_flow_by_client.return_value = mock_client
        self.task_manager.loop = mock_client
        deployment_id = ConstantForTest.deployment_id
        flow_run_id = self.task_manager.run_task_flow(
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
        job_id = asyncio.run(
            self.task_manager.run_task_flow_by_client(
                ConstantForTest.job_id, ConstantForTest.args, None
            )
        )
        assert job_id is not None

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_get_task_flow_result(self, mock_get_flow_run_id_by_job_id):
        mock_client = Mock()
        mock_run = Mock()
        mock_run.get_task_flow_result_by_client.return_value = mock_client
        mock_get_flow_run_id_by_job_id.return_value = None
        with pytest.raises(Exception) as context:
            self.task_manager.get_task_flow_result(ConstantForTest.job_id)
        assert str(context.value) == "None"

    def test_delete_flow_artifacts(self):
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        mock_client.read_artifacts.return_value = [
            ConstantForTest.artifact_obj
        ]
        mock_client.delete_artifact.return_value = None
        self.task_manager.delete_flow_artifacts(ConstantForTest.job_id)
        assert mock_client.delete_artifact.call_count == 1

    def test_get_job_artifact(self):
        mock_client = Mock()
        self.task_manager.get_job_artifact_by_client = mock_client
        mock_client.get_job_artifact_by_client.return_value = []
        artifact = self.task_manager.get_job_artifact(ConstantForTest.job_id)
        assert artifact is not None

    def test_get_job_artifact_by_client(self):
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        mock_client.read_artifacts.return_value = []
        job_id = self.task_manager.get_job_artifact_by_client(
            ConstantForTest.job_id
        )
        assert job_id is not None

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_has_flow(self, mock_get_flow_run_id_by_job_id):
        mock_get_flow_run_id_by_job_id.return_value = "1234"
        exist = self.task_manager.has_flow(ConstantForTest.job_id)
        assert exist is True

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_update_flow(self, mock_get_flow_run_id_by_job_id):
        mock_client = AsyncMock()
        mock_run = AsyncMock()
        self.task_manager.loop = mock_client
        mock_run._update_flow.return_value = mock_client
        mock_get_flow_run_id_by_job_id.return_value = None
        success = self.task_manager.update_flow(ConstantForTest.job_id)
        assert success is False

        mock_get_flow_run_id_by_job_id.return_value = "1234"
        self.task_manager.update_flow(ConstantForTest.job_id)

    def test_get_task_flow_result_by_client(self):
        mock_client = Mock()
        mock_run = Mock()
        self.task_manager._sync_client = mock_client
        mock_run.read_flow_run.return_value = {}
        results = self.task_manager.get_task_flow_result_by_client(
            ConstantForTest.job_id
        )
        assert results is not None

    def test_get_task_flow_list(self):
        mock_client = Mock()
        self.task_manager.get_task_flow_list_by_client = mock_client
        mock_client.get_task_flow_list_by_client.return_value = []
        results = self.task_manager.get_task_flow_list(None)
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
        results = self.task_manager.get_task_flow_list_by_client(tags=None)
        assert results is not None

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_get_task_flow_run(self, mock_get_flow_run_id_by_job_id):
        mock_get_flow_run_id_by_job_id.return_value = 1
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        mock_client.read_artifacts.return_value = []
        mock_client.read_flow_runs.return_value = []
        results = self.task_manager.get_task_flow_run(1)
        assert results is not None

    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_delete_task_flow_run(self, mock_get_flow_run_id_by_job_id):
        mock_get_flow_run_id_by_job_id.return_value = ["1", "2", "3"]
        mock_run = Mock()
        mock_client = Mock()
        mock_client.delete_task_flow_run_by_client.return_value = mock_run
        self.task_manager.loop = mock_client
        success_list = self.task_manager.delete_task_flow_run(
            ConstantForTest.job_ids, None
        )
        assert not success_list

    def test_delete_task_flow_run_by_client(self):
        mock_client = Mock()
        self.task_manager._sync_client = mock_client
        results = self.task_manager.delete_task_flow_run_by_client(
            ConstantForTest.flow_run_ids
        )
        assert results is not None

    def test_run_callbacks(self):
        mock_client = Mock()
        mock_run = Mock()
        self.task_manager.loop = mock_client
        mock_client.async_run_callbacks.return_value = mock_run
        results = self.task_manager.run_callbacks([], "call")
        assert results is not None

    def test_process_aggregation_job(self):
        mock_client = AsyncMock()
        self.task_manager._client = mock_client
        results = asyncio.run(self.task_manager.process_aggregation_job())
        assert results is None

    @patch.object(TaskFlowManager, "cancel_task_flow_run_by_client")
    @patch.object(TaskFlowManager, "get_flow_run_id_by_job_id")
    def test_cancel_task_flow_run(
        self,
        mock_get_flow_run_id_by_job_id,
        mock_cancel_task_flow_run_by_client,
    ):
        mock_get_flow_run_id_by_job_id.return_value = "1234"
        mock_cancel_task_flow_run_by_client.return_value = None
        success_list = self.task_manager.cancel_task_flow_run(
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
        success_list = self.task_manager.cancel_task_flow_run_by_client(
            ConstantForTest.job_ids
        )
        assert not success_list
