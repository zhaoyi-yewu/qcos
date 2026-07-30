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

import argparse
import json
import io
import os
import sys

from argparse import Namespace
from unittest.mock import patch, Mock

import pytest
from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    SubmitJob,
    GetJobStatus,
    GetJobResults,
    GetJobs,
    CancelJobs,
    DeleteJobs,
    SetJobResults,
    UpdateJob,
    CalibrateDevice,
    GetCalibrateResults,
    SetDeviceOptions,
    GetDeviceOptions,
)
from wy_qcos_client.common.qcos_version import QcosVersion
from wy_qcos_client.common.constant import Constant
from wy_qcos_client.tests.unit_tests.constant_for_test import ConstantForTest

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")
job_id = ConstantForTest.job_id
response = {
    "jsonrpc": "2.0",
    "result": {
        "job_id": "f02aa1a5-900b-44f1-99df-22d8087f5d9f",
        "job_name": None,
        "job_status": "QUEUED",
        "job_priority": 5,
        "description": None,
        "backend": "uqc_matrix2",
        "driver_options": None,
        "transpiler": None,
        "transpiler_options": None,
        "circuit_aggregation": None,
        "shots": 100,
        "dry_run": False,
        "progress": -1,
        "created_at": "2025-11-25T16:02:33.182619",
        "started_at": None,
        "ended_at": None,
    },
    "id": 0,
}
header_list = [
    "name",
    "alias_name",
    "version",
    "tech_type",
    "max_qubits",
    "transpiler",
    "description",
]
jsonrpc_response = json.dumps(response)


shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
submit_job = SubmitJob(shell, None)
get_job_status = GetJobStatus(shell, None)
get_job_results = GetJobResults(shell, None)
get_jobs = GetJobs(shell, None)
cancel_jobs = CancelJobs(shell, None)
delete_jobs = DeleteJobs(shell, None)
set_job_results = SetJobResults(shell, None)
update_job = UpdateJob(shell, None)
calibrate_device = CalibrateDevice(shell, None)
get_calibrate_results = GetCalibrateResults(shell, None)
set_device_options = SetDeviceOptions(shell, None)
get_device_options = GetDeviceOptions(shell, None)


class TestSubmitJob:
    def test_validate_filepath(self):
        with pytest.raises(argparse.ArgumentTypeError) as e:
            submit_job.validate_filepath("")
        assert "Error" in str(e)

    @patch.object(Client, "version")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch("wy_qcos_client.shell.get_content_by_type")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self,
        mock_check_results,
        mock_get_content_by_type,
        mock_handle_invalid_arguments,
        mock_version,
    ):
        mock_version.return_value = -1, None, None, None
        mock_handle_invalid_arguments.return_value = None
        mock_get_content_by_type.return_value = (True, "no", "qcos")
        mock_check_results.return_value = {
            "capabilities": {
                "job_types": ["sample"],
                "profiling": 1,
                "tech_types": "ion_trap",
                "drivers": "DriverUQCMatrix2",
                "transpilers": {"cmss": "cmss"},
                "driver_transpiler_mappings": None,
            },
            "version": "0.0.1",
            "api_version": "0.1.0",
            "supported_api_versions": "0.1.0",
            "platform_version": "1.0.0",
        }
        mock_client = Mock(spec=Namespace)
        mock_client.job_name = "test-job"
        mock_client.dry_run = False
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.job_id = job_id
        mock_client.circuit_aggregation = Constant.AGGREGATION_TYPE_INTERNAL
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_priority = Constant.DEFAULT_JOB_PRIORITY
        mock_client.description = "test description"
        mock_client.shots = Constant.DEFAULT_SHOTS
        mock_client.backend = "dummy"
        mock_client.driver_options = '{"options": "options"}'
        mock_client.transpiler = Constant.TRANSPILER_CMSS
        mock_client.transpiler_options = '{"options": "options"}'
        mock_client.profiling = [Constant.PROFILING_TYPE_CODE]
        mock_client.callbacks = '[{"name":"cb","type":"results","method":"post","url":"http://test"}]'
        mock_client.source_code_files = ["/qcos/test.qasm"]
        mock_client.qec_options = None
        mock_client.flavor = None
        mock_client.extra_specs = None

        assert submit_job.take_action(mock_client) is None

    def test_get_parser(self):
        parser = submit_job.get_parser("")
        assert parser is not None


class TestGetJobStatus:
    def test_get_parser(self):
        parser = get_job_status.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_job_status")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self,
        mock_check_results,
        mock_get_job_status,
        mock_handle_invalid_arguments,
        mock_get_table_data,
    ):
        mock_check_results.return_value = None
        mock_get_job_status.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_get_table_data.return_value = None

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        table_values = get_job_status.take_action(mock_client)
        assert table_values is None


