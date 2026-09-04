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


from loguru import logger
from quark import Task
from schema import And, Optional, Schema

from wy_qcos.common.cmss.qasm_converter import QasmConverter
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.driver_gate_base import DriverGateBase


class DriverQuafu(DriverGateBase):
    """北京量子院 夸父-Dongling 超导驱动.

    Dongling driver
    https://quafu-sqc.baqis.ac.cn/
    """

    task_status_success = "Finished"
    task_status_failure = frozenset({"Failed", "Canceled", "Cancelled"})
    shots_per_repeat = 1024

    def __init__(self):
        super().__init__()
        self.tmgr = None
        self.token = None
        self.version = "0.0.1"
        self.alias_name = "北京量子院-夸父-Dongling 超导驱动"
        self.description = "北京量子院-夸父-Dongling 超导驱动"
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
        self.transpiler = Constant.TRANSPILER_CMSS
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
        self.supported_transpilers = [
            Constant.TRANSPILER_DUMMY,
            Constant.TRANSPILER_CMSS,
            Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS,
        ]
        # input constrains for scheduling
        self.input_constrains["job_shots"] = Schema(
            And(
                int,
                lambda x: 1024 <= x <= 102400,  # min: 1024, max: 102400
                lambda x: x % 1024 == 0,  # must be multiple of 1024
            )
        )
        # enable_mapping: true, false are all allowed
        self.transpiler_options_schema["enable_mapping"] = (
            Optional("enable_mapping", default=False),
            bool,
        )

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

        driver_config_schema = {
            "token": str,
            "chip_name": str,
            "url": str,
            "transpiler": {
                "qpu_configs": {
                    "qubits": int,
                    "coupler_map": {str: [str]},
                }
            },
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema, ignore_extra_keys=True
        )
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False

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
        device_running_info = {"status": Device.DEVICE_STATUS_ONLINE}
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
        # QuarkStudio accepts a repeat count and converts each repeat to 1024
        # shots.  A "shots" key inside the task dictionary is ignored.
        repeat = self.shots_to_repeat(shots)

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
            "options": {
                "compiler": "quarkcircuit",  # defaults to 'quarkcircuit'
                "correct": False,  # readout error correction
                "open_dd": None,  # dynamical decoupling, defaults to None
                "target_qubits": [],  # [0, 1]
            },
        }
        task_id = self.submit_task(task, repeat=repeat)

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
        self.set_results(
            job_id,
            data_index,
            results=results,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )

        # 6. Save results and set driver status to ONLINE
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    @classmethod
    def shots_to_repeat(cls, shots):
        """Convert a Quafu shot count to a QuarkStudio repeat count."""
        if isinstance(shots, bool) or not isinstance(shots, int):
            raise ValueError("Quafu shots must be an integer")

        repeat, remainder = divmod(shots, cls.shots_per_repeat)
        if repeat < 1 or remainder:
            raise ValueError(
                "Quafu shots must be a positive multiple of "
                f"{cls.shots_per_repeat}"
            )
        return repeat

    def submit_task(self, task_info, repeat=1):
        """Submit task.

        Args:
            task_info: task info
            repeat: number of 1024-shot execution batches

        Returns:
            success, error message, task_id
        """
        tid = self.tmgr.run(task_info, repeat=repeat)
        # QuarkStudio returns an integer task ID on success and an error
        # response on submission failure.  Do not pass an error dictionary
        # back into the status/result endpoints as though it were a task ID.
        if isinstance(tid, bool) or not isinstance(tid, int):
            raise ValueError(
                f"Quafu task submission returned an invalid task ID: {tid!r}"
            )
        return tid

    def check_task_status(self, task_id, expect_task_status):
        """Check task status.

        Args:
            task_id: task id
            expect_task_status: expect task status

        Returns:
            success or fail, err_msg, status
        """
        _, response = self.get_task_status(task_id)
        if not response:
            return False, "Quafu task status response is empty", None

        if isinstance(response, str):
            status = response
        elif isinstance(response, dict):
            status = response.get("status")
        else:
            status = None

        if not isinstance(status, str) or not status:
            raise ValueError(
                f"Invalid Quafu task status response for {task_id}: "
                f"{response!r}"
            )

        expected_statuses = (
            {expect_task_status}
            if isinstance(expect_task_status, str)
            else set(expect_task_status)
        )
        if status in expected_statuses:
            return True, None, status

        if status in self.task_status_failure:
            remote_result = None
            result_fetch_error = None
            try:
                _, remote_result = self.get_task_results(task_id)
            except Exception as e:
                result_fetch_error = str(e)

            logger.error(
                f"Quafu remote task failed: task_id={task_id}, "
                f"status_response={response!r}, "
                f"result_response={remote_result!r}, "
                f"result_fetch_error={result_fetch_error!r}"
            )

            error_detail = None
            if isinstance(remote_result, dict):
                error_detail = (
                    remote_result.get("error")
                    or remote_result.get("message")
                    or remote_result.get("msg")
                    or remote_result.get("detail")
                )
            elif isinstance(remote_result, str) and remote_result:
                error_detail = remote_result

            if isinstance(response, dict):
                error_detail = (
                    error_detail
                    or response.get("error")
                    or response.get("message")
                )
            if not error_detail and result_fetch_error:
                error_detail = (
                    f"failed to fetch remote result: {result_fetch_error}"
                )
            suffix = f": {error_detail}" if error_detail else ""
            raise ValueError(
                f"Quafu task {task_id} failed with status {status}{suffix}"
            )

        err_msg = (
            "Task status is not in "
            f"{', '.join(map(str, expected_statuses))}, "
            f"and current status: {status}"
        )
        return False, err_msg, status

    def get_task_status(self, task_id):
        """Get the current status response from QuarkStudio.

        Args:
            task_id: task id

        Returns:
            success flag and the remote status response
        """
        result = self.tmgr.status(task_id)
        if result is None:
            return False, None
        return True, result

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
