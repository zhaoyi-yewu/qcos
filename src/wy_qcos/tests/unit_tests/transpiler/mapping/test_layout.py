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

import pytest

from wy_qcos.common.cmss.gate_operation import CX, H
from wy_qcos.transpiler.cmss.mapping.init_mapping import (
    dense_layout,
)
from wy_qcos.transpiler.cmss.mapping.init_mapping.subgraph_isomorphism import (
    vf2_layout_mapping,
)


def _are_adjacent(
    phys_a: int,
    phys_b: int,
    coupling_list: list[tuple[int, int]],
) -> bool:
    """Check if two physical qubits are adjacent in the coupling graph."""
    for u, v in coupling_list:
        if (u == phys_a and v == phys_b) or (u == phys_b and v == phys_a):
            return True
    return False


def _has_duplicate(mapping: list[int]) -> bool:
    """Check if the mapping has duplicate physical qubit IDs."""
    return len(set(mapping)) != len(mapping)


def _all_gates_adjacent(
    gates: list,
    mapping: list[int],
    coupling_list: list[tuple[int, int]],
) -> bool:
    """Verify all two-qubit gates have adjacent physical endpoints."""
    for gate in gates:
        if gate.name != "cx":
            continue
        p0 = mapping[gate.targets[0]]
        p1 = mapping[gate.targets[1]]
        if not _are_adjacent(p0, p1, coupling_list):
            return False
    return True


class TestDenseLayout:
    """Tests for dense_layout_mapping."""

    def test_basic_connectivity(self):
        coupling = [
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (2, 3),
            (3, 2),
            (3, 0),
            (0, 3),
        ]
        gates = [CX([0, 1])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 2)
        assert len(mapping) == 2
        assert not _has_duplicate(mapping)
        for phys in mapping:
            assert 0 <= phys <= 3
        assert _are_adjacent(mapping[0], mapping[1], coupling)

    def test_dense_subgraph_selection(self):
        coupling = [
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (2, 3),
            (3, 2),
            (3, 4),
            (4, 3),
            (1, 3),
            (3, 1),
        ]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 3)
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)
        phys_set = set(mapping)
        assert 1 in phys_set
        assert 2 in phys_set
        assert 3 in phys_set

    def test_duplicate_edges(self):
        coupling = [
            (0, 1),
            (1, 0),
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (1, 2),
            (2, 1),
        ]
        gates = [CX([0, 1])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 2)
        assert len(mapping) == 2
        assert not _has_duplicate(mapping)
        assert _are_adjacent(mapping[0], mapping[1], coupling)

    def test_unidirectional_coupling(self):
        coupling = [(0, 1), (1, 2), (2, 3)]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 3)
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)
        assert len(set(mapping)) == 3

    def test_sparse_physical_ids(self):
        coupling = [(10, 20), (20, 10), (20, 30), (30, 20)]
        gates = [CX([0, 1])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 2)
        assert len(mapping) == 2
        assert not _has_duplicate(mapping)
        for phys in mapping:
            assert phys in (10, 20, 30)
        assert _are_adjacent(mapping[0], mapping[1], coupling)

    def test_all_physical_qubits_used(self):
        coupling = [(0, 1), (1, 0), (1, 2), (2, 1)]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 3)
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)
        phys_set = set(mapping)
        assert phys_set == {0, 1, 2}

    def test_edge_fidelity_influence(self):
        coupling = [
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (2, 3),
            (3, 2),
        ]
        fids = [0.99, 0.99, 0.80, 0.80, 0.99, 0.99]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping_no_fid = dense_layout.dense_layout_mapping(
            gates, coupling, [], [], 3
        )
        mapping_with_fid = dense_layout.dense_layout_mapping(
            gates, coupling, fids, [], 3
        )
        assert len(mapping_no_fid) == 3
        assert len(mapping_with_fid) == 3
        assert not _has_duplicate(mapping_no_fid)
        assert not _has_duplicate(mapping_with_fid)

    def test_single_logical_qubit(self):
        coupling = [(0, 1), (1, 0), (1, 2), (2, 1)]
        gates = [H([0])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 1)
        assert len(mapping) == 1
        assert 0 <= mapping[0] <= 2

    def test_empty_gates(self):
        coupling = [(0, 1), (1, 0), (1, 2), (2, 1)]
        mapping = dense_layout.dense_layout_mapping([], coupling, [], [], 0)
        assert mapping == []

    def test_too_many_logical_qubits(self):
        coupling = [(0, 1), (1, 0), (1, 2), (2, 1)]
        gates = [CX([0, 1]), CX([2, 3])]
        with pytest.raises(ValueError):
            dense_layout.dense_layout_mapping(gates, coupling, [], [], 4)

    def test_empty_coupling_list(self):
        gates = [H([0])]
        with pytest.raises(ValueError):
            dense_layout.dense_layout_mapping(gates, [], [], [], 1)

    def test_disconnected_graph(self):
        coupling = [(0, 1), (1, 0), (3, 4), (4, 3)]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = dense_layout.dense_layout_mapping(gates, coupling, [], [], 3)
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)

    def test_fidelity_weight_default(self):
        coupling = [
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (2, 3),
            (3, 2),
        ]
        fids = [0.95, 0.95, 0.90, 0.90, 0.95, 0.95]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = dense_layout.dense_layout_mapping(
            gates, coupling, fids, [], 3, 0.5
        )
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)

    def test_fidelity_weight_extremes(self):
        coupling = [
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (2, 3),
            (3, 2),
        ]
        fids = [0.99, 0.99, 0.70, 0.70, 0.99, 0.99]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping_density = dense_layout.dense_layout_mapping(
            gates, coupling, fids, [], 3, 0.0
        )
        assert len(mapping_density) == 3
        assert not _has_duplicate(mapping_density)
        mapping_fidelity = dense_layout.dense_layout_mapping(
            gates, coupling, fids, [], 3, 1.0
        )
        assert len(mapping_fidelity) == 3
        assert not _has_duplicate(mapping_fidelity)

    def test_density_normalization(self):
        coupling = [
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (2, 3),
            (3, 2),
            (3, 4),
            (4, 3),
            (4, 5),
            (5, 4),
        ]
        fids = [0.95] * 10
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = dense_layout.dense_layout_mapping(
            gates, coupling, fids, [], 3, 0.5
        )
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)


