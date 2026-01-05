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

from loguru import logger
from qiskit_aer import AerSimulator

from wy_qcos.common.constant import Constant
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase


class DriverQiskitAerSim(DriverBase):
    """Qiskit Aer 模拟器驱动."""

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "Qiskit Aer 模拟器驱动"
        self.description = "Qiskit Aer 模拟器驱动"
        self.enable_transpiler = True
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
        simulator = AerSimulator()
        result = simulator.run(transpile_results, shots=shots).result()

        self.set_results(job_id, data_index, results=result.get_counts())
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")
