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

import pytest

from qcos.drivers.driver_base import DriverBase


obj = DriverBase()


class TestDriverBase:
    @classmethod
    def setup_class(cls):
        cls.driver_options = {"driver_options": "driver_options"}

    def test_validate_driver(self):
        obj.enable_transpiler = True
        obj.supported_code_types = True
        success, err_msgs = obj.validate_driver()
        assert success is False

        obj.enable_transpiler = False
        obj.supported_code_types = False
        success, err_msgs = obj.validate_driver()
        assert success is False

    def test_validate_driver_configs(self):
        configs = {}
        with pytest.raises(NotImplementedError) as context:
            obj.validate_driver_configs(configs)
        assert (f"Driver: {obj.__class__.__name__} "
                f"must implement method: validate_driver_configs"
                in str(context.value))

    def test_init_driver(self):
        with pytest.raises(NotImplementedError) as context:
            obj.init_driver()
        assert (f"Driver: {obj.__class__.__name__} "
                f"must implement method: init_driver"
                in str(context.value))

    def test_close_driver(self):
        with pytest.raises(NotImplementedError) as context:
            obj.close_driver()
        assert (f"Driver: {obj.__class__.__name__} "
                f"must implement method: close_driver"
                in str(context.value))

    def test_get_driver_options_schema(self):
        driver_options_schema = obj.get_driver_options_schema()
        assert driver_options_schema == obj.driver_options_schema

    def test_update_driver_options(self):
        assert obj.update_driver_options(self.driver_options) is None

    def test_get_driver_info(self):
        driver_info = obj.get_driver_info()
        assert driver_info == (
            f"[{obj.__class__.__name__}]\n"
            f"name: {obj.name}\n"
            f"alias_name: None\n"
            f"description: Quantum Computer base driver\n"
            f"version: {obj.version}\n"
            f"enable_transpiler: {obj.enable_transpiler}\n"
            f"transpiler: {obj.transpiler}\n"
            f"enable_circuit_aggregation: {obj.enable_circuit_aggregation}\n"
            f"results_fetch_mode: {obj.results_fetch_mode}\n"
            f"max_qubits: {obj.max_qubits}"
        )

    def test_set_name_and_get_name(self):
        obj.set_name("name")
        assert obj.get_name() == "name"

    def test_set_module_name_and_get_module_name(self):
        obj.set_module_name("module_name")
        assert obj.get_module_name() == "module_name"

    def test_set_class_name_and_get_class_name(self):
        obj.set_class_name("class_name")
        assert obj.get_class_name() == "class_name"


    def test_get_transpiler(self):
        obj.enable_transpiler = False
        assert obj.get_transpiler() is None
        obj.enable_transpiler = True
        assert obj.get_transpiler() == obj.transpiler

    def test_get_supported_code_types(self):
        assert obj.get_supported_code_types() == obj.supported_code_types

    def test_get_supported_basis_gates(self):
        assert obj.get_supported_basis_gates() == obj.supported_basis_gates

    def test_run(self):
        with pytest.raises(NotImplementedError) as context:
            obj.run("1", 5, {})
        assert (f"Driver: {obj.__class__.__name__} "
                f"must implement method: run")

    def test_dry_run(self):
        assert obj.dry_run("1", 5, {"index": "233"}) is None


    def test_get_default_data_type(self):
        assert obj.get_default_data_type() == obj.default_data_type

    def test_set_max_qubits_and_get_max_qubits(self):
        obj.set_max_qubits(10)
        assert obj.get_max_qubits() == 10
