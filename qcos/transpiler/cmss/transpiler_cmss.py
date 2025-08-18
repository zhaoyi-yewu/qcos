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
from qcos.transpiler.cmss.mapping.hierachy_tree import HierarchyTree, get_block
from qcos.transpiler.cmss.mapping.mapping_factory import MappingFactory
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from qcos.transpiler.common.errors import TranspilerException
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_base import TranspilerBase


class TranspilerCmss(TranspilerBase):
    """
    Transpiler Class for CMSS
    """

    def __init__(self):
        super().__init__()
        self.total_qubits = 0
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

    def mapping(self, qpu_cfg, opt_result_dict):
        """
        mapping

        :param qpu_cfg: qpu_cfg
        :param opt_result_dict: opt_result_dict
        :return mapping result dict
        """
        factory = MappingFactory()
        mapper = factory.get_mapper_by_type(trans_cfg_inst.get_tech_type())
        if len(opt_result_dict) == 1:
            key, value = list(opt_result_dict.items())[0]
            mapper.prepare_data(value[0], value[1], qpu_cfg)
            mapping_res = mapper.execute_with_order()
            logger.info(f"after mapping: {mapping_res}")
            return mapping_res
        else:
            ht = HierarchyTree(qpu_cfg)
            ht.construct()
            mapping_res = []
            for key, value in opt_result_dict.items():
                blk = get_block(ht, value[0])
                if blk is None:
                    # TODO (xudong): need to remove the task item.
                    self.total_qubits -= value[0]
                    continue
                qpu_cfg['operate_area'] = blk
                qpu_cfg['storage_area'] = [qpu_cfg['closest'][o] for o in blk]
                mapper.prepare_data(value[0], value[1], qpu_cfg)
                mapping_res += mapper.execute_with_order()
            return mapping_res

    def parse(self, job_data, aggregation_info):
        """
        parse source codes

        :param job_data: job data
        :param aggregation_info: aggregation job info
        :return parse result
        """
        # compile
        source_codes = job_data['source_code'][0]
        logger.info(f"source_codes:\n{source_codes}")
        num_qubits, parse_result = compile(source_codes)
        if num_qubits > trans_cfg_inst.max_qubits:
            raise TranspilerException("reach max qubits limitation")
        self.total_qubits = num_qubits
        parse_result_dict = {job_data["job_id"]: (num_qubits, parse_result)}
        if aggregation_info is not None:
            for key, value in aggregation_info.sub_jobs.items():
                job_code = value["job_info"]["data"]["source_code"][0]
                num_qubits, parse_result = compile(job_code)
                if self.total_qubits + num_qubits > trans_cfg_inst.max_qubits:
                    # TODO (xudong): need to remove the remained task item.
                    break
                self.total_qubits += num_qubits
                parse_result_dict[key] = (num_qubits, parse_result)
        return parse_result_dict

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

        opt_result_dict = {}
        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1])
            opt_result_dict[key] = (value[0], opt_result)

        mapping_res = self.mapping(qpu_cfg, opt_result_dict)

        # decompose gates
        parsed_circuit = decompose_gates(mapping_res)

        # optimize circuit
        basis_gate_list = optimize_gate(parsed_circuit)
        logger.debug(f"final basis_gate_list: {basis_gate_list}")
        return basis_gate_list
