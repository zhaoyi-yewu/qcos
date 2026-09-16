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

import stim

from collections import Counter
from loguru import logger
from schema import Optional

from wy_qcos.common.cmss.base_operation import (
    BaseOperation,
    OperationType,
)
from wy_qcos.common.constant import Constant
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.driver_gate_base import DriverGateBase
from wy_qcos.qec.qec_factory import QecFactory


class DriverStim(DriverGateBase):
    """Stim QEC 专用驱动."""

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "Stim驱动"
        self.description = "Stim驱动"
        self.tech_type = Constant.TECH_TYPE_GENERIC_SIMULATOR
        self.transpiler = Constant.TRANSPILER_CMSS
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CY,
            Constant.TWO_QUBIT_GATE_CZ,
            Constant.TWO_QUBIT_GATE_SWAP,
            Constant.TWO_QUBIT_GATE_ISWAP,
        ]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.default_results_type = self.DATA_TYPE_GATE_SEQUENCE
        self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
        self.default_data_type = DriverBase.DATA_TYPE_QASM2
        self.supported_code_types = [Constant.CODE_TYPE_QASM2]
        self.max_qubits = 10
        # qec_options schema
        self.qec_options_schema = {
            "qec_code": str,
            Optional("distance"): int,
            Optional("phy_bit_num"): int,
            Optional("logical_bit_num"): int,
            Optional("error_inject"): {
                "error_type": str,
                "noise_prob": float,
            },
        }

    def init_driver(self):
        """Init driver."""
        # pylint: disable=duplicate-code
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success, err_msgs
        """
        success = True
        err_msg = None
        return success, err_msg

    def close_driver(self):
        """Close driver."""

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """

    def validate_circuit(self, circuit: list):
        """Validate circuit.

        Args:
        circuit: circuit

        Returns:
            true for succ and false for failure
        """
        for gate in circuit:
            if not isinstance(gate, BaseOperation):
                return False
            if (
                gate.operation_type != OperationType.SINGLE_QUBIT_OPERATION
                and gate.operation_type != OperationType.DOUBLE_QUBIT_OPERATION
            ):
                continue
            if gate.name not in self.supported_basis_gates:
                return False
        return True

    def convert_circuit(self, raw_circuit: list, num_qubits: int):
        """Convert to stim circuit.

        Args:
            raw_circuit: raw_circuit
            num_qubits: num of qubits

        Returns:
            stim cricuit
        """
        circuit = stim.Circuit()
        for gate in raw_circuit:
            if (
                gate.operation_type
                == OperationType.SINGLE_QUBIT_OPERATION.value
                or gate.operation_type
                == OperationType.DOUBLE_QUBIT_OPERATION.value
            ):
                logger.info(f"gate: {gate}, gate.name :{gate.name}")
                circuit.append(gate.name.upper(), gate.targets)
        return circuit

    def format_result(self, logic_res: list) -> dict:
        """format_result.

        Args:
            logic_res: logical result
            num_qubits: num of qubits

        Returns:
            formatted result (dict)
        """
        count_dict = Counter(logic_res)
        return {str(k): v for k, v in count_dict.items()}

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
            qec_options: qec_options
        """
        if qec_options is None:
            raise ValueError("Qec_options are needed for qec.")
        qec_code_str = qec_options.get("qec_code", "")
        if qec_code_str == "":
            raise ValueError("Qec_code is mandatory for qec.")
        distance = qec_options.get("distance", None)
        phy_bit_num = qec_options.get("phy_bit_num", None)
        logical_bit_num = qec_options.get("logical_bit_num", None)

        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )
        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)
        raw_circuit = data["transpile_results"]
        valid = self.validate_circuit(raw_circuit)
        if not valid:
            raise ValueError("Unsupported quantum circuit.")

        circuit = self.convert_circuit(raw_circuit, num_qubits)
        factory = QecFactory(None)
        qec_code = factory.create(qec_code_str)
        if distance is not None:
            qec_code.set_distance(distance)
        if phy_bit_num is not None:
            qec_code.set_physical_bit_num(phy_bit_num)
        if logical_bit_num is not None:
            qec_code.set_logical_bit_num(logical_bit_num)

        formatted_circuit = qec_code.validate_and_format_circuit(
            circuit, num_qubits
        )
        logger.info(f"formatted_circuit: {formatted_circuit}")
        error_inject = qec_options.get("error_inject", None)
        encodded_circuit = qec_code.encode(
            formatted_circuit,
            error_inject=error_inject,
        )
        logger.info(f"encodded_circuit: {encodded_circuit}")

        sampler = encodded_circuit.compile_sampler()
        samples = sampler.sample(shots=shots)
        qec_code.compute_samples(formatted_circuit, samples)

        err_pos = qec_code.decode(formatted_circuit)
        corrected_bits = qec_code.correct(formatted_circuit, err_pos=err_pos)
        logic_res = qec_code.logical_measure(formatted_circuit, corrected_bits)
        logger.info(f"logic_res: {logic_res}")

        result = self.format_result(logic_res)
        self.set_results(
            job_id,
            data_index,
            results=result,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

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
        max_qubits_value = self.driver_options.get("max_qubits")
        if max_qubits_value is not None:
            self.set_max_qubits(max_qubits_value)

    def get_qec_options_schema(self):
        """Get qec options schema."""
        return self.qec_options_schema
