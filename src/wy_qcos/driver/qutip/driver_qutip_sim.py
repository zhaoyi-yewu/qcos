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

import time
import numpy as np
from loguru import logger

from qutip import basis, tensor, sigmax, sigmay, sigmaz, Qobj
from qutip_qip.circuit import CircuitSimulator, QubitCircuit
from schema import Optional

from wy_qcos.device.device import Device
from wy_qcos.common.constant import Constant
from wy_qcos.driver.driver_gate_base import DriverGateBase
from wy_qcos.common.cmss.base_operation import OperationType

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


class DriverQutipSim(DriverGateBase):
    """QUTIP 模拟器驱动."""

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "QUTIP 模拟器驱动"
        self.description = "QUTIP 模拟器驱动"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_GENERIC_SIMULATOR
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_ASHN,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = True
        self.max_qubits = 10
        self.driver_options_schema = {
            Optional("sleep"): int,
            Optional("max_qubits"): int,
        }

    def convert_result(self, results, shots):
        """Convert result.

        Args:
            results: [(state, probability), ...]
            shots: shots number

        Returns:
            final results
        """
        counts_dict = {}

        for state, prob in results:
            vec = state.full().flatten()
            n_qubits = int(np.log2(len(vec)))
            nonzero_idx = np.where(np.abs(vec) > 1e-10)[0]

            for idx in nonzero_idx:
                bitstring = format(idx, f"0{n_qubits}b")
                count = np.abs(vec[idx]) ** 2 * prob * shots
                counts_dict[bitstring] = counts_dict.get(bitstring, 0) + count

            counts_dict = {s: int(round(c)) for s, c in counts_dict.items()}
            if sum(counts_dict.values()) != shots:
                diff = shots - sum(counts_dict.values())
                max_state = max(counts_dict, key=counts_dict.get)
                counts_dict[max_state] += diff

        return counts_dict

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success, err_msgs
        """
        success = True
        err_msg = None

        return success, err_msg

    def close_driver(self):
        """Close driver."""

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """

    def update_driver_options(self, driver_options):
        """Update driver options.

        Args:
            driver_options: new driver options
        """
        self.driver_options.update(driver_options)
        max_qubits_value = self.driver_options.get("max_qubits")
        if max_qubits_value is not None:
            self.set_max_qubits(max_qubits_value)

    def convert_gates(self, transpile_results, num_qubits):
        """Fetch configs.

        Args:
            transpile_results: gates list
            num_qubits: number of qubits

        Returns:
            qc
        """
        qc = QubitCircuit(N=num_qubits, num_cbits=num_qubits)
        for operation in transpile_results:
            gate_name = operation.name.upper()
            if (
                operation.operation_type
                == OperationType.DOUBLE_QUBIT_OPERATION.value
            ):
                if operation.arg_value:
                    qc.add_gate(
                        gate_name,
                        targets=operation.targets,
                        arg_value=operation.arg_value[0],
                    )
                else:
                    qc.add_gate(
                        gate_name,
                        targets=operation.targets[-1],
                        controls=operation.targets[:-1],
                    )
            elif (
                operation.operation_type
                == OperationType.SINGLE_QUBIT_OPERATION.value
            ):
                if operation.arg_value:
                    if operation.name == "u3":
                        qc.add_gate(
                            "QASMU",
                            targets=operation.targets[-1],
                            arg_value=operation.arg_value,
                        )
                    else:
                        qc.add_gate(
                            gate_name,
                            targets=operation.targets[-1],
                            arg_value=operation.arg_value[0],
                        )
                else:
                    qc.add_gate(gate_name, targets=operation.targets[-1])
        for i in range(num_qubits):
            qc.add_measurement(f"M{i}", targets=[i], classical_store=i)
        return qc

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
        qc = self.convert_gates(transpile_results, num_qubits)
        qc.user_gates["ASHN"] = ashn
        initial_state = basis(2, 0)
        for i in range(num_qubits - 1):
            initial_state = tensor(initial_state, basis(2, 0))

        sim = CircuitSimulator(qc, mode="state_vector_simulator")
        result = sim.run_statistics(state=initial_state)
        states = result.get_final_states()
        probabilities = result.get_probabilities()
        count_probs = self.convert_result(zip(states, probabilities), shots)

        sleep = self.driver_options.get("sleep", None)
        if sleep:
            self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
            sleep_count = 1
            while sleep_count <= sleep:
                logger.info(f"sleep: {sleep_count} / {sleep}")
                time.sleep(1)
                sleep_count += 1

        self.set_results(
            job_id,
            data_index,
            results=count_probs,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")
