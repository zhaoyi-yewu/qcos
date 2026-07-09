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

from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.device import (
    calibrate_device,
    get_calibrate_results,
    get_device,
    get_devices,
    set_device_options,
    get_device_options,
    _get_device_info,
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
        device.status = Device.DEVICE_STATUS_ONLINE
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
        assert response_info.status == Device.DEVICE_STATUS_ONLINE
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

    @patch.object(TaskScheduler, "submit_manage_job")
    def test_calibrate(self, mock_submit_manage_job):
        mock_submit_manage_job.return_value = None
        mock_client = Mock(spec=CalibrateDeviceRequest)
        mock_client.device_name = self.dummy
        mock_client.method = "calibrate_device"
        mock_client.details = None
        response_info = calibrate_device(mock_client)
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

    @patch.object(TaskScheduler, "submit_manage_job")
    def test_set_device_options(
        self,
        mock_submit_manage_job,
    ):
        mock_submit_manage_job.return_value = None
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

    @patch("wy_qcos.api.posiq.routes_jsonrpc.device.validate_virtual_instance")
    @patch.object(DeviceManager, "get_devices")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_get_devices_skip_unauthorized_device(
        self,
        mock_get_device_manager,
        mock_get_devices,
        mock_validate_virtual_instance,
    ):
        mock_get_devices.return_value = {
            "device_a": Device("device_a", DriverDummy())
        }
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_validate_virtual_instance.return_value = (False, "forbidden")

        response_info = get_devices(None, {"dummy": "auth"})
        assert response_info == {}

    def test_get_device_info_hides_configs_for_virtual_instance_user(self):
        device = Device("dummy", DriverDummy())
        device.configs = {"password": "secret"}
        device.details = {"key": "value"}
        auth_data = {
            Constant.AUTH_MODE_KEY: Constant.AUTH_MODE_VIRTUAL_INSTANCE,
            "is_super_admin": False,
            "is_project_admin": False,
        }

        response = _get_device_info(device, auth_data, details=False)
        assert "configs" not in response
        assert "details" not in response

    @patch(
        "wy_qcos.api.posiq.routes_jsonrpc.device."
        "jsonrpc_errors.handle_error_not_found"
    )
    @patch("wy_qcos.api.posiq.routes_jsonrpc.device.validate_virtual_instance")
    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_get_device_not_found_by_virtual_instance_validation(
        self,
        mock_get_device_manager,
        mock_get_device,
        mock_validate_virtual_instance,
        mock_handle_error_not_found,
    ):
        mock_get_device.return_value = Device("dummy", DriverDummy())
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_validate_virtual_instance.return_value = (False, "forbidden")
        mock_handle_error_not_found.side_effect = jsonrpc_errors.NotFoundError(
            data={"details": "missing"}
        )

        mock_client = Mock(spec=GetDeviceRequest)
        mock_client.name = self.dummy
        mock_client.details = False

        with pytest.raises(jsonrpc_errors.NotFoundError):
            get_device(mock_client, {"dummy": "auth"})

    @patch(
        "wy_qcos.api.posiq.routes_jsonrpc.device."
        "jsonrpc_errors.handle_error_not_found"
    )
    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_get_calibrate_results_device_not_found(
        self,
        mock_get_device_manager,
        mock_get_device,
        mock_handle_error_not_found,
    ):
        mock_get_device.return_value = None
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_handle_error_not_found.side_effect = jsonrpc_errors.NotFoundError(
            data={"details": "missing"}
        )

        mock_client = Mock(spec=GetCalibrateResultRequest)
        mock_client.device_name = self.dummy
        mock_client.method = "get_calibrate_results"

        with pytest.raises(jsonrpc_errors.NotFoundError):
            get_calibrate_results(mock_client)
