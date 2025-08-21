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

from qcos.common.constant import Constant
from qcos.drivers.driver_base import DriverBase


class DriverPassthrough(DriverBase):
    """
    直通测试驱动
    Passthrough driver for test purpose
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.name = "passthrough"
        self.alias_name = "测试空载直通驱动"
        self.enable = False
        self.enable_transpiler = False
        self.tech_type = Constant.TECH_TYPE_NONE
        self.supported_code_types = [
            Constant.CODE_TYPE_QUBO
        ]

    def init_driver(self):
        """
        Init driver
        """
        # pylint: disable=duplicate-code
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def validate_driver_configs(self):
        """
        Validate driver configurations

        :return bool: True if successful, False otherwise
        :return err_msg: error message
        """
        return True, ""

    def close_driver(self):
        """
        Close driver
        """
        # pylint: disable=duplicate-code
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
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}")

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_status(self.DRIVER_STATUS_BUSY)
        result = self.get_fake_results(num_qubits, shots, data)
        self.set_results(job_id, data_index, results=result)
        self.set_status(self.DRIVER_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)
