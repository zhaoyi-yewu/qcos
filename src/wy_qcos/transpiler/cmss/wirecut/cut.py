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

from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.circuit.register import QuantumRegister
from wy_qcos.transpiler.cmss.common.measure import Measure


class Cut:
    """Cut class."""

    def __init__(self, circuit, MIP_result):
        """Init cut class.

        Args:
            circuit (QuantumCircuit): The input circuit.
            MIP_result (list(list(str))): The result of MIP.
        """
        self.circuit = circuit
        self.MIP_result = MIP_result
        self.dag = DAGCircuit.circuit_to_dag(self.circuit)

    def cut_circuit(self):
        """Cutting circuit.

        Returns:
            subcircuits (list): Subcircuit List.
            qubit_allocation_map (dict): Mapping relationship between original
            circuit bits and subcircuit bits.
            eg. ubit_allocation_map[input circuit qubit]
            = [{subcircuit_idx, subcircuit_qubit}]
        """
        # Initialize encoding and translate MIP encoding
        gate_depth_encodings = self._initialize_gate_depth_encodings()
        # Allocate subcircuits for qubits and construct the mapping
        subcircuit_operations, subcircuit_width, qubit_allocation_map = (
            self._assign_qubits_to_subcircuits(gate_depth_encodings)
        )
        # Update subcircuit qubit information
        qubit_allocation_map = self._update_path_elements(
            qubit_allocation_map, subcircuit_width
        )
        # Generate subcircuit
        subcircuits = self.generate_subcircuits(
            subcircuit_operations=subcircuit_operations,
            path_mapping=qubit_allocation_map,
            subcircuit_widths=subcircuit_width,
            dag=self.dag,
        )
        return subcircuits, qubit_allocation_map

    def _initialize_gate_depth_encodings(self):
        """Initialize the gate depth encodings.

        Returns:
            dict: The gate depth encodings.
        """
        num = self.circuit._num_qubits
        all_gate_counter = {x: 0 for x in range(num)}
        two_qubit_gate_counter = {qubit: 0 for qubit in range(num)}
        gate_encoding_map = {}
        # Generate codes for each operation node
        for op_node in self.dag.topological_op_nodes():
            full_encoding = " ".join([
                f"q[{qarg}]{all_gate_counter[qarg]}" for qarg in op_node.qargs
            ])
            gate_encoding_map[op_node] = full_encoding
            # Update all door counters
            for qarg in op_node.qargs:
                all_gate_counter[qarg] += 1
            # Generate special encoding for two-qubit gates and perform mapping
            if len(op_node.qargs) == 2:
                mip_encoding = " ".join([
                    f"q[{qarg}]{two_qubit_gate_counter[qarg]}"
                    for qarg in op_node.qargs
                ])
                # Update the counter for two-qubit gates
                for qarg in op_node.qargs:
                    two_qubit_gate_counter[qarg] += 1
                # Update subcircuit gate mapping
                for sc_idx, sc_gates in enumerate(self.MIP_result):
                    for gate_idx, gate in enumerate(sc_gates):
                        if gate == mip_encoding:
                            self.MIP_result[sc_idx][gate_idx] = full_encoding
                            break
        return gate_encoding_map

    def _assign_qubits_to_subcircuits(self, gate_encoding_map):
        """Assign subcircuits to qubits and construct qubit allocation map.

        Args:
            gate_encoding_map (dict): Mapping of gate encodings to subcircuits.

        Returns:
            dict: Updated qubit allocation map.
        """
        subcircuit_operations = {
            idx: [] for idx in range(len(self.MIP_result))
        }
        subcircuit_widths = [0] * len(self.MIP_result)
        path_mapping = {}
        for qubit in self.dag.qubits:
            path_mapping[qubit] = []
            qubit_operations = list(
                self.dag.nodes_on_wire(wire=qubit, only_ops=True)
            )
            for _, op in enumerate(qubit_operations):
                if isinstance(op.op, Measure):
                    continue
                gate_encoding = gate_encoding_map[op]
                closest_sc_idx = -1
                closest_distance = float("inf")
                for sc_idx, sc_gates in enumerate(self.MIP_result):
                    current_distance = float("inf")
                    for gate in sc_gates:
                        # Skip the comparison of single-qubit gates
                        if len(gate.split(" ")) > 1:
                            current_distance = min(
                                current_distance,
                                self.compute_gate_distance(
                                    gate_encoding, gate
                                ),
                            )
                    if current_distance < closest_distance:
                        closest_distance = current_distance
                        closest_sc_idx = sc_idx

                path_element = {
                    "subcircuit_idx": closest_sc_idx,
                    "subcircuit_qubit": subcircuit_widths[closest_sc_idx],
                }
                if (
                    len(path_mapping[qubit]) == 0
                    or closest_sc_idx
                    != path_mapping[qubit][-1]["subcircuit_idx"]
                ):
                    path_mapping[qubit].append(path_element)
                    subcircuit_widths[closest_sc_idx] += 1
                # Record the subcircuit to which the operation node belongs to
                subcircuit_operations[closest_sc_idx].append(op)
        return subcircuit_operations, subcircuit_widths, path_mapping

    def _update_path_elements(self, path_mapping, subcircuit_widths):
        """Update the subcircuit qubit information of path element.

        Args:
            path_mapping (dict): The mapping of qubits to subcircuits.
            subcircuit_widths (list): The width of each subcircuit.

        Returns:
            dict: The updated path mapping.
        """
        for qubit in path_mapping:
            for path_element in path_mapping[qubit]:
                sc_idx = path_element["subcircuit_idx"]
                qubit_idx = path_element["subcircuit_qubit"]
                qreg_bit = QuantumRegister(
                    subcircuit_widths[sc_idx], name="q"
                )[qubit_idx]
                path_element["subcircuit_qubit"] = qreg_bit
        return path_mapping

    def compute_gate_distance(self, gate1, gate2):
        """Calculate the distance between two quantum gates.

        Args:
            gate1 (str): The string representation of the first gate.
            gate2 (str): The string representation of the second gate.

        Returns:
            float: Minimum distance between two doors
        """
        # Ensure gate1 is a gate with fewer parameters
        if len(gate1.split(" ")) > len(gate2.split(" ")):
            gate1, gate2 = gate2, gate1
        # Analyzing the quantum bit information of two gates.
        gate1_qubits = self._parse_gate_qubits(gate1)
        gate2_qubits = self._parse_gate_qubits(gate2)
        # Find the minimum distance on shared qubits
        min_distance = float("inf")
        for qubit_name, gate_idx1 in gate1_qubits:
            for qubit_name2, gate_idx2 in gate2_qubits:
                if qubit_name == qubit_name2:
                    min_distance = min(
                        min_distance, abs(gate_idx2 - gate_idx1)
                    )
        return min_distance

    def _parse_gate_qubits(self, gate_str):
        """Parsing the quantum bit information of the gate.

        Args:
            gate_str (str): String representation of the door

        Returns:
            List: Contains (quantum bit name, gate index)
        """
        parsed_qubits = []
        for q_arg in gate_str.split(" "):
            parts = q_arg.split("]")
            qubit_name = parts[0] + "]"
            gate_idx = int(parts[-1])
            parsed_qubits.append((qubit_name, gate_idx))
        return parsed_qubits

    def generate_subcircuits(
        self, subcircuit_operations, path_mapping, subcircuit_widths, dag
    ):
        """Generate subcircuits based on operation allocation and path mapping.

        Args:
            subcircuit_operations: Each subcircuit contains operational nodes
            path_mapping: Mapping of input qubits to subcircuit qubits
            subcircuit_widths: The size of each subcircuit
            dag: The DAG representation of the original circuit

        Returns:
            list: Generated subcircuit list
        """
        qubit_position_tracker = {qubit: 0 for qubit in path_mapping}
        circuit_list = [
            QuantumCircuit(size, size) for size in subcircuit_widths
        ]
        # Process operation nodes in topological order
        for operation_node in dag.topological_op_nodes():
            if isinstance(operation_node.op, Measure):
                continue
            containing_subcircuits = [
                sc_idx
                for sc_idx in subcircuit_operations.keys()
                if operation_node in subcircuit_operations[sc_idx]
            ]
            target_subcircuit = containing_subcircuits[0]
            target_qargs = []
            for qarg in operation_node.qargs:
                current_pointer = qubit_position_tracker[qarg]
                current_path = path_mapping[qarg][current_pointer]
                if current_path["subcircuit_idx"] != target_subcircuit:
                    qubit_position_tracker[qarg] += 1
                    current_pointer = qubit_position_tracker[qarg]
                    current_path = path_mapping[qarg][current_pointer]
                # Add target qubit
                target_qargs.append(current_path["subcircuit_qubit"])
            # Add operation to subcircuit.
            operation_node.qargs = tuple(target_qargs)
            operation_node.op.targets = tuple(target_qargs)
            circuit_list[target_subcircuit].append(operation_node.op)
        return circuit_list
