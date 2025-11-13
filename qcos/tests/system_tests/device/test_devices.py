#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.drivers.device import Device
from qcos.tests.system_tests.common.library import StLibrary
from qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


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

    def test_get_devices(self):
        devices = StLibrary.get_devices(self.client)
        assert isinstance(devices, dict)

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
