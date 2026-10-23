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

"""Unit tests for JobRepository."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from wy_qcos.api import schemas
from wy_qcos.db.models import Job
from wy_qcos.db.repositories.job import JobRepository


def _make_job(**kwargs):
    """Create a Job with required project_id field."""
    defaults = {
        "project_id": "00000000-0000-0000-0000-000000000000",
    }
    defaults.update(kwargs)
    return Job(**defaults)


def _patched_model_dump(self, **kwargs):
    """Patch model_dump to exclude created_at/updated_at None values."""
    from pydantic import BaseModel

    result = BaseModel.model_dump(self, **kwargs)
    # Remove None values for created_at/updated_at to avoid NOT NULL
    # constraint violations, but keep other None fields like job_id
    for key in ("created_at", "updated_at"):
        if result.get(key) is None:
            result.pop(key, None)
    return result


class TestJobRepositoryCreate:
    """Test JobRepository create_job method."""

    @pytest.fixture(autouse=True)
    def _patch_model_dump(self):
        """Patch SubmitJobRequest.model_dump to exclude None values."""
        with patch.object(
            schemas.SubmitJobRequest,
            "model_dump",
            _patched_model_dump,
        ):
            yield

    def test_create_job_success(self, in_memory_db):
        """Test creating a job successfully."""
        repo = JobRepository(in_memory_db)
        job_create = schemas.SubmitJobRequest(
            project_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
        )
        success, error, job = repo.create_job(job_create)
        assert success is True
        assert error is None
        assert job is not None
        assert job.backend == "dev1"

    def test_create_job_with_none_defaults(self, in_memory_db):
        """Test creating job with None values defaults to empty."""
        repo = JobRepository(in_memory_db)
        job_create = schemas.SubmitJobRequest(
            project_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
            params=None,
            options=None,
            tags=None,
            profiling=None,
            callbacks=None,
            driver_options=None,
            transpiler_options=None,
            qec_options=None,
            qem_options=None,
            extra_specs=None,
        )
        success, error, job = repo.create_job(job_create)
        assert success is True
        assert job.params == {}
        assert job.options == {}
        assert job.tags == []
        assert job.profiling == []
        assert job.callbacks == []
        assert job.driver_options == {}
        assert job.transpiler_options == {}
        assert job.qec_options == {}
        assert job.qem_options == {}
        assert job.extra_specs == {}

    def test_create_job_with_custom_job_id(self, in_memory_db):
        """Test creating job with custom job_id."""
        repo = JobRepository(in_memory_db)
        custom_id = str(uuid.uuid4())
        job_create = schemas.SubmitJobRequest(
            project_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
            job_id=custom_id,
        )
        success, error, job = repo.create_job(job_create)
        assert success is True
        assert str(job.id) == custom_id

    def test_create_job_no_commit(self, in_memory_db):
        """Test creating job without auto commit."""
        repo = JobRepository(in_memory_db)
        job_create = schemas.SubmitJobRequest(
            project_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
        )
        success, error, job = repo.create_job(job_create, auto_commit=False)
        assert success is True
        # rollback to avoid affecting other tests
        in_memory_db.rollback()

    def test_create_job_integrity_error_duplicate(self, mock_db_session):
        """Test create job with duplicate key integrity error."""
        from sqlalchemy.exc import IntegrityError

        mock_db_session.add.side_effect = IntegrityError(
            "INSERT INTO jobs", {}, "duplicate key value"
        )
        repo = JobRepository(mock_db_session)
        job_create = schemas.SubmitJobRequest(
            project_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
        )
        success, error, job = repo.create_job(job_create)
        assert success is False
        assert "already exists" in error
        assert job is None

    def test_create_job_integrity_error_foreign_key(self, mock_db_session):
        """Test create job with foreign key integrity error."""
        from sqlalchemy.exc import IntegrityError

        mock_db_session.add.side_effect = IntegrityError(
            "INSERT INTO jobs", {}, "foreign key constraint failed"
        )
        repo = JobRepository(mock_db_session)
        job_create = schemas.SubmitJobRequest(
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
        )
        success, error, job = repo.create_job(job_create)
        assert success is False
        assert "Invalid project or user" in error
        assert job is None

    def test_create_job_integrity_error_other(self, mock_db_session):
        """Test create job with other integrity error."""
        from sqlalchemy.exc import IntegrityError

        mock_db_session.add.side_effect = IntegrityError(
            "INSERT INTO jobs", {}, "some other constraint"
        )
        repo = JobRepository(mock_db_session)
        job_create = schemas.SubmitJobRequest(
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
        )
        success, error, job = repo.create_job(job_create)
        assert success is False
        assert "constraint violation" in error
        assert job is None

    def test_create_job_generic_error(self, mock_db_session):
        """Test create job with generic database error."""
        mock_db_session.add.side_effect = Exception("DB connection lost")
        repo = JobRepository(mock_db_session)
        job_create = schemas.SubmitJobRequest(
            source_code=["OPENQASM 2.0;"],
            code_type="qasm",
            backend="dev1",
        )
        success, error, job = repo.create_job(job_create)
        assert success is False
        assert "Database error" in error
        assert job is None


class TestJobRepositoryGet:
    """Test JobRepository get methods."""

    def test_get_job_by_uuid(self, in_memory_db):
        """Test getting job by UUID."""
        repo = JobRepository(in_memory_db)
        job_id = str(uuid.uuid4())
        job = _make_job(
            id=job_id,
            backend="dev1",
            job_status="QUEUED",
        )
        in_memory_db.add(job)
        in_memory_db.commit()

        success, error, result = repo.get_job_by_uuid(job_id)
        assert success is True
        assert result is not None
        assert str(result.id) == job_id

    def test_get_jobs(self, in_memory_db):
        """Test getting all jobs."""
        repo = JobRepository(in_memory_db)
        for i in range(3):
            job = _make_job(
                id=str(uuid.uuid4()),
                backend=f"dev{i}",
                job_status="QUEUED",
            )
            in_memory_db.add(job)
        in_memory_db.commit()

        success, error, jobs = repo.get_jobs()
        assert success is True
        assert len(jobs) == 3

    def test_get_jobs_with_filters(self, in_memory_db):
        """Test getting jobs with filters."""
        repo = JobRepository(in_memory_db)
        job = _make_job(
            id=str(uuid.uuid4()),
            backend="dev1",
            job_status="RUNNING",
        )
        in_memory_db.add(job)
        in_memory_db.commit()

        success, error, jobs = repo.get_jobs(filters={"job_status": "RUNNING"})
        assert success is True
        assert len(jobs) == 1
        assert jobs[0].job_status == "RUNNING"

    def test_get_jobs_paginated(self, in_memory_db):
        """Test getting jobs with pagination."""
        repo = JobRepository(in_memory_db)
        for i in range(5):
            job = _make_job(
                id=str(uuid.uuid4()),
                backend=f"dev{i}",
                job_status="QUEUED",
            )
            in_memory_db.add(job)
        in_memory_db.commit()

        success, error, result = repo.get_jobs_paginated(page=1, page_size=2)
        assert success is True
        assert result["total"] == 5
        assert len(result["items"]) == 2

    def test_get_jobs_count(self, in_memory_db):
        """Test getting jobs count."""
        repo = JobRepository(in_memory_db)
        for i in range(3):
            job = _make_job(
                id=str(uuid.uuid4()),
                backend="dev1",
                job_status="QUEUED",
            )
            in_memory_db.add(job)
        in_memory_db.commit()

        count = repo.get_jobs_count()
        assert count == 3

    def test_get_jobs_count_with_filters(self, in_memory_db):
        """Test getting jobs count with filters."""
        repo = JobRepository(in_memory_db)
        job = _make_job(
            id=str(uuid.uuid4()),
            backend="dev1",
            job_status="RUNNING",
        )
        in_memory_db.add(job)
        in_memory_db.commit()

        count = repo.get_jobs_count(filters={"job_status": "RUNNING"})
        assert count == 1


class TestJobRepositoryCount:
    """Test JobRepository count methods."""

    def test_count_by_status(self, in_memory_db):
        """Test counting jobs by status for a backend."""
        repo = JobRepository(in_memory_db)
        statuses = ["QUEUED", "RUNNING", "COMPLETED", "QUEUED"]
        for status in statuses:
            job = _make_job(
                id=str(uuid.uuid4()),
                backend="dev1",
                job_status=status,
            )
            in_memory_db.add(job)
        in_memory_db.commit()

        result = repo.count_by_status("dev1")
        assert result["QUEUED"] == 2
        assert result["RUNNING"] == 1
        assert result["COMPLETED"] == 1

    def test_count_by_status_error(self, mock_db_session):
        """Test count_by_status handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = JobRepository(mock_db_session)
        result = repo.count_by_status("dev1")
        assert result == {}

    def test_count_recent_created(self, in_memory_db):
        """Test counting recent jobs by created_at."""
        repo = JobRepository(in_memory_db)
        old_job = _make_job(
            id=str(uuid.uuid4()),
            backend="dev1",
            job_status="COMPLETED",
            created_at=datetime.now() - timedelta(days=2),
        )
        new_job = _make_job(
            id=str(uuid.uuid4()),
            backend="dev1",
            job_status="COMPLETED",
        )
        in_memory_db.add(old_job)
        in_memory_db.add(new_job)
        in_memory_db.commit()

        since = datetime.now() - timedelta(days=1)
        count = repo.count_recent(since, time_field="created_at")
        assert count == 1

    def test_count_recent_with_status(self, in_memory_db):
        """Test counting recent jobs with status filter."""
        repo = JobRepository(in_memory_db)
        job1 = _make_job(
            id=str(uuid.uuid4()),
            backend="dev1",
            job_status="COMPLETED",
        )
        job2 = _make_job(
            id=str(uuid.uuid4()),
            backend="dev1",
            job_status="RUNNING",
        )
        in_memory_db.add(job1)
        in_memory_db.add(job2)
        in_memory_db.commit()

        since = datetime.now() - timedelta(days=1)
        count = repo.count_recent(
            since, time_field="created_at", job_status="COMPLETED"
        )
        assert count == 1

    def test_count_recent_invalid_time_field(self, in_memory_db):
        """Test count_recent with invalid time_field returns 0."""
        repo = JobRepository(in_memory_db)
        since = datetime.now() - timedelta(days=1)
        count = repo.count_recent(since, time_field="invalid_field")
        assert count == 0

    def test_count_recent_error(self, mock_db_session):
        """Test count_recent handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = JobRepository(mock_db_session)
        since = datetime.now() - timedelta(days=1)
        count = repo.count_recent(since, time_field="created_at")
        assert count == 0


class TestJobRepositoryUpdate:
    """Test JobRepository update methods."""

    def test_update_job_results(self, in_memory_db):
        """Test updating job results."""
        repo = JobRepository(in_memory_db)
        job_id = str(uuid.uuid4())
        job = _make_job(
            id=job_id,
            backend="dev1",
            job_status="RUNNING",
        )
        in_memory_db.add(job)
        in_memory_db.commit()

        job_update = schemas.SetJobResultsRequest(
            job_id=job_id,
            job_status="COMPLETED",
            results=[{"counts": {"0": 100}}],
        )
        success, error, result = repo.update_job_results(job_id, job_update)
        assert success is True
        assert result.job_status == "COMPLETED"

    def test_update_job_results_none_values_excluded(self, in_memory_db):
        """Test update_job_results excludes None values."""
        repo = JobRepository(in_memory_db)
        job_id = str(uuid.uuid4())
        job = _make_job(
            id=job_id,
            backend="dev1",
            job_status="RUNNING",
        )
        in_memory_db.add(job)
        in_memory_db.commit()

        job_update = schemas.SetJobResultsRequest(
            job_id=job_id,
            job_status="COMPLETED",
            results=[{"counts": {"0": 100}}],
            started_at=None,
            ended_at=None,
            errors=None,
        )
        success, error, result = repo.update_job_results(job_id, job_update)
        assert success is True
        assert result.job_status == "COMPLETED"
        # None fields should not be updated
        assert result.started_at is None
        assert result.ended_at is None
