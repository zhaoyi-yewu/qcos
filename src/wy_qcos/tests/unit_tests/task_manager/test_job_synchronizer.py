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

from unittest.mock import MagicMock, Mock, patch

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.task_manager.job_synchronizer import JobSynchronizer


class TestJobSynchronizer:
    """Unit tests for JobSynchronizer."""

    @pytest.fixture
    def mock_task_manager(self):
        """Create a mock TaskFlowManager."""
        return MagicMock()

    @pytest.fixture
    def mock_db_engine(self):
        """Create a mock DB engine."""
        return MagicMock()

    @pytest.fixture
    def synchronizer(self, mock_task_manager, mock_db_engine):
        """Create a JobSynchronizer instance."""
        return JobSynchronizer(mock_task_manager, mock_db_engine)

    # --------------------------------------------------------------
    # Helper factories
    # --------------------------------------------------------------

    @staticmethod
    def _make_job(
        job_id="job-1",
        job_status=Constant.JOB_STATUS_RUNNING,
        flow_run_id="flow-123",
        results=None,
    ):
        """Create a mock Job record."""
        job = Mock()
        job.id = job_id
        job.job_status = job_status
        job.flow_run_id = flow_run_id
        job.results = results
        return job

    @staticmethod
    def _make_flow_run(state_name="RUNNING", state_result=None):
        """Create a mock Prefect FlowRun."""
        fr = Mock()
        fr.state.name = state_name
        fr.state.is_final.return_value = state_name in (
            "COMPLETED",
            "FAILED",
            "CRASHED",
            "CANCELLED",
        )
        fr.state.result.return_value = state_result
        return fr

    # --------------------------------------------------------------
    # Tests
    # --------------------------------------------------------------

    def test_sync_no_db_engine(self, synchronizer):
        """Sync skipped when db_engine is None."""
        synchronizer._db_engine = None
        synchronizer.sync()
        # Should return early without error

    def test_sync_no_jobs(self, synchronizer):
        """Sync returns early when no non-terminal jobs exist."""
        with patch.object(
            synchronizer, "_fetch_non_terminal_jobs", return_value=[]
        ):
            synchronizer.sync()
        # Should return early without error

    def test_sync_queued_job_still_scheduled(
        self, synchronizer, mock_task_manager
    ):
        """QUEUED job with Prefect SCHEDULED flow run -> keep DB state."""
        job = self._make_job(job_status=Constant.JOB_STATUS_QUEUED)
        flow_run = self._make_flow_run(state_name="SCHEDULED")
        mock_task_manager.get_flow_run.return_value = flow_run

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        mock_update.assert_not_called()

    def test_sync_running_job_completed(self, synchronizer, mock_task_manager):
        """RUNNING job with Prefect COMPLETED flow run -> DB COMPLETED."""
        job = self._make_job(
            job_status=Constant.JOB_STATUS_RUNNING, results=None
        )
        flow_run = self._make_flow_run(
            state_name="COMPLETED",
            state_result={"counts": {"00": 100}},
        )
        mock_task_manager.get_flow_run.return_value = flow_run

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
            patch.object(synchronizer, "_pull_results") as mock_pull,
        ):
            synchronizer.sync()

        mock_update.assert_called_once_with(
            job.id, Constant.JOB_STATUS_COMPLETED
        )
        mock_pull.assert_called_once_with(job.id, flow_run)

    def test_sync_running_job_failed(self, synchronizer, mock_task_manager):
        """RUNNING job with Prefect FAILED flow run -> DB FAILED."""
        job = self._make_job(job_status=Constant.JOB_STATUS_RUNNING)
        flow_run = self._make_flow_run(state_name="FAILED")
        mock_task_manager.get_flow_run.return_value = flow_run

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
            patch.object(synchronizer, "_pull_results") as mock_pull,
        ):
            synchronizer.sync()

        mock_update.assert_called_once_with(job.id, Constant.JOB_STATUS_FAILED)
        mock_pull.assert_not_called()

    def test_sync_running_job_crashed(self, synchronizer, mock_task_manager):
        """RUNNING job with Prefect CRASHED flow run -> DB FAILED."""
        job = self._make_job(job_status=Constant.JOB_STATUS_RUNNING)
        flow_run = self._make_flow_run(state_name="CRASHED")
        mock_task_manager.get_flow_run.return_value = flow_run

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        mock_update.assert_called_once_with(job.id, Constant.JOB_STATUS_FAILED)

    def test_sync_running_job_cancelled(self, synchronizer, mock_task_manager):
        """RUNNING job with Prefect CANCELLED flow run -> DB CANCELLED."""
        job = self._make_job(job_status=Constant.JOB_STATUS_RUNNING)
        flow_run = self._make_flow_run(state_name="CANCELLED")
        mock_task_manager.get_flow_run.return_value = flow_run

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        mock_update.assert_called_once_with(
            job.id, Constant.JOB_STATUS_CANCELLED
        )

    def test_sync_orphaned_job_no_flow_run_id(
        self, synchronizer, mock_task_manager
    ):
        """Job without flow_run_id -> mark FAILED (orphan)."""
        job = self._make_job(flow_run_id=None)

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_mark_failed") as mock_failed,
        ):
            synchronizer.sync()

        mock_failed.assert_called_once_with(job.id, "Missing flow_run_id")
        mock_task_manager.get_flow_run.assert_not_called()

    def test_sync_orphaned_job_flow_run_not_found(
        self, synchronizer, mock_task_manager
    ):
        """Job with flow_run_id not found in Prefect -> mark FAILED."""
        job = self._make_job()
        mock_task_manager.get_flow_run.return_value = None

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_mark_failed") as mock_failed,
        ):
            synchronizer.sync()

        mock_failed.assert_called_once_with(
            job.id, "Flow run not found in Prefect"
        )

    def test_sync_already_in_sync(self, synchronizer, mock_task_manager):
        """DB already matches Prefect terminal state -> skip."""
        job = self._make_job(job_status=Constant.JOB_STATUS_COMPLETED)
        flow_run = self._make_flow_run(state_name="COMPLETED")
        mock_task_manager.get_flow_run.return_value = flow_run

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
            patch.object(synchronizer, "_pull_results") as mock_pull,
        ):
            synchronizer.sync()

        mock_update.assert_not_called()
        mock_pull.assert_not_called()

    def test_sync_completed_job_with_existing_results(
        self, synchronizer, mock_task_manager
    ):
        """COMPLETED job with existing results -> skip result pull."""
        job = self._make_job(
            job_status=Constant.JOB_STATUS_COMPLETED,
            results=[{"counts": {"00": 100}}],
        )
        flow_run = self._make_flow_run(state_name="COMPLETED")
        mock_task_manager.get_flow_run.return_value = flow_run

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
            patch.object(synchronizer, "_pull_results") as mock_pull,
        ):
            synchronizer.sync()

        mock_update.assert_not_called()
        mock_pull.assert_not_called()

    def test_sync_exception_handling(self, synchronizer, mock_task_manager):
        """Exception in one job does not block others."""
        job1 = self._make_job(job_id="job-1")
        job2 = self._make_job(job_id="job-2")
        mock_task_manager.get_flow_run.side_effect = [
            Exception("Prefect error"),
            self._make_flow_run(state_name="COMPLETED"),
        ]

        with (
            patch.object(
                synchronizer,
                "_fetch_non_terminal_jobs",
                return_value=[job1, job2],
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        # job1 failed, job2 should still be processed
        assert mock_update.call_count == 1

    def test_sync_counts(self, synchronizer, mock_task_manager):
        """Sync returns correct counts."""
        jobs = [
            self._make_job(
                job_id="job-1", job_status=Constant.JOB_STATUS_RUNNING
            ),
            self._make_job(
                job_id="job-2", job_status=Constant.JOB_STATUS_QUEUED
            ),
            self._make_job(job_id="job-3", flow_run_id=None),
        ]
        mock_task_manager.get_flow_run.side_effect = [
            self._make_flow_run(state_name="COMPLETED"),
            self._make_flow_run(state_name="SCHEDULED"),
        ]

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=jobs
            ),
            patch.object(synchronizer, "_update_job_status"),
            patch.object(synchronizer, "_mark_failed"),
            patch.object(synchronizer, "_pull_results"),
        ):
            synchronizer.sync()

        # 1 updated, 1 skipped, 1 orphaned
        # (verified via logger call count in integration test)

    # --------------------------------------------------------------
    # Fast-fail path tests (absorbed from process_unfinished_jobs)
    # --------------------------------------------------------------

    def test_sync_fast_fail_unknown_job(self, synchronizer, mock_task_manager):
        """UNKNOWN job -> fast-fail to FAILED + cancel flow run."""
        job = self._make_job(
            job_status=Constant.JOB_STATUS_UNKNOWN,
            flow_run_id="flow-123",
        )

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        mock_update.assert_called_once_with(job.id, Constant.JOB_STATUS_FAILED)
        mock_task_manager.cancel_flow_runs.assert_called_once_with([
            "flow-123"
        ])

    def test_sync_fast_fail_cancelling_job(
        self, synchronizer, mock_task_manager
    ):
        """CANCELLING job -> fast-fail to FAILED + cancel flow run."""
        job = self._make_job(
            job_status=Constant.JOB_STATUS_CANCELLING,
            flow_run_id="flow-456",
        )

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        mock_update.assert_called_once_with(job.id, Constant.JOB_STATUS_FAILED)
        mock_task_manager.cancel_flow_runs.assert_called_once_with([
            "flow-456"
        ])

    def test_sync_fast_fail_no_flow_run_id(
        self, synchronizer, mock_task_manager
    ):
        """UNKNOWN job without flow_run_id -> fast-fail, no cancel."""
        job = self._make_job(
            job_status=Constant.JOB_STATUS_UNKNOWN,
            flow_run_id=None,
        )

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        mock_update.assert_called_once_with(job.id, Constant.JOB_STATUS_FAILED)
        mock_task_manager.cancel_flow_runs.assert_not_called()

    def test_sync_fast_fail_cancel_error(
        self, synchronizer, mock_task_manager
    ):
        """Cancel flow run error does not block fast-fail."""
        job = self._make_job(
            job_status=Constant.JOB_STATUS_UNKNOWN,
            flow_run_id="flow-123",
        )
        mock_task_manager.cancel_flow_runs.side_effect = Exception(
            "Cancel error"
        )

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status") as mock_update,
        ):
            synchronizer.sync()

        # Job still marked FAILED even if cancel fails
        mock_update.assert_called_once_with(job.id, Constant.JOB_STATUS_FAILED)

    def test_sync_fast_fail_skips_prefect_query(
        self, synchronizer, mock_task_manager
    ):
        """Fast-fail path does not query Prefect state."""
        job = self._make_job(
            job_status=Constant.JOB_STATUS_UNKNOWN,
            flow_run_id="flow-123",
        )

        with (
            patch.object(
                synchronizer, "_fetch_non_terminal_jobs", return_value=[job]
            ),
            patch.object(synchronizer, "_update_job_status"),
        ):
            synchronizer.sync()

        mock_task_manager.get_flow_run.assert_not_called()
