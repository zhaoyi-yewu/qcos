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

import argparse
from argparse import Namespace
from unittest.mock import patch, Mock

import pytest
from cliff.commandmanager import CommandManager
from jsonrpcclient import Ok, Error

from qcos.client.client import Client
from qcos.client.shell import (
    QcosShell,
    CommandHelper,
    Version,
    GetDrivers,
    GetDevices,
    GetDevice,
    GetTranspilers,
    GetTranspiler,
    Ping,
    SubmitJob,
    GetJobStatus,
    GetJobResults,
    GetJobs,
    CancelJobs,
    DeleteJobs,
    SetJobResults,
    set_debug_option,
    get_content_by_type,
    GetDriver,
)
from qcos.common import errors
from qcos.common.config import Config
from qcos.common.constant import HttpCode, Constant
from qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)

DESCRIPTION = "QCOS command line interface"
VERSION = Config.VERSION
command_manager = CommandManager("qcos")
job_id = ConstantForTest.job_id

shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()
helper = CommandHelper()
version = Version(shell, None)
get_drivers = GetDrivers(shell, None)
get_driver = GetDriver(shell, None)
get_devices = GetDevices(shell, None)
get_device = GetDevice(shell, None)
get_transpilers = GetTranspilers(shell, None)
get_transpiler = GetTranspiler(shell, None)
ping = Ping(shell, None)
submit_job = SubmitJob(shell, None)
get_job_status = GetJobStatus(shell, None)
get_job_results = GetJobResults(shell, None)
get_jobs = GetJobs(shell, None)
cancel_jobs = CancelJobs(shell, None)
delete_jobs = DeleteJobs(shell, None)
set_job_results = SetJobResults(shell, None)


class TestQcosShell:
    def test_build_option_parser(self):
        shell.build_option_parser("description", "1.0.0")


class TestCommandHelper:
    def test_handle_invalid_arguments(self):
        with pytest.raises(errors.InvalidArguments) as e:
            helper.handle_invalid_arguments([False, "no"])
        assert "no" in str(e)

    @patch.object(Client, "parse_jsonrpc_response")
    def test_check_results(self, mock_parse_jsonrpc_response):
        mock_parse_jsonrpc_response.return_value = iter(
            [True, Ok("result", "id")]
        )
        helper.check_results(
            "resource",
            "Tzeentch",
            HttpCode.SUCCESS_OK,
            "reason",
            '{"name": "Nurgle"}',
        )

        mock_parse_jsonrpc_response.return_value = iter(
            [
                False,
                Error(
                    114,
                    "message",
                    {
                        "errors": [
                            {"msg": "msg1", "loc": "loc1"},
                            {"msg": "msg2", "loc": "loc2"},
                        ],
                        "details": "detail",
                    },
                    "",
                ),
            ]
        )
        with pytest.raises(errors.GenericException) as e:
            helper.check_results(
                "resource",
                "Tzeentch",
                HttpCode.SUCCESS_OK,
                "reason",
                '{"name": "Nurgle"}',
            )
        assert "114" in str(e)

    def test_get_table_list_data(self):
        helper.get_table_list_data(
            [{"key": "value"}, {"T": "Tzeentch"}],
            ["Tzeentch", "Nurgle", "Khorne", "Slaanesh", "Emperor"],
        )

    def test_get_table_data(self):
        helper.get_table_data({"key": "value", "T": "Tzeentch"})

    def test_get_content_by_type(self):
        get_content_by_type(Constant.CODE_TYPE_QASM, "qcos")
        get_content_by_type("0111", "qcos")

    @patch("argparse.ArgumentParser.parse_known_args")
    def test_set_debug_option(self, mock_parse_known_args):
        mock_client = Mock()
        mock_client.debug = True
        mock_parse_known_args.return_value = (mock_client, None)
        set_debug_option("args")


class TestVersion:
    def test_get_parser(self):
        version.get_parser("")

    @patch.object(Client, "version")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(self, mock_check_results, mock_version):
        mock_client = Mock(spec=Namespace)
        mock_version.return_value = -1, None, None, None
        mock_check_results.return_value = {
            "capabilities": {
                "job_types": ["1", "2", "3"],
                "profiling": 1,
                "tech_types": 2,
                "drivers": 3,
                "transpilers": 4,
                "driver_transpiler_mappings": 5,
            },
            "version": 2,
            "api_version": 3,
            "supported_api_versions": 4,
            "platform_version": 5,
        }
        version.take_action(mock_client)


class TestGetDrivers:
    def test_get_parser(self):
        get_drivers.get_parser("")

    @patch.object(Client, "get_drivers")
    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    def test_take_action(
        self, mock_check_results, mock_get_table_list_data, mock_get_drivers
    ):
        mock_get_drivers.return_value = -1, None, None, None
        mock_client = Mock(spec=Namespace)
        mock_get_table_list_data.return_value = None
        mock_check_results.return_value = None
        get_drivers.take_action(mock_client)


