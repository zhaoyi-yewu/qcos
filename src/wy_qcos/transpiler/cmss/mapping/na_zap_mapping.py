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

import random
import numpy as np
import networkx as nx

from abc import ABC
from copy import deepcopy

from wy_qcos.transpiler.cmss.common.move import Move
from wy_qcos.transpiler.common.errors import MappingException


class NA_ZAP_Route(ABC):
    def __init__(self):
        self.qids = None
        self.mapping = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.operate_area = None
        self.storage_area = None
        self.qpu_config = None

    def prepare_data(self, qbit_num, gates, qpu_configs):
        """Prepare QPU configuration, gates and qubit num, build topo graph.

        Description:
            This method sets up internal data structures:
            - stores qpu_config, storage and operate areas
            - constructs an adjacency graph (ag) restricted to operate_area
            - precomputes all-pairs shortest path lengths on the operate graph
            - initializes scheduling lists and result container

        Args:
            qbit_num(int): Number of logical qubits.
            gates(list): List of gate objects (IR).
            qpu_configs: QPU configuration. Expected keys:
                - "storage_area": iterable of storage locations
                - "operate_area": iterable of operate locations
                - "coupler_map": mapping of couplers
                - "readout_error": dict of readout errors (used later)

        Raises:
            MappingException: If storage area size is smaller than qbit_num.
        """
        self.qpu_config = qpu_configs
        self.storage_area = self.qpu_config["storage_area"]
        self.operate_area = self.qpu_config["operate_area"]

        # Build operate-area adjacency graph from coupler_map entries that
        # fall into operate_area
        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config["coupler_map"].items():
            if (a not in self.operate_area) or (b not in self.operate_area):
                continue
            self.ag.add_edge(a, b)
        # Precompute shortest path lengths on operate graph (Dijkstra)
        self.ag.shortest_length = dict(
            nx.shortest_path_length(
                self.ag,
                source=None,
                target=None,
                weight=None,
                method="dijkstra",
            )
        )

        self.gates = gates
        self.qbit_num = qbit_num
        if len(self.storage_area) < self.qbit_num:
            raise MappingException(
                f"not enough qubits, need {self.qbit_num}, "
                f"but only {len(self.operate_area)}."
            )
        # Lists used for gate/qubit scheduling and final result
        self.gate_scheduling_list = []
        self.qubit_scheduling_list = []
        self.res = []

    def scheduling(self):
        """ASAP scheduling (As-Soon-As-Possible) for the given gates IR.

        This scheduler groups gates into time stages respecting device
        constraints:

        - single-qubit gates can be scheduled on their qubit's
          earliest available time.
        - two-qubit gates need a pair of operate-area atoms (Rydberg
          pair),and the number of parallel two-qubit gates per stage is
          limited by the number of available operate-area coupler edges

        It builds:

        - self.gate_scheduling_list: list of gate-lists per stage
        - self.qubit_scheduling_list: list of qubit-id lists per stage
        - self.storage_area_oloc and self.operate_area_oloc placeholders
          (filled later)

        Returns:
            list: list of measurement gate objects encountered (measure
            operations).
        """
        measure_op = []
        # Limit on simultaneously executable two-qubit gates determined by
        # number of operate edges
        na_ryd_limit = len(self.ag.edges())

        # Track per-logical-qubit available time index (initially 0)
        list_qubit_time = [0 for i in range(len(self.gates))]

        # Track how many two-qubit gates scheduled per stage
        two_qubit_gate_list = [0 for i in range(len(self.gates))]

        for gate in self.gates:
            if gate.name in ("barrier", "measure"):
                if gate.name == "measure":
                    measure_op.append(gate)
                continue

            if len(gate.targets) == 1:
                # Single-qubit gate
                tg = list_qubit_time[gate.targets[0]]

                #  # Create a new stage if needed
                if tg >= len(self.gate_scheduling_list):
                    self.gate_scheduling_list.append([])
                    self.qubit_scheduling_list.append([])

                self.gate_scheduling_list[tg].append(gate)
                self.qubit_scheduling_list[tg].append(gate.targets[0])

                # single-qubit gate does not advance time in this model
                # (keeps same tg)
                list_qubit_time[gate.targets[0]] = tg
            else:
                # Two-qubit gate
                tq0 = list_qubit_time[gate.targets[0]]
                tq1 = list_qubit_time[gate.targets[1]]
                tg = max(tq0, tq1)

                # If current stage has reached two-qubit gate capacity,
                # postpone to next stage(s)
                while True:
                    # Ensure the stage exists
                    if tg >= len(self.gate_scheduling_list):
                        self.gate_scheduling_list.append([])
                        self.qubit_scheduling_list.append([])

                    # Check if can add a two-qubit gate to this stage
                    if two_qubit_gate_list[tg] < na_ryd_limit:
                        # Add gate to current stage and mark occupancy
                        self.gate_scheduling_list[tg].append(gate)
                        two_qubit_gate_list[tg] += 1

                        for qid in gate.targets:
                            if qid not in self.qubit_scheduling_list[tg]:
                                self.qubit_scheduling_list[tg].append(qid)
                        # Advance logical qubits to next stage (they
                        # become busy for next stage)
                        tg += 1
                        list_qubit_time[gate.targets[0]] = tg
                        list_qubit_time[gate.targets[1]] = tg
                        break

                    # Cannot add to this stage, try the next one
                    tg += 1

        stage_num = len(self.gate_scheduling_list)

        # Record storage and operate area occupancy maps to prevent atom
        # position conflicts.
        # Occupied positions map to logical qubit id; free positions set to -1.
        self.storage_area_oloc = [
            {a: -1 for a in self.storage_area} for _ in range(stage_num + 1)
        ]
        self.operate_area_oloc = [
            {a: -1 for a in self.operate_area} for _ in range(stage_num + 1)
        ]

        return measure_op

    def get_cost(self, mapping):
        """Calculate the movement cost for a given mapping plan.

        Description:
            Cost is computed as Manhattan-like distance between consecutive
            stages for each atom movement. The objective is to minimize total
            movement steps.

            Notes about movement model (device-specific):
            - Only single-atom moves are supported.
            - Movement is grid-like (row/column moves).
            - Each moved grid step costs 1 time unit (ms in device model).

        Args:
            mapping (list[dict]): mapping for each stage. Each stage is a dict
                mapping logical qubit id -> physical location string.

        Returns:
            int: total movement cost across the mapping plan.
        """
        cost = 0
        pre_stage = None
        for idx, stage in enumerate(mapping):
            # Initial placement stage (index 0) involves no movement
            if idx > 0:
                for qid in range(len(stage)):
                    # Movement types:
                    # 1) storage -> operate
                    # 2) operate -> storage
                    # 3) operate -> operate

                    pre_na_id = int(pre_stage[qid][1:])
                    pre_coordinate = (int(pre_na_id / 20), pre_na_id % 20)

                    na_id = int(stage[qid][1:])
                    coordinate = (int(na_id / 20), na_id % 20)

                    cost += abs(pre_coordinate[0] - coordinate[0]) + abs(
                        pre_coordinate[1] - coordinate[1]
                    )

            pre_stage = stage
        return cost

    def find_ryd_pos(self, stage):
        """Find an unused Rydberg (operate-area) atom pair for a given stage.

        Description:
            This function randomly samples edges (pairs of operate-area nodes)
            and returns the first pair where both positions are free (not
            occupied) in the operate_area_oloc at the provided stage.

        Args:
            stage (int): stage index for which to find a free Rydberg pair.

        Returns:
            tuple: (pos_a, pos_b) a pair of operate-area node identifiers.
        """
        while True:
            edges = random.choice(list(self.ag.edges()))
            a, b = edges
            if (
                self.operate_area_oloc[stage][a] == -1
                and self.operate_area_oloc[stage][b] == -1
            ):
                return (a, b)

    def find_pos(self, stage):
        """Find an unused storage-area position for a given stage.

        Description:
            Randomly picks a storage-area location that is currently free in
            storage_area_oloc[stage].

        Args:
            stage (int): stage index for which to find a free storage location.

        Returns:
            any: a storage-area location identifier which is free.
        """
        while True:
            pos = random.choice(list(self.storage_area))
            if self.storage_area_oloc[stage][pos] == -1:
                return pos

    def get_init_mapping_and_placing(self, mapping):
        """Initialize atom positions across mapping stages.

        Description:
            The method assigns initial storage-area positions for logical
            qubits at stage 0 based on readout_error ranking (prefer lower
            error).For subsequent stages, it allocates operate-area pairs for
            two-qubit gates and appropriate storage positions for single-qubit
            gates, attempting to reuse previous positions when possible.

        Args:
            mapping (list[dict]): preallocated mapping list (each stage a dict
                                  logical_qubit_id -> None/position). This list
                                  will be filled in place.

        Returns:
            list[dict]: mapping after initial placement (same structure as
            input).
        """
        pre_stage = None
        for idx, stage in enumerate(mapping):
            if idx == 0:
                # Initial stage: place all logical qubits in storage area.
                err_dict = {}
                for k, v in self.qpu_config["readout_error"].items():
                    if k in self.storage_area:
                        err_dict[k] = v

                # Choose storage positions sorted by readout error (lowest
                # first)
                sq = sorted(err_dict.items(), key=lambda e: e[1])[
                    : self.qbit_num
                ]
                init_map = {a: b[0] for a, b in zip(range(self.qbit_num), sq)}
                for qid in range(self.qbit_num):
                    stage[qid] = init_map[qid]
                    self.storage_area_oloc[idx][stage[qid]] = qid
            else:
                # For each subsequent stage:
                #   - single-qubit gates can be executed at either operate or
                # storage area
                #   - two-qubit gates require a pair of operate-area (Rydberg)
                # positions

                # First handle two-qubit gates; single-qubit gates are handled
                # afterwards
                for gate in self.gate_scheduling_list[idx - 1]:
                    if len(gate.targets) == 2:
                        qid_0 = gate.targets[0]
                        qid_1 = gate.targets[1]
                        if (
                            pre_stage[qid_0] in self.storage_area
                            and pre_stage[qid_1] in self.operate_area
                        ):
                            # Find neighbor of previous operate position and
                            # place qid_0 there
                            pre_neighbor = list(
                                self.ag.neighbors(pre_stage[qid_1])
                            )
                            if (
                                self.operate_area_oloc[idx][pre_neighbor[0]]
                                > -1
                            ):
                                # pos have atom
                                pos = self.find_ryd_pos(idx)
                                stage[qid_0] = pos[0]
                                stage[qid_1] = pos[1]

                                # Mark operate positions as occupied by logical
                                # qubits
                                self.operate_area_oloc[idx][pos[0]] = qid_0
                                self.operate_area_oloc[idx][pos[1]] = qid_1
                            else:
                                # Move qid_0 to operate neighbor position;
                                stage[qid_0] = pre_neighbor[0]
                                self.operate_area_oloc[idx][stage[qid_0]] = (
                                    qid_0
                                )

                                # qid_1 remains
                                stage[qid_1] = pre_stage[qid_1]
                                self.operate_area_oloc[idx][stage[qid_1]] = (
                                    qid_1
                                )

                        # Case: qid_0 in operate and qid_1 in storage
                        if (
                            pre_stage[qid_0] in self.operate_area
                            and pre_stage[qid_1] in self.storage_area
                        ):
                            pre_neighbor = list(
                                self.ag.neighbors(pre_stage[qid_0])
                            )
                            if (
                                self.operate_area_oloc[idx][pre_neighbor[0]]
                                > -1
                            ):
                                # pos have atom
                                pos = self.find_ryd_pos(idx)
                                stage[qid_0] = pos[0]
                                stage[qid_1] = pos[1]

                                # Mark operate positions as occupied by logical
                                # qubits
                                self.operate_area_oloc[idx][pos[0]] = qid_0
                                self.operate_area_oloc[idx][pos[1]] = qid_1
                            else:
                                # Move qid_1 to neighbor operate position;
                                stage[qid_1] = pre_neighbor[0]
                                self.operate_area_oloc[idx][stage[qid_1]] = (
                                    qid_1
                                )

                                # qid_0 remains
                                stage[qid_0] = pre_stage[qid_0]
                                self.operate_area_oloc[idx][stage[qid_0]] = (
                                    qid_0
                                )
                        # Case: both qubits were in storage previously
                        # find a free Rydberg pair
                        if (
                            pre_stage[qid_0] in self.storage_area
                            and pre_stage[qid_1] in self.storage_area
                        ):
                            pos = self.find_ryd_pos(idx)
                            stage[qid_0] = pos[0]
                            stage[qid_1] = pos[1]

                            # Mark operate positions as occupied by logical
                            # qubits
                            self.operate_area_oloc[idx][pos[0]] = qid_0
                            self.operate_area_oloc[idx][pos[1]] = qid_1
                        # Case: both in operate area previously
                        if (
                            pre_stage[qid_0] in self.operate_area
                            and pre_stage[qid_1] in self.operate_area
                        ):
                            # If neighbor already, keep positions;
                            # otherwise find free pair
                            pre_neighbor = list(
                                self.ag.neighbors(pre_stage[qid_0])
                            )
                            if pre_stage[qid_1] != pre_neighbor[0]:
                                pos = self.find_ryd_pos(idx)
                                stage[qid_0] = pos[0]
                                stage[qid_1] = pos[1]

                                self.operate_area_oloc[idx][pos[0]] = qid_0
                                self.operate_area_oloc[idx][pos[1]] = qid_1
                            else:
                                # Both qubits keep their previous operate
                                # positions
                                stage[qid_1] = pre_stage[qid_1]
                                self.operate_area_oloc[idx][stage[qid_1]] = (
                                    qid_1
                                )
                                stage[qid_0] = pre_stage[qid_0]
                                self.operate_area_oloc[idx][stage[qid_0]] = (
                                    qid_0
                                )

                # Handle single-qubit gates and cases where a target position
                # is None
                for gate in self.gate_scheduling_list[idx - 1]:
                    q_index = stage[gate.targets[0]]
                    if len(gate.targets) == 1 and q_index is None:
                        # Two cases:
                        # 1) single-qubit logical qubit needs to be in storage
                        # area -> inherit previous storage
                        # 2) or it was in operate area last stage; if that
                        # operate position is occupied,then allocate a storage
                        # position, otherwise keep operate position.
                        if pre_stage[gate.targets[0]] in self.operate_area:
                            # Previous stage in operate area, this stage needs
                            # to move out (so that two-qubit gates can use the
                            # operate area)
                            pos = self.find_pos(idx)
                            stage[gate.targets[0]] = pos
                            self.storage_area_oloc[idx][
                                stage[gate.targets[0]]
                            ] = gate.targets[0]
                        else:
                            # Previous stage in storage area, inherit previous
                            # storage position
                            stage[gate.targets[0]] = pre_stage[gate.targets[0]]
                            self.storage_area_oloc[idx][
                                stage[gate.targets[0]]
                            ] = gate.targets[0]

                # For qubits not involved in this stage, assign them to storage
                # area
                for qid in range(self.qbit_num):
                    if stage[qid] is None:
                        # If previous stage in storage, inherit that position
                        if pre_stage[qid] in self.storage_area:
                            stage[qid] = pre_stage[qid]
                            self.storage_area_oloc[idx][stage[qid]] = qid
                        else:
                            # If previous stage in operate area, move back to
                            # storage
                            pos = self.find_pos(idx)
                            stage[qid] = pos
                            self.storage_area_oloc[idx][stage[qid]] = qid
            pre_stage = stage
        return mapping

    def update_mapping(self, mapping):
        """Propose a new mapping by randomly updating the current mapping.

        Description:
            The update strategies include:
            - swapping operate-area positions between neighbors
            - swapping operate-area pairs
            - swapping or moving storage-area positions

        Args:
            mapping (list[dict]): current mapping plan (stages -> dicts).

        Returns:
            list[dict]: new mapping plan (deep copy) proposed by random update.
        """
        new_mapping = deepcopy(mapping)

        # Choose a random stage index to update
        idx = random.randint(0, len(self.gate_scheduling_list) - 1)
        stage = new_mapping[idx]
        # Choose a random logical qubit id
        qid = random.randint(0, self.qbit_num - 1)

        if stage[qid] in self.operate_area:
            # If the qubit is in operate area, randomly choose update action
            up_id = random.randint(0, 5)
            if up_id == 0:
                # Swap with a neighbor operate position
                neighbor = list(self.ag.neighbors(stage[qid]))
                neighbor_id = self.operate_area_oloc[idx][neighbor[0]]
                stage[neighbor_id] = stage[qid]
                stage[qid] = neighbor[0]
            else:
                # Swap with another Rydberg pair in operate area
                edge = random.choice(list(self.ag.edges()))
                node_a, node_b = edge

                if (
                    self.operate_area_oloc[idx][node_a] == -1
                    and self.operate_area_oloc[idx][node_b] == -1
                ):
                    # If the target Rydberg pair is free, move into this pai
                    neighbor = list(self.ag.neighbors(stage[qid]))
                    neighbor_id = self.operate_area_oloc[idx][neighbor[0]]
                    stage[qid] = node_a
                    stage[neighbor_id] = node_b
                else:
                    # If the pair is used, swap positions across the two pairs
                    neighbor = list(self.ag.neighbors(stage[qid]))
                    neighbor_id = self.operate_area_oloc[idx][neighbor[0]]

                    # Identify logical qubits currently occupying the target
                    # pair
                    swap_id_a = self.operate_area_oloc[idx][node_a]
                    swap_id_b = self.operate_area_oloc[idx][node_b]

                    # Swap the two Rydberg pairs' occupants
                    stage[swap_id_a] = stage[qid]
                    stage[swap_id_b] = stage[neighbor_id]

                    stage[qid] = node_a
                    stage[neighbor_id] = node_b

        else:
            # Qubit is in storage area: randomly choose a storage position
            # to swap/move to
            up_local = random.choice(list(self.storage_area))
            if self.storage_area_oloc[idx][up_local] >= 0:
                # If the chosen storage location already has an atom,
                # swap positions
                tmp_id = self.storage_area_oloc[idx][up_local]

                stage[tmp_id] = stage[qid]
                stage[qid] = up_local

            else:
                # Move the atom to the free storage location
                stage[qid] = up_local

        return new_mapping

    def update_storage_and_operate_area_oloc(self, mapping):
        """Update  storage and operate areas oloc if a new mapping is accepted.

        Description:
            This function rebuild storage_area_oloc and operate_area_oloc from
            the provided mapping: positions (keys) map to logical qubit id or
            -1 if free.

        Args:
            mapping (list[dict]): mapping plan across stages to update
            occupancy from.
        """
        stage_num = len(self.gate_scheduling_list)
        self.storage_area_oloc = [
            {a: -1 for a in self.storage_area} for _ in range(stage_num + 1)
        ]
        self.operate_area_oloc = [
            {a: -1 for a in self.operate_area} for _ in range(stage_num + 1)
        ]

        for idx, stage in enumerate(mapping):
            for key, value in stage.items():
                if value in self.storage_area:
                    self.storage_area_oloc[idx][value] = key
                if value in self.operate_area:
                    self.operate_area_oloc[idx][value] = key

    def init_para(self):
        """Initialize parameters for simulated annealing (SA).

        Returns:
            tuple: (alpha, t, markovlen)
                alpha (float): temperature decay factor per outer loop.
                t (tuple): temperature range as (t_min, t_init).
                markovlen (int): number of inner iterations (Markov chain
                length).
        """
        alpha = 0.98
        t = (1, 100)
        markovlen = 200
        return alpha, t, markovlen

    def sa_mapping_and_placing(self):
        """Perform simulated annealing to search a mapping and placement.

        Description:
            The SA objective is to minimize total movement cost computed by
            get_cost.
            Procedure:
            - initialize mapping using get_init_mapping_and_placing
            - iteratively propose new mappings via update_mapping
            - accept lower-cost mappings or accept worse mappings with a
            probability dependent on temperature
            - gradually lower temperature until below t_min, then validate
            best mapping

        Returns:
            list[dict]: best mapping plan found after annealing and validation.
        """
        # Target: minimize movement distance (device modeled as 20x10 grid)
        # Initialize mapping structure:
        # number of stages = len(gate_scheduling_list) + 1

        # column = self.qpu_config.get("column")
        # row = self.qpu_config.get("row")

        mapping = [
            {a: None for a in range(self.qbit_num)}
            for _ in range(len(self.gate_scheduling_list) + 1)
        ]

        # Initialize mapping placements
        cur_mapping = self.get_init_mapping_and_placing(mapping)

        # Compute initial mapping cost
        cur_cost = self.get_cost(cur_mapping)

        # create best cost and best mapping for sa
        best_cost = cur_cost
        best_mapping = deepcopy(cur_mapping)

        alpha, t2, markovlen = self.init_para()

        # # starting temperature (t_init)
        t = t2[1]
        # Record the optimal solution during the iteration process
        result = None

        while t > t2[0]:
            for _ in np.arange(markovlen):
                # Propose a new mapping
                new_maping = self.update_mapping(cur_mapping)
                # Evaluate new mapping cost
                new_cost = self.get_cost(new_maping)

                # Accept if cost improved
                if new_cost <= cur_cost:
                    # update solution
                    cur_cost = new_cost
                    cur_mapping = deepcopy(new_maping)
                    # Update occupancy tables to reflect accepted mapping
                    self.update_storage_and_operate_area_oloc(cur_mapping)
                    # Update best solution if improved
                    if new_cost < best_cost:
                        best_cost = new_cost
                        best_mapping = deepcopy(new_maping)
                else:
                    # accept the solution with a certain probability
                    if np.random.rand() < np.exp(-(new_cost - cur_cost) * 8):
                        cur_cost = new_cost
                        cur_mapping = deepcopy(new_maping)
                        self.update_storage_and_operate_area_oloc(cur_mapping)
            # Cool down
            t = alpha * t
        result = self.validate_mapping(best_mapping)

        return result

    def validate_mapping(self, mapping):
        """Validate the final mapping and remove redundant moves.

        Description:
            Post-processing: if a logical qubit stays in storage across two
            consecutive stages, the mapping keep the previous storage position
            (no move required).

        Args:
            mapping (list[dict]): mapping to validate.

        Returns:
            list[dict]: cleaned mapping after validation.
        """
        new_mapping = deepcopy(mapping)
        pre_stage = None
        for stage_id, stage in enumerate(new_mapping):
            # Initial stage: no move involved
            if stage_id == 0:
                pre_stage = stage
                continue
            for qid in range(self.qbit_num):
                # If both previous and current positions are in storage area,
                # keep previous (no move)
                if (
                    stage[qid] in self.storage_area
                    and pre_stage[qid] in self.storage_area
                ):
                    stage[qid] = pre_stage[qid]
            pre_stage = stage

        return new_mapping

    def routing_asap(self, mapping, measure):
        """Convert the mapping plan into a sequence of Move and gates.

        Description:
            For each stage (except initial), create Move operations for atoms
            whose positions changed compared to previous stage. Then insert
            scheduled gates for that stage and finally append measurement
            operations (with updated physical positions).

        Args:
            mapping (list[dict]): mapping plan across stages.
            measure (list): list of measurement gate objects collected
            during scheduling.

        Returns:
            list: list of operations(Move and gate objects)ready for execution.

        """
        pre_stage = None
        for stage_id, stage in enumerate(mapping):
            # For each stage, first add move to reach the stage atom positions,
            # then append the gates scheduled for that stage.
            # Skip the initial stage (no moves necessary)
            if stage_id == 0:
                pre_stage = stage
                continue

            for key, value in stage.items():
                # position differs from previous stage, add a Move operation.
                # Prefer moving atoms in operate area first

                if value != pre_stage[key]:
                    self.res.append(
                        Move(
                            targets=[key],
                            arg_value=[
                                int(pre_stage[key][1:]),
                                int(value[1:]),
                            ],
                        )
                    )
            # After moves for the stage, append gates of that stage.
            for gate in self.gate_scheduling_list[stage_id - 1]:
                qid_list = gate.targets
                for key, id in enumerate(qid_list):
                    gate.targets[key] = int(stage[id][1:])

                self.res.append(gate)

            pre_stage = stage

        # Update measurement gates to the final physical positions of
        # logical qubits
        for idx in range(len(measure)):
            qid = measure[idx].targets[0]
            measure[qid].targets = [int(mapping[-1][qid][1:])]

        # Append measurement operations to final result list
        self.res += measure

        return self.res

    def execute_with_order(self):
        """Run scheduling, mapping and routing to produce final op list.

        Description:
            Workflow:
                1. scheduling() to generate gate stages and measure ops
                2. sa_mapping_and_placing() to find a mapping plan
                3. routing_asap() to create Move and gate execution sequence

        Returns:
            list: ordered list of operations (Move and gates) mapping logical
                  qubits to physical qpu positions ready for execution.
        """
        measure_op = self.scheduling()

        mapping = self.sa_mapping_and_placing()

        res = self.routing_asap(mapping, measure_op)

        return res
