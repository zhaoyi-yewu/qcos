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

import random

from loguru import logger

from qcos.common.constant import Constant
from qcos.drivers.device import Device
from qcos.drivers.driver_base import DriverBase


class DriverQuboBase(DriverBase):
    """QUBO驱动基类

    QUBO Base driver
    """

    def __init__(self):
        super().__init__()
        self.enable_transpiler = False
        self.tech_type = Constant.TECH_TYPE_PHOTON
        self.default_data_type = DriverBase.DATA_TYPE_QUBO
        self.supported_code_types = [Constant.CODE_TYPE_QUBO]

    def init_driver(self):
        """Init driver"""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def validate_driver_configs(self, configs):
        """Validate driver configs

        Args:
            configs: configs dictionary

        Returns:
            success, err_msg
        """
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} "
            f"must implement method: validate_driver_configs"
        )

    def close_driver(self):
        """Close driver"""

    def fetch_configs(self):
        """
        Fetch configs

        Returns:
            remote transpiler configs
        """

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """Run job

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 1)
        """
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} "
            f"must implement method: validate_driver_configs"
        )

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def get_fake_results(self, num_qubits, shots, data):
        """Get fake results

        Args:
            num_qubits: number of qubits
            shots: number of shots
            data: source data
        """
        results = []
        for i in range(10):  # return 10 best solutions is enough
            code_length = len(data.get("source_code", [])[0])
            result = {
                "result": i + 1,
                "quboValue": -112,
                "maxcutValue": 28.0,
                "solutionVector": [
                    random.randint(0, 1) for _ in range(code_length)
                ],
            }
            results.append(result)
        return results
