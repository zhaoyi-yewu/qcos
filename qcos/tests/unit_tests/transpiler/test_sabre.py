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

from qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE
from qcos.transpiler.cmss.mapping.initial_mapping.sabre_mapping import (
    sabre_initial_mapping,
)
from qcos.transpiler.cmss.common.gate_operation import X, H, CX, SWAP


class TestSabre:
    def test_sabre_routing(self):
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        coupling_graph.add_edges_from(edges)
        sabre = SABRE(coupling_graph)

        gate1 = X([0])
        gate2 = CX([0, 1])
        gate3 = H([1])
        gates_list = [gate1, gate2, gate3]
        sabre.execute(gates_list)
        assert sabre.logic2phy == [0, 1, 2, 3]
        assert len(sabre.phy_exe_gates) == len(gates_list)

        gate1 = CX([0, 1])
        gate2 = CX([2, 3])
        gate3 = CX([1, 2])
        gate4 = CX([0, 2])
        gates_list = [gate1, gate2, gate3, gate4]
        sabre.execute(gates_list)
        # mapping is modified
        assert sabre.logic2phy == [1, 0, 2, 3]
        # inserted one swap gate
        assert len(sabre.phy_exe_gates) == len(gates_list) + 1
        # between gate3 and gate4
        assert isinstance(sabre.phy_exe_gates[3], SWAP)

        gate1 = CX([0, 3])
        gate2 = CX([1, 3])
        gate3 = CX([0, 2])
        gate4 = CX([0, 1])
        gates_list = [gate1, gate2, gate3, gate4]
        sabre.execute(gates_list)
        assert sabre.logic2phy == [1, 0, 2, 3]
        assert len(sabre.phy_exe_gates) == len(gates_list) + 1
        assert isinstance(sabre.phy_exe_gates[1], SWAP)

    def test_sabre_mapping(self):
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3)]
        coupling_graph.add_edges_from(edges)
        sabre = SABRE(coupling_graph)

        gate1 = CX([0, 1])
        gate2 = CX([2, 3])
        gate3 = CX([1, 2])
        gate4 = CX([0, 2])
        gates_list = [gate1, gate2, gate3, gate4]
        mapping = sabre_initial_mapping(gates_list, coupling_graph)
        # insert one swap, between gate1 and gate2
        assert mapping == [0, 1, 2, 3]

        gate1 = CX([0, 3])
        gate2 = CX([1, 3])
        gate3 = CX([0, 2])
        gate4 = CX([0, 1])
        gates_list = [gate1, gate2, gate3, gate4]
        mapping = sabre_initial_mapping(gates_list, coupling_graph)
        sabre.execute(gates_list, initial_l2p=mapping)
        # insert one swap, between gate3 and gate4
        assert mapping == [2, 0, 3, 1]
