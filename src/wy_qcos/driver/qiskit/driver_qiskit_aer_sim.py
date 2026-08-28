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

import json
import sys

from loguru import logger
from qiskit import qasm2
from qiskit_aer import AerSimulator

from wy_qcos.common.constant import Constant
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_gate_base import DriverGateBase

MAX_IDEAL_SIMULATOR_QUBITS = 10


def simulate_qasm_probabilities(source_code):
    """Calculate ideal probabilities with the Qiskit Aer backend.

    Final measurements are removed before state-vector simulation so the
    returned dictionary contains exact probabilities instead of sampled
    counts.
    """
    if not isinstance(source_code, str) or not source_code.strip():
        raise ValueError("source_code must be a non-empty OpenQASM string")

    try:
        circuit = qasm2.loads(source_code)
        if circuit.num_qubits > MAX_IDEAL_SIMULATOR_QUBITS:
            raise ValueError(
                f"ideal simulation supports at most "
                f"{MAX_IDEAL_SIMULATOR_QUBITS} qubits"
            )
        circuit = circuit.remove_final_measurements(inplace=False)
        circuit.save_statevector()
        simulator = AerSimulator(method="statevector")
        result = simulator.run(circuit).result()
        statevector = result.get_statevector(circuit)
    except Exception as error:
        raise ValueError(
            f"unable to simulate OpenQASM circuit with Qiskit Aer: {error}"
        ) from error

    probabilities = {}
    for index, amplitude in enumerate(statevector):
        probability = float(abs(amplitude) ** 2)
        if probability > 0:
            state = format(index, f"0{circuit.num_qubits}b")
            probabilities[state] = probability
    return probabilities


def _run_ideal_simulation_cli():
    """Run ideal simulation over a stdin/stdout JSON subprocess protocol."""
    try:
        probabilities = simulate_qasm_probabilities(sys.stdin.read())
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print(json.dumps(probabilities, sort_keys=True))
    return 0


class DriverQiskitAerSim(DriverGateBase):
    """Qiskit Aer 模拟器驱动."""

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "Qiskit Aer 模拟器驱动"
        self.description = "Qiskit Aer 模拟器驱动"
        self.transpiler = Constant.TRANSPILER_QISKIT
        self.tech_type = Constant.TECH_TYPE_GENERIC_SIMULATOR
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_QISKIT]
        self.enable_circuit_aggregation = True
        self.max_qubits = 30
        self._final_response = None

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
        simulator = AerSimulator()
        results_obj = simulator.run(transpile_results, shots=shots).result()
        results = results_obj.get_counts()

        self.set_results(
            job_id,
            data_index,
            results=results,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--ideal-probabilities"]:
        sys.exit(_run_ideal_simulation_cli())
    print("unsupported command", file=sys.stderr)
    sys.exit(2)
