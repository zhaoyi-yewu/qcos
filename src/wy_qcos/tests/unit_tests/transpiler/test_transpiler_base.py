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

from wy_qcos.transpiler.transpiler_base import TranspilerBase


obj = TranspilerBase()


class TestTranspilerBase:
    def test_init_transpiler(self):
        with pytest.raises(NotImplementedError) as context:
            obj.init_transpiler()
        assert (
            f"Transpiler: {obj.__class__.__name__} "
            f"must implement method: init_transpiler" in str(context.value)
        )

    def test_update_transpiler_options(self):
        obj.update_transpiler_options({1: 1, 2: 2, 3: 3, 4: 4})
        assert obj.transpiler_options == {1: 1, 2: 2, 3: 3, 4: 4}

    def test_get_transpiler_info(self):
        assert obj.get_transpiler_info() == (
            f"[{obj.__class__.__name__}]"
            f"\ntranspiler_name: {obj.name}"
            f"\nenable: {obj.enable}"
            f"\ntranspiler_options: {obj.get_transpiler_options()}"
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

    def test_get_supported_code_types(self):
        assert obj.get_supported_code_types() == obj.supported_code_types

    def test_parse(self):
        with pytest.raises(NotImplementedError) as context:
            obj.parse("", "")
        assert (
            f"Transpiler: {obj.__class__.__name__} "
            f"must implement method: parse" in str(context.value)
        )

    def test_transpile(self):
        with pytest.raises(NotImplementedError) as context:
            obj.transpile("", None)
        assert (
            f"Transpiler: {obj.__class__.__name__} "
            f"must implement method: transpile" in str(context.value)
        )
