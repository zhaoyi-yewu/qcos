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

import numpy as np
import itertools
import copy

from functools import lru_cache


class Prepare_data:
    """Class of quantum circuit cutting data preparation."""

    def __init__(
        self,
        circuit,
        subcircuits,
        qubit_allocation_map,
    ):
        """Initialize circuit data preparation.

        Args:
            circuit: Original quantum circuit
            subcircuits: List of subcircuits after cutting
            qubit_allocation_map: Qubit mapping
        """
        self.circuit = circuit
        self.subcircuits = subcircuits
        self.qubit_allocation_map = qubit_allocation_map
        self.connection_pairs = self.get_connections()
        self.subcircuit_metadata = self.compute_subcircuit_metadata()
        # Generate relevant data for the subcircuit topology structure
        self.topo_subcircuits = build_topo_subcircuits(
            subcircuit_metadata=self.subcircuit_metadata,
            subcircuits=self.subcircuits,
            qubit_allocation_map=self.qubit_allocation_map,
        )
        self.measure_config, self.measure_config_value = generate_run_config(
            topo_subcircuits=self.topo_subcircuits
        )
        self.origin_qubit_order = self.get_origin_qubit_order()

    def get_connections(self):
        """Obtain connections between subcircuits."""
        connection_pairs = []
        for input_qubit in self.qubit_allocation_map:
            path = self.qubit_allocation_map[input_qubit]
            if len(path) > 1:
                for path_idx, item in enumerate(path[:-1]):
                    output_qubit = item
                    input_next_qubit = path[path_idx + 1]
                    connection_pairs.append((output_qubit, input_next_qubit))
        return connection_pairs

    def compute_subcircuit_metadata(self):
        """Calculate the metadata for each subcircuit."""
        connection_pairs = []
        for input_qubit in self.qubit_allocation_map:
            path = self.qubit_allocation_map[input_qubit]
            if len(path) > 1:
                for path_idx, item in enumerate(path[:-1]):
                    output_qubit = item
                    input_next_qubit = path[path_idx + 1]
                    connection_pairs.append((output_qubit, input_next_qubit))
        self.connection_pairs = connection_pairs
        metadata = {}
        for subcircuit_idx, subcircuit in enumerate(self.subcircuits):
            metadata[subcircuit_idx] = {
                "significant": subcircuit.num_qubits,
                "input": 0,
                "output": 0,
            }
        for pair in self.connection_pairs:
            output_qubit, input_qubit = pair
            metadata[output_qubit["subcircuit_idx"]]["significant"] -= 1
            metadata[output_qubit["subcircuit_idx"]]["output"] += 1
            metadata[input_qubit["subcircuit_idx"]]["input"] += 1
        return metadata

    def get_origin_qubit_order(self):
        """Obtain the sequential mapping of reconstructed qubits.

        Returns:
            The mapping of each subcircuit output qubit to circuit qubit
        """
        origin_qubit_order = {
            subcircuit_idx: []
            for subcircuit_idx in range(len(self.subcircuits))
        }
        # Step 1：Collect the output qubits of each subcircuit and
        # their indices in the original circuit.
        for input_qubit in self.qubit_allocation_map:
            path = self.qubit_allocation_map[input_qubit]
            output_qubit = path[-1]
            # Extract the subcircuit index and the qubits in the subcircuit
            subcircuit_idx = output_qubit["subcircuit_idx"]
            subcircuit_qubit = output_qubit["subcircuit_qubit"]
            # Get the index of the input qubit in the original circuit
            original_qubit_idx = input_qubit
            origin_qubit_order[subcircuit_idx].append((
                subcircuit_qubit,
                original_qubit_idx,
            ))
        # Step 2: Sort and transform the quantum bit list for each subcircuit
        for subcircuit_idx in origin_qubit_order:
            # Sort by the index of qubits in the subcircuit, in reverse order
            origin_qubit_order[subcircuit_idx] = sorted(
                origin_qubit_order[subcircuit_idx],
                key=lambda x: x[0],
                reverse=True,
            )
            # Only retain the quantum bit indices in the original circuit
            origin_qubit_order[subcircuit_idx] = [
                x[1] for x in origin_qubit_order[subcircuit_idx]
            ]
        return origin_qubit_order