class TestGetJobResults:
    def test_get_parser(self):
        parser = get_job_results.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_job_results")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self,
        mock_check_results,
        mock_get_job_results,
        mock_handle_invalid_arguments,
        mock_get_table_data,
    ):
        mock_check_results.return_value = response
        mock_get_job_results.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_get_table_data.return_value = (
            ("ID", "Name", "Status", "CreateTime"),
            ("job-001", "test-job", "running", "2026-05-29 10:00:00"),
        )

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        mock_client.output_file = None
        mock_client.assume_override = False
        table_values = get_job_results.take_action(mock_client)
        assert table_values != ((), ())

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_job_results")
    @patch.object(CommandHelper, "check_results")
    def test_take_action_save_txt_file_succ_1(
        self,
        mock_check_results,
        mock_get_job_results,
        mock_handle_invalid_arguments,
        mock_get_table_data,
    ):
        mock_check_results.return_value = response
        mock_get_job_results.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_get_table_data.return_value = (
            ("ID", "Name", "Status", "CreateTime"),
            ("job-001", "test-job", "running", "2026-05-29 10:00:00"),
        )

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        mock_client.output_file = "result.txt"
        mock_client.assume_override = True
        mock_client.max_width = 16
        mock_client.fit_width = False
        mock_client.formatter = "table"

        table_values = get_job_results.take_action(mock_client)
        assert table_values == ((), ())
        assert os.path.exists("result.txt") is True
        os.remove("result.txt")

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_job_results")
    @patch.object(CommandHelper, "check_results")
    def test_take_action_save_txt_file_succ_2(
        self,
        mock_check_results,
        mock_get_job_results,
        mock_handle_invalid_arguments,
        mock_get_table_data,
    ):
        mock_check_results.return_value = response
        mock_get_job_results.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_get_table_data.return_value = (
            ("ID", "Name", "Status", "CreateTime"),
            ("job-001", "test-job", "running", "2026-05-29 10:00:00"),
        )

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        mock_client.output_file = "result.doc"
        mock_client.assume_override = True
        mock_client.max_width = 16
        mock_client.fit_width = False
        mock_client.formatter = "table"

        table_values = get_job_results.take_action(mock_client)
        assert table_values == ((), ())
        assert os.path.exists("result.doc") is True
        os.remove("result.doc")

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_job_results")
    @patch.object(CommandHelper, "check_results")
    def test_take_action_save_txt_file_succ_3(
        self,
        mock_check_results,
        mock_get_job_results,
        mock_handle_invalid_arguments,
        mock_get_table_data,
    ):
        mock_check_results.return_value = response
        mock_get_job_results.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_get_table_data.return_value = (
            ("ID", "Name", "Status", "CreateTime"),
            ("job-001", "test-job", "running", "2026-05-29 10:00:00"),
        )

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        mock_client.output_file = "./result/result.doc"
        mock_client.assume_override = True
        mock_client.max_width = 16
        mock_client.fit_width = False
        mock_client.formatter = "table"

        table_values = get_job_results.take_action(mock_client)
        assert table_values == ((), ())
        assert os.path.exists("./result/result.doc") is True
        os.remove("./result/result.doc")

    @patch("builtins.input")
    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_job_results")
    @patch.object(CommandHelper, "check_results")
    def test_take_action_save_txt_file_fail(
        self,
        mock_check_results,
        mock_get_job_results,
        mock_handle_invalid_arguments,
        mock_get_table_data,
        mock_input,
    ):
        mock_check_results.return_value = response
        mock_get_job_results.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_get_table_data.return_value = (
            ("ID", "Name", "Status", "CreateTime"),
            ("job-001", "test-job", "running", "2026-05-29 10:00:00"),
        )

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        mock_client.output_file = "result.txt"
        mock_client.assume_override = True
        mock_client.max_width = 16
        mock_client.fit_width = False
        mock_client.formatter = "table"

        table_values = get_job_results.take_action(mock_client)
        assert table_values == ((), ())
        assert os.path.exists("result.txt") is True

        captured_stdout = io.StringIO()
        sys.stdout = captured_stdout
        mock_client.assume_override = False
        mock_get_job_results.return_value = iter([None, None, None, None])
        mock_input.return_value = "n"
        table_values = get_job_results.take_action(mock_client)
        output = captured_stdout.getvalue().strip()
        assert table_values == ((), ())
        assert os.path.exists("result.txt") is True
        assert "File exists and do not override it, abort saving" in output
        os.remove("result.txt")


