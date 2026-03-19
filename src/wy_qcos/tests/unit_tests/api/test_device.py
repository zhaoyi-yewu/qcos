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

from unittest.mock import Mock, patch

from wy_qcos.api.posiq.routes_jsonrpc.device import (
    calibrate,
    get_calibrate_results,
    get_device,
    get_devices,
    set_device_options,
    get_device_options,
)
from wy_qcos.api.schemas import (
    GetDeviceRequest,
    CalibrateDeviceRequest,
    GetCalibrateResultRequest,
    SetDeviceOptionsRequest,
    GetDeviceOptionsRequest,
)
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.device_manager import DeviceManager
from wy_qcos.drivers.driver_manager import DriverManager
from wy_qcos.drivers.dummy.driver_dummy import DriverDummy
from wy_qcos.task_manager import TaskScheduler


class TestDevice:
    @classmethod
    def setup_class(cls):
        cls.dummy = Constant.TRANSPILER_DUMMY

    @pytest.mark.smoke
    @patch.object(DeviceManager, "get_devices")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_get_devices(self, mock_get_device_manager, mock_get_devices):
        mock_get_devices.return_value = {}
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=GetDeviceRequest)
        mock_client.name = self.dummy
        mock_client.details = False
        response_info = get_devices(mock_client, None)
        assert not response_info

    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(DeviceManager, "get_device")
    @patch.object(Device, "get_driver")
    def test_get_device(
        self,
        mock_get_driver,
        mock_get_device,
        mock_get_device_manager,
    ):
        mock_get_driver.return_value = DriverDummy()
        device = Device("dummy", DriverDummy())
        device.status = "online"
        device.details = {
            "single_qubit_prop": {
                "qubit1": {
                    "single_qubit_gate_fidelity": 0.999,
                    "qubit_frequency": 5.018,
                    "readout_frequency": 6.8295,
                    "single_qubit_gate_duration": 30.0,
                    "T1": 28.994326898773733,
                    "T2": 5.690175203450656,
                    "readout_fidelity_state0": 0.9705333333333334,
                    "readout_fidelity_state1": 0.8440000000000001,
                }
            },
            "double_qubit_prop": None,
            "topo_configs": None,
        }
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=GetDeviceRequest)
        mock_client.name = self.dummy
        mock_client.details = True

        response_info = get_device(mock_client, None)
        assert response_info.status == "online"
        assert response_info.details["double_qubit_prop"] is None
        assert response_info.details["topo_configs"] is None
        assert response_info.details["single_qubit_prop"] is not None
        assert len(response_info.details["single_qubit_prop"]) == 1
        assert (
            response_info.details["single_qubit_prop"]["qubit1"][
                "single_qubit_gate_fidelity"
            ]
            == 0.999
        )
        assert (
            response_info.details["single_qubit_prop"]["qubit1"][
                "qubit_frequency"
            ]
            == 5.018
        )
        assert (
            response_info.details["single_qubit_prop"]["qubit1"][
                "readout_frequency"
            ]
            == 6.8295
        )
        assert (
            response_info.details["single_qubit_prop"]["qubit1"][
                "single_qubit_gate_duration"
            ]
            == 30.0
        )
        assert (
            response_info.details["single_qubit_prop"]["qubit1"]["T1"]
            == 28.994326898773733
        )
        assert (
            response_info.details["single_qubit_prop"]["qubit1"]["T2"]
            == 5.690175203450656
        )
        assert (
            response_info.details["single_qubit_prop"]["qubit1"][
                "readout_fidelity_state0"
            ]
            == 0.9705333333333334
        )
        assert (
            response_info.details["single_qubit_prop"]["qubit1"][
                "readout_fidelity_state1"
            ]
            == 0.8440000000000001
        )

    @patch.object(TaskScheduler, "add_manage_job")
    def test_calibrate(self, mock_add_manage_job):
        mock_add_manage_job.return_value = None
        mock_client = Mock(spec=CalibrateDeviceRequest)
        mock_client.device_name = self.dummy
        mock_client.method = "calibrate"
        mock_client.details = None
        response_info = calibrate(mock_client)
        assert response_info is not None
        assert response_info.details is None

    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(DeviceManager, "get_device")
    def test_get_calibrate_results(
        self,
        mock_get_device,
        mock_get_device_manager,
    ):
        mock_get_device.return_value = Device("dummy", DriverDummy())
        mock_get_device.calibrate_info = None
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=GetCalibrateResultRequest)
        mock_client.device_name = self.dummy
        mock_client.method = "get_calibrate_results"
        response_info = get_calibrate_results(mock_client)
        assert response_info is not None
        assert response_info.details is not None

    @patch.object(TaskScheduler, "add_manage_job")
    def test_set_device_options(
        self,
        mock_add_manage_job,
    ):
        mock_add_manage_job.return_value = None
        mock_client = Mock(spec=SetDeviceOptionsRequest)
        mock_client.device_name = self.dummy
        mock_client.method = "set_device_options"
        response_info = set_device_options(mock_client)
        assert response_info is not None
        assert response_info.details is None

    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(DeviceManager, "get_device")
    def test_get_device_options(
        self,
        mock_get_device,
        mock_get_device_manager,
    ):
        mock_get_device.return_value = Device("dummy", DriverDummy())
        mock_get_device.device_options_info = {}
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=GetDeviceOptionsRequest)
        mock_client.device_name = self.dummy
        mock_client.method = "get_device_options"
        response_info = get_device_options(mock_client)
        assert response_info is not None
        assert response_info.details is not None
