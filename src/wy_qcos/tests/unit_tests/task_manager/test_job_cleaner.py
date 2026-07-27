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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from prefect.client.schemas.objects import StateType

from wy_qcos.common.constant import Constant
from wy_qcos.task_manager.job_cleaner import JobCleaner

MODULE = "wy_qcos.task_manager.job_cleaner"
DEV_PREFIX = Constant.WORK_POOL_DEVICE_PREFIX


# Default job-flow id used by _make_cleaner and _make_flow_run_for_expire
# so that flow-runs produced by the helper match the job-flow filter.
_DEFAULT_JOB_FLOW_ID = "00000000-0000-4000-8000-000000000001"


def _make_cleaner(db_engine=None):
    cleaner = JobCleaner.__new__(JobCleaner)
    cleaner._db_engine = db_engine
    cleaner._running = False
    cleaner._interval = 60
    cleaner._expire_days = 7
    cleaner._flow_expire_days = 7
    # _clean_prefect_flows reads task_manager.flows to resolve the
    # job-flow id; provide a mock with the default job-flow entry.
    cleaner._task_manager = Mock(
        flows={"job-flow": {"flow_id": _DEFAULT_JOB_FLOW_ID}}
    )
    return cleaner


def _make_flow_run(name, work_pool_name, state_name="PENDING"):
    mock = MagicMock()
    mock.name = name
    mock.work_pool_name = work_pool_name
    mock.id = uuid4()
    mock.state = MagicMock()
    mock.state.name = state_name
    mock.state.type = StateType.PENDING
    return mock


async def _mock_run_sync(func, *args, **kwargs):
    return func(*args, **kwargs)


_sentinel = object()


def _setup_orphan_cleaner(flows, job_ids=_sentinel):
    cleaner = _make_cleaner()
    sync_client = MagicMock()
    sync_client.read_flow_runs = Mock(return_value=flows)
    cleaner._get_sync_client = Mock(return_value=sync_client)
    cleaner._run_sync = Mock(side_effect=_mock_run_sync)
    cleaner._get_all_job_ids = Mock(
        return_value=set() if job_ids is _sentinel else job_ids
    )
    cleaner._get_loop = Mock(return_value=None)
    cleaner._poll_until_terminal = AsyncMock(return_value=True)
    return cleaner, sync_client


def _make_expired_job(days=30, flow_run_id=None):
    job = MagicMock()
    job.id = uuid4()
    job.created_at = datetime.now(timezone.utc) - timedelta(days=days)
    job.flow_run_id = flow_run_id
    return job


def _setup_expired_cleaner(
    jobs,
    mock_session_ctx,
    mock_repo_cls,
    delete_result=(True, None),
    **cleaner_kwargs,
):
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=MagicMock())
    ctx.__exit__ = Mock(return_value=False)
    mock_session_ctx.return_value = ctx
    mock_repo = MagicMock()
    mock_repo.get_jobs.return_value = (True, None, jobs)
    mock_repo.delete_by_uuid.return_value = delete_result
    mock_repo_cls.return_value = mock_repo

    cleaner = _make_cleaner(db_engine=MagicMock())
    if "sync_client" not in cleaner_kwargs:
        cleaner._run_sync = Mock(side_effect=_mock_run_sync)
        cleaner._get_loop = Mock(return_value=None)
    return cleaner, mock_repo


# ---- __init__ ----


class TestInit:
    def test_init_sets_defaults(self):
        with patch(f"{MODULE}.Config") as mock_cfg:
            mock_cfg.DEFAULT.JOB_CLEAN_INTERVAL = 30
            mock_cfg.DEFAULT.JOB_EXPIRE_DAYS = 3
            mock_cfg.DEFAULT.FLOW_EXPIRE_DAYS = 5
            cleaner = JobCleaner(MagicMock())
        assert cleaner._interval == 30
        assert cleaner._expire_days == 3
        assert cleaner._flow_expire_days == 5
        assert cleaner._running is False


