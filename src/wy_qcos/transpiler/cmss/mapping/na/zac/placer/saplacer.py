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
import sys
import math
import random
import numpy as np
from copy import deepcopy
from random import randrange, uniform


class SAPlacer:
    """Class to find a qubit initial placement using Simulated Annealing (SA).

    Description:
        This class implements a simulated annealing based optimizer for
        determining the initial placement of logical qubits onto physical
        storage locations of a QPU. The optimization objective is to minimize
        the weighted interaction distance induced by two-qubit gates.
    """

    def __init__(self):
        """Initialize the SA placer.

        Description:
            Initialize simulated annealing parameters and internal state.
            Problem-specific information such as qubit number, gate list,
            and hardware configuration are assigned later in `run()`.
        """
        self.initialize_param()
        self.n_qubit = 0
        self.list_gate = []
        self.movement = []
        self.list_qubit_dict_gate = []

    def initialize_param(self):
        """Initialize simulated annealing hyper-parameters.

        Description:
            Set temperature schedule parameters, iteration limits, and
            bookkeeping variables for tracking the current and best
            solutions during the simulated annealing process.
        """
        # SA temperature parameters
        self.sa_t = 100000.0
        self.sa_t1 = 4.0
        self.sa_t_frozen = 0.0001

        # Annealing control parameters
        self.sa_p = 0.987
        self.sa_l = 400
        self.sa_n = 0
        # use for updating t
        self.sa_k = 7
        self.sa_c = 100
        self.sa_iter_limit = 100

        # Statistics for adaptive temperature update
        self.sa_delta_cost_cnt = 0
        self.sa_delta_sum = 0
        self.sa_delta = 0
        self.sa_n_trials = 1

        # Solution bookkeeping
        self.best_mapping = None
        self.best_cost = sys.maxsize
        self.current_mapping = None
        self.current_cost = sys.maxsize

    def preprocessing(self):
        """Preprocess gate information and hardware geometry.

        Description:
            Construct weighted interaction information for each logical
            qubit based on the gate execution order. In addition, compute
            nearest coupler indices and optimal storage positions for
            operation sites to enable fast cost evaluation.
        """
        # Weight gates by execution stage (earlier stages weighted higher)
        max_level = 5
        self.list_weight = [1 - 0.1 * l for l in range(max_level)]
        self.list_qubit_dict_gate = [dict() for i in range(self.n_qubit)]

        # Build weighted interaction list for each qubit
        for i, gates in enumerate(self.list_gate):
            if i < max_level:
                weight = self.list_weight[i]
            else:
                weight = self.list_weight[-1]
            for gate in gates:
                if gate[1] in self.list_qubit_dict_gate[gate[0]]:
                    self.list_qubit_dict_gate[gate[0]][gate[1]] += weight
                else:
                    self.list_qubit_dict_gate[gate[0]][gate[1]] = weight
                # Symmetric interaction
                self.list_qubit_dict_gate[gate[1]][gate[0]] = (
                    self.list_qubit_dict_gate[gate[0]][gate[1]]
                )

        # Precompute nearest coupler for each storage site
        self.w_near = {a: -1 for a in self.qpu_config["storage_area"]}
        self.near = {a: "" for a in self.qpu_config["operate_area"]}
        opt_dis = {a: np.inf for a in self.qpu_config["operate_area"]}

        for pos in self.qpu_config["storage_area"]:
            min_val = np.inf
            near = -1
            for k, (a, b) in self.qpu_config["coupler_map"].items():
                cost = 0
                # Mid-point of a coupler defines the effective interaction site
                mid_id = (int(a[1:]) + int(b[1:])) / 2
                pre_coordinate = (int(mid_id / 20), mid_id % 20)

                na_id = int(pos[1:])
                coordinate = (int(na_id / 20), na_id % 20)

                cost = abs(pre_coordinate[0] - coordinate[0]) + abs(
                    pre_coordinate[1] - coordinate[1]
                )
                if cost < min_val:
                    near = k
                    min_val = cost

                # Track nearest storage site for each operation zone
                dis_a = self.get_steps(a, na_id)
                if dis_a < opt_dis[a]:
                    opt_dis[a] = dis_a
                    self.near[a] = pos
                dis_b = self.get_steps(b, na_id)
                if dis_b < opt_dis[b]:
                    opt_dis[b] = dis_b
                    self.near[b] = pos

            self.w_near[pos] = int(near[-1])

    def run(self, qpu_config, n_qubit: int, list_gate: list):
        """Run simulated annealing to find an optimized initial placement.

        Args:
            qpu_config (dict): Hardware configuration of the QPU.
            n_qubit (int): Number of logical qubits.
            list_gate (list): Two-qubit gates grouped by execution stage.
        """
        self.n_qubit = n_qubit
        self.list_gate = list_gate
        self.qpu_config = qpu_config
        self.preprocessing()

        # Multiple SA trials (default is one)
        for _ in range(self.sa_n_trials):
            self.init_sa_solution()
            n_reject = 0
            self.sa_n = 0
            while self.sa_t > self.sa_t_frozen:
                self.sa_n += 1
                self.sa_delta_cost_cnt = 0
                self.sa_delta_sum = 0
                n_reject = 0
                for _ in range(self.sa_l):
                    # make movement and calculate cost difference
                    self.make_movement()
                    self.sa_delta_cost_cnt += 1
                    self.sa_delta_sum += abs(self.sa_delta)
                    if self.sa_delta <= 0:
                        # Accept better solution
                        self.current_cost += self.sa_delta
                        if self.best_cost - self.current_cost > 1e-9:
                            self.update_optimal_sol()
                    else:  # delta > 0
                        # Probabilistically accept worse solution
                        if self.accept_worse_sol():
                            self.current_cost += self.sa_delta
                        else:
                            # undo current movement
                            self.recover()
                            n_reject += 1
                self.update_temperature()
                if self.sa_n > self.sa_iter_limit:
                    break

    def make_movement(self):
        """Generate a random movement and compute its cost difference.

        Description:
            Randomly select a logical qubit and move it to a new storage
            position. If the target position is already occupied, perform
            a swap. Only the gates affected by this movement are used to
            compute the incremental cost difference.
        """
        # Randomly select a logical qubit to move
        qubit_to_move = randrange(self.n_qubit)
        old_pos = self.current_mapping[qubit_to_move]

        new_pos = random.choice(list(self.qpu_config["storage_area"]))

        # Check whether the target position is already occupied
        has_na = -1

        for qid in range(self.n_qubit):
            if self.current_mapping[qid] == new_pos:
                has_na = qid

        self.movement = (qubit_to_move, old_pos, new_pos, has_na)

        # Collect affected two-qubit interactions
        set_affected_gate = set()
        for gate_qubit in self.list_qubit_dict_gate[qubit_to_move]:
            weight = self.list_qubit_dict_gate[qubit_to_move][gate_qubit]
            if gate_qubit < qubit_to_move:
                set_affected_gate.add((qubit_to_move, gate_qubit, weight))
            else:
                set_affected_gate.add((gate_qubit, qubit_to_move, weight))

        if has_na > -1:
            for gate_qubit in self.list_qubit_dict_gate[has_na]:
                weight = self.list_qubit_dict_gate[has_na][gate_qubit]
                if gate_qubit < has_na:
                    set_affected_gate.add((has_na, gate_qubit, weight))
                else:
                    set_affected_gate.add((gate_qubit, has_na, weight))

        # Original cost contribution
        ori_cost = 0
        for gate in set_affected_gate:
            q0 = gate[0]
            q1 = gate[1]
            weight = gate[2]
            dis = self.distance(
                self.current_mapping[q0], self.current_mapping[q1]
            )
            ori_cost += weight * dis
        # Apply movement (swap or move)
        if has_na > -1:
            self.current_mapping[qubit_to_move] = new_pos
            self.current_mapping[has_na] = old_pos
        else:
            self.current_mapping[qubit_to_move] = new_pos

        # calculate new cost
        new_cost = 0
        for gate in set_affected_gate:
            q0 = gate[0]
            q1 = gate[1]
            weight = gate[2]
            dis = self.distance(
                self.current_mapping[q0], self.current_mapping[q1]
            )
            new_cost += weight * dis

        self.sa_delta = new_cost - ori_cost

    def recover(self):
        """Undo the last rejected movement."""
        qubit_to_move, old_pos, new_pos, has_na = self.movement

        if has_na > -1:
            self.current_mapping[qubit_to_move] = old_pos
            self.current_mapping[has_na] = new_pos
        else:
            self.current_mapping[qubit_to_move] = old_pos

    def init_sa_solution(self):
        """Generate an initial mapping based on readout error ranking."""
        self.current_mapping = []

        # Initial stage: place all logical qubits in storage area.
        err_dict = {}
        for k, v in self.qpu_config["readout_error"].items():
            if k in self.qpu_config["storage_area"]:
                err_dict[k] = v
        sq = sorted(err_dict.items(), key=lambda e: e[1])[: self.n_qubit]
        self.current_mapping = {
            a: b[0] for a, b in zip(range(self.n_qubit), sq)
        }
        self.current_cost = self.get_cost()

    def get_cost(self):
        """Calculate the movement cost for a given mapping plan.

        Description:
            Cost is computed as Manhattan-like distance between consecutive
            stages for each atom movement. The objective is to minimize total
            movement steps.
            cost(mapping) = sum for gate in G2 (w_g * gCost(q0,q1))
            where:gCost is movement steps for closest Rydberg zone site,
            w_g = max(0.1, 1-0.1(t-1)),where t is Rydberg stage

        Returns:
            int: total movement cost across the mapping plan.
        """
        cost = 0

        for i in range(self.n_qubit):
            for j in range(i):
                if j in self.list_qubit_dict_gate[i]:
                    dis = self.distance(
                        self.current_mapping[i], self.current_mapping[j]
                    )
                    cost += dis * self.list_qubit_dict_gate[i][j]

        return cost

    def distance(self, posa, posb):
        """Compute effective interaction distance between two atoms."""
        gate_near = int((self.w_near[posa] + self.w_near[posb]) / 2)
        a, b = self.qpu_config["coupler_map"]["R_G" + str(gate_near)]

        c = (int(a[1:]) + int(b[1:])) / 2

        cost = self.get_steps(posa, c) + self.get_steps(posb, c)

        return cost

    def get_steps(self, posa, posb):
        """Compute Manhattan distance between two physical positions."""
        pre_na_id = int(posa[1:])
        pre_coordinate = (int(pre_na_id / 20), pre_na_id % 20)

        na_id = posb
        coordinate = (int(na_id / 20), na_id % 20)

        return abs(pre_coordinate[0] - coordinate[0]) + abs(
            pre_coordinate[1] - coordinate[1]
        )

    def update_temperature(self):
        """Update SA temperature according to adaptive schedule."""
        if self.sa_n <= self.sa_k:
            self.sa_t = (
                (self.sa_t1 * abs(self.sa_delta_sum) / self.sa_delta_cost_cnt)
                / self.sa_n
                / self.sa_c
            )
        else:
            self.sa_t = (
                self.sa_t1 * abs(self.sa_delta_sum) / self.sa_delta_cost_cnt
            ) / self.sa_n

    def accept_worse_sol(self):
        """Metropolis criterion for accepting worse solutions."""
        accept = (uniform(0, 1)) <= math.exp(-(self.sa_delta) / (self.sa_t))
        return accept

    def update_optimal_sol(self):
        """Update the globally best solution found so far."""
        self.best_mapping = deepcopy(self.current_mapping)
        self.best_cost = self.current_cost
