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

from qcos.transpiler.cmss.mapping.utils.dg import DG
from qcos.transpiler.cmss.mapping.initial_mapping.simulated_annealing import (
    init_cost_matrix,
    sa_initial_mapping,
)


class TestSAMapping:
    def test_sa_initial_mapping(self):
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (7, 8)]
        coupling_graph.add_edges_from(edges)
        dependency_graph = DG()
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        gate3 = ("cx", (2, 0), [])
        dependency_graph.add_multi_gates([gate1, gate2, gate3])
        assert dependency_graph.get_dg_num_q() == 3

        mapping = sa_initial_mapping(dependency_graph, coupling_graph)
        assert mapping is not None
        assert len(mapping) == 3

    def test_init_cost_matrix(self):
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2)]
        coupling_graph.add_edges_from(edges)
        dependency_graph = DG()
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        gate3 = ("cx", (2, 0), [])
        dependency_graph.add_multi_gates([gate1, gate2, gate3])
        assert dependency_graph.get_dg_num_q() == 3
        cost_matrix, qubits = init_cost_matrix(
            dependency_graph, coupling_graph, add_weight=True
        )
        assert qubits == {0, 1, 2}
        assert cost_matrix is not None
