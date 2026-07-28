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
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from prefect.client.schemas.objects import StateType
from prefect.states import State

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.db.models import Job
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.db.utils.db_utils import create_db_session
from wy_qcos.task_manager import scheduler
from wy_qcos.task_manager.task_manager import TaskFlowManager


logger = logging.getLogger(__name__)


class JobCleaner:
    """Periodic job clean service.

    Scans Prefect flow runs to remove orphaned flows in device work
    pools that have no corresponding job in the database, and to delete
    expired jobs (older than configured days) along with their associated
    Prefect flow runs.
    """

    def __init__(self, app_db_engine, task_manager=None) -> None:
        self._scheduler = AsyncIOScheduler(daemon=True)
        self._running = False
        self._interval = Config.DEFAULT.JOB_SCAN_INTERVAL
        self._expire_days = Config.DEFAULT.JOB_EXPIRE_DAYS
        self._flow_expire_days = Config.DEFAULT.FLOW_EXPIRE_DAYS
        self._db_engine = app_db_engine
        self._task_manager = task_manager

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        logger.info(
            f"Starting job cleaner "
            f"(interval: {self._interval}min, "
            f"expire: {self._expire_days}d, "
            f"flow_expire: {self._flow_expire_days}d)"
        )

        self._scheduler.start()
        self._scheduler.add_job(
            self._cleanup_job,
            trigger="interval",
            minutes=self._interval,
            coalesce=True,
            max_instances=1,
            id="job_clean",
            replace_existing=True,
        )
        logger.info("Job cleaner started")

    async def stop(self) -> None:
        if not self._running:
            return
        logger.info("Stopping job cleaner...")
        self._running = False
        try:
            self._scheduler.shutdown(wait=True)
        except Exception as e:
            logger.warning(f"Error shutting down job cleaner: {e}")
        logger.info("Job cleaner stopped")

    async def _cleanup_job(self):
        if not self._running:
            return
        logger.info("Starting periodic job clean")
        try:
            await self._clean_orphaned_device_flows()
            await self._clean_prefect_flows()
            await self._clean_expired_job_flows()
        except Exception:
            logger.error("Job clean failed", exc_info=True)

    def _get_sync_client(self):
        return scheduler._task_manager._sync_client

    def _get_loop(self):
        return scheduler._task_manager.loop

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _poll_until_terminal(
        self, sync_client, flow_run_id, timeout_seconds
    ):
        """Poll flow run until it reaches a terminal state.

        Returns:
        True if flow reached a terminal state within timeout, False otherwise.
        """
        end_time = time.time() + timeout_seconds
        # Use short sleep intervals for polling
        while time.time() < end_time:
            try:
                flow_run = await self._run_sync(
                    sync_client.read_flow_run, flow_run_id
                )
                if (
                    flow_run
                    and flow_run.state
                    and flow_run.state.type
                    in (
                        StateType.COMPLETED,
                        StateType.FAILED,
                        StateType.CRASHED,
                        StateType.CANCELLED,
                        StateType.CANCELLING,
                    )
                ):
                    return True
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                return False
            except Exception:
                await asyncio.sleep(1)
        return False

    def _get_all_job_ids(self):
        """Get all job IDs from database.

        Returns:
            set of UUID strings on success, or None if DB query failed
            (to prevent falsely deleting all flows as orphans).
        """
        db_engine = self._db_engine
        if db_engine is None:
            logger.warning("DB engine not available, skipping orphan cleanup")
            return None

        try:
            with create_db_session(db_engine) as session:
                repo = JobRepository(session)
                success, error, jobs = repo.get_jobs()
                if not success:
                    logger.error(
                        f"DB query failed: {error} - "
                        f"skipping orphan cleanup to prevent data loss"
                    )
                    return None
                # Empty result is valid (no jobs in DB) - return empty set
                if not jobs:
                    return set()
                return {str(job.id) for job in jobs}
        except Exception as e:
            logger.error(
                f"Failed to fetch job IDs from DB: {e} - "
                f"skipping orphan cleanup to prevent data loss"
            )
            return None

    async def _clean_orphaned_device_flows(self):
        """Cancel and delete Prefect flows.

        Prefect flows in device|* pools that don't belong to any job
        in the database.
        """
        logger.info("Scanning for orphaned device flows...")
        sync_client = self._get_sync_client()

        # Get all flow runs via pagination (read_flow_runs is bounded by
        # PREFECT_API_DEFAULT_LIMIT, so loop over pages to fetch all).
        all_flow_runs = await self._run_sync(
            TaskFlowManager.read_all_flow_runs,
            sync_client,
        )
        logger.info(f"Fetched {len(all_flow_runs)} flow runs in total")

        # Get all job IDs from database
        job_ids = await self._run_sync(self._get_all_job_ids)
        if job_ids is None:
            # DB query failed - abort to prevent data loss
            logger.warning("Aborting orphan cleanup due to DB failure")
            return

        orphaned = []

        for flow_run in all_flow_runs:
            pool_name = getattr(flow_run, "work_pool_name", None)
            if not pool_name or not pool_name.startswith(
                Constant.WORK_POOL_DEVICE_PREFIX
            ):
                continue

            if pool_name.startswith(
                Constant.WORK_POOL_MONITOR_PREFIX
            ) or pool_name.startswith(Constant.WORK_POOL_MGR_PREFIX):
                continue

            name = flow_run.name
            # Validate UUID format (job IDs are UUIDs)
            is_uuid, _ = self._check_uuid(name=name)
            if not is_uuid:
                continue

            if name not in job_ids:
                orphaned.append(flow_run)

        if not orphaned:
            logger.info("No orphaned device flows found")
            return

        logger.info(
            f"Found {len(orphaned)} orphaned device flow(s), cleaning up..."
        )

        for flow_run in orphaned:
            try:
                # Step 1: Request cancellation
                state_name = flow_run.state.name.upper()
                if state_name in Constant.PREFECT_CANCEL_REQUIRED_STATES:
                    cancelling = State(type=StateType.CANCELLING)

                    def _cancel(fid=flow_run.id):
                        sync_client.set_flow_run_state(
                            fid, state=cancelling, force=True
                        )

                    await self._run_sync(_cancel)
                    logger.debug(f"Requested cancellation for {flow_run.name}")

                # Step 2: Wait for terminal state (max 5 seconds)
                await self._poll_until_terminal(
                    sync_client, flow_run.id, timeout_seconds=5
                )

                # Step 3: Delete the flow run
                def _delete(fid=flow_run.id):
                    sync_client.delete_flow_run(fid)

                await self._run_sync(_delete)

                # Step 4: Delete artifacts
                try:
                    await self._run_sync(
                        self._delete_artifacts_sync,
                        sync_client,
                        flow_run.id,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete artifacts for {flow_run.name}: "
                        f"{type(e).__name__}: {e}"
                    )

                logger.info(
                    f"Cleaned orphaned flow: {flow_run.name} "
                    f"(pool: {flow_run.work_pool_name})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to cleanup orphaned flow {flow_run.name}: {e}"
                )

    async def _clean_prefect_flows(self):
        """Clean expired completed Prefect flow-runs.

        Delete completed flow-runs that belong to the 'job-flow' flow
        and are older than the configured FLOW_EXPIRE_DAYS.
        A FLOW_EXPIRE_DAYS value of -1 disables this cleanup.
        """
        if self._flow_expire_days == -1:
            logger.info(
                "Flow expiration disabled (FLOW_EXPIRE_DAYS=-1), "
                "skipping expired flow cleanup"
            )
            return

        flow_expire_minutes = self._flow_expire_days * 24 * 60
        logger.info(
            f"Scanning for completed job-flow runs "
            f"(>{self._flow_expire_days} days / "
            f"{flow_expire_minutes} minutes)..."
        )

        sync_client = self._get_sync_client()

        # Compute cutoff timestamp
        flow_expire_cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=flow_expire_minutes * 60
        )

        expect_job_flow_id = None
        job_flow = self._task_manager.flows.get("job-flow", None)
        if job_flow:
            expect_job_flow_id = job_flow.get("flow_id", None)
        if not expect_job_flow_id:
            logger.error("Failed to fetch job-flow")
            return
        try:
            all_job_flow_runs = await self._run_sync(
                TaskFlowManager.read_all_flow_runs, sync_client
            )
        except Exception as e:
            logger.error(f"Failed to fetch flow runs: {e}")
            return

        expired_flow_runs = []
        for flow_run in all_job_flow_runs:
            # Only process flow-runs belonging to the job-flow
            flow_id = flow_run.flow_id
            if expect_job_flow_id != str(flow_id):
                continue

            # Only process completed flow-runs
            state = flow_run.state
            if state is None:
                continue
            if state.type not in (
                StateType.COMPLETED,
                StateType.FAILED,
                StateType.CRASHED,
                StateType.CANCELLED,
            ):
                continue

            # Check if flow-run completed time is older than cutoff
            end_time = flow_run.end_time
            if end_time is None:
                continue
            # Ensure timezone-aware comparison
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            if end_time < flow_expire_cutoff:
                expired_flow_runs.append(flow_run)

        if not expired_flow_runs:
            logger.info("No expired completed flow-runs found")
            return

        logger.info(
            f"Found {len(expired_flow_runs)} expired flow-run(s), deleting..."
        )

        for flow_run in expired_flow_runs:
            try:
                # Delete the flow run
                def _delete(fid=flow_run.id):
                    sync_client.delete_flow_run(fid)

                await self._run_sync(_delete)

                # Delete artifacts
                try:
                    await self._run_sync(
                        self._delete_artifacts_sync,
                        sync_client,
                        flow_run.id,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete artifacts for "
                        f"{flow_run.name}: {type(e).__name__}: {e}"
                    )

                logger.info(
                    f"Deleted expired flow-run: {flow_run.name} "
                    f"(ended: {end_time})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to delete expired flow-run {flow_run.name}: {e}"
                )

    async def _clean_expired_job_flows(self):
        """Clean expired job.

        Delete jobs older than expiry days from DB and
        their associated Prefect flow runs.
        A JOB_EXPIRE_DAYS value of -1 disables expiration cleanup.
        """
        if self._expire_days == -1:
            logger.info(
                "Job expiration disabled (JOB_EXPIRE_DAYS=-1), "
                "skipping expired job cleanup"
            )
            return

        logger.info(
            f"Scanning for expired jobs (>{self._expire_days} days)..."
        )

        db_engine = self._db_engine
        if db_engine is None:
            logger.warning(
                "DB engine not available, skipping expired job cleanup"
            )
            return

        expire_cutoff = datetime.now(timezone.utc) - timedelta(
            days=self._expire_days
        )

        expired_jobs = []
        try:
            with create_db_session(db_engine) as session:
                repo = JobRepository(session)
                success, error, jobs = repo.get_jobs()
                if not success or not jobs:
                    logger.info("No jobs found or failed to fetch jobs")
                    return

                for job in jobs:
                    created = job.created_at
                    if created is None:
                        continue
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if created < expire_cutoff:
                        expired_jobs.append({
                            "id": str(job.id),
                            "flow_run_id": str(job.flow_run_id)
                            if job.flow_run_id
                            else None,
                            "created_at": str(created),
                        })
        except Exception as e:
            logger.error(f"Failed to fetch expired jobs from DB: {e}")
            return

        if not expired_jobs:
            logger.info("No expired jobs found")
            return

        logger.info(f"Found {len(expired_jobs)} expired job(s), deleting...")

        sync_client = None
        try:
            sync_client = self._get_sync_client()
        except Exception:
            logger.warning(
                "Prefect sync client not available, "
                "will only delete DB records"
            )

        with create_db_session(db_engine) as session:
            repo = JobRepository(session)
            for job_info in expired_jobs:
                job_id = job_info["id"]
                flow_run_id = job_info["flow_run_id"]

                if sync_client and flow_run_id:
                    try:
                        fid = uuid.UUID(flow_run_id)

                        def _delete_flow(fid=fid):
                            sync_client.delete_flow_run(fid)

                        await self._run_sync(_delete_flow)

                        try:
                            await self._run_sync(
                                self._delete_artifacts_sync,
                                sync_client,
                                fid,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to delete artifacts for {job_id}: "
                                f"{type(e).__name__}: {e}"
                            )

                        logger.info(
                            f"Deleted Prefect flow for expired "
                            f"job: {job_id} "
                            f"(flow_run_id: {flow_run_id})"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete Prefect flow "
                            f"for job {job_id}: {e}"
                        )

                try:
                    deleted, err = repo.delete_by_uuid(Job, job_id)
                    if deleted:
                        logger.info(
                            f"Deleted expired job: {job_id} "
                            f"(created: {job_info['created_at']})"
                        )
                    elif err:
                        logger.error(
                            f"Failed to delete expired job {job_id}: {err}"
                        )
                except Exception as e:
                    logger.error(f"Error deleting expired job {job_id}: {e}")

    @staticmethod
    def _delete_artifacts_sync(sync_client, flow_run_id):
        from prefect.client.schemas.filters import (
            ArtifactFilter,
            ArtifactFilterFlowRunId,
        )

        artifacts = sync_client.read_artifacts(
            artifact_filter=ArtifactFilter(
                flow_run_id=ArtifactFilterFlowRunId(any_=[flow_run_id])
            )
        )
        for artifact in artifacts:
            sync_client.delete_artifact(artifact.id)

    @staticmethod
    def _check_uuid(name):
        is_valid, err = True, None
        try:
            uuid_obj = uuid.UUID(name, version=4)
            if str(uuid_obj) != name:
                is_valid = False
                err = "UUID version mismatch"
        except ValueError:
            is_valid = False
            err = "Not a valid UUID"
        return is_valid, err
