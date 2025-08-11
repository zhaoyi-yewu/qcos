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

from schema import Optional

from loguru import logger

from qcos.common.constant import Constant
from qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from qcos.transpiler.cmss.compiler.parser import compile
from qcos.transpiler.cmss.mapping.mapping_factory import MappingFactory
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_base import TranspilerBase


class TranspilerCmss(TranspilerBase):
    """
    Transpiler Class for CMSS
    """

    def __init__(self):
        super().__init__()
        self.name = Constant.TRANSPILER_CMSS
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2
        ]
        # transpiler_options
        self.transpiler_options = {
            "optimization_level": 1  # default optimization level
        }
        # transpiler_options schema used in submit-job from user
        self.transpiler_options_schema = {
            Optional("optimization_level"): int
        }
        # qpu_config
        self.qpu_config = None

    def init_transpiler(self):
        pass

    def parse(self, codes: str):
        """
        parse source codes

        :param codes: source codes
        :return parse result
        """
        # compile and mapping
        num_qubits, parse_result = compile(codes)
        self.num_qubits = num_qubits
        return parse_result

    def transpile(self, parse_result, supp_basis_gates: list):
        """
        CMSS transpiler function.

        :param parse_result: parse result
        :param supp_basis_gates: supported basis gates
        :return basis gate list
        """
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        if not qpu_cfg:
            err_msg = "Missing qpu configs"
            logger.error(err_msg)
            raise ValueError(err_msg)
        opt_result = optimize_gate(parse_result)
        factory = MappingFactory(self.num_qubits, opt_result, qpu_cfg)
        mapper = factory.get_mapper_by_type(trans_cfg_inst.get_tech_type())
        mapping_res = mapper.execute_with_order()
        logger.info(f"after mapping: {mapping_res}")

        # decompose gates
        parsed_circuit = decompose_gates(mapping_res)

        # optimize circuit
        basis_gate_list = optimize_gate(parsed_circuit)
        logger.debug(f"final basis_gate_list: {basis_gate_list}")
        return basis_gate_list
