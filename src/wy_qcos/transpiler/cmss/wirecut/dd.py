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

import itertools
import copy
import math
import numpy as np

from wy_qcos.transpiler.cmss.wirecut.reconstructor import (
    Reconstructor,
    parse_results_from_hardware_service,
)
from wy_qcos.transpiler.cmss.wirecut.utils import asign_probability


class DD:
    """Dynamic definition class."""

    def __init__(
        self,
        topo_subcircuits,
        results_from_hardware,
        prepare_data,
        max_memory,
        max_depths,
    ) -> None:
        """Initialize DD class.

        Args:
            topo_subcircuits: TopoSubcircuits class.
            results_from_hardware: The results from hardware.
            prepare_data: PrepareData class.
            max_memory (int): Memory upper limit.
            max_depths (int): Maximum recursion depth.
        """
        self.topo_subcircuits = topo_subcircuits
        self.prepare_data = prepare_data
        self.max_depths = max_depths
        self.dd_bins = {}
        self.init_data()
        # Calculate the number of available bits (logarithm of memory limit).
        self.mem_qubits = int(math.log2(max_memory))
        # Analyze measurement results and assign them to each sub-circuit item.
        self.subcircuit_entry_probs = self._assign_probabilities(
            results_from_hardware
        )

    def _assign_probabilities(self, all_results_dict):
        """Analyze measurement results and assign them to sub-circuit items."""
        parsed = parse_results_from_hardware_service(
            results_for_execute=all_results_dict
        )
        result = {}
        for idx, measured in parsed.items():
            result[idx] = asign_probability(
                measured_results=measured,
                measure_configs=self.prepare_data.measure_config[idx],
            )
        return result

    def init_data(self):
        # Count the total number of bits and the capacity of each subcircuit
        self.total_qubits = sum(
            self.topo_subcircuits.subcircuits[idx]["significant"]
            for idx in self.topo_subcircuits.subcircuits
        )
        self.capacities = {
            idx: self.topo_subcircuits.subcircuits[idx]["significant"]
            for idx in self.topo_subcircuits.subcircuits
        }

    def dd(self):
        """The main process of DD algorithm."""
        expand_queue = []
        layer = 0

        def schedule_state(prev_state=None, bin_id=None, order=None):
            """Unified schedule generation."""
            if prev_state is None:
                # Initialization: Assign active bits, others are merged.
                active_qubits = self._distribute_load(self.capacities)
                subcircuit_state = {
                    idx: ["active"] * active_qubits[idx]
                    + ["merged"] * (self.capacities[idx] - active_qubits[idx])
                    for idx in self.capacities
                }
                return {"subcircuit_state": subcircuit_state, "prev": None}
            else:
                # Recursive expansion: Fill the active bits of the upper-level
                # bin with bin_id, and reassign the merged active bits.
                n_active = sum(
                    prev_state[idx].count("active") for idx in prev_state
                )
                bin_str = bin(bin_id)[2:].zfill(n_active)
                next_state = copy.deepcopy(prev_state)
                ptr = 0
                for idx in order:
                    for q, state in enumerate(next_state[idx]):
                        if state == "active":
                            next_state[idx][q] = int(bin_str[ptr])
                            ptr += 1
                # Count the number of merged and reassign active
                capacities = {
                    idx: next_state[idx].count("merged") for idx in next_state
                }
                active_qubits = self._distribute_load(capacities)
                for idx in next_state:
                    n = active_qubits[idx]
                    for q, state in enumerate(next_state[idx]):
                        if state == "merged" and n > 0:
                            next_state[idx][q] = "active"
                            n -= 1
                return {
                    "subcircuit_state": next_state,
                    "prev": (layer - 1, bin_id),
                }

        while layer < self.max_depths:
            if layer == 0:
                schedule = schedule_state()
            elif not expand_queue:
                break
            else:
                # Expand the bin with the highest probability of being drawn.
                expand_info = expand_queue.pop(0)
                prev_state = self.dd_bins[expand_info["depth"]][
                    "subcircuit_state"
                ]
                order = self.dd_bins[expand_info["depth"]]["order"]
                schedule = schedule_state(
                    prev_state, expand_info["bin_id"], order
                )
            # Combine the probability distributions of each subcircuit.
            merged_probs = self._merge_states(schedule)
            reconstructor = Reconstructor(self.prepare_data, merged_probs)
            rec_prob = reconstructor.reconstructed_prob
            order = reconstructor.sorted_subcircuit_config
            # Save this layer's information.
            self.dd_bins[layer] = {
                "subcircuit_state": schedule["subcircuit_state"],
                "prev": schedule["prev"],
                "order": order,
                "bins": rec_prob,
                "expanded_bins": [],
            }
            has_merged = any(
                "merged" in schedule["subcircuit_state"][idx]
                for idx in schedule["subcircuit_state"]
            )
            if layer < self.max_depths - 1 and has_merged:
                threshold = 1 / 2**self.total_qubits / 10
                top_indices = np.argsort(rec_prob)[-self.max_depths :]
                candidates = [
                    {
                        "depth": layer,
                        "bin_id": bin_id,
                        "prob": rec_prob[bin_id],
                    }
                    for bin_id in top_indices
                    if rec_prob[bin_id] > threshold
                ]
                expand_queue = (
                    sorted(candidates, key=lambda x: x["prob"], reverse=True)
                    + expand_queue
                )
                expand_queue = expand_queue[: self.max_depths]
            layer += 1

    def _distribute_load(self, capacities):
        """Allocate the number of active bits.

        Args:
            capacities: The number of bits in each subcircuit.

        Returns:
            active_qubits: The number of active bits in each subcircuit.
        """
        total = min(sum(capacities.values()), self.mem_qubits)
        total_cap = sum(capacities.values())
        # Allocate active bits proportionally
        loads = {
            idx: int(capacities[idx] / total_cap * total) for idx in capacities
        }
        remain = total - sum(loads.values())
        for idx in loads:
            while remain > 0 and loads[idx] < capacities[idx]:
                loads[idx] += 1
                remain -= 1
        return loads

    def _merge_states(self, schedule):
        """Merge the probability distributions of each subcircuit into bins.

        Args:
            schedule: The schedule of the DD algorithm.

        Returns:
            dict: The merged probability distributions of each subcircuit.
        """

        def _merge_single_subcircuit(
            idx, entry, subcircuit_entry_probs, subcircuit_state
        ):
            unmerged = subcircuit_entry_probs[idx][entry]
            return merge_prob_vector(unmerged, subcircuit_state[idx])

        merged = {}
        for idx in self.topo_subcircuits.subcircuits:
            merged[idx] = {}
            subcircuit_state = schedule["subcircuit_state"]
            for entry in self.subcircuit_entry_probs[idx]:
                merged[idx][entry] = _merge_single_subcircuit(
                    idx, entry, self.subcircuit_entry_probs, subcircuit_state
                )
        return merged


