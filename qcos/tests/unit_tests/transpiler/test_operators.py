#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import numpy as np

from qcos.transpiler.cmss.circuit.operators.operator import Operator
from qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


class TestOperators:
    def test_operator(self):
        op = Operator(np.eye(4))
        assert op._data.shape == (4, 4)

        qc = QuantumCircuit(num_qubits=2, num_clbits=2)
        op = Operator(qc)
        assert op._data.shape == (4, 4)
