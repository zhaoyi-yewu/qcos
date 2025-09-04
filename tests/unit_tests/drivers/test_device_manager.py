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

from qcos.common.config import Config
from qcos.drivers.device_manager import DeviceManager
from qcos.drivers.driver_manager import DriverManager

device_manager = DeviceManager(Config(), DriverManager())


class TestDeviceManager:
    def test_load_devices(self):
        device_manager.load_devices()

    def test_init_devices(self):
        device_manager.init_devices()

    def test_has_device(self):
        assert device_manager.has_device("no_such_device") is False

    def test_get_device(self):
        assert device_manager.get_device("no_such_device") is None

    def test_get_devices(self):
        device_manager.get_devices()
