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

from unittest.mock import patch

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.drivers.driver_pulse_base import DriverPulseBase


@pytest.mark.driver
class TestDriverPulseBase:
    def test_init(self):
        driver = DriverPulseBase()
        assert driver.version == "0.0.1"
        assert driver.transpiler == Constant.TRANSPILER_CMSS
        assert driver.supported_transpilers == [Constant.TRANSPILER_CMSS]

    @patch.object(DriverPulseBase, "set_device_status")
    def test_init_driver(self, mock_set_status):
        driver = DriverPulseBase()
        driver.init_driver()
        mock_set_status.assert_called_once()

    def test_fetch_running_info(self):
        driver = DriverPulseBase()
        info = driver.fetch_running_info()
        assert info == {"status": "online"}
