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
from wy_qcos.drivers.dummy.driver_dummy import DriverDummy

device = Device("dummy", DriverDummy())


class TestDevice:
    def test_init_device(self):
        success, err_msg = device.init_device()
        assert success is True
        assert err_msg is None

    def test_get_name(self):
        name = device.get_name()
        assert name == "dummy"

    @pytest.mark.smoke
    def test_get_driver(self):
        driver = device.get_driver()
        assert isinstance(driver, DriverDummy)

    def test_set_enable(self):
        device.set_enable(True)
        enable = device.get_enable()
        assert enable is True

    def test_set_status(self):
        assert device.set_status("status") is None
        device.set_status(device.DEVICE_STATUS_ONLINE)
        status = device.get_status()
        assert status == "online"

    def test_set_alias_name(self):
        device.set_alias_name("alias_name")
        alias_name = device.get_alias_name()
        assert alias_name == "alias_name"

    def test_set_description(self):
        device.set_description("description")
        description = device.get_description()
        assert description == "description"

    def test_set_configs(self):
        device.set_configs("configs")
        configs = device.get_configs()
        assert configs == "configs"

    def test_set_device_detail(self):
        details = {}
        calibrate_info = {}
        calibrate_info["step"] = 0.1
        details["calibrate_info"] = calibrate_info
        device.set_device_detail(details)
        assert device.details is not None
        assert device.calibrate_info is not None
        assert device.calibrate_info["step"] == 0.1

    def test_set_device_option(self):
        dev_opt_info = {}
        dev_opt_info["gap"] = 50
        device.set_device_options_info(dev_opt_info)
        res = device.get_device_options_info()
        assert res is not None
        assert res["gap"] == 50
