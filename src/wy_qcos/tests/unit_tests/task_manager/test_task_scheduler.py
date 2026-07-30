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

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device_manager import DeviceManager
from wy_qcos.driver.driver_manager import DriverManager
from wy_qcos.task_manager.task_manager import TaskFlowManager
from wy_qcos.task_manager.task_scheduler import PrioritySchedulingPolicy
from wy_qcos.task_manager.task_scheduler import TaskScheduler
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

        mock_device_manager = Mock()
        mock_driver_manager = Mock()
        mock_transpiler_manager = Mock()
        task.set_device_manager(mock_device_manager)
        task.set_driver_manager(mock_driver_manager)
        task.set_transpiler_manager(mock_transpiler_manager)

        mock_job_info = Mock()
        mock_job_info.backend = "dummy"
        mock_job_info.model_dump.return_value = ConstantForTest.job_info

        mock_device_manager.get_device.return_value = None
        result, error = task.submit(mock_job_info, None)
        assert result is None
        assert error is not None
        assert "Backend" in error
        assert mock_logger.error.called

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

    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    def test_submit_flow_limit_exceeded(self, mock_get_flow_runs_with_filters):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.return_value = [
            object()
        ] * Constant.FLOW_LIMIT

        result, error = scheduler.submit(Mock(backend="dummy"), None)

        assert result is None
        assert "max flow limit" in error

    @patch.object(TaskFlowManager, "convert_to_prefect_states")
    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    def test_submit_queued_limit_exceeded(
        self,
        mock_get_flow_runs_with_filters,
        mock_convert_to_prefect_states,
    ):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        # Use a positive limit to test the exceeded scenario
        # (default MAX_QUEUED_JOBS=-1 means unlimited)
        test_limit = 5
        original = Config.DEFAULT.MAX_QUEUED_JOBS
        Config.DEFAULT.MAX_QUEUED_JOBS = test_limit
        try:
            scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
                [],
                [object()] * test_limit,
            ]
            scheduler._device_manager = Mock()
            mock_convert_to_prefect_states.return_value = ["RUNNING"]

            result, error = scheduler.submit(Mock(backend="dummy"), None)

            assert result is None
            assert "max queued job limit" in error
        finally:
            Config.DEFAULT.MAX_QUEUED_JOBS = original

    def test_submit_device_disabled(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
            [],
            [],
        ]
        scheduler._task_manager.convert_to_prefect_states.return_value = []
        mock_device = Mock(enable=False)
        scheduler._device_manager = Mock()
        scheduler._device_manager.get_device.return_value = mock_device

        result, error = scheduler.submit(Mock(backend="dummy"), None)

        assert result is None
        assert "disabled" in error

    def test_submit_device_disallow_queued_jobs(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
            [],
            [],
            [object()],
        ]
        scheduler._task_manager.convert_to_prefect_states.return_value = []
        mock_driver = Mock(
            get_module_name=Mock(return_value="module"),
            get_class_name=Mock(return_value="DriverClass"),
            get_package_paths=Mock(return_value=[]),
            get_transpiler=Mock(return_value=None),
        )
        mock_device = Mock(enable=True)
        mock_device.get_max_queued_jobs.return_value = 0
        mock_device.get_driver.return_value = mock_driver
        scheduler._device_manager = Mock()
        scheduler._device_manager.get_device.return_value = mock_device

        result, error = scheduler.submit(Mock(backend="dummy"), None)

        assert result is None
        assert error == "Device does not allow queued jobs"

    def test_submit_device_queued_limit_exceeded(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
            [],
            [],
            [object(), object()],
        ]
        scheduler._task_manager.convert_to_prefect_states.return_value = []
        mock_driver = Mock(
            get_module_name=Mock(return_value="module"),
            get_class_name=Mock(return_value="DriverClass"),
            get_package_paths=Mock(return_value=[]),
            get_transpiler=Mock(return_value=None),
        )
        mock_device = Mock(enable=True)
        mock_device.get_max_queued_jobs.return_value = 2
        mock_device.get_driver.return_value = mock_driver
        scheduler._device_manager = Mock()
        scheduler._device_manager.get_device.return_value = mock_device

        result, error = scheduler.submit(Mock(backend="dummy"), None)

        assert result is None
        assert "max queued job limit: 2" in error

    def test_submit_with_transpiler(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
            [],
            [],
            [],
        ]
        scheduler._task_manager.convert_to_prefect_states.return_value = []
        scheduler._task_manager.get_deployment.return_value = {
            "deploy_id": "deploy-1",
        }
        mock_driver = Mock(
            get_module_name=Mock(return_value="driver_module"),
            get_class_name=Mock(return_value="DriverClass"),
            get_package_paths=Mock(return_value=[]),
            get_transpiler=Mock(return_value="dummy_transpiler"),
        )
        mock_device = Mock(enable=True)
        mock_device.get_max_queued_jobs.return_value = -1
        mock_device.get_driver.return_value = mock_driver
        mock_device.get_configs.return_value = {"a": 1}
        scheduler._device_manager = Mock()
        scheduler._device_manager.get_device.return_value = mock_device
        mock_transpiler = Mock(
            get_module_name=Mock(return_value="trans_module"),
            get_class_name=Mock(return_value="TransClass"),
        )
        scheduler._transpiler_manager = Mock()
        scheduler._transpiler_manager.get_transpiler.return_value = (
            mock_transpiler
        )
        scheduler._policy_handler = Mock()
        scheduler._policy_handler.exec_task.return_value = "flow-id"
        job_info = Mock()
        job_info.backend = "dummy"
        job_info.model_dump.return_value = ConstantForTest.job_info

        result, error = scheduler.submit(job_info, ["tag-1"])

        assert error is None
        assert result == {"flow_run_id": "flow-id"}
        submit_args = scheduler._policy_handler.exec_task.call_args[0]
        assert submit_args[1]["transpiler"]["module_name"] == "trans_module"
        assert submit_args[1]["transpiler"]["class_name"] == "TransClass"

    def test_submit_exec_task_exception(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
            [],
            [],
            [],
        ]
        scheduler._task_manager.convert_to_prefect_states.return_value = []
        scheduler._task_manager.get_deployment.return_value = {
            "deploy_id": "deploy-1",
        }
        mock_driver = Mock(
            get_module_name=Mock(return_value="driver_module"),
            get_class_name=Mock(return_value="DriverClass"),
            get_package_paths=Mock(return_value=[]),
            get_transpiler=Mock(return_value=None),
        )
        mock_device = Mock(enable=True)
        mock_device.get_max_queued_jobs.return_value = -1
        mock_device.get_driver.return_value = mock_driver
        mock_device.get_configs.return_value = {}
        scheduler._device_manager = Mock()
        scheduler._device_manager.get_device.return_value = mock_device
        scheduler._transpiler_manager = Mock()
        scheduler._transpiler_manager.get_transpiler.return_value = None
        scheduler._policy_handler = Mock()
        scheduler._policy_handler.exec_task.side_effect = RuntimeError("boom")
        job_info = Mock()
        job_info.backend = "dummy"
        job_info.model_dump.return_value = ConstantForTest.job_info

        with pytest.raises(Exception):
            scheduler.submit(job_info, None)

    @patch("wy_qcos.task_manager.task_scheduler.logger")
    @patch.object(TaskFlowManager, "get_flow_runs_with_filters")
    @patch.object(TaskFlowManager, "get_deployment")
    def test_submit_manage_job(
        self, mock_get_deployment, mock_get_flow_runs_with_filters, mock_logger
    ):
        """Test manage job submission."""
        mock_get_flow_runs_with_filters.return_value = []
        mock_device = Mock()
        mock_device.enable = True
        mock_device.get_driver.return_value = Mock(
            get_module_name=Mock(return_value="driver_module"),
            get_class_name=Mock(return_value="DriverClass"),
            get_package_paths=Mock(return_value=[]),
        )
        mock_device.get_configs.return_value = {}

        mock_device_manager = Mock()
        mock_device_manager.get_device.return_value = None
        mock_device_manager.config.REDIS.REDIS_SERVER_IP = "127.0.0.1"
        mock_device_manager.config.REDIS.REDIS_SERVER_PORT = 6379
        task.set_device_manager(mock_device_manager)

        mock_job_info = Mock()
        mock_job_info.device_name = "dummy"
        mock_job_info.method = "calibrate"
        mock_job_info.model_dump.return_value = {"device_name": "dummy"}

        result, error = task.submit_manage_job(mock_job_info)
        assert result is None
        assert "Backend" in error
        assert mock_logger.error.called

        mock_device_manager.get_device.return_value = mock_device
        mock_get_deployment.return_value = {"deploy_id": "test_deployment_id"}
        task._policy_handler = Mock()
        task._policy_handler.exec_manage_task.return_value = (
            True,
            {"job_id": "job-123"},
        )

        result = task.submit_manage_job(mock_job_info)
        assert result == {"job_id": "job-123"}

    def test_submit_manage_job_flow_limit_exceeded(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.return_value = [
            object()
        ] * Constant.FLOW_LIMIT

        result, error = scheduler.submit_manage_job(Mock(device_name="dummy"))

        assert result is None
        assert "max flow limit" in error

    def test_submit_manage_job_queued_limit_exceeded(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        # Use a positive limit to test the exceeded scenario
        # (default MAX_QUEUED_JOBS=-1 means unlimited)
        test_limit = 5
        original = Config.DEFAULT.MAX_QUEUED_JOBS
        Config.DEFAULT.MAX_QUEUED_JOBS = test_limit
        try:
            scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
                [],
                [object()] * test_limit,
            ]
            scheduler._task_manager.convert_to_prefect_states.return_value = []

            result, error = scheduler.submit_manage_job(
                Mock(device_name="dummy")
            )

            assert result is None
            assert "running+queued job count exceeds" in error
        finally:
            Config.DEFAULT.MAX_QUEUED_JOBS = original

    def test_submit_manage_job_device_disabled(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
            [],
            [],
        ]
        scheduler._task_manager.convert_to_prefect_states.return_value = []
        mock_device = Mock(enable=False)
        scheduler._device_manager = Mock()
        scheduler._device_manager.get_device.return_value = mock_device
        job_info = Mock(device_name="dummy")

        result, error = scheduler.submit_manage_job(job_info)

        assert result is None
        assert "disabled" in error

    def test_submit_manage_job_exec_manage_task_failure(self):
        scheduler = TaskScheduler()
        scheduler._task_manager = Mock()
        scheduler._task_manager.get_flow_runs_with_filters.side_effect = [
            [],
            [],
        ]
        scheduler._task_manager.convert_to_prefect_states.return_value = []
        scheduler._task_manager.get_deployment.return_value = {
            "deploy_id": "deploy-1",
        }
        mock_driver = Mock(
            get_module_name=Mock(return_value="driver_module"),
            get_class_name=Mock(return_value="DriverClass"),
            get_package_paths=Mock(return_value=[]),
        )
        mock_device = Mock(enable=True)
        mock_device.get_driver.return_value = mock_driver
        mock_device.get_configs.return_value = {}
        scheduler._device_manager = Mock()
        scheduler._device_manager.get_device.return_value = mock_device
        scheduler._device_manager.config.REDIS.REDIS_SERVER_IP = "127.0.0.1"
        scheduler._device_manager.config.REDIS.REDIS_SERVER_PORT = 6379
        scheduler._policy_handler = Mock()
        scheduler._policy_handler.exec_manage_task.return_value = (
            False,
            "failed",
        )
        job_info = Mock()
        job_info.device_name = "dummy"
        job_info.method = "calibrate"
        job_info.model_dump.return_value = {"device_name": "dummy"}

        with pytest.raises(Exception):
            scheduler.submit_manage_job(job_info)

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

        mock_device = Mock()
        mock_device.get_name.return_value = "tiangong100"
        mock_device_manager = Mock()
        mock_device_manager.get_device.return_value = mock_device
        task.set_device_manager(mock_device_manager)

        mock_policy_handler = Mock()
        mock_policy_handler.exec_task.return_value = "mock_job_id_123"
        task._policy_handler = mock_policy_handler
        result = task.update_flow(
            ConstantForTest.job_id, None, parameters={"job_priority": 1}
        )
        assert result is not None

    @patch("wy_qcos.task_manager.task_scheduler.create_db_session")
    def test_process_unfinished_jobs(self, mock_create_db_session):
        scheduler = TaskScheduler()
        scheduler._db_engine = Mock()
        # avoid real task_manager side-effects when cancelling flow runs
        scheduler._task_manager = Mock()

        # process_unfinished_jobs only resets jobs in intermediate states
        # (UNKNOWN/CANCELLING) to FAILED; use CANCELLING so the job is
        # updated and committed.
        job_running = Mock(
            id="job-1",
            job_status=Constant.JOB_STATUS_CANCELLING,
            flow_run_id=None,
        )
        job_done = Mock(id="job-2", job_status=Constant.JOB_STATUS_COMPLETED)
        db_session = Mock()
        mock_create_db_session.return_value = nullcontext(db_session)

        with patch(
            "wy_qcos.task_manager.task_scheduler.JobRepository"
        ) as mock_repo_cls:
            mock_repo = Mock()
            mock_repo.get_jobs.return_value = (
                True,
                None,
                [job_running, job_done],
            )
            mock_repo_cls.return_value = mock_repo

            scheduler.process_unfinished_jobs()

        assert job_running.job_status == Constant.JOB_STATUS_FAILED
        assert job_done.job_status == Constant.JOB_STATUS_COMPLETED
        db_session.commit.assert_called_once()

    @patch("wy_qcos.task_manager.task_scheduler.logger")
    @patch("wy_qcos.task_manager.task_scheduler.create_db_session")
    def test_process_unfinished_jobs_commit_failure(
        self,
        mock_create_db_session,
        mock_logger,
    ):
        scheduler = TaskScheduler()
        scheduler._db_engine = Mock()
        # avoid real task_manager side-effects when cancelling flow runs
        scheduler._task_manager = Mock()
        # process_unfinished_jobs only commits jobs in intermediate states
        # (UNKNOWN/CANCELLING); use CANCELLING so the commit path (and
        # thus the rollback on failure) is exercised.
        job_running = Mock(
            id="job-1",
            job_status=Constant.JOB_STATUS_CANCELLING,
            flow_run_id=None,
        )
        db_session = Mock()
        db_session.commit.side_effect = RuntimeError("commit failed")
        mock_create_db_session.return_value = nullcontext(db_session)

        with patch(
            "wy_qcos.task_manager.task_scheduler.JobRepository"
        ) as mock_repo_cls:
            mock_repo = Mock()
            mock_repo.get_jobs.return_value = (True, None, [job_running])
            mock_repo_cls.return_value = mock_repo

            scheduler.process_unfinished_jobs()

        db_session.rollback.assert_called_once()
        assert mock_logger.error.called

    @patch("wy_qcos.task_manager.task_scheduler.logger")
    def test_process_unfinished_jobs_without_db_engine(self, mock_logger):
        scheduler = TaskScheduler()
        scheduler.process_unfinished_jobs()
        mock_logger.warning.assert_called_once()

    @patch("wy_qcos.task_manager.task_scheduler.create_db_session")
    def test_process_callbacks(self, mock_create_db_session):
        scheduler = TaskScheduler()
        scheduler._db_engine = Mock()

        job_record = Mock(
            id="job-1",
            job_status=Constant.JOB_STATUS_COMPLETED,
            backend="dummy",
            callbacks=["http://callback"],
            is_callback_success=False,
            results={"status": "ok"},
            project_id="project-1",
            user_id="user-1",
        )
        db_session = Mock()
        mock_create_db_session.return_value = nullcontext(db_session)

        with patch(
            "wy_qcos.task_manager.task_scheduler.JobRepository"
        ) as mock_repo_cls:
            mock_repo = Mock()
            mock_repo.get_jobs.return_value = (True, None, [job_record])
            mock_repo_cls.return_value = mock_repo

            with patch.object(
                Library,
                "job_callback",
                return_value=True,
            ) as mock_callback:
                scheduler.process_callbacks()

        assert job_record.is_callback_success is True
        mock_callback.assert_called_once()
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once_with(job_record)

    @patch("wy_qcos.task_manager.task_scheduler.logger")
    def test_process_callbacks_without_db_engine(self, mock_logger):
        scheduler = TaskScheduler()

        scheduler.process_callbacks()

        mock_logger.warning.assert_called_once()

    @patch("wy_qcos.task_manager.task_scheduler.create_db_session")
    def test_process_callbacks_skip_job_without_callbacks(
        self, mock_create_db_session
    ):
        scheduler = TaskScheduler()
        scheduler._db_engine = Mock()
        job_record = Mock(
            callbacks=[],
            is_callback_success=False,
        )
        db_session = Mock()
        mock_create_db_session.return_value = nullcontext(db_session)

        with patch(
            "wy_qcos.task_manager.task_scheduler.JobRepository"
        ) as mock_repo_cls:
            mock_repo = Mock()
            mock_repo.get_jobs.return_value = (True, None, [job_record])
            mock_repo_cls.return_value = mock_repo

            with patch.object(Library, "job_callback") as mock_callback:
                scheduler.process_callbacks()

        mock_callback.assert_not_called()
        db_session.commit.assert_not_called()

    @patch("wy_qcos.task_manager.task_scheduler.logger")
    @patch("wy_qcos.task_manager.task_scheduler.create_db_session")
    def test_process_callbacks_callback_exception(
        self,
        mock_create_db_session,
        mock_logger,
    ):
        scheduler = TaskScheduler()
        scheduler._db_engine = Mock()
        job_record = Mock(
            id="job-1",
            job_status=Constant.JOB_STATUS_COMPLETED,
            backend="dummy",
            callbacks=["http://callback"],
            is_callback_success=False,
            results={"status": "ok"},
            project_id="project-1",
            user_id="user-1",
        )
        db_session = Mock()
        mock_create_db_session.return_value = nullcontext(db_session)

        with patch(
            "wy_qcos.task_manager.task_scheduler.JobRepository"
        ) as mock_repo_cls:
            mock_repo = Mock()
            mock_repo.get_jobs.return_value = (True, None, [job_record])
            mock_repo_cls.return_value = mock_repo

            with patch.object(
                Library,
                "job_callback",
                side_effect=RuntimeError("callback failed"),
            ):
                scheduler.process_callbacks()

        assert mock_logger.error.called


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
        mock_run_flow.assert_called_once()
        _, call_kwargs = mock_run_flow.call_args
        assert call_kwargs["work_queue_name"] == (
            f"{Constant.WORK_POOL_DEVICE_PREFIX}{Constant.DRIVER_DUMMY}_1"
        )
