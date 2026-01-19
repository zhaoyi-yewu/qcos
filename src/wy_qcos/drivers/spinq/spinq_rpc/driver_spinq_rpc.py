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

import enum
import json
import time
import zerorpc
from functools import wraps

from loguru import logger
from schema import Optional, Or

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase
from wy_qcos.transpiler.cmss.common.base_operation import OperationType
from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation
from wy_qcos.transpiler.cmss.common.measure import Measure


def rpc_retry(max_retries=3, retry_interval=1):
    """Rpc retry decorator.

    Args:
        max_retries: max retries
        retry_interval: retry interval
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = (
                max_retries if max_retries is not None else self.max_retries
            )
            retry_count = 0
            err_msgs = []

            while retry_count < retries:
                try:
                    # run function
                    return func(self, *args, **kwargs)
                except (
                    zerorpc.exceptions.LostRemote,
                    zerorpc.exceptions.RemoteError,
                ) as e:
                    # handle rpc connection errors
                    err_msgs.append(f"RPC connection error: {str(e)}")
                    self._client.close()
                    time.sleep(retry_interval)
                    self._client.connect(self._rpc_conn_str)
                    retry_count += 1
                except Exception as e:
                    # handle other exceptions
                    err_msgs.append(f"RPC error occurred: {str(e)}")
                    retry_count += 1

            # all attempts are failed
            return False, "\n".join(err_msgs), None

        return wrapper

    return decorator


class DriverSpinQRpc(DriverBase):
    """量旋科技 大熊座-S25 超导驱动 (RPC版本).

    SpinQ SQC-S25 Superconducting driver (RPC)
    """

    max_retries = 3
    task_time_out = 3600
    default_rpc_host = "127.0.0.1"
    default_rpc_port = 4242

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "量旋科技 大熊座-S25 超导量子计算机驱动 (RPC版本)"
        self.description = "量旋科技 大熊座-S25 超导量子计算机驱动 (RPC版本)"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = True
        self.max_qubits = 57
        self.default_data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE

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
        self._password = None
        self._rpc_host = None
        self._rpc_port = None
        self._rpc_conn_str = None
        self._client = None
        self._session_id = None

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver."""
        if self._session_id:
            self.client_close(self._username, self._session_id)

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success or fail, err_msg
        """
        success = True
        err_msg = None

        # check and load driver configs
        # Note: storage_area and operate_area are optional for
        # superconducting devices as they don't require separate storage
        # and operation areas like neutral atom devices
        driver_config_schema = {  # TODO(zhouyunxiao): qpu_configs redefine
            "rpc_host": str,
            "rpc_port": int,
            "username": str,
            "password": str,
            Optional("transpiler"): {
                "qpu_configs": {
                    "qubits": int,
                    Optional("storage_area"): [str],
                    Optional("operate_area"): [str],
                    "coupler_map": {str: [str]},
                    "readout_error": {str: Or(float, int)},
                    Optional("coupler_error"): {str: Or(float, int)},
                    Optional("closest"): {str: str},
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

    def update_qubit_depth(self, qubit_depth, targets):
        """Update qubit depth.

        Args:
            qubit_depth: qubit depth
            targets: targets

        Returns:
            curr_qubit_depth
        """
        curr_qubit_depth = -1
        if len(targets) == 1:
            curr_qubit_depth = qubit_depth[targets[0]]
            qubit_depth[targets[0]] += 1
        elif len(targets) == 2:
            curr_qubit_depth = max(
                qubit_depth[targets[0]], qubit_depth[targets[1]]
            )
            qubit_depth[targets[0]] = curr_qubit_depth + 1
            qubit_depth[targets[1]] = curr_qubit_depth + 1
        elif len(targets) == 3:
            curr_qubit_depth = max(
                qubit_depth[targets[0]],
                qubit_depth[targets[1]],
                qubit_depth[targets[2]],
            )
            qubit_depth[targets[0]] = curr_qubit_depth + 1
            qubit_depth[targets[1]] = curr_qubit_depth + 1
            qubit_depth[targets[2]] = curr_qubit_depth + 1
        else:
            raise ValueError("invalid target length.")
        return curr_qubit_depth

    def convert_gate(self, gate, qubit_depth):
        """Convert input qcos gate data to spinq gate data.

        Args:
            gate: input data
            qubit_depth: qubit depth

        Returns:
            spin gate info dict
        """
        if gate.targets is None:
            raise ValueError("invalid target length.")

        curr_qubit_depth = self.update_qubit_depth(qubit_depth, gate.targets)

        gate_info_dict = {
            "type": gate.name,
            "controlQubit": -1,
            "angle": 0,
            "timeslot": curr_qubit_depth,
        }
        if gate.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value:
            gate_info_dict["qubitIndex"] = gate.targets[0]
        elif gate.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value:
            gate_info_dict["controlQubit"] = gate.targets[0]
            gate_info_dict["qubitIndex"] = gate.targets[1]
        elif gate.operation_type == OperationType.TRIPLE_QUBIT_OPERATION.value:
            gate_info_dict["controlQubit"] = gate.targets[1]
            gate_info_dict["qubitIndex"] = gate.targets[2]
        else:
            raise ValueError("invalid gate type.")

        if gate.arg_value is not None and len(gate.arg_value) > 0:
            gate_info_dict["angle"] = gate.arg_value[0]
        return gate_info_dict

    def convert_gates(self, transpile_results, num_qubits):
        """Convert input data to gates and measures.

        Args:
            transpile_results (list): input data (sequence of basis gates)
            num_qubits: number of qubits (logical qubits)

        Returns:
            gates, measures
        """
        gates = []
        measures = []
        # qubit_depth needs to be initialized based on the maximum index of
        # physical qubits.
        # the index of physical qubits after mapping may exceed the number of
        # logical qubits
        # Use available_num_qubits (the number of physical qubits obtained from
        # the hardware)
        max_physical_qubits = self.available_num_qubits

        # Ensure it can accommodate at least all physical qubit indices
        # (from 0 to max_physical_qubits-1)
        # Therefore, it is necessary to initialize max_physical_qubits elements
        qubit_depth = [0] * max_physical_qubits
        logger.info(
            f"Initializing qubit_depth with {max_physical_qubits} qubits "
            f"(logical qubits: {num_qubits})"
        )
        for obj in transpile_results:
            if isinstance(obj, Measure):
                measures.extend(obj.targets)
            if isinstance(obj, GateOperation):
                gates.append(self.convert_gate(obj, qubit_depth))
        return gates, measures

    def convert_results(self, results):
        """Convert results.

        Args:
             results (dict): spinq results

        Returns:
            qcos results
        """
        converted_results = results["qubit_result"]
        return converted_results

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """
        extra_configs = self.get_configs()
        self._username = extra_configs.get("username", "")
        self._password = extra_configs.get("password", "")
        self._rpc_host = extra_configs.get("rpc_host", self.default_rpc_host)
        self._rpc_port = extra_configs.get("rpc_port", self.default_rpc_port)
        self._rpc_conn_str = f"tcp://{self._rpc_host}:{self._rpc_port}"

        # init zerorpc client
        try:
            self._client = zerorpc.Client(self._rpc_conn_str)
        except Exception as e:
            raise ValueError(f"SpinQ exception: {e}") from e

        # 1. User authentication and get session id
        logger.info("1. user authentication")
        self.set_progress_by_task(self.TASK_STAGE_USER_AUTHENTICATION)
        success, err_msg, _results = self.user_auth(
            self._username, self._password
        )
        if not success:
            raise ValueError(f"Authorize failed: {err_msg}")

        self._session_id = _results["session_id"]

        transpiler_configs = {"qpu_configs": _results["coupling_list"]}
        return transpiler_configs

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
        gates, measures = self.convert_gates(
            data["transpile_results"], num_qubits
        )

        # 3. Submit task
        logger.info("3. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        task_name = f"{job_id}_{data_index}"
        task_desc = f"qcos: {task_name}"
        task_info = {
            "task_name": task_name,
            "task_gates": gates,
            "measures": measures,
            "task_desc": task_desc,
            "shots": shots,
        }
        success, err_msg, task_id = self.submit_task(task_info)
        if not success:
            raise ValueError(f"Failed to submit task [{task_name}]: {err_msg}")

        # 4. Wait for task_status is finished
        logger.info("4. wait and check task_status")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_status,
            self.task_time_out,
            5,
            task_id,
            expect_task_status=[TaskStatus.finished.value],
        )
        if not success:
            raise ValueError(
                f"Failed to wait for task [{task_name}]: {err_msg}"
            )

        # 5. Get task results
        logger.info("5. get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, err_msg, _results = self.get_task_results(task_id)
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        # 6. convert results
        logger.info("6. convert results")
        results = self.convert_results(_results["task_result"])

        # 8. Save results and set driver status to ONLINE
        self.set_results(job_id, data_index, results=results)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    @rpc_retry()
    def user_auth(self, username, password):
        """User authorization.

        Args:
            username: username
            password: password

        Returns:
            success, error message, response
        """
        resp_msg = self._client.request_login(username, password)
        response = json.loads(resp_msg)
        return_code = response["return_code"]

        if return_code == 1:
            return False, f"Failed to login. ret_code: {return_code}", None
        self.available_num_qubits = response["qubits_num"]
        return True, None, response

    @rpc_retry()
    def submit_task(self, task_info):
        """Submit task.

        Args:
            task_info: task info

        Returns:
            success, error message, task_id
        """
        task_name = task_info["task_name"]
        task_gates = task_info["task_gates"]
        measures = task_info["measures"]
        task_desc = task_info["task_desc"]
        shots = task_info["shots"]

        status, task_id = self._client.push_task(
            task_name, task_gates, measures, task_desc, shots, self._session_id
        )
        if status == 0:
            return True, None, task_id
        return False, f"Task submission failed, status: {status}", None

    def check_task_status(self, task_id, expect_task_status):
        """Check task status meets requirements.

        Args:
            task_id: task id
            expect_task_status: expected task status

        Returns:
            bool: success of failed
            str: error message
            str: task status
        """
        success, _, task_status = self.get_task_status(task_id)
        if success and task_status in expect_task_status:
            return True, None, task_status
        err_msg = (
            "Task status is not in "
            f"{', '.join(map(str, expect_task_status))}, "
            f"and current status: {task_status}"
        )
        return False, err_msg, None

    @rpc_retry()
    def get_task_status(self, task_id):
        """Get task status.

        Args:
            task_id: task id

        Returns:
            success, error message, task_id
        """
        task_status = self._client.get_task_status(task_id, self._session_id)
        return True, None, task_status

    @rpc_retry()
    def get_task_results(self, task_id):
        """Get task results.

        Args:
            task_id: task id
        Returns:
            success, error message, response
        """
        resp_json = self._client.get_task_result(task_id, self._session_id)
        response = json.loads(resp_json)
        return True, None, response

    def client_close(self, username, session_id):
        """Close client rpc.

        Args:
            username: username
            session_id: session id
        """
        try:
            self._client.request_logout(username, session_id)
        except Exception as e:
            logger.warning(f"Logout failed: {e}")
        finally:
            self._client.close()

    def cancel(self, job_id):
        """Cancel running job in driver.

        Args:
            job_id: job id
        """
        logger.info(f"Cancel job: job_id: {job_id}")


class TaskStatus(enum.Enum):
    """Task status."""

    finished = 0
    failed = 1
    running = 2
    queueing = 3
    not_found = 4