class Topo_Subcircuits:
    """Class of topological relationships between subgraphs."""

    def __init__(self):
        """Initialize the topological relationships between subgraphs."""
        self.subcircuits = {}
        self.connections = []
        self._connection_cache = {}

    def _build_connection_cache(self):
        """Build a connection cache to optimize connection lookup."""
        self._connection_cache = {
            "outgoing": {},  # Connections from the node
            "incoming": {},  # Connections to the node
        }
        # Initialize the connection list of all sub-circuits
        for subcircuit_idx in self.subcircuits:
            self._connection_cache["outgoing"][subcircuit_idx] = []
            self._connection_cache["incoming"][subcircuit_idx] = []
        # Category Storage Connection
        for conn in self.connections:
            source, target, _ = conn
            if source in self._connection_cache["outgoing"]:
                self._connection_cache["outgoing"][source].append(conn)
            if target in self._connection_cache["incoming"]:
                self._connection_cache["incoming"][target].append(conn)

    def get_init_meas(self, subcircuit_idx):
        """Obtain initialization configuration of subcircuit."""
        node_attributes = self.subcircuits[subcircuit_idx]
        subcircuit = node_attributes["subcircuit"]
        # Initialize to zero state
        init_config = ["0"] * subcircuit.num_qubits
        # Processing input edges
        input_edges = self.get_connection(
            from_node=None, to_node=subcircuit_idx
        )
        for edge in input_edges:
            _, target, edge_attributes = edge
            qubit_idx = edge_attributes["input_qubit"]
            init_config[qubit_idx] = edge_attributes["basis"]

        # All qubits are initialized to special measurements.
        meas_config = ["common-measure"] * subcircuit.num_qubits
        output_edges = self.get_connection(
            from_node=subcircuit_idx, to_node=None
        )
        for edge in output_edges:
            source, _, edge_attributes = edge
            qubit_idx = edge_attributes["output_qubit"]
            meas_config[qubit_idx] = edge_attributes["basis"]
        return (tuple(init_config), tuple(meas_config))

    def get_connection(self, from_node=None, to_node=None):
        """Get the connections between eligible subgraphs.

        Args:
            from_node: Only edges originating from this node are returned.
            to_node: Only return the edges that reach this node

        Returns:
            list: List of connections between eligible subgraphs.
        """
        if hasattr(self, "_connection_cache") and self._connection_cache:
            if from_node is not None and to_node is None:
                return self._connection_cache["outgoing"].get(from_node, [])
            elif from_node is None and to_node is not None:
                return self._connection_cache["incoming"].get(to_node, [])
        filtered_connections = []
        for conn in self.connections:
            source, target, _ = conn
            from_match = from_node is None or source == from_node
            to_match = to_node is None or target == to_node
            if from_match and to_match:
                filtered_connections.append(conn)
        return filtered_connections

    def assign_bases_to_connections(self, conn_bases, connections):
        """Assign base attributes to connections between subgraphs."""
        for conn_basis, conn in zip(conn_bases, connections):
            _, _, attributes = conn
            attributes["basis"] = conn_basis


def tensor_product(*distributions):
    """Tensor product operation."""
    result = None
    for distribution in distributions:
        if result is None:
            result = distribution
        else:
            result = np.kron(result, distribution)
    return result


@lru_cache(maxsize=1024)
def translate_to_instance_config(init_label, meas_label):
    """Convert initialization and measurement labels to instance configuration.

    Args:
        init_label: Initialize tags
        meas_label: Measurement label

    Returns:
        Possible instance configuration list.
    """
    init_combinations = []
    init_mapping = {
        "0": ("0",),
        "I": ("+0", "+1"),
        "X": ("+2+", "-0", "-1"),
        "Y": ("+2+i", "-0", "-1"),
        "Z": ("+0", "-1"),
    }
    for x in init_label:
        if x in init_mapping:
            init_combinations.append(init_mapping[x])
        else:
            raise ValueError(f"Illegal initialization symbol: {x}.")
    # Generate all possible initialization combinations
    init_combinations = list(itertools.product(*init_combinations))
    instance_configs = []
    for init in init_combinations:
        instance_configs.append((init, meas_label))
    return tuple(instance_configs)


@lru_cache(maxsize=1024)
def to_basic_init(init):
    coefficient = 1
    init_list = list(init)
    # Each mapping value is a tuple of (new state, coefficient multiplier)
    init_mapping = {
        "0": ("0", 1),
        "+0": ("0", 1),
        "+1": ("1", 1),
        "+2+": ("+", 2),
        "-0": ("0", -1),
        "-1": ("1", -1),
        "+2+i": ("+i", 2),
    }
    for idx, x in enumerate(init_list):
        if x == "0":
            continue
        if x in init_mapping:
            init_list[idx] = init_mapping[x][0]
            coefficient *= init_mapping[x][1]
        else:
            raise ValueError(f"Illegal initialization symbol: {x}")

    return coefficient, tuple(init_list)


