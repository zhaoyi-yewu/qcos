#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase


driver_base = DriverBase()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {"index": 0, "source_code": None, "transpile_results": []}


class TestDriverBase:
    @classmethod
    def setup_class(cls):
        cls.driver_options = {"driver_options": "driver_options"}

    def test_validate_driver(self):
        driver_base.enable_transpiler = True
        driver_base.supported_code_types = True
        success, err_msgs = driver_base.validate_driver()
        assert success is False

        driver_base.enable_transpiler = False
        driver_base.supported_code_types = False
        success, err_msgs = driver_base.validate_driver()
        assert success is False

    def test_validate_driver_configs(self):
        configs = {}
        with pytest.raises(NotImplementedError) as context:
            driver_base.validate_driver_configs(configs)
        assert (
            f"Driver: {driver_base.__class__.__name__} "
            f"must implement method: validate_driver_configs"
            in str(context.value)
        )

    def test_init_driver(self):
        with pytest.raises(NotImplementedError) as context:
            driver_base.init_driver()
        assert (
            f"Driver: {driver_base.__class__.__name__} "
            f"must implement method: init_driver" in str(context.value)
        )

    def test_close_driver(self):
        with pytest.raises(NotImplementedError) as context:
            driver_base.close_driver()
        assert (
            f"Driver: {driver_base.__class__.__name__} "
            f"must implement method: close_driver" in str(context.value)
        )

    def test_get_driver_options_schema(self):
        driver_options_schema = driver_base.get_driver_options_schema()
        assert driver_options_schema == driver_base.driver_options_schema

    def test_update_driver_options(self):
        assert driver_base.update_driver_options(self.driver_options) is None

    def test_set_name_and_get_name(self):
        driver_base.set_name("no_name")
        assert driver_base.get_name() == "no_name"

    def test_get_driver_info(self):
        driver_info = driver_base.get_driver_info()
        assert "Quantum Computer base driver" in driver_info

    def test_set_module_name_and_get_module_name(self):
        driver_base.set_module_name("no_module_name")
        assert driver_base.get_module_name() == "no_module_name"

    def test_set_class_name_and_get_class_name(self):
        driver_base.set_class_name("no_class_name")
        assert driver_base.get_class_name() == "no_class_name"

    def test_get_transpiler(self):
        driver_base.enable_transpiler = False
        assert driver_base.get_transpiler() is None
        driver_base.enable_transpiler = True
        assert driver_base.get_transpiler() == driver_base.transpiler

    def test_get_supported_code_types(self):
        supported_code_types = driver_base.get_supported_code_types()
        assert supported_code_types == driver_base.supported_code_types

    def test_get_supported_basis_gates(self):
        supported_transpilers = driver_base.get_supported_basis_gates()
        assert supported_transpilers == driver_base.supported_basis_gates

    def test_run(self):
        with pytest.raises(NotImplementedError):
            driver_base.run(job_id, num_qubits, data)
        assert (
            f"Driver: {driver_base.__class__.__name__} "
            f"must implement method: run"
        )

    def test_dry_run(self):
        assert driver_base.dry_run(job_id, num_qubits, data) is None

    def test_get_default_data_type(self):
        data_type = driver_base.get_default_data_type()
        assert data_type == driver_base.default_data_type

    def test_set_max_qubits_and_get_max_qubits(self):
        driver_base.set_max_qubits(10)
        assert driver_base.get_max_qubits() == 10

    def test_set_alias_name_and_get_alias_name(self):
        driver_base.set_alias_name("alias_name")
        assert driver_base.get_alias_name() == "alias_name"

    def test_get_supported_transpilers(self):
        supported_transpilers = driver_base.get_supported_transpilers()
        assert supported_transpilers == driver_base.supported_transpilers

    def test_set_progress_and_get_progress(self):
        driver_base.set_progress(100)
        assert driver_base.get_progress() == 100

    def test_set_configs_and_get_configs(self):
        configs = {}
        driver_base.set_configs(configs)
        assert driver_base.get_configs() == configs

    def test_cancel(self):
        with pytest.raises(NotImplementedError) as context:
            driver_base.cancel(job_id)
        assert "cancel" in str(context.value)

    @patch.object(Library, "get_nested_dict_value")
    def test_get_results(self, mock_get_nested_dict_value):
        mock_get_nested_dict_value.return_value = {}
        driver_base.get_results(job_id)

    def test_set_device_status(self):
        assert driver_base.set_device_status("") is None

    def test_fetch_configs(self):
        with pytest.raises(NotImplementedError) as context:
            driver_base.fetch_configs()
        assert "fetch_configs" in str(context)
