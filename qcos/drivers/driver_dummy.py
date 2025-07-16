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
from schema import Optional, Or

from loguru import logger

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase


# 配置 Loguru
# pylint: disable=duplicate-code
logger.add(
    Constant.PREFECT_JOB_LOG_PATH,
    rotation=Constant.PREFECT_JOB_LOG_ROTATION,
    retention=Constant.PREFECT_JOB_LOG_RETENTION,
    format=Constant.PREFECT_JOB_LOG_FORMAT
)


class DriverDummy(DriverBase):
    """
    Dummy driver for test purpose
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.layout_method = DriverBase.LAYOUT_METHOD_CMSS_NEUTRAL_ATOM
        self.supported_transpiler_list = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_merge = False
        self.default_results_type = self.DATA_TYPE_GATE_SEQUENCE
        self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
        self.max_qubits = 10
        self.supported_basis_gates = []
        # pylint: disable=duplicate-code
        self.coupling_map = []
        self.extra_configs = {}

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
        # TODO(zhaoyi): load transpiler plugin, and implemented in transpiler
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            Optional("ip_address"): str,
            Optional("port"): int,
            "qpu_configs": {
                "qubits": int,
                "storage_area": [str],
                "operate_area": [str],
                "coupler_map": {str: [str]},
                "readout_error": {str: Or(float, int)},
                Optional("coupler_error"): {str: Or(float, int)},
                Optional("closest"): {str: str}
            },
            "decomposition_rule": {
                str: {
                    "gates": [list],
                    Optional("params"): [str]
                }
            }
        }
        extra_configs = self.get_extra_configs()
        _success, err_msgs = Library.validate_schema(
            extra_configs, driver_config_schema)
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        else:
            # copy configs to self.qpu_configs
            self.qpu_configs = copy.deepcopy(
                extra_configs.get("qpu_configs", {}))
            # copy configs to self.decomposition_rule
            self.decomposition_rule = copy.deepcopy(
                extra_configs.get("decomposition_rule", {}))
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
        # pylint: disable=duplicate-code
        logger.info(f"job_id: {job_id}, shots: {shots}, "
                        f"num_qubits: {num_qubits}, "
                        f"data_type: {data_type}, data: {data}")
        self.set_status(self.DRIVER_STATUS_BUSY)
        # dummy driver results
        results = [{'00': 00, '01': 1, '10': 10, '11': 11}]
        self.set_results(job_id, results=results)
        self.set_status(self.DRIVER_STATUS_ONLINE)
