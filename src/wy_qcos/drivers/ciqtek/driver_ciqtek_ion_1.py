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

from loguru import logger

from wy_qcos.common.constant import Constant, HttpCode, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase


class DriverCiqtekIon1(DriverBase):
    """国仪量子 离子阱驱动.

    Ion 1 driver
    https://www.ciqtek.com/
    """

    task_time_out = 3600

    def __init__(self):
        super().__init__()
        self.access_token = None
        self.host = None
        self.port = None
        self.app_id = None
        self.app_secret = None
        self.device_id = None
        self.version = "0.0.1"
        self.alias_name = "国仪量子 离子阱驱动"
        self.description = "国仪量子 离子阱驱动"
        self.transpiler = Constant.TRANSPILER_DUMMY
        self.tech_type = Constant.TECH_TYPE_ION_TRAP
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        self.enable_circuit_aggregation = False
        self.max_qubits = 5
        self.default_data_type = DriverBase.DATA_TYPE_QASM2
        self.supported_code_types = [DriverBase.DATA_TYPE_QASM2]
        self.supported_transpilers = [Constant.TRANSPILER_DUMMY]

        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_VALIDATING: 5,
            self.TASK_STAGE_SUBMIT_TASK: 10,
            self.TASK_STAGE_WAIT_TASK: 20,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }
        self.conn_str = None

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success, err_msg
        """
        success = True
        err_msg = None

        driver_config_schema = {
            "host": str,
            "port": int,
            "device_id": str,
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
        self.host = extra_configs.get("host", "127.0.0.1")
        self.port = extra_configs.get("port", 8888)
        self.device_id = extra_configs.get("device_id", "")
        self.conn_str = f"http://{self.host}:{self.port}"

        # 1. get or refresh access token
        logger.info("1. get or refresh access token")
        if self.access_token:
            success, err_msg, access_token = self.refresh_access_token(
                self.access_token
            )
        else:
            success, err_msg, access_token = self.get_access_token(
                self.app_id, self.app_secret
            )
        self.set_progress_by_task(self.TASK_STAGE_USER_AUTHENTICATION)
        self.access_token = access_token
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

        task_info = {
            "appId": self.app_id,
            "outerExperimentId": job_id,
            "deviceId": self.device_id,
            "notifyUrl": "https://www.ciqtek.com/experiment/result",
            "gateData": [
                {"mold": "H", "x": "0", "y": "1", "param1": ""},
                {"mold": "H", "x": "0", "y": "2", "param1": ""},
            ],
            "codeType": "openqasm",
            "code": data["source_code"],
        }

        # 2. Submit task
        logger.info("2. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg, task_id = self.submit_task(
            task_info, self.access_token
        )
        if not success:
            raise ValueError(f"Failed to submit task [{job_id}]: {err_msg}")

        # 3. get task results
        logger.info("3. get task results")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _results = Library.loop_with_timeout(
            self.get_task_result,
            self.task_time_out,
            5,
            task_id,
            expect_task_status=[2],
        )
        if not success:
            raise ValueError(f"Failed to wait for task [{job_id}]: {err_msg}")

        # 4. convert results
        logger.info("4. convert results")
        results = self.convert_result(_results, shots)

        # 5. save results and set driver status to ONLINE
        self.set_results(job_id, data_index, results=results)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def get_access_token(self, app_id, app_secret):
        """Get access token.

        Args:
            app_id: app id
            app_secret:  app secret

        Returns:
            success, error message, access token
        """
        success = True
        err_msgs = []
        access_token = None
        url = f"{self.conn_str}/control/v1/token"
        data = {"appId": app_id, "appSecret": app_secret}
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=data,
            headers=self.default_headers,
            func_name="get_access_token",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            access_token = response["data"]["access_token"]
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), access_token

    def refresh_access_token(self, access_token):
        """Refresh access token expire time.

        Args:
            access_token: access token

        Returns:
            success, error message, access token
        """
        success = True
        err_msgs = []
        url = (
            f"{self.conn_str}/control/v1/"
            f"token/refresh?access_token={access_token}"
        )
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            headers=self.default_headers,
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            access_token = response["data"]["access_token"]
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), access_token

    def submit_task(self, tasks_info, access_token):
        """Submit tasks.

        Args:
            tasks_info: tasks info
            access_token: access token

        Returns:
            success, error message, task id
        """
        success = True
        err_msgs = []
        experiment_id = None
        # Submit task
        url = (
            f"{self.conn_str}/control/v1/"
            f"experiment/submit?access_token={access_token}"
        )
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=tasks_info,
            headers=self.default_headers,
            func_name="submit_tasks",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            experiment_id = response["data"]["experimentId"]
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), experiment_id

    def get_task_result(self, experiment_id, expect_task_status):
        """Get task results.

        Args:
            experiment_id: experiment id
            expect_task_status: expected task status

        Returns:
            success, error message, result
        """
        success = True
        err_msgs = []
        url = (
            f"{self.conn_str}/control/v1/experiment/"
            f"get?access_token={self.access_token}&experimentId={experiment_id}"
        )
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.GET,
            headers=self.default_headers,
            func_name="get_task_result",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            task_status = response["data"]["status"]
            if task_status in expect_task_status:
                results = response["data"]["result"]
                return success, "\n".join(err_msgs), results
        else:
            err_msgs.append(reason)
        return False, err_msgs, None

    def convert_result(self, results, shots):
        """Convert result.

        Args:
            results: task results
            shots: shots

        Returns:
            converted task results
        """
        counts = [(item["name"], shots * item["value"]) for item in results]
        normalized_results = []
        remainders = []
        total_base = 0

        for name, val in counts:
            base = int(val)  # 向下取整
            rem = val - base
            normalized_results.append({"name": name, "count": base})
            remainders.append((name, rem))
            total_base += base

        remaining = shots - total_base
        remainders.sort(key=lambda x: x[1], reverse=True)

        for i in range(remaining):
            target_name = remainders[i][0]
            for item in normalized_results:
                if item["name"] == target_name:
                    item["count"] += 1
                    break

        converted_results = {}
        for result in normalized_results:
            converted_results[result["name"]] = result["count"]
        return converted_results

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        # TODO(jidalong) mock data currently
        device_running_info = {"status": "online"}
        return device_running_info
