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


from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.transpiler_base import TranspilerBase


class TranspilerDummy(TranspilerBase):
    """Transpiler Class for Dummy."""

    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_DUMMY
        # alias name
        self.alias_name = "空载转译器(dummy)"
        # version
        self.version = "0.1"
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3,
        ]

    def init_transpiler(self):
        """Init transpiler."""

    def parse(self, src_code_dict):
        """Parse src_code_dict.

        Args:
            src_code_dict: src_code_dict

        Returns:
            parse result
        """

    def transpile(self, parse_result, supp_basis_gates: list):
        """Transpile codes.

        Args:
            parse_result: parse result
            supp_basis_gates: supported basis gates

        Returns:
            transpiled quantum circuit
        """
