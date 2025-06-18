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

    def __init__(self):
        # 版本号
        self.version = "unknown"
        # 驱动状态, 不允许直接修改, 需要调用set_status修改
        self._status = self.DRIVER_STATUS_OFFLINE
        # 是否要调用transpiler
        self.enable_transpiler = True
        # transpiler类型
        self.transpiler = Constant.TRANSPILER_CMSS
        # 量子比特布局方式
        self.layout_method = DriverBase.LAYOUT_METHOD_CMSS_NONE
        # 是否允许量子电路聚合
        self.allow_circuit_merge = False
        # 量子比特数量
        self.num_qubits = 0
        # 基础门列表
        self.basis_gates = []
        # 量子比特耦合图
        self.coupling_map = []
        # 额外的配置, 一般从配置文件得来
        self.extra_configs = {}
        # 调用量子计算机/测控系统run的返回结果, 格式: {JOB_ID: {"results": RESULTS}}
        self._results = {}

    def load_driver_configs(self):
        """
        Load driver configs
        """
        self.extra_configs = Config.EXTRA_CONFIGS.get(
            self.__class__.__name__, {})

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

    def show_driver_info(self):
        """
        Show driver info
        """
        logger.info(f"[{self.__class__.__name__}]")
        logger.info(f"version: {self.version}")
        logger.info(f"status: {self._status}")
        logger.info(f"enable_transpiler: {self.enable_transpiler}")
        logger.info(f"default_transpiler: {self.transpiler}")
        logger.info(f"layout_method: {self.layout_method}")
        logger.info(f"allow_circuit_merge: {self.allow_circuit_merge}")
        logger.info(f"num_qubits: {self.num_qubits}")
        logger.info(f"basis_gates: {self.basis_gates}")
        logger.info(f"coupling_map: {self.coupling_map}")
        logger.info(f"extra_configs: {self.extra_configs}")
        logger.info("\n")

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

    def run(self, job_id, data, data_type=DATA_TYPE_GATE_SEQUENCE, shots=1):
        """
        Run job

        :params job_id: job ID
        :params data: data
        :params data_type: data type
        :params shots: shots
        """
        raise NotImplementedError(f"Driver: {self.__class__.__name__} "
                                  f"must implement method: run")

    def set_results(self, job_id, results):
        """
        Set job results

        :params job_id: job ID
        :params results: results
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
