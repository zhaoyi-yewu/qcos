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

from unittest.mock import Mock, patch

from qcos.drivers.driver_base import DriverBase
from qcos.drivers.dummy.driver_dummy import DriverDummy
from qcos.engine.job_engine import init_driver, init_transpiler


class TestJobEngine:
    @patch.object(DriverBase, "validate_driver_configs")
    def test_init_driver(self, mock_validate_driver_configs):
        driver_info = {"module_name": "name", "class_name": "DriverDummy"}
        mock_run = Mock()
        mock_run.name = DriverDummy()
        mock_validate_driver_configs.return_value = iter([True, "err_msg"])

        driver = init_driver.fn
        driver(driver_info, None, None)

    def test_init_transpiler(self):
        transpiler_info = {"module_name": "name",
                           "class_name": "TranspilerDummy"}

        transpiler = init_transpiler.fn
        transpiler(transpiler_info, None)