# ---- start / stop ----


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start(self):
        cleaner = _make_cleaner()
        cleaner._scheduler = MagicMock()
        await cleaner.start()
        assert cleaner._running is True
        cleaner._scheduler.start.assert_called_once()
        cleaner._scheduler.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        cleaner = _make_cleaner()
        cleaner._running = True
        cleaner._scheduler = MagicMock()
        await cleaner.start()
        cleaner._scheduler.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop(self):
        cleaner = _make_cleaner()
        cleaner._running = True
        cleaner._scheduler = MagicMock()
        await cleaner.stop()
        assert cleaner._running is False
        cleaner._scheduler.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        cleaner = _make_cleaner()
        cleaner._scheduler = MagicMock()
        await cleaner.stop()
        cleaner._scheduler.shutdown.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_shutdown_exception(self):
        cleaner = _make_cleaner()
        cleaner._running = True
        cleaner._scheduler = MagicMock()
        cleaner._scheduler.shutdown.side_effect = RuntimeError("fail")
        await cleaner.stop()
        assert cleaner._running is False


# ---- _cleanup_job ----


class TestCleanupJob:
    @pytest.mark.asyncio
    async def test_skips_when_not_running(self):
        cleaner = _make_cleaner()
        cleaner._clean_orphaned_device_flows = AsyncMock()
        cleaner._clean_prefect_flows = AsyncMock()
        cleaner._clean_expired_job_flows = AsyncMock()
        await cleaner._cleanup_job()
        cleaner._clean_orphaned_device_flows.assert_not_called()
        cleaner._clean_prefect_flows.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_all_clean_methods(self):
        cleaner = _make_cleaner()
        cleaner._running = True
        cleaner._clean_orphaned_device_flows = AsyncMock()
        cleaner._clean_prefect_flows = AsyncMock()
        cleaner._clean_expired_job_flows = AsyncMock()
        await cleaner._cleanup_job()
        cleaner._clean_orphaned_device_flows.assert_awaited_once()
        cleaner._clean_prefect_flows.assert_awaited_once()
        cleaner._clean_expired_job_flows.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        cleaner = _make_cleaner()
        cleaner._running = True
        cleaner._clean_orphaned_device_flows = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        cleaner._clean_prefect_flows = AsyncMock()
        cleaner._clean_expired_job_flows = AsyncMock()
        await cleaner._cleanup_job()

    @pytest.mark.asyncio
    async def test_run_sync(self):
        cleaner = _make_cleaner()
        fn = Mock(return_value=42)
        result = await cleaner._run_sync(fn, "a", key="b")
        fn.assert_called_once_with("a", key="b")
        assert result == 42


# ---- _poll_until_terminal ----


