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

import logging
import tempfile

from schema import Optional

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.transpiler.cmss.common.measure import Measure

logger = logging.getLogger(__name__)


class DriverBase:
    """Quantum Computer base driver."""

    # Data types
    DATA_TYPE_GATE_SEQUENCE = "gate_sequence"
    DATA_TYPE_QUBO = "qubo"
    DATA_TYPE_QASM2 = "qasm2"
    DATA_TYPE_QASM3 = "qasm3"
    DATA_TYPES = [
        DATA_TYPE_GATE_SEQUENCE,
        DATA_TYPE_QUBO,
        DATA_TYPE_QASM2,
        DATA_TYPE_QASM3,
    ]

    # TASK STAGES
    TASK_STAGE_START = "start"
    TASK_STAGE_INIT = "init"
    TASK_STAGE_LOADING = "loading"
    TASK_STAGE_VALIDATING = "validating"
    TASK_STAGE_USER_AUTHENTICATION = "user_authentication"
    TASK_STAGE_CHECK_DEVICE_STATUS = "check_device_status"
    TASK_STAGE_COMPILE = "compile"
    TASK_STAGE_UPLOAD_FILE = "upload_file"
    TASK_STAGE_PREPARE_DATA = "prepare_data"
    TASK_STAGE_SUBMIT_TASK = "submit_task"
    TASK_STAGE_WAIT_TASK = "wait_task"
    TASK_STAGE_GET_RESULTS = "get_results"
    TASK_STAGE_COMPLETE = "complete"

    # http request headers
    default_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN",
    }
    auth_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN",
        "Authorization": None,
    }

    temp_driver_dir = f"/{tempfile.gettempdir()}/qcos/drivers/"

    def __init__(self):
        # driver version
        self.version = "unknown"
        # driver name
        self.name = self.__class__.__name__
        # driver alias name
        self.alias_name = None
        # description
        self.description = None
        # module name
        self._module_name = None
        # class name
        self._class_name = None
        # enable transpiler or not
        self.enable_transpiler = True
        # transpiler type
        self.transpiler = Constant.TRANSPILER_CMSS
        # supported code types (enable_transpiler=False only)
        self.supported_code_types = None
        # quantum computer technology type
        self.tech_type = None
        # enable circuit aggregation or not
        self.enable_circuit_aggregation = False
        # max number of qubits
        self.max_qubits = 0
        # available number of qubits.
        # This value may vary according to the status of quantum hardware
        self.available_num_qubits = -1
        # supported basis gates
        self.supported_basis_gates = None
        # supported transpilers
        self.supported_transpilers = []

        # task stage to track progress
        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_WAIT_TASK: 50,
            self.TASK_STAGE_COMPLETE: 100,
        }

        # job runtime data
        self.job_runtime_data = {
            "run_progress": 0,
            "device_status": Device.DEVICE_STATUS_UNKNOWN,
            "configs": {},
            # results from run(): fetches the results from quantum computer
            # format: {JOB_ID: {"results": RESULTS}}
            "results": {},
        }

        # measurement results fetch mode
        self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
        # default data type in run()
        self.default_data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE
        # driver_options
        self.driver_options = {
            "max_qubits": 10,
            "enable_wirecut": False,
        }
        # driver_options schema
        self.driver_options_schema = {Optional("enable_wirecut"): bool}

    def validate_driver(self):
        """Validate driver."""
        success = True
        err_msgs = []
        if self.enable_transpiler:
            if self.supported_code_types:
                success = False
                err_msgs.append(
                    "supported_code_types should not be specified "
                    "when driver.enable_transpiler=True"
                )
            if self.transpiler not in self.supported_transpilers:
                success = False
                err_msgs.append(
                    "driver.transpiler must be specified in "
                    "driver.supported_transpilers list"
                )
        else:
            if not self.supported_code_types:
                success = False
                err_msgs.append(
                    "supported_code_types must be specified "
                    "when driver.enable_transpiler=False"
                )
        return success, "\n".join(err_msgs)

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs to validate

        Returns:
            success, err_msgs
        """
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} "
            f"must implement method: validate_driver_configs"
        )

    def init_driver(self):
        """Init driver."""
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} "
            f"must implement method: init_driver"
        )

    def close_driver(self):
        """Close driver."""
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} "
            f"must implement method: close_driver"
        )

    def get_driver_options_schema(self):
        """Get driver options schema.

        Returns:
            driver options schema
        """
        return self.driver_options_schema

    def update_driver_options(self, driver_options):
        """Update driver options.

        Args:
            driver_options: new driver options
        """
        self.driver_options.update(driver_options)

    def get_driver_info(self):
        """Show driver info."""
        show_list = [
            f"[{self.__class__.__name__}]",
            f"name: {self.name}",
            f"alias_name: {self.alias_name}",
            f"description: {self.get_description()}",
            f"version: {self.version}",
            f"enable_transpiler: {self.enable_transpiler}",
            f"transpiler: {self.transpiler}",
            f"enable_circuit_aggregation: {self.enable_circuit_aggregation}",
            f"results_fetch_mode: {self.results_fetch_mode}",
            f"max_qubits: {self.max_qubits}",
        ]
        return "\n".join(show_list)

    def set_name(self, name):
        """Set driver name.

        Args:
            name: driver_name
        """
        self.name = name

    def get_name(self):
        """Get driver name.

        Returns:
            driver name
        """
        return self.name

    def set_alias_name(self, alias_name):
        """Set driver alias name.

        Args:
            alias_name: alias_name
        """
        self.alias_name = alias_name

    def get_alias_name(self):
        """Get driver alias name.

        Returns:
            driver alias name
        """
        return self.alias_name

    def get_description(self):
        """Get driver description.

        Returns:
            driver description
        """
        if self.description is None:
            return Library.get_brief_description(self.__doc__)
        return self.description

    def set_module_name(self, module_name):
        """Set module name.

        Args:
            module_name: module name
        """
        self._module_name = module_name

    def get_module_name(self):
        """Get module name.

        Returns:
            module name
        """
        return self._module_name

    def set_class_name(self, class_name):
        """Set class name.

        Args:
            class_name: class name
        """
        self._class_name = class_name

    def get_class_name(self):
        """Get class name.

        Returns:
            class name
        """
        return self._class_name

    def get_transpiler(self):
        """Get transpiler."""
        if self.enable_transpiler:
            return self.transpiler
        return None

    def get_supported_code_types(self):
        """Get supported code types."""
        return self.supported_code_types

    def get_supported_basis_gates(self):
        """Get supported basis gates.

        Returns:
            list of supported basis gates
        """
        return self.supported_basis_gates

    def get_supported_transpilers(self):
        """Get supported transpilers.

        Returns:
            list of supported transpilers
        """
        return self.supported_transpilers

    def get_tech_type(self):
        """Get tech type."""
        return self.tech_type

    def set_progress(self, progress):
        """Set progress.

        Args:
            progress: progress percentage in integer between 0 and 100
        """
        self.job_runtime_data["run_progress"] = progress

    def set_progress_by_task(self, task_name):
        """Set progress by task name.

        Args:
            task_name: task name
        """
        progress = self.task_stages.get(task_name, None)
        if progress is not None:
            self.job_runtime_data["run_progress"] = progress

    def get_progress(self):
        """Get progress.

        Returns:
            progress percentage in integer between 0 and 100
        """
        return self.job_runtime_data["run_progress"]

    def set_device_status(self, device_status):
        """Set device status.

        Args:
            device_status: device status
        """
        self.job_runtime_data["device_status"] = device_status

    def set_configs(self, configs):
        """Set configs.

        Args:
            configs: configs to set
        """
        self.job_runtime_data["configs"] = configs

    def get_configs(self):
        """Get configs.

        Returns:
            configs
        """
        return self.job_runtime_data["configs"]

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} "
            f"must implement method: fetch_configs"
        )

    def run(
        self,
        job_id,
        num_qubits,
        data,
        data_type=DATA_TYPE_GATE_SEQUENCE,
        shots=1,
    ):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type (Default value = DATA_TYPE_GATE_SEQUENCE)
            shots: shots (Default value = 1)
        """
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} must implement method: run"
        )

    def dry_run(
        self,
        job_id,
        num_qubits,
        data,
        data_type=DATA_TYPE_GATE_SEQUENCE,
        shots=1,
    ):
        """Dry-run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type (Default value = DATA_TYPE_GATE_SEQUENCE)
            shots: shots (Default value = 1)
        """
        data_index = data["index"]
        logger.info(
            f"Dry-run: job_id: {job_id}, shots: {shots}, "
            f"num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )

        result = self.get_fake_results(num_qubits, shots, data)
        self.set_results(job_id, data_index, results=result)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        raise NotImplementedError(
            f"Driver: {self.__class__.__name__} must implement method: cancel"
        )

    def set_results(self, job_id, data_index, results):
        """Set job results.

        Sample: results = {"00": 9, "11": 1}.

        Args:
            job_id: job ID
            data_index: code index
            results: results
        """
        if job_id not in self.job_runtime_data["results"]:
            self.job_runtime_data["results"][job_id] = {}
        self.job_runtime_data["results"][job_id][data_index] = results

    def get_results(self, job_id=None, data_index=None):
        """Get results.

        Args:
            job_id: job ID (Default value = None)
            data_index: code index (Default value = None)

        Returns:
            results
        """
        if job_id is not None:
            if data_index is not None:
                return Library.get_nested_dict_value(
                    self.job_runtime_data["results"],
                    job_id,
                    data_index,
                    default=None,
                )
            return Library.get_nested_dict_value(
                self.job_runtime_data["results"], job_id, default=None
            )
        return self.job_runtime_data["results"]

    def get_default_data_type(self):
        """Get default data type.

        Returns:
            default data type
        """
        return self.default_data_type

    def set_max_qubits(self, max_qubits):
        """Set max qubits.

        Args:
            max_qubits: max qubits
        """
        self.max_qubits = max_qubits

    def get_max_qubits(self):
        """Get max qubits.

        Returns:
            max qubits
        """
        return self.max_qubits

    def get_fake_results(self, num_qubits, shots, data):
        """Get fake results.

        Args:
            num_qubits: number of qubits
            shots: number of shots
            data: source data
        """
        bit_length = 0
        gate_list = data["transpile_results"]
        measure_qubits = set()
        if gate_list:
            for obj in gate_list:
                if isinstance(obj, Measure):
                    measure_qubits.update(obj.targets)
            bit_length = len(measure_qubits)
        else:
            if not num_qubits:
                max_qubits = self.max_qubits
                if not max_qubits:
                    max_qubits = 5
                num_qubits = max_qubits
            bit_length = num_qubits
        return Library.generate_binary_combinations(bit_length, shots)

    def get_enable_wirecut(self):
        """Get enable wirecut.

        Returns:
            bool: enable wirecut
        """
        return self.driver_options["enable_wirecut"]

    def get_driver_options(self):
        """Get driver options.

        Returns:
            dict: driver options
        """
        return self.driver_options
