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


from qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from qcos.transpiler.cmss.compiler.parser import compile
from qcos.transpiler.cmss.mapping import NASingleRoute
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_base import TranspilerBase


logger = logging.getLogger(__name__)


class TranspilerCmss(TranspilerBase):
    """
    Transpiler Class for CMSS
    """

    def transpile(self, qasm: str):
        """
        CMSS transpiler function.

        :param qasm: openqasm codes
        :return basis gate list
        """
        try:
            qpu_cfg = trans_cfg_inst.get_qpu_cfg()
            if not qpu_cfg:
                err_msg = "Missing qpu configs"
                logger.error(err_msg)
                raise ValueError(err_msg)

            # compile and mapping
            logger.debug(f"raw_qasm: {qasm}")
            num_qubits, gates = compile(qasm)
            self.num_qubits = num_qubits
            gates = optimize_gate(gates)
            na_map = NASingleRoute(num_qubits, gates, qpu_cfg)
            mapping_res = na_map.execute_with_order()
            logger.debug(f"initial mapping: {na_map.mapping}")
            logger.debug(f"after mapping: {mapping_res}")

            # decompose gates
            parsed_circuit = decompose_gates(mapping_res)

            # optimize circuit
            basis_gate_list = optimize_gate(parsed_circuit)
            logger.debug(f"final basis_gate_list: {basis_gate_list}")
            return {"basis_gate_list": basis_gate_list, "error": None}
        except Exception as e:
            return {"basis_gate_list": None, "error": ValueError(str(e))}
