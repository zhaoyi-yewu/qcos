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

import json
import re

from loguru import logger
from schema import Optional

from wy_qcos.common.constant import Constant, HttpMethod, HttpCode
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase
from wy_qcos.transpiler.cmss.common.base_operation import OperationType
from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation


class DriverSpinQNmr(DriverBase):
    """量旋科技 核磁驱动.

    SpinQ NMR driver
    https://cloud.spinq.cn
    """

    max_retries = 3
    task_time_out = 3600
    default_nmr_host = "127.0.0.1"
    default_nmr_port = 6060

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "量旋科技 核磁量子计算机驱动"
        self.description = "量旋科技 核磁量子计算机驱动"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NMR

        self.supported_basis_gates = [
            # Gates: H, X, Y, Z, RX, RY, RZ, T, TDG, U, CX, CZ, CCX
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_TDG,
            Constant.SINGLE_QUBIT_GATE_U,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CZ,
            Constant.THREE_QUBIT_GATE_CCX,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = False
        self.platform_name = "triangulum_vp"
        self.max_qubits = 3

        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_USER_AUTHENTICATION: 10,
            self.TASK_STAGE_SUBMIT_TASK: 20,
            self.TASK_STAGE_WAIT_TASK: 30,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }

        # private variables
        self._username = None
        self._signature = None
        self._nmr_host = None
        self._nmr_port = None
        self._nmr_conn_str = None
        self.token = None
        self.active_bits = []

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver."""

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
            "remote_host": str,
            "remote_port": int,
            "username": str,
            "signature": str,
            Optional("transpiler"): {
                "qpu_configs": {
                    "qubits": int,
                    "coupler_map": {str: [str]},
                }
            },
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        return success, err_msg

    def convert_gate(self, gate, qubit_depth):
        """Convert input qcos gate data to spinq gate data.

        Args:
            gate: input data
            qubit_depth: qubit depth

        Returns:
            spin gate info dict
        """
        gtag = None

        if gate.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value:
            gtag = "C1"
        elif gate.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value:
            gtag = "C2"
        elif gate.operation_type == OperationType.TRIPLE_QUBIT_OPERATION.value:
            gtag = "C3"

        pattern = r"^r"
        match_result = re.match(pattern, gate.name)
        if not match_result:
            gate.name = gate.name.upper()
        else:
            gate.name = re.sub(pattern, "R", gate.name)

        new_target_list = [x + 1 for x in gate.targets]
        for qubit in gate.targets:
            qubit += 1
            if qubit not in self.active_bits:
                self.active_bits.append(qubit)

        gate_info_dict = {
            "timeSlot": qubit_depth,
            "nativeOperation": True,
            "gate": {"gname": gate.name, "gtag": gtag},
            "qubits": new_target_list,
            "arguments": gate.arg_value,
        }
        return gate_info_dict

    def convert_gates(self, transpile_results, num_qubits):
        """Convert input data to gates and measures.

        Args:
            transpile_results (list): input data (sequence of basis gates)
            num_qubits: number of qubits (logical qubits)

        Returns:
            gates
        """
        gates = []

        max_physical_qubits = self.available_num_qubits

        logger.info(
            f"Initializing qubit_depth with {max_physical_qubits} qubits "
            f"(logical qubits: {num_qubits})"
        )
        index = 1
        for obj in transpile_results:
            if isinstance(obj, GateOperation):
                gates.append(self.convert_gate(obj, index))
                index += 1
        circuits = {"operations": gates, "definitions": []}
        return circuits

    def fetch_configs(self):
        """Fetch configs."""
        extra_configs = self.get_configs()
        self._username = extra_configs.get("username", "")
        self._signature = extra_configs.get("signature", "")
        self._nmr_host = extra_configs.get(
            "remote_host", self.default_nmr_host
        )
        self._nmr_port = extra_configs.get(
            "remote_port", self.default_nmr_port
        )
        self._nmr_conn_str = f"http://{self._nmr_host}:{self._nmr_port}"

        # 1. User authentication and get session id
        logger.info("1. user authentication")
        self.set_progress_by_task(self.TASK_STAGE_USER_AUTHENTICATION)
        success, err_msg, token = self.user_auth(
            self._username, self._signature
        )
        self.token = token
        if not success:
            raise ValueError(f"Authorize failed: {err_msg}")

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

        # 2. convert transpile_results to gates and measures
        logger.info("2. convert transpile_results to gates and measures")
        circuits = self.convert_gates(data["transpile_results"], num_qubits)

        # 3. Submit task
        logger.info("3. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        task_name = f"{job_id}_{data_index}"
        task_desc = f"qcos: {task_name}"
        task_info = {
            "tname": task_name,
            "bitNum": num_qubits,
            "sourceType": "spinqit",
            "calcMatrix": False,
            "simulator": False,
            "proceedNow": True,
            "platformCode": self.platform_name,
            "description": task_desc,
            "circuit": circuits,
            "activeBits": self.active_bits,
            "shots": shots,
        }
        success, err_msg, task_code = self.submit_task(task_info)
        if not success:
            raise ValueError(f"Failed to submit task [{task_name}]: {err_msg}")

        # 4. Wait for task_status is finished
        logger.info("4. get task results")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _results = Library.loop_with_timeout(
            self.get_task_results,
            self.task_time_out,
            5,
            task_code,
            expect_task_status=["S"],
        )
        if not success:
            raise ValueError(
                f"Failed to wait for task [{task_name}]: {err_msg}"
            )

        # 5. convert results
        logger.info("5. convert results")
        results = self.convert_results(_results, num_qubits, shots)

        # 6. Save results and set driver status to ONLINE
        self.set_results(job_id, data_index, results=results)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def user_auth(self, username, signature):
        """User authorization.

        Args:
            username: username
            signature: signature

        Returns:
            success, error message, token
        """
        success = True
        err_msgs = []
        token = None
        url = f"{self._nmr_conn_str}/user/spinqit/login"
        data = {"username": username, "signature": signature}
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=data,
            headers=self.default_headers,
            func_name="user_auth",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            token = response["token"]
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), token

    def submit_task(self, task_info):
        """Submit task.

        Args:
            task_info: task info

        Returns:
            success, error message, task code
        """
        success = True
        err_msgs = []
        task_code = None

        self.auth_headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "Authorization": None,
            "token": self.token,
        }
        # Submit task
        url = f"{self._nmr_conn_str}/task/user/create"
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=task_info,
            headers=self.auth_headers,
            func_name="submit_tasks",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            task_code = response["task"]["tcode"]
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), task_code

    def get_task_results(self, task_code, expect_task_status):
        """Get task results.

        Args:
            task_code: task code
            expect_task_status: expect task status S

        Returns:
            success, error message, result
        """
        success = True
        err_msgs = []

        # Get task results
        url = (
            f"{self._nmr_conn_str}/task/user"
            f"/getTaskRunResultByTcode?taskCode={task_code}"
        )
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.GET,
            headers=self.auth_headers,
            func_name="get_task_results",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            task_status = response["taskStatus"]
            if task_status in expect_task_status:
                results = response["run"]["module"]
                return success, "\n".join(err_msgs), results
        else:
            err_msgs.append(reason)
        return False, err_msgs, None

    def cancel(self, job_id):
        """Cancel running job in driver.

        Args:
            job_id: job id
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def convert_results(self, results, num_qubits, shots):
        """Valid shots.

        Args:
            results: task results
            num_qubits: number of qubits
            shots: number of shots

        Returns:
            converted task results
        """
        converted_result = {}
        state_range = 2**num_qubits
        remaining = shots
        dict_result = {x: 0 for x in range(state_range)}

        i = 0
        for result in results:
            dict_result[i] = result * shots
            i += 1
        for key, value in dict_result.items():
            bin_str = bin(key)
            value = round(value)
            value = min(value, remaining)
            remaining -= value
            if value != 0:
                converted_result[bin_str[2:].zfill(num_qubits)] = value

        return converted_result
