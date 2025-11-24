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

from loguru import logger
from schema import Optional

from spinqit import get_compiler
from spinqit.backend import get_spinq_cloud, SpinQCloudConfig

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers import driver_errors
from qcos.drivers.device import Device
from qcos.drivers.driver_base import DriverBase


class DriverSpinQCloudBase(DriverBase):
    """量旋科技 核磁驱动 (Cloud版本)

    SpinQ NMR driver (Cloud)
    https://cloud.spinq.cn
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "量旋科技 核磁量子计算机驱动"
        self.description = "量旋科技 核磁量子计算机驱动"
        self.enable_transpiler = False
        self.tech_type = Constant.TECH_TYPE_NMR
        self.supported_basis_gates = [
            # Gates: H, I, X, Y, Z, RX, RY, RZ, P, S, T, TDG, U, CX, CY, CZ,
            # SWAP, CCX, CCZ
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.SINGLE_QUBIT_GATE_P,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_TDG,
            Constant.SINGLE_QUBIT_GATE_U,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CY,
            Constant.TWO_QUBIT_GATE_CZ,
            Constant.TWO_QUBIT_GATE_SWAP,
            Constant.THREE_QUBIT_GATE_CCX,
        ]
        self.enable_circuit_aggregation = False
        self.max_qubits = 2
        self.default_data_type = DriverBase.DATA_TYPE_QASM2
        self.supported_code_types = [DriverBase.DATA_TYPE_QASM2]

        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_COMPILE: 5,
            self.TASK_STAGE_USER_AUTHENTICATION: 10,
            self.TASK_STAGE_SUBMIT_TASK: 20,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }

        # private variables
        self.remote_host = None
        self.remote_port = None
        self.username = None
        self.password_key = None
        self.platform_name = None

    def init_driver(self):
        """Init driver"""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver"""

    def validate_driver_configs(self, configs):
        """Validate driver configs

        Args:
            configs: configs dictionary

        Returns:
            success or fail, err_msg
        """
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            Optional("remote_host"): str,
            Optional("remote_port"): int,
            "username": str,
            "password_key": str,
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if _success:
            self.remote_host = configs.get("remote_host", None)
            self.remote_port = configs.get("remote_port", None)
            self.username = configs.get("username", "")
            self.password_key = configs.get("password_key", "")
        else:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        return success, err_msg

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
        ir = None
        backend = None
        host = None
        if self.remote_host and self.remote_port:
            host = f"http://{self.remote_host}:{self.remote_port}"

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # 1. compile
        self.set_progress_by_task(self.TASK_STAGE_COMPILE)
        logger.info("1. compile")

        # remove measures
        new_source_code_list = []
        for code in data["source_code"].split("\n"):
            new_op_list = []
            op_list = code.split(";")
            for op in op_list:
                if not op.strip().startswith("measure"):
                    new_op_list.append(op)
            new_source_code_list.append(";".join(new_op_list))
        new_source_code = "\n".join(new_source_code_list)

        with Library.create_temp_file(
            new_source_code.encode("utf-8"),
            dir=self.temp_driver_dir,
            dir_mode=0o777,
        ) as qasm_temp_file:
            compiler = get_compiler("qasm")
            ir = compiler.compile(qasm_temp_file.name, 0)

        # 2. authentication
        self.set_progress_by_task(self.TASK_STAGE_USER_AUTHENTICATION)
        logger.info("2. authentication")
        with Library.create_temp_file(
            self.password_key.encode("utf-8"),
            dir=self.temp_driver_dir,
            dir_mode=0o777,
        ) as key_temp_file:
            backend = get_spinq_cloud(
                self.username, key_temp_file.name, host=host
            )

        platform = backend.get_platform(self.platform_name)
        logger.info(
            f"SpinQ {self.platform_name} has "
            f"{platform.machine_count} active machines"
        )
        if not platform.available():
            raise driver_errors.DriverServiceUnavailable(
                f"No more {self.platform_name} machines available"
            )

        # 3. submit task
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        logger.info("3. submit task and wait results")
        config = SpinQCloudConfig()
        config.configure_platform(self.platform_name)
        config.configure_shots(shots)
        config.configure_task(f"qcos-{job_id}", f"qcos-{job_id}")
        _results = backend.execute(ir, config)

        # 4. get results
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        logger.info("4. get and convert results")
        results = self.convert_results(_results.probabilities, shots)

        # 5. Save results and set driver status to ONLINE
        self.set_results(job_id, data_index, results=results)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def convert_results(self, results, shots):
        """Convert results

        Args:
             results (dict): spinq results
             shots (int): number of shots

        Returns:
            qcos results
        """

        converted_results = {}
        remaining = shots

        keys = list(results.keys())
        for i, key in enumerate(keys):
            prob = results[key]
            if i == len(keys) - 1:
                value = remaining
            else:
                value = round(prob * shots)
                value = min(value, remaining)
                remaining -= value
            if value != 0:  # remove empty results
                converted_results[key] = value
        return converted_results

    def cancel(self, job_id):
        """Cancel running job in driver

        Args:
            job_id: job id
        """
        logger.info(f"Cancel job: job_id: {job_id}")
