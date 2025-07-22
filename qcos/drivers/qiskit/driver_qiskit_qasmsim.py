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

import copy
from loguru import logger
import time

from qiskit_aer import QasmSimulator
from schema import Optional, Or

from jsonrpcclient import request

from qcos.common.constant import Constant, HttpMethod
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase

# 配置 Loguru
logger.add(
    Constant.PREFECT_JOB_LOG_PATH,
    rotation=Constant.PREFECT_JOB_LOG_ROTATION,
    retention=Constant.PREFECT_JOB_LOG_RETENTION,
    format=Constant.PREFECT_JOB_LOG_FORMAT
)


class DriverQiskitQasmSim(DriverBase):
    """
    Qiskit Qasm 模拟器驱动
    """

    verbose = False

    def __init__(self):
        super().__init__()
        self.name = "qiskit_qasm"
        self.version = "0.0.1"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_QISKIT
        self.supported_basis_gates = [Constant.SQ_GATE_RX, Constant.SQ_GATE_RY,
                                      Constant.SQ_GATE_RZ, Constant.DQ_GATE_CX]
        self.supported_transpiler_list = [Constant.TRANSPILER_QISKIT]
        self.enable_circuit_merge = True
        self.max_qubits = 30
        self._final_response = None

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
        logger.info(f"job_id: {job_id}, shots: {shots}, "
                    f"num_qubits: {num_qubits}, "
                    f"data_type: {data_type}, data: {data}")
        self.set_status(self.DRIVER_STATUS_BUSY)

        simulator = QasmSimulator()
        result = simulator.run(data, shots=shots).result()
        print("测量结果:", result.get_counts())

        self.set_results(job_id, results=result.get_counts())
        self.set_status(self.DRIVER_STATUS_ONLINE)
