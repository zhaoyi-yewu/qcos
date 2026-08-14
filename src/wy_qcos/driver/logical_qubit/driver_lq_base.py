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

from datetime import datetime

from loguru import logger
from lqcloud import LQCloudProvider, QuantumCircuit
from schema import Or, Optional

from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.common.cmss.qasm_converter import QasmConverter
from wy_qcos.common.constant import Constant, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit as QCircuit
from wy_qcos.transpiler.high_performance import OperationType


class DriverLogicalQubitBase(DriverBase):
    """逻辑比特驱动基类.

    Logical Qubit Base driver
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
            Constant.SINGLE_QUBIT_GATE_I,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_SDG,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.supported_transpilers = [
            Constant.TRANSPILER_CMSS,
            Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS,
        ]
        self.enable_circuit_aggregation = False
        self.optimized_circuit = None
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
        self.driver_options_schema = {
            Optional("qes"): {
                Optional("dynamical_decoupling"): {
                    Optional("enable"): bool,
                }
            },
            Optional("qem"): {
                Optional("readout_error"): {
                    Optional("enable"): bool,
                }
            },
        }
        self.enable_device_monitor = True

    def init_driver(self):
        """Init driver."""
        extra_configs = self.get_configs()
        self.token = extra_configs.get("token", "")
        self.url = extra_configs.get("url", "")
        self.qpu_name = extra_configs.get("chip_name", "")
        self.provider = LQCloudProvider(
            api_key=self.token,
            url=self.url,
        )
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

    def update_driver_options(self, driver_options):
        """Update driver options.

        Args:
            driver_options: new driver options
        """
        self.driver_options.update(driver_options)

    def fetch_configs(self):
        """Fetch configs."""
        extra_configs = self.get_configs()
        self.token = extra_configs.get("token", "")
        self.url = extra_configs.get("url", "")
        self.qpu_name = extra_configs.get("chip_name", "")
        try:
            self.provider = LQCloudProvider(
                api_key=self.token,
                url=self.url,
            )
            self.backend = self.provider.get_backend(self.qpu_name)
        except Exception as e:
            raise ValueError(f"Logical_qubit exception: {e}") from e

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

    def convert_code_to_qasm(
        self, num_qubits: int, src_code: str, transpile_results
    ):
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

        circ = QCircuit(num_qubits)
        circ.append_operations(transpile_results)
        converter = QasmConverter(circ)
        qasm_code = converter.to_qasm2()
        return qasm_code

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
            "id": qc.id,
            "h": qc.h,
            "s": qc.s,
            "sdg": qc.sdg,
            "t": qc.t,
            "x": qc.x,
            "y": qc.y,
            "z": qc.z,
            "rz": qc.rz,
            "cz": qc.cz,
        }
        measure_list = []
        for operation in transpile_results:
            gate_name = operation.name
            if (
                operation.operation_type
                == OperationType.DOUBLE_QUBIT_OPERATION
                or operation.operation_type == 2
            ):
                method_mapping[gate_name](
                    operation.targets[0], operation.targets[1]
                )
                continue
            if gate_name == "measure":
                measure_list.append(operation.targets[0])
                continue
            if gate_name == "sync":
                qc.barrier(operation.targets[0])
                continue
            if operation.arg_value:
                method_mapping[gate_name](
                    operation.arg_value[0], operation.targets[0]
                )
            else:
                method_mapping[gate_name](operation.targets[0])
        cbits = 0
        qc.barrier()
        for key, value in phys_to_logical.items():
            if key in measure_list:
                qc.measure(key, cbits)
                cbits += 1
        return qc

    def get_device_info(self):
        """Get device info.

        Returns:
            device info
        """
        try:
            cfg = self.provider.get_backend_config(self.qpu_name)
            return True, None, cfg
        except Exception as e:
            return False, str(e) if str(e) else "request failed", None

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        success, err_msg, cfg = self.get_device_info()
        device_running_info = {}
        if not success:
            logger.debug(f"Failed to get device info: {err_msg}")
            device_running_info["status"] = "offline"
            device_running_info["details"] = {}
            return device_running_info

        fidelity_2q_values_list = []
        for qubit in cfg["properties"]["coupler_metrics"]:
            qubit_couple = qubit.get("qubits")
            double_qubit_fidelity = qubit.get("cz_fidelity")
            qubits_data = {
                "qubits": qubit_couple,
                "cz_fidelity": double_qubit_fidelity,
            }
            fidelity_2q_values_list.append(qubits_data)

        fidelity_1q_values_list = []
        for qubit in cfg["properties"]["qubit_metrics"]:
            idx = qubit.get("id")
            single_fidelity = qubit.get("xeb_fidelity", 0.0)
            t1_time = qubit.get("t1", 0.0)
            t2_time = qubit.get("t2", 0.0)
            readout_fidelity_0 = qubit.get("measure_f0", 0.0)
            readout_fidelity_1 = qubit.get("measure_f1", 0.0)
            qubit_data = {
                "qubit_id": idx,
                "xeb_fidelity": single_fidelity,
                "t1": t1_time,
                "t2": t2_time,
                "readout_fidelity_0": readout_fidelity_0,
                "readout_fidelity_1": readout_fidelity_1,
            }
            fidelity_1q_values_list.append(qubit_data)

        device_running_info["details"] = {}
        device_running_info["details"]["calibration"] = {}
        qpu_update_time = cfg["properties"].get("last_update", None)
        if qpu_update_time:
            dt_obj = datetime.strptime(qpu_update_time, "%Y-%m-%d %H:%M:%S")
            target_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")
            target_str = datetime.strptime(target_str, "%Y-%m-%d %H:%M:%S.%f")
            result = Library.to_iso(target_str.timestamp())
            result = result + ".000000"
            device_running_info["details"]["calibration"][
                "last_updated_at"
            ] = result

        api_key = self.token
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self.url}/api/v1/qpus/queue-stats"
        status_code, reason, text, response_obj = Library.call_http_api(
            url, method=HttpMethod.GET, headers=headers, verify_ssl=True
        )
        data = response_obj.json()
        queued = (data.get(self.qpu_name)).get("queued")
        running = (data.get(self.qpu_name)).get("running")
        total = (data.get(self.qpu_name)).get("total_pending")

        vendor_job_count = {
            "queued": queued,
            "running": running,
            "total": total,
        }
        available_qubits = cfg.get("qubits")
        device_running_info["available_qubits"] = available_qubits

        status = cfg.get("status", "offline")
        if status == "active":
            device_running_info["status"] = Device.DEVICE_STATUS_ONLINE
        elif status == "maintenance":
            device_running_info["status"] = Device.DEVICE_STATUS_MAINTAIN
        else:
            device_running_info["status"] = Device.DEVICE_STATUS_OFFLINE
        device_running_info["details"]["calibration"]["qubit_metrics"] = (
            fidelity_1q_values_list
        )
        device_running_info["details"]["calibration"]["coupler_metrics"] = (
            fidelity_2q_values_list
        )
        device_running_info["details"]["vendor_job_count"] = vendor_job_count
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
        src_code = data["source_code"]
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
        success, err_msg, task = self.submit_task(final_code, shots)
        if not success:
            raise ValueError(f"failed to submit task: {err_msg}")

        # 3. Wait task results
        logger.info("3. wait task results")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _results = self.get_task_results(task)
        if not success:
            raise ValueError(f"failed to get task result: {err_msg}")

        # 4. Get task results
        logger.info("4. get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        results = self.convert_results(_results)
        line_result = results
        optimization = self.convert_code_to_qasm(
            num_qubits, src_code, transpile_results
        )
        final_result = {
            "lineResult": line_result,
        }
        self.set_results(
            job_id,
            data_index,
            results=results,
            raw_results=final_result,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_optimized_circuit(optimization)
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
        try:
            enable_readout_correction = False
            enable_dynamic_decoupling = False
            qes = self.driver_options.get("qes", None)
            qem = self.driver_options.get("qem", None)
            if qes is not None:
                enable_dynamic_decoupling = qes.get(
                    "dynamical_decoupling"
                ).get("enable")
            if qem is not None:
                enable_readout_correction = qem.get("readout_error").get(
                    "enable"
                )
            if enable_dynamic_decoupling:
                qc.dynamic_decoupling = True
            task = self.backend.run(
                qc,
                shots=shots,
                enable_readout_correction=enable_readout_correction,
            )
            return True, None, task
        except Exception as e:
            return False, str(e), None

    def get_task_results(self, task):
        """Get task results.

        Args:
            task: task
        Returns:
            success, response
        """
        success = False
        try:
            result = task.result(timeout=300)
            if result:
                success = True
            return success, None, result
        except Exception as e:
            return success, str(e), None

    def convert_results(self, results):
        """Convert results.

        Args:
            results: task results

        Returns:
            converted task results
        """
        dict_result = results.get_counts()
        return dict_result

    def set_optimized_circuit(self, optimized_circuit):
        """Set optimized circuit.

        Args:
            optimized_circuit: the optimized circuit
        """
        self.optimized_circuit = optimized_circuit

    def get_optimized_circuit(self):
        """Get optimized circuit.

        Returns:
            optimized_circuit
        """
        return self.optimized_circuit
