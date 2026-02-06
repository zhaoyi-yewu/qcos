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
    enable_and_disable_qubit,
    get_device,
    get_devices,
    set_device_options,
)
from wy_qcos.api.schemas import (
    GetDeviceRequest,
    CalibrateDeviceRequest,
    SetDeviceOptionsRequest,
    EnableAndDisableQubitRequest,
)
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.device_manager import DeviceManager
from wy_qcos.drivers.driver_manager import DriverManager
from wy_qcos.drivers.driver_base import DriverBase
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
            "tupo_configs": None,
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
        assert response_info.details["tupo_configs"] is None
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

    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(DeviceManager, "get_device")
    @patch.object(Device, "get_driver")
    def test_calibrate(
        self, mock_get_driver, mock_get_device, mock_get_device_manager
    ):
        mock_get_driver.return_value = DriverDummy()
        mock_get_device.return_value = Device("dummy", DriverDummy())
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=CalibrateDeviceRequest)
        mock_client.device_name = self.dummy
        mock_client.cal_cmd = True
        mock_client.options = {
            "init_freq": 5.018,
            "step": 0.001,
            "machine_type": "superconducting",
            "scan_param": "qubit_frequency",
            "scan_shots": 100,
        }
        response_info = calibrate(mock_client, None)
        assert response_info is None

    @patch.object(DriverBase, "set_device_options")
    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(DeviceManager, "get_device")
    @patch.object(Device, "get_driver")
    def test_set_device_options(
        self,
        mock_get_driver,
        mock_get_device,
        mock_get_device_manager,
        mock_set_device_options,
    ):
        mock_get_driver.return_value = DriverDummy()
        mock_get_device.return_value = Device("dummy", DriverDummy())
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=SetDeviceOptionsRequest)
        mock_client.device_name = self.dummy
        mock_client.device_options = {
            "sleep": 300,
            "shot_gap": 1000,
            "readout_threshold": 0.8,
        }
        mock_set_device_options.return_value = {
            "results": {
                "sleep": True,
                "shot_gap": True,
                "readout_threshold": False,
            }
        }
        response_info = set_device_options(mock_client, None)
        assert response_info is not None
        assert response_info.results["sleep"] is True
        assert response_info.results["shot_gap"] is True
        assert response_info.results["readout_threshold"] is False

    @patch.object(DriverBase, "enable_and_disable_qubit")
    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(DeviceManager, "get_device")
    @patch.object(Device, "get_driver")
    def test_enable_and_disable_qubit(
        self,
        mock_get_driver,
        mock_get_device,
        mock_get_device_manager,
        mock_enable_and_disable_qubit,
    ):
        mock_get_driver.return_value = DriverDummy()
        mock_get_device.return_value = Device("dummy", DriverDummy())
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=EnableAndDisableQubitRequest)
        mock_client.device_name = self.dummy
        mock_client.qubits = {
            "qubit1": True,
            "qubit2": False,
            "qubit1_qubit2": False,
        }
        mock_enable_and_disable_qubit.return_value = {
            "results": {
                "qubit1": True,
                "qubit2": True,
                "qubit1_qubit2": True,
            }
        }
        response_info = enable_and_disable_qubit(mock_client, None)
        assert response_info is not None
        assert response_info.results["qubit1"] is True
        assert response_info.results["qubit2"] is True
        assert response_info.results["qubit1_qubit2"] is True
