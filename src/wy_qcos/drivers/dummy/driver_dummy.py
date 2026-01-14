#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
import time

from loguru import logger
from schema import Optional, Or

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase


class DriverDummy(DriverBase):
    """空载测试驱动.

    Dummy neutral-atom driver for test purpose
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "空载测试驱动(中性原子)"
        self.description = "空载测试驱动(中性原子)"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = True
        self.default_results_type = self.DATA_TYPE_GATE_SEQUENCE
        self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
        self.max_qubits = 10
        # pylint: disable=duplicate-code
        self.extra_configs = {}
        self.driver_options_schema = {
            Optional("sleep"): int,
            Optional("enable_wirecut"): bool,
            Optional("max_qubits"): int,
        }

    def init_driver(self):
        """Init driver."""
        # pylint: disable=duplicate-code
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success, err_msgs
        """
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            Optional("ip_address"): str,
            Optional("port"): int,
            "transpiler": {
                "qpu_configs": {
                    "qubits": int,
                    "storage_area": [str],
                    "operate_area": [str],
                    "coupler_map": {str: [str]},
                    "readout_error": {str: Or(float, int)},
                    Optional("coupler_error"): {str: Or(float, int)},
                    Optional("closest"): {str: str},
                },
                "decomposition_rule": {
                    str: {"gates": [list], Optional("params"): [str]}
                },
            },
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"device config file error: {_err_msg}"
            success = False
        else:
            # copy configs to self.qpu_configs
            self.qpu_configs = copy.deepcopy(configs.get("qpu_configs", {}))
            # copy configs to self.decomposition_rule
            self.decomposition_rule = copy.deepcopy(
                configs.get("decomposition_rule", {})
            )
        return success, err_msg

    def close_driver(self):
        """Close driver."""

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 1)
        """
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # handle extra_configs
        sleep = self.driver_options.get("sleep", None)
        if sleep:
            self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
            sleep_count = 1
            while sleep_count <= sleep:
                logger.info(f"sleep: {sleep_count} / {sleep}")
                time.sleep(1)
                sleep_count += 1

        # dummy driver results
        result = self.get_fake_results(num_qubits, shots, data)
        self.set_results(job_id, data_index, results=result)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def update_driver_options(self, driver_options):
        """Update driver options.

        Args:
            driver_options: new driver options
        """
        self.driver_options.update(driver_options)
        max_qubits_value = self.driver_options.get("max_qubits")
        if max_qubits_value is not None:
            self.set_max_qubits(max_qubits_value)
