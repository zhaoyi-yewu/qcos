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

from unittest.mock import patch, Mock

from wy_qcos.common.config import Config
from wy_qcos.drivers.device_manager import DeviceManager
from wy_qcos.drivers.driver_manager import DriverManager
from wy_qcos.task_manager.task_manager import TaskFlowManager
from wy_qcos.task_manager.task_scheduler import TaskScheduler
from wy_qcos.task_manager.task_scheduler import PrioritySchedulingPolicy
from wy_qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)

task = TaskScheduler()
driver_manager = DriverManager()
device_manager = DeviceManager(Config, driver_manager)


class TestTaskScheduler:
    @patch.object(TaskFlowManager, "start")
    def test_start_taskmanager(self, mock_start):
        mock_start.return_value = None
        assert task.start_taskmanager() is None

    def test_set_driver_manager(self):
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = "Mocked task done"
        assert task.set_driver_manager(driver_manager) is None

    def test_get_driver_manager(self):
        driver_manager = task.get_driver_manager()
        assert driver_manager is not None

    def test_set_transpiler_manager(self):
        transpiler_manager = None
        assert task.set_transpiler_manager(transpiler_manager) is None

    def test_get_transpiler_manager(self):
        transpiler_manager = task.get_transpiler_manager()
        assert transpiler_manager is None

    @patch.object(TaskFlowManager, "set_device_manager")
    def test_set_device_manager(self, mock_set_device_manager):
        mock_set_device_manager.return_value = None
        assert task.set_device_manager(device_manager) is None

    def test_get_device_manager(self):
        device_manager = task.get_device_manager()
        assert device_manager is not None

    @patch("wy_qcos.task_manager.task_scheduler.logger")
    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    @patch.object(TaskFlowManager, "get_deployment")
    def test_submit(
        self, mock_get_deployment, mock_get_flow_runs_with_filters, mock_logger
    ):
        """Test job submission with proper error handling."""
        # Setup mocks
        mock_get_flow_runs_with_filters.return_value = []
        mock_device = Mock()
        mock_device.enable = True
        mock_device.get_max_queued_jobs.return_value = -1
        mock_device.get_driver.return_value = Mock(
            get_module_name=Mock(return_value="driver_module"),
            get_class_name=Mock(return_value="DriverClass"),
            get_package_paths=Mock(return_value=[]),
            get_transpiler=Mock(return_value=None),
        )
        mock_device.get_configs.return_value = {}

        # Setup task scheduler
        mock_device_manager = Mock()
        mock_driver_manager = Mock()
        mock_transpiler_manager = Mock()
        task.set_device_manager(mock_device_manager)
        task.set_driver_manager(mock_driver_manager)
        task.set_transpiler_manager(mock_transpiler_manager)

        # Create mock job info with model_dump method
        mock_job_info = Mock()
        mock_job_info.backend = "dummy"
        mock_job_info.model_dump.return_value = ConstantForTest.job_info

        # Test case 1: Device not found returns error
        mock_device_manager.get_device.return_value = None
        result, error = task.submit(mock_job_info, None)
        assert result is None
        assert error is not None
        assert "Backend" in error
        # Verify logger was called
        assert mock_logger.error.called

        # Test case 2: Successful submission with valid device
        mock_device_manager.get_device.return_value = mock_device
        mock_device_manager.config.REDIS.REDIS_SERVER_IP = "localhost"
        mock_device_manager.config.REDIS.REDIS_SERVER_PORT = 6379
        mock_get_deployment.return_value = {
            "deploy_id": "test_deployment_id",
        }
        task._policy_handler = Mock()
        task._policy_handler.exec_task.return_value = "flow_run_id_123"

        result, error = task.submit(mock_job_info, None)
        assert result is not None
        assert error is None
        assert result.get("flow_run_id") == "flow_run_id_123"

    @patch.object(TaskFlowManager, "delete_flow_runs")
    def test_delete_jobs(self, mock_delete_flow_runs):
        mock_delete_flow_runs.return_value = [
            {"job_status": 111, "state": 222},
        ]
        flow_list = task.delete_flows([1, 2, 3])
        assert flow_list[0]["state"] == 222

    @patch.object(TaskFlowManager, "cancel_flow_runs")
    def test_cancel_jobs(self, mock_cancel_flow_runs):
        mock_cancel_flow_runs.return_value = []
        flow_list = task.cancel_flows(ConstantForTest.job_ids)
        assert not flow_list

    @patch.object(TaskFlowManager, "update_flow")
    @patch.object(TaskFlowManager, "get_flow_run")
    @patch.object(TaskFlowManager, "delete_flow_runs")
    def test_update_job(
        self,
        mock_delete_flow_runs,
        mock_get_flow_run,
        mock_update_flow,
    ):
        mock_flow_run = Mock()
        mock_state = Mock()
        mock_state.name = "QUEUED"
        mock_flow_run.state = mock_state
        mock_flow_run.parameters = {
            "job_info": {
                "data": {
                    "job_priority": 2,
                    "backend": "tiangong100",
                    "code_type": "qubo",
                }
            }
        }
        mock_update_flow.return_value = True, None
        mock_get_flow_run.return_value = mock_flow_run
        mock_delete_flow_runs.return_value = [
            {"job_status": 111, "state": 222},
        ]
        mock_deploy_flow = Mock()
        mock_deploy_flow.__name__ = "test_deploy_flow"

        mock_device = Mock()
        mock_device.get_name.return_value = "tiangong100"
        mock_device_manager = Mock()
        mock_device_manager.get_device.return_value = mock_device
        task.set_device_manager(mock_device_manager)

        mock_policy_handler = Mock()
        mock_policy_handler.exec_task.return_value = "mock_job_id_123"
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = "Mocked task done"
        task._policy_handler = mock_policy_handler
        result = task.update_flow(
            ConstantForTest.job_id, None, parameters={"job_priority": 1}
        )
        assert result is not None


task_manager = TaskFlowManager()
priority_scheduling_policy = PrioritySchedulingPolicy(task_manager)


class TestPrioritySchedulingPolicy:
    @patch.object(TaskFlowManager, "run_flow")
    def test_exec_task(self, mock_run_flow):
        mock_run_flow.return_value = 514

        result = priority_scheduling_policy.exec_task(
            ConstantForTest.deployment,
            ConstantForTest.args["job_info"],
            None,
        )
        assert result == 514
