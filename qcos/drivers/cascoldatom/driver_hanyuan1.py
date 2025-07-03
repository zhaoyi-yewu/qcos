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
import logging
from schema import Optional, Or

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
        self.max_qubits = 10

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
        # TODO(zhaoyi): load transpiler plugin, and implemented in transpiler
        success = True
        # check and load driver configs
        driver_config_schema = {
            "ip_address": str,
            "port": int,
            "qpu_configs": {
                "qubits": int,
                "storage_area": [str],
                "operate_area": [str],
                "coupler_map": {str: [str]},
                "readout_error": {str: Or(float, int)},
                Optional("coupler_error"): {str: Or(float, int)},
                Optional("closest"): {str: str}
            },
            Optional("decomposition_rule"): {
                str: {
                    "gates": [list],
                    Optional("params"): [str]
                }
            }
        }
        err_msg = Library.validate_schema(
            self.extra_configs, driver_config_schema)
        if err_msg:
            err_msg = f"driver config file error: {err_msg}"
            success = False
        else:
            # copy configs to self.qpu_configs
            self.qpu_configs = copy.deepcopy(
                self.extra_configs.get("qpu_configs", {}))
            # copy configs to self.decomposition_rule
            self.decomposition_rule = copy.deepcopy(
                self.extra_configs.get("decomposition_rule", {}))
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
        logger.info(f"job_id: {job_id}, shots: {shots}, "
                    f"data_type: {data_type}, data: {data}")
        self.set_status(self.DRIVER_STATUS_BUSY)
        # TODO(zhaoyi): to be implemented
        extra_configs = self.get_extra_configs()
        ip_address = extra_configs.get("ip_address", "127.0.0.1")
        port = extra_configs.get("port", 18401)
        logger.info(f"ip_address: {ip_address}, port: {port}")
        results = {"test": 1}
        self.set_results(job_id, results=results)
        self.set_status(self.DRIVER_STATUS_ONLINE)
