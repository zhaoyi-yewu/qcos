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

import copy
import json
import logging
import socket
import threading
import time
from schema import Optional, Or

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase


logger = logging.getLogger(__name__)
# pylint: disable=duplicate-code


class DriverHanyuan1(DriverBase):
    """
    中科酷原-汉原1 中性原子驱动
    Cascoldatom Hanyuan1 driver
    CA-NAQC-20Q-A1
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.layout_method = DriverBase.LAYOUT_METHOD_CMSS_NONE
        self.supported_transpiler_list = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_merge = True
        self.max_qubits = 10
        self.client = None
        self._final_response = None

    def init_driver(self):
        """
        Init driver
        """
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def validate_driver_configs(self):
        """
        Validate driver configurations

        :return bool: True if successful, False otherwise
        :return err_msg: error message
        """
        # TODO(zhaoyi): load transpiler plugin, and implemented in transpiler
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            "ip_address": str,
            "port": int,
            "qpu_configs": {
                "qubits": int,
                "storage_area": [str],
                "operate_area": [str],
                "coupler_map": {str: [str]},
                "readout_error": {str: Or(float, int)},
                Optional("coupler_error"): {str: Or(float, int)},
                Optional("closest"): {str: str}
            },
            Optional("decomposition_rule"): {
                str: {
                    "gates": [list],
                    Optional("params"): [str]
                }
            }
        }
        _success, err_msgs = Library.validate_schema(
            self.extra_configs, driver_config_schema)
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        else:
            # copy configs to self.qpu_configs
            self.qpu_configs = copy.deepcopy(
                self.extra_configs.get("qpu_configs", {}))
            # copy configs to self.decomposition_rule
            self.decomposition_rule = copy.deepcopy(
                self.extra_configs.get("decomposition_rule", {}))
        return success, err_msg

    def close_driver(self):
        """
        Close driver
        """
        self.set_status(self.DRIVER_STATUS_OFFLINE)

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """
        Run job

        :param job_id: job ID
        :param num_qubits: number of qubits
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        # pylint: disable=duplicate-code
        logger.info(f"job_id: {job_id}, shots: {shots}, "
                    f"num_qubits: {num_qubits}, "
                    f"data_type: {data_type}, data: {data}")
        self.set_status(self.DRIVER_STATUS_BUSY)

        extra_configs = self.get_extra_configs()
        ip_address = extra_configs.get("ip_address", "100.78.62.2")
        port = extra_configs.get("port", 18402)

        # 1. init_task(class instantiation, connect)
        success = self.init_task(ip_address, port)
        if not success:
            logger.error("Failed to connect to quantum machine")
            results = {"error": "Failed to connect to quantum machine"}
            self.set_results(job_id, results=results)
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # 2. submit_task
        success = self.submit_task(job_id, num_qubits, data, data_type, shots)
        if not success:
            logger.error("Failed to submit task to quantum machine")
            results = {"error": "Failed to submit task to quantum machine"}
            self.set_results(job_id, results=results)
            self.close_task()
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # 3. Wait for task result
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_result, 3600, 5, job_id)
        if not success:
            logger.error(f"Failed to wait for task completion [{job_id}]: {err_msg}")
            results = {"error": f"Failed to wait for task completion: {err_msg}"}
            self.set_results(job_id, results=results)
            self.close_task()
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # 4. Get execution result from response
        if self._final_response is None:
            logger.error("No final task result received")
            results = {"error": "No final task result received"}
            self.set_results(job_id, results=results)
            self.close_task()
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # Get results and ensure they meet API schema requirements
        raw_results = self._final_response.get("result")
        if raw_results is None:
            logger.warning("Server returned empty result, using default result")
            results = {"status": "do failed", "data": []}
        else:
            # Ensure result is valid type (str, int, list, dict)
            if isinstance(raw_results, (str, int, list, dict)):
                results = raw_results
            else:
                logger.warning(f"Result type does not meet requirements: {type(raw_results)}, converting to string")
                results = str(raw_results)

        # Log final result for debugging
        logger.info(f"Final result: {results}")

        self.set_results(job_id, results=results)
        self.close_task()
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def init_task(self, ip_address: str, port: int) -> bool:
        """
        Initialize task: connect to server, start heartbeat detection thread

        :param ip_address: server IP address
        :param port: server port
        :return: whether connection is successful
        """
        try:
            self.client = HanyuanConnection(ip_address, port)
            return self.client.connect()
        except Exception as e:
            logger.error(f"Failed to initialize task: {e}")
            return False

    def close_task(self):
        """
        Close task: disconnect from server
        """
        if self.client:
            self.client.disconnect()
            self.client = None

    def submit_task(self, job_id: str, qubit_num: int, data, data_type: str,
                    shots: int) -> bool:
        """
        Submit task for execution

        :param job_id: task ID
        :param qubit_num: number of qubits
        :param data: data
        :param data_type: data type
        :param shots: number of executions
        :return: whether submission is successful
        """
        try:
            logger.info(f"Submit task: job_id={job_id}, data_type={data_type}, "
                        f"shots={shots}")

            processed_data = []
            # Check data format, if it's a dictionary containing basis_gate_list
            if isinstance(data, dict) and 'basis_gate_list' in data:
                gate_list = data['basis_gate_list']
                logger.info(f"Extract gate list from data['basis_gate_list']: {gate_list}")
            else:
                # If data itself is a gate list
                gate_list = data
                logger.info(f"Data itself is gate list: {gate_list}")

            for i, gate in enumerate(gate_list):
                logger.info(f"Processing {i+1}th gate: {gate}")
                gate_dict = {
                    "name": gate.name.upper(),  # Convert to uppercase for consistency
                    "targets": gate.targets,
                    "arg_value": gate.arg_value
                }
                logger.info(f"Converted gate_dict: {gate_dict}")
                processed_data.append(gate_dict)

            logger.info(f'processed_data: {processed_data}')
            message = {
                "job_id": job_id,
                "data_type": data_type,
                "qubit_num": qubit_num,
                "shots": shots,
                "data": processed_data,
                "timestamp": time.time()
            }

            # Send task
            success = self.client.send_message(message)
            if success:
                logger.info(f"Task {job_id} submitted successfully")
                return True
            else:
                logger.error(f"Task {job_id} submission failed")
                return False
        except Exception as e:
            logger.error(f"Error occurred while submitting task: {e}")
            return False

    def check_task_result(self, job_id: str) -> bool:
        """
        Check task return result

        :param job_id: task ID
        :return: whether task is completed
        """
        try:
            if not self.client or not self.client.is_connection_alive():
                logger.error("Connection disconnected")
                return False

            # Receive response
            response = self.client.receive_message()
            if response is None:
                # No response received, task may still be executing
                logger.info(f"Task {job_id} still executing...")
                return False

            # Check response format
            if not isinstance(response, dict):
                logger.warning(f"Received non-dictionary format response: {type(response)}")
                return False

            # Check if result is included
            if "result" in response:
                logger.info(f"Task {job_id} completed")
                # Save final result for subsequent use
                self._final_response = response
                logger.info(f"Task {job_id} completed, result: {response}")
                return True
            elif "error" in response:
                logger.error(f"Task {job_id} execution error: {response['error']}")
                # Save response even if error occurs to avoid infinite waiting
                self._final_response = response
                return True
            elif "status" in response:
                status = response.get("status")
                if status in ["completed", "finished", "done"]:
                    logger.info(f"Task {job_id} completed, status: {status}")
                    self._final_response = response
                    return True
                elif status in ["failed", "error"]:
                    logger.error(f"Task {job_id} execution failed, status: {status}")
                    self._final_response = response
                    return True
                elif status == "not_found":
                    # Task not found, continue waiting
                    logger.info(f"Task {job_id} not found, continue waiting...")
                    return False

            # Task still executing
            logger.info(f"Task {job_id} still executing...")
            return False

        except Exception as e:
            logger.error(f"Error occurred while checking task result: {e}")
            return False


