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
from schema import Optional

import qiskit
import qiskit.qasm3
from qiskit_aer import QasmSimulator, AerSimulator

from qcos.common.constant import Constant
from qcos.transpiler.common.errors import TranspilerException
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_base import TranspilerBase


class TranspilerQiskit(TranspilerBase):
    """Transpiler Class for Qiskit"""

    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_QISKIT
        # alias name
        self.alias_name = "IBM Qiskit"
        # version
        self.version = qiskit.__version__
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3,
        ]
        # transpiler_options
        self.transpiler_options = {
            # default optimization level
            "optimization_level": Constant.DEFAULT_OPTIMIZATION_LEVEL
        }
        # transpiler_options schema used in submit-job from user
        self.transpiler_options_schema = {Optional("optimization_level"): int}

    def init_transpiler(self):
        """Init transpiler"""

    def parse(self, src_code_dict):
        """Parse src_code_dict

        Args:
            src_code_dict: src_code_dict

        Returns:
            parse result
        """
        if isinstance(src_code_dict, dict) and len(src_code_dict) == 1:
            source_code: str = next(iter(src_code_dict.values()))
            logger.info(f"source_code:\n{source_code}")
            if "OPENQASM 3.0" in source_code:
                parse_result = qiskit.qasm3.loads(source_code)
            else:
                parse_result = qiskit.QuantumCircuit.from_qasm_str(source_code)

            self.total_qubits = parse_result.num_qubits
            return parse_result
        else:
            raise TranspilerException("unsupported input")

    def transpile(self, parse_result, supp_basis_gates: list):
        """Transpile codes

        Args:
            parse_result: parse result
            supp_basis_gates: supported basis gates

        Returns:
            transpiled quantum circuit
        """
        driver_name = trans_cfg_inst.get_driver_name()
        if driver_name == "DriverQiskitQasmSim":
            simulator = QasmSimulator()
        elif driver_name == "DriverQiskitAerSim":
            simulator = AerSimulator()
        else:
            raise TranspilerException(f"invalid driver name: {driver_name}")

        transpiled_circuit = qiskit.transpile(
            parse_result,
            simulator,
            optimization_level=self.transpiler_options["optimization_level"],
            basis_gates=supp_basis_gates,
        )

        return transpiled_circuit, None
