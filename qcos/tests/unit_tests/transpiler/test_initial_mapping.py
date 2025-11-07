#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.transpiler.cmss.mapping.dg import DG
from qcos.transpiler.cmss.mapping.initial_mapping import get_initial_mapping
from qcos.transpiler.cmss.mapping.subgraph_mapping import (
    subgraph_isomorphism_mapping,
    topgraph_mapping,
)


class TestInitialMapping:
    def test_get_init_mapping(self):
        adjacency_graph = Graph()
        dependency_graph = DG()
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        adjacency_graph.add_edges_from(edges)
        # naive method
        mapping = get_initial_mapping(dependency_graph, adjacency_graph)
        assert mapping == [0, 1, 2, 3]

        # subgraph_isomorphism method
        gate1 = ("cx", (0, 1), [])
        dependency_graph.add_gate(gate1)
        mapping = get_initial_mapping(
            dependency_graph, adjacency_graph, method="subgraph_isomorphism"
        )
        assert mapping == [0, 1]

    def test_subgraph_isomorphism_mapping(self):
        adjacency_graph = Graph()
        edges = [(1, 2), (2, 3), (3, 4), (4, 1), (4, 5)]
        adjacency_graph.add_edges_from(edges)
        dependency_graph = DG()
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        gate3 = ("cx", (2, 3), [])
        gate4 = ("cx", (3, 0), [])
        dependency_graph.add_gate(gate1)
        dependency_graph.add_gate(gate2)
        dependency_graph.add_gate(gate3)
        dependency_graph.add_gate(gate4)
        # dg and ag is isomorphic
        mapping = subgraph_isomorphism_mapping(
            dependency_graph, adjacency_graph
        )
        assert mapping == [1, 2, 3, 4]

        # dg and ag is isomorphic
        gate5 = ("cx", (1, 0), [])
        dependency_graph.add_gate(gate5)
        mapping = subgraph_isomorphism_mapping(
            dependency_graph, adjacency_graph
        )
        assert mapping == [1, 2, 3, 4]

        # dg and ag is not isomorphic
        # 1->2, 2->3, cannot 1->3
        gate6 = ("cx", (1, 3), [])
        dependency_graph.add_gate(gate6)
        mapping = subgraph_isomorphism_mapping(
            dependency_graph, adjacency_graph
        )
        assert mapping is None

    def test_topgraph_mapping(self):
        # liner topo
        adjacency_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (7, 8)]
        adjacency_graph.add_edges_from(edges)

        dependency_graph = DG()
        # connected
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        # not connected
        gate3 = ("cx", (2, 0), [])
        gate4 = ("cx", (0, 3), [])
        dependency_graph.add_multi_gates([gate1, gate2, gate3])
        num, mapping = topgraph_mapping(dependency_graph, adjacency_graph)
        assert num == 2
        assert mapping == [0, 1, 2]

        dependency_graph.add_gate(gate4)
        num, mapping = topgraph_mapping(dependency_graph, adjacency_graph)
        assert num == 2
        assert mapping == [0, 1, 2, 3]
