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

import networkx as nx
import pytest
from unittest.mock import Mock

from qcos.transpiler.common.errors import MappingException
from qcos.transpiler.cmss.mapping.routing.sc_routing import SCRouting


class TestSCRouting:
    """Test SCRouting class"""

    def test_init(self):
        """Test SCRouting initialization"""
        routing = SCRouting()
        assert routing.selec_times == 50

    def test_layout_list_to_dict(self):
        """Test _layout_list_to_dict method"""
        routing = SCRouting()
        layout_list = [0, 1, 2, 3]
        result = routing._layout_list_to_dict(layout_list)
        assert result == {0: 0, 1: 1, 2: 2, 3: 3}

    def test_layout_dict_reverse(self):
        """Test _layout_dict_reverse method"""
        routing = SCRouting()
        layout_dict = {0: 1, 1: 0, 2: 2}
        result = routing._layout_dict_reverse(layout_dict)
        assert result == {1: 0, 0: 1, 2: 2}

    def test_execute_routing_none_search_tree(self):
        """Test execute_routing with None search_tree"""
        routing = SCRouting()
        with pytest.raises(MappingException) as exc_info:
            routing.execute_routing(None, None, None, 0, [])
        assert "search_tree cannot be None" in str(exc_info.value)

    def test_execute_routing_none_ag(self):
        """Test execute_routing with None ag"""
        routing = SCRouting()
        mock_tree = Mock()
        with pytest.raises(MappingException) as exc_info:
            routing.execute_routing(mock_tree, None, None, 0, [])
        assert "ag cannot be None" in str(exc_info.value)

    def test_execute_routing_none_initial_layout(self):
        """Test execute_routing with None initial_layout"""
        routing = SCRouting()
        mock_tree = Mock()
        mock_ag = Mock()
        with pytest.raises(MappingException) as exc_info:
            routing.execute_routing(mock_tree, mock_ag, None, 0, [])
        assert "initial_layout cannot be None" in str(exc_info.value)

    def test_execute_routing_basic(self):
        """Test execute_routing basic functionality"""
        routing = SCRouting()
        routing.selec_times = 1  # Reduce iterations for testing

        # Create mock search_tree
        mock_tree = Mock()
        mock_tree.root_node = 0
        mock_tree.nodes = {
            0: {"num_remain_gates": 0}  # No remaining gates
        }
        mock_tree.selec_count = 0

        # Create mock AG
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2)])
        ag.nodes = [0, 1, 2]

        # Create mock DG
        mock_dg = Mock()
        mock_dg.to_ir.return_value = []
        mock_dg.num_q = 3

        mock_tree.to_dg.return_value = mock_dg
        mock_tree.get_swaps.return_value = []

        initial_layout = {0: 0, 1: 1}
        measure_ops = []

        result = routing.execute_routing(
            mock_tree, ag, initial_layout, 2, measure_ops
        )
        assert isinstance(result, list)

    def test_execute_routing_with_swaps(self):
        """Test execute_routing with swaps"""
        routing = SCRouting()
        routing.selec_times = 1

        # Create mock search_tree
        mock_tree = Mock()
        mock_tree.root_node = 0
        mock_tree.nodes = {0: {"num_remain_gates": 0}}
        mock_tree.selec_count = 0

        # Create mock AG
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2)])
        ag.nodes = [0, 1, 2]

        # Create mock DG
        mock_dg = Mock()
        mock_dg.to_ir.return_value = []
        mock_dg.num_q = 3

        mock_tree.to_dg.return_value = mock_dg
        mock_tree.get_swaps.return_value = [(0, 1), (1, 2)]

        initial_layout = {0: 0, 1: 1}
        measure_ops = []

        result = routing.execute_routing(
            mock_tree, ag, initial_layout, 2, measure_ops
        )
        assert isinstance(result, list)

    def test_execute_routing_with_measure_ops(self):
        """Test execute_routing with measure operations"""
        routing = SCRouting()
        routing.selec_times = 1

        # Create mock search_tree
        mock_tree = Mock()
        mock_tree.root_node = 0
        mock_tree.nodes = {0: {"num_remain_gates": 0}}
        mock_tree.selec_count = 0

        # Create mock AG
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2)])
        ag.nodes = [0, 1, 2]

        # Create mock DG
        mock_dg = Mock()
        mock_dg.to_ir.return_value = []
        mock_dg.num_q = 3

        mock_tree.to_dg.return_value = mock_dg
        mock_tree.get_swaps.return_value = []

        initial_layout = {0: 0, 1: 1}
        measure_op = Mock()
        measure_op.targets = [0, 1]
        measure_ops = [measure_op]

        result = routing.execute_routing(
            mock_tree, ag, initial_layout, 2, measure_ops
        )
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_execute_routing_swap_mapping_not_dict(self):
        """Test execute_routing when swap_mapping is not a dict"""
        routing = SCRouting()
        routing.selec_times = 1

        # Create mock search_tree
        mock_tree = Mock()
        mock_tree.root_node = 0
        mock_tree.nodes = {0: {"num_remain_gates": 0}}
        mock_tree.selec_count = 0

        # Create mock AG
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2)])
        ag.nodes = [0, 1, 2]

        # Create mock DG
        mock_dg = Mock()
        mock_dg.to_ir.return_value = []
        mock_dg.num_q = 3

        mock_tree.to_dg.return_value = mock_dg
        mock_tree.get_swaps.return_value = []

        # Mock _layout_dict_reverse to return non-dict
        routing._layout_dict_reverse = Mock(return_value="not_a_dict")

        initial_layout = {0: 0, 1: 1}
        measure_ops = []

        with pytest.raises(MappingException) as exc_info:
            routing.execute_routing(
                mock_tree, ag, initial_layout, 2, measure_ops
            )
        assert "swap_mapping should be a dict" in str(exc_info.value)

    def test_execute_routing_phy_q_not_in_swap_mapping(self):
        """Test execute_routing when phy_q not in swap_mapping"""
        routing = SCRouting()
        routing.selec_times = 1

        # Create mock search_tree
        mock_tree = Mock()
        mock_tree.root_node = 0
        mock_tree.nodes = {0: {"num_remain_gates": 0}}
        mock_tree.selec_count = 0

        # Create mock AG
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2)])
        ag.nodes = [0, 1, 2]

        # Create mock DG
        mock_dg = Mock()
        mock_dg.to_ir.return_value = []
        mock_dg.num_q = 3

        mock_tree.to_dg.return_value = mock_dg
        mock_tree.get_swaps.return_value = []

        initial_layout = {0: 10}  # phy_q=10 not in swap_mapping
        measure_ops = []

        result = routing.execute_routing(
            mock_tree, ag, initial_layout, 2, measure_ops
        )
        assert isinstance(result, list)

    def test_execute_routing_num_q_vir_filtering(self):
        """Test execute_routing filtering by num_q_vir"""
        routing = SCRouting()
        routing.selec_times = 1

        # Create mock search_tree
        mock_tree = Mock()
        mock_tree.root_node = 0
        mock_tree.nodes = {0: {"num_remain_gates": 0}}
        mock_tree.selec_count = 0

        # Create mock AG
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2)])
        ag.nodes = [0, 1, 2]

        # Create mock DG
        mock_dg = Mock()
        mock_dg.to_ir.return_value = []
        mock_dg.num_q = 3

        mock_tree.to_dg.return_value = mock_dg
        mock_tree.get_swaps.return_value = []

        initial_layout = {0: 0, 1: 1, 5: 5}  # q=5 >= num_q_vir=2
        measure_ops = []

        result = routing.execute_routing(
            mock_tree, ag, initial_layout, 2, measure_ops
        )
        assert isinstance(result, list)
        assert 5 not in initial_layout
