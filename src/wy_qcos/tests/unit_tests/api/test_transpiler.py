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
from unittest.mock import Mock, patch

from wy_qcos.api.posiq.routes_jsonrpc.transpiler import (
    get_transpilers,
    get_transpiler,
    _get_transpiler_info,
)
from wy_qcos.api.schemas import GetTranspilerRequest
from wy_qcos.common.constant import Constant
from wy_qcos.task_manager import TaskScheduler
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.transpiler.transpiler_manager import TranspilerManager

response_info = {
    "name": "",
    "alias_name": "",
    "version": "",
    "supported_code_types": [],
    "transpiler_options": {},
    "transpiler_options_schema": {},
    "enable": True,
}


class TestTranspiler:
    @pytest.mark.smoke
    @patch.object(TranspilerManager, "get_transpilers")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    def test_get_transpilers(
        self, mock_get_transpiler_manager, mock_get_transpilers
    ):
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpilers.return_value = {}
        mock_client = Mock(spec=GetTranspilerRequest)
        response = get_transpilers(mock_client)
        assert not response

    @patch("wy_qcos.api.posiq.routes_jsonrpc.transpiler._get_transpiler_info")
    @patch.object(TranspilerManager, "get_transpiler")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    def test_get_transpiler(
        self,
        mock_get_transpiler_manager,
        mock_get_transpiler,
        mock_get_transpiler_info,
    ):
        mock_get_transpiler_info.return_value = response_info
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpiler.return_value = TranspilerBase()
        mock_client = Mock(spec=GetTranspilerRequest)
        mock_client.name = Constant.TRANSPILER_DUMMY
        response = get_transpiler(mock_client)
        assert response.name == ""

    def test__get_transpiler_info(self):
        mock_client = TranspilerBase()
        response = _get_transpiler_info(mock_client)
        assert response["name"] is None

    @patch.object(TranspilerManager, "get_transpilers")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    def test_get_transpilers_with_entries(
        self, mock_get_transpiler_manager, mock_get_transpilers
    ):
        transpiler = Mock(spec=TranspilerBase)
        transpiler.name = Constant.TRANSPILER_DUMMY
        transpiler.alias_name = "Dummy"
        transpiler.enable = True
        transpiler.supported_code_types = [Constant.CODE_TYPE_QASM]
        transpiler.get_version.return_value = "1.0"

        transpiler_manager = Mock(spec=TranspilerManager)
        transpiler_manager.get_transpilers.return_value = {
            Constant.TRANSPILER_DUMMY: transpiler
        }
        mock_get_transpiler_manager.return_value = transpiler_manager
        mock_get_transpilers.return_value = {
            Constant.TRANSPILER_DUMMY: transpiler
        }

        response = get_transpilers(None)

        assert Constant.TRANSPILER_DUMMY in response
        assert response[Constant.TRANSPILER_DUMMY].name == (
            Constant.TRANSPILER_DUMMY
        )

    @patch.object(TranspilerManager, "get_transpiler")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    def test_get_transpiler_not_found(
        self, mock_get_transpiler_manager, mock_get_transpiler
    ):
        mock_get_transpiler_manager.return_value = TranspilerManager()
        mock_get_transpiler.return_value = None
        mock_client = Mock(spec=GetTranspilerRequest)
        mock_client.name = "missing"

        with pytest.raises(Exception):
            get_transpiler(mock_client)
