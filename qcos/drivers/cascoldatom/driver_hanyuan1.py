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

import copy
import requests
import time

from jsonrpcclient import request
from loguru import logger
from schema import Optional, Or

from qcos.common.constant import Constant, HttpMethod, HttpCode
from qcos.common.library import Library
from qcos.drivers.device import Device
from qcos.drivers.driver_base import DriverBase


class DriverHanyuan1(DriverBase):
    """中科酷原-汉原1 中性原子驱动

    Cascoldatom Hanyuan1 driver
    CA-NAQC-20Q-A1
    """

    verbose = False
    DEFAULT_CONTROL_SYSTEM_IP = "127.0.0.1"
    DEFAULT_CONTROL_SYSTEM_PORT = 18402
    # task status
    task_status_unknown = "unknown"
    task_status_running = "running"
    task_status_completed = "completed"
    task_status_failed = "failed"

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "中科酷原-汉原1 中性原子驱动"
        self.description = "中科酷原-汉原1 中性原子驱动"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = True
        self.max_qubits = 10
        self.server_host = None
        self.server_port = None
        self.base_url = None
        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_INIT: 10,
            self.TASK_STAGE_SUBMIT_TASK: 20,
            self.TASK_STAGE_WAIT_TASK: 30,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }

    def init_driver(self):
        """Init driver"""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def validate_driver_configs(self, configs):
        """Validate driver configs

        Args:
          configs: configs dictionary

        Returns:
            success, err_msg
        """
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            "ip_address": str,
            "port": int,
            "callback_baseurl": str,
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
                Optional("decomposition_rule"): {
                    str: {"gates": [list], Optional("params"): [str]}
                },
            },
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
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
        """Close driver"""

    def fetch_configs(self):
        """
        Fetch configs

        Returns:
            remote transpiler configs
        """

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """Run job

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
        gates_list = data["transpile_results"]
        extra_configs = self.get_configs()
        ip_address = extra_configs.get(
            "ip_address", self.DEFAULT_CONTROL_SYSTEM_IP
        )
        port = extra_configs.get("port", self.DEFAULT_CONTROL_SYSTEM_PORT)

        # 1. init task connection
        logger.info("init task")
        self.set_progress_by_task(self.TASK_STAGE_INIT)
        self.init_task(ip_address, port)

        # 2. submit task
        logger.info("submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg = self.submit_task(
            job_id, num_qubits, gates_list, data_type, shots, data_index
        )
        if not success:
            raise ValueError(f"Failed to submit task [{job_id}]: {err_msg}")

        # 3. wait task results
        logger.info("wait task status")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_status,
            1800,
            5,
            job_id,
            data_index,
            expect_task_status=[self.task_status_completed],
        )
        if not success:
            raise ValueError(f"Failed to wait for task [{job_id}]: {err_msg}")

        # 4. get task results
        logger.info("wait done")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, err_msg, results = self.get_task_results(job_id, data_index)
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        self.set_results(job_id, data_index, results=results)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def init_task(self, ip_address: str, port: int):
        """Init task

        Args:
            ip_address: server ip address
            port: server port
        """
        self.server_host = ip_address
        self.server_port = port

        api_version = "v1"
        self.base_url = f"http://{ip_address}:{port}/api/{api_version}/job"

    @staticmethod
    def print_api_response(status_code, reason, text, result=None):
        """Print API response

        Args:
            status_code: status code
            reason: reason
            text: text
            result: result (Default value = None)
        """
        if DriverHanyuan1.verbose:
            print(
                f"Response: status_code: {status_code}, reason: {reason}, "
                f"text: {text}, result: {result}"
            )

    @staticmethod
    def call_json_rpc(url, method_name, data=None, params=None):
        """Call json rpc method

        Args:
            url: json rpc url
            method_name: method name
            data: data (Default value = None)
            params: params (Default value = None)

        Returns:
            response result
        """
        status_code = None
        reason = None
        text = None
        result = None
        try:
            jsonrpc_data = request(method_name, params={"body": data})

            status_code, reason, text, response_obj = Library.call_http_api(
                url,
                method=HttpMethod.POST,
                json=jsonrpc_data,
                params=params,
                func_name=method_name,
                debug=DriverHanyuan1.verbose,
            )

            # parse response_obj and get json
            if response_obj and hasattr(response_obj, "json"):
                try:
                    result = response_obj.json()
                except Exception as e:
                    logger.warning(f"parse json response failed: {e}")
                    result = None
            else:
                result = None

        except requests.exceptions.ConnectionError as ce:
            status_code = -1
            reason = f"Connection error: {str(ce)}"
        except Exception as e:
            status_code = -1
            reason = str(e)
        DriverHanyuan1.print_api_response(status_code, reason, text, result)
        return status_code, reason, text, result

    def submit_task(
        self,
        job_id: str,
        num_qubits: int,
        data: list,
        data_type: str,
        shots: int,
        data_index: int,
    ) -> tuple:
        """Submit task

        Args:
            job_id: job id
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots
            data_index: data index

        Returns:
            success, err_msgs
        """
        success = True
        err_msgs = []
        try:
            # process data format
            gate_list = (
                data.get("basis_gate_list", data)
                if isinstance(data, dict)
                else data
            )

            processed_data = []
            for gate in gate_list:
                gate_dict = {
                    "name": gate.name.upper(),
                    "targets": gate.targets,
                    "arg_value": gate.arg_value,
                }
                processed_data.append(gate_dict)

            # construct request data
            request_data = {
                "job_id": job_id,
                "data_index": data_index,
                "data": processed_data,
                "data_type": data_type,
                "shots": shots,
                "qubit_num": num_qubits,
                "timestamp": time.time(),
            }

            method_name = "submit_task"
            status_code, reason, text, result = self.call_json_rpc(
                self.base_url, method_name, request_data
            )

            # 检查JSON-RPC响应
            if status_code == HttpCode.SUCCESS_OK and result:
                if "error" in result:
                    success = False
                    err_msgs.append(result["error"])
                elif "result" in result:
                    success = True
                else:
                    success = False
                    err_msgs.append("unknown jsonrpc format")
            else:
                success = False
                err_msgs.append(reason)

        except Exception as e:
            success = False
            err_msgs.append(str(e))

        return success, "\n".join(err_msgs)

    def check_task_status(
        self, job_id: str, data_index: int, expect_task_status: list
    ) -> tuple:
        """Check task status

        Args:
            job_id: job id
            data_index: data index
            expect_task_status: expect task status

        Returns:
            bool: True if task status meets requirements, False otherwise
            str: error message
            str: task status
        """
        try:
            # construct request data
            request_data = {"job_id": job_id, "data_index": data_index}

            method_name = "query_task_status"
            status_code, reason, text, result = self.call_json_rpc(
                self.base_url, method_name, request_data
            )

            if status_code == HttpCode.SUCCESS_OK and result:
                result = result.get("result")
                task_status = result.get("status", self.task_status_unknown)
                if task_status in expect_task_status:
                    return True, None, task_status
                err_msg = (
                    f"Task status is not in {expect_task_status}, "
                    f"and current status: {task_status}"
                )
                return False, err_msg, None
            else:
                return (
                    False,
                    (f"Failed to get task status, status_code: {status_code}"),
                    None,
                )
        except Exception as e:
            return False, str(e), None

    def get_task_results(self, job_id: str, data_index: int):
        """Check task results

        Args:
            job_id: job id
            data_index: data index

        Returns:
            task results
        """
        success = True
        err_msgs = []
        results = None

        # construct request data
        request_data = {"job_id": job_id, "data_index": data_index}

        method_name = "query_task_result"
        status_code, reason, text, result = self.call_json_rpc(
            self.base_url, method_name, request_data
        )

        if status_code == HttpCode.SUCCESS_OK and result:
            result = result.get("result")
            status = result.get("status")
            if status == "success":
                success = True
                results = result.get("result")
                if results is None:
                    success = False
                    err_msgs.append("no task results")
            else:
                success = False
                err_m = result.get("result")
                err_msgs.append(err_m)

        return success, "\n".join(err_msgs), results
