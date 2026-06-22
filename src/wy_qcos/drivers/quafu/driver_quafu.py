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

from loguru import logger
from quark import Task

from wy_qcos.common.cmss.qasm_converter import QasmConverter
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase


class DriverQuafu(DriverBase):
    """北京量子院 夸父-Dongling 超导驱动.

    Dongling driver
    https://quafu-sqc.baqis.ac.cn/
    """

    task_status_success = "Finished"

    def __init__(self):
        super().__init__()
        self.tmgr = None
        self.token = None
        self.version = "0.0.1"
        self.alias_name = "北京量子院 夸父-Dongling 超导驱动"
        self.description = "北京量子院 夸父-Dongling 超导驱动"
        self.backend_name = [
            "Baihua",
            "Yudu",
            "Dongling",
            "Honglu",
            "Baiwang",
            "Ling",
            "Shenglian",
        ]
        self.chip_name = None
        self.transpiler = Constant.TRANSPILER_DUMMY
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.enable_circuit_aggregation = False
        self.max_qubits = 84
        self.default_data_type = DriverBase.DATA_TYPE_QASM2
        self.supported_code_types = [Constant.CODE_TYPE_QASM]
        self.supported_transpilers = [Constant.TRANSPILER_DUMMY]

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver."""

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success or fail, err_msg
        """
        success = True
        err_msg = None

        driver_config_schema = copy.deepcopy(self.default_driver_config_schema)
        driver_config_schema.update({
            "token": str,
            "chip_name": str,
            "url": str,
            "transpiler": {
                "qpu_configs": {
                    "qubits": int,
                    "coupler_map": {str: [str]},
                }
            },
        })
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        else:
            self.max_job_wait_time = configs.get(
                "max_job_wait_time", Constant.DEFAULT_JOB_WAIT_TIME
            )
            self.job_query_interval = configs.get(
                "job_query_interval", Constant.DEFAULT_JOB_QUERY_INTERVAL
            )

        return success, err_msg

    def fetch_configs(self):
        """Fetch configs."""
        extra_configs = self.get_configs()
        self.chip_name = extra_configs.get("chip_name", "")
        self.token = extra_configs.get("token", "")
        url = extra_configs.get("url", "")
        if url:
            Task.URL = url
        self.tmgr = Task(self.token)

    def convert_code(self, num_qubits: int, src_code: str, transpile_results):
        """Convert code.

        Args:
            num_qubits: num qubits
            src_code: src code
            transpile_results: transpile results

        Returns:
            converted code
        """
        if transpile_results is None or len(transpile_results) == 0:
            return src_code

        if not isinstance(transpile_results, list):
            return src_code

        for op in transpile_results:
            if not isinstance(op, BaseOperation):
                return src_code

        circ = QuantumCircuit(num_qubits)
        circ.append_operations(transpile_results)
        converter = QasmConverter(circ)
        qasm_code = converter.to_qasm2()
        return qasm_code

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        # TODO(jidalong) mock data currently
        device_running_info = {"status": "online"}
        return device_running_info

    def run(
        self, job_id, num_qubits, data, data_type, shots=1, qec_options=None
    ):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 1)
            qec_options: qec options
        """
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )
        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # 1. Convert code
        logger.info("1. convert code")
        self.set_progress_by_task(self.TASK_STAGE_VALIDATING)
        src_code = data["source_code"]
        transpile_results = data["transpile_results"]
        final_code = self.convert_code(num_qubits, src_code, transpile_results)
        logger.info(f"after converting, code is: {final_code}")

        # 2. Submit task
        logger.info("2. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        task = {
            "chip": self.chip_name,  # chip name
            "name": job_id,  # task name
            "circuit": final_code,  # circuit written in OpenQASM2.0
            "shots": shots,  # an integer multiple of 1024
            "options": {
                "compiler": "quarkcircuit",  # defaults to 'quarkcircuit'
                "correct": False,  # readout error correction
                "open_dd": None,  # dynamical decoupling, defaults to None
                "target_qubits": [],  # [0, 1]
            },
        }
        task_id = self.submit_task(task)

        # 3. Wait for task_status success
        logger.info("3. wait for task_status is success")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, _, _ = Library.loop_with_timeout(
            self.check_task_status,
            self.max_job_wait_time,
            self.job_query_interval,
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
        logger.info("5. normalize results")
        results = self.convert_results(_results)
        self.set_results(job_id, data_index, results=results)

        # 6. Save results and set driver status to ONLINE
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def submit_task(self, task_info):
        """Submit task.

        Args:
            task_info: task info

        Returns:
            success, error message, task_id
        """
        tid = self.tmgr.run(task_info)
        return tid

    def check_task_status(self, task_id, expect_task_status):
        """Check task status.

        Args:
            task_id: task id
            expect_task_status: expect task status

        Returns:
            success or fail, err_msg, status
        """
        _, result = self.get_task_results(task_id)
        if result:
            status = result["status"]
        else:
            status = None
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
            success, error message, response
        """
        result = self.tmgr.result(task_id)
        if result is None:
            return False, None
        return True, result

    def convert_results(self, results):
        """Convert results.

        Args:
            results: task results

        Returns:
            converted task results
        """
        dict_result = results["count"]
        return dict_result
