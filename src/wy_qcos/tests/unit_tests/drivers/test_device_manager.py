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

from wy_qcos.common.config import Config
from wy_qcos.drivers.device_manager import DeviceManager
from wy_qcos.drivers.driver_manager import DriverManager

device_manager = DeviceManager(Config(), DriverManager())


class TestDeviceManager:
    @pytest.mark.smoke
    def test_load_devices(self):
        device_manager.config.DEVICE_LIST = ["dummy"]
        assert device_manager.load_devices() is None

    def test_init_devices(self):
        assert device_manager.init_devices() is None

    def test_has_device(self):
        assert device_manager.has_device("tiangong10000") is False

    def test_get_device(self):
        assert device_manager.get_device("tiangong10000") is None

    def test_get_devices(self):
        assert device_manager.get_devices() is not None
