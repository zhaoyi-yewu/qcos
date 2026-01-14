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
import itertools

from wy_qcos.transpiler.cmss.wirecut.prepare_data import tensor_product
from wy_qcos.transpiler.cmss.wirecut.utils import (
    compute_measure_combian,
    attribute_prob,
)


class Reconstructor:
    def __init__(
        self,
        prepare_data,
        results_for_execute,
    ) -> None:
        self.prepare_data = prepare_data
        self.topo_subcircuits = prepare_data.topo_subcircuits
        self.evaluate_results = results_for_execute
        self.init_data()
        self.reconstructed_prob = self.reconstruct()

    def init_data(self):
        """Initializing the data required for the reconstructor."""
        # Calculate the measurement configuration length for each sub-circuit
        self.measure_config_length = {
            subcircuit_idx: self.get_measure_config_length(subcircuit_idx)
            for subcircuit_idx in self.evaluate_results
        }

        # Calculate the total number of qubits
        self.num_qubits = sum(
            subcircuit_data["significant"]
            for subcircuit_data in self.topo_subcircuits.subcircuits.values()
        )
        # Sort sub-circuits based on the measured configuration length
        self.sorted_subcircuit_config = sorted(
            self.measure_config_length.keys(),
            key=lambda subcircuit_idx: self.measure_config_length[
                subcircuit_idx
            ],
        )

    def get_measure_config_length(self, subcircuit_idx):
        """Get the measurement configuration length of the given subcircuit.

        Args:
            subcircuit_idx: Subcircuit index

        Return:
            int: Measurement configuration length
        """
        # Get the key of the first entry and return the length of its result
        first_entry = next(iter(self.evaluate_results[subcircuit_idx]))
        return len(self.evaluate_results[subcircuit_idx][first_entry])

    def reconstruct(self):
        """Reconstructing the probability distribution of quantum circuits.

        Main steps:
            1. Traverse all possible base combinations(I、X、Y、Z)
            2. Calculate the tensor product of subcircuits for each combination
            3. Accumulate the results of all combinations
            4. Normalized final probability distribution
            5. Reorder the probability distribution

        Returns:
            Normalized complete quantum circuit probability distribution.
        """
        # Obtain connections and substrate possibilities between sub-circuits
        connections = self.topo_subcircuits.get_connection(
            from_node=None, to_node=None
        )
        total_bases = ["I", "X", "Y", "Z"]

        sorted_subcircuit_config = self.sorted_subcircuit_config
        evaluate_results = self.evaluate_results
        topo_subcircuits = self.topo_subcircuits

        # Accumulator initialization
        reconstructed_prob = None
        # Traverse all possible base combinations
        for conn_bases in itertools.product(
            total_bases, repeat=len(connections)
        ):
            # Calculate probability distribution of current base combination
            current_product = self.compute_tensor_product_for_bases(
                conn_bases,
                connections,
                sorted_subcircuit_config,
                evaluate_results,
                topo_subcircuits,
            )

            # Accumulate to the total result
            reconstructed_prob = (
                current_product
                if reconstructed_prob is None
                else reconstructed_prob + current_product
            )

        # Normalization result
        normalized_prob = self.normalize_probability(reconstructed_prob)
        return normalized_prob

    def compute_tensor_product_for_bases(
        self,
        conn_bases,
        connections,
        sorted_subcircuit_config,
        evaluate_results,
        topo_subcircuits,
    ):
        """Compute tensor product of subcircuits.

        Args:
            conn_bases: Current base combination
            connections: Connections between subcircuits
            sorted_subcircuit_config: Subcircuit processing sequence
            evaluate_results: Subcircuit evaluation results
            topo_subcircuits: Subcircuit topology structure

        Returns:
            Tensor product result of the current basis combination.
        """
        topo_subcircuits.assign_bases_to_connections(
            conn_bases=conn_bases, connections=connections
        )

        # Collect the probability distribution of each sub-circuit
        # under the current basis
        each_measure_result = []
        for subcircuit_idx in sorted_subcircuit_config:
            init_meas_config = topo_subcircuits.get_init_meas(
                subcircuit_idx=subcircuit_idx
            )
            measure_result = evaluate_results[subcircuit_idx][init_meas_config]
            each_measure_result.append(measure_result)
        return tensor_product(*each_measure_result)

    def normalize_probability(self, prob_distribution):
        """Normalized probability distribution.

        Args:
            prob_distribution: Probability distribution array

        Returns:
            Normalized probability distribution.
        """
        if prob_distribution is None:
            return None

        total_prob = np.sum(prob_distribution)
        if total_prob > 0:
            return prob_distribution / total_prob

        return prob_distribution


def parse_results_from_hardware_service(results_for_execute):
    """Parse measurement results from hardware simulator outputs.

    Args:
        results_for_execute: Results for execute.

    Returns:
        dict: Measurement results for each subcircuit.
    """
    all_results_dict = {}
    for (
        subcircuit_index,
        result_probabilities_with_config,
    ) in results_for_execute.items():
        results_dict = {}
        for (
            config,
            result_probabilities,
        ) in result_probabilities_with_config.items():
            init, meas = config
            # Generate all possible measurement basis variants
            possible_measurements = compute_measure_combian(meas=meas)
            # Handle every possible variant of the measurement basis
            for measurement_basis in possible_measurements:
                processed_prob = attribute_prob(
                    unattribute_prob=result_probabilities,
                    meas=measurement_basis,
                )
                results_dict[(init, measurement_basis)] = processed_prob
        all_results_dict[subcircuit_index] = results_dict
    return all_results_dict
