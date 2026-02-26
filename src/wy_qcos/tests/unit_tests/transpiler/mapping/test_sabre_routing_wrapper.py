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
import pytest
from unittest.mock import Mock, patch

from wy_qcos.transpiler.common.errors import MappingException
from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing_wrapper import (
    SABRERouting,
)


class TestSABRERoutingWrapper:
    def test_layout_list_to_dict(self):
        routing = SABRERouting()
        assert routing._layout_list_to_dict([2, 1, 0]) == {0: 2, 1: 1, 2: 0}

    def test_layout_dict_to_list_invalid_type(self):
        routing = SABRERouting()
        with pytest.raises(MappingException):
            routing._layout_dict_to_list([0, 1])

    def test_layout_dict_to_list_no_int_key(self):
        routing = SABRERouting()
        with pytest.raises(MappingException):
            routing._layout_dict_to_list({"a": 0})

    def test_layout_dict_to_list_basic(self):
        routing = SABRERouting()
        assert routing._layout_dict_to_list({0: 1, 1: 0}) == [1, 0]

    def test_dg_to_gates_list(self):
        routing = SABRERouting()
        mock_dg = Mock()
        mock_dg.to_ir.return_value = ["g1", "g2"]
        assert routing._dg_to_gates_list(mock_dg) == ["g1", "g2"]
        mock_dg.to_ir.assert_called_once_with(decompose_swap=False)

    def test_execute_routing_requires_ag(self):
        routing = SABRERouting()
        with pytest.raises(MappingException):
            routing.execute_routing(None, None, {0: 0}, 1, [])

    def test_execute_routing_requires_initial_layout(self):
        routing = SABRERouting()
        ag = nx.Graph()
        ag.add_edge(0, 1)
        with pytest.raises(MappingException):
            routing.execute_routing(None, ag, None, 1, [])

    def test_execute_routing_requires_dg(self):
        routing = SABRERouting()
        ag = nx.Graph()
        ag.add_edge(0, 1)
        with pytest.raises(MappingException):
            routing.execute_routing(None, ag, {0: 0}, 1, [])

    @patch(
        "wy_qcos.transpiler.cmss.mapping.routing.sabre_routing_wrapper.SABRE"
    )
    def test_execute_routing_updates_measure_ops(self, mock_sabre):
        routing = SABRERouting()
        ag = nx.Graph()
        ag.add_edges_from([(0, 1), (1, 2)])
        dg = Mock()
        dg.to_ir.return_value = ["g1", "g2"]

        measure_op = Mock()
        measure_op.targets = [0, 1]

        sabre_instance = Mock()
        sabre_instance.phy_exe_gates = ["mapped"]
        sabre_instance.logic2phy = [2, 1, 0]
        mock_sabre.return_value = sabre_instance

        mapped_ir, mapping = routing.execute_routing(
            search_tree=None,
            ag=ag,
            initial_layout={0: 0, 1: 1, 2: 2},
            num_q_vir=2,
            measure_ops=[measure_op],
            dg=dg,
        )

        sabre_instance.execute.assert_called_once()
        assert mapped_ir[-1] is measure_op
        assert measure_op.targets == [2, 1]
        assert mapping == {0: 2, 1: 1}

    @patch(
        "wy_qcos.transpiler.cmss.mapping.routing.sabre_routing_wrapper.SABRE"
    )
    def test_execute_routing_truncate_initial_layout(self, mock_sabre):
        routing = SABRERouting()
        ag = nx.Graph()
        ag.add_edge(0, 1)

        dg = Mock()
        dg.to_ir.return_value = []

        sabre_instance = Mock()
        sabre_instance.phy_exe_gates = []
        sabre_instance.logic2phy = [0, 1]
        mock_sabre.return_value = sabre_instance

        routing.execute_routing(
            search_tree=None,
            ag=ag,
            initial_layout={0: 0, 1: 1, 2: 2},
            num_q_vir=2,
            measure_ops=[],
            dg=dg,
        )

        execute_args = sabre_instance.execute.call_args[0]
        assert execute_args[1] == [0, 1]
