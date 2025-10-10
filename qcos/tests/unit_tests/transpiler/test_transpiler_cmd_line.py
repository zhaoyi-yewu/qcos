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
from unittest.mock import patch

from qcos.transpiler.cmss.transpiler_cmd_line import (
    read_qasm_from_file,
    Timer,
    main,
)

timer = Timer()


class TestTranspilerCmdLine:
    def test_read_qasm_from_file(self):
        read_qasm_from_file("None")

    @patch("qcos.transpiler.cmss.transpiler_cmd_line.decompose_gates")
    @patch("qcos.transpiler.cmss.transpiler_cmd_line.optimize_gate")
    @patch("qcos.transpiler.cmss.transpiler_cmd_line.get_ir")
    @patch("qcos.transpiler.cmss.transpiler_cmd_line.get_abs_tree")
    def test_main(
        self,
        mock_get_abs_tree,
        mock_get_ir,
        mock_optimize_gate,
        mock_decompose_gates,
    ):
        mock_get_abs_tree.return_value = None
        mock_get_ir.return_value = (None, None)
        mock_optimize_gate.return_value = None
        mock_decompose_gates.return_value = None
        main()
