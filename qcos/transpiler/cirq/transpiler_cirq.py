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

import logging
from schema import Optional

import cirq
from cirq.contrib.qasm_import import circuit_from_qasm

from qcos.common.constant import Constant
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_base import TranspilerBase


logger = logging.getLogger(__name__)


class TranspilerCirq(TranspilerBase):
    """
    Transpiler Class for Cirq
    """

    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_CIRQ
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3
        ]
        # transpiler_info
        self.transpiler_info = {
            "optimization_level": 1  # default optimization level
        }
        # transpiler_info schema used in submit-job from user
        self.transpiler_info_schema = {
            Optional("optimization_level"): int
        }

    def init_transpiler(self):
        pass

    def transpile(self, qasm: str, expect_basis_gates: list):
        """
        Transpile codes

        :param qasm: qasm codes
        :param expect_basis_gates: expect basis gates
        :return transpiled quantum circuit
        """
        circuit = circuit_from_qasm(qasm)

        if trans_cfg_inst.get_driver_name() == "cirq_qasm":
            simulator = cirq.Simulator()
        else:
            simulator = cirq.Simulator()


        return transpiled_circuit
