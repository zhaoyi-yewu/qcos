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
import random
import requests
import time
from typing import Any

from jsonrpcclient import request
from loguru import logger
from schema import Optional, Or
import zerorpc

from datetime import datetime

from wy_qcos.common.constant import Constant, HttpMethod, HttpCode
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_gate_base import DriverGateBase


class DriverHanyuan1(DriverGateBase):
    """中科酷原-汉原1 中性原子驱动.

    Cascoldatom Hanyuan1 driver
    CA-NAQC-20Q-A1
    """

    verbose = False
    DEFAULT_CONTROL_SYSTEM_IP = "127.0.0.1"
    DEFAULT_CONTROL_SYSTEM_PORT = 18402
    DEFAULT_CONTROL_SYSTEM_ZMQ_PORT = 18403
    # task status
    task_status_unknown = "unknown"
    task_status_running = "running"
    task_status_completed = "completed"
    task_status_failed = "failed"
    # extended data type
    data_type_qu_topo = "qu_topo"

    def __init__(self) -> None:
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "中科酷原-汉原1 中性原子驱动"
        self.description = "中科酷原-汉原1 中性原子驱动"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = True
        self.max_qubits = 100
        self.server_host: str | None = None
        self.server_port: int | None = None
        self.base_url: str | None = None
        self.zerorpc_clients: list = []  # 连接池，每个元素为 zerorpc.Client
        self.use_zmq = False
        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_INIT: 10,
            self.TASK_STAGE_SUBMIT_TASK: 20,
            self.TASK_STAGE_WAIT_TASK: 30,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }
        self.enable_device_mgr = True
        self.enable_device_monitor = True

    def init_driver(self):
        """Init driver."""
        extra_configs = self.get_configs()
        ip_address = extra_configs.get(
            "ip_address", self.DEFAULT_CONTROL_SYSTEM_IP
        )
        port = extra_configs.get("port", self.DEFAULT_CONTROL_SYSTEM_PORT)
        zmq_ip_address = extra_configs.get(
            "zmq_ip_address", self.DEFAULT_CONTROL_SYSTEM_IP
        )
        zmq_port = extra_configs.get(
            "zmq_port", self.DEFAULT_CONTROL_SYSTEM_ZMQ_PORT
        )
        self.use_zmq = extra_configs.get("use_zmq", False)
        zmq_pool_size = extra_configs.get("zmq_pool_size", 60)
        logger.info(f"use_zmq: {self.use_zmq}")

        if self.use_zmq:
            self.init_zerorpc_client(
                zmq_ip_address, zmq_port, pool_size=zmq_pool_size
            )
        else:
            self.init_base_url(ip_address, port)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
          configs: configs dictionary

        Returns:
            success, err_msg
        """
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            "debug": bool,
            "ip_address": str,
            "port": int,
            "callback_baseurl": str,
            "zmq_ip_address": str,
            "zmq_port": int,
            "use_zmq": bool,
            "zmq_pool_size": int,
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
            configs, driver_config_schema, ignore_extra_keys=True
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
        """Close driver."""
        if self.zerorpc_clients:
            for client in self.zerorpc_clients:
                try:
                    client.close()
                except Exception as e:
                    logger.error(f"Failed to close ZeroRPC client: {e}")
            self.zerorpc_clients = []

    def get_formatted_timestamp(self):
        """get_formatted_timestamp.

        Returns:
            str: formatted timestamp.
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """
        data_type = self.data_type_qu_topo
        job_id = str(Library.create_uuid())
        qpu_configs = {}

        # Execute task workflow
        qu_configs = self._execute_task_workflow(
            job_id=job_id,
            data_type=data_type,
            interval=1,
        )

        qpu_configs = {"qpu_configs": qu_configs}
        return qpu_configs

    def _check_task_status(
        self,
        job_id: str,
        data_type: str,
        data_index: int | None = 0,
        timeout: int = 1800,
        interval: int = 5,
    ) -> tuple[bool, str | None]:
        """Wait for task status.

        Args:
            job_id: job ID
            data_type: data type
            data_index: data index
            timeout: wait timeout in seconds (optional, default 1800)
            interval: check interval in seconds (optional, default 5)

        Returns:
            tuple[bool, str | None]: (success, err_msg)
        """
        err_msg = None
        start_time = time.time()
        elapsed_time: float = 0.0
        while True:
            task_status = self._get_task_status(job_id, data_type, data_index)
            if task_status == self.task_status_completed:
                return True, None
            elif task_status == self.task_status_unknown:
                err_msg = f"Task [{job_id}] unknown"
                return False, err_msg
            else:
                if elapsed_time >= timeout:
                    err_msg = f"Task [{job_id}] timed out"
                    return False, err_msg
            time.sleep(interval)
            elapsed_time = time.time() - start_time

    def _execute_task_workflow(
        self,
        job_id: str,
        data_type: str,
        num_qubits: int | None = None,
        data: list[Any] | None = None,
        shots: int | None = None,
        data_index: int | None = 0,
        timeout: int = 1800,
        interval: int = 5,
    ) -> Any:
        """Execute task workflow.

        This is a generic task workflow includes the following steps:
        1. Submit task
        2. Wait for task completion
        3. Get task results

        Args:
            job_id: job ID (required)
            data_type: data type (required)
            num_qubits: number of qubits (optional)
            data: gate list data (optional)
            shots: shots (optional)
            data_index: data index (optional, default 0)
            timeout: wait timeout in seconds (optional, default 1800)
            interval: check interval in seconds (optional, default 5)

        Returns:
            Any: task results

        Raises:
            ValueError: if task submission, waiting, or result retrieval fails
        """
        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # Step 1: Submit task
        logger.info(f"submit task: job_id={job_id}, data_type={data_type}")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg = self.submit_task(
            job_id=job_id,
            data_type=data_type,
            num_qubits=num_qubits,
            data=data,
            shots=shots,
            data_index=data_index,
        )
        if not success:
            raise ValueError(f"Failed to submit task [{job_id}]: {err_msg}")

        # Step 2: Wait for task completion
        logger.info(
            f"wait task status: job_id={job_id}, data_type={data_type}"
        )
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)

        success, err_msg = self._check_task_status(
            job_id=job_id,
            data_type=data_type,
            data_index=data_index,
            timeout=timeout,
            interval=interval,
        )
        if not success:
            raise ValueError(
                f"Failed to wait for task status [{job_id}]: {err_msg}"
            )

        # Step 3: Get task results
        logger.info(
            f"get task results: job_id={job_id}, data_type={data_type}"
        )
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, err_msg, results = self.get_task_results(
            job_id=job_id,
            data_type=data_type,
            data_index=data_index,
        )
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        return results

    def run(
        self,
        job_id,
        num_qubits,
        data,
        data_type,
        shots=1,
        qec_options=None,
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
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )

        gates_list = data["transpile_results"]
        data_index = data["index"]

        # Execute task workflow
        results = self._execute_task_workflow(
            job_id=job_id,
            data_type=data_type,
            num_qubits=num_qubits,
            data=gates_list,
            shots=shots,
            data_index=data_index,
        )

        self.set_results(
            job_id,
            data_index,
            results=results,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def cancel(
        self,
        job_id: str,
    ) -> tuple:
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID

        Returns:
            (success, err_msg)
        """
        success = True
        err_msg = None
        try:
            # call set_task method, pass data_type="cancel_task"
            success, err_msg, _ = self.set_task(
                job_id=job_id,
                data_type="cancel_task",
            )
            if success:
                logger.info(f"Successfully canceled task: job_id={job_id}")
            else:
                logger.warning(
                    f"Failed to cancel task: job_id={job_id}, error={err_msg}"
                )
        except Exception as e:
            success = False
            err_msg = str(e)
            logger.error(f"Exception while canceling task: {e}")

        return success, err_msg

    def init_base_url(self, ip_address: str, port: int):
        """Init base url.

        Args:
            ip_address: server ip address
            port: server port
        """
        self.server_host = ip_address
        self.server_port = port

        api_version = "v1"
        self.base_url = f"http://{ip_address}:{port}/api/{api_version}/job"

    def init_zerorpc_client(
        self, ip_address: str, port: int, pool_size: int = 60
    ):
        """Init ZeroRPC client pool (over ZeroMQ + MessagePack).

        Args:
            ip_address: server ip address
            port: server port
            pool_size: pool size, default 60
        """
        self.server_host = ip_address
        self.server_port = port
        connect_address = f"tcp://{ip_address}:{port}"
        self.zerorpc_clients = []
        for _ in range(pool_size):
            client = zerorpc.Client(timeout=30)
            client.connect(connect_address)
            self.zerorpc_clients.append(client)
        logger.info(
            f"ZeroRPC connection ready: {connect_address}, "
            f"pool size: {pool_size}"
        )

    def _get_zerorpc_client(self):
        """Get a client from the connection pool."""
        if not self.zerorpc_clients:
            return None
        return random.choice(self.zerorpc_clients)

    @staticmethod
    def print_api_response(status_code, reason, text, result=None):
        """Print API response.

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

    def call_zerorpc_rpc(
        self, method_name: str, data: dict[str, Any] | None = None
    ) -> tuple:
        """Call ZeroRPC method (same semantics as former call_zmq_rpc).

        Args:
            method_name: method name
            data: params dict (Default value = None)

        Returns:
            status_code, reason, text, result
        """
        status_code = None
        reason = None
        text = None
        result = None

        try:
            client = self._get_zerorpc_client()
            if not client:
                return -1, "ZeroRPC client pool not initialized", None, None

            fn = getattr(client, method_name, None)
            if fn is None:
                return -1, f"Unknown method: {method_name}", None, None

            ret = fn(data or {})

            if isinstance(ret, dict) and ret.get("error") is True:
                status_code = -1
                reason = ret.get("message", "Unknown error")
                result = ret
            else:
                status_code = HttpCode.SUCCESS_OK
                reason = "OK"
                result = (
                    ret.get("result", ret) if isinstance(ret, dict) else ret
                )

            DriverHanyuan1.print_api_response(
                status_code, reason, text, result
            )
            return status_code, reason, text, result

        except Exception as e:
            if (
                "timeout" in str(e).lower()
                or type(e).__name__ == "TimeoutExpired"
            ):
                status_code = -1
                reason = "ZeroRPC request timeout"
                logger.warning(f"ZeroRPC request timeout: {method_name}")
            else:
                status_code = -1
                reason = str(e)
                logger.error(f"ZeroRPC call failed: {e}")

        DriverHanyuan1.print_api_response(status_code, reason, text, result)
        return status_code, reason, text, result

    @staticmethod
    def call_json_rpc(url, method_name, data=None, params=None):
        """Call json rpc method.

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

    def _build_request_data(
        self,
        job_id: str,
        data_type: str,
        num_qubits: int | None = 1,
        data: list[Any] | dict[str, Any] | None = None,
        shots: int | None = 1,
        data_index: int | None = 0,
    ) -> dict[str, Any]:
        """_build_request_data.

        Build request data based on different data_type.

        Args:
            job_id: job id
            data_type: data type (gate_sequence, qu_topo, etc.)
            num_qubits: number of qubits (optional, default 1)
            data: gate list data (optional, default None)
            shots: shots (optional, default 1)
            data_index: data index (optional, default 0)

        Returns:
            request data dictionary
        """
        # basic request data
        request_data: dict[str, Any] = {
            "job_id": job_id,
            "data_type": data_type,
        }

        if data_type == "gate_sequence":
            # gate_sequence: requires complete parameters
            if data is None:
                raise ValueError("gate_sequence task requires data parameter")

            # process data format
            if isinstance(data, dict):
                gate_list_raw = data.get("basis_gate_list", data)
                # Ensure gate_list is a list
                if isinstance(gate_list_raw, list):
                    gate_list: list[Any] = gate_list_raw
                else:
                    # If basis_gate_list doesn't exist, use data itself
                    gate_list = data if isinstance(data, list) else []
            else:
                gate_list = data

            processed_data = []
            for gate in gate_list:
                gate_dict = {
                    "name": gate.name.upper(),
                    "targets": gate.targets,
                    "arg_value": gate.arg_value,
                }
                processed_data.append(gate_dict)

            request_data.update({
                "data_index": data_index,
                "data": processed_data,
                "shots": shots if shots is not None else 1,
                "qubit_num": num_qubits if num_qubits is not None else 1,
                "timestamp": self.get_formatted_timestamp(),
            })

        elif data_type == "qu_topo":
            # qu_topo: only data_type
            pass

        elif data_type == "cancel_task":
            # cancel_task: only job_id and data_type
            pass

        else:
            pass

        return request_data

    def submit_task(
        self,
        job_id: str,
        data_type: str,
        num_qubits: int | None = 1,
        data: list[Any] | None = None,
        shots: int | None = 1,
        data_index: int | None = 0,
    ) -> tuple:
        """Submit task.

        Support multiple data_type task submission.

        Args:
            job_id: job id
            data_type: data type (gate_sequence, qu_topo, etc.)
            num_qubits: number of qubits (optional)
            data: gate list data (optional, default None)
            shots: shots (optional)
            data_index: data index (optional)

        Returns:
            (success, err_msg)
        """
        success = True
        err_msgs = []
        try:
            # build request data based on data_type
            request_data = self._build_request_data(
                job_id=job_id,
                data_type=data_type,
                num_qubits=num_qubits,
                data=data,
                shots=shots,
                data_index=data_index,
            )

            method_name = "submit_task"
            if self.use_zmq:
                status_code, reason, text, result = self.call_zerorpc_rpc(
                    method_name, request_data
                )
            else:
                status_code, reason, text, result = self.call_json_rpc(
                    self.base_url, method_name, request_data
                )

            # check response (support JSON-RPC and ZeroRPC)
            if status_code == HttpCode.SUCCESS_OK and result:
                if self.use_zmq:
                    if (
                        isinstance(result, dict)
                        and result.get("error") is False
                    ):
                        success = True
                    elif (
                        isinstance(result, dict)
                        and result.get("error") is True
                    ):
                        success = False
                        err_msgs.append(result.get("message", "Unknown error"))
                    else:
                        success = True
                else:
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

    def _get_task_status(
        self,
        job_id: str,
        data_type: str,
        data_index: int | None = 0,
    ) -> str | None:
        """Get task status.

        Args:
            job_id: job id
            data_type: data type
            data_index: data index (optional, default 0)

        Returns:
            str: task status, if failed return None
        """
        try:
            # construct request data
            request_data = {
                "job_id": job_id,
                "data_type": data_type,
                "data_index": data_index,
            }

            method_name = "query_task_status"
            if self.use_zmq:
                status_code, reason, text, result = self.call_zerorpc_rpc(
                    method_name, request_data
                )
            else:
                status_code, reason, text, result = self.call_json_rpc(
                    self.base_url, method_name, request_data
                )

            if status_code == HttpCode.SUCCESS_OK and result:
                if self.use_zmq:
                    if isinstance(result, dict):
                        return result.get("status", self.task_status_unknown)
                    return self.task_status_unknown
                else:
                    result = (
                        result.get("result")
                        if isinstance(result, dict)
                        else result
                    )
                    if isinstance(result, dict):
                        return result.get("status", self.task_status_unknown)
                    return self.task_status_unknown
            return None
        except Exception:
            return None

    def get_task_results(
        self,
        job_id: str,
        data_type: str,
        data_index: int | None = 0,
    ) -> tuple:
        """Check task results.

        Args:
            job_id: job id
            data_type: data type (gate_sequence, qu_topo, etc.)
            data_index: data index (optional, default 0)

        Returns:
            bool: True if task results meets requirements, False otherwise
            str: error message
            str: task results
        """
        success = True
        err_msgs = []
        results = None

        # construct request data
        request_data = {
            "job_id": job_id,
            "data_type": data_type,
            "data_index": data_index,
        }

        method_name = "query_task_result"
        if self.use_zmq:
            status_code, reason, text, result = self.call_zerorpc_rpc(
                method_name, request_data
            )
        else:
            status_code, reason, text, result = self.call_json_rpc(
                self.base_url, method_name, request_data
            )

        if status_code == HttpCode.SUCCESS_OK and result:
            if self.use_zmq:
                if isinstance(result, dict):
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
                        err_msgs.append(err_m if err_m else "task failed")
                else:
                    success = False
                    err_msgs.append("invalid response format")
            else:
                result = (
                    result.get("result")
                    if isinstance(result, dict)
                    else result
                )
                if isinstance(result, dict):
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
                        err_msgs.append(err_m if err_m else "task failed")
                else:
                    success = False
                    err_msgs.append("invalid response format")
        else:
            success = False
            err_msgs.append(reason if reason else "request failed")

        return success, "\n".join(err_msgs), results

    def set_task(
        self,
        job_id: str,
        data_type: str,
    ) -> tuple:
        """Set task.

        Support multiple data_type tasks setting:
        - cancel_task: cancel executing or queued tasks
        - other types: (to be extended)

        Args:
            job_id: job id
            data_type: data type (cancel_task, etc.)

        Returns:
            (success, err_msg, result)
        """
        try:
            request_data = self._build_request_data(job_id, data_type)
            method_name = "set_task"
            if self.use_zmq:
                status_code, reason, text, result = self.call_zerorpc_rpc(
                    method_name, request_data
                )
            else:
                status_code, reason, text, result = self.call_json_rpc(
                    self.base_url, method_name, request_data
                )

            if status_code == HttpCode.SUCCESS_OK and result:
                if self.use_zmq:
                    if isinstance(result, dict):
                        status = result.get("status", "")
                        if status == "success":
                            return True, None, result
                        elif status == "failed":
                            message = result.get(
                                "message", "Task operation failed"
                            )
                            return False, message, result
                        else:
                            return True, None, result
                    else:
                        return False, "invalid response format", None
                else:
                    result_data = (
                        result.get("result")
                        if isinstance(result, dict)
                        else result
                    )
                    if isinstance(result_data, dict):
                        status = result_data.get("status", "")
                        if status == "success":
                            return True, None, result_data
                        elif status == "failed":
                            message = result_data.get(
                                "message", "Task operation failed"
                            )
                            return False, message, result_data
                        else:
                            return True, None, result_data
                    else:
                        return False, "invalid response format", None
            else:
                return False, reason if reason else "request failed", None
        except Exception as e:
            return False, str(e) if str(e) else "request failed", None

    def get_device_info(self):
        """Get device info.

        Returns:
            device info
        """
        try:
            job_id = str(Library.create_uuid())
            data_type = "device_info"
            request_data = self._build_request_data(job_id, data_type)
            method_name = "get_device_info"

            if self.use_zmq:
                status_code, reason, text, result = self.call_zerorpc_rpc(
                    method_name, request_data
                )
            else:
                status_code, reason, text, result = self.call_json_rpc(
                    self.base_url, method_name, request_data
                )

            if status_code == HttpCode.SUCCESS_OK and result:
                if self.use_zmq:
                    if isinstance(result, dict):
                        status = result.get("status", "")
                        if status == "success":
                            return True, None, result
                        elif status == "failed":
                            message = result.get(
                                "message", "Task operation failed"
                            )
                            return False, message, result
                        else:
                            return True, None, result
                    else:
                        return False, "invalid response format", None
                else:
                    result_data = (
                        result.get("result")
                        if isinstance(result, dict)
                        else result
                    )
                    if isinstance(result_data, dict):
                        status = result_data.get("status", "")
                        if status == "success":
                            return True, None, result_data
                        elif status == "failed":
                            message = result_data.get(
                                "message", "Task operation failed"
                            )
                            return False, message, result_data
                        else:
                            return True, None, result_data
                    else:
                        return False, "invalid response format", None
            else:
                return False, reason if reason else "request failed", None
        except Exception as e:
            return False, str(e) if str(e) else "request failed", None

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        device_running_info = {}
        success, err_msg, result = self.get_device_info()
        if not success:
            logger.warning(f"Failed to get device info: {err_msg}")
            device_running_info["status"] = Device.DEVICE_STATUS_DISCONNECTED
            device_running_info["details"] = {}
            return device_running_info

        logger.info(f"Device info: {result}")
        device_info = result.get("device_info")
        device_running_info["status"] = device_info.get(
            "device_status", "offline"
        )
        topo_data = device_info.get("topo_data")
        if not topo_data:
            logger.error("Topo data is None")
            device_running_info["details"] = {}
            return device_running_info
        # handle single_qubit_prop
        single_qubit_prop = {}
        device_running_info["details"] = {}
        if topo_data and isinstance(topo_data, dict):
            storage_area = topo_data.get("storage_area", [])
            readout_error = topo_data.get("readout_error", {})

            for idx, storage_qubit in enumerate(storage_area, 1):
                qubit_name = f"qubit{idx}"

                single_fidelity = readout_error.get(storage_qubit, 0.0)

                single_qubit_prop[qubit_name] = {
                    "single_qubit_gate_fidelity": single_fidelity,
                }

        # handle double_qubit_prop
        double_qubit_prop = None

        # handle topo_configs
        topo_configs = None

        device_running_info["details"]["single_qubit_prop"] = (
            single_qubit_prop if single_qubit_prop else None
        )
        device_running_info["details"]["double_qubit_prop"] = double_qubit_prop

        device_running_info["details"]["topo_configs"] = topo_configs

        return device_running_info
