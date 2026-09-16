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


class TranspilerCmssQubo(TranspilerBase):
    """Transpiler Class for Cmss Qubo."""

    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_CMSS_QUBO
        # alias name
        self.alias_name = "五岳QUBO转译器"
        # version
        self.version = "0.1"
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QUBO,
        ]

    def init_transpiler(self):
        """Init transpiler."""

    def parse(self, src_code_dict, code_type: str = Constant.CODE_TYPE_QUBO):
        """Parse src_code_dict.

        Args:
            src_code_dict: src_code_dict
            code_type(str): code type

        Returns:
            parse result
        """
        return src_code_dict

    def transpile(self, parse_result, supp_basis_gates: list):
        """Transpile codes.

        Args:
            parse_result: parse result
            supp_basis_gates: supported basis gates

        Returns:
            transpiled quantum circuit, mapping dict, final layout dict
        """
        return parse_result, None, None
