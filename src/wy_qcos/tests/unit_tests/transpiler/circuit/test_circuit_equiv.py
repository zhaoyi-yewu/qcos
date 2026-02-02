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

import pytest

from wy_qcos.transpiler.common.errors import CircuitException
from wy_qcos.transpiler.cmss.common.gate_operation import X, H, CX
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.circuit.circuit_equiv import CircuitEquivChecker


class TestCircuitEquvChecker:
    @pytest.mark.smoke
    def test_circuit_equiv(self):
        qc1 = QuantumCircuit(num_qubits=2)
        gates_list = [X([0]), CX([0, 1]), H([1])]
        for gate in gates_list:
            qc1.append(gate)

        qc2 = QuantumCircuit(num_qubits=2)
        gates_list = [X([0]), CX([0, 1]), H([1])]
        for gate in gates_list:
            qc2.append(gate)

        cec = CircuitEquivChecker(qc1, qc2)

        assert cec.algo_equiv(algo_no=0) is True
        assert cec.algo_equiv(algo_no=1) is True
        assert cec.algo_equiv(algo_no=2) is True

    def test_circuit_exception(self):
        with pytest.raises(CircuitException) as e:
            _ = CircuitEquivChecker("qc1", "qc2")

        err_msg = str(e.value)
        assert "Invalid quantum circuit type." in err_msg

        with pytest.raises(CircuitException) as e:
            cec = CircuitEquivChecker(QuantumCircuit(), QuantumCircuit())
            cec.algo_equiv(algo_no=-1)

        err_msg = str(e.value)
        assert "Invalid argument algo_num" in err_msg

        with pytest.raises(CircuitException) as e:
            cec = CircuitEquivChecker(QuantumCircuit(), QuantumCircuit())
            cec.algo_equiv(algo_no=-1)

        err_msg = str(e.value)
        assert "Invalid argument algo_num" in err_msg

        with pytest.raises(CircuitException) as e:
            _ = CircuitEquivChecker.cicuit_equiv_by_qcec(1, 1)

        err_msg = str(e.value)
        assert "The input circuit is not a string" in err_msg

        with pytest.raises(CircuitException) as e:
            _ = CircuitEquivChecker.cicuit_equiv_by_qcec("qc", 1)

        err_msg = str(e.value)
        assert "The input circuit is not a string" in err_msg
