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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Unit tests for list_workers and restart_worker in TaskFlowManager."""

import pytest
from unittest import mock

from prefect.client.schemas.objects import WorkerStatus

from wy_qcos.common.constant import Constant
from wy_qcos.task_manager.task_manager import TaskFlowManager


def _make_pool(name):
    """Build a mock work pool object."""
    pool = mock.Mock()
    pool.name = name
    return pool


def _make_worker(name, status, pid=None):
    """Build a mock worker object."""
    worker = mock.Mock()
    worker.name = name
    worker.status = status
    worker.process_pid = pid
    return worker


@pytest.fixture
def task_manager():
    """Provide a TaskFlowManager instance with check_connection mocked."""
    with mock.patch.object(TaskFlowManager, "check_connection"):
        return TaskFlowManager()


class TestListWorkers:
    """Tests for TaskFlowManager.list_workers."""

    def test_no_sync_client(self, task_manager):
        """Return empty list when sync client not initialized."""
        task_manager._sync_client = None
        assert task_manager.list_workers() == []

    def test_read_pools_failure(self, task_manager):
        """Return empty list when read_work_pools raises."""
        sync_client = mock.Mock()
        sync_client.read_work_pools.side_effect = RuntimeError("conn error")
        task_manager._sync_client = sync_client

        result = task_manager.list_workers()
        assert result == []

    def test_list_with_workers(self, task_manager):
        """List workers across multiple pools."""
        pool_a = _make_pool("device|dummy")
        pool_b = _make_pool("monitor|dummy")

        worker1 = _make_worker("process-device|dummy", WorkerStatus.ONLINE)
        worker2 = _make_worker(
            "process-device|dummy_monitor", WorkerStatus.OFFLINE
        )

        sync_client = mock.Mock()
        sync_client.read_work_pools.return_value = [pool_a, pool_b]
        sync_client.read_workers_for_work_pool.side_effect = [
            [worker1],
            [worker2],
        ]
        task_manager._sync_client = sync_client

        with mock.patch.object(TaskFlowManager, "_get_worker_pid") as mock_pid:
            mock_pid.side_effect = [101, None]
            result = task_manager.list_workers()

        assert len(result) == 2
        assert result[0]["worker_name"] == "process-device|dummy"
        assert result[0]["work_pool"] == "device|dummy"
        assert result[0]["worker_status"] == WorkerStatus.ONLINE.value
        assert result[0]["pid"] == 101
        assert result[1]["worker_status"] == WorkerStatus.OFFLINE.value
        assert result[1]["pid"] is None

    def test_online_without_process_corrected_to_offline(self, task_manager):
        """ONLINE worker with no running process is corrected to OFFLINE."""
        pool = _make_pool("device|dummy")
        worker = _make_worker("process-device|dummy", WorkerStatus.ONLINE)
        sync_client = mock.Mock()
        sync_client.read_work_pools.return_value = [pool]
        sync_client.read_workers_for_work_pool.return_value = [worker]
        task_manager._sync_client = sync_client

        with mock.patch.object(
            TaskFlowManager, "_get_worker_pid", return_value=None
        ):
            result = task_manager.list_workers()

        assert len(result) == 1
        # prefect reports ONLINE but no process exists -> OFFLINE
        assert result[0]["worker_status"] == (WorkerStatus.OFFLINE.value)
        assert result[0]["pid"] is None

    def test_list_empty_pool(self, task_manager):
        """Pool with no workers is reported with no_workers status."""
        pool = _make_pool("device|dummy")
        sync_client = mock.Mock()
        sync_client.read_work_pools.return_value = [pool]
        sync_client.read_workers_for_work_pool.return_value = []
        task_manager._sync_client = sync_client

        result = task_manager.list_workers()
        assert len(result) == 1
        assert result[0]["worker_name"] == ""
        assert result[0]["worker_status"] == "no_workers"

    def test_read_workers_failure_skipped(self, task_manager):
        """Pool whose worker read fails is skipped."""
        pool_a = _make_pool("device|dummy")
        pool_b = _make_pool("monitor|dummy")
        worker = _make_worker("w1", WorkerStatus.ONLINE)

        sync_client = mock.Mock()
        sync_client.read_work_pools.return_value = [pool_a, pool_b]
        sync_client.read_workers_for_work_pool.side_effect = [
            RuntimeError("fail"),
            [worker],
        ]
        task_manager._sync_client = sync_client

        result = task_manager.list_workers()
        assert len(result) == 1
        assert result[0]["worker_name"] == "w1"


class TestRestartWorker:
    """Tests for TaskFlowManager.restart_worker."""

    def test_empty_name(self, task_manager):
        """Empty worker name returns failure."""
        success, msg = task_manager.restart_worker("")
        assert success is False
        assert "empty" in msg

    @mock.patch.object(TaskFlowManager, "_start_worker_process")
    @mock.patch.object(TaskFlowManager, "_kill_workers_by_regex")
    def test_process_not_found_starts_new_worker(
        self, mock_kill, mock_start, task_manager
    ):
        """When no process found (OFFLINE), start a new worker."""
        mock_kill.return_value = ([], [])
        mock_start.return_value = True

        success, msg = task_manager.restart_worker("process-device|dummy")
        assert success is True
        assert "restarted successfully" in msg
        mock_start.assert_called_once_with("dummy", "job")

    @mock.patch.object(TaskFlowManager, "_start_worker_process")
    @mock.patch.object(TaskFlowManager, "_kill_workers_by_regex")
    def test_kill_and_restart_success(
        self, mock_kill, mock_start, task_manager
    ):
        """Worker is killed and restarted successfully."""
        mock_kill.return_value = ([1234], [])
        mock_start.return_value = True

        success, msg = task_manager.restart_worker("process-device|dummy")
        assert success is True
        assert "restarted successfully" in msg
        mock_start.assert_called_once_with("dummy", "job")

    @mock.patch.object(TaskFlowManager, "_start_worker_process")
    @mock.patch.object(TaskFlowManager, "_kill_workers_by_regex")
    def test_kill_without_restart(self, mock_kill, mock_start, task_manager):
        """When restart cannot start, returns True with warning message."""
        mock_kill.return_value = ([1234], [])
        mock_start.return_value = False

        success, msg = task_manager.restart_worker("process-device|dummy")
        assert success is True
        assert "could not be restarted" in msg

    @mock.patch.object(TaskFlowManager, "_start_worker_process")
    @mock.patch.object(TaskFlowManager, "_kill_workers_by_regex")
    def test_kill_unknown_worker_name(
        self, mock_kill, mock_start, task_manager
    ):
        """When worker name unrecognized, returns True with warning."""
        mock_kill.return_value = ([1234], [])

        success, msg = task_manager.restart_worker("process-unknown|dummy")
        assert success is True
        assert "could not be restarted" in msg
        mock_start.assert_not_called()


class TestWorkerNameToProctitle:
    """Tests for TaskFlowManager._worker_name_to_proctitle."""

    def test_empty_name(self):
        """Empty worker name returns empty string."""
        assert TaskFlowManager._worker_name_to_proctitle("") == ""

    def test_job_worker(self):
        """Job worker proctitle matches worker name directly."""
        name = "process-device|dummy"
        assert (
            TaskFlowManager._worker_name_to_proctitle(name)
            == "[prefect] process-device|dummy"
        )

    def test_monitor_worker(self):
        """Monitor worker proctitle uses _device_monitor suffix."""
        name = "process-device|dummy_monitor"
        assert (
            TaskFlowManager._worker_name_to_proctitle(name)
            == "[prefect] process-device|dummy_device_monitor"
        )

    def test_mgr_worker(self):
        """Mgr worker proctitle uses _device_mgr suffix."""
        name = "process-device|dummy_mgr"
        assert (
            TaskFlowManager._worker_name_to_proctitle(name)
            == "[prefect] process-device|dummy_device_mgr"
        )


class TestParseWorkerName:
    """Tests for TaskFlowManager._parse_worker_name."""

    def test_invalid_prefix(self):
        """Worker name without process- prefix returns (None, None)."""
        assert TaskFlowManager._parse_worker_name("dummy") == (None, None)

    def test_unknown_pool_prefix(self):
        """Pool name with unknown prefix returns (None, None)."""
        result = TaskFlowManager._parse_worker_name("process-unknown|dummy")
        assert result == (None, None)

    def test_parse_job_worker(self):
        """Job worker name parsed correctly."""
        name = f"process-{Constant.WORK_POOL_DEVICE_PREFIX}dummy"
        assert TaskFlowManager._parse_worker_name(name) == (
            "dummy",
            "job",
        )

    def test_parse_monitor_worker(self):
        """Monitor worker name parsed correctly."""
        name = f"process-{Constant.WORK_POOL_DEVICE_PREFIX}dummy_monitor"
        assert TaskFlowManager._parse_worker_name(name) == (
            "dummy",
            "monitor",
        )

    def test_parse_mgr_worker(self):
        """Manager worker name parsed correctly."""
        name = f"process-{Constant.WORK_POOL_DEVICE_PREFIX}dummy_mgr"
        assert TaskFlowManager._parse_worker_name(name) == (
            "dummy",
            "mgr",
        )


class TestStartWorkerProcess:
    """Tests for TaskFlowManager._start_worker_process."""

    def test_device_not_found(self, task_manager):
        """Device not in device manager returns False."""
        device_manager = mock.Mock()
        device_manager.get_devices.return_value = {}
        task_manager.device_manager = device_manager

        result = task_manager._start_worker_process("nope", "job")
        assert result is False

    @mock.patch("wy_qcos.task_manager.task_manager.multiprocessing")
    def test_start_job_worker(self, mock_mp, task_manager):
        """Job worker is started for a known device."""
        device = mock.Mock()
        device_manager = mock.Mock()
        device_manager.get_devices.return_value = {"dummy": device}
        task_manager.device_manager = device_manager
        task_manager.deployments = {}

        mock_process = mock.Mock()
        mock_mp.Process.return_value = mock_process

        result = task_manager._start_worker_process("dummy", "job")
        assert result is True
        mock_mp.Process.assert_called_once()
        mock_process.start.assert_called_once()

    @mock.patch("wy_qcos.task_manager.task_manager.multiprocessing")
    def test_start_monitor_worker_disabled(self, mock_mp, task_manager):
        """Monitor worker not started when device monitor disabled."""
        device = mock.Mock()
        device_manager = mock.Mock()
        device_manager.get_devices.return_value = {"dummy": device}
        task_manager.device_manager = device_manager
        task_manager.deployments = {}
        task_manager._is_device_monitor_enabled = mock.Mock(return_value=False)

        result = task_manager._start_worker_process("dummy", "monitor")
        assert result is False
        mock_mp.Process.assert_not_called()
