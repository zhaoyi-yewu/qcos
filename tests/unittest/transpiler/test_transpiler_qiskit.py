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
        expected_basis_gates = [Constant.SQ_GATE_RX, Constant.SQ_GATE_RY,
                                Constant.SQ_GATE_RZ, Constant.DQ_GATE_CX]
        transpiler = TranspilerQiskit()
        transpiled_circuit = transpiler.transpile(self.simple_data,
                                                  expected_basis_gates)
        assert len(transpiled_circuit) == 3
