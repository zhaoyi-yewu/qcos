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

"""Synchronize non-terminal job states with Prefect flow runs on startup.

This module is invoked once during QCOS server startup (from
:func:`wy_qcos.server.Server.run`) to reconcile database job records with
the actual flow-run states stored in Prefect. It handles cases where QCOS
was restarted while jobs were in-flight, leaving DB states stale.

The synchronizer absorbs the legacy `process_unfinished_jobs()` logic:
jobs in UNKNOWN / CANCELLING states are fast-failed (set FAILED + cancel
Prefect flow run) before the full Prefect state sync runs.
"""

import time

from loguru import logger

from wy_qcos.common.constant import Constant
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.db.utils import db_utils
from wy_qcos.db.utils.db_utils import create_db_session


class JobSynchronizer:
    """Synchronize DB job states with Prefect flow-run states.

    Usage:
        syncer = JobSynchronizer(task_manager=..., db_engine=...)
        syncer.sync()
    """

    def __init__(self, task_manager, db_engine):
        """Initialize the synchronizer.

        Args:
            task_manager: TaskFlowManager instance for Prefect queries.
            db_engine: SQLAlchemy engine for DB access.
        """
        self._task_manager = task_manager
        self._db_engine = db_engine

    def sync(self):
        """Main entry point: sync all non-terminal jobs.

        Fetches every job whose status is not terminal, queries Prefect
        for the corresponding flow-run state, and updates the DB record
        to match. Results are pulled for completed jobs that do not yet
        have results stored.
        """
        if self._db_engine is None:
            logger.warning("DB engine not initialized, skipping job sync")
            return

        started_at = time.monotonic()
        jobs = self._fetch_non_terminal_jobs()
        if not jobs:
            logger.info("No non-terminal jobs to sync")
            return

        logger.info(f"Syncing {len(jobs)} non-terminal jobs with Prefect")

        updated = 0
        skipped = 0
        orphaned = 0
        fast_failed = 0
        failed = 0

        for job in jobs:
            try:
                result = self._sync_one(job)
                if result == "updated":
                    updated += 1
                elif result == "skipped":
                    skipped += 1
                elif result == "orphaned":
                    orphaned += 1
                elif result == "fast_failed":
                    fast_failed += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to sync job {job.id}: {e}")

        elapsed = time.monotonic() - started_at
        logger.info(
            f"Job sync complete in {elapsed:.2f}s: "
            f"{updated} updated, {skipped} skipped, "
            f"{orphaned} orphaned, {fast_failed} fast-failed, "
            f"{failed} failed"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_non_terminal_jobs(self):
        """Fetch all jobs with non-terminal status from DB.

        Returns:
            list of Job model instances.
        """
        with create_db_session(self._db_engine) as session:
            repo = JobRepository(session)
            success, err, records = repo.get_jobs()
            if not success:
                logger.error(f"Failed to fetch jobs: {err}")
                return []
            return [
                r
                for r in records
                if r.job_status in Constant.JOB_NON_TERMINAL_STATUSES
            ]

    def _sync_one(self, job_record):
        """Sync a single job with its Prefect flow run.

        Absorbs the legacy `process_unfinished_jobs()` fast-fail logic:
        jobs in UNKNOWN / CANCELLING states are set to FAILED and their
        Prefect flow runs are cancelled before any Prefect state query.

        Args:
            job_record: Job model instance from the initial query.

        Returns:
            "updated"     — job status was updated
            "skipped"     — job status unchanged (still active in Prefect)
            "orphaned"    — flow run missing, job marked FAILED
            "fast_failed" — legacy UNKNOWN/CANCELLING fast-fail path
        """
        job_id = job_record.id
        flow_run_id = job_record.flow_run_id

        # ---- Legacy fast-fail path (absorbed from process_unfinished_jobs)
        # Jobs in UNKNOWN / CANCELLING are likely stuck from a previous
        # run; fail them immediately and cancel any associated flow run.
        if job_record.job_status in (
            Constant.JOB_STATUS_UNKNOWN,
            Constant.JOB_STATUS_CANCELLING,
        ):
            logger.info(
                f"Fast-failing job {job_id} (status: {job_record.job_status})"
            )
            self._update_job_status(job_id, Constant.JOB_STATUS_FAILED)
            if flow_run_id:
                try:
                    self._task_manager.cancel_flow_runs([flow_run_id])
                except Exception as e:
                    logger.error(
                        f"Failed to cancel flow run {flow_run_id} "
                        f"for job {job_id}: {e}"
                    )
            return "fast_failed"

        # ---- Normal Prefect sync path
        # No flow_run_id -> orphan job
        if not flow_run_id:
            logger.warning(f"Job {job_id} has no flow_run_id, marking FAILED")
            self._mark_failed(job_id, "Missing flow_run_id")
            return "orphaned"

        # Query Prefect for the actual flow-run state
        flow_run = self._task_manager.get_flow_run(flow_run_id)
        if flow_run is None:
            logger.warning(
                f"Flow run {flow_run_id} not found for job {job_id}, "
                f"marking FAILED"
            )
            self._mark_failed(job_id, "Flow run not found in Prefect")
            return "orphaned"

        prefect_state = flow_run.state.name.upper()
        qcos_state = self._map_prefect_state(prefect_state)

        # Prefect still active -> keep DB state unchanged
        if qcos_state is None:
            logger.debug(
                f"Job {job_id} still active in Prefect "
                f"(state={prefect_state}), skipping"
            )
            return "skipped"

        # DB already matches Prefect terminal state -> nothing to do
        if job_record.job_status == qcos_state:
            logger.debug(
                f"Job {job_id} already in sync "
                f"(DB={job_record.job_status}, Prefect={prefect_state})"
            )
            return "skipped"

        # Update DB to match Prefect terminal state
        logger.info(
            f"Syncing job {job_id}: "
            f"DB={job_record.job_status} -> {qcos_state} "
            f"(Prefect={prefect_state})"
        )
        self._update_job_status(job_id, qcos_state)

        # Pull results if completed and results not yet stored
        if (
            qcos_state == Constant.JOB_STATUS_COMPLETED
            and not job_record.results
        ):
            self._pull_results(job_id, flow_run)

        return "updated"

    @staticmethod
    def _map_prefect_state(prefect_state):
        """Map Prefect state to QCOS terminal state.

        Args:
            prefect_state: Upper-case Prefect state name.

        Returns:
            QCOS terminal state string, or None if the Prefect state
            is not terminal (RUNNING, SCHEDULED, PENDING, etc.).
        """
        return Constant.PREFECT_TO_QCOS_TERMINAL_STATE.get(prefect_state)

    def _update_job_status(self, job_id, new_status):
        """Update job status in DB.

        Args:
            job_id: Job UUID.
            new_status: New QCOS job status string.
        """
        with create_db_session(self._db_engine) as session:
            repo = JobRepository(session)
            job = repo.get_job_by_uuid(str(job_id))
            if job:
                job.job_status = new_status
                session.commit()
            else:
                logger.warning(f"Job {job_id} not found during status update")

    def _mark_failed(self, job_id, reason):
        """Mark job as FAILED with an explanatory error entry.

        Args:
            job_id: Job UUID.
            reason: Human-readable failure reason.
        """
        with create_db_session(self._db_engine) as session:
            repo = JobRepository(session)
            job = repo.get_job_by_uuid(str(job_id))
            if not job:
                logger.warning(f"Job {job_id} not found during mark-failed")
                return
            job.job_status = Constant.JOB_STATUS_FAILED
            if not job.results:
                job.results = []
            job.results.append({
                "error": f"Startup sync: {reason}",
                "metadata": {"status": Constant.JOB_STATUS_FAILED},
            })
            session.commit()

    def _pull_results(self, job_id, flow_run):
        """Pull results from a completed Prefect flow run into DB.

        Args:
            job_id: Job UUID.
            flow_run: Prefect FlowRun object.
        """
        try:
            state = flow_run.state
            if not (state.is_final() and hasattr(state, "result")):
                return
            results = state.result()
            if results is None:
                return

            # Use the existing storage-backend-aware update path so
            # results land in SQL or Redis according to configuration.
            db_utils.db_update_job(
                job_id,
                self._db_engine,
                job_status=Constant.JOB_STATUS_COMPLETED,
                job_results=results,
                ended_at=results.get("ended_at")
                if isinstance(results, dict)
                else None,
            )
            logger.info(f"Pulled results for completed job {job_id}")
        except Exception as e:
            logger.error(f"Failed to pull results for job {job_id}: {e}")