class TestVF2Layout:
    """Tests for vf2_layout_mapping."""

    def test_chain_perfect_embedding(self):
        coupling = [(0, 1), (1, 2), (2, 3), (3, 4)]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 3)
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)
        assert _all_gates_adjacent(gates, mapping, coupling)

    def test_star_perfect_embedding(self):
        coupling = [
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (1, 2),
        ]
        gates = [CX([0, 1]), CX([0, 2]), CX([0, 3])]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 4)
        assert len(mapping) == 4
        assert not _has_duplicate(mapping)
        assert _all_gates_adjacent(gates, mapping, coupling)
        assert mapping[0] == 0

    def test_no_solution_triangle_on_line(self):
        coupling = [(0, 1), (1, 2), (2, 3)]
        gates = [CX([0, 1]), CX([1, 2]), CX([0, 2])]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 3)
        assert mapping == []

    def test_no_two_qubit_gates(self):
        coupling = [(0, 1)]
        gates = [H([0]), H([1])]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 2)
        assert mapping == []

    def test_fidelity_scoring(self):
        coupling = [(0, 1), (1, 2), (3, 4), (4, 5)]
        fids = [0.9, 0.9, 0.99, 0.99]
        gates = [CX([0, 1]), CX([1, 2])]
        mapping = vf2_layout_mapping(gates, coupling, fids, [], 3)
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)
        assert _all_gates_adjacent(gates, mapping, coupling)
        phys_set = set(mapping)
        assert 3 in phys_set
        assert 4 in phys_set
        assert 5 in phys_set

    def test_multiple_gates_same_pair(self):
        coupling = [(0, 1), (1, 2), (2, 3)]
        gates = [CX([0, 1]), CX([0, 1]), CX([1, 2])]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 3)
        assert len(mapping) == 3
        assert not _has_duplicate(mapping)
        assert _all_gates_adjacent(gates, mapping, coupling)

    def test_isolated_logical_qubit(self):
        coupling = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),
        ]
        gates = [CX([0, 1]), CX([1, 2]), H([3])]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 4)
        assert len(mapping) == 4
        assert not _has_duplicate(mapping)
        assert _all_gates_adjacent(gates, mapping, coupling)
        for phys in mapping:
            assert 0 <= phys <= 4

    def test_long_chain_circuit(self):
        coupling = [(i, i + 1) for i in range(19)]
        gates = [CX([i, i + 1]) for i in range(9)]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 10)
        assert len(mapping) == 10
        assert not _has_duplicate(mapping)
        assert _all_gates_adjacent(gates, mapping, coupling)

    def test_ring_circuit_on_ring_topology(self):
        coupling = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (3, 4),
            (4, 5),
        ]
        gates = [
            CX([0, 1]),
            CX([1, 2]),
            CX([2, 3]),
            CX([3, 0]),
        ]
        mapping = vf2_layout_mapping(gates, coupling, [], [], 4)
        assert len(mapping) == 4
        assert not _has_duplicate(mapping)
        assert _all_gates_adjacent(gates, mapping, coupling)

    def test_empty_coupling_list(self):
        gates = [CX([0, 1])]
        with pytest.raises(ValueError):
            vf2_layout_mapping(gates, [], [], [], 2)

    def test_logical_exceeds_physical(self):
        coupling = [(0, 1)]
        gates = [CX([0, 1]), CX([1, 2])]
        with pytest.raises(ValueError):
            vf2_layout_mapping(gates, coupling, [], [], 3)
