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
from typing import Any
import smbclient

from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_pulse_base import DriverPulseBase


class DriverHanyuan1Pulse(DriverPulseBase):
    """中科酷原-汉原1 中性原子驱动, 后端为汉原原生测控系统.

    Wuyue Cascoldatom Hanyuan1 driver
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "中科酷原-汉原1-Pulse 中性原子驱动"
        self.description = "中科酷原-汉原1-Pulse 中性原子驱动"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.supported_code_types = [Constant.CODE_TYPE_QASM2]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.max_qubits = 100
        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_INIT: 10,
            self.TASK_STAGE_SUBMIT_TASK: 20,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }
        self.ip_address = "127.0.0.1"
        self.port = 445
        self.username = "username"
        self.password = ""
        self.shared_dir = "shared_dir"

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
            "ip_address": str,
            "port": int,
            "username": str,
            "password": str,
            "shared_dir": str,
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema, ignore_extra_keys=True
        )
        if _success:
            self.ip_address = configs.get("ip_address", "127.0.0.1")
            self.port = configs.get("port", 445)
            self.username = configs.get("username", "username")
            self.password = configs.get("password", "password")
            self.shared_dir = configs.get("shared_dir", "shared_dir")
            try:
                smbclient.register_session(
                    server=self.ip_address,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                )
            except Exception as e:
                _err_msg = "\n".join(str(e))
                err_msg = f"smbclient register_session error: {_err_msg}"
        else:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        return success, err_msg

    def _generate_pulse(self, transpile_results: list) -> tuple[list, list]:
        """Generate pulse data.

        Args:
            transpile_results: transpile results

        Returns:
            pulse data, qubit_id_list
        """
        pulse_data = []
        time = 0
        qubit_id_list = []
        for gate in transpile_results:
            single_pulse: dict[str, Any] = {}
            single_pulse["time"] = time
            if (
                gate.operation_type
                == OperationType.SINGLE_QUBIT_OPERATION.value
            ):
                single_pulse["type"] = 2
                if len(gate.arg_value) == 0:
                    logger.warning("wrong arg value parameter")
                    continue
                phase = 0
                degree = gate.arg_value[0]
                if len(gate.arg_value) >= 2:
                    phase = gate.arg_value[1]
                    continue
                param_lst = [
                    gate.targets[0],
                    round(degree, 6),
                    round(phase, 6),
                    0,
                    0,
                ]
                single_pulse["param"] = param_lst
                pulse_data.append(single_pulse)
                time = time + 1
                qubit_id_list.extend(gate.targets)
            if (
                gate.operation_type
                == OperationType.DOUBLE_QUBIT_OPERATION.value
            ):
                single_pulse["type"] = 4
                param_lst = [
                    gate.targets[0],
                    gate.targets[1],
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ]
                single_pulse["param"] = param_lst
                pulse_data.append(single_pulse)
                time = time + 1
                qubit_id_list.extend(gate.targets)
        return pulse_data, qubit_id_list

    def _generate_qubit_map(
        self, transpile_results: list, qubit_id_list: list
    ) -> list:
        """Generate qubit map.

        Args:
            transpile_results: transpile results
            qubit_id_list: qubit_id_list

        Returns:
            qubit map data
        """
        qubit_map = []
        meas_qubit_list = []
        for gate in transpile_results:
            if gate.operation_type == OperationType.MEASURE.value:
                meas_qubit_list.extend(gate.targets)
                logger.info(f"meas_qubit_list: {meas_qubit_list}")

                for value in qubit_id_list:
                    if value in meas_qubit_list:
                        qubit_map.append([value, 0, 0, 1])
                    else:
                        qubit_map.append([value, 0, 0, 0])
        return qubit_map

    def _prepare_data(
        self,
        task_id: str,
        transpile_results: list,
        shots: int,
        num_qubits: int,
    ):
        """Prepare data.

        Args:
            task_id: task_id
            transpile_results: transpile results
            shots: shots
            num_qubits: num_qubits

        Returns:
            prepared task data
        """
        task_data = {
            "MsgType": "MsgTask",
            "TaskID": task_id,
            "Pulse": [],
            "QubitMap": [],
            "QuantumNum": num_qubits,
            "RepeatTime": shots,
            "Mode": "circuit",
        }
        task_data["Pulse"], qubit_id_list = self._generate_pulse(
            transpile_results
        )
        task_data["QubitMap"] = self._generate_qubit_map(
            transpile_results, qubit_id_list
        )
        return task_data

    def _reset_and_reconnect(self):
        succ = True
        err_msg = None
        try:
            smbclient.reset_connection_cache()
            smbclient.register_session(
                server=self.ip_address,
                username=self.username,
                password=self.password,
                port=self.port,
            )
        except Exception as e:
            succ = False
            err_msg = f"smbclient register_session error: {str(e)}"
        return succ, err_msg

    def submit_task(self, task_data):
        """submit_task.

        Args:
            task_data: task_data

        Returns:
            qubit map data
        """
        remote_dir_path = rf"\\\\{self.ip_address}\\{self.shared_dir}"
        if not smbclient.path.exists(
            path=remote_dir_path,
            username=self.username,
            password=self.password,
            port=self.port,
        ):
            smbclient.mkdir(
                path=remote_dir_path,
                username=self.username,
                password=self.password,
                port=self.port,
            )
        remote_full_path = rf"{remote_dir_path}\\datatest.txt"
        json_str = json.dumps(task_data, ensure_ascii=False)
        succ = True
        err_msg = None
        try:
            with smbclient.open_file(
                path=remote_full_path,
                mode="wb",
                username=self.username,
                password=self.password,
                port=self.port,
            ) as f:
                f.write(json_str.encode("utf-8"))
        except ConnectionResetError:
            succ, err_msg = self._reset_and_reconnect()
            if not succ:
                return succ, err_msg
            with smbclient.open_file(
                path=remote_full_path,
                mode="wb",
                username=self.username,
                password=self.password,
                port=self.port,
            ) as f:
                f.write(json_str.encode("utf-8"))
        except Exception as e:
            succ = False
            err_msg = str(e)
            logger.error(f"Exception while submitting task: {e}")

        return succ, err_msg

    def get_task_result(self, task_id):
        """Get task result.

        Args:
            task_id: task id

        Returns:
            True if get result, False otherwise
        """
        remote_dir_path = rf"\\\\{self.ip_address}\\{self.shared_dir}"
        if not smbclient.path.exists(
            path=remote_dir_path,
            username=self.username,
            password=self.password,
            port=self.port,
        ):
            smbclient.mkdir(
                path=remote_dir_path,
                username=self.username,
                password=self.password,
                port=self.port,
            )
        remote_full_path = rf"{remote_dir_path}\\dataout.txt"
        succ = True
        err_msg = None
        content = None
        try:
            with smbclient.open_file(
                path=remote_full_path,
                mode="rb",
                username=self.username,
                password=self.password,
                port=self.port,
            ) as f:
                content = f.read().decode("utf-8")
        except ConnectionResetError:
            succ, err_msg = self._reset_and_reconnect()
            if not succ:
                return succ, err_msg
            with smbclient.open_file(
                path=remote_full_path,
                mode="rb",
                username=self.username,
                password=self.password,
                port=self.port,
            ) as f:
                content = f.read().decode("utf-8")
        except Exception as e:
            succ = False
            err_msg = str(e)
            logger.error(f"Exception while getting task result: {e}")
            return succ, err_msg, None

        result_data = json.loads(content)
        if not isinstance(result_data, dict):
            logger.error("Error format.")
            return False, None, None
        file_task_id = result_data.get("TaskID", "")
        if file_task_id != task_id:
            logger.info("Unexpected task id, continue waiting.")
            succ = False
            return False, None, None
        raw_result = result_data.get("Result2", [])
        return succ, err_msg, raw_result

    def format_result(self, raw_results: list, shots: int) -> dict:
        result = {}
        for item in raw_results:
            key = item["Type"]
            val = int(item["Percent"] * shots)
            result[key] = val
        return result

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
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.debug(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # 1. Prepare task data
        logger.info("1. prepare data")
        transpile_results = data["transpile_results"]
        self.set_progress_by_task(self.TASK_STAGE_PREPARE_DATA)
        task_id = f"{job_id}-{data_index}"
        task_data = self._prepare_data(
            task_id, transpile_results, shots, num_qubits
        )

        # 2. Submit Task
        logger.info("2. Submit Task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg = self.submit_task(task_data)
        if not success:
            raise ValueError(f"Failed to submit task: {err_msg}")

        # 3. Get Result
        logger.info("3. wait for task_status=completed")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        task_id = f"{job_id}-{data_index}"
        success, err_msg, raw_results = Library.loop_with_timeout(
            self.get_task_result,
            self.max_job_wait_time,
            self.job_query_interval,
            task_id,
        )
        if not success:
            raise ValueError(
                f"Failed to get task [{job_id}] result: {err_msg}"
            )

        if raw_results is None or len(raw_results) == 0:
            raise ValueError(
                "Failed to getting job result. Result is None or empty"
            )

        # 4. Formate Result
        results = self.format_result(raw_results, shots)

        # 5. Save results and set driver status to ONLINE
        self.set_results(
            job_id,
            data_index,
            results=results,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