class TestGetJobs:
    def test_get_parser(self):
        parser = get_jobs.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(Client, "get_jobs")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self, mock_check_results, mock_get_jobs, mock_get_table_data
    ):
        mock_get_jobs.return_value = iter([None, None, None, None])
        mock_get_table_data.return_value = None
        mock_check_results.return_value = None
        mock_client = Mock(spec=Namespace)
        mock_client.project_id = None
        mock_client.user_id = None
        mock_client.job_ids = None
        mock_client.all_projects = False
        mock_client.all_users = False
        table_values = get_jobs.take_action(mock_client)
        assert table_values is None


class TestCancelJobs:
    def test_get_parser(self):
        parser = cancel_jobs.get_parser("")
        assert parser is not None

    @patch.object(Client, "cancel_jobs")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_jobs")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self,
        mock_check_results,
        mock_get_jobs,
        mock_handle_invalid_arguments,
        mock_cancel_jobs,
    ):
        mock_check_results.return_value = [response["result"]]
        mock_get_jobs.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_cancel_jobs.return_value = (None, None, None, None)

        mock_client = Mock(spec=Namespace)
        mock_client.job_ids = "ALL"
        mock_client.assume_yes = "DMA"
        cancel_jobs.take_action(mock_client)

        mock_client.job_ids = "NO"
        assert cancel_jobs.take_action(mock_client) is None


class TestDeleteJobs:
    def test_get_parser(self):
        parser = delete_jobs.get_parser("")
        assert parser is not None

    @patch.object(Client, "delete_jobs")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "get_jobs")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self,
        mock_check_results,
        mock_get_jobs,
        mock_handle_invalid_arguments,
        mock_delete_jobs,
    ):
        mock_check_results.return_value = [response["result"]]
        mock_get_jobs.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_delete_jobs.return_value = (None, None, None, None)

        mock_client = Mock(spec=Namespace)
        mock_client.job_ids = "all"
        mock_client.assume_yes = "DMA"
        mock_client.force = False
        delete_jobs.take_action(mock_client)

        mock_client.job_ids = "NO"
        mock_check_results.return_value = [response["result"]]
        assert delete_jobs.take_action(mock_client) is None


class TestSetJobResults:
    def test_get_parser(self):
        parser = set_job_results.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(Client, "set_job_results")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self,
        mock_check_results,
        mock_set_job_results,
        mock_handle_invalid_arguments,
    ):
        mock_check_results.return_value = None
        mock_set_job_results.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        mock_client.results = [
            '{"options": "options"}',
        ]
        assert set_job_results.take_action(mock_client) is None


class TestUpdateJob:
    def test_get_parser(self):
        parser = update_job.get_parser("")
        assert parser is not None

    @patch.object(Client, "update_job")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self,
        mock_check_results,
        mock_handle_invalid_arguments,
        mock_update_job,
    ):
        mock_handle_invalid_arguments.return_value = None
        mock_check_results.return_value = response["result"]
        mock_update_job.return_value = iter([None, None, None, None])
        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        mock_client.job_priority = Constant.DEFAULT_JOB_PRIORITY
        mock_client.job_name = None
        mock_client.description = None

        assert update_job.take_action(mock_client) is None


class TestCalibrateDevice:
    def test_get_parser(self):
        parser = calibrate_device.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "calibrate_device")
    def test_take_action(self, mock_calibrate_device, mock_check_results):
        mock_client = Mock(spec=Namespace)
        mock_client.device_name = "device"
        mock_client.options = '{"options": "value"}'
        mock_calibrate_device.return_value = iter([None, None, None, None])
        mock_check_results.return_value = None

        assert calibrate_device.take_action(mock_client) is None


class TestGetCalibrateResults:
    def test_get_parser(self):
        parser = get_calibrate_results.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_calibrate_results")
    def test_take_action(self, mock_get_calibrate_results, mock_check_results):
        mock_client = Mock(spec=Namespace)
        mock_client.device_name = "device"
        mock_get_calibrate_results.return_value = iter([
            None,
            None,
            None,
            None,
        ])
        mock_check_results.return_value = None

        assert get_calibrate_results.take_action(mock_client) is None


class TestSetDeviceOptions:
    def test_get_parser(self):
        parser = set_device_options.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "set_device_options")
    def test_take_action(self, mock_set_device_options, mock_check_results):
        mock_client = Mock(spec=Namespace)
        mock_client.device_name = "device"
        mock_client.options = '{"options": "value"}'
        mock_set_device_options.return_value = iter([None, None, None, None])
        mock_check_results.return_value = None

        assert set_device_options.take_action(mock_client) is None


class TestGetDeviceOptions:
    def test_get_parser(self):
        parser = get_device_options.get_parser("")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_options")
    def test_take_action(self, mock_get_device_options, mock_check_results):
        mock_client = Mock(spec=Namespace)
        mock_client.device_name = "device"
        mock_get_device_options.return_value = iter([None, None, None, None])
        mock_check_results.return_value = None

        assert get_device_options.take_action(mock_client) is None
