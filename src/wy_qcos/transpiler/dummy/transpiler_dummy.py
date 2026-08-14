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


from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.transpiler.cmss.compiler.openqasm3.parser import (
    parse as openqasm3_parse,
)
from wy_qcos.transpiler.cmss.compiler.parser import compile
from wy_qcos.transpiler.common.errors import TranspilerException
import logging

logger = logging.getLogger(__name__)


class TranspilerDummy(TranspilerBase):
    """Transpiler Class for Dummy."""

    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_DUMMY
        # alias name
        self.alias_name = "空载转译器(dummy)"
        # version
        self.version = "0.1"

    def init_transpiler(self):
        """Init transpiler."""

    def parse(self, src_code_dict, code_type: str = Constant.CODE_TYPE_QASM):
        """Parse src_code_dict.

        Args:
            src_code_dict: src_code_dict
            code_type(str): code type

        Returns:
            parse result
        """
        parse_result_dict = {}
        if code_type == Constant.CODE_TYPE_QUBO:
            return parse_result_dict
        if isinstance(src_code_dict, dict):
            for key, value in src_code_dict.items():
                logger.debug(f"source_code:\n{value}")
                num_qubits = 0
                if code_type in [
                    Constant.CODE_TYPE_QASM,
                    Constant.CODE_TYPE_QASM2,
                ]:
                    num_qubits, _ = compile(value)
                else:
                    circuit = openqasm3_parse(value)
                    num_qubits = circuit.num_qubits
                self.total_qubits += num_qubits
                parse_result_dict[key] = (num_qubits, value)
            return parse_result_dict
        else:
            raise TranspilerException("unsupported input")

    def transpile(self, parse_result, supp_basis_gates: list):
        """Transpile codes.

        Args:
            parse_result: parse result
            supp_basis_gates: supported basis gates

        Returns:
            transpiled quantum circuit, mapping dict, final layout dict
        """
        return parse_result, None, None
