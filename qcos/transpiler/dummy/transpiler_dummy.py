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

from loguru import logger

from qcos.common.constant import Constant
from qcos.transpiler.transpiler_base import TranspilerBase


class TranspilerDummy(TranspilerBase):
    """
    Transpiler Class for Dummy
    """
    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_DUMMY
        # alias name
        self.alias_name = "空载转译器(dummy)"
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3
        ]

    def init_transpiler(self):
        """
        Init transpiler
        """

    def parse(self, circuits):
        """
        parse circuits

        :param circuits: circuits
        :return parse result
        """

    def transpile(self, parse_result, supp_basis_gates: list):
        """
        Transpile codes

        :param parse_result: parse result
        :param supp_basis_gates: supported basis gates
        :return transpiled quantum circuit
        """
