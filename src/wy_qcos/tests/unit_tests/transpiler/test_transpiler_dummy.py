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
from unittest.mock import patch

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.common.errors import TranspilerException
from wy_qcos.transpiler.dummy.transpiler_dummy import TranspilerDummy


transpiler_dummy = TranspilerDummy()


class TestTranspilerDummy:
    def test_init_transpiler(self):
        transpiler_dummy.init_transpiler()

    def test_parse_qubo_returns_empty_dict(self):
        assert transpiler_dummy.parse(None, Constant.CODE_TYPE_QUBO) == {}

    @patch("wy_qcos.transpiler.dummy.transpiler_dummy.compile")
    def test_parse_qasm_dict(self, mock_compile):
        transpiler = TranspilerDummy()
        source = {"code1": "OPENQASM 2.0; qreg q[2];"}
        mock_compile.return_value = (2, None)

        result = transpiler.parse(source, Constant.CODE_TYPE_QASM)

        assert result == {"code1": (2, "OPENQASM 2.0; qreg q[2];")}
        assert transpiler.total_qubits == 1

    @patch("wy_qcos.transpiler.dummy.transpiler_dummy.openqasm3_parse")
    def test_parse_openqasm3_dict(self, mock_openqasm3_parse):
        transpiler = TranspilerDummy()
        source = {"code2": "qubit[3] q;"}
        mock_openqasm3_parse.return_value.num_qubits = 3

        result = transpiler.parse(source, Constant.CODE_TYPE_QASM3)

        assert result == {"code2": (3, "qubit[3] q;")}
        assert transpiler.total_qubits == 2

    def test_parse_unsupported_input_raises(self):
        with pytest.raises(TranspilerException):
            transpiler_dummy.parse(["invalid"], Constant.CODE_TYPE_QASM)

    def test_transpile(self):
        parse_result = {"k": (1, "code")}
        assert transpiler_dummy.transpile(parse_result, [None]) == (
            parse_result,
            None,
        )
