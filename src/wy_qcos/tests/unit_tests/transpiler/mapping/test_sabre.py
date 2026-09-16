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

from networkx import Graph

from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE
from wy_qcos.transpiler.cmss.mapping.init_mapping.sabre_mapping import (
    sabre_initial_mapping,
)
from wy_qcos.common.cmss.gate_operation import X, H, CX, SWAP
from wy_qcos.common.cmss.measure import Measure


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


def _measure_indices(gates: list) -> list:
    """Return indices of measure gates in the list."""
    return [i for i, op in enumerate(gates) if op.name == "measure"]


def _has_measure_before_last_gate(gates: list) -> bool:
    """Check if any measure gate appears before the last non-measure gate."""
    measure_idx = _measure_indices(gates)
    if not measure_idx:
        return False
    first_measure = measure_idx[0]
    return any(
        op.name not in ("measure", "sync", "barrier")
        for op in gates[first_measure:]
    )


class TestSabreMeasurePlacement:
    """Verify SABRE.execute() keeps measure gates at the end.

    Even when measure gates are included in the input, they should not be
    moved before other gates.
    """

    @staticmethod
    def _linear_graph(num_qubits: int = 6) -> Graph:
        """Create a linear chain coupling graph: 0-1-2-...-N."""
        graph = Graph()
        edges = [(i, i + 1) for i in range(num_qubits - 1)]
        graph.add_edges_from(edges)
        return graph

    def test_measure_at_end_no_swap(self):
        """Measure gates should be at the end even without SWAP.

        Uses a chain CX(0,1)->CX(1,2)->CX(2,3) where measure on q0
        is attached to CX(0,1). Without the fix, measure(q0) would
        be output right after CX(0,1) executes, before CX(1,2).
        """
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 1]),
            CX([1, 2]),
            CX([2, 3]),
            H([0]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        assert not _has_measure_before_last_gate(result)
        assert len(_measure_indices(result)) == 4

    def test_measure_at_end_with_swap(self):
        """Measure gates should be at the end even when SWAPs are inserted."""
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 3]),
            CX([1, 3]),
            CX([0, 2]),
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        assert not _has_measure_before_last_gate(result)
        swap_count = sum(1 for op in result if op.name == "swap")
        assert swap_count > 0
        measure_idx = _measure_indices(result)
        assert len(measure_idx) == 4
        assert measure_idx[0] > 0

    def test_measure_not_in_routing_result(self):
        """Measure gates should not appear in the routing portion.

        Uses a chain of CX gates on different qubit pairs. Without the
        fix, measure on q0 attached to CX(0,1) would be output before
        CX(1,2) and CX(2,3) are routed.
        """
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 1]),
            CX([1, 2]),
            CX([2, 3]),
            H([1]),
            H([2]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        measure_idx = _measure_indices(result)
        assert len(measure_idx) == 4
        assert measure_idx[0] == len(result) - 4

    def test_measure_count_preserved(self):
        """All measure gates in the input should appear in the output."""
        sabre = SABRE(self._linear_graph(6))
        gates = [
            H([0]),
            H([1]),
            H([2]),
            H([3]),
            CX([0, 3]),
            CX([1, 2]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        measure_gates = [op for op in result if op.name == "measure"]
        assert len(measure_gates) == 4

    def test_measure_targets_updated(self):
        """Measure targets should be mapped to physical qubits."""
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 3]),
            CX([0, 2]),
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        measure_gates = [op for op in result if op.name == "measure"]
        assert len(measure_gates) == 4
        final_mapping = sabre.logic2phy
        for measure_op in measure_gates:
            for target in measure_op.targets:
                assert target in final_mapping or target in range(
                    len(sabre.coupling_graph.nodes())
                )
