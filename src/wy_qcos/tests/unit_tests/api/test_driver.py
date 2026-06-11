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

from wy_qcos.api.posiq.routes_jsonrpc.driver import (
    get_drivers,
    get_driver,
    _get_driver_info,
)
from wy_qcos.common.constant import Constant
from wy_qcos.common.qcos_version import QcosVersion
from wy_qcos.drivers.driver_base import DriverBase
from wy_qcos.drivers.driver_manager import DriverManager
from wy_qcos.drivers.dummy.driver_dummy import DriverDummy
from wy_qcos.task_manager import TaskScheduler
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.transpiler.transpiler_manager import TranspilerManager


response_info = {
    "alias_name": Constant.TECH_TYPE_NEUTRAL_ATOM,
    "description": Constant.TECH_TYPE_NEUTRAL_ATOM,
    "enable_circuit_aggregation": True,
    "max_qubits": 10,
    "name": Constant.TRANSPILER_DUMMY,
    "results_fetch_mode": Constant.RESULTS_FETCH_MODE_SYNC,
    "supported_basis_gates": [
        Constant.SINGLE_QUBIT_GATE_X,
        Constant.SINGLE_QUBIT_GATE_Y,
    ],
    "supported_code_types": [],
    "supported_transpilers": [Constant.TRANSPILER_CMSS],
    "tech_type": Constant.TECH_TYPE_NEUTRAL_ATOM,
    "transpiler": Constant.TRANSPILER_CMSS,
    "version": QcosVersion.VERSION,
}


class TestDriver:
    @classmethod
    def setup_class(cls):
        cls.dummy = Constant.TRANSPILER_DUMMY

    @pytest.mark.smoke
    @patch.object(DriverManager, "get_drivers")
    @patch.object(TaskScheduler, "get_driver_manager")
    def test_get_drivers(self, mock_get_driver_manager, mock_get_drivers):
        mock_get_drivers.return_value = {}
        mock_get_driver_manager.return_value = DriverManager()
        mock_client = Mock()
        mock_client.name = self.dummy
        response = get_drivers(mock_client)
        assert not response

    @pytest.mark.smoke
    @patch("wy_qcos.api.posiq.routes_jsonrpc.driver._get_driver_info")
    @patch.object(TranspilerManager, "get_transpiler")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    @patch.object(DriverManager, "get_driver")
    @patch.object(TaskScheduler, "get_driver_manager")
    def test_get_driver(
        self,
        mock_get_driver_manager,
        mock_get_driver,
        mock_get_transpiler_manager,
        mock_get_transpiler,
        mock__get_driver_info,
    ):
        mock_get_transpiler.return_value = TranspilerBase()
        mock_get_transpiler_manager.return_value = TranspilerManager()
        return_dummy = DriverDummy()
        return_dummy.name = self.dummy
        mock_get_driver.return_value = return_dummy
        mock_get_driver_manager.return_value = DriverManager()
        mock__get_driver_info.return_value = response_info
        mock_client = Mock()
        mock_client.name = self.dummy
        response = get_driver(mock_client)
        assert response.name == self.dummy

    @patch.object(DriverBase, "get_supported_code_types")
    def test_get_driver_info(self, mock_get_supported_code_types):
        mock_get_supported_code_types.return_value = ["qasm"]
        mock_client = DriverBase()
        transpiler = TranspilerCmss()
        _driver_info = _get_driver_info(mock_client, transpiler)
        assert _driver_info["name"] is None

    @patch("wy_qcos.api.posiq.routes_jsonrpc.driver._get_driver_info")
    @patch.object(TaskScheduler, "get_transpiler_manager")
    @patch.object(DriverManager, "get_drivers")
    @patch.object(TaskScheduler, "get_driver_manager")
    def test_get_drivers_with_entries(
        self,
        mock_get_driver_manager,
        mock_get_drivers,
        mock_get_transpiler_manager,
        mock_get_driver_info,
    ):
        transpiler = Mock(spec=TranspilerBase)
        transpiler_manager = Mock(spec=TranspilerManager)
        transpiler_manager.get_transpiler.return_value = transpiler

        driver = DriverDummy()
        driver.transpiler = Constant.TRANSPILER_CMSS

        mock_get_drivers.return_value = {self.dummy: driver}
        mock_get_driver_manager.return_value = DriverManager()
        mock_get_transpiler_manager.return_value = transpiler_manager
        mock_get_driver_info.return_value = response_info

        response = get_drivers(None)
        assert self.dummy in response
        assert response[self.dummy].name == self.dummy
        mock_get_driver_info.assert_called_once_with(driver, transpiler)

    @patch(
        "wy_qcos.api.posiq.routes_jsonrpc.driver."
        "jsonrpc_errors.handle_error_not_found"
    )
    @patch.object(DriverManager, "get_driver")
    @patch.object(TaskScheduler, "get_driver_manager")
    def test_get_driver_not_found(
        self,
        mock_get_driver_manager,
        mock_get_driver,
        mock_handle_error_not_found,
    ):
        mock_get_driver.return_value = None
        mock_get_driver_manager.return_value = DriverManager()
        mock_handle_error_not_found.side_effect = RuntimeError("not found")

        mock_client = Mock()
        mock_client.name = "missing_driver"

        with pytest.raises(RuntimeError, match="not found"):
            get_driver(mock_client)

        mock_handle_error_not_found.assert_called_once()

    @patch.object(DriverBase, "set_supported_code_types")
    @patch.object(DriverBase, "get_supported_code_types")
    def test_get_driver_info_fallback_driver_code_types(
        self,
        mock_get_supported_code_types,
        mock_set_supported_code_types,
    ):
        mock_get_supported_code_types.return_value = ["openqasm"]
        driver = DriverBase()
        _driver_info = _get_driver_info(driver, None)
        mock_set_supported_code_types.assert_called_once_with(["openqasm"])
        assert _driver_info["supported_code_types"] == ["openqasm"]
