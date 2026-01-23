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
import random
import math
import networkx as nx
from networkx import Graph

from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.transpiler.cmss.mapping.utils.front_circuit import FrontCircuit


class SimulatedAnnealingMapping:
    def __init__(self, level="light") -> None:
        """Init SimulatedAnnealingMapping.

        Args:
            level (str, optional): If choose light level, it will be faster.
                Defaults to "light".
        """
        if level == "light":
            self.alpha = 0.9
            self.markovlen = 30
        elif level == "heavy":
            self.alpha = 0.95
            self.markovlen = 70
        else:
            raise ValueError(f"Unsupport level: {level}.")
        self.temperature = (1.0, 100.0)

    def cal_cost_matrix(
        self,
        cost_m: np.ndarray,
        current_sol: list,
        phy_distance: dict,
        qubits_logic: tuple,
    ):
        """Estimate the cost of inserting swaps under the current mapping.

        Args:
            cost_m (np.ndarray): cost of matrix.
            current_sol (list): current mapping.
            phy_distance (dict): dict of shortest path length.
            qubits_logic (tuple): logic qubits.

        Returns:
            float: cost of swaps in current mapping.
        """
        cost_total = 0
        for q1_log in qubits_logic:
            for q2_log in qubits_logic:
                q1_phy, q2_phy = current_sol[q1_log], current_sol[q2_log]
                num_swap = phy_distance[q1_phy][q2_phy] - 1
                cost_total += num_swap * cost_m[q1_log][q2_log]
        return cost_total

    def cal_cost_matrix_incremental(
        self,
        cost_m: np.ndarray,
        current_sol: list,
        phy_distance: dict,
        qubits_logic: tuple,
        q_swap: tuple | None = None,
        cost_cur: float | None = None,
    ) -> float:
        """Incrementally calculate cost after swapping two logical qubits.

        Args:
            cost_m (np.ndarray): cost matrix (weights of logical qubit pairs)
            current_sol (list): current mapping
            phy_distance (dict): physical qubits shortest paths
            qubits_logic (tuple): logic qubits
            q_swap (tuple, optional): (q_log1, q_log2) swapped in this step
            cost_cur (float, optional): previous total cost

        Returns:
            float: new total cost
        """
        # full computation
        if q_swap is None or cost_cur is None:
            return self.cal_cost_matrix(
                cost_m, current_sol, phy_distance, qubits_logic
            )

        q1, q2 = q_swap
        cost_total = cost_cur

        # qubit mapping before swap
        phy1_old, phy2_old = current_sol[q2], current_sol[q1]
        # qubit mapping after swap
        phy1_cur, phy2_cur = current_sol[q1], current_sol[q2]

        # update only pairs involving q1 or q2
        for q in qubits_logic:
            if q not in (q1, q2):
                phy_q = current_sol[q]

                # update contribution of pair (q1, q)
                if cost_m[q1][q] != 0:
                    # remove old contribution
                    num_swap = phy_distance[phy1_old][phy_q] - 1
                    cost_total -= num_swap * cost_m[q1][q]
                    # add new contribution
                    num_swap = phy_distance[phy1_cur][phy_q] - 1
                    cost_total += num_swap * cost_m[q1][q]

                # update contribution of pair (q2, q)
                if cost_m[q2][q] != 0:
                    # remove old contribution
                    num_swap = phy_distance[phy2_old][phy_q] - 1
                    cost_total -= num_swap * cost_m[q2][q]
                    # add new contribution
                    num_swap = phy_distance[phy2_cur][phy_q] - 1
                    cost_total += num_swap * cost_m[q2][q]

        # finally update the pair (q1, q2)
        cost_total -= (phy_distance[phy1_old][phy2_old] - 1) * cost_m[q1][q2]
        cost_total += (phy_distance[phy1_cur][phy2_cur] - 1) * cost_m[q1][q2]

        return cost_total

    def init_cost_matrix(
        self,
        dependency_graph: DG,
        coupling_graph: Graph,
        add_weight: bool = False,
    ):
        """Initialize cost matrix.

        Args:
            dependency_graph (DG): dependency graph of the circuit.
            coupling_graph (Graph): adjacency graph of the quantum machine.
            add_weight (bool, optional): ignore two-qubit gates acting
                consecutively on the same two qubits. Defaults to False.

        Returns:
            tuple(np.ndarray, set): cost matrix and qubits set.
        """
        num_q, qubits_logic = len(coupling_graph), set()
        cost_m = np.zeros((num_q, num_q))
        front_circ = FrontCircuit(dependency_graph, coupling_graph)
        num_cx = len(dependency_graph.nodes())
        num_cx_cur = num_cx
        weight = 1.0
        while len(front_circ.front_layer) != 0:
            # reduce the weight as the remaining number of gates decreases
            weight = num_cx_cur / num_cx
            current_nodes = front_circ.front_layer
            num_cx_cur -= len(current_nodes)
            for node in current_nodes:
                # increasing the cost of the two bits affected by the gate
                op = dependency_graph.nodes[node]["qubits"]
                if len(op) == 1:
                    continue
                if len(op) > 2:
                    raise ValueError("Not support more than 2 qubits gate.")
                if add_weight:
                    flag = 1
                    # ignore the successive CX
                    if dependency_graph.out_degree(node) == 1:
                        qubits = op
                        op_next = dependency_graph.nodes[
                            list(dependency_graph.successors(node))[0]
                        ]["qubits"]
                        qubits_next = op_next
                        if (
                            qubits[0] == qubits_next[0]
                            and qubits[1] == qubits_next[1]
                        ):
                            flag = 0
                        if (
                            qubits[0] == qubits_next[1]
                            and qubits[1] == qubits_next[0]
                        ):
                            flag = 0
                    dependency_graph.nodes[node]["weight"] = weight * flag
                qubits = op
                qubits_logic.add(qubits[0])
                qubits_logic.add(qubits[1])
                if add_weight:
                    cost_m[qubits[0]][qubits[1]] += dependency_graph.nodes[
                        node
                    ]["weight"]
                else:
                    cost_m[qubits[0]][qubits[1]] += weight
            front_circ.execute_front_layer()
        return cost_m, qubits_logic

    def run(
        self,
        dependency_graph: DG,
        coupling_graph: Graph,
        start_mapping=None,
    ):
        """Heuristic qubit mapping based on simulated annealing.

        Args:
            dependency_graph (DG): dependency graph of the circuit.
            coupling_graph (Graph): adjacency graph of the hardware.
            start_mapping (list, optional): partial mapping. Defaults to None.

        Returns:
            list[int]: represents a mapping in which indices and values stand
                for logical and physical qubits.
        """
        # the shortest path between any two bits
        coupling_graph.shortest_length_weight = dict(
            nx.shortest_path_length(
                coupling_graph,
                source=None,
                target=None,
                weight=None,
                method="dijkstra",
            )
        )
        phy_distance = coupling_graph.shortest_length_weight

        if start_mapping is None:
            start_mapping = list(coupling_graph.nodes)
        if (
            len(start_mapping) != len(coupling_graph.nodes())
            or None in start_mapping
        ):
            # if logical qubits is less than physical, we extend logical qubit
            # to ensure the completeness and delete added qubits at the end of
            # the algorithm
            for v in coupling_graph.nodes():
                if v not in start_mapping:
                    count = start_mapping.count(None)
                    if count:
                        idx = start_mapping.index(None)
                        start_mapping[idx] = v
                        continue
                    start_mapping.append(v)
        # initialize the weighted cost matrix
        cost_m, qubits_logic = self.init_cost_matrix(
            dependency_graph, coupling_graph, True
        )
        qubits_logic = tuple(qubits_logic)
        # Simulated Annealing
        solution_new = start_mapping
        solution_cur = solution_new.copy()
        value_cur = self.cal_cost_matrix_incremental(
            cost_m,
            solution_new,
            phy_distance,
            qubits_logic,
            q_swap=None,
            cost_cur=None,
        )
        solution_best = solution_new.copy()
        value_best = value_cur

        alpha = self.alpha
        t_min, t_max = self.temperature
        markovlen = self.markovlen

        while t_max > t_min:
            for _ in range(markovlen):
                # select two bits
                q_log1 = random.choice(qubits_logic)
                q_phy1 = solution_new[q_log1]
                q_phy2 = random.choice(list(coupling_graph.neighbors(q_phy1)))
                q_log2 = solution_new.index(q_phy2)
                # Exchange, recalculate costs
                solution_new[q_log1], solution_new[q_log2] = (
                    solution_new[q_log2],
                    solution_new[q_log1],
                )
                value_new = self.cal_cost_matrix_incremental(
                    cost_m,
                    solution_new,
                    phy_distance,
                    qubits_logic,
                    q_swap=(q_log1, q_log2),
                    cost_cur=value_cur,
                )
                # accept this solution
                if value_new < value_cur:
                    # update solution
                    value_cur = value_new
                    solution_cur = solution_new.copy()
                    # renew best solution
                    if value_new < value_best:
                        value_best = value_new
                        solution_best = solution_new.copy()
                else:
                    # accept the solution with a certain probability
                    if random.random() < math.exp(
                        -(value_new - value_cur) / t_max
                    ):
                        value_cur = value_new
                        solution_cur = solution_new.copy()
                    else:
                        solution_new = solution_cur.copy()

            t_max = alpha * t_max

        return solution_best[: dependency_graph.num_q]
