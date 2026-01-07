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
import networkx as nx
from networkx import Graph

from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.transpiler.cmss.mapping.utils.front_circuit import FrontCircuit


def cal_cost_matrix(
    cost_m: np.ndarray,
    current_sol: list,
    shortest_length_G: dict,
    qubits_logic: tuple,
):
    """Estimate the cost of inserting swaps under the current mapping.

    Args:
        cost_m (np.ndarray): cost of matrix.
        current_sol (list): current mapping.
        shortest_length_G (dict): dict of shortest path length.
        qubits_logic (tuple): logic qubits.

    Returns:
        float: cost of swaps in current mapping.
    """
    cost_total = 0
    for q1_log in qubits_logic:
        for q2_log in qubits_logic:
            q1_phy, q2_phy = current_sol[q1_log], current_sol[q2_log]
            num_swap = shortest_length_G[q1_phy][q2_phy] - 1
            cost_total += num_swap * cost_m[q1_log][q2_log]
    return cost_total


def init_cost_matrix(
    dependency_graph: DG, coupling_graph: Graph, add_weight: bool = False
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
                cost_m[qubits[0]][qubits[1]] += dependency_graph.nodes[node][
                    "weight"
                ]
            else:
                cost_m[qubits[0]][qubits[1]] += weight
        front_circ.execute_front_layer()
    return cost_m, qubits_logic


def init_para():
    """Initialize parameters for simulated annealing."""
    alpha = 0.95
    t = (1, 100)
    markovlen = 70
    return alpha, t, markovlen


def sa_initial_mapping(
    dependency_graph: DG,
    coupling_graph: Graph,
    start_mapping=None,
):
    """Heuristic qubit mapping based on simulated annealing.

    Args:
        dependency_graph (DG): dependency graph of the circuit.
        coupling_graph (Graph): adjacency graph of the hardware.
        start_mapping (list, optional): a partial mapping. Defaults to None.

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
    shortest_length_G = coupling_graph.shortest_length_weight

    if start_mapping is None:
        start_mapping = list(coupling_graph.nodes)
    if (
        len(start_mapping) != len(coupling_graph.nodes())
        or None in start_mapping
    ):
        # if logical qubits is less than physical, we extend logical qubit to
        # ensure the completeness and delete added qubits at the end of the
        # algorithm
        for v in coupling_graph.nodes():
            if v not in start_mapping:
                count = start_mapping.count(None)
                if count:
                    idx = start_mapping.index(None)
                    start_mapping[idx] = v
                    continue
                start_mapping.append(v)
    # initialize the weighted cost matrix
    cost_m, qubits_logic = init_cost_matrix(
        dependency_graph, coupling_graph, True
    )
    qubits_logic = tuple(qubits_logic)
    # Simulated Annealing
    solution_new = start_mapping
    solution_cur = solution_new.copy()
    value_cur = np.inf
    solution_best = solution_new.copy()
    value_best = np.inf
    alpha, t2, markovlen = init_para()
    # temperature
    t = t2[1]
    # Record the optimal solution during the iteration process
    result = []

    while t > t2[0]:
        for _ in np.arange(markovlen):
            # select two bits
            q_log1 = np.random.choice(qubits_logic)
            q_phy1 = solution_new[q_log1]
            q_phy2 = np.random.choice(list(coupling_graph.neighbors(q_phy1)))
            q_log2 = solution_new.index(q_phy2)
            # Exchange, recalculate costs
            solution_new[q_log1], solution_new[q_log2] = (
                solution_new[q_log2],
                solution_new[q_log1],
            )
            value_new = cal_cost_matrix(
                cost_m, solution_new, shortest_length_G, qubits_logic
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
                if np.random.rand() < np.exp(-(value_new - value_cur) / t):
                    value_cur = value_new
                    solution_cur = solution_new.copy()
                else:
                    solution_new = solution_cur.copy()

        t = alpha * t
        result.append(value_best)

    return solution_best[: dependency_graph.num_q]
