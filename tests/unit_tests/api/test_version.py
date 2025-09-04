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

from qcos.api.posiq.routes_jsonrpc.version import version
from qcos.api.schemas import GetVersionRequest
from qcos.drivers.driver_base import DriverBase
from qcos.drivers.driver_manager import DriverManager
from qcos.drivers.dummy.driver_dummy import DriverDummy
from qcos.task_manager import TaskScheduler
from qcos.transpiler.transpiler_base import TranspilerBase
from qcos.transpiler.transpiler_manager import TranspilerManager


class TestVersion:
    @patch.object(TranspilerManager, 'get_transpiler')
    @patch.object(DriverBase, 'get_supported_transpilers')
    @patch.object(TaskScheduler, 'get_transpiler_manager')
    @patch.object(DriverManager, 'get_drivers')
    @patch.object(TaskScheduler, 'get_driver_manager')
    def test_version(self, mock_get_driver_manager, mock_get_drivers,
                     mock_get_transpiler_manager,
                     mock_get_supported_transpilers, mock_get_transpiler):
        mock_get_supported_transpilers.return_value = ["transpilers"]
        mock_get_transpiler.return_value = TranspilerBase()
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_driver_manager.return_value = DriverManager()
        mock_get_drivers.return_value = {"Dummy": DriverDummy()}
        mock_client = Mock(spec=GetVersionRequest)
        version(mock_client)
