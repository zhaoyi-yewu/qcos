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

from qcos.common.config import Config
from qcos.common.constant import Constant


logger = logging.getLogger(__name__)


class DriverBase:
    """
    Quantum Computer base driver
    """

    # Driver status
    DRIVER_STATUS_ONLINE = "online"
    DRIVER_STATUS_OFFLINE = "offline"
    DRIVER_STATUS_BUSY = "busy"
    DRIVER_STATUS_UNKNOWN = "unknown"
    DRIVER_STATUSES = [
        DRIVER_STATUS_ONLINE,
        DRIVER_STATUS_OFFLINE,
        DRIVER_STATUS_BUSY,
        DRIVER_STATUS_UNKNOWN
    ]

    # Layout methods
    LAYOUT_METHOD_CMSS_NONE = None
    LAYOUT_METHOD_CMSS_NEUTRAL_ATOM = "cmss-neutral-atom"
    LAYOUT_METHOD_CMSS_ION_TRAP = "cmss-ion-trap"
    LAYOUT_METHODS = [
        LAYOUT_METHOD_CMSS_NONE,
        LAYOUT_METHOD_CMSS_NEUTRAL_ATOM,
        LAYOUT_METHOD_CMSS_ION_TRAP
    ]

    # Data types
    DATA_TYPE_GATE_SEQUENCE = "gate-sequence"
    DATA_TYPE_QUBO = "qubo"
    DATA_TYPES = [
        DATA_TYPE_GATE_SEQUENCE,
        DATA_TYPE_QUBO
    ]

    # Default dry-run results
    DEFAULT_DRY_RUN_RESULTS = {'00': 0}

    def __init__(self):
        # driver name
        self.driver_name = None
        # driver version
        self.version = "unknown"
        # module name
        self._module_name = None
        # class name
        self._class_name = None
        # enable this driver or not
        self.enable = True
        # driver status (TODO(zhaoyi): not used)
        self._status = self.DRIVER_STATUS_OFFLINE
        # enable transpiler or not
        self.enable_transpiler = True
        # transpiler type
        self.transpiler = Constant.TRANSPILER_CMSS
        # quantum computer technology type
        self.tech_type = None
        # layout method (TODO(zhaoyi): not used)
        self.layout_method = DriverBase.LAYOUT_METHOD_CMSS_NONE
        # enable circuit merge or not (TODO(zhaoyi): not used)
        self.enable_circuit_merge = False
        # max number of qubits
        self.max_qubits = 0
        # qpu configs
        self.qpu_configs = None
        # decomposition rule
        self.decomposition_rule = None
        # extra_configs, usually from driver config files
        self.extra_configs = {}
        # results from run(), which fetch the results from quantum computer
        # format: {JOB_ID: {"results": RESULTS}}
        self._results = {}
        # measurement results fetch mode (TODO(zhaoyi): not used)
        self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
        # default data type in run() (TODO(zhaoyi): not used)
        self.default_data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE

    def load_driver_configs(self):
        """
        Load driver configs
        """
        self.extra_configs = Config.EXTRA_CONFIGS.get(
            self.__class__.__name__, {})

    def validate_driver_configs(self):
        """
        Validate driver configs
        """
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} "
            f"must implement method: validate_driver_configs")

    def get_extra_configs(self):
        """
        Get extra configs

        :return: dict of extra configs
        """
        return self.extra_configs

    def init_driver(self):
        """
        Init driver
        """
        raise NotImplementedError(f"Driver: {self.__class__.__name__} "
                                  f"must implement method: init_driver")

    def close_driver(self):
        """
        Close driver
        """
        raise NotImplementedError(f"Driver: {self.__class__.__name__} "
                                  f"must implement method: close_driver")

    def get_driver_info(self):
        """
        Show driver info
        """
        show_list = [
            f"[{self.__class__.__name__}]",
            f"driver_name: {self.driver_name}",
            f"version: {self.version}",
            f"enable: {self.enable}",
            f"status: {self._status}",
            f"enable_transpiler: {self.enable_transpiler}",
            f"transpiler: {self.transpiler}",
            f"layout_method: {self.layout_method}",
            f"enable_circuit_merge: {self.enable_circuit_merge}",
            f"max_qubits: {self.max_qubits}",
            f"qpu_configs: {self.qpu_configs}",
            f"decomposition_rule: {self.decomposition_rule}",
            f"extra_configs: {self.extra_configs}"
        ]
        return "\n".join(show_list)

    def set_name(self, driver_name):
        """
        Set driver name

        :param driver_name: driver_name
        """
        self.driver_name = driver_name

    def get_name(self):
        """
        Get driver name

        :return: driver name
        """
        return self.driver_name

    def set_module_name(self, module_name):
        """
        Set module name

        :param module_name: module name
        """
        self._module_name = module_name

    def get_module_name(self):
        """
        Get module name

        :return: module name
        """
        return self._module_name

    def set_class_name(self, class_name):
        """
        Set class name

        :param class_name: class name
        """
        self._class_name = class_name

    def get_class_name(self):
        """
        Get class name

        :return: class name
        """
        return self._class_name

    def set_status(self, status):
        """
        Set driver status

        :param status: driver status
        """
        if status not in self.DRIVER_STATUSES:
            logger.warning(f"Failed to set driver status: '{status}'."
                           f"valid statuses: {', '.join(self.DRIVER_STATUSES)}"
                           )
            return
        self._status = status

    def get_status(self):
        """
        Get driver status
        """
        return self._status

    def get_transpiler(self):
        """
        Get transpiler
        """
        if self.enable_transpiler:
            return self.transpiler
        return None

    def get_qpu_configs(self):
        """
        Get qpu configs
        """
        return self.qpu_configs

    def get_decomposition_rule(self):
        """
        Get decomposition rule
        """
        return self.decomposition_rule

    def run(self, job_id, data, data_type=DATA_TYPE_GATE_SEQUENCE, shots=1):
        """
        Run job

        :param job_id: job ID
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        raise NotImplementedError(f"Driver: {self.__class__.__name__} "
                                  f"must implement method: run")

    def dry_run(self, job_id, data, data_type=DATA_TYPE_GATE_SEQUENCE,
                shots=1):
        """
        Dry-run job

        :param job_id: job ID
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        logger.info(f"Dry-run: job_id: {job_id}, shots: {shots}, "
                    f"data_type: {data_type}, data: {data}")
        self.set_results(job_id, results=DriverBase.DEFAULT_DRY_RUN_RESULTS)

    def set_results(self, job_id, results):
        """
        Set job results

        :param job_id: job ID
        :param results: results
        """
        self._results[job_id] = results

    def get_results(self, job_id=None):
        """
        Get results

        :param job_id: job ID
        """
        if job_id:
            return self._results.get(job_id, None)
        return self._results

    def get_default_data_type(self):
        """
        Get default data type

        :return: default data type
        """
        return self.default_data_type

    def set_max_qubits(self, max_qubits):
        """
        Set max qubits

        :param max_qubits: max qubits
        """
        self.max_qubits = max_qubits

    def get_max_qubits(self):
        """
        Get max qubits

        :return: max qubits
        """
        return self.max_qubits
