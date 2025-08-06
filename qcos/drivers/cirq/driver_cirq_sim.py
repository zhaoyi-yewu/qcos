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

from loguru import logger

import cirq
from cirq.contrib.qasm_import import circuit_from_qasm
from collections import Counter

from qcos.common.constant import Constant
from qcos.drivers.driver_base import DriverBase


class DriverCirqSim(DriverBase):
    """
    Cirq Simulator 模拟器驱动
    """
    def __init__(self):
        super().__init__()
        self.name = "cirq-sim"
        self.version = "0.0.1"
        self.enable_transpiler = False
        self.enable_circuit_aggregation = True
        self.tech_type = Constant.TECH_TYPE_GENERIC_SIMULATOR
        self.max_qubits = 30
        self._final_response = None
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3
        ]

    def init_driver(self):
        """
        Init driver
        """
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def validate_driver_configs(self):
        success = True
        err_msg = None
        return success, err_msg

    def close_driver(self):
        """
        Close driver
        """
        self.set_status(self.DRIVER_STATUS_OFFLINE)

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """
        Run job

        :param job_id: job ID
        :param num_qubits: number of qubits
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}")

        self.set_status(self.DRIVER_STATUS_BUSY)
        # create circuit form qasm code
        source_code = data["source_code"]
        circuit = circuit_from_qasm(source_code)

        # run simulation
        simulator = cirq.Simulator()
        result = simulator.run(circuit, repetitions=shots)

        # get measurement keys
        measurement_keys = list(result.measurements.keys())
        combined_results = []
        for rep in range(shots):
            state = tuple(
                int(result.measurements[key][rep][0])
                for key in measurement_keys
            )
            combined_results.append(state)

        # serialize results
        counts = Counter(combined_results)
        serializable_counts = {
            ''.join(map(str, state)): count
            for state, count in counts.items()
        }

        # store results
        self.set_results(job_id, data_index, results=serializable_counts)
        self.set_status(self.DRIVER_STATUS_ONLINE)
