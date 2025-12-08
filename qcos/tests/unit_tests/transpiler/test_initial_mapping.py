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
from qcos.transpiler.cmss.mapping.initial_mapping.sc_initial_mapping import (
    get_initial_mapping,
)
from qcos.transpiler.cmss.mapping.initial_mapping.subgraph_isomorphism import (
    subgraph_isomorphism_mapping,
    topgraph_mapping,
)


class TestInitialMapping:
    qasm_str1 = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg c[2];
    cx q[0],q[1];
    measure q -> c;
    """

    qasm_str2 = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[4];
    creg c[4];
    x q[0];
    cx q[0],q[1];
    x q[1];
    cx q[1],q[3];
    x q[2];
    cx q[2],q[3];
    measure q -> c;
    """

    qasm_str3 = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg c[2];
    x q[0];
    x q[1];
    measure q -> c;
    """

    def test_get_init_mapping(self):
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        coupling_graph.add_edges_from(edges)

        # test qasm1
        dependency_graph = DG()
        dependency_graph.from_qasm_string(self.qasm_str1)

        mapping = get_initial_mapping(dependency_graph, coupling_graph)
        assert mapping == [0, 1]

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="subgraph_isomorphism"
        )
        assert mapping == [0, 1]

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="topgraph"
        )
        assert len(mapping) == 2

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="simulated_annealing"
        )
        assert len(mapping) == 2

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="sabre"
        )
        assert mapping == [0, 1]

        # test qasm2
        dependency_graph = DG()
        dependency_graph.from_qasm_string(self.qasm_str2)

        mapping = get_initial_mapping(dependency_graph, coupling_graph)
        assert mapping == [0, 1, 2, 3]

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="subgraph_isomorphism"
        )
        assert mapping is None

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="simulated_annealing"
        )
        assert len(mapping) == 4

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="topgraph"
        )
        assert len(mapping) == 4

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="sabre"
        )
        assert mapping == [1, 0, 2, 3]

        # test qasm3
        dependency_graph = DG()
        dependency_graph.from_qasm_string(self.qasm_str3)

        mapping = get_initial_mapping(
            dependency_graph, coupling_graph, method="topgraph"
        )
        assert len(mapping) == 2

    def test_subgraph_isomorphism_mapping(self):
        coupling_graph = Graph()
        edges = [(1, 2), (2, 3), (3, 4), (4, 1), (4, 5)]
        coupling_graph.add_edges_from(edges)
        dependency_graph = DG()
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        gate3 = ("cx", (2, 3), [])
        gate4 = ("cx", (3, 0), [])
        dependency_graph.add_gate(gate1)
        dependency_graph.add_gate(gate2)
        dependency_graph.add_gate(gate3)
        dependency_graph.add_gate(gate4)
        dependency_graph.num_q = 4
        # dg and ag is isomorphic
        mapping = subgraph_isomorphism_mapping(
            dependency_graph, coupling_graph
        )
        assert mapping == [1, 2, 3, 4]

        # dg and ag is isomorphic
        gate5 = ("cx", (1, 0), [])
        dependency_graph.add_gate(gate5)
        mapping = subgraph_isomorphism_mapping(
            dependency_graph, coupling_graph
        )
        assert mapping == [1, 2, 3, 4]

        # dg and ag is not isomorphic
        # 1->2, 2->3, cannot 1->3
        gate6 = ("cx", (1, 3), [])
        dependency_graph.add_gate(gate6)
        mapping = subgraph_isomorphism_mapping(
            dependency_graph, coupling_graph
        )
        assert mapping is None

    def test_topgraph_mapping(self):
        # liner topo
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (7, 8)]
        coupling_graph.add_edges_from(edges)

        dependency_graph = DG()
        # connected
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        # not connected
        gate3 = ("cx", (2, 0), [])
        gate4 = ("cx", (0, 3), [])
        dependency_graph.add_multi_gates([gate1, gate2, gate3])
        dependency_graph.num_q = 3
        mapping = topgraph_mapping(dependency_graph, coupling_graph)
        assert len(mapping) == 3

        dependency_graph.add_gate(gate4)
        dependency_graph.num_q = 4
        mapping = topgraph_mapping(dependency_graph, coupling_graph)
        assert len(mapping) == 4
