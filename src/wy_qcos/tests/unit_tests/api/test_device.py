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

from unittest.mock import MagicMock, Mock, patch

from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.device import (
    calibrate_device,
    get_calibrate_results,
    get_device,
    get_devices,
    set_device,
    set_device_options,
    get_device_options,
    _get_device_info,
)
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.api.schemas import (
    GetDeviceRequest,
    CalibrateDeviceRequest,
    GetCalibrateResultRequest,
    SetDeviceOptionsRequest,
    GetDeviceOptionsRequest,
    SetDeviceRequest,
)
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.device.device import Device
from wy_qcos.device.device_manager import DeviceManager
from wy_qcos.driver.driver_manager import DriverManager
from wy_qcos.driver.dummy.driver_dummy import DriverDummy
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

    @patch.object(TaskScheduler, "get_device_manager")
    @patch.object(DeviceManager, "get_device")
    @patch.object(Device, "get_driver")
    def test_get_device_with_job_count(
        self,
        mock_get_driver,
        mock_get_device,
        mock_get_device_manager,
    ):
        """get_device should return job_count grouped by status."""
        mock_get_driver.return_value = DriverDummy()
        device = Device("dummy", DriverDummy())
        device.status = Device.DEVICE_STATUS_ONLINE
        device.details = {}
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=GetDeviceRequest)
        mock_client.name = "dummy"
        mock_client.details = False

        # Mock count_by_status: single GROUP BY query returning
        # only statuses present in the database (QUEUED=3, RUNNING=1)
        # spec=JobRepository makes isinstance(mock_repo, JobRepository)
        # return True so _get_job_count queries the repository.
        mock_repo = MagicMock(spec=JobRepository)
        mock_repo.count_by_status.return_value = {
            Constant.JOB_STATUS_QUEUED: 3,
            Constant.JOB_STATUS_RUNNING: 1,
        }

        response_info = get_device(mock_client, None, job_repo=mock_repo)
        # _get_job_count normalizes keys to lowercase
        assert response_info.job_count[Constant.JOB_STATUS_QUEUED.lower()] == 3
        assert (
            response_info.job_count[Constant.JOB_STATUS_RUNNING.lower()] == 1
        )
        assert (
            response_info.job_count[Constant.JOB_STATUS_COMPLETED.lower()] == 0
        )
        # TOTAL = sum of all statuses (3 + 1 = 4)
        assert response_info.job_count[Constant.JOB_STATUS_TOTAL.lower()] == 4
        # All statuses in JOB_STATUSES are present (lowercase keys)
        for status in Constant.JOB_STATUSES:
            assert status.lower() in response_info.job_count
        assert Constant.JOB_STATUS_TOTAL.lower() in response_info.job_count
        # count_by_status called once (single GROUP BY query)
        mock_repo.count_by_status.assert_called_once_with("dummy")

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
        mock_client = Mock(spec=GetDeviceRequest)
        mock_client.details = False
        mock_validate_virtual_instance.return_value = (False, "forbidden")

        response_info = get_devices(mock_client, {"dummy": "auth"})
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


class TestSetDevice:
    """Tests for set_device API route."""

    @classmethod
    def setup_class(cls):
        cls.dummy = Constant.TRANSPILER_DUMMY

    def _make_device(self):
        """Create a real Device instance for testing."""
        return Device("dummy", DriverDummy())

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_status_online(self, mock_get_device_manager, mock_get_device):
        """Set device status to online clears manual maintain."""
        device = self._make_device()
        device.set_manual_maintain_mode(True)
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = "online"
        body.enable = None
        body.max_qubits = None

        result = set_device(body)
        assert result.name == "dummy"
        assert result.status == "online"
        assert device.get_manual_maintain_mode() is False

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_status_maintain(
        self, mock_get_device_manager, mock_get_device
    ):
        """Set device status to maintain enables manual maintain."""
        device = self._make_device()
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = "maintain"
        body.enable = None
        body.max_qubits = None

        result = set_device(body)
        assert result.status == "maintain"
        assert device.get_manual_maintain_mode() is True

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_status_auto_no_change(
        self, mock_get_device_manager, mock_get_device
    ):
        """status='auto' does not change device status."""
        device = self._make_device()
        device.set_status("offline")
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = "auto"
        body.enable = None
        body.max_qubits = None

        result = set_device(body)
        assert result.status == "offline"

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_enable(self, mock_get_device_manager, mock_get_device):
        """Set device enable flag."""
        device = self._make_device()
        device.set_enable(True)
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = None
        body.enable = False
        body.max_qubits = None

        result = set_device(body)
        assert result.enable is False
        assert device.enable is False

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_max_qubits(self, mock_get_device_manager, mock_get_device):
        """Set device max qubits to a specific value."""
        device = self._make_device()
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = None
        body.enable = None
        body.max_qubits = "50"

        result = set_device(body)
        assert result.max_qubits == 50

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_max_qubits_auto(
        self, mock_get_device_manager, mock_get_device
    ):
        """Set max_qubits='auto' restores driver default."""
        device = self._make_device()
        device.set_max_qubits(10)
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = None
        body.enable = None
        body.max_qubits = "auto"

        result = set_device(body)
        assert result.max_qubits == (device.get_driver().get_max_qubits())

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_all_attributes(
        self, mock_get_device_manager, mock_get_device
    ):
        """Set status, enable, and max_qubits together."""
        device = self._make_device()
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = "online"
        body.enable = True
        body.max_qubits = "100"

        result = set_device(body)
        assert result.status == "online"
        assert result.enable is True
        assert result.max_qubits == 100

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_device_not_found(
        self, mock_get_device_manager, mock_get_device
    ):
        """Device not found raises NotFoundError."""
        mock_get_device.return_value = None
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "missing"
        body.status = "online"
        body.enable = None
        body.max_qubits = None

        with pytest.raises(jsonrpc_errors.NotFoundError):
            set_device(body)

    @patch(
        "wy_qcos.api.posiq.routes_jsonrpc.device."
        "jsonrpc_errors.handle_error_not_found"
    )
    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_invalid_max_qubits(
        self,
        mock_get_device_manager,
        mock_get_device,
        mock_handle_error,
    ):
        """Invalid max_qubits raises error."""
        device = self._make_device()
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_handle_error.side_effect = jsonrpc_errors.NotFoundError(
            data={"details": "invalid"}
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = None
        body.enable = None
        body.max_qubits = "not_a_number"

        with pytest.raises(jsonrpc_errors.NotFoundError):
            set_device(body)

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_set_none_leaves_unchanged(
        self, mock_get_device_manager, mock_get_device
    ):
        """All-None fields leave device attributes unchanged."""
        device = self._make_device()
        device.set_status("online")
        device.set_enable(True)
        device.set_max_qubits(42)
        mock_get_device.return_value = device
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )

        body = Mock(spec=SetDeviceRequest)
        body.device_name = "dummy"
        body.status = None
        body.enable = None
        body.max_qubits = None

        result = set_device(body)
        assert result.status == "online"
        assert result.enable is True
        assert result.max_qubits == 42