def reconstruct_prob_from_bins(
    subcircuit_out_qubits,
    dd_bins,
    max_memory,
    is_complete_reconstruction,
):
    """Read all bins and reconstruct the final probability distribution.

    Args:
        subcircuit_out_qubits: The correspondence between the subcircuit qubits
                                and the original circuit qubits.
        dd_bins: The probability box set returned by the dd function.
        max_memory: Memory limit during the refactoring phase.
        is_complete_reconstruction: Whether to perform a complete refactoring.

    Returns:
        probability_distribution: The final probability distribution.
    """

    def _fill_binary_full(
        bin_id, n_active, order, subcircuit_state, subcircuit_out_qubits
    ):
        """Generate a complete binary bit string based on bin_id and state."""
        bin_str = bin(bin_id)[2:].zfill(n_active)
        binary_full = ["" for _ in range(total_qubits)]
        ptr = 0
        for idx in order:
            state = subcircuit_state[idx]
            for q, s in enumerate(state):
                qubit_idx = subcircuit_out_qubits[idx][q]
                if s == "active":
                    binary_full[qubit_idx] = bin_str[ptr]
                    ptr += 1
                else:
                    binary_full[qubit_idx] = str(s)
        return binary_full

    def _expand_merged_states(binary_full, merged_indices, bin_prob):
        """Expand all merged bits and distribute the probability evenly."""
        n_merged = len(merged_indices)
        avg_prob = bin_prob / 2**n_merged
        for merged_state in itertools.product(["0", "1"], repeat=n_merged):
            for i, val in enumerate(merged_state):
                binary_full[merged_indices[i]] = val
            state_str = "".join(binary_full)[::-1]
            idx = int(state_str, 2)
            reconstructed_prob[idx] = avg_prob

    total_qubits = sum(
        len(subcircuit_out_qubits[idx]) for idx in subcircuit_out_qubits
    )
    reconstructed_prob = np.zeros(max_memory, dtype=np.float32)
    active_prob_list = []
    sparse_prob_list = []
    for _, layer_info in dd_bins.items():
        subcircuit_state = layer_info["subcircuit_state"]
        order = layer_info["order"]
        bins = layer_info["bins"]
        expanded_bins = layer_info["expanded_bins"]
        n_active = sum(
            subcircuit_state[idx].count("active") for idx in subcircuit_state
        )
        for bin_id, bin_prob in enumerate(bins):
            if bin_prob <= 0 or bin_id in expanded_bins:
                continue
            binary_full = _fill_binary_full(
                bin_id,
                n_active,
                order,
                subcircuit_state,
                subcircuit_out_qubits,
            )
            merged_indices = [
                i for i, s in enumerate(binary_full) if s == "merged"
            ]
            active_indices = [
                i for i, s in enumerate(binary_full) if s != "merged"
            ]
            n_merged = len(merged_indices)
            n = len(active_indices)
            if not is_complete_reconstruction:
                if n == int(math.log2(max_memory)):
                    active_prob_list.append((bin_id, bin_prob))

                if n_merged == 0:
                    full_state = "".join(binary_full)[::-1]
                    sparse_prob_list.append((full_state, bin_prob))
            else:
                _expand_merged_states(binary_full, merged_indices, bin_prob)

    if not is_complete_reconstruction:
        sum_active_prob = sum(prob for _, prob in active_prob_list)
        for bin_id, prob in active_prob_list:
            reconstructed_prob[bin_id] = prob / sum_active_prob
        sum_sparse_prob = sum(prob for _, prob in sparse_prob_list)
        for i, (full_state, prob) in enumerate(sparse_prob_list):
            sparse_prob_list[i] = (full_state, prob / sum_sparse_prob)
        return reconstructed_prob, sparse_prob_list
    else:
        return reconstructed_prob, None


def merge_prob_vector(unmerged_prob_vector, qubit_states):
    """According to the active/merged bit merge probability distribution."""
    if not qubit_states:
        return unmerged_prob_vector
    num_active = qubit_states.count("active")
    num_merged = qubit_states.count("merged")
    merged_vector = np.zeros(2**num_active, dtype="float32")
    # Enumerate all combinations of active and merged bits
    for active_pattern in itertools.product(["0", "1"], repeat=num_active):
        merged_bin_idx = (
            int("".join(active_pattern), 2) if active_pattern else 0
        )
        for merged_pattern in itertools.product(["0", "1"], repeat=num_merged):
            active_ptr = 0
            merged_ptr = 0
            full_state = []
            for s in qubit_states:
                if s == "active":
                    full_state.append(active_pattern[active_ptr])
                    active_ptr += 1
                elif s == "merged":
                    full_state.append(merged_pattern[merged_ptr])
                    merged_ptr += 1
                else:
                    full_state.append(str(s))
            idx = int("".join(full_state), 2)
            merged_vector[merged_bin_idx] += unmerged_prob_vector[idx]
    return merged_vector
