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
# ----------------------------------------------------------------------

import pytest

from wy_qcos.common.library import Constant
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestDrivers:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]

    @classmethod
    def teardown_class(cls):
        pass

    def test_get_drivers(self):
        drivers = StLibrary.get_drivers(self.client)
        assert isinstance(drivers, dict)

    def test_get_driver(self):
        driver_name = "DriverDummy"
        driver = StLibrary.get_driver(self.client, driver_name)
        assert isinstance(driver, dict)
        assert driver["alias_name"] is not None
        if driver["description"] is not None:
            assert isinstance(driver["description"], str)
        assert driver["name"] == driver_name
        assert driver["enable_circuit_aggregation"] is True
        assert driver["enable_transpiler"] is True
        assert driver["max_qubits"] == 10
        assert driver["results_fetch_mode"] == Constant.RESULTS_FETCH_MODE_SYNC
        assert driver["supported_basis_gates"] == [
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
        ]
        assert driver["supported_code_types"] == [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
        ]
        assert driver["supported_transpilers"] == [Constant.TRANSPILER_CMSS]
        assert driver["tech_type"] == Constant.TECH_TYPE_NEUTRAL_ATOM
        assert driver["transpiler"] == Constant.TRANSPILER_CMSS
        if driver["version"] is not None:
            assert isinstance(driver["version"], str)

    def test_get_drivers_check_details(self):
        drivers = StLibrary.get_drivers(self.client)
        assert isinstance(drivers, dict)
        for driver_name, driver_info in drivers.items():
            driver = StLibrary.get_driver(self.client, driver_name)
            _driver_name = driver["name"]
            assert driver_name == _driver_name
            assert isinstance(driver["name"], str)
            assert isinstance(driver["alias_name"], str)
            assert isinstance(driver["version"], str)
            assert isinstance(driver["description"], str)
            assert isinstance(driver["tech_type"], str)
            assert isinstance(driver["max_qubits"], int)
            assert isinstance(driver["enable_transpiler"], bool)
            assert isinstance(driver["transpiler"], str | None)
            assert isinstance(driver["supported_transpilers"], list)
            assert isinstance(driver["enable_circuit_aggregation"], bool)
            assert isinstance(driver["supported_code_types"], list)
            assert isinstance(driver["supported_basis_gates"], list | None)
            assert isinstance(driver["results_fetch_mode"], str)
            assert driver["max_qubits"] > 0
            if driver["enable_transpiler"]:
                assert len(driver["transpiler"]) > 0
                assert len(driver["supported_transpilers"]) > 0
                assert len(driver["supported_basis_gates"]) > 0
            assert len(driver["supported_code_types"]) > 0
