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

from datetime import datetime
from uuid import UUID
import logging
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from wy_qcos.db.models import Job
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.api import schemas

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """Database operation function library related to Job."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_job(
        self, job_create: schemas.SubmitJobRequest, auto_commit: bool = True
    ):
        """Create a new job.

        Args:
            job_create: Job creation request data
            auto_commit: If True, automatically commit the transaction.
                        If False, only add to session (requires manual commit).
                        In both cases, flush is called to populate object IDs.

        Returns:
            Tuple[bool, Exception|None, Job|None]: (success, error, job_record)
        """
        try:
            job_create_dict = job_create.model_dump()
            if job_create_dict.get("job_id"):
                job_create_dict["id"] = job_create_dict.get("job_id")
            del job_create_dict["job_id"]
            db_record = Job(**job_create_dict)
            self._db_session.add(db_record)

            # Flush to ensure object is in session
            # (populates auto-generated fields like ID)
            self._db_session.flush()

            if auto_commit:
                self._db_session.commit()
                self._db_session.refresh(db_record)

            return True, None, db_record
        except IntegrityError as e:
            error_msg = None
            error_str = str(e).lower()
            if "duplicate key" in error_str:
                error_msg = "Job ID already exists"
            elif "foreign key constraint" in error_str:
                error_msg = "Invalid project or user reference"
            else:
                error_msg = "Database constraint violation"
            return False, error_msg, None
        except Exception as e:
            return False, f"Database error: {e}", None

    def get_job_by_uuid(self, job_id: UUID, filters={}):
        """Get job by uuid.

        Args:
            job_id: UUID
            filters: db filters

        Returns:
            job records by uuid with filters
        """
        return self.get_by_uuid(Job, str(job_id), filters=filters)

    def get_jobs(self, filters: dict | None = None):
        """Get jobs with optional filtering.

        Args:
            filters: Dictionary with filter conditions. Supported keys are
                'id', 'uuid', 'project_id', 'user_id', 'job_status',
                'code_type', 'backend', 'job_name', 'is_callback_success'.

        Example::

            # No filter - get all jobs
            success, error, jobs = self.get_jobs()

            # Single filter
            success, error, jobs = self.get_jobs(filters={"project_id": "xxx"})

            # Multiple filters (AND condition)
            success, error, jobs = self.get_jobs(
                filters={
                    "project_id": "xxx",
                    "user_id": "yyy",
                    "job_status": "COMPLETED",
                }
            )

        Returns:
            Tuple[bool, Exception|None, list[Job]|None]
        """
        return self.get_all(Job, filters=filters)

    def get_jobs_count(self, filters: dict | None = None) -> int:
        """Get count of jobs with optional filtering.

        Args:
            filters: Dictionary with filter conditions. Supported keys are
                'project_id', 'user_id', 'job_status', 'code_type',
                'backend', 'job_name', 'is_callback_success'.

        Example::

            # Get total jobs count
            count = self.count_jobs()

            # Count jobs with specific status
            count = self.count_jobs(filters={"job_status": "COMPLETED"})

            # Multiple filters (AND condition)
            count = self.count_jobs(
                filters={"project_id": "xxx", "job_status": "QUEUED"}
            )

        Returns:
            Count of matching jobs, returns 0 on error
        """
        return self.count_with_filters(Job, filters=filters)

    def count_by_status(self, backend: str) -> dict:
        """Count jobs grouped by job_status for a backend (single query).

        Uses a single GROUP BY query instead of N separate COUNT
        queries, so the job table is scanned only once.

        Args:
            backend: device name (matches job.backend column)

        Returns:
            dict mapping each job_status value present in the
            database to its count for the given backend. Statuses
            with zero jobs are omitted from the result; callers
            should fill missing keys with 0 as needed.
        """
        try:
            query = (
                select(Job.job_status, func.count())
                .select_from(Job)
                .where(Job.backend == backend)
                .group_by(Job.job_status)
            )
            result = self._db_session.execute(query)
            return {row[0]: row[1] for row in result}
        except Exception as e:
            logger.error(
                f"Error counting jobs by status for backend {backend}: {e}"
            )
            return {}

    def count_recent(
        self,
        since: datetime,
        time_field: str = "created_at",
        job_status: str | None = None,
    ) -> int:
        """Count jobs whose time_field is at or after the given timestamp.

        Args:
            since: datetime threshold (inclusive). Jobs whose
                time_field >= since are counted.
            time_field: name of the Job datetime column to filter on,
                either 'created_at' (default) or 'ended_at'.
            job_status: optional job_status value to filter by (e.g.
                Constant.JOB_STATUS_COMPLETED). When None, all statuses
                are counted.

        Returns:
            Count of recently created/ended jobs, returns 0 on error
        """
        if time_field not in ("created_at", "ended_at"):
            logger.error(
                f"Unsupported time_field '{time_field}', expected "
                f"'created_at' or 'ended_at'"
            )
            return 0
        try:
            column = getattr(Job, time_field)
            query = (
                select(func.count()).select_from(Job).where(column >= since)
            )
            if job_status is not None:
                query = query.where(Job.job_status == job_status)
            result = self._db_session.execute(query)
            count = result.scalar()
            return count if count is not None else 0
        except Exception as e:
            logger.error(
                f"Error counting recent {time_field} "
                f"{job_status or 'all'} jobs since {since}: {e}"
            )
            return 0

    def update_job_results(
        self, job_id: UUID, job_update: schemas.SetJobResultsRequest
    ):
        """Update a job.

        Only updates fields that are explicitly set
        (non-None values are included).
        None values are excluded to prevent overwriting existing data.
        """
        # Exclude None values to avoid overwriting existing fields
        job_update_dict = job_update.model_dump(exclude_none=True)
        del job_update_dict["job_id"]
        job_update_dict["id"] = job_id

        return self.update(Job, str(job_id), **job_update_dict)
