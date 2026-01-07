#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from wy_qcos.api.posiq.routes_jsonrpc.device import get_devices, get_device
from wy_qcos.api.schemas import GetDeviceRequest
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

    @patch.object(DeviceManager, "get_devices")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_get_devices(self, mock_get_device_manager, mock_get_devices):
        mock_get_devices.return_value = {}
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=GetDeviceRequest)
        mock_client.name = self.dummy
        response_info = get_devices(mock_client, None)
        assert not response_info

    @patch.object(DeviceManager, "get_device")
    @patch.object(TaskScheduler, "get_device_manager")
    def test_get_device(self, mock_get_device_manager, mock_get_device):
        mock_get_device.return_value = Device(self.dummy, DriverDummy())
        mock_get_device_manager.return_value = DeviceManager(
            Config(), DriverManager()
        )
        mock_client = Mock(spec=GetDeviceRequest)
        mock_client.name = self.dummy
        response_info = get_device(mock_client, None)
        assert response_info.name == self.dummy
