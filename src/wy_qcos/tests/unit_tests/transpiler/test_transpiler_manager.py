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

from unittest.mock import patch

from wy_qcos.common.library import Library
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.transpiler.transpiler_manager import TranspilerManager

manager = TranspilerManager()


class TestTranspilerManager:
    @patch.object(Library, "import_classes")
    def test_load_transpilers(self, mock_import_classes):
        classes = {"TranspilerCmss": TranspilerCmss}
        venv_dirs = {}
        mock_import_classes.return_value = classes, venv_dirs

        manager.load_transpilers()

    def test_init_transpilers(self):
        manager.init_transpilers()

    def test_has_transpiler(self):
        manager.has_transpiler("no_name")

    def test_get_transpiler(self):
        manager.get_transpiler("no_name")

    def test_get_transpilers(self):
        manager.get_transpilers()
