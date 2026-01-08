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

import random
import time

from loguru import logger
from itertools import product
from collections import Counter

from qiskit.result import Counts
from qutip import basis, expect, tensor
from qutip_qip.circuit import CircuitSimulator, QubitCircuit
from schema import Optional

from wy_qcos.drivers.device import Device
from wy_qcos.common.constant import Constant
from wy_qcos.drivers.driver_base import DriverBase
from wy_qcos.transpiler.cmss.common.base_operation import OperationType


class DriverQutipSim(DriverBase):
    """QUTIP 模拟器驱动."""

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "QUTIP 模拟器驱动"
        self.description = "QUTIP 模拟器驱动"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_GENERIC_SIMULATOR
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = True
        self.max_qubits = 10
        self.driver_options_schema = {
            Optional("sleep"): int,
            Optional("max_qubits"): int,
        }

    def get_measurement_prob(self, final_states, num_qubit):
        """Get measurement probability.

        Args:
            final_states: final state
            num_qubit: qubit number

        Returns:
            measure results
        """
        measurement_results = {}
        for bits in product([0, 1], repeat=num_qubit):
            proj = tensor([basis(2, b) * basis(2, b).dag() for b in bits])
            prob = expect(proj, final_states)
            bit_str = "".join(map(str, bits))
            measurement_results[bit_str] = prob
        return measurement_results

    def convert_result(self, count_prob: dict, shots: int) -> Counts:
        """Convert result.

        Args:
            count_prob: final state counts
            shots: qubit shots

        Returns:
            results
        """
        random.seed(42)
        samples = random.choices(
            list(count_prob.keys()), list(count_prob.values()), k=shots
        )
        return Counts(Counter(samples))

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
        qc = QubitCircuit(N=num_qubits)
        for operation in transpile_results:
            gate_name = operation.name.upper()
            if (
                operation.operation_type
                == OperationType.DOUBLE_QUBIT_OPERATION.value
            ):
                if operation.arg_value:
                    if operation.name == "cp":
                        gate_name = "CPHASE"
                    qc.add_gate(
                        gate_name,
                        targets=operation.targets[-1],
                        controls=operation.targets[:-1],
                        arg_value=operation.arg_value[0],
                    )
                elif operation.name == "swap":
                    qc.add_gate(
                        gate_name,
                        targets=operation.targets,
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
                        if operation.name == "p":
                            gate_name = "PHASEGATE"
                        elif operation.name == "sx":
                            gate_name = "SQRTNOT"
                        qc.add_gate(
                            gate_name,
                            targets=operation.targets[-1],
                            arg_value=operation.arg_value[0],
                        )
                else:
                    qc.add_gate(gate_name, targets=operation.targets[-1])
            elif (
                operation.operation_type
                == OperationType.TRIPLE_QUBIT_OPERATION.value
            ):
                qc.add_gate(
                    "TOFFOLI",
                    targets=operation.targets[-1],
                    controls=operation.targets[:-1],
                )
        return qc

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 1)
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
        initial_state = basis(2, 0)
        for i in range(num_qubits - 1):
            initial_state = tensor(initial_state, basis(2, 0))

        sim = CircuitSimulator(qc, mode="state_vector_simulator")
        result = sim.run_statistics(state=initial_state)

        final_dm = result.final_states[0]
        state_probs = self.get_measurement_prob(final_dm, num_qubits)
        count_probs = self.convert_result(state_probs, shots)

        sleep = self.driver_options.get("sleep", None)
        if sleep:
            self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
            sleep_count = 1
            while sleep_count <= sleep:
                logger.info(f"sleep: {sleep_count} / {sleep}")
                time.sleep(1)
                sleep_count += 1

        self.set_results(job_id, data_index, results=count_probs)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")
