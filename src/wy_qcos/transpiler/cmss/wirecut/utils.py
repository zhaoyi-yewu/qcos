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

import numpy as np
import copy
import itertools

from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.common.gate_operation import H, S, SDG, X
from wy_qcos.transpiler.cmss.common.qasm_converter import QasmConverter


def generate_subcircuits_for_execute(prepare_data):
    """Generate subcircuits for execution.

    Args:
        prepare_data: The data for preparing subcircuits for execution

    Returns:
        subcircuits_for_execute: The subcircuits for execution.
    """
    subcircuits_for_execute = {}
    for subcircuit_index in range(len(prepare_data.subcircuits)):
        subcircuits_for_one_subcircuit = (
            generate_config_circuits_for_one_subcircuit(
                subcircuit=prepare_data.subcircuits[subcircuit_index],
                input_status=prepare_data.measure_config_value[
                    subcircuit_index
                ],
            )
        )
        subcircuits_for_execute[subcircuit_index] = (
            subcircuits_for_one_subcircuit
        )
    return subcircuits_for_execute


def generate_config_circuits_for_one_subcircuit(
    subcircuit: QuantumCircuit, input_status
):
    """Generate subcircuits for execution for one subcircuit.

    Args:
        subcircuit (QuantumCircuit): Original subcircuit.
        input_status: input status.

    Returns:
        dict: subcircuits for execute
    """
    subcircuits_for_execute = {}
    for instance_config in input_status:
        # Process each instance configuration and retrieve the results
        init, meas = instance_config
        modified_circuit = generate_measure_plans(
            subcircuit=subcircuit,
            init=init,
            meas=meas,
        )
        # Convert the quantum circuit to an OpenQASM 2.0 format string
        modified_circuit.measure_all()
        converter = QasmConverter(modified_circuit)
        qasm_str = converter.to_qasm2()
        subcircuits_for_execute[instance_config] = qasm_str
    return subcircuits_for_execute


def compute_measure_combian(meas):
    """Generate possible measurement basis variants.

    Args:
        meas: Measuring the ground state

    Returns:
        List of possible measured ground states
    """
    # If there is no I, return the original measured ground state directly
    if all(basis != "I" for basis in meas):
        return [meas]

    # Handling cases involving I
    basis_options = []
    for basis in meas:
        if basis != "I":
            basis_options.append([basis])
        else:
            basis_options.append(["I", "Z"])

    # Generate all possible combinations
    return list(itertools.product(*basis_options))


def generate_measure_plans(subcircuit, init, meas):
    """Modify subcircuit based on initialization and measurement basis states.

    Args:
        subcircuit (QuantumCircuit): Original subcircuit
        init: Initial configuration
        meas: Measuring ground state configuration

    Returns:
        modified_dag: Modified subcircuit instance.
    """
    circuit_dag = DAGCircuit.circuit_to_dag(subcircuit)
    modified_dag = copy.deepcopy(circuit_dag)
    # Initialization operation
    for qubit_idx, init_state in enumerate(init):
        qubit = qubit_idx

        if init_state == "0":
            # Default state
            continue
        if init_state == "1":
            # Using X to construct |1> state
            modified_dag.apply_operation_front(op=X([qubit]))
        elif init_state == "+":
            # Using H to construct |+> state
            modified_dag.apply_operation_front(op=H([qubit]))
        elif init_state == "-":
            # Using H and X to construct |-> state
            modified_dag.apply_operation_front(op=H([qubit]))
            modified_dag.apply_operation_front(op=X([qubit]))
        elif init_state == "+i":
            # Using S and H to construct |+i> state
            modified_dag.apply_operation_front(op=S([qubit]))
            modified_dag.apply_operation_front(op=H([qubit]))
        elif init_state == "-i":
            modified_dag.apply_operation_front(op=S([qubit]))
            # Using S, H and X to construct |-i> state
            modified_dag.apply_operation_front(op=H([qubit]))
            modified_dag.apply_operation_front(op=X([qubit]))
        else:
            raise ValueError(f"Unsupported initialization state: {init_state}")
    # Application measurement ground state operation
    for qubit_idx, basis in enumerate(meas):
        qubit = qubit_idx

        if basis in ["I", "common-measure", "Z"]:
            # No additional action required
            continue
        if basis == "X":
            modified_dag.apply_operation_back(op=H([qubit]))
        elif basis == "Y":
            modified_dag.apply_operation_back(op=SDG([qubit]))
            modified_dag.apply_operation_back(op=H([qubit]))
        else:
            raise ValueError(f"Unsupported measurement basis: {basis}")
    return modified_dag.dag_to_circuit()


def attribute_prob(unattribute_prob, meas):
    """Calculate the probability under the specified measurement basis.

    Args:
        unattribute_prob: Unmeasured probability
        meas (dict): Measuring the ground state

    Returns:
        Measured probability
    """
    if meas.count("common-measure") == len(meas) or isinstance(
        unattribute_prob, float
    ):
        return unattribute_prob

    special_measure_count = meas.count("common-measure")
    measured_prob = np.zeros(int(2**special_measure_count), dtype=float)

    for state_idx, prob in enumerate(unattribute_prob):
        sign, effective_idx = attribute_state(full_state=state_idx, meas=meas)
        measured_prob[effective_idx] += sign * prob

    return measured_prob


def attribute_state(full_state, meas):
    """Calculate effective state of specific state under measurement basis.

    Args:
        full_state (int): Complete state index.
        meas: Measuring the ground state.

    Returns:
        (sign, effective_state): Symbol (±1) and valid status index.
    """
    binary_state = bin(full_state)[2:].zfill(len(meas))
    sign = 1
    effective_binary = ""

    # Traverse status bits from right to left
    for bit, basis in zip(binary_state, meas[::-1]):
        # Calculation symbols
        if bit == "1" and basis not in ["I", "common-measure"]:
            sign *= -1

        # Collect special measurement points
        if basis == "common-measure":
            effective_binary += bit

    # Calculate effective status
    if effective_binary:
        effective_state = int(effective_binary, 2)
    else:
        effective_state = 0

    return sign, effective_state


def asign_probability(measured_results, measure_configs):
    """Assign the measurement results to corresponding subcircuit.

    Args:
        measured_results: Subcircuit measurement results
        measure_configs: Subcircuit item configuration

    Returns:
        config_results_map: Probability mapping of subcircuit items
    """
    config_results_map = {}

    for measure_config in measure_configs:
        config = measure_configs[measure_config]
        accumulated_prob = None

        for config_item in config:
            coef, instance_config = config_item
            instance_prob = measured_results[instance_config]
            if accumulated_prob is None:
                accumulated_prob = coef * instance_prob
            else:
                accumulated_prob += coef * instance_prob
        config_results_map[measure_config] = accumulated_prob
    return config_results_map
