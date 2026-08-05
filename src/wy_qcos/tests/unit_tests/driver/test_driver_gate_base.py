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
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.driver_gate_base import DriverGateBase


@pytest.mark.driver
class TestDriverGateBase:
    def test_init(self):
        driver = DriverGateBase()
        assert driver.supported_code_types == [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3,
        ]
        assert driver.default_data_type == (DriverBase.DATA_TYPE_GATE_SEQUENCE)
        assert driver.enable_circuit_aggregation is False
        assert driver.results_fetch_mode == (Constant.RESULTS_FETCH_MODE_SYNC)
        assert driver.supported_basis_gates == []

    def test_is_subclass_of_driver_base(self):
        assert issubclass(DriverGateBase, DriverBase)

    def test_init_driver(self):
        driver = DriverGateBase()
        with patch.object(DriverGateBase, "set_device_status") as mock_set:
            driver.init_driver()
            mock_set.assert_called_once_with(Device.DEVICE_STATUS_ONLINE)

    def test_close_driver(self):
        driver = DriverGateBase()
        assert driver.close_driver() is None

    def test_cancel(self):
        driver = DriverGateBase()
        assert driver.cancel("test_job_id") is None

    def test_fetch_running_info(self):
        driver = DriverGateBase()
        info = driver.fetch_running_info()
        assert info == {"status": Device.DEVICE_STATUS_ONLINE}

    def test_fetch_configs(self):
        driver = DriverGateBase()
        assert driver.fetch_configs() is None