class TestPollUntilTerminal:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "state_type",
        [
            StateType.COMPLETED,
            StateType.FAILED,
            StateType.CRASHED,
            StateType.CANCELLED,
            StateType.CANCELLING,
        ],
    )
    async def test_returns_true_on_terminal_state(self, state_type):
        cleaner = _make_cleaner()
        fr = MagicMock()
        fr.state = MagicMock()
        fr.state.type = state_type
        sync_client = Mock()
        sync_client.read_flow_run = Mock(return_value=fr)
        cleaner._run_sync = Mock(side_effect=_mock_run_sync)
        assert (
            await cleaner._poll_until_terminal(sync_client, uuid4(), 2) is True
        )

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self):
        cleaner = _make_cleaner()
        fr = MagicMock()
        fr.state = MagicMock()
        fr.state.type = StateType.PENDING
        sync_client = Mock()
        sync_client.read_flow_run = Mock(return_value=fr)
        cleaner._run_sync = Mock(side_effect=_mock_run_sync)
        assert (
            await cleaner._poll_until_terminal(sync_client, uuid4(), 0.1)
            is False
        )

    @pytest.mark.asyncio
    async def test_returns_false_on_cancelled_error(self):
        cleaner = _make_cleaner()

        async def raise_cancelled(func, *a, **kw):
            raise asyncio.CancelledError()

        cleaner._run_sync = Mock(side_effect=raise_cancelled)
        assert await cleaner._poll_until_terminal(Mock(), uuid4(), 2) is False

    @pytest.mark.asyncio
    async def test_continues_on_read_exception(self):
        cleaner = _make_cleaner()
        call_count = {"n": 0}

        async def side_effect(func, *a, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("read error")
            fr = MagicMock()
            fr.state = MagicMock()
            fr.state.type = StateType.FAILED
            return fr

        cleaner._run_sync = Mock(side_effect=side_effect)
        assert await cleaner._poll_until_terminal(Mock(), uuid4(), 5) is True

    @pytest.mark.asyncio
    async def test_returns_false_on_none_flow_run(self):
        cleaner = _make_cleaner()
        sync_client = Mock()
        sync_client.read_flow_run = Mock(return_value=None)
        cleaner._run_sync = Mock(side_effect=_mock_run_sync)
        assert (
            await cleaner._poll_until_terminal(sync_client, uuid4(), 0.1)
            is False
        )


# ---- _get_all_job_ids ----


class TestGetAllJobIds:
    def test_returns_none_when_db_engine_is_none(self):
        assert _make_cleaner(db_engine=None)._get_all_job_ids() is None

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    def test_returns_none_when_db_query_fails(self, mock_ctx, mock_repo_cls):
        ctx = MagicMock()
        ctx.__enter__ = Mock(return_value=MagicMock())
        ctx.__exit__ = Mock(return_value=False)
        mock_ctx.return_value = ctx
        mock_repo = MagicMock()
        mock_repo.get_jobs.return_value = (False, "DB error", None)
        mock_repo_cls.return_value = mock_repo
        assert _make_cleaner(db_engine=MagicMock())._get_all_job_ids() is None

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    def test_returns_empty_set_when_no_jobs(self, mock_ctx, mock_repo_cls):
        ctx = MagicMock()
        ctx.__enter__ = Mock(return_value=MagicMock())
        ctx.__exit__ = Mock(return_value=False)
        mock_ctx.return_value = ctx
        mock_repo = MagicMock()
        mock_repo.get_jobs.return_value = (True, None, [])
        mock_repo_cls.return_value = mock_repo
        assert _make_cleaner(db_engine=MagicMock())._get_all_job_ids() == set()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    def test_returns_set_of_uuids_on_success(self, mock_ctx, mock_repo_cls):
        ctx = MagicMock()
        ctx.__enter__ = Mock(return_value=MagicMock())
        ctx.__exit__ = Mock(return_value=False)
        mock_ctx.return_value = ctx
        id1, id2 = uuid4(), uuid4()
        j1, j2 = MagicMock(), MagicMock()
        j1.id, j2.id = id1, id2
        mock_repo = MagicMock()
        mock_repo.get_jobs.return_value = (True, None, [j1, j2])
        mock_repo_cls.return_value = mock_repo
        result = _make_cleaner(db_engine=MagicMock())._get_all_job_ids()
        assert result == {str(id1), str(id2)}

    @patch(f"{MODULE}.create_db_session")
    def test_returns_none_on_exception(self, mock_ctx):
        mock_ctx.side_effect = RuntimeError("connection lost")
        assert _make_cleaner(db_engine=MagicMock())._get_all_job_ids() is None


# ---- _check_uuid ----


class TestCheckUuid:
    def test_valid_uuid(self):
        is_valid, err = JobCleaner._check_uuid(str(uuid4()))
        assert is_valid is True
        assert err is None

    def test_invalid_uuid(self):
        assert JobCleaner._check_uuid("not-a-uuid")[0] is False

    def test_empty_string(self):
        assert JobCleaner._check_uuid("")[0] is False

    def test_uuid_version_mismatch(self):
        is_valid, err = JobCleaner._check_uuid(
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        )
        assert is_valid is False
        assert err == "UUID version mismatch"


# ---- _get_sync_client / _get_loop ----


class TestGetSyncClientAndLoop:
    @patch(f"{MODULE}.scheduler")
    def test_get_sync_client(self, mock_sched):
        mock_sched._task_manager._sync_client = MagicMock()
        assert (
            _make_cleaner()._get_sync_client()
            is mock_sched._task_manager._sync_client
        )

    @patch(f"{MODULE}.scheduler")
    def test_get_loop(self, mock_sched):
        mock_sched._task_manager.loop = MagicMock()
        assert _make_cleaner()._get_loop() is mock_sched._task_manager.loop


# ---- _clean_orphaned_device_flows ----


class TestCleanOrphanedDeviceFlows:
    @pytest.mark.asyncio
    async def test_aborts_when_db_fails(self):
        flow = _make_flow_run(str(uuid4()), DEV_PREFIX + "d")
        cleaner, sync_client = _setup_orphan_cleaner([flow], job_ids=None)
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "pool_name",
        [
            "other_pool",
            None,
        ],
    )
    async def test_skips_non_device_pool(self, pool_name):
        flow = _make_flow_run(str(uuid4()), pool_name)
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "pool_name",
        [
            "monitor|dev",
            "mgr|dev",
        ],
    )
    async def test_skips_monitor_and_mgr_prefix(self, pool_name):
        flow = _make_flow_run(str(uuid4()), pool_name)
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_non_uuid_name(self):
        flow = _make_flow_run("not-uuid", DEV_PREFIX + "d")
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_flow_in_job_ids(self):
        jid = str(uuid4())
        flow = _make_flow_run(jid, DEV_PREFIX + "d")
        cleaner, sync_client = _setup_orphan_cleaner([flow], job_ids={jid})
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_orphan_without_cancel(self):
        flow = _make_flow_run(
            str(uuid4()), DEV_PREFIX + "d", state_name="COMPLETED"
        )
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_called_once_with(flow.id)
        sync_client.set_flow_run_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_orphan_with_cancel(self):
        flow = _make_flow_run(
            str(uuid4()), DEV_PREFIX + "d", state_name="RUNNING"
        )
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        await cleaner._clean_orphaned_device_flows()
        sync_client.set_flow_run_state.assert_called_once()
        sync_client.delete_flow_run.assert_called_once_with(flow.id)

    @pytest.mark.asyncio
    async def test_cleanup_exception_per_flow(self):
        flow = _make_flow_run(
            str(uuid4()), DEV_PREFIX + "d", state_name="COMPLETED"
        )
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        sync_client.delete_flow_run.side_effect = RuntimeError("fail")
        await cleaner._clean_orphaned_device_flows()

    @pytest.mark.asyncio
    async def test_deletes_artifacts_via_sync_client(self):
        flow = _make_flow_run(
            str(uuid4()), DEV_PREFIX + "d", state_name="COMPLETED"
        )
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        sync_client.read_artifacts.return_value = [MagicMock(id=uuid4())]
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_called_once_with(flow.id)
        sync_client.read_artifacts.assert_called_once()
        sync_client.delete_artifact.assert_called_once()

    @pytest.mark.asyncio
    async def test_artifact_delete_exception_does_not_block_cleanup(self):
        flow = _make_flow_run(
            str(uuid4()), DEV_PREFIX + "d", state_name="COMPLETED"
        )
        cleaner, sync_client = _setup_orphan_cleaner([flow])
        sync_client.read_artifacts.side_effect = RuntimeError("fail")
        await cleaner._clean_orphaned_device_flows()
        sync_client.delete_flow_run.assert_called_once_with(flow.id)


