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

from qcos.common.constant import Constant
from qcos.tests.system_tests.common.library import StLibrary
from qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestTranspilers:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]

    @classmethod
    def teardown_class(cls):
        pass

    def test_get_transpilers(self):
        transpilers = StLibrary.get_transpilers(self.client)
        assert isinstance(transpilers, dict)

    def test_get_transpiler(self):
        transpiler_name = Constant.TRANSPILER_CMSS
        transpiler = StLibrary.get_transpiler(self.client, transpiler_name)
        assert isinstance(transpiler, dict)
        assert isinstance(transpiler["alias_name"], str)
        assert transpiler["enable"] is True
        assert transpiler["name"] == transpiler_name
        assert transpiler["supported_code_types"] == [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
        ]
        if transpiler["transpiler_options"] is not None:
            assert isinstance(transpiler["transpiler_options"], dict)
        if transpiler["transpiler_options_schema"] is not None:
            assert isinstance(transpiler["transpiler_options_schema"], dict)
        if transpiler["version"] is not None:
            assert isinstance(transpiler["version"], str)
