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
from lqcloud import LQCloudProvider, QuantumCircuit
from schema import Or

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase


class DriverLogicalQubit(DriverBase):
    """逻辑比特 QZ01 超导驱动.

    QZ01 driver
    https://cloud.logicalqubit.com
    """

    def __init__(self) -> None:
        super().__init__()
        self.backend = None
        self.provider = None
        self.qpu_name = None
        self.url = None
        self.token = None
        self.version = "0.0.1"
        self.alias_name = "逻辑比特 QZ01 超导驱动"
        self.description = "逻辑比特 QZ01 超导驱动"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_SDG,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_aggregation = False
        self.max_qubits = 17
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

    def fetch_configs(self):
        """Fetch configs."""
        extra_configs = self.get_configs()
        self.token = extra_configs.get("token", "")
        self.url = extra_configs.get("url", "")
        self.qpu_name = extra_configs.get("chip_name", "")
        self.provider = LQCloudProvider(
            api_key=self.token,
            url=self.url,
        )
        self.backend = self.provider.get_backend(self.qpu_name)

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
                    "readout_error": {str: Or(float, int)},
                    "coupler_error": {str: Or(float, int)},
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

    def convert_code(self, transpile_results, phys_to_logical):
        """Convert code.

        Args:
            transpile_results: transpile results
            phys_to_logical: phys to logical

        Returns:
            converted code
        """
        qc = QuantumCircuit(self.max_qubits, self.max_qubits)
        method_mapping = {
            "h": qc.h,
            "s": qc.s,
            "sdg": qc.sdg,
            "t": qc.t,
            "rx": qc.rx,
            "ry": qc.ry,
            "rz": qc.rz,
            "cz": qc.cz,
        }
        measure_list = []
        for operation in transpile_results:
            gate_name = operation.name
            if operation.operation_type == 2:
                method_mapping[gate_name](
                    operation.targets[0], operation.targets[1]
                )
                continue
            if gate_name == "measure":
                measure_list.append(operation.targets[0])
                continue
            if gate_name == "sync":
                qc.barrier()
                continue
            if operation.arg_value:
                method_mapping[gate_name](
                    operation.arg_value[0], operation.targets[0]
                )
            else:
                method_mapping[gate_name](operation.targets[0])
        qc.barrier()
        for key, value in phys_to_logical.items():
            if key in measure_list:
                qc.measure(key, value)
        return qc

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
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
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )
        final_layout = data["final_layout_dict"]
        final_layout_dict = list(final_layout.values())[0]
        n_logical = max(final_layout_dict.keys()) + 1
        [int(final_layout_dict[k]) for k in range(n_logical)]
        phys_to_logical = {
            int(p): int(l) for l, p in final_layout_dict.items()
        }

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # 1. Convert code
        logger.info("1. convert code")
        self.set_progress_by_task(self.TASK_STAGE_VALIDATING)
        transpile_results = data["transpile_results"]
        final_code = self.convert_code(transpile_results, phys_to_logical)

        # 2. Submit task
        logger.info("2. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        task = self.submit_task(final_code, shots)

        # 3. Wait and get task results
        logger.info("3. wait and get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, _results = self.get_task_results(task)
        if not success:
            raise ValueError(f"failed to get task {task} result")

        # 4. Normalize results
        logger.info("4. normalize results")
        results = self.convert_results(_results)
        self.set_results(
            job_id,
            data_index,
            results=results,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )

        # 5. Save results and set driver status to ONLINE
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def submit_task(self, qc, shots):
        """Submit task.

        Args:
            qc: task info
            shots: circuit shots

        Returns:
            task
        """
        task = self.backend.run(qc, shots=shots)
        return task

    def get_task_results(self, task):
        """Get task results.

        Args:
            task: task id
        Returns:
            success, response
        """
        success = False
        result = task.result(timeout=3600)
        if result:
            success = True
            return success, result
        return success, None

    def convert_results(self, results):
        """Convert results.

        Args:
            results: task results

        Returns:
            converted task results
        """
        dict_result = results.get_counts()
        return dict_result