def _make_flow_run_for_expire(
    name,
    flow_name="job-flow",
    state_type=StateType.COMPLETED,
    start_time=None,
    end_time=None,
    flow_id=None,
):
    """Build a mock flow-run for _clean_prefect_flows tests.

    _clean_prefect_flows filters by flow_id and uses end_time to decide
    expiration, so both are populated here. ``start_time`` is kept for
    backward compatibility with existing test call-sites.
    """
    mock = MagicMock()
    mock.name = name
    mock.id = uuid4()
    mock.flow_name = flow_name
    # flow_id must match the job-flow id configured in _make_cleaner so
    # the flow-run is not skipped by the job-flow filter.
    mock.flow_id = flow_id or _DEFAULT_JOB_FLOW_ID
    mock.state = MagicMock()
    mock.state.type = state_type
    ts = start_time or datetime.now(timezone.utc)
    mock.start_time = ts
    # _clean_prefect_flows checks end_time (not start_time) for expiration;
    # default end_time to start_time when not explicitly provided.
    mock.end_time = end_time if end_time is not None else ts
    return mock


# ---- _clean_prefect_flows ----


class TestCleanPrefectFlows:
    @pytest.mark.asyncio
    async def test_skips_when_flow_expire_disabled(self):
        """When FLOW_EXPIRE_DAYS=-1, cleanup is skipped entirely."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = -1
        cleaner._get_sync_client = Mock()
        await cleaner._clean_prefect_flows()
        cleaner._get_sync_client.assert_not_called()

    @staticmethod
    def _make_run_sync_that_calls_fn(flow_runs):
        """Create _run_sync mock that returns flow_runs on first call."""
        call_count = [0]

        async def _run_sync(fn, *args, **kwargs):
            if call_count[0] == 0:
                call_count[0] += 1
                return flow_runs
            call_count[0] += 1
            return fn(*args, **kwargs)

        return _run_sync

    @pytest.mark.asyncio
    async def test_no_expired_flows(self):
        """No expired flow-runs found."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = 7
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        flow = _make_flow_run_for_expire(
            "recent-flow",
            start_time=datetime.now(timezone.utc),
        )
        cleaner._run_sync = self._make_run_sync_that_calls_fn([flow])
        await cleaner._clean_prefect_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_expired_completed_flow(self):
        """Expired completed flow-run is deleted."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = 7
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        flow = _make_flow_run_for_expire(
            "old-flow",
            state_type=StateType.COMPLETED,
            start_time=old_time,
        )
        cleaner._run_sync = self._make_run_sync_that_calls_fn([flow])
        await cleaner._clean_prefect_flows()
        sync_client.delete_flow_run.assert_called_once_with(flow.id)

    @pytest.mark.asyncio
    async def test_skips_non_job_flow(self):
        """Flow-runs not belonging to job-flow are skipped."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = 7
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        # use a flow_id that differs from the job-flow id configured in
        # _make_cleaner so the flow-run is skipped by the job-flow filter
        flow = _make_flow_run_for_expire(
            "other-flow",
            flow_name="other-flow",
            start_time=old_time,
            flow_id="00000000-0000-4000-8000-000000000999",
        )
        cleaner._run_sync = self._make_run_sync_that_calls_fn([flow])
        await cleaner._clean_prefect_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_running_flow(self):
        """Non-completed flow-runs are skipped."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = 7
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        flow = _make_flow_run_for_expire(
            "running-flow",
            state_type=StateType.RUNNING,
            start_time=old_time,
        )
        cleaner._run_sync = self._make_run_sync_that_calls_fn([flow])
        await cleaner._clean_prefect_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_flow_without_start_time(self):
        """Flow-runs without start_time are skipped."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = 7
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        flow = _make_flow_run_for_expire(
            "no-start-flow",
            start_time=None,
        )
        cleaner._run_sync = self._make_run_sync_that_calls_fn([flow])
        await cleaner._clean_prefect_flows()
        sync_client.delete_flow_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_exception_does_not_block(self):
        """Exception deleting one flow-run does not block others."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = 7
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        flow1 = _make_flow_run_for_expire("flow1", start_time=old_time)
        flow2 = _make_flow_run_for_expire("flow2", start_time=old_time)
        sync_client.delete_flow_run.side_effect = RuntimeError("fail")
        cleaner._run_sync = self._make_run_sync_that_calls_fn([flow1, flow2])
        await cleaner._clean_prefect_flows()
        assert sync_client.delete_flow_run.call_count == 2

    @pytest.mark.asyncio
    async def test_read_flow_runs_exception_returns(self):
        """Exception fetching flow runs returns gracefully."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._flow_expire_days = 7
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)

        async def _failing_run_sync(fn, *args, **kwargs):
            raise RuntimeError("fail")

        cleaner._run_sync = _failing_run_sync
        await cleaner._clean_prefect_flows()
        sync_client.delete_flow_run.assert_not_called()


