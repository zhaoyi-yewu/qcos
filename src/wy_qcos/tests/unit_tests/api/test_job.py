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

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4


from wy_qcos.api.posiq.routes_jsonrpc.errors import BadRequestError
from wy_qcos.api.posiq.routes_jsonrpc.job import (
    submit_job,
    get_job_status,
    get_job_results,
    get_jobs,
    cancel_jobs,
    delete_jobs,
    set_job_results,
    update_job,
)
from wy_qcos.api.schemas import (
    SubmitJobResponse,
    GetJobStatusRequest,
    GetJobResultsRequest,
    CancelJobsRequest,
    DeleteJobsRequest,
    SetJobResultsRequest,
    UpdateJobRequest,
)
from wy_qcos_client.client import Client
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.device.device_manager import DeviceManager
from wy_qcos.driver.driver_manager import DriverManager
from wy_qcos.driver.dummy.driver_dummy import DriverDummy
from wy_qcos.task_manager import TaskScheduler
from wy_qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.transpiler.transpiler_manager import TranspilerManager

response_info = {
    "job_id": uuid4(),
    "job_name": "",
    "job_status": "",
    "job_priority": 1,
    "description": "",
    "backend": "",
    "code_type": "",
    "source_code": [],
    "driver_options": {},
    "transpiler": "",
    "transpiler_options": {},
    "circuit_aggregation": "",
    "shots": 10,
    "dry_run": True,
    "progress": -1,
    "created_at": datetime.now(),
    "started_at": None,
    "ended_at": None,
}
job_ids = [uuid4(), uuid4(), uuid4()]