def build_topo_subcircuits(
    subcircuit_metadata, subcircuits, qubit_allocation_map
):
    """Constructing topological relationships between subcircuits.

    Args:
        subcircuit_metadata: Subcircuit metadata
        subcircuits: Subcircuit List
        qubit_allocation_map: Qubit mapping

    Returns:
        Subcircuit topology relationship object
    """
    topo_subcircuits = Topo_Subcircuits()
    # Add node
    for subcircuit_idx in subcircuit_metadata:
        node_attributes = copy.deepcopy(subcircuit_metadata[subcircuit_idx])
        node_attributes["subcircuit"] = subcircuits[subcircuit_idx]
        topo_subcircuits.subcircuits[subcircuit_idx] = node_attributes
    # Add edges
    for qubit_id in qubit_allocation_map:
        path = qubit_allocation_map[qubit_id]
        for path_idx in range(len(path) - 1):
            source_info = path[path_idx]
            target_info = path[path_idx + 1]
            # Add an edge from the source subcircuit to the target subcircuit
            topo_subcircuits.connections.append((
                source_info["subcircuit_idx"],
                target_info["subcircuit_idx"],
                {
                    "output_qubit": source_info["subcircuit_qubit"],
                    "input_qubit": target_info["subcircuit_qubit"],
                },
            ))
    # Building a connection cache
    topo_subcircuits._build_connection_cache()
    return topo_subcircuits


def generate_run_config(topo_subcircuits):
    """Generate subcircuit entries and instances.

    Args:
        topo_subcircuits: Subcircuit topology relationship

    Returns:
        config_measures: Subcircuit entries
        measure_config_value: Subcircuit instances
    """
    config_measures = {}
    measure_config_value = {}
    qubit_index_maps = {}
    for subcircuit_idx in topo_subcircuits.subcircuits:
        subcircuit = topo_subcircuits.subcircuits[subcircuit_idx]["subcircuit"]
        qubit_index_maps[subcircuit_idx] = {
            qubit: idx
            for idx, qubit in enumerate(range(subcircuit._num_qubits))
        }

    related_edges_cache = {}
    for subcircuit_idx in topo_subcircuits.subcircuits:
        related_edges_cache[subcircuit_idx] = get_related_edges(
            topo_subcircuits, subcircuit_idx
        )

    for subcircuit_idx in topo_subcircuits.subcircuits:
        subcircuit = topo_subcircuits.subcircuits[subcircuit_idx]["subcircuit"]
        config_measures[subcircuit_idx] = {}
        measure_config_value[subcircuit_idx] = []
        process_subcircuit_optimized(
            subcircuit_idx,
            subcircuit,
            config_measures,
            measure_config_value,
            qubit_index_maps[subcircuit_idx],
            related_edges_cache[subcircuit_idx],
        )
    return config_measures, measure_config_value


def process_subcircuit_optimized(
    subcircuit_idx,
    subcircuit,
    config_measures,
    measure_config_value,
    qubit_index_map,
    related_edges,
):
    """Process subcircuit optimized.

    Args:
        subcircuit_idx: Subcircuit subscript
        subcircuit: Subcircuit
        config_measures: Measurement configuration
        measure_config_value: Converted measurement configuration
        qubit_index_map: Bit mapping relationship
        related_edges: Connection edges (cut points) between subcircuits
    """
    existing_instances = set()
    # Traverse all possible base combinations
    for edge_bases in itertools.product(
        ["I", "X", "Y", "Z"], repeat=len(related_edges)
    ):
        entry_init, entry_meas = create_entry_config_optimized(
            subcircuit,
            subcircuit_idx,
            edge_bases,
            related_edges,
            qubit_index_map,
        )
        process_subcircuit_entry_optimized(
            subcircuit_idx,
            entry_init,
            entry_meas,
            config_measures,
            measure_config_value,
            existing_instances,
        )


def get_related_edges(topo_subcircuits, subcircuit_idx):
    """Get all edges related to the subcircuit.

    Args:
        topo_subcircuits (Topo_Subcircuits): Topological subcircuits.
        subcircuit_idx: subcircuit index
    """
    outgoing_edges = topo_subcircuits.get_connection(
        from_node=subcircuit_idx, to_node=None
    )
    incoming_edges = topo_subcircuits.get_connection(
        from_node=None, to_node=subcircuit_idx
    )
    return outgoing_edges + incoming_edges


def create_entry_config_optimized(
    subcircuit, subcircuit_idx, edge_bases, related_edges, qubit_index_map
):
    # Initialize the configuration of sub-circuit entries
    entry_init = ["0"] * subcircuit.num_qubits
    entry_meas = ["common-measure"] * subcircuit.num_qubits
    # Assign a basis to each edge
    for edge_basis, edge in zip(edge_bases, related_edges):
        source, target, edge_attrs = edge

        if subcircuit_idx == source:
            output_qubit = edge_attrs["output_qubit"]
            qubit_idx = qubit_index_map[output_qubit]
            entry_meas[qubit_idx] = edge_basis
        elif subcircuit_idx == target:
            input_qubit = edge_attrs["input_qubit"]
            qubit_idx = qubit_index_map[input_qubit]
            entry_init[qubit_idx] = edge_basis
        else:
            raise IndexError(
                "When generating entries, the subcircuit index "
                "should be the source or target of the edge."
            )
    return entry_init, entry_meas


