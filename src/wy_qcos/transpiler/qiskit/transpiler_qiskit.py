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

import qiskit
import qiskit.qasm3
import qiskit.qasm2
from qiskit_aer import QasmSimulator, AerSimulator
from qiskit.transpiler import Target, CouplingMap
from qiskit.transpiler import InstructionProperties
from qiskit.circuit import Parameter
from qiskit.circuit.library import (
    RXGate,
    RYGate,
    RZGate,
    HGate,
    XGate,
    Reset,
    Measure,
    CZGate,
    CXGate,
)

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.common.errors import TranspilerException
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.transpiler_base import TranspilerBase


class TranspilerQiskit(TranspilerBase):
    """Transpiler Class for Qiskit."""

    def __init__(self, opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL):
        super().__init__()
        self.name = Constant.TRANSPILER_QISKIT
        # alias name
        self.alias_name = "IBM Qiskit"
        # version
        self.version = qiskit.__version__
        # supported code types
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3,
        ]
        # transpiler_options
        if (
            opt_level < Constant.MIN_OPTIMIZATION_LEVEL
            or opt_level > Constant.MAX_OPTIMIZATION_LEVEL
        ):
            raise TranspilerException(
                f"unsupported optimizing level. opt_level: {opt_level}"
            )

        self.transpiler_options = {
            # default optimization level
            "optimization_level": opt_level
        }
        # transpiler_options schema used in submit-job from user
        self.transpiler_options_schema = {Optional("optimization_level"): int}

    def init_transpiler(self):
        """Init transpiler."""

    def parse(self, src_code_dict: dict):
        """Parse src_code_dict.

        Args:
            src_code_dict: src_code_dict

        Returns:
            parse result
        """
        if isinstance(src_code_dict, dict) and len(src_code_dict) == 1:
            source_code: str = next(iter(src_code_dict.values()))
            logger.info(f"source_code:\n{source_code}")
            if "OPENQASM 3.0" in source_code:
                parse_result = qiskit.qasm3.loads(source_code)
            elif "OPENQASM 2.0" in source_code:
                inst = qiskit.qasm2.LEGACY_CUSTOM_INSTRUCTIONS
                parse_result = qiskit.qasm2.loads(
                    string=source_code,
                    custom_instructions=inst,
                )
            else:
                raise TranspilerException(
                    "unsupported openqasm version in qiskit transpiler"
                )

            self.total_qubits = parse_result.num_qubits
            return parse_result
        else:
            raise TranspilerException(
                "unsupported input for qiskit transpiler"
            )

    def transpile(
        self, parse_result: qiskit.QuantumCircuit, supp_basis_gates: list
    ):
        """Transpile codes.

        Args:
            parse_result(QuantumCircuit): parse result
            supp_basis_gates(list): supported basis gates

        Returns:
            transpiled quantum circuit
        """
        # other basis gates
        gates_map = {
            Constant.SINGLE_QUBIT_GATE_RX: RXGate(Parameter("θ")),
            Constant.SINGLE_QUBIT_GATE_RY: RYGate(Parameter("θ")),
            Constant.SINGLE_QUBIT_GATE_RZ: RZGate(Parameter("θ")),
            Constant.SINGLE_QUBIT_GATE_X: XGate(),
            Constant.SINGLE_QUBIT_GATE_H: HGate(),
            "reset": Reset(),
            Constant.TWO_QUBIT_GATE_CZ: CZGate(),
            Constant.TWO_QUBIT_GATE_CX: CXGate(),
            "measure": Measure(),
        }
        simulator = None
        driver_name = trans_cfg_inst.get_driver_name()
        if driver_name != "NoDriverQiskit":
            if driver_name == "DriverQiskitQasmSim":
                simulator = QasmSimulator()
            elif driver_name == "DriverQiskitAerSim":
                simulator = AerSimulator()
            else:
                raise TranspilerException(
                    f"invalid driver name: {driver_name}"
                )

            transpiled_circuit = qiskit.transpile(
                circuits=parse_result,
                backend=simulator,
                optimization_level=self.transpiler_options[
                    "optimization_level"
                ],
                basis_gates=supp_basis_gates,
            )

        else:
            # initialize qpu info
            qpu_config = trans_cfg_inst.get_qpu_cfg()
            # coupling map info
            coupling_map_info = [
                [] for _ in range(len(qpu_config["coupler_map"]))
            ]
            coupling_input: dict = qpu_config["coupler_map"]
            for key, value in coupling_input.items():
                pos = int(key[1:])
                coupling_map_info[pos] = [
                    int(value[0][1:]),
                    int(value[1][1:]),
                ]

            coupling_map = CouplingMap(coupling_map_info)

            # qiskit target set
            num_qubits = trans_cfg_inst.get_max_qubits()
            target = Target(num_qubits=num_qubits)

            for gate in supp_basis_gates:
                # single qubit gate info
                if gate == Constant.SINGLE_QUBIT_GATE_RX:
                    rx_err_info = [
                        0.0 for _ in range(trans_cfg_inst.get_max_qubits())
                    ]
                    rx_err_input: dict = qpu_config["rx_error"]
                    for key, value in rx_err_input.items():
                        pos = int(key[1:])
                        rx_err_info[pos] = float(value)

                    # single qubit gate target set
                    rxgate_error = {}
                    for qubit in range(num_qubits):
                        rxgate_error[(qubit,)] = InstructionProperties(
                            error=rx_err_info[qubit]
                        )

                    theta = Parameter("θ")
                    rx_param = RXGate(theta)
                    target.add_instruction(rx_param, rxgate_error)
                elif gate == Constant.SINGLE_QUBIT_GATE_RY:
                    ry_err_info = [
                        0.0 for _ in range(trans_cfg_inst.get_max_qubits())
                    ]
                    ry_err_input: dict = qpu_config["ry_error"]
                    for key, value in ry_err_input.items():
                        pos = int(key[1:])
                        ry_err_info[pos] = float(value)

                    rygate_error = {}
                    for qubit in range(num_qubits):
                        rygate_error[(qubit,)] = InstructionProperties(
                            error=ry_err_info[qubit]
                        )

                    theta = Parameter("θ")
                    ry_param = RYGate(theta)
                    target.add_instruction(ry_param, rygate_error)
                # two qubits gate info
                elif gate == Constant.TWO_QUBIT_GATE_CX:
                    cx_err_info = {}
                    for key, value in qpu_config["coupler_error"].items():
                        coupling_cx_pos = key[2:]
                        cx_key = (
                            int(coupling_cx_pos.split("_")[0]),
                            int(coupling_cx_pos.split("_")[1]),
                        )
                        cx_err_info[cx_key] = float(value)

                    # two qubits gate
                    properties_cx = {}
                    for key, val in cx_err_info.items():
                        properties_cx[key] = InstructionProperties(error=val)

                    target.add_instruction(
                        CXGate(),
                        properties_cx,
                    )
                elif gate in Constant.SINGLE_QUBIT_GATE_LIST:
                    single_gate_properties = {}
                    gate_inst = gates_map[gate]
                    for q in range(num_qubits):
                        single_gate_properties[(q,)] = InstructionProperties()
                    target.add_instruction(gate_inst, single_gate_properties)
                elif gate in Constant.TWO_QUBIT_GATE_LIST:
                    two_gate_properties = {}
                    gate_inst = gates_map[gate]
                    for e in coupling_map.get_edges():
                        two_gate_properties[e] = InstructionProperties()
                    target.add_instruction(gate_inst, two_gate_properties)
                else:
                    raise TranspilerException(
                        f"unsupported the basis gate[{gate}]."
                    )

            # measure error
            readout_err_info = [
                0.0 for _ in range(trans_cfg_inst.get_max_qubits())
            ]
            readout_err_input: dict = qpu_config["readout_error"]
            for key, value in readout_err_input.items():
                pos = int(key[1:])
                readout_err_info[pos] = float(value)

            mea_props = {}
            for qubit in range(num_qubits):
                mea_props[(qubit,)] = InstructionProperties(
                    error=readout_err_info[qubit]
                )
            target.add_instruction(Measure(), mea_props)

            # reset error
            reset_error = {}
            for q in range(num_qubits):
                reset_error[(q,)] = InstructionProperties()
            target.add_instruction(Reset(), reset_error)

            # qiskit transpiler without driver
            transpiled_circuit = qiskit.transpile(
                circuits=parse_result,
                target=target,
                coupling_map=coupling_map,
                routing_method="sabre",
                layout_method="trivial",
                optimization_level=self.transpiler_options[
                    "optimization_level"
                ],
            )

        return transpiled_circuit
