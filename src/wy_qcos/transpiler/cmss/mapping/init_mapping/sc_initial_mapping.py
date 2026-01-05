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

from networkx import Graph

from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.transpiler.cmss.mapping.init_mapping.subgraph_isomorphism import (
    subgraph_isomorphism_mapping,
    topgraph_mapping,
)
from wy_qcos.transpiler.cmss.mapping.init_mapping.simulated_annealing import (
    sa_initial_mapping,
)
from wy_qcos.transpiler.cmss.mapping.init_mapping.sabre_mapping import (
    sabre_initial_mapping,
)


def get_initial_mapping(
    dependency_graph: DG, coupling_graph: Graph, method="naive"
):
    """Get the initial mapping, providing 4 methods.

    - naive: directly mapping logical qubits to physical qubits in order.
    - simulated_annealing: heuristic mapping, based on simulated annealing,
      ref: "Quantum Circuit Transformation Based on Simulated Annealing
      and Heuristic Search."
    - subgraph_isomorphism: Based on subgraph isomorphism, achieves precise
      allocation of qubits (this method may not always yield a solution).
    - topgraph: Combines the above two methods. For the top part of the
      circuit topology graph, subgraph isomorphism is used. ref "Qubit
      Mapping Based on Subgraph Isomorphism and Filtered Depth-Limited
      Search.".

    Args:
        dependency_graph (DG): dependency graph of the circuit
        coupling_graph (Graph): adjacency graph of the quantum machine
        method (str, optional): mapping method. Defaults to 'naive'.

    Returns:
        list[int]: represents a mapping in which indices and values stand for
            logical and physical qubits.
    """
    # if there is zero 2-qubit gate, no need to mapping
    if dependency_graph.num_gate_2q == 0:
        method = "naive"

    if method == "naive":
        return list(range(dependency_graph.get_dg_num_q()))
    elif method == "simulated_annealing":
        return sa_initial_mapping(dependency_graph, coupling_graph)
    elif method == "subgraph_isomorphism":
        return subgraph_isomorphism_mapping(dependency_graph, coupling_graph)
    elif method == "topgraph":
        return topgraph_mapping(dependency_graph, coupling_graph)
    elif method == "sabre":
        ir = dependency_graph.origin_ir
        num_qubits = dependency_graph.num_q
        mapping = sabre_initial_mapping(ir, coupling_graph)
        return mapping[:num_qubits]
    else:
        raise ValueError(f"Unsupported method {method} for initial mapping")
