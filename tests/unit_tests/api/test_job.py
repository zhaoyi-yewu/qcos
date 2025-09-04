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

from unittest.mock import Mock, patch

import pytest

from qcos.api.posiq.routes_jsonrpc.errors import BadRequestError
from qcos.api.posiq.routes_jsonrpc.job import (submit_job,
                                               get_job_status,
                                               get_job_results)
from qcos.api.schemas import (SubmitJobResponse, GetJobResultsRequest,
                              GetJobStatusRequest)
from qcos.client.client import Client
from qcos.common.config import Config
from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.device import Device
from qcos.drivers.device_manager import DeviceManager
from qcos.drivers.driver_manager import DriverManager
from qcos.drivers.dummy.driver_dummy import DriverDummy
from qcos.task_manager import TaskScheduler
from qcos.transpiler.transpiler_base import TranspilerBase
from qcos.transpiler.transpiler_manager import TranspilerManager


class TestJob:
    @patch.object(TaskScheduler, 'add')
    @patch.object(TranspilerManager, 'get_transpiler')
    @patch.object(TaskScheduler, 'get_transpiler_manager')
    @patch.object(Client, 'get_driver')
    @patch.object(Library, 'validate_values_enum')
    @patch.object(DeviceManager, 'get_devices')
    @patch.object(TaskScheduler, 'get_device_manager')
    @patch.object(Client, 'get_drivers')
    @patch.object(TaskScheduler, 'get_driver_manager')
    def test_submit_job(self, mock_get_driver_manager, mock_get_drivers,
                        mock_get_device_manager, mock_get_devices,
                        mock_validate_values_enum, mock_get_driver,
                        mock_get_transpiler_manager, mock_get_transpiler,
                        mock_add):
        mock_client = Mock(spec=SubmitJobResponse)
        mock_client.source_code = ['''
          OPENQASM 2.0;
          include "qelib1.inc";
          qreg q[1];
          creg c[1];
          h q[0];
          h q[0];
          x q[0];
          rx(1) q[0];
          measure q->c;
        ''']
        mock_client.code_type = Constant.CODE_TYPE_QASM
        mock_client.circuit_aggregation = None
        mock_client.job_id = None
        mock_client.job_name = None
        mock_client.job_type = Constant.JOB_TYPE_SAMPLING
        mock_client.job_sched_policy = Constant.DEFAULT_JOB_SCHED_POLICY
        mock_client.job_priority = Constant.DEFAULT_JOB_PRIORITY
        mock_client.description = None
        mock_client.shots = Constant.DEFAULT_SHOTS
        mock_client.backend = Constant.DRIVER_DUMMY
        mock_client.driver_options = None
        mock_client.transpiler = Constant.TRANSPILER_CMSS
        mock_client.transpiler_options = None
        mock_client.profiling = []
        mock_client.callbacks = None
        mock_client.dry_run = None

        mock_add.return_value = iter([{"job_id": "1234"}, None])
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpiler.return_value = TranspilerBase()
        mock_get_driver.return_value = DriverDummy()
        mock_validate_values_enum.return_value = (True, None)
        mock_get_driver_manager.return_value = DriverManager()
        mock_get_drivers.return_value = {}
        mock_get_device_manager.return_value = DeviceManager(Config(),
                                                             DriverManager())
        device = Device("dummy", DriverDummy())
        device.set_enable(True)
        device.set_status("online")
        mock_get_devices.return_value = {mock_client.backend: device}

        submit_job(mock_client)

    @patch.object(TaskScheduler, 'get_result_by_id')
    def test_get_job_status(self, mock_get_result_by_id):
        mock_get_result_by_id.return_value = iter([{"artifact": {
            "progress": -1}}, "err_msg"])
        mock_client = Mock(spec=GetJobStatusRequest)
        mock_client.job_id = None
        get_job_status(mock_client)

    @patch.object(TaskScheduler, 'get_result_by_id')
    @patch.object(TaskScheduler, 'has_job')
    def test_get_job_results(self, mock_has_job, mock_get_result_by_id):
        mock_has_job.return_value = True
        mock_get_result_by_id.return_value = iter([{"artifact": {
            "progress": -1}}, "err_msg"])
        mock_client = Mock(spec=GetJobResultsRequest)
        mock_client.job_id = None
        get_job_results(mock_client)
