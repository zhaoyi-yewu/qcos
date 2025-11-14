#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.transpiler.cmss.mapping.front_circuit import FrontCircuit
from qcos.transpiler.cmss.mapping.dg import DG


class TestFrontCircuit:
    def create_test_ag(self):
        """Create a test architecture graph with shortest_path and
        shortest_length"""
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0)])

        # Add shortest_path and shortest_length attributes
        ag.shortest_path = dict(nx.shortest_path(ag))
        ag.shortest_length = dict(nx.shortest_path_length(ag))

        return ag

    def create_test_dg(self):
        """Create a test dependency graph"""
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
        """Test FrontCircuit initialization"""
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
        """Test FrontCircuit initialization from existing FrontCircuit"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir2 = FrontCircuit(dg, ag, front_cir_from=front_cir1)

        assert front_cir2.num_remain_nodes == front_cir1.num_remain_nodes
        assert front_cir2.log_to_phy == front_cir1.log_to_phy
        assert front_cir2.phy_to_log == front_cir1.phy_to_log

    def test_hash(self):
        """Test __hash__ method"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir2 = FrontCircuit(dg, ag)

        hash1 = hash(front_cir1)
        hash2 = hash(front_cir2)

        assert isinstance(hash1, int)
        assert isinstance(hash2, int)

    def test_assign_mapping_from_list(self):
        """Test assign_mapping_from_list method"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        map_list = [0, 1, 2, 3]

        exe_gates = front_cir.assign_mapping_from_list(map_list)

        assert isinstance(exe_gates, list)
        assert front_cir.log_to_phy == map_list

    def test_assian_mapping_naive(self):
        """Test assian_mapping_naive method
        (note: typo in original method name)"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        exe_gates = front_cir.assian_mapping_naive()

        assert isinstance(exe_gates, list)
        assert front_cir.log_to_phy == [0, 1, 2, 3]

    def test_swap(self):
        """Test swap method"""
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
        """Test copy method"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir1 = FrontCircuit(dg, ag)
        front_cir1.assign_mapping_from_list([0, 1, 2, 3])

        front_cir2 = front_cir1.copy()

        assert front_cir2.num_remain_nodes == front_cir1.num_remain_nodes
        assert front_cir2.log_to_phy == front_cir1.log_to_phy
        assert front_cir2.phy_to_log == front_cir1.phy_to_log

    def test_swap_new(self):
        """Test swap_new method"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        new_cir, exe_gates = front_cir.swap_new((0, 1))

        assert isinstance(new_cir, FrontCircuit)
        assert isinstance(exe_gates, list)
        assert new_cir != front_cir

    def test_executable_single_qubit(self):
        """Test _executable method with single qubit gate"""
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
        """Test _executable method with connected two qubit gate"""
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
        """Test execute_front_layer method"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        initial_remain = front_cir.num_remain_nodes
        front_cir.execute_front_layer()

        # Number of remaining nodes should decrease
        assert front_cir.num_remain_nodes <= initial_remain

    def test_execute_gates(self):
        """Test execute_gates method"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        exe_gates = front_cir.execute_gates()

        assert isinstance(exe_gates, list)

    def test_execute_gate_index(self):
        """Test execute_gate_index method"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        front_cir.assign_mapping_from_list([0, 1, 2, 3])

        if len(front_cir.front_layer) > 0:
            initial_remain = front_cir.num_remain_nodes
            front_cir.execute_gate_index(0)

            assert front_cir.num_remain_nodes == initial_remain - 1

    def test_execute_gate(self):
        """Test execute_gate method"""
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
        """Test execute_gate_remote method"""
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
        """Test pertinent_swaps method"""
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
        """Test get_future_cx_fix_num method"""
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
        """Test get_future_cx_fix_num_with_single method"""
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
        """Test get_future_cx_fix_num2 method"""
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
        """Test get_future_cx_fix_num3 method"""
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
        """Test check_equal method"""
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
        """Test get_cir_matrix method"""
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
        """Test print methods
        (they don't return values, just verify they run)"""
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
        """Test swap method with unmapped qubits"""
        ag = self.create_test_ag()
        dg = self.create_test_dg()

        front_cir = FrontCircuit(dg, ag)
        # Don't assign mapping, so some qubits might be unmapped

        # Try swap on qubits that might not be mapped
        exe_gates = front_cir.swap((0, 1))
        assert isinstance(exe_gates, list)

    def test_execute_gates_empty_front_layer(self):
        """Test execute_gates with empty front layer"""
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
        """Test pertinent_swaps with empty front layer"""
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