def process_subcircuit_entry_optimized(
    subcircuit_idx,
    entry_init,
    entry_meas,
    config_measures,
    measure_config_value,
    existing_instances,
):
    """Process subcircuit entry optimized.

    Args:
        subcircuit_idx: Subcircuit index
        entry_init: Initialization label of subcircuit
        entry_meas: Measurement label of subcircuit
        config_measures: Dictionary for storing subcircuit entry configurations
        measure_config_value: Dictionary for storing subcircuit configurations
        existing_instances: Set of existing instances
    """
    instance_configs = translate_to_instance_config(
        init_label=tuple(entry_init), meas_label=tuple(entry_meas)
    )
    entry_term = []
    for instance_config in instance_configs:
        init, meas = instance_config
        coef, physical_init = to_basic_init(init)
        instance_key = (physical_init, meas)
        if instance_key not in existing_instances:
            measure_config_value[subcircuit_idx].append(instance_key)
            existing_instances.add(instance_key)
        entry_term.append((coef, instance_key))
    entry_key = (tuple(entry_init), tuple(entry_meas))
    config_measures[subcircuit_idx][entry_key] = entry_term


def process_subcircuit(
    topo_subcircuits,
    subcircuit_idx,
    subcircuit,
    config_measures,
    measure_config_value,
):
    """Configuration generation for subcircuits."""
    related_edges = get_related_edges(topo_subcircuits, subcircuit_idx)
    # Traverse all possible base combinations
    for edge_bases in itertools.product(
        ["I", "X", "Y", "Z"], repeat=len(related_edges)
    ):
        entry_init, entry_meas = create_entry_config(
            subcircuit, subcircuit_idx, edge_bases, related_edges
        )
        process_subcircuit_entry(
            subcircuit_idx,
            entry_init,
            entry_meas,
            config_measures,
            measure_config_value,
        )


def create_entry_config(subcircuit, subcircuit_idx, edge_bases, related_edges):
    """Create entry configuration for subcircuits.

    Args:
        subcircuit (QuantumCircuit): The subcircuit.
        subcircuit_idx (int): The index of the subcircuit.
        edge_bases (tuple): The bases for each edge.
        related_edges (list): The related edges of the subcircuit.

    Returns:
        tuple: initialization and measurement configuration for the subcircuit.
    """
    entry_init = ["0"] * subcircuit.num_qubits
    entry_meas = ["common-measure"] * subcircuit.num_qubits

    for edge_basis, edge in zip(edge_bases, related_edges):
        source, target, edge_attrs = edge
        if subcircuit_idx == source:
            qubit_idx = edge_attrs["output_qubit"]
            entry_meas[qubit_idx] = edge_basis
        elif subcircuit_idx == target:
            qubit_idx = edge_attrs["input_qubit"]
            entry_init[qubit_idx] = edge_basis
        else:
            raise IndexError(
                "When generating entries, the subcircuit index should be "
                "the source or target of the edge."
            )
    return entry_init, entry_meas


def process_subcircuit_entry(
    subcircuit_idx,
    entry_init,
    entry_meas,
    config_measures,
    measure_config_value,
):
    """Convert the initialization and measurement into instance configurations.

    Args:
        subcircuit_idx: Subcircuit index
        entry_init: Initialization label of the subcircuit
        entry_meas: Measurement label of the subcircuit
        config_measures: Dictionary for storing subcircuit entry configurations
        measure_config_value: Dictionary for storing subcircuit configurations
    """
    # Get the instance configuration corresponding to this entry
    instance_configs = translate_to_instance_config(
        init_label=tuple(entry_init), meas_label=tuple(entry_meas)
    )

    # Handle each instance configuration
    entry_term = []
    for instance_config in instance_configs:
        init, meas = instance_config

        # Convert to physical initialization
        coef, physical_init = to_basic_init(init)

        # Add the instance to the instance list
        if (physical_init, meas) not in measure_config_value[subcircuit_idx]:
            measure_config_value[subcircuit_idx].append((physical_init, meas))

        # Add to entry item
        entry_term.append((coef, (physical_init, meas)))

    # Save this entry
    entry_key = (tuple(entry_init), tuple(entry_meas))
    config_measures[subcircuit_idx][entry_key] = entry_term
