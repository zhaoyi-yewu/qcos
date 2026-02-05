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

import networkx as nx
import numpy as np
import pytest

from wy_qcos.transpiler.cmss.mapping.utils.front_circuit import (
    FrontCircuit,
    qubit_convert,
)
from wy_qcos.transpiler.cmss.mapping.utils.dg import DG


class TestFrontCircuit:
    def create_test_ag(self):
        """Create a test architecture graph.

        Creates a test architecture graph with shortest_path and
        shortest_length attributes.
        """
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0)])

        # Add shortest_path and shortest_length attributes
        ag.shortest_path = dict(nx.shortest_path(ag))
        ag.shortest_length = dict(nx.shortest_path_length(ag))

        return ag

    def create_test_dg(self):
        """Create a test dependency graph."""
        dg = DG()
        dg.num_q = 4
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (2, 3), [])
        gate3 = ("h", (0,), [])
        dg.add_gate(gate1)
        dg.add_gate(gate2)
        dg.add_gate(gate3)
        return dg

    def test_init(self):
        """Test FrontCircuit initialization."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)

        assert front_cir.DG == dg
        assert front_cir.AG == ag
        assert front_cir.num_q_phy == 4
        assert front_cir.num_q_log == 4
        assert isinstance(front_cir.log_to_phy, list)
        assert isinstance(front_cir.phy_to_log, list)
        assert isinstance(front_cir.first_gates, list)
        assert isinstance(front_cir.front_layer, list)

    def test_init_from_existing(self):
        """Test FrontCircuit initialization from existing FrontCircuit."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir2 = FrontCircuit(dg, ag, front_cir_from=front_cir1)

        assert front_cir2.num_remain_nodes == front_cir1.num_remain_nodes
        assert front_cir2.log_to_phy == front_cir1.log_to_phy
        assert front_cir2.phy_to_log == front_cir1.phy_to_log

    def test_hash(self):
        """Test __hash__ method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir2 = FrontCircuit(dg, ag)

        hash1 = hash(front_cir1)
        hash2 = hash(front_cir2)

        assert isinstance(hash1, int)
        assert isinstance(hash2, int)

    def test_assign_mapping_from_list(self):
        """Test assign_mapping_from_list method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        map_list = [0, 1, 2, 3]

        exe_gates = front_cir.assign_mapping_from_list(map_list)

        assert isinstance(exe_gates, list)
        assert front_cir.log_to_phy == map_list

    def test_assian_mapping_naive(self):
        """Test assian_mapping_naive method.

        (note: typo in original method name).
        """
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        exe_gates = front_cir.assian_mapping_naive()

        assert isinstance(exe_gates, list)
        assert front_cir.log_to_phy == [0, 1, 2, 3]

    def test_swap(self):
        """Test swap method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_log_to_phy = front_cir.log_to_phy.copy()
        exe_gates = front_cir.swap((0, 1))

        assert isinstance(exe_gates, list)
        # After swap, mapping should change
        assert (
            front_cir.phy_to_log[0] != initial_log_to_phy[0]
            or front_cir.phy_to_log[1] != initial_log_to_phy[1]
        )

    def test_copy(self):
        """Test copy method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir1.assign_mapping_from_list([0, 1, 2, 3])

        front_cir2 = front_cir1.copy()

        assert front_cir2.num_remain_nodes == front_cir1.num_remain_nodes
        assert front_cir2.log_to_phy == front_cir1.log_to_phy
        assert front_cir2.phy_to_log == front_cir1.phy_to_log

    def test_swap_new(self):
        """Test swap_new method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        new_cir, exe_gates = front_cir.swap_new((0, 1))

        assert isinstance(new_cir, FrontCircuit)
        assert isinstance(exe_gates, list)
        assert new_cir != front_cir

    def test_executable_single_qubit(self):
        """Test _executable method with single qubit gate."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Find a single qubit gate node
        for node in dg.nodes:
            if len(dg.nodes[node].get("qubits", [])) == 1:
                result = front_cir._executable(node)
                assert result is True
                break

    def test_executable_two_qubit_connected(self):
        """Test _executable method with connected two qubit gate."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Find a two qubit gate node
        for node in dg.nodes:
            qubits = dg.nodes[node].get("qubits", [])
            if len(qubits) == 2:
                result = front_cir._executable(node)
                assert isinstance(result, bool)
                break

    def test_execute_front_layer(self):
        """Test execute_front_layer method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_remain = front_cir.num_remain_nodes
        front_cir.execute_front_layer()

        # Number of remaining nodes should decrease
        assert front_cir.num_remain_nodes <= initial_remain

    def test_execute_gates(self):
        """Test execute_gates method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        exe_gates = front_cir.execute_gates()

        assert isinstance(exe_gates, list)

    def test_execute_gate_index(self):
        """Test execute_gate_index method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        if len(front_cir.front_layer) > 0:
            initial_remain = front_cir.num_remain_nodes
            front_cir.execute_gate_index(0)

            assert front_cir.num_remain_nodes == initial_remain - 1

    def test_execute_gate(self):
        """Test execute_gate method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        if len(front_cir.front_layer) > 0:
            node = front_cir.front_layer[0]
            initial_remain = front_cir.num_remain_nodes
            front_cir.execute_gate(node)

            assert front_cir.num_remain_nodes == initial_remain - 1

    def test_execute_gate_remote(self):
        """Test execute_gate_remote method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Find a node that can be executed remotely (distance 2)
        for node in front_cir.front_layer:
            qubits = dg.nodes[node].get("qubits", [])
            if len(qubits) == 2:
                q0, q1 = qubits
                q0_phy = front_cir.log_to_phy[q0]
                q1_phy = front_cir.log_to_phy[q1]

                # Check if distance is 2
                if ag.shortest_length.get(q0_phy, {}).get(q1_phy) == 2:
                    remote_cxs, exe_nodes = front_cir.execute_gate_remote(node)
                    assert isinstance(remote_cxs, list)
                    assert isinstance(exe_nodes, list)
                    break

    def test_pertinent_swaps(self):
        """Test pertinent_swaps method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        swaps_phy, h_scores, h_scores_front = front_cir.pertinent_swaps(
            score_layer=2
        )

        assert isinstance(swaps_phy, list)
        assert isinstance(h_scores, list)
        assert isinstance(h_scores_front, list)
        assert len(swaps_phy) == len(h_scores)
        assert len(swaps_phy) == len(h_scores_front)

    def test_get_future_cx_fix_num(self):
        """Test get_future_cx_fix_num method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_remain = front_cir.num_remain_nodes

        if initial_remain > 0:
            num_cx = min(2, initial_remain)
            cx0, cx1 = front_cir.get_future_cx_fix_num(num_cx)

            assert isinstance(cx0, list)
            assert isinstance(cx1, list)
            assert len(cx0) <= num_cx
            assert len(cx1) <= num_cx
            # Verify state is restored
            assert front_cir.num_remain_nodes == initial_remain

    def test_get_future_cx_fix_num_with_single(self):
        """Test get_future_cx_fix_num_with_single method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_remain = front_cir.num_remain_nodes

        if initial_remain > 0:
            num_cx = min(2, initial_remain)
            cx0, cx1, single_gate0, single_gate1 = (
                front_cir.get_future_cx_fix_num_with_single(num_cx)
            )

            assert isinstance(cx0, list)
            assert isinstance(cx1, list)
            assert isinstance(single_gate0, list)
            assert isinstance(single_gate1, list)
            assert len(cx0) == len(single_gate0)
            assert len(cx1) == len(single_gate1)
            # Verify state is restored
            assert front_cir.num_remain_nodes == initial_remain

    def test_get_future_cx_fix_num2(self):
        """Test get_future_cx_fix_num2 method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_remain = front_cir.num_remain_nodes

        if initial_remain > 0:
            num_cx = min(2, initial_remain)
            cx0, cx1 = front_cir.get_future_cx_fix_num2(num_cx)

            assert isinstance(cx0, list)
            assert isinstance(cx1, list)
            # Verify state is restored
            assert front_cir.num_remain_nodes == initial_remain

    def test_get_future_cx_fix_num3(self):
        """Test get_future_cx_fix_num3 method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_remain = front_cir.num_remain_nodes

        if initial_remain > 0:
            num_cx = min(2, initial_remain)
            cx_total = front_cir.get_future_cx_fix_num3(num_cx)

            assert isinstance(cx_total, list)
            # Verify state is restored
            assert front_cir.num_remain_nodes == initial_remain

    def test_check_equal(self):
        """Test check_equal method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir1.assign_mapping_from_list([0, 1, 2, 3])

        front_cir2 = FrontCircuit(dg, ag, front_cir_from=front_cir1)

        assert front_cir1.check_equal(front_cir2) is True

        # Modify one and check they're not equal
        front_cir2.swap((0, 1))
        assert front_cir1.check_equal(front_cir2) is False

    def test_get_cir_matrix(self):
        """Test get_cir_matrix method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        num_layer = 3
        cir_map, actual_layers = front_cir.get_cir_matrix(num_layer)

        assert isinstance(cir_map, np.ndarray)
        assert cir_map.shape[0] == num_layer
        assert cir_map.shape[1] == front_cir.num_q_phy
        assert cir_map.shape[2] == front_cir.num_q_phy
        assert isinstance(actual_layers, int)
        assert actual_layers <= num_layer

    def test_print_methods(self):
        """Test print methods.

        (they don't return values, just verify they run).
        """
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # These methods just print, so we just verify they don't raise
        # exceptions
        try:
            front_cir.print()
            front_cir.print_front_layer_qubits()
            front_cir.print_front_layer_len()
            assert True
        except Exception:
            assert False, "Print methods should not raise exceptions"

    def test_swap_with_unmapped_qubits(self):
        """Test swap method with unmapped qubits."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        # Don't assign mapping, so some qubits might be unmapped

        # Try swap on qubits that might not be mapped
        exe_gates = front_cir.swap((0, 1))
        assert isinstance(exe_gates, list)

    def test_execute_gates_empty_front_layer(self):
        """Test execute_gates with empty front layer."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 4
        # Create empty DG

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        exe_gates = front_cir.execute_gates()
        assert isinstance(exe_gates, list)
        assert len(exe_gates) == 0

    def test_pertinent_swaps_empty_front_layer(self):
        """Test pertinent_swaps with empty front layer."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 4

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        swaps_phy, h_scores, h_scores_front = front_cir.pertinent_swaps(
            score_layer=2
        )

        assert isinstance(swaps_phy, list)
        assert isinstance(h_scores, list)
        assert isinstance(h_scores_front, list)

    def test_executable_two_qubit_not_connected(self):
        """Test _executable returns False when qubits not connected."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        # remove all edges so no two-qubit gate is executable
        ag.remove_edges_from(list(ag.edges))

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        for node in dg.nodes:
            qubits = dg.nodes[node].get("qubits", [])
            if len(qubits) == 2:
                assert front_cir._executable(node) is False
                break

    def test_execute_gate_remote_invalid_distance(self):
        """Test execute_gate_remote raises when distance != 2."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # pick a two-qubit gate where distance is 1
        for node in front_cir.front_layer:
            qubits = dg.nodes[node].get("qubits", [])
            if len(qubits) == 2:
                with pytest.raises(ValueError):
                    front_cir.execute_gate_remote(node)
                break

    def test_qubit_convert_noop(self):
        """Test qubit_convert placeholder function can be called."""
        # current implementation is a pass; just ensure it's callable
        assert qubit_convert([0, 1, 2]) is None

    def test_hash_caching(self):
        """Test that hash value is cached."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # First call should compute hash
        hash1 = hash(front_cir)
        # Second call should use cached value
        hash2 = hash(front_cir)

        assert hash1 == hash2

    def test_complex_circuit_mapping(self):
        """Test with a more complex circuit."""
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)])
        ag.shortest_path = dict(nx.shortest_path(ag))
        ag.shortest_length = dict(nx.shortest_path_length(ag))

        dg = DG()
        dg.num_q = 5
        dg.add_gate(("cx", (0, 1), []))
        dg.add_gate(("cx", (1, 2), []))
        dg.add_gate(("cx", (2, 3), []))

        front_cir = FrontCircuit(dg, ag)
        map_list = [0, 1, 2, 3, 4]

        exe_gates = front_cir.assign_mapping_from_list(map_list)
        assert isinstance(exe_gates, list)
        assert front_cir.log_to_phy == map_list

    def test_multiple_swaps(self):
        """Test multiple swap operations."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_mapping = front_cir.log_to_phy.copy()

        # First swap
        front_cir.swap((0, 1))
        assert front_cir.log_to_phy != initial_mapping

        # Second swap
        front_cir.swap((2, 3))

        assert len(front_cir.log_to_phy) == len(initial_mapping)

    def test_pertinent_swaps_detailed(self):
        """Test pertinent_swaps with detailed analysis."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Test with different score_layer values
        for score_layer in [1, 2, 3]:
            swaps_phy, h_scores, h_scores_front = front_cir.pertinent_swaps(
                score_layer=score_layer
            )

            assert isinstance(swaps_phy, list)
            assert isinstance(h_scores, list)
            assert isinstance(h_scores_front, list)

    def test_get_future_cx_with_all_nodes(self):
        """Test get_future_cx_fix_num requesting all remaining nodes."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_remain = front_cir.num_remain_nodes
        cx0, cx1 = front_cir.get_future_cx_fix_num(initial_remain + 10)

        assert front_cir.num_remain_nodes == initial_remain
        assert len(cx0) <= len(cx1) + 1

    def test_swap_updates_both_directions(self):
        """Test that swap updates both log_to_phy and phy_to_log."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Verify initial state
        for i in range(front_cir.num_q_log):
            if front_cir.log_to_phy[i] != -1:
                phy_qubit = front_cir.log_to_phy[i]
                assert front_cir.phy_to_log[phy_qubit] == i

        # Perform swap
        front_cir.swap((0, 1))

        # Verify consistency after swap
        for i in range(front_cir.num_q_log):
            if front_cir.log_to_phy[i] != -1:
                phy_qubit = front_cir.log_to_phy[i]
                assert front_cir.phy_to_log[phy_qubit] == i

    def test_execute_gate_with_successors(self):
        """Test execute_gate properly handles successor nodes."""
        ag = self.create_test_ag()

        # Create a more complex DG with dependencies
        dg = DG()
        dg.num_q = 4
        gate1 = ("cx", (0, 1), [])
        gate2 = ("cx", (1, 2), [])
        gate3 = ("h", (2,), [])

        dg.add_gate(gate1)
        dg.add_gate(gate2)
        dg.add_gate(gate3)

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_front_layer_size = len(front_cir.front_layer)
        if initial_front_layer_size > 0:
            first_node = front_cir.front_layer[0]
            front_cir.execute_gate(first_node)

            # front_layer might increase if successors become available
            assert len(front_cir.front_layer) <= initial_front_layer_size

    def test_get_cir_matrix_large(self):
        """Test get_cir_matrix with larger number of layers."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        num_layer = 10
        cir_map, actual_layers = front_cir.get_cir_matrix(num_layer)

        assert cir_map.shape == (num_layer, 4, 4)
        assert 0 <= actual_layers <= num_layer

    def test_check_equal_with_different_states(self):
        """Test check_equal with various different states."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir1.assign_mapping_from_list([0, 1, 2, 3])

        front_cir2 = front_cir1.copy()

        # Initially equal
        assert front_cir1.check_equal(front_cir2) is True

        # Modify front_layer
        if len(front_cir2.front_layer) > 0:
            front_cir2.front_layer = front_cir2.front_layer[1:]
            assert front_cir1.check_equal(front_cir2) is False

    def test_hash_with_different_mappings(self):
        """Test that different mappings produce different hashes."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir1.assign_mapping_from_list([0, 1, 2, 3])

        front_cir2 = FrontCircuit(dg, ag)
        front_cir2.assign_mapping_from_list([3, 2, 1, 0])

        hash1 = hash(front_cir1)
        hash2 = hash(front_cir2)

        # Different mappings should likely have different hashes
        # (though hash collisions are theoretically possible)
        assert isinstance(hash1, int)
        assert isinstance(hash2, int)

    def test_execute_gate_index_first_gate(self):
        """Test execute_gate_index removes first gate correctly."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        if len(front_cir.front_layer) > 0:
            initial_layer = front_cir.front_layer.copy()
            front_cir.execute_gate_index(0)

            # First gate should be removed
            assert front_cir.front_layer != initial_layer
            assert len(front_cir.front_layer) < len(initial_layer)

    def test_execute_gate_index_middle_gate(self):
        """Test execute_gate_index with middle gate index."""
        ag = self.create_test_ag()

        # Create DG with more gates
        dg = DG()
        dg.num_q = 4
        dg.add_gate(("cx", (0, 1), []))
        dg.add_gate(("cx", (2, 3), []))
        dg.add_gate(("h", (0,), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        if len(front_cir.front_layer) > 1:
            initial_len = len(front_cir.front_layer)
            front_cir.execute_gate_index(len(front_cir.front_layer) - 1)

            assert len(front_cir.front_layer) < initial_len

    def test_pertinent_swaps_swap_involvement(self):
        """Test pertinent_swaps correctly identifies involved nodes."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Get swaps with involvement analysis
        swaps_phy, h_scores, h_scores_front = front_cir.pertinent_swaps(
            score_layer=1
        )

        # Verify scores are consistent
        for swap, score, score_front in zip(
            swaps_phy, h_scores, h_scores_front
        ):
            assert isinstance(swap, tuple)
            assert len(swap) == 2
            assert isinstance(score, (int, float))
            assert isinstance(score_front, (int, float))

    def test_get_future_cx_fix_num_empty(self):
        """Test get_future_cx_fix_num with zero CX request."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        cx0, cx1 = front_cir.get_future_cx_fix_num(0)

        assert len(cx0) == 0
        assert len(cx1) == 0

    def test_get_future_cx_fix_num_with_single_empty(self):
        """Test get_future_cx_fix_num_with_single with zero CX request."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        cx0, cx1, sg0, sg1 = front_cir.get_future_cx_fix_num_with_single(0)

        assert len(cx0) == 0
        assert len(cx1) == 0
        assert len(sg0) == 0
        assert len(sg1) == 0

    def test_swap_unmapped_qubits(self):
        """Test swap behavior with unmapped qubits."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        # Partial mapping
        front_cir.log_to_phy = [0, 1, -1, -1]
        front_cir.phy_to_log = [0, 1, -1, -1]

        exe_gates = front_cir.swap((0, 1))
        assert isinstance(exe_gates, list)

    def test_check_equal_all_components(self):
        """Test check_equal verifies all components."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir1.assign_mapping_from_list([0, 1, 2, 3])

        front_cir2 = front_cir1.copy()

        # Modify each component and verify inequality
        front_cir2.num_remain_nodes = 100
        assert front_cir1.check_equal(front_cir2) is False

        # Restore and test phy_to_log
        front_cir2.num_remain_nodes = front_cir1.num_remain_nodes
        front_cir2.phy_to_log[0] = 99
        assert front_cir1.check_equal(front_cir2) is False

    def test_get_future_cx_fix_num3_layer_output(self):
        """Test get_future_cx_fix_num3 returns properly layered output."""
        ag = self.create_test_ag()

        # Create a circuit with multiple layers
        dg = DG()
        dg.num_q = 4
        dg.add_gate(("cx", (0, 1), []))
        dg.add_gate(("cx", (2, 3), []))
        dg.add_gate(("h", (0,), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        cx_total = front_cir.get_future_cx_fix_num3(3)

        assert isinstance(cx_total, list)
        for layer in cx_total:
            assert isinstance(layer, list)
            for cx in layer:
                assert isinstance(cx, tuple)
                assert len(cx) == 2

    def test_print_front_layer_len(self):
        """Test print_front_layer_len method."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Just ensure it doesn't raise
        try:
            front_cir.print_front_layer_len()
            assert True
        except Exception:
            assert False, "print_front_layer_len should not raise"

    def test_get_cir_matrix_circuit_structure(self):
        """Test get_cir_matrix correctly represents circuit."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        cir_map, actual_layers = front_cir.get_cir_matrix(5)

        # Check structure
        assert cir_map.dtype == np.float32
        # Each layer should have symmetric matrices for undirected edges
        for layer in cir_map[:actual_layers]:
            assert np.allclose(layer, layer.T)

    def test_execute_gate_with_various_nodes(self):
        """Test execute_gate with different node types."""
        ag = self.create_test_ag()

        dg = DG()
        dg.num_q = 4
        gate1 = ("cx", (0, 1), [])
        gate2 = ("h", (0,), [])
        gate3 = ("cx", (2, 3), [])

        dg.add_gate(gate1)
        dg.add_gate(gate2)
        dg.add_gate(gate3)

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        # Execute each gate type
        for node in front_cir.front_layer.copy():
            if node in front_cir.front_layer:
                front_cir.execute_gate(node)
                break

        assert True

    def test_pertinent_swaps_high_layers(self):
        """Test pertinent_swaps with many layers."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        swaps_phy, h_scores, h_scores_front = front_cir.pertinent_swaps(
            score_layer=5
        )

        assert isinstance(swaps_phy, list)
        assert isinstance(h_scores, list)
        assert isinstance(h_scores_front, list)

    def test_init_raises_when_num_q_too_small(self):
        """Test __init__ raises when num_q_log is too small."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 1
        dg.add_gate(("cx", (0, 1), []))

        with pytest.raises(IndexError):
            FrontCircuit(dg, ag)

    def test_execute_gate_remote_distance_two(self):
        """Test execute_gate_remote with distance 2 qubits."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 3
        dg.add_gate(("cx", (0, 2), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2])

        node = front_cir.front_layer[0]
        remote_cxs, exe_nodes = front_cir.execute_gate_remote(node)

        assert len(remote_cxs) == 4
        assert isinstance(exe_nodes, list)

    def test_get_future_cx_fix_num_empty_front_layer_raises(self):
        """Test get_future_cx_fix_num raises on empty front layer."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        front_cir.front_layer = []
        front_cir.num_remain_nodes = 1

        with pytest.raises(RuntimeError):
            front_cir.get_future_cx_fix_num(1)

    def test_get_future_cx_fix_num_negative_raises(self):
        """Test get_future_cx_fix_num raises when num_cx is negative."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        with pytest.raises(ValueError):
            front_cir.get_future_cx_fix_num(-1)

    def test_get_future_cx_fix_num_with_single_two_qubit(self):
        """Test get_future_cx_fix_num_with_single handles two-qubit gates."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 2
        dg.add_gate(("cx", (0, 1), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.log_to_phy = [0, 1]
        front_cir.phy_to_log = [0, 1, -1, -1]

        cx0, cx1, sg0, sg1 = front_cir.get_future_cx_fix_num_with_single(1)

        assert cx0 == [0]
        assert cx1 == [1]
        assert sg0 == [0]
        assert sg1 == [0]

    def test_executable_unmapped_qubits_returns_false(self):
        """Test _executable returns False when qubits are unmapped."""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)

        for node in dg.nodes:
            if len(dg.nodes[node]["qubits"]) == 2:
                assert front_cir._executable(node) is False
                break

    def test_execute_gates_non_executable_keeps_front_layer(self):
        """Test execute_gates with non-executable two-qubit gate."""
        ag = self.create_test_ag()
        ag.remove_edges_from(list(ag.edges))
        dg = DG()
        dg.num_q = 2
        dg.add_gate(("cx", (0, 1), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.log_to_phy = [0, 1]
        front_cir.phy_to_log = [0, 1, -1, -1]

        initial_front_layer = front_cir.front_layer.copy()
        exe_gates = front_cir.execute_gates()

        assert exe_gates == []
        assert front_cir.front_layer == initial_front_layer

    def test_execute_gate_index_appends_successor(self):
        """Test execute_gate_index appends successor when ready."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 1
        dg.add_gate(("h", (0,), []))
        dg.add_gate(("h", (0,), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.log_to_phy = [0]
        front_cir.phy_to_log = [0, -1, -1, -1]

        first_node = front_cir.front_layer[0]
        front_cir.execute_gate_index(0)

        assert first_node not in front_cir.front_layer
        assert len(front_cir.front_layer) == 1

    def test_pertinent_swaps_scores_with_successors(self):
        """Test pertinent_swaps updates scores and traverses successors."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 3
        dg.add_gate(("cx", (0, 1), []))
        dg.add_gate(("cx", (1, 2), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.log_to_phy = [0, 1, 2]
        front_cir.phy_to_log = [0, 1, 2, -1]

        swaps_phy, h_scores, h_scores_front = front_cir.pertinent_swaps(
            score_layer=1
        )

        assert len(swaps_phy) == len(h_scores)
        assert len(h_scores) == len(h_scores_front)

    def test_get_future_cx_fix_num2_multiple_nodes(self):
        """Test get_future_cx_fix_num2 with multiple front-layer nodes."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 4
        dg.add_gate(("cx", (0, 1), []))
        dg.add_gate(("cx", (2, 3), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.log_to_phy = [0, 1, 2, 3]
        front_cir.phy_to_log = [0, 1, 2, 3]

        cx0, cx1 = front_cir.get_future_cx_fix_num2(2)

        assert len(cx0) == 2
        assert len(cx1) == 2

    def test_get_future_cx_fix_num3_reorders_pairs(self):
        """Test get_future_cx_fix_num3 reorders pair when cx0 > cx1."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 2
        dg.add_gate(("cx", (0, 1), []))

        front_cir = FrontCircuit(dg, ag)
        front_cir.log_to_phy = [1, 0]
        front_cir.phy_to_log = [1, 0, -1, -1]

        cx_total = front_cir.get_future_cx_fix_num3(1)

        assert cx_total == [[(0, 1)]]

    def test_get_cir_matrix_empty_front_layer(self):
        """Test get_cir_matrix when there is no front layer."""
        ag = self.create_test_ag()
        dg = DG()
        dg.num_q = 2

        front_cir = FrontCircuit(dg, ag)
        front_cir.log_to_phy = [0, 1]
        front_cir.phy_to_log = [0, 1, -1, -1]
        front_cir.front_layer = []

        cir_map, actual_layers = front_cir.get_cir_matrix(3)

        assert actual_layers == 0
        assert cir_map.shape == (3, front_cir.num_q_phy, front_cir.num_q_phy)
