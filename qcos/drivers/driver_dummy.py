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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import logging

from common.constant import Constant
from drivers.driver_base import DriverBase


logger = logging.getLogger(__name__)


class DriverDummy(DriverBase):
    """
    Dummy driver for test purpose
    """

    def __init__(self):
        super(DriverDummy, self).__init__()
        self.version = "0.0.1"
        self.status = self.DRIVER_STATUS_ONLINE
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.layout_method = DriverBase.LAYOUT_METHOD_CMSS_NEUTRAL_ATOM
        self.allow_circuit_merge = True
        self.num_qubits = 20
        self.basis_gates = []
        self.coupling_map = []
        self.extra_configs = {}

    def init_driver(self):
        """
        Init driver
        """
        pass

    def close_driver(self):
        """
        Close driver
        """
        pass

    def run(self, job_id, data, data_type, shots=1):
        """
        Run job

        :params job_id: job ID
        :params data: data
        :params data_type: data type
        :params shots: shots
        """
        logger.info(f"job_id: {job_id}, data_type: {data_type}, data: {data},"
                    f" shots: {shots}")
