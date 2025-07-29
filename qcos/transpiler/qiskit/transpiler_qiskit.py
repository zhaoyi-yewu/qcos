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

from qiskit import transpile, QuantumCircuit
from qiskit_aer import QasmSimulator, AerSimulator

from qcos.common.constant import Constant
from qcos.transpiler.common.errors import TranspilerException
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_base import TranspilerBase


logger = logging.getLogger(__name__)


class TranspilerQiskit(TranspilerBase):
    """
    Transpiler Class for Qiskit
    """
    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_QISKIT
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3
        ]
        # transpiler_options
        self.transpiler_options = {
            "optimization_level": 1  # default optimization level
        }
        # transpiler_options schema used in submit-job from user
        self.transpiler_options_schema = {
            Optional("optimization_level"): int
        }

    def init_transpiler(self):
        pass

    def parse(self, codes: str):
        """
        parse source codes

        :param codes: source codes
        :return parse result
        """
        parse_result = QuantumCircuit.from_qasm_str(codes)
        self.num_qubits = parse_result.num_qubits
        return parse_result

    def transpile(self, parse_result, supp_basis_gates: list):
        """
        Transpile codes

        :param parse_result: parse result
        :param supp_basis_gates: supported basis gates
        :return transpiled quantum circuit
        """
        if trans_cfg_inst.get_driver_name() == "qiskit-qasm-sim":
            simulator = QasmSimulator()
        elif trans_cfg_inst.get_driver_name() == "qiskit-aer-sim":
            simulator = AerSimulator()
        else:
            raise TranspilerException("invalid driver name")
        transpiled_circuit = transpile(
            parse_result,
            simulator,
            optimization_level=self.transpiler_options["optimization_level"],
            basis_gates=supp_basis_gates
        )
        return transpiled_circuit
