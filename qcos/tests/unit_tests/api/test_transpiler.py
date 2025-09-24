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

from qcos.api.posiq.routes_jsonrpc.transpiler import (get_transpilers,
                                                      get_transpiler)
from qcos.api.schemas import GetTranspilerRequest
from qcos.common.constant import Constant
from qcos.task_manager import TaskScheduler
from qcos.transpiler.transpiler_base import TranspilerBase
from qcos.transpiler.transpiler_manager import TranspilerManager


class TestTranspiler:
    @patch.object(TranspilerManager, 'get_transpilers')
    @patch.object(TaskScheduler, 'get_transpiler_manager')
    def test_get_transpilers(self, mock_get_transpiler_manager,
                             mock_get_transpilers):
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpilers.return_value = {}
        mock_client = Mock(spec=GetTranspilerRequest)
        get_transpilers(mock_client)

    @patch.object(TranspilerManager, 'get_transpiler')
    @patch.object(TaskScheduler, 'get_transpiler_manager')
    def test_get_transpiler(self, mock_get_transpiler_manager,
                            mock_get_transpiler):
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpiler.return_value = TranspilerBase()
        mock_client = Mock(spec=GetTranspilerRequest)
        mock_client.name = Constant.TRANSPILER_DUMMY
        get_transpiler(mock_client)
