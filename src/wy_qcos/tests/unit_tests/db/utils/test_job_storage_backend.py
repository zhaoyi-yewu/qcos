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

"""Unit tests for job_storage_backend module."""

from unittest.mock import MagicMock, patch

from wy_qcos.common.constant import Constant
from wy_qcos.db.utils.job_storage_backend import (
    JobRecord,
    JobStorageBackend,
    SqlJobStorageBackend,
    redis_job_key,
)


class TestRedisJobKey:
    """Test redis_job_key function."""

    def test_key_without_flow_run_id(self):
        key = redis_job_key("job123")
        assert key == f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/job123"

    def test_key_with_flow_run_id(self):
        key = redis_job_key("job123", "flow456")
        assert key == f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/job123/flow456"

    def test_key_strips_wirecut_prefix(self):
        wirecut_prefix = Constant.WIRECUT_FLOW_RUN_PREFIX
        key = redis_job_key(f"{wirecut_prefix}job123")
        assert key == f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/job123"


class TestJobRecord:
    """Test JobRecord dataclass."""

    def test_from_sql_model(self):
        mock_record = MagicMock()
        mock_record.id = "job-id-123"
        mock_record.project_id = "proj-id-456"
        mock_record.user_id = "user-id-789"
        mock_record.backend = "dev1"
        mock_record.callbacks = ["cb1"]
        mock_record.profiling = ["prof1"]

        record = JobRecord.from_sql_model(mock_record)
        assert record.job_id == "job-id-123"
        assert record.project_id == "proj-id-456"
        assert record.user_id == "user-id-789"
        assert record.backend == "dev1"
        assert record.callbacks == ["cb1"]
        assert record.profiling == ["prof1"]

    def test_from_redis_dict(self):
        data = {
            "project_id": "proj-id-456",
            "user_id": "user-id-789",
            "backend": "dev1",
            "callbacks": ["cb1"],
            "profiling": ["prof1"],
        }
        record = JobRecord.from_redis_dict("job-id-123", data)
        assert record.job_id == "job-id-123"
        assert record.project_id == "proj-id-456"
        assert record.user_id == "user-id-789"
        assert record.backend == "dev1"
        assert record.callbacks == ["cb1"]
        assert record.profiling == ["prof1"]

    def test_from_redis_dict_defaults(self):
        record = JobRecord.from_redis_dict("job-id-123", {})
        assert record.job_id == "job-id-123"
        assert record.project_id == {}
        assert record.user_id == {}
        assert record.backend is None
        assert record.callbacks == []
        assert record.profiling == []


class TestJobStorageBackend:
    """Test JobStorageBackend abstract base class."""

    def test_store_sub_job_context_default(self):
        """Test default store_sub_job_context returns True."""

        class ConcreteBackend(JobStorageBackend):
            @property
            def storage_type(self):
                return "test"

            def get_job(self, job_id, flow_run_id=None):
                return None

            def update_job(self, job_id, **kwargs):
                return True

        backend = ConcreteBackend()
        assert backend.store_sub_job_context("job1", "flow1") is True


class TestSqlJobStorageBackend:
    """Test SqlJobStorageBackend class."""

    def test_storage_type(self):
        backend = SqlJobStorageBackend(MagicMock())
        assert backend.storage_type == Constant.RESULTS_DB_STORAGE_SQL

    def test_db_engine_property(self):
        engine = MagicMock()
        backend = SqlJobStorageBackend(engine)
        assert backend.db_engine is engine

    def test_get_job_no_engine(self):
        backend = SqlJobStorageBackend(None)
        assert backend.get_job("job1") is None

    @patch("wy_qcos.db.utils.job_storage_backend._create_sql_session")
    @patch("wy_qcos.db.utils.job_storage_backend.JobRepository")
    def test_get_job_success(self, mock_repo_class, mock_create_session):
        mock_session = MagicMock()
        mock_create_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_create_session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        mock_repo = MagicMock()
        mock_record = MagicMock()
        mock_record.id = "job1"
        mock_record.project_id = "proj1"
        mock_record.user_id = "user1"
        mock_record.backend = "dev1"
        mock_record.callbacks = []
        mock_record.profiling = []
        mock_repo.get_job_by_uuid.return_value = (True, None, mock_record)
        mock_repo_class.return_value = mock_repo

        backend = SqlJobStorageBackend(MagicMock())
        result = backend.get_job("job1")
        assert result is not None
        assert result.job_id == "job1"

    @patch("wy_qcos.db.utils.job_storage_backend._create_sql_session")
    @patch("wy_qcos.db.utils.job_storage_backend.JobRepository")
    def test_get_job_not_found(self, mock_repo_class, mock_create_session):
        mock_session = MagicMock()
        mock_create_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_create_session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        mock_repo = MagicMock()
        mock_repo.get_job_by_uuid.return_value = (False, None, None)
        mock_repo_class.return_value = mock_repo

        backend = SqlJobStorageBackend(MagicMock())
        assert backend.get_job("job1") is None

    def test_update_job_no_engine(self):
        backend = SqlJobStorageBackend(None)
        assert backend.update_job("job1", job_status="RUNNING") is False

    @patch("wy_qcos.db.utils.job_storage_backend._create_sql_session")
    @patch("wy_qcos.db.utils.job_storage_backend.JobRepository")
    def test_update_job_success(self, mock_repo_class, mock_create_session):
        mock_session = MagicMock()
        mock_create_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_create_session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        mock_repo = MagicMock()
        mock_record = MagicMock()
        mock_repo.get_job_by_uuid.return_value = (True, None, mock_record)
        mock_repo_class.return_value = mock_repo

        backend = SqlJobStorageBackend(MagicMock())
        result = backend.update_job(
            "job1",
            job_status="RUNNING",
            progress=50,
            started_at="2026-01-01T00:00:00",
        )
        assert result is True
        assert mock_record.job_status == "RUNNING"
        assert mock_record.progress == 50
        assert mock_record.started_at == "2026-01-01T00:00:00"
        mock_repo.commit.assert_called_once()

    @patch("wy_qcos.db.utils.job_storage_backend._create_sql_session")
    @patch("wy_qcos.db.utils.job_storage_backend.JobRepository")
    def test_update_job_not_found(self, mock_repo_class, mock_create_session):
        mock_session = MagicMock()
        mock_create_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_create_session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        mock_repo = MagicMock()
        mock_repo.get_job_by_uuid.return_value = (False, None, None)
        mock_repo_class.return_value = mock_repo

        backend = SqlJobStorageBackend(MagicMock())
        assert backend.update_job("job1", job_status="RUNNING") is False
