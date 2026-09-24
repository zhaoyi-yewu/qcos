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

from wy_qcos.common.cmss.gate_operation import CX, SWAP
from wy_qcos.common.cmss.measure import Measure
from wy_qcos.transpiler.cmss.mapping.utils.routing_verifier import (
    check_routing,
)


class TestCheckRouting:
    """Tests for check_routing verifier."""

    @staticmethod
    def _linear_graph(n: int) -> Graph:
        g = Graph()
        g.add_edges_from([(i, i + 1) for i in range(n - 1)])
        return g

    def test_valid_routing_accepted(self):
        """Valid routing should be accepted."""
        graph = self._linear_graph(4)
        gates = [CX([0, 1]), CX([1, 2]), CX([2, 3])]
        initial_mapping = [0, 1, 2, 3]
        # Manually construct a known-correct physical gate sequence
        phy_gates = [
            # 0-1 adjacent
            CX([0, 1]),
            # 1-2 adjacent
            CX([1, 2]),
            # 2-3 adjacent
            CX([2, 3]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        final_mapping = [0, 1, 2, 3]
        result = check_routing(
            graph,
            gates,
            phy_gates,
            initial_mapping,
            final_mapping,
        )
        assert result

    def test_invalid_topology_rejected(self):
        """2-qubit gate on non-adjacent qubits should be rejected."""
        # 0-1-2-3
        graph = self._linear_graph(4)
        gates = [CX([0, 1])]
        initial_mapping = [0, 1, 2, 3]
        # Invalid: 0-3 not adjacent
        phy_gates = [
            CX([0, 3]),
            Measure([0]),
            Measure([1]),
        ]
        result = check_routing(
            graph,
            gates,
            phy_gates,
            initial_mapping,
            initial_mapping,
        )
        assert result is False

    def test_missing_gate_rejected(self):
        """Missing gates in physical sequence should be rejected."""
        graph = self._linear_graph(4)
        gates = [CX([0, 1]), CX([1, 2])]
        initial_mapping = [0, 1, 2, 3]
        # Only executed the first gate, missing the second
        phy_gates = [
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        result = check_routing(
            graph,
            gates,
            phy_gates,
            initial_mapping,
            initial_mapping,
        )
        assert result is False

    def test_invalid_swap_rejected(self):
        """SWAP on non-adjacent qubits should be rejected."""
        graph = self._linear_graph(4)
        gates = [CX([0, 1])]
        initial_mapping = [0, 1, 2, 3]
        # Invalid SWAP: 0-3 not adjacent
        phy_gates = [
            SWAP([0, 3]),
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
        ]
        result = check_routing(
            graph,
            gates,
            phy_gates,
            initial_mapping,
            initial_mapping,
        )
        assert result is False

    def test_wrong_final_mapping_rejected(self):
        """Wrong final mapping should be rejected."""
        graph = self._linear_graph(4)
        gates = [CX([0, 1])]
        initial_mapping = [0, 1, 2, 3]
        phy_gates = [
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        # Report an incorrect final mapping
        wrong_final_mapping = [1, 0, 2, 3]
        result = check_routing(
            graph,
            gates,
            phy_gates,
            initial_mapping,
            wrong_final_mapping,
        )
        assert result is False
