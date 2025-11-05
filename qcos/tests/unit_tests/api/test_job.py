#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from qcos.api.posiq.routes_jsonrpc.errors import BadRequestError
from qcos.api.posiq.routes_jsonrpc.job import (
    submit_job,
    get_job_status,
    get_job_results,
    get_jobs,
    cancel_jobs,
    delete_jobs,
    set_job_results,
    update_job,
)
from qcos.api.schemas import (
    SubmitJobResponse,
    GetJobStatusRequest,
    GetJobResultsRequest,
    CancelJobsRequest,
    DeleteJobsRequest,
    SetJobResultsRequest,
    UpdateJobRequest,
)
from qcos.client.client import Client
from qcos.common.config import Config
from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.device import Device
from qcos.drivers.device_manager import DeviceManager
from qcos.drivers.driver_manager import DriverManager
from qcos.drivers.dummy.driver_dummy import DriverDummy
from qcos.task_manager import TaskScheduler
from qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)
from qcos.transpiler.transpiler_base import TranspilerBase
from qcos.transpiler.transpiler_manager import TranspilerManager

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
    "creation_date": datetime.now(),
    "end_date": None,
}
job_ids = [uuid4(), uuid4(), uuid4()]


class TestJob:
    @classmethod
    def setup_class(cls):
        cls.job_id = ConstantForTest.job_id
        cls.job_ids = ConstantForTest.job_ids

    @patch.object(Library, "validate_schema")
    @patch.object(TaskScheduler, "add")
    @patch.object(TranspilerManager, "get_transpiler")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    @patch.object(Client, "get_driver")
    @patch.object(Library, "validate_values_enum")
    @patch.object(DeviceManager, "get_devices")
    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(Client, "get_drivers")
    @patch.object(TaskScheduler, "get_driver_manager")
    def test_submit_job(
        self,
        mock_get_driver_manager,
        mock_get_drivers,
        mock_get_device_manager,
        mock_get_devices,
        mock_validate_values_enum,
        mock_get_driver,
        mock_get_transpiler_manager,
        mock_get_transpiler,
        mock_add,
        mock_validate_schema,
    ):
        mock_client = Mock(spec=SubmitJobResponse)
        mock_client.source_code = [
            """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """
        ]
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.circuit_aggregation = Constant.AGGREGATION_TYPE_INTERNAL
        mock_client.job_id = None
        mock_client.job_name = Constant.AGGREGATION_TYPE_NONE
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_sched_policy = Constant.DEFAULT_JOB_SCHED_POLICY
        mock_client.job_priority = Constant.DEFAULT_JOB_PRIORITY
        mock_client.description = Constant.AGGREGATION_TYPE_NONE
        mock_client.shots = Constant.DEFAULT_SHOTS
        mock_client.backend = Constant.DRIVER_DUMMY
        mock_client.driver_options = {
            "driver_options": "options",
        }
        mock_client.transpiler = Constant.TRANSPILER_CMSS
        mock_client.transpiler_options = {
            "transpiler_options": "options",
        }
        mock_client.profiling = ["1", "2"]
        mock_client.callbacks = [
            "callbacks",
        ]
        mock_client.dry_run = True

        mock_validate_schema.return_value = (True, None)
        mock_add.return_value = [{"job_id": self.job_id}, None]
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
        mock_get_devices.return_value = {mock_client.backend: device}
        submit_job(mock_client, None)

        mock_client.source_code = None
        with pytest.raises(BadRequestError) as e:
            submit_job(mock_client, None)
        assert "BadRequestError" in str(e)

        mock_client.source_code = [
            """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """
        ]
        mock_client.job_id = "111"
        with pytest.raises(BadRequestError) as e:
            submit_job(mock_client, None)
        assert "BadRequestError" in str(e)

    @patch("qcos.api.posiq.routes_jsonrpc.job.merge_results")
    @patch.object(TaskScheduler, "get_result_by_id")
    def test_get_job_status(self, mock_get_result_by_id, mock_merge_results):
        mock_get_result_by_id.return_value = iter([
            {"artifact": {"progress": -1}},
            "err_msg",
        ])
        mock_client = Mock(spec=GetJobStatusRequest)
        mock_client.job_id = None
        mock_merge_results.return_value = response_info
        get_job_status(mock_client)

    @patch("qcos.api.posiq.routes_jsonrpc.job.merge_results")
    @patch.object(TaskScheduler, "get_result_by_id")
    @patch.object(TaskScheduler, "has_job")
    def test_get_job_results(
        self, mock_has_job, mock_get_result_by_id, mock_merge_results
    ):
        mock_has_job.return_value = True
        mock_merge_results.return_value = response_info
        mock_get_result_by_id.return_value = iter([
            {"artifact": {"progress": -1}},
            "err_msg",
        ])
        mock_client = Mock(spec=GetJobResultsRequest)
        mock_client.job_id = None
        get_job_results(mock_client)

    @patch("qcos.api.posiq.routes_jsonrpc.job.merge_results")
    @patch.object(TaskScheduler, "get_jobs")
    def test_get_jobs(self, mock_get_jobs, mock_merge_results):
        mock_get_jobs.return_value = iter([
            [
                {
                    "job_status": Constant.JOB_STATUS_UNKNOWN,
                    "id": self.job_id,
                    "progress": -1,
                }
            ],
            None,
        ])
        mock_merge_results.return_value = response_info
        mock_client = Mock(spec=GetJobResultsRequest)
        mock_client.job_id = None
        get_jobs(mock_client, None)

    @patch.object(TaskScheduler, "cancel_jobs")
    def test_cancel_jobs(self, mock_cancel_jobs):
        mock_cancel_jobs.return_value = [
            {"state": Constant.PREFECT_STATE_CANCELLING, "id": uuid4()},
        ]
        mock_client = Mock(spec=CancelJobsRequest)
        mock_client.job_ids = self.job_ids
        cancel_jobs(mock_client, None)

    @patch.object(TaskScheduler, "delete_jobs")
    def test_delete_jobs(self, mock_delete_jobs):
        mock_delete_jobs.return_value = [
            {"state": Constant.PREFECT_STATE_CANCELLING, "id": uuid4()},
        ]
        mock_client = Mock(spec=DeleteJobsRequest)
        mock_client.job_ids = self.job_ids
        delete_jobs(mock_client, None)

    @patch.object(Library, "get_nested_dict_value")
    @patch.object(TaskScheduler, "run_callbacks")
    @patch.object(TaskScheduler, "update_job")
    @patch.object(TaskScheduler, "get_result_by_id")
    @patch.object(Library, "validate_schema")
    def test_set_job_results(
        self,
        mock_validate_schema,
        mock_get_result_by_id,
        mock_update_job,
        mock_run_callbacks,
        mock_get_nested_dict_value,
    ):
        mock_get_nested_dict_value.return_value = ""
        mock_run_callbacks.return_value = iter([True, None])
        mock_update_job.return_value = iter([True, None])
        mock_get_result_by_id.return_value = iter([
            {
                "job_status": Constant.JOB_STATUS_RUNNING,
                "parameters": [],
                "results": [
                    {
                        "metadata": {
                            "status": Constant.JOB_STATUS_COMPLETED,
                            "end_date": "never",
                        }
                    },
                ],
            },
            "err_msg",
        ])
        mock_validate_schema.return_value = (True, None)

        mock_client = Mock(spec=SetJobResultsRequest)
        mock_client.job_id = self.job_id
        mock_client.results = {0: {"a": "a"}}
        set_job_results(mock_client)

    @patch.object(TaskScheduler, "update_job")
    @patch.object(TaskScheduler, "get_result_by_id")
    def test_update_job(self, mock_get_result_by_id, mock_update_job):
        mock_get_result_by_id.return_value = (
            {
                "job_status": "QUEUED",
                "parameters": {},
                "results": None,
                "artifact": {"progress": -1},
                "error_message": None,
            },
            None,
        )
        mock_update_job.return_value = (
            {
                "job_id": uuid4(),
                "job_name": "",
                "job_type": "",
                "job_status": "",
                "job_priority": 1,
                "code_type": "",
                "source_code": [],
                "description": "",
                "backend": "",
                "driver_options": {},
                "transpiler": "",
                "transpiler_options": {},
                "shots": 10,
                "profiling": None,
                "callbacks": None,
                "dry_run": True,
                "creation_date": datetime.now(),
                "end_date": None,
            },
            None,
        )
        mock_client = Mock(spec=UpdateJobRequest)
        mock_client.job_id = self.job_id
        mock_client.job_priority = 1
        update_job(mock_client)
