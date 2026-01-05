#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import re

import numpy as np
import uqc_client
from loguru import logger
from uqc_client.uqc import uqc_config

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase


class DriverUQCMatrix2(DriverBase):
    """幺正量子 UQC-Matrix2 离子阱驱动.

    UQC-Matrix2 driver
    """

    task_time_out = 3600
    task_status_success = "SUCCESS"

    def __init__(self):
        super().__init__()
        self.token = None
        self.uqc_host = None
        self.uqc_port = None
        self.backend_device_name = "Matrix2"
        self.version = "0.0.1"
        self.alias_name = "幺正量子 UQC-Matrix2 离子阱驱动"
        self.description = "幺正量子 UQC-Matrix2 离子阱驱动"
        self.enable_transpiler = False
        self.tech_type = Constant.TECH_TYPE_ION_TRAP
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_RZZ,
        ]
        self.enable_circuit_aggregation = False
        self.max_qubits = 5
        self.default_data_type = DriverBase.DATA_TYPE_QASM3
        self.supported_code_types = [DriverBase.DATA_TYPE_QASM3]

        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_VALIDATING: 5,
            self.TASK_STAGE_SUBMIT_TASK: 10,
            self.TASK_STAGE_WAIT_TASK: 20,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }
        self._uqc = None

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success or fail, err_msg
        """
        success = True
        err_msg = None

        driver_config_schema = {
            "uqc_host": str,
            "uqc_port": int,
            "password_token": str,
            "backend_device_name": str,
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        return success, err_msg

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver."""

    def fetch_configs(self):
        """Fetch configs."""
        extra_configs = self.get_configs()
        self.token = extra_configs.get("password_token", "")
        self.uqc_host = extra_configs.get("uqc_host", "127.0.0.1")
        self.uqc_port = extra_configs.get("uqc_port", 5001)
        self.backend_device_name = extra_configs.get("backend_device_name", "")
        try:
            uqc_config.SERVER_HOST = self.uqc_host
            uqc_config.SERVER_PORT = self.uqc_port
            uqc_config.DEFAULT_TASKS_FILE_PATH = "/dev/null"
            self._uqc = uqc_client.UQC(self.token)
        except Exception as e:
            raise ValueError(f"UQC exception: {e}") from e

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def run(self, job_id, num_qubits, data, data_type, shots=100):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 100)
        """
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )
        if num_qubits is None and self.default_data_type == "qasm3":
            pattern = r"qubit\s*\[\s*(\d+)\s*\]"
            matches = re.findall(pattern, data["source_code"], re.IGNORECASE)
            num_qubits = sum(int(match) for match in matches)

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # 1. Validate shots
        logger.info("1. validate shots")
        self.set_progress_by_task(self.TASK_STAGE_VALIDATING)
        self.is_valid_shots(shots)

        # 2. Submit task
        logger.info("2. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        task_id = self._uqc.submit_task(
            data["source_code"], self.backend_device_name, shots
        )

        # 3. Wait for task_status success
        logger.info("3. wait for task_status is success")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, _, _ = Library.loop_with_timeout(
            self.check_task_status,
            self.task_time_out,
            5,
            task_id,
            expect_task_status=[self.task_status_success],
        )
        if not success:
            raise ValueError(f"Failed to get task results [{job_id}]")

        # 4. Get task results
        logger.info("4. get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, _results = self.get_task_results(task_id)
        if not success:
            raise ValueError(f"failed to get task {task_id} result")

        # 5. Normalize results
        results = _results
        logger.info("5. normalize results")
        if self.backend_device_name == "qiskit-sim":
            results = self.convert_results(
                _results[0]["results"][0]["data"]["counts"],
                num_qubits,
            )
        if self.backend_device_name == "Matrix2":
            results = self.normalize_task_results(
                _results[0]["datasets"]["computational_basis_histogram"],
                num_qubits,
                shots,
            )
        self.set_results(job_id, data_index, results=results)

        # 6. Save results and set driver status to ONLINE
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def check_task_status(self, task_id, expect_task_status):
        """Check task status.

        Args:
            task_id: task id
            expect_task_status: expect task status

        Returns:
            success or fail, err_msg, status
        """
        status = self._uqc.get_task_status(task_id)
        if status in expect_task_status:
            return True, None, status
        err_msg = (
            "Task status is not in "
            f"{', '.join(map(str, expect_task_status))}, "
            f"and current status: {status}"
        )
        return False, err_msg, None

    def get_task_results(self, task_id):
        """Get task results.

        Args:
            task_id: task id

        Returns:
            success or fail, task results
        """
        resp_json = self._uqc.get_task_result(task_id)
        if resp_json is None:
            return False, None
        return True, resp_json

    def normalize_task_results(self, results, num_qubits, shots):
        """Normalize task results.

        Args:
            results: task results
            num_qubits: number of qubits
            shots: number of shots

        Returns:
            normalized task results
        """
        dict_result = {}

        indices = np.array([x[0] for x in results], dtype=int)
        signal = np.array([x[1] for x in results])

        baseline = np.median(signal)
        baseline = min(baseline, 0)
        signal_calibrated = signal - baseline

        weight = np.abs(signal_calibrated)
        weight_normalized = weight / np.sum(weight)
        total_measurements = shots
        counts = np.round(weight_normalized * total_measurements).astype(int)

        counts_sum = np.sum(counts)
        if counts_sum != total_measurements:
            diff = total_measurements - counts_sum
            max_count_idx = np.argmax(counts)
            counts[max_count_idx] += diff

        result = np.column_stack((indices, counts))
        for key, value in result:
            if value == 0:
                continue
            keys = f"{bin(key)[2:].zfill(num_qubits)}"
            dict_result[keys] = int(value)
        return dict_result

    def convert_results(self, results, num_qubits):
        """Valid shots.

        Args:
            results: task results
            num_qubits: number of qubits

        Returns:
            converted task results
        """
        dict_result = {}
        for key, value in results.items():
            decimal_num = int(key, 16)
            bin_str = bin(decimal_num)
            dict_result[bin_str[2:].zfill(num_qubits)] = value
        return dict_result

    def is_valid_shots(self, shots):
        """Valid shots.

        Args:
            shots: number of shots
        """
        if not isinstance(shots, int):
            raise ValueError("shots must be integer")
        if shots % 100 != 0:
            raise ValueError("shots must be a multiple of 100")
        if shots > 1000:
            raise ValueError("shots must in [100,1000]")
