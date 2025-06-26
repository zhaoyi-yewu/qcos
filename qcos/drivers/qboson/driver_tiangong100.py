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

import logging

from qcos.drivers.driver_base import DriverBase


logger = logging.getLogger(__name__)


class DriverTiangong100(DriverBase):
    """
    玻色量子-天工1000 光量子伊辛机驱动
    Qboson Tiangong1000 driver
    CQ-D-100
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.enable_transpiler = False
        self.enable_circuit_merge = False
        self.max_qubits = 100
        self.extra_configs = {}  # TODO(zhaoyi): 填入extra_configs值

    def init_driver(self):
        """
        Init driver
        """
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

    def run(self, job_id, data, data_type, shots=1):
        """
        Run job

        :param job_id: job ID
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        # pylint: disable=duplicate-code
        logger.info(f"job_id: {job_id}, shots: {shots}, "
                    f"data_type: {data_type}, data: {data}")
        self.set_status(self.DRIVER_STATUS_BUSY)
        # TODO(zhaoyi): to be implemented
        results = {}
        self.set_results(job_id, results=results)
        self.set_status(self.DRIVER_STATUS_ONLINE)