class HanyuanConnection:
    """
    Cascoldatom Hanyuan1 neutral atom driver connection to real machine
    Cascoldatom Hanyuan1 connection
    """

    def __init__(self, server_host: str, server_port: int):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.is_connected = False
        self.heartbeat_thread = None
        self.heartbeat_running = False

    def connect(self) -> bool:
        """
        Establish server connection
        """
        try:
            logger.info(
                f"Connecting to server {self.server_host}:{self.server_port}")

            # Create TCP connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # Set connection timeout
            self.socket.connect((self.server_host, self.server_port))
            self.socket.settimeout(None)  # Reset to blocking mode
            self.is_connected = True

            # Start heartbeat thread
            self.heartbeat_running = True
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

            logger.info(
                f"Connected to server {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        """
        Disconnect server connection
        """
        # Stop heartbeat thread
        self.heartbeat_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)

        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error occurred while disconnecting: {e}")
            finally:
                self.is_connected = False
                logger.info("Disconnected from server")

    def send_message(self, message: dict) -> bool:
        """
        Send message to server
        """
        if not self.is_connected or not self.socket:
            logger.error("Not connected to server")
            return False

        try:
            data = json.dumps(message, ensure_ascii=False).encode('utf-8')
            self.socket.send(data + b'\n')
            logger.info(
                f"Send message to {self.server_host}:{self.server_port}: {message}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to send message to {self.server_host}:{self.server_port}: {e}")
            return False

    def receive_message(self) -> dict:
        """
        Receive server message
        """
        if not self.is_connected or not self.socket:
            logger.error("Not connected to server")
            return None

        try:
            data = self.socket.recv(4096)
            if not data:
                logger.warning("Server closed connection")
                self.is_connected = False
                return None

            # Decode data
            decoded_data = data.decode('utf-8')

            # Try to parse JSON, handle possible multiple JSON objects
            try:
                message = json.loads(decoded_data)
            except json.JSONDecodeError as e:
                # If parsing fails, try to find the first complete JSON object
                logger.info(f"JSON parsing failed, trying to fix: {e}")

                # Find the first complete JSON object
                brace_count = 0
                start_pos = -1
                message = None

                for i, char in enumerate(decoded_data):
                    if char == '{':
                        if brace_count == 0:
                            start_pos = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_pos != -1:
                            # Found complete JSON object
                            json_str = decoded_data[start_pos:i + 1]
                            try:
                                message = json.loads(json_str)
                                logger.debug(f"Successfully parsed JSON object: {json_str}")
                                break
                            except json.JSONDecodeError as parse_error:
                                logger.error(f"Failed to parse JSON object: {parse_error}")
                                # Continue searching for next JSON object
                                start_pos = -1
                                continue

                if message is None:
                    # No complete JSON object found
                    logger.warning("Unable to parse any valid JSON object")
                    self.is_connected = False
                    return None

            logger.info(
                f"Received message from {self.server_host}:{self.server_port}"
                f": {message}")

            # Handle heartbeat response
            if message.get("type") == "heartbeat_ack":
                return None  # Heartbeat response not returned to upper layer

            return message
        except Exception as e:
            logger.error(
                f"Failed to receive message from {self.server_host}:{self.server_port}: {e}")
            # Receiving message failure may indicate connection disconnect
            self.is_connected = False
            return None

    def _heartbeat_loop(self):
        """
        Heartbeat loop
        """
        while self.heartbeat_running and self.is_connected:
            try:
                # Send heartbeat message
                heartbeat_msg = {
                    "type": "heartbeat",
                    "timestamp": time.time()
                }

                success = self.send_message(heartbeat_msg)
                if not success:
                    logger.warning("Heartbeat send failed")
                    self.is_connected = False
                    break

                # Wait for heartbeat interval
                time.sleep(30)

            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                self.is_connected = False
                break

    def is_connection_alive(self) -> bool:
        """
        Check if connection is still alive
        """
        if not self.is_connected or not self.socket:
            return False

        try:
            # 检查socket状态
            self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return True
        except Exception:
            self.is_connected = False
            return False
