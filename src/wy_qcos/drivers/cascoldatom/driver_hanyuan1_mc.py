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
from smbprotocol import smbclient

from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase



class DriverHanyuan1MC(DriverBase):
    """五岳中科酷原-汉原1 中性原子驱动, 后端为汉原原生测控系统.

    Wuyue Cascoldatom Hanyuan1 driver
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "中科酷原-汉原1-MC 中性原子驱动"
        self.description = "中科酷原-汉原1-MC 中性原子驱动"
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
        self.ip_address = "192.168.1.100"
        self.port = 445
        self.user = "user"
        self.pwd = "123456"

    def init_driver(self):
        """Init driver."""
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
        driver_config_schema = copy.deepcopy(self.default_driver_config_schema)
        driver_config_schema.update({
            "ip_address": str,
            "port": int,
            "user": str,
            "pwd": str,
        })
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if _success:
            self.ip_addr = configs.get("ip_address", "192.168.1.100")
            self.port = configs.get("port", 445)
            self.user = configs.get("user", "user")
            self.pwd = configs.get("pwd", "123456")
            with smbclient.open_session(self.ip_addr, username=self.user, password=self.pwd, port=self.port):
                pass
        else:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        return success, err_msg

    def close_driver(self):
        """Close driver."""

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
            single_pulse = {}
            single_pulse["time"] = time
            if gate.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value:
                single_pulse["type"] = 2
                if len(gate.arg_value) == 0:
                    logger.warning("wrong arg value parameter")
                    continue
                phase = 0
                degree = gate.arg_value[0]
                if len(gate.arg_value) >= 2:
                    phase = gate.arg_value[1]
                    continue
                param_lst = [gate.targets[0], round(degree, 6), round(phase, 6), 0, 0]
                single_pulse["param"] = param_lst
                pulse_data.append(single_pulse)
                time = time + 1
                qubit_id_list.extend(gate.targets)
            if gate.operation_type == OperationType.DOUBLE_QUBIT_OPERATION.value:
                single_pulse["type"] = 3
                if len(gate.arg_value) == 0:
                    logger.warning("wrong arg value parameter")
                    continue
                phase = 0
                degree = gate.arg_value[0]
                if len(gate.arg_value) >= 2:
                    phase = gate.arg_value[1]
                    continue
                param_lst = [gate.targets[0], round(degree, 6), round(phase, 6), 0, 0, 0, gate.targets[1]]
                single_pulse["param"] = param_lst
                pulse_data.append(single_pulse)
                time = time + 1
                qubit_id_list.extend(gate.targets)
        return pulse_data, qubit_id_list

    def _generate_qubit_map(self, transpile_results: list, qubit_id_list: list) -> list:
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
            
            for value in qubit_id_list:
                if value in meas_qubit_list:
                    qubit_map.append([value, 0, 0, 1])
                else:
                    qubit_map.append([value, 0, 0, 0])
        return qubit_map

    def _prepare_data(self, task_id: str, transpile_results: list, shots: int, num_qubits: int):
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
        task_data["Pulse"], qubit_id_list= self._generate_pulse(transpile_results)
        task_data["QubitMap"] = self._generate_qubit_map(transpile_results, qubit_id_list)
        return task_data

    def submit_task(self, task_data):
        """submit_task.

        Args:
            task_data: task_data

        Returns:
            qubit map data
        """


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
        task_data = self._prepare_data(task_id, transpile_results, shots, num_qubits)

        # 2. Submit Task
        logger.info("2. Submit Task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg = self.submit_tasks(task_data)
        if not success:
            raise ValueError(f"Failed to submit task: {err_msg}")

        # 4. Wait for task_status is completed or failed
        logger.info("4. wait for task_status=completed")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        task_id = f"{job_id}-{data_index}"
        success, err_msg, results = Library.loop_with_timeout(
            self.check_task_status,
            3600,
            5,
            task_id,
            expect_task_status=[
                self.task_status_completed,
                self.task_status_failed,
            ],
        )
        if not success:
            raise ValueError(f"Failed to wait for task [{job_id}]: {err_msg}")

        if results is None or results != self.task_status_completed:
            raise ValueError(
                f"Failed to wait for task [{job_id}]: {err_msg},"
                f"task status:{results}"
            )

        # 7. Save results and set driver status to ONLINE
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

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        device_running_info = {"status": "online"}
        return device_running_info
