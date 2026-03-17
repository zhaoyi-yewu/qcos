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

import numpy as np
import pytest
from pathlib import Path

from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.transpiler.cmss.common.gate_operation import X, H, CX
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.transpiler_cmd_line import (
    CMSSTranspilerPerf,
)
from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.transpiler.cmss.circuit.register import (
    QuantumRegister,
    ClassicalRegister,
)
from wy_qcos.transpiler.common.errors import CircuitException


@pytest.mark.usefixtures("global_configs")
class TestQuantumCircuit:
    @pytest.mark.smoke
    def test_quantum_circuit_init(self):
        qc = QuantumCircuit(num_qubits=2, num_clbits=2)

        assert qc.num_qubits == 2
        assert qc.num_clbits == 2
        assert len(qc.get_operations()) == 0

        with pytest.raises(CircuitException) as e:
            qc = QuantumCircuit(num_qubits="2", num_clbits="2")

        err_msg = str(e.value)
        assert err_msg == "num_qubits and num_clbits must be integers."

        with pytest.raises(CircuitException) as e:
            qc = QuantumCircuit(num_qubits=-1, num_clbits=-1)

        err_msg = str(e.value)
        assert err_msg == "Number of qubits and clbits must be non-negative."

    def test_quantum_circuit_append(self):
        qc = QuantumCircuit(num_qubits=2, num_clbits=2)
        gate1 = X([0])
        gate2 = CX([0, 1])
        gate3 = H([1])
        gates_list = [gate1, gate2, gate3]
        for gate in gates_list:
            qc.append(gate)

        gates = qc.get_operations()
        assert len(gates) == 3
        assert gates[0].name == "x" and gates[0].targets == [0]
        assert gates[1].name == "cx" and gates[1].targets == [0, 1]
        assert gates[2].name == "h" and gates[2].targets == [1]

    def test_quantum_circuit_append_operations(self):
        qc = QuantumCircuit()
        gate1 = X([0])
        gate2 = CX([0, 1])
        gate3 = H([1])
        qc.set_num_qubits(2)
        qc.set_num_clbits(2)
        qc.set_global_phase(np.pi)
        assert (
            qc.num_qubits == 2
            and qc.num_clbits == 2
            and qc.global_phase == np.pi
        )

        gates_list = [gate1, gate2, gate3]
        qc.append_operations(gates_list)
        gates = qc.get_operations()
        assert len(gates) == 3
        assert gates[0].name == "x" and gates[0].targets == [0]
        assert gates[1].name == "cx" and gates[1].targets == [0, 1]
        assert gates[2].name == "h" and gates[2].targets == [1]

    def test_quantum_circuit_depth_width(self):
        qasm_path = GLOBAL_CONFIGS["samples_dir"]
        qasm_file = f"{qasm_path}/qasm/2.0/simple-qasm.qasm"
        file_path = Path(qasm_file).resolve()
        qasm_data = CMSSTranspilerPerf.read_qasm_from_file(str(file_path))
        cir = get_ir(get_abs_tree(qasm_data))
        depth = cir.depth()
        width = cir.width()
        assert depth == 2
        assert width == 4
        assert cir.num_qubits == 2
        assert cir.size() == 4

    def test_quantum_circuit_register(self):
        qc = QuantumCircuit()
        qreg1 = QuantumRegister(size=2, name="qreg1")
        creg1 = ClassicalRegister(size=2, name="creg1")

        qc.add_register(qreg1)
        qc.add_register(creg1)

        assert len(qc.qregs) == 1
        assert len(qc.cregs) == 1
        assert qc.qregs[0].name == "qreg1"
        assert qc.cregs[0].name == "creg1"
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2

        with pytest.raises(TypeError) as e:
            qc.add_register("invalid_register")

        err_msg = str(e.value)
        assert err_msg == "Invalid register type!"
