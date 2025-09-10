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
from unittest.mock import patch

import pytest
from cliff.app import App
from cliff.commandmanager import CommandManager
from jsonrpcclient import Ok

from qcos.client.client import Client
from qcos.client.shell import (QcosShell, CommandHelper, Version, GetDrivers,
                               GetDevices, GetDevice, GetTranspilers,
                               GetTranspiler, Ping, SubmitJob, GetJobStatus,
                               GetJobResults, GetJobs, CancelJobs, DeleteJobs,
                               SetJobResults, set_debug_option,
                               get_content_by_type)
from qcos.common.constant import HttpCode

command_manager = CommandManager("qcos")
shell = QcosShell("description", "1.0.0", command_manager)
helper = CommandHelper()
version = Version(App("description", "1.0.0", command_manager), None)
get_drivers = GetDrivers(App("description", "1.0.0", command_manager), None)
get_devices = GetDevices(App("description", "1.0.0", command_manager), None)
get_device = GetDevice(App("description", "1.0.0", command_manager), None)
get_transpilers = GetTranspilers(
    App("description", "1.0.0", command_manager), None)
get_transpiler = GetTranspiler(
    App("description", "1.0.0", command_manager), None)
ping = Ping(App("description", "1.0.0", command_manager), None)
submit_job = SubmitJob(App("description", "1.0.0", command_manager), None)
get_job_status = GetJobStatus(
    App("description", "1.0.0", command_manager), None)
get_job_results = GetJobResults(
    App("description", "1.0.0", command_manager), None)
get_jobs = GetJobs(App("description", "1.0.0", command_manager), None)
cancel_jobs = CancelJobs(App("description", "1.0.0", command_manager), None)
delete_jobs = DeleteJobs(App("description", "1.0.0", command_manager), None)
set_job_results = SetJobResults(
    App("description", "1.0.0", command_manager), None)


class TestQcosShell:
    def test_build_option_parser(self):
        shell.build_option_parser("description", "1.0.0")


class TestCommandHelper:
    def test_handle_invalid_arguments(self):
        helper.handle_invalid_arguments("no")

    @patch.object(Client, "parse_jsonrpc_response")
    def test_check_results(self, mock_parse_jsonrpc_response):
        mock_parse_jsonrpc_response.return_value = iter(
            [True, Ok("result", "id")])
        helper.check_results("resource", "Tzeentch", HttpCode.SUCCESS_OK,
                             "reason", '{"name": "Nurgle"}')

    def test_get_table_list_data(self):
        helper.get_table_list_data([{"key": "value"}, {"T": "Tzeentch"}],
                                   ["Tzeentch", "Nurgle",
                                    "Khorne", "Slaanesh", "Emperor"])

    def test_get_table_data(self):
        helper.get_table_data({"key": "value", "T": "Tzeentch"})


class TestVersion:
    def test_get_parser(self):
        version.get_parser("")


class TestGetDrivers:
    def test_get_parser(self):
        get_drivers.get_parser("")


class TestGetDevices:
    def test_get_parser(self):
        get_devices.get_parser("")


class TestGetDevice:
    def test_get_parser(self):
        get_device.get_parser("")


class TestGetTranspilers:
    def test_get_parser(self):
        get_transpilers.get_parser("")


class TestGetTranspiler:
    def test_get_parser(self):
        get_transpiler.get_parser("")


class TestPing:
    def test_get_parser(self):
        ping.get_parser("")


class TestSubmitJob:
    def test_validate_filepath(self):
        with pytest.raises(argparse.ArgumentTypeError) as e:
            submit_job.validate_filepath("")
        assert "Error" in str(e)

    def test_get_parser(self):
        submit_job.get_parser("")


class TestGetJobStatus:
    def test_get_parser(self):
        get_job_status.get_parser("")


class TestGetJobResults:
    def test_get_parser(self):
        get_job_results.get_parser("")


class TestGetJobs:
    def test_get_parser(self):
        get_jobs.get_parser("")


class TestCancelJobs:
    def test_get_parser(self):
        cancel_jobs.get_parser("")


class TestDeleteJobs:
    def test_get_parser(self):
        delete_jobs.get_parser("")


class TestSetJobResults:
    def test_get_parser(self):
        set_job_results.get_parser("")


def test_set_debug_option():
    set_debug_option(None)


def test_get_content_by_type():
    get_content_by_type("no", "")
