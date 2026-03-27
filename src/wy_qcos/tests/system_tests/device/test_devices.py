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

from wy_qcos.drivers.device import Device
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestDevice:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]

    @classmethod
    def teardown_class(cls):
        pass

    @pytest.mark.smoke
    def test_get_devices(self):
        devices = StLibrary.get_devices(self.client)
        assert isinstance(devices, dict)

    @pytest.mark.smoke
    def test_get_device(self):
        device_name = "dummy"
        device = StLibrary.get_device(self.client, device_name)
        assert isinstance(device, dict)
        assert isinstance(device["alias_name"], str)
        if device["configs"] is not None:
            assert isinstance(device["configs"], dict)
        if device["description"] is not None:
            assert isinstance(device["description"], str)
        assert device["driver_name"] == "DriverDummy"
        assert device["enable"] is True
        assert device["name"] == device_name
        assert device["status"] == Device.DEVICE_STATUS_ONLINE

    def test_get_devices_check_details(self):
        devices = StLibrary.get_devices(self.client)
        assert isinstance(devices, dict)
        for device_name, device_info in devices.items():
            device = StLibrary.get_device(self.client, device_name)
            _drvice_name = device["name"]
            assert device_name == _drvice_name
            assert isinstance(device["name"], str)
            assert isinstance(device["alias_name"], str)
            assert isinstance(device["description"], str)
            assert isinstance(device["driver_name"], str)
            assert isinstance(device["enable"], bool)
            assert isinstance(device["status"], str)
            assert isinstance(device["tech_type"], str | None)
            assert isinstance(device["max_qubits"], int)
            assert isinstance(device["configs"], dict | None)
            assert isinstance(device["details"], dict | None)
            assert device["max_qubits"] > 0

    def test_get_device_with_details(self):
        device_name = "dummy"
        device = StLibrary.get_device(self.client, device_name, True)
        assert isinstance(device, dict)
        assert isinstance(device["alias_name"], str)
        if device["configs"] is not None:
            assert isinstance(device["configs"], dict)
        if device["description"] is not None:
            assert isinstance(device["description"], str)
        assert device["driver_name"] == "DriverDummy"
        assert device["enable"] is True
        assert device["name"] == device_name
        assert device["status"] == Device.DEVICE_STATUS_ONLINE
        assert isinstance(device["details"], dict)