# ---- _clean_expired_job_flows ----


class TestCleanExpiredJobFlows:
    @pytest.mark.asyncio
    async def test_skips_when_expire_disabled(self):
        """When JOB_EXPIRE_DAYS=-1, cleanup is skipped entirely."""
        cleaner = _make_cleaner(db_engine=MagicMock())
        cleaner._expire_days = -1
        cleaner._get_sync_client = Mock()
        await cleaner._clean_expired_job_flows()
        cleaner._get_sync_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_db_engine(self):
        cleaner = _make_cleaner(db_engine=None)
        cleaner._get_sync_client = Mock()
        await cleaner._clean_expired_job_flows()
        cleaner._get_sync_client.assert_not_called()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_no_jobs_or_failed_query(self, mock_ctx, mock_repo_cls):
        cleaner, mock_repo = _setup_expired_cleaner(
            [], mock_ctx, mock_repo_cls
        )
        mock_repo.get_jobs.return_value = (False, "err", None)
        cleaner._get_sync_client = Mock()
        await cleaner._clean_expired_job_flows()
        cleaner._get_sync_client.assert_not_called()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_no_expired_jobs(self, mock_ctx, mock_repo_cls):
        job = MagicMock()
        job.created_at = datetime.now(timezone.utc)
        job.id = uuid4()
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        await cleaner._clean_expired_job_flows()
        mock_repo.delete_by_uuid.assert_not_called()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_deletes_expired_job_with_flow(
        self, mock_ctx, mock_repo_cls
    ):
        job = _make_expired_job(flow_run_id=uuid4())
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        await cleaner._clean_expired_job_flows()
        sync_client.delete_flow_run.assert_called_once()
        mock_repo.delete_by_uuid.assert_called_once()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_deletes_expired_job_without_flow(
        self, mock_ctx, mock_repo_cls
    ):
        job = _make_expired_job(flow_run_id=None)
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        cleaner._get_sync_client = Mock(return_value=MagicMock())
        await cleaner._clean_expired_job_flows()
        mock_repo.delete_by_uuid.assert_called_once()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_sync_client_unavailable(self, mock_ctx, mock_repo_cls):
        job = _make_expired_job(flow_run_id=uuid4())
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        cleaner._get_sync_client = Mock(side_effect=RuntimeError("no client"))
        await cleaner._clean_expired_job_flows()
        mock_repo.delete_by_uuid.assert_called_once()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_delete_flow_exception(self, mock_ctx, mock_repo_cls):
        job = _make_expired_job(flow_run_id=uuid4())
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        sync_client = MagicMock()
        sync_client.delete_flow_run.side_effect = RuntimeError("fail")
        cleaner._get_sync_client = Mock(return_value=sync_client)
        await cleaner._clean_expired_job_flows()
        mock_repo.delete_by_uuid.assert_called_once()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_delete_by_uuid_error(self, mock_ctx, mock_repo_cls):
        job = _make_expired_job(flow_run_id=None)
        cleaner, _ = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls, delete_result=(False, "error")
        )
        cleaner._get_sync_client = Mock(return_value=MagicMock())
        await cleaner._clean_expired_job_flows()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_delete_by_uuid_exception(self, mock_ctx, mock_repo_cls):
        job = _make_expired_job(flow_run_id=None)
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        mock_repo.delete_by_uuid.side_effect = RuntimeError("boom")
        cleaner._get_sync_client = Mock(return_value=MagicMock())
        await cleaner._clean_expired_job_flows()

    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_db_exception_during_query(self, mock_ctx):
        mock_ctx.side_effect = RuntimeError("db down")
        await _make_cleaner(db_engine=MagicMock())._clean_expired_job_flows()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_naive_datetime_treated_as_utc(
        self, mock_ctx, mock_repo_cls
    ):
        job = MagicMock()
        job.id = uuid4()
        job.created_at = datetime.utcnow() - timedelta(days=30)
        job.flow_run_id = None
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        cleaner._get_sync_client = Mock(return_value=MagicMock())
        await cleaner._clean_expired_job_flows()
        mock_repo.delete_by_uuid.assert_called_once()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_job_with_none_created_at_skipped(
        self, mock_ctx, mock_repo_cls
    ):
        job = MagicMock()
        job.id = uuid4()
        job.created_at = None
        cleaner, mock_repo = _setup_expired_cleaner(
            [job], mock_ctx, mock_repo_cls
        )
        await cleaner._clean_expired_job_flows()
        mock_repo.delete_by_uuid.assert_not_called()

    @patch(f"{MODULE}.JobRepository")
    @patch(f"{MODULE}.create_db_session")
    @pytest.mark.asyncio
    async def test_expired_deletes_artifacts(self, mock_ctx, mock_repo_cls):
        job = _make_expired_job(flow_run_id=uuid4())
        cleaner, _ = _setup_expired_cleaner([job], mock_ctx, mock_repo_cls)
        sync_client = MagicMock()
        cleaner._get_sync_client = Mock(return_value=sync_client)
        await cleaner._clean_expired_job_flows()
        sync_client.delete_flow_run.assert_called_once()
        sync_client.read_artifacts.assert_called_once()


# ---- _delete_artifacts_sync ----


class TestDeleteArtifactsSync:
    @pytest.mark.parametrize("artifacts_count", [0, 2])
    def test_delete_artifacts(self, artifacts_count):
        arts = [MagicMock(id=uuid4()) for _ in range(artifacts_count)]
        sync_client = MagicMock()
        sync_client.read_artifacts = Mock(return_value=arts)
        JobCleaner._delete_artifacts_sync(sync_client, uuid4())
        assert sync_client.read_artifacts.call_count == 1
        assert sync_client.delete_artifact.call_count == artifacts_count

    def test_propagates_exception(self):
        sync_client = MagicMock()
        sync_client.read_artifacts = Mock(side_effect=RuntimeError("fail"))
        with pytest.raises(RuntimeError, match="fail"):
            JobCleaner._delete_artifacts_sync(sync_client, uuid4())