class TestJob:
    @classmethod
    def setup_class(cls):
        cls.job_id = ConstantForTest.job_id
        cls.job_ids = ConstantForTest.job_ids

    @pytest.mark.smoke
    @patch.object(Library, "validate_values_range")
    @patch.object(Library, "validate_schema")
    @patch.object(TranspilerManager, "get_transpiler")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    @patch.object(Client, "get_driver")
    @patch.object(Library, "validate_values_enum")
    @patch.object(DeviceManager, "get_devices")
    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(Client, "get_drivers")
    @patch.object(TaskScheduler, "get_driver_manager")
    @patch.object(TaskScheduler, "submit")
    def test_submit_job_success(
        self,
        mock_submit,
        mock_get_driver_manager,
        mock_get_drivers,
        mock_get_device_manager,
        mock_get_devices,
        mock_validate_values_enum,
        mock_get_driver,
        mock_get_transpiler_manager,
        mock_get_transpiler,
        mock_validate_schema,
        mock_validate_values_range,
    ):
        """Test successful job submission."""
        mock_validate_schema.return_value = (True, None)
        mock_validate_values_range.return_value = (True, None)
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpiler.return_value = TranspilerBase()
        mock_get_driver.return_value = DriverDummy()
        mock_validate_values_enum.return_value = (True, None)
        mock_get_driver_manager.return_value = DriverManager()
        mock_get_drivers.return_value = {}
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        device = Device("dummy", DriverDummy())
        device.set_enable(True)
        device.set_status("online")
        mock_get_devices.return_value = {"dummy": device}

        mock_submit.return_value = ({"flow_run_id": "flow-run-123"}, None)

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.flow_run_id = None
        mock_job_repo.create_job.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None
        mock_job_repo.get_job_by_uuid.return_value = (False, None, None)
        mock_job_repo.get_jobs_count.return_value = 1

        mock_client = Mock(spec=SubmitJobResponse)
        mock_client.source_code = [
            """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        measure q->c;
        """
        ]
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.circuit_aggregation = None
        mock_client.job_id = None
        mock_client.job_name = "Test Job"
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_priority = Constant.DEFAULT_JOB_PRIORITY
        mock_client.description = "Test description"
        mock_client.shots = Constant.DEFAULT_SHOTS
        mock_client.backend = "dummy"
        mock_client.driver_options = {}
        mock_client.transpiler = Constant.TRANSPILER_CMSS
        mock_client.transpiler_options = {}
        mock_client.profiling = None
        mock_client.callbacks = None
        mock_client.dry_run = False
        mock_client.project_id = None
        mock_client.user_id = None
        mock_client.code_compression_level = 0
        mock_client.tags = None
        mock_client.qec_options = None
        mock_client.flavor_id = None
        mock_client.extra_specs = None

        response = submit_job(mock_client, None, job_repo=mock_job_repo)

        assert response is not None
        assert response.job_status == Constant.JOB_STATUS_QUEUED
        mock_submit.assert_called_once()
        mock_job_repo.create_job.assert_called_once()
        mock_job_repo.commit.assert_called_once()

    @pytest.mark.smoke
    @patch.object(Library, "validate_values_range")
    @patch.object(Library, "validate_schema")
    @patch.object(TranspilerManager, "get_transpiler")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    @patch.object(Client, "get_driver")
    @patch.object(Library, "validate_values_enum")
    @patch.object(DeviceManager, "get_devices")
    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(Client, "get_drivers")
    @patch.object(TaskScheduler, "get_driver_manager")
    @patch.object(TaskScheduler, "submit")
    def test_submit_job_with_driver_options_new_fields(
        self,
        mock_submit,
        mock_get_driver_manager,
        mock_get_drivers,
        mock_get_device_manager,
        mock_get_devices,
        mock_validate_values_enum,
        mock_get_driver,
        mock_get_transpiler_manager,
        mock_get_transpiler,
        mock_validate_schema,
        mock_validate_values_range,
    ):
        mock_validate_schema.return_value = (True, None)
        mock_validate_values_range.return_value = (True, None)
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpiler.return_value = TranspilerBase()
        mock_get_driver.return_value = DriverDummy()
        mock_validate_values_enum.return_value = (True, None)
        mock_get_driver_manager.return_value = DriverManager()
        mock_get_drivers.return_value = {}
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        device = Device("dummy", DriverDummy())
        device.set_enable(True)
        device.set_status("online")
        mock_get_devices.return_value = {"dummy": device}

        mock_submit.return_value = ({"flow_run_id": "flow-run-123"}, None)

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.flow_run_id = None
        mock_job_repo.create_job.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None
        mock_job_repo.get_job_by_uuid.return_value = (False, None, None)
        mock_job_repo.get_jobs_count.return_value = 1

        mock_client = Mock(spec=SubmitJobResponse)
        mock_client.source_code = [
            """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        measure q->c;
        """
        ]
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.circuit_aggregation = None
        mock_client.job_id = None
        mock_client.job_name = "Test Job"
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_priority = Constant.DEFAULT_JOB_PRIORITY
        mock_client.description = "Test description"
        mock_client.shots = Constant.DEFAULT_SHOTS
        mock_client.backend = "dummy"
        mock_client.driver_options = {
            "max_job_wait_time": 100,
            "job_query_interval": 2,
        }
        mock_client.transpiler = Constant.TRANSPILER_CMSS
        mock_client.transpiler_options = {}
        mock_client.profiling = None
        mock_client.callbacks = None
        mock_client.dry_run = False
        mock_client.project_id = None
        mock_client.user_id = None
        mock_client.code_compression_level = 0
        mock_client.tags = None
        mock_client.qec_options = None
        mock_client.flavor_name = None
        mock_client.flavor_id = None
        mock_client.extra_specs = None

        response = submit_job(mock_client, None, job_repo=mock_job_repo)

        assert response is not None
        assert response.job_status == Constant.JOB_STATUS_QUEUED
        assert response.driver_options is not None
        assert response.driver_options["max_job_wait_time"] == 100
        assert response.driver_options["job_query_interval"] == 2
        mock_submit.assert_called_once()
        mock_job_repo.create_job.assert_called_once()
        mock_job_repo.commit.assert_called_once()

    @pytest.mark.smoke
    @patch.object(Library, "validate_values_enum")
    @patch.object(Library, "validate_schema")
    def test_submit_job_invalid_source_code(
        self, mock_validate_schema, mock_validate_enum
    ):
        """Test job submission with invalid source code."""
        # Simulate validation failure
        mock_validate_schema.return_value = (False, "Invalid source code")
        mock_validate_enum.return_value = (True, None)

        mock_client = Mock(spec=SubmitJobResponse)
        mock_client.source_code = []
        mock_client.job_id = None
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.circuit_aggregation = None
        mock_client.job_name = "Test"
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_priority = 1
        mock_client.description = None
        mock_client.shots = 1024
        mock_client.backend = "dummy"
        mock_client.driver_options = None
        mock_client.transpiler = None
        mock_client.transpiler_options = None
        mock_client.profiling = None
        mock_client.callbacks = None
        mock_client.dry_run = False
        mock_client.code_compression_level = 0
        mock_client.tags = None
        mock_client.qec_options = None
        mock_client.flavor_id = None
        mock_client.extra_specs = None

        with pytest.raises(BadRequestError):
            submit_job(mock_client, None)

    @pytest.mark.smoke
    @patch.object(Library, "validate_values_uuid")
    def test_submit_job_invalid_job_id(self, mock_validate_uuid):
        """Test job submission with invalid job_id format."""
        # ...existing code...
        mock_validate_uuid.return_value = (False, "Invalid UUID")

        mock_client = Mock(spec=SubmitJobResponse)
        mock_client.source_code = ["OPENQASM 2.0;"]
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.circuit_aggregation = None
        mock_client.job_id = "invalid-uuid"
        mock_client.job_name = "Test"
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_priority = 1
        mock_client.description = None
        mock_client.shots = 1024
        mock_client.backend = "dummy"
        mock_client.driver_options = {}
        mock_client.transpiler = None
        mock_client.transpiler_options = {}
        mock_client.profiling = None
        mock_client.callbacks = None
        mock_client.dry_run = False
        mock_client.code_compression_level = 0
        mock_client.tags = None
        mock_client.qec_options = None
        mock_client.flavor_id = None
        mock_client.extra_specs = None

        with pytest.raises(BadRequestError):
            submit_job(mock_client, None)

    @pytest.mark.smoke
    def test_get_job_status(self):
        """Test retrieving job status by job_id - success case."""
        mock_client = Mock(spec=GetJobStatusRequest)
        mock_client.job_id = self.job_id

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.asdict.return_value = response_info
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )

        result = get_job_status(mock_client, None, job_repo=mock_job_repo)
        assert str(result.job_id) == str(response_info["job_id"])
        assert result.job_status == response_info["job_status"]
        # Verify repository method was called with filters
        mock_job_repo.get_job_by_uuid.assert_called_once_with(
            self.job_id, filters={}
        )

    def test_get_job_status_not_found(self):
        """Test retrieving job status when job does not exist."""
        from wy_qcos.api.posiq.routes_jsonrpc.errors import NotFoundError

        mock_client = Mock(spec=GetJobStatusRequest)
        mock_client.job_id = uuid4()

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (False, None, None)

        with pytest.raises(NotFoundError):
            get_job_status(mock_client, None, job_repo=mock_job_repo)

    @pytest.mark.smoke
    def test_get_job_results(self):
        """Test retrieving job results by job_id - success case."""
        mock_client = Mock(spec=GetJobResultsRequest)
        mock_client.job_id = self.job_id

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.asdict.return_value = response_info
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )

        result = get_job_results(mock_client, None, job_repo=mock_job_repo)
        assert str(result.job_id) == str(response_info["job_id"])
        assert result.job_status == response_info["job_status"]
        mock_job_repo.get_job_by_uuid.assert_called_once_with(
            self.job_id, filters={}
        )

    def test_get_job_results_with_results(self):
        """Test retrieving job results when results are available."""
        mock_client = Mock(spec=GetJobResultsRequest)
        mock_client.job_id = self.job_id

        results_data = response_info.copy()
        results_data["results"] = [
            {
                "results": {"00": 100, "01": 50},
                "metadata": {
                    "status": Constant.JOB_STATUS_COMPLETED,
                    "ended_at": datetime.now().isoformat(),
                },
            }
        ]

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.asdict.return_value = results_data
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )

        result = get_job_results(mock_client, None, job_repo=mock_job_repo)
        assert result.results is not None
        assert len(result.results) == 1

    def test_get_job_results_not_found(self):
        """Test retrieving job results when job does not exist."""
        from wy_qcos.api.posiq.routes_jsonrpc.errors import NotFoundError

        mock_client = Mock(spec=GetJobResultsRequest)
        mock_client.job_id = uuid4()

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (False, None, None)

        with pytest.raises(NotFoundError):
            get_job_results(mock_client, None, job_repo=mock_job_repo)

    def test_get_jobs(self):
        """Test retrieving all jobs - successful case."""
        mock_job_repo = Mock()
        job_record_mock = Mock()
        # Include 'id' field since get_jobs expects it
        response_with_id = response_info.copy()
        response_with_id["id"] = response_info["job_id"]
        job_record_mock.created_at = response_info["created_at"]
        job_record_mock.asdict.return_value = response_with_id
        mock_job_repo.get_jobs.return_value = (
            True,
            None,
            [job_record_mock],
        )

        auth_data = {"user_id": "test-user", "roles": ["user"]}
        result = get_jobs(None, None, auth_data, job_repo=mock_job_repo)
        assert len(result) > 0
        assert str(result[0].job_id) == str(response_info["job_id"])
        mock_job_repo.get_jobs.assert_called_once()

    def test_get_jobs_empty(self):
        """Test retrieving jobs when no jobs exist."""
        mock_job_repo = Mock()
        mock_job_repo.get_jobs.return_value = (True, None, None)

        auth_data = {"user_id": "test-user", "roles": ["user"]}
        result = get_jobs(None, None, auth_data, job_repo=mock_job_repo)
        assert result == []

    def test_get_jobs_multiple(self):
        """Test retrieving multiple jobs with sorting."""
        mock_job_repo = Mock()

        # Create multiple job records with different timestamps
        job_records = []
        datetime(2026, 5, 22, 10, 0, 0)

        for i in range(3):
            job_record = Mock()
            job_record.created_at = datetime(
                2026,
                5,
                22,
                10,
                i,
                0,  # Incrementing times
            )
            response_data = response_info.copy()
            response_data["id"] = uuid4()
            response_data["created_at"] = job_record.created_at
            job_record.asdict.return_value = response_data
            job_records.append(job_record)

        mock_job_repo.get_jobs.return_value = (True, None, job_records)

        auth_data = {"user_id": "test-user", "roles": ["user"]}
        result = get_jobs(None, None, auth_data, job_repo=mock_job_repo)
        assert len(result) == 3
        # Verify sorting - should be descending (newest first)
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at

    @patch.object(TaskScheduler, "cancel_flows")
    def test_cancel_jobs(self, mock_cancel_flows):
        """Test cancelling jobs - successful case."""
        job_id_to_use = self.job_ids[0]
        # cancel_flows now returns a dict keyed by flow_run_id
        mock_cancel_flows.return_value = {
            "flow-run-123": {
                "state": Constant.PREFECT_STATE_CANCELLING,
            },
        }
        mock_client = Mock(spec=CancelJobsRequest)
        mock_client.job_ids = [job_id_to_use]

        mock_job_repo = Mock()
        job_record = Mock()
        job_record.id = job_id_to_use
        job_record.flow_run_id = "flow-run-123"

        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record,
        )

        result = cancel_jobs(mock_client, None, job_repo=mock_job_repo)

        assert len(result) == 1
        # Compare using str() because UUIDs can be different types
        assert str(result[0].job_id) == str(job_id_to_use)
        mock_cancel_flows.assert_called_once()

    @patch.object(TaskScheduler, "cancel_flows")
    def test_cancel_jobs_with_duplicates(self, mock_cancel_flows):
        """Test cancelling jobs with duplicate job_ids."""
        duplicate_ids = [self.job_ids[0], self.job_ids[0], self.job_ids[1]]

        # cancel_flows now returns a dict keyed by flow_run_id
        mock_cancel_flows.return_value = {
            "flow-run-123": {
                "state": Constant.PREFECT_STATE_CANCELLING,
            },
            "flow-run-456": {
                "state": Constant.PREFECT_STATE_CANCELLING,
            },
        }

        mock_client = Mock(spec=CancelJobsRequest)
        mock_client.job_ids = duplicate_ids

        mock_job_repo = Mock()

        # Mock to return different flow_run_ids for different job_ids
        def get_job_side_effect(job_id, filters=None):
            if job_id == self.job_ids[0]:
                return True, None, Mock(id=job_id, flow_run_id="flow-run-123")
            elif job_id == self.job_ids[1]:
                return True, None, Mock(id=job_id, flow_run_id="flow-run-456")
            return False, None, None

        mock_job_repo.get_job_by_uuid.side_effect = get_job_side_effect

        result = cancel_jobs(mock_client, None, job_repo=mock_job_repo)

        # Should have unique job_ids only
        assert len(result) == 2

    @patch.object(TaskScheduler, "delete_flows")
    def test_delete_jobs(self, mock_delete_flows):
        """Test deleting jobs - successful case."""
        # delete_flows now returns a dict keyed by flow_run_id
        mock_delete_flows.return_value = {
            "flow-run-123": {
                "state": Constant.JOB_STATUS_DELETED,
            },
        }
        mock_client = Mock(spec=DeleteJobsRequest)
        # use a single job_id so the result count is deterministic
        mock_client.job_ids = [self.job_ids[0]]
        mock_client.force = False

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.id = self.job_ids[0]
        job_record_mock.flow_run_id = "flow-run-123"
        job_record_mock.job_status = Constant.JOB_STATUS_QUEUED

        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None
        mock_job_repo.delete_by_uuid.return_value = (True, None)

        result = delete_jobs(mock_client, None, job_repo=mock_job_repo)

        assert len(result) == 1
        assert result[0].job_status == Constant.JOB_STATUS_DELETED
        mock_delete_flows.assert_called_once()

    @patch.object(TaskScheduler, "delete_flows")
    def test_delete_jobs_force_delete(self, mock_delete_flows):
        """Test force deleting jobs - when scheduler returns empty."""
        # delete_flows now returns a dict keyed by flow_run_id; force
        # delete a RUNNING job by having the scheduler report it as
        # DELETED so the db delete path is exercised.
        mock_delete_flows.return_value = {
            "flow-run-123": {"state": Constant.JOB_STATUS_DELETED}
        }

        mock_client = Mock(spec=DeleteJobsRequest)
        mock_client.job_ids = [self.job_ids[0]]
        mock_client.force = True

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.id = self.job_ids[0]
        job_record_mock.flow_run_id = "flow-run-123"
        job_record_mock.job_status = Constant.JOB_STATUS_RUNNING

        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None
        mock_job_repo.delete_by_uuid.return_value = (True, None)

        result = delete_jobs(mock_client, None, job_repo=mock_job_repo)

        assert len(result) == 1
        assert result[0].job_status == Constant.JOB_STATUS_DELETED
        # Verify deletion was called even though scheduler returned empty
        mock_job_repo.delete_by_uuid.assert_called_once()

    @patch.object(Library, "job_callback")
    @patch.object(Library, "get_nested_dict_value")
    @patch.object(Library, "validate_schema")
    def test_set_job_results_success(
        self,
        mock_validate_schema,
        mock_get_nested_dict_value,
        mock_job_callback,
    ):
        """Test set_job_results with successful completion."""
        mock_validate_schema.return_value = (True, None)
        mock_job_callback.return_value = True
        mock_get_nested_dict_value.return_value = ""

        mock_client = Mock(spec=SetJobResultsRequest)
        mock_client.job_id = self.job_id
        # Set results as list of dicts (not dict of dicts)
        mock_client.results = [{"00": 100, "01": 50}]

        # Create mock job_record with proper attributes
        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.job_status = Constant.JOB_STATUS_RUNNING
        job_record_mock.source_code = ["OPENQASM 2.0;"]
        job_record_mock.results = None
        job_record_mock.backend = "dummy"
        job_record_mock.callbacks = [{"url": "http://example.com"}]

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None

        # Execute
        response = set_job_results(mock_client, None, job_repo=mock_job_repo)

        # Assertions
        assert response is not None
        assert str(response.job_id) == str(self.job_id)
        assert response.job_status == Constant.JOB_STATUS_COMPLETED
        assert response.backend == "dummy"

        # Verify job_repo methods were called
        mock_job_repo.get_job_by_uuid.assert_called_once()
        mock_job_repo.commit.assert_called_once()
        mock_job_repo.refresh.assert_called_once()

        # Verify callbacks were triggered
        mock_job_callback.assert_called_once()

    @patch.object(Library, "job_callback")
    @patch.object(Library, "get_nested_dict_value")
    @patch.object(Library, "validate_schema")
    def test_set_job_results_with_errors(
        self,
        mock_validate_schema,
        mock_get_nested_dict_value,
        mock_job_callback,
    ):
        """Test set_job_results with error responses."""
        mock_validate_schema.return_value = (True, None)
        mock_job_callback.return_value = True
        mock_get_nested_dict_value.return_value = ""

        mock_client = Mock(spec=SetJobResultsRequest)
        mock_client.job_id = self.job_id
        # Results with error code
        mock_client.results = [
            {
                "code": 400,
                "message": "Invalid circuit",
                "details": "Qubit count exceeds limit",
            }
        ]

        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.job_status = Constant.JOB_STATUS_RUNNING
        job_record_mock.source_code = ["OPENQASM 2.0;"]
        job_record_mock.results = None
        job_record_mock.backend = "dummy"
        job_record_mock.callbacks = []

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None

        # Execute
        response = set_job_results(mock_client, None, job_repo=mock_job_repo)

        # Assertions - job should be marked as FAILED
        assert response.job_status == Constant.JOB_STATUS_FAILED
        mock_job_repo.commit.assert_called_once()

    @patch.object(Library, "job_callback")
    @patch.object(Library, "get_nested_dict_value")
    @patch.object(Library, "validate_schema")
    def test_set_job_results_multiple_source_codes(
        self,
        mock_validate_schema,
        mock_get_nested_dict_value,
        mock_job_callback,
    ):
        """Test set_job_results with multiple source codes."""
        mock_validate_schema.return_value = (True, None)
        mock_job_callback.return_value = True
        mock_get_nested_dict_value.return_value = ""

        mock_client = Mock(spec=SetJobResultsRequest)
        mock_client.job_id = self.job_id
        # Multiple results for multiple source codes
        mock_client.results = [
            {"00": 100, "01": 50},
            {"10": 75, "11": 25},
            {"0": 150},
        ]

        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.job_status = Constant.JOB_STATUS_RUNNING
        job_record_mock.source_code = [
            "OPENQASM 2.0; h q[0]; measure q->c;",
            "OPENQASM 2.0; x q[0]; measure q->c;",
            "OPENQASM 2.0; measure q->c;",
        ]
        job_record_mock.results = None
        job_record_mock.backend = "dummy"
        job_record_mock.callbacks = []

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None

        # Execute
        response = set_job_results(mock_client, None, job_repo=mock_job_repo)

        # Assertions
        assert response.job_status == Constant.JOB_STATUS_COMPLETED
        # Job record should have been updated with 3 results
        assert job_record_mock.results is not None

    @patch.object(Library, "job_callback")
    @patch.object(Library, "get_nested_dict_value")
    @patch.object(Library, "validate_schema")
    def test_set_job_results_datetime_serialization(
        self,
        mock_validate_schema,
        mock_get_nested_dict_value,
        mock_job_callback,
    ):
        """Test set_job_results handles datetime serialization correctly."""
        mock_validate_schema.return_value = (True, None)
        mock_job_callback.return_value = True
        mock_get_nested_dict_value.return_value = ""

        mock_client = Mock(spec=SetJobResultsRequest)
        mock_client.job_id = self.job_id
        mock_client.results = [{"00": 100}]

        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.job_status = Constant.JOB_STATUS_RUNNING
        job_record_mock.source_code = ["OPENQASM 2.0;"]
        job_record_mock.results = None
        job_record_mock.backend = "dummy"
        job_record_mock.callbacks = []
        # Mock asdict to return datetime object (verifies serialization)
        job_record_mock.asdict.return_value = {
            "id": self.job_id,
            "job_status": Constant.JOB_STATUS_COMPLETED,
            "ended_at": datetime.now(),  # datetime object
            "backend": "dummy",
        }

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None

        # Execute - should not raise TypeError about datetime serialization
        response = set_job_results(mock_client, None, job_repo=mock_job_repo)

        # Assertions
        assert response is not None
        assert response.job_status == Constant.JOB_STATUS_COMPLETED

    @patch.object(TaskScheduler, "update_flow")
    def test_update_job(self, mock_update_flow):
        """Test updating job - successful case."""
        mock_update_flow.return_value = (
            {
                "flow_run_id": "flow-run-456",
                "job_id": uuid4(),
                "job_name": "Updated Job Name",
                "job_type": "",
                "job_status": "",
                "job_priority": 1,
                "code_type": "",
                "source_code": [],
                "description": "Updated Description",
                "backend": "",
                "driver_options": {},
                "transpiler": "",
                "transpiler_options": {},
                "shots": 10,
                "profiling": None,
                "callbacks": None,
                "dry_run": True,
                "created_at": datetime.now(),
                "started_at": None,
                "ended_at": None,
            },
            None,
        )
        mock_client = Mock(spec=UpdateJobRequest)
        mock_client.job_id = self.job_id
        mock_client.job_name = "Updated Job Name"
        mock_client.description = "Updated Description"
        mock_client.job_priority = 1

        mock_job_repo = Mock()
        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.flow_run_id = "flow-run-123"
        job_record_mock.job_status = Constant.JOB_STATUS_QUEUED
        job_record_mock.asdict.return_value = {
            "id": self.job_id,
            "job_name": "Updated Job Name",
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_status": Constant.JOB_STATUS_QUEUED,
            "job_priority": 1,
            "description": "Updated Description",
            "code_type": Constant.CODE_TYPE_QASM,
            "source_code": ["OPENQASM 2.0;"],
            "backend": Constant.DRIVER_DUMMY,
            "driver_options": {},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {},
            "shots": 1000,
            "dry_run": True,
            "created_at": datetime.now(),
            "flow_run_id": "flow-run-123",
        }
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None

        result = update_job(mock_client, None, job_repo=mock_job_repo)

        assert result.job_name == "Updated Job Name"
        assert result.description == "Updated Description"
        assert result.job_priority == 1
        mock_job_repo.commit.assert_called_once()
        mock_job_repo.refresh.assert_called_once()

    @patch.object(TaskScheduler, "update_flow")
    def test_update_job_priority_only(self, mock_update_flow):
        """Test updating only job priority."""
        mock_update_flow.return_value = ({"flow_run_id": "flow-run-456"}, None)

        mock_client = Mock(spec=UpdateJobRequest)
        mock_client.job_id = self.job_id
        mock_client.job_name = None
        mock_client.description = None
        mock_client.job_priority = 5

        job_record_mock = Mock()
        job_record_mock.id = self.job_id
        job_record_mock.flow_run_id = "flow-run-123"
        job_record_mock.job_status = Constant.JOB_STATUS_QUEUED
        job_record_mock.asdict.return_value = {
            "id": self.job_id,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_status": Constant.JOB_STATUS_QUEUED,
            "code_type": Constant.CODE_TYPE_QASM,
            "source_code": ["OPENQASM 2.0;"],
            "backend": "dummy",
            "shots": 1000,
            "dry_run": False,
            "created_at": datetime.now(),
            "job_priority": 5,
        }

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )
        mock_job_repo.commit.return_value = None
        mock_job_repo.refresh.return_value = None

        update_job(mock_client, None, job_repo=mock_job_repo)

        # Should update flow in scheduler
        mock_update_flow.assert_called_once()
        mock_job_repo.commit.assert_called_once()

    @patch.object(TaskScheduler, "update_flow")
    def test_update_job_not_in_queued_state(self, mock_update_flow):
        """Test updating job priority when not in QUEUED state."""
        from wy_qcos.api.posiq.routes_jsonrpc.errors import InternalServerError

        mock_client = Mock(spec=UpdateJobRequest)
        mock_client.job_id = self.job_id
        mock_client.job_name = None
        mock_client.description = None
        mock_client.job_priority = 5

        job_record_mock = Mock()
        job_record_mock.job_status = Constant.JOB_STATUS_RUNNING

        mock_job_repo = Mock()
        mock_job_repo.get_job_by_uuid.return_value = (
            True,
            None,
            job_record_mock,
        )

        with pytest.raises(InternalServerError):
            update_job(mock_client, None, job_repo=mock_job_repo)
