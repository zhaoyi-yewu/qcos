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

from schema import Optional
from loguru import logger

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from wy_qcos.transpiler.cmss.compiler.parser import compile
from wy_qcos.transpiler.cmss.mapping.aggregate.hierachy_tree import (
    HierarchyTree,
    get_block,
)
from wy_qcos.transpiler.cmss.mapping.empty_mapping import EmptyRoute
from wy_qcos.transpiler.cmss.mapping.mapping_factory import MappingFactory
from wy_qcos.transpiler.cmss.mapping.sc_mapping import (
    SCRoute,
    SC_MAPPING_OPTIONS_SCHEMA,
)
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from wy_qcos.transpiler.common.errors import TranspilerException
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.transpiler_base import TranspilerBase


class TranspilerCmss(TranspilerBase):
    """Transpiler Class for CMSS."""

    def __init__(
        self,
        optimization_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
        enable_na_move: bool = False,
    ):
        super().__init__()
        self.total_qubits = 0
        self.name = Constant.TRANSPILER_CMSS
        # alias name
        self.alias_name = "五岳转译器"
        # version
        self.version = "0.1"
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
        ]
        # transpiler_options
        if (
            optimization_level < Constant.MIN_OPTIMIZATION_LEVEL
            or optimization_level > Constant.MAX_OPTIMIZATION_LEVEL
        ):
            raise TranspilerException(
                f"""
                optimization_level should be between
                {Constant.MIN_OPTIMIZATION_LEVEL} and
                {Constant.MAX_OPTIMIZATION_LEVEL}
                """
            )
        self.transpiler_options = {
            # default optimization level
            "optimization_level": optimization_level,
            "enable_na_move": enable_na_move,
            # sc_mapping options
            "sc_mapping_options": {},
        }
        # transpiler_options schema used in submit-job from user
        self.transpiler_options_schema = {
            Optional("optimization_level"): int,
            Optional("enable_na_move"): bool,
            Optional("sc_mapping_options"): SC_MAPPING_OPTIONS_SCHEMA,
        }
        # qpu_config
        self.qpu_config = None

    def init_transpiler(self):
        """Init transpiler."""

    def mapping(self, qpu_cfg, opt_result_dict):
        """Mapping.

        Args:
          qpu_cfg: qpu_cfg
          opt_result_dict: opt_result_dict
        :return mapping result dict
        """
        factory = MappingFactory()

        enable_na_move = self.transpiler_options.get("enable_na_move", False)
        sc_mapping_options = self.transpiler_options.get(
            "sc_mapping_options", {}
        )
        mapper = factory.get_mapper_by_type(
            trans_cfg_inst.get_tech_type(), enable_na_move
        )
        if isinstance(mapper, EmptyRoute):
            mapping_dict = {}
            key, value = list(opt_result_dict.items())[0]
            mapping_dict[key] = value[0]
            mapping_res = value[1]
            return mapping_res, mapping_dict

        # set sc_mapping_options
        if isinstance(mapper, SCRoute) and sc_mapping_options:
            mapper.set_sc_mapping_options(sc_mapping_options)

        mapping_dict = {}
        if len(opt_result_dict) == 1:
            key, value = list(opt_result_dict.items())[0]
            mapping_dict[key] = value[0]
            mapper.prepare_data(value[0], value[1], qpu_cfg)
            mapping_res = mapper.execute_with_order()
            logger.info(f"after mapping: {mapping_res}")
            return mapping_res, mapping_dict
        else:
            ht = HierarchyTree(qpu_cfg)
            ht.construct()
            mapping_res = []
            for key, value in opt_result_dict.items():
                # 不使用b+树进行block查找
                blk = get_block(ht, value[0])
                # 使用b+树进行block查找
                # TODO (wangjujun): use b+ tree by parameter.
                # blk = get_block_bplus(ht, value[0])
                if blk is None:
                    # TODO (xudong): need to remove the task item.
                    self.total_qubits -= value[0]
                    continue
                mapping_dict[key] = value[0]
                if not isinstance(mapper, SCRoute):
                    qpu_cfg["operate_area"] = blk
                    qpu_cfg["storage_area"] = [
                        qpu_cfg["closest"][o] for o in blk
                    ]
                mapper.prepare_data(value[0], value[1], qpu_cfg)
                mapping_res += mapper.execute_with_order()
            return mapping_res, mapping_dict

    def parse(self, src_code_dict):
        """Parse src_code_dict.

        Args:
          src_code_dict: src_code_dict
        :return parse result
        """
        # compile
        parse_result_dict = {}
        self.total_qubits = 0
        if isinstance(src_code_dict, dict):
            for key, value in src_code_dict.items():
                logger.info(f"source_code:\n{value}")
                num_qubits, parse_result = compile(value)
                if self.total_qubits + num_qubits > trans_cfg_inst.max_qubits:
                    # TODO (xudong): need to remove the remained task item.
                    break
                self.total_qubits += num_qubits
                parse_result_dict[key] = (num_qubits, parse_result)
            return parse_result_dict
        else:
            raise TranspilerException("unsupported input")

    def transpile(self, parse_result, supp_basis_gates: list):
        """CMSS transpiler function.

        Args:
          parse_result: parse result
          supp_basis_gates: supported basis gates

        Returns:
            basis gate list(list): basis gate list by cmss transpiler
            mapping_dict(dict): mapping dict by cmss mapping.
            only for neutral atom now
        """
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        if not qpu_cfg:
            err_msg = "Missing qpu configs"
            logger.error(err_msg)
            raise ValueError(err_msg)

        opt_result_dict = {}
        opt_level = self.transpiler_options.get(
            "optimization_level", Constant.DEFAULT_OPTIMIZATION_LEVEL
        )
        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], opt_level)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_res, mapping_dict = self.mapping(qpu_cfg, opt_result_dict)

        # decompose gates
        enable_na_move = self.transpiler_options.get("enable_na_move", False)

        # support cz gate for NARoute
        if enable_na_move:
            supp_basis_gates = [
                Constant.SINGLE_QUBIT_GATE_RX,
                Constant.SINGLE_QUBIT_GATE_RY,
                Constant.TWO_QUBIT_GATE_CZ,
            ]
        parsed_circuit = decompose_gates(mapping_res, supp_basis_gates)

        # optimize circuit
        basis_gate_list = optimize_gate(parsed_circuit, opt_level)
        logger.debug(f"final basis_gate_list: {basis_gate_list}")
        return basis_gate_list, mapping_dict