class TestGetDriver:
    def test_get_parser(self):
        get_driver.get_parser("")

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_driver")
    def test_take_action(
        self, mock_get_driver, mock_check_results, mock_get_table_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_client.driver_name = "driver"
        mock_get_driver.return_value = iter([None, None, None, None])
        mock_get_table_data.return_value = None
        mock_check_results.return_value = None
        get_driver.take_action(mock_client)


class TestGetDevices:
    def test_get_parser(self):
        get_devices.get_parser("")

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_devices")
    def test_take_action(
        self, mock_get_devices, mock_check_results, mock_get_table_list_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_devices.return_value = iter([None, None, None, None])
        mock_get_table_list_data.return_value = None
        mock_check_results.return_value = None
        get_devices.take_action(mock_client)


class TestGetDevice:
    def test_get_parser(self):
        get_device.get_parser("")

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device")
    def test_take_action(
        self, mock_get_device, mock_check_results, mock_get_table_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_client.device_name = "device"
        mock_get_device.return_value = iter([None, None, None, None])
        mock_get_table_data.return_value = None
        mock_check_results.return_value = None
        get_device.take_action(mock_client)


class TestGetTranspilers:
    def test_get_parser(self):
        get_transpilers.get_parser("")

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_transpilers")
    def test_take_action(
        self,
        mock_get_transpilers,
        mock_check_results,
        mock_get_table_list_data,
    ):
        mock_client = Mock(spec=Namespace)
        mock_get_transpilers.return_value = iter([None, None, None, None])
        mock_get_table_list_data.return_value = None
        mock_check_results.return_value = None
        get_transpilers.take_action(mock_client)


class TestGetTranspiler:
    def test_get_parser(self):
        get_transpiler.get_parser("")

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_transpiler")
    def test_take_action(
        self, mock_get_transpiler, mock_check_results, mock_get_table_data
    ):
        mock_client = Mock(spec=Namespace)
        mock_client.transpiler_name = "transpiler"
        mock_get_transpiler.return_value = iter([None, None, None, None])
        mock_get_table_data.return_value = None
        mock_check_results.return_value = None
        get_transpiler.take_action(mock_client)


class TestPing:
    def test_get_parser(self):
        ping.get_parser("")

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "ping")
    def test_take_action(self, mock_ping, mock_check_results):
        mock_client = Mock(spec=Namespace)
        mock_client.message = "msg"
        mock_ping.return_value = iter([None, None, None, None])
        mock_check_results.return_value = {"message": "msg"}
        ping.take_action(mock_client)


class TestSubmitJob:
    def test_validate_filepath(self):
        with pytest.raises(argparse.ArgumentTypeError) as e:
            submit_job.validate_filepath("")
        assert "Error" in str(e)

    @patch.object(Client, "version")
    @patch.object(CommandHelper, "handle_invalid_arguments")
    @patch("qcos.client.shell.get_content_by_type")
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
                "job_types": ["1", "2", "3"],
                "profiling": 1,
                "tech_types": 2,
                "drivers": 3,
                "transpilers": {"0111": 7},
                "driver_transpiler_mappings": 5,
            },
            "version": 2,
            "api_version": 3,
            "supported_api_versions": 4,
            "platform_version": 5,
        }
        mock_client = Mock(spec=Namespace)
        mock_client.job_name = "name"
        mock_client.dry_run = None
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.job_id = job_id
        mock_client.circuit_aggregation = Constant.AGGREGATION_TYPE_INTERNAL
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_priority = Constant.DEFAULT_JOB_PRIORITY
        mock_client.description = None
        mock_client.shots = Constant.DEFAULT_SHOTS
        mock_client.backend = Constant.DRIVER_DUMMY
        mock_client.driver_options = (
            '{"options": "options", "option": "option"}'
        )
        mock_client.transpiler = Constant.TRANSPILER_CMSS
        mock_client.transpiler_options = (
            '{"options": "options", "option": "option"}'
        )
        mock_client.profiling = ["1", "2"]
        mock_client.callbacks = '{"options": "options", "option": "option"}'
        mock_client.source_code_files = ["qcos", "os"]

        submit_job.take_action(mock_client)

    def test_get_parser(self):
        submit_job.get_parser("")


class TestGetJobStatus:
    def test_get_parser(self):
        get_job_status.get_parser("")

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
        get_job_status.take_action(mock_client)


class TestGetJobResults:
    def test_get_parser(self):
        get_job_results.get_parser("")

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
        mock_check_results.return_value = {
            "results": [{"k1": "v1", "k2": "v2"}, {"k3": "v3"}],
        }
        mock_get_job_results.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_get_table_data.return_value = None

        mock_client = Mock(spec=Namespace)
        mock_client.job_id = job_id
        get_job_results.take_action(mock_client)


class TestGetJobs:
    def test_get_parser(self):
        get_jobs.get_parser("")

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
        get_jobs.take_action(mock_client)


class TestCancelJobs:
    def test_get_parser(self):
        cancel_jobs.get_parser("")

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
        mock_check_results.return_value = [
            {"k1": "v1", "job_id": job_id},
        ]
        mock_get_jobs.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_cancel_jobs.return_value = (None, None, None, None)

        mock_client = Mock(spec=Namespace)
        mock_client.job_ids = "ALL"
        mock_client.assume_yes = "DMA"
        cancel_jobs.take_action(mock_client)

        mock_client.job_ids = "NO"
        cancel_jobs.take_action(mock_client)


class TestDeleteJobs:
    def test_get_parser(self):
        delete_jobs.get_parser("")

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
        mock_check_results.return_value = [
            {"k1": "v1", "job_id": job_id},
        ]
        mock_get_jobs.return_value = iter([None, None, None, None])
        mock_handle_invalid_arguments.return_value = None
        mock_delete_jobs.return_value = (None, None, None, None)

        mock_client = Mock(spec=Namespace)
        mock_client.job_ids = "all"
        mock_client.assume_yes = "DMA"
        delete_jobs.take_action(mock_client)

        mock_client.job_ids = "NO"
        mock_check_results.return_value = [
            {"k1": "v1", "job_id": job_id},
        ]
        delete_jobs.take_action(mock_client)


class TestSetJobResults:
    def test_get_parser(self):
        set_job_results.get_parser("")

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
            '{"options": "options","option": "option"}',
            '{"options": "options","option": "option"}',
        ]
        set_job_results.take_action(mock_client)


def test_set_debug_option():
    assert set_debug_option(None) is None


def test_get_content_by_type():
    success, _, _ = get_content_by_type("no", "")
    assert success is False
