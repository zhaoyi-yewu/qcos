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


from loguru import logger

from qutip import basis, tensor, sigmax, sigmay, sigmaz, Qobj
from qutip_qip.circuit import CircuitSimulator
from schema import Optional

from wy_qcos.device.device import Device
from wy_qcos.common.constant import Constant
from wy_qcos.common.cmss.base_operation import OperationType
from .driver_qutip_sim import DriverQutipSim
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import (
    optimize,
)
from wy_qcos.transpiler.cmss.decomposer.kak_decomposer import KAKDecomposer

Z = sigmaz()
Y = sigmay()
X = sigmax()


def ashn(arg_value):
    """Ashn gate.

    Args:
        arg_value: arg_value for the gate.

    Returns:
        the ashn gate Qobj
    """
    a = arg_value[0]
    b = arg_value[1]
    c = arg_value[2]
    H = a * tensor(X, X) + b * tensor(Y, Y) + c * tensor(Z, Z)
    U = (1j * H).expm()
    return Qobj(U, dims=[[2, 2], [2, 2]])


class DriverQutipAshnSim(DriverQutipSim):
    """QUTIP 模拟器驱动(支持ASHN)."""

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "QUTIP-模拟器驱动(支持ASHN)"
        self.description = "QUTIP-模拟器驱动(支持ASHN)"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_GENERIC_SIMULATOR
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CH,
            Constant.TWO_QUBIT_GATE_CRX,
            Constant.TWO_QUBIT_GATE_CRY,
            Constant.TWO_QUBIT_GATE_CRZ,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CY,
            Constant.TWO_QUBIT_GATE_CZ,
            Constant.TWO_QUBIT_GATE_SWAP,
            Constant.TWO_QUBIT_GATE_ISWAP,
            Constant.TWO_QUBIT_GATE_CP,
            Constant.TWO_QUBIT_GATE_CS,
            Constant.TWO_QUBIT_GATE_CSDG,
            Constant.TWO_QUBIT_GATE_CU,
            Constant.TWO_QUBIT_GATE_RXX,
            Constant.TWO_QUBIT_GATE_RZZ,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = True
        self.max_qubits = 10
        self.driver_options_schema.update({
            Optional("max_qubits"): int,
        })

    def run(
        self,
        job_id,
        num_qubits,
        data,
        data_type,
        shots=1,
        qec_options=None,
    ):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 1)
            qec_options: qec options
        """
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        transpile_results = data["transpile_results"]
        basis_gate_list = []
        kak_decomposer = KAKDecomposer()
        for gate in transpile_results:
            if (
                gate.operation_type
                == OperationType.DOUBLE_QUBIT_OPERATION.value
            ):
                kak_decomposer.set_matrix(gate.to_matrix())
                kak_decomposer.run()
                result = kak_decomposer.get_decompose_result(gate.targets)
                basis_gate_list.extend(result)
            else:
                basis_gate_list.append(gate)
        basis_gate_list = optimize(
            basis_gate_list,
            opt_level=3,
            basis_gates=set(self.supported_basis_gates),
        )
        logger.info(f"converted circuit{basis_gate_list}")
        qc = self.convert_gates(basis_gate_list, num_qubits)
        qc.user_gates["ASHN"] = ashn
        initial_state = basis(2, 0)
        for i in range(num_qubits - 1):
            initial_state = tensor(initial_state, basis(2, 0))

        sim = CircuitSimulator(qc, mode="state_vector_simulator")
        result = sim.run_statistics(state=initial_state)
        states = result.get_final_states()
        probabilities = result.get_probabilities()
        count_probs = self.convert_result(zip(states, probabilities), shots)

        self.set_results(
            job_id,
            data_index,
            results=count_probs,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
