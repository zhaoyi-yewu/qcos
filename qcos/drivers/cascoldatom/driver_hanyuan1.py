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

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase


logger = logging.getLogger(__name__)


# pylint: disable=duplicate-code
class DriverHanyuan1(DriverBase):
    """
    中科酷原-汉原1 中性原子驱动
    Cascoldatom Hanyuan1 driver
    CA-NAQC-20Q-A1
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.layout_method = DriverBase.LAYOUT_METHOD_CMSS_NONE
        self.enable_circuit_merge = True
        self.num_qubits = 20
        self.basis_gates = []  # TODO(zhaoyi): fill basis_gates
        self.coupling_map = []  # TODO(zhaoyi): fill coupling_map
        self.extra_configs = {}  # TODO(zhaoyi): fill extra_configs

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
        success = False
        err_msg = ""
        mandatory_keys = [
            "qubits",
            "storage_area",
            "operate_area",
            "coupler_map",
            "readout_error",
            "coupler_error",
            "closest"
        ]
        missing_keys = Library.find_missing_keys_in_dict(
            self.extra_configs, mandatory_keys)
        if missing_keys:
            err_msg = (f"Missing mandatory keys: {', '.join(missing_keys)}. "
                       f"Driver will be disabled")
        else:
            # copy configs to self.qpu_configs
            self.qpu_configs = {key: self.extra_configs[key] for key in
                                mandatory_keys if key in self.extra_configs}
            success = True
        return success, err_msg

    def close_driver(self):
        """
        Close driver
        """
        self.set_status(self.DRIVER_STATUS_OFFLINE)

    def run(self, job_id, data, data_type, shots=1):
        """
        Run job

        :param job_id: job ID
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        logger.info(f"job_id: {job_id}, data_type: {data_type}, data: {data},"
                    f" shots: {shots}")
        self.set_status(self.DRIVER_STATUS_BUSY)
        # TODO(zhaoyi): to be implemented
        results = {'00': 47, '01': 0, '10': 0, '11': 53}
        self.set_results(job_id, results=results)
        self.set_status(self.DRIVER_STATUS_ONLINE)
