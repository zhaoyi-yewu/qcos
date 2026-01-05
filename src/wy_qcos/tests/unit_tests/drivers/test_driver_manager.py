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
# ---------------------------------------------------------------------

from unittest.mock import patch

from wy_qcos.common.library import Library
from wy_qcos.drivers.driver_base import DriverBase
from wy_qcos.drivers.driver_manager import DriverManager
from wy_qcos.drivers.dummy.driver_dummy import DriverDummy

obj = DriverManager()


class TestDriverManager:
    @patch.object(Library, "import_classes")
    def test_load_drivers(self, mock_import_classes):
        mock_import_classes.return_value = {"class": DriverDummy}
        assert obj.load_drivers() is None

    @patch.object(DriverBase, "validate_driver")
    def test_init_drivers(self, mock_validate_driver):
        mock_validate_driver.return_value = iter([True, "err_msg"])
        assert obj.init_drivers() is None

        mock_validate_driver.return_value = iter([False, "err_msg"])
        assert obj.init_drivers() is None

    def test_has_driver(self):
        assert obj.has_driver("tiangong10000") is False

    def test_get_driver(self):
        assert obj.get_driver("tiangong10000") is None

    def test_get_drivers(self):
        assert obj.get_drivers() == obj.drivers
