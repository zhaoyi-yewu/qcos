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

from qcos.common.constant import Constant
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.qiskit.transpiler_qiskit import TranspilerQiskit


class TestTranspilerQiskit:
    @classmethod
    def setup_class(cls):
        cls.simple_data = '''
          OPENQASM 2.0;
          include "qelib1.inc";
          qreg q[1];
          creg c[1];
          h q[0];
          x q[0];
          rx(1) q[0];
          measure q->c;
        '''

    def test_transpiler_qiskit(self):
        expected_basis_gates = [Constant.SINGLE_QUBIT_GATE_RX,
                                Constant.SINGLE_QUBIT_GATE_RY,
                                Constant.SINGLE_QUBIT_GATE_RZ,
                                Constant.TWO_QUBIT_GATE_CX]
        trans_cfg_inst.set_driver_name("DriverQiskitAerSim")
        transpiler = TranspilerQiskit()
        src_code_info = {"000": self.simple_data}
        parse_result = transpiler.parse(src_code_info)
        transpiled_circuit, _ = transpiler.transpile(parse_result,
                                                     expected_basis_gates)
        assert len(transpiled_circuit) == 3

    def test_transpiler_qiskit_abnormal(self):
        expected_basis_gates = [Constant.SINGLE_QUBIT_GATE_RX,
                                Constant.SINGLE_QUBIT_GATE_RY,
                                Constant.SINGLE_QUBIT_GATE_RZ,
                                Constant.TWO_QUBIT_GATE_CX]
        trans_cfg_inst.set_driver_name("DriverQiskitAerSim")
        transpiler = TranspilerQiskit()
        src_code_info = {"000": self.simple_data}
        try:
            parse_result = transpiler.parse(src_code_info)
        except Exception as e:
            assert 'unsupported input' in str(e)
