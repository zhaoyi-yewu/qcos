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
# ---------------------------------------------------------------------

from qcos.drivers.driver_manager import DriverManager

obj = DriverManager()


class TestDriverManager:

    def test_load_drivers(self):
        assert obj.load_drivers() is None

    def test_init_drivers(self):
        assert obj.init_drivers() is None

    def test_has_driver(self):
        assert obj.has_driver("driver_name") is False

    def test_get_driver(self):
        assert obj.get_driver("driver_name") is None

    def test_get_drivers(self):
        assert obj.get_drivers() == obj.drivers
