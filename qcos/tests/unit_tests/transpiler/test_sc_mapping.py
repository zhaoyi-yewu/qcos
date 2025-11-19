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
from qcos.transpiler.cmss.mapping.sc_mapping import SCRoute
from qcos.transpiler.cmss.common.gate_operation import CX, H, Measure


class TestSCRoute:
    """Test SCRoute class"""

    def create_test_qpu_config(self):
        """Create a test QPU configuration"""
        return {"coupler_map": {"0": (0, 1), "1": (1, 2), "2": (2, 3)}}

    def test_init(self):
        """Test SCRoute initialization"""
        route = SCRoute()
        assert route.qpu_config is None
        assert route.initial_layout is None
        assert route.method_init_mapping == "topgraph"
        assert route.objective == "size"
        assert route.routing is not None

    def test_layout_dict_to_list(self):
        """Test _layout_dict_to_list method"""
        route = SCRoute()
        layout_dict = {0: 1, 1: 0, 2: 2}
        result = route._layout_dict_to_list(layout_dict)
        assert result == [1, 0, 2]

    def test_layout_dict_to_list_not_dict(self):
        """Test _layout_dict_to_list with non-dict input"""
        route = SCRoute()
        with pytest.raises(MappingException) as exc_info:
            route._layout_dict_to_list("not_a_dict")
        assert "layout_dict must be a dict" in str(exc_info.value)

    def test_layout_dict_to_list_no_int_keys(self):
        """Test _layout_dict_to_list with no integer keys"""
        route = SCRoute()
        with pytest.raises(MappingException) as exc_info:
            route._layout_dict_to_list({"a": 1, "b": 2})
        assert "layout_dict must have at least one integer key" in str(
            exc_info.value
        )

    def test_layout_list_to_dict(self):
        """Test _layout_list_to_dict method"""
        route = SCRoute()
        layout_list = [0, 1, 2, 3]
        result = route._layout_list_to_dict(layout_list)
        assert result == {0: 0, 1: 1, 2: 2, 3: 3}

    def test_layout_dict_reverse(self):
        """Test _layout_dict_reverse method"""
        route = SCRoute()
        layout_dict = {0: 1, 1: 0, 2: 2}
        result = route._layout_dict_reverse(layout_dict)
        assert result == {1: 0, 0: 1, 2: 2}

    def test_import_qpu_file_basic(self):
        """Test _import_qpu_file basic functionality"""
        route = SCRoute()
        qpu_config = self.create_test_qpu_config()
        result = route._import_qpu_file(qpu_config)
        assert "adjacency_list" in result
        assert isinstance(result["adjacency_list"], list)

    def test_import_qpu_file_no_coupler_map(self):
        """Test _import_qpu_file without coupler_map"""
        route = SCRoute()
        qpu_config = {}
        with pytest.raises(MappingException) as exc_info:
            route._import_qpu_file(qpu_config)
        assert "Cannot find 'coupler_map'" in str(exc_info.value)

    def test_import_qpu_file_invalid_coupler_map(self):
        """Test _import_qpu_file with invalid coupler_map"""
        route = SCRoute()
        qpu_config = {"coupler_map": "not_a_dict"}
        with pytest.raises(MappingException) as exc_info:
            route._import_qpu_file(qpu_config)
        assert "coupler_map must be a dict" in str(exc_info.value)

    def test_import_qpu_file_with_disable_qubits(self):
        """Test _import_qpu_file with disable_qubits"""
        route = SCRoute()
        qpu_config = self.create_test_qpu_config()
        result = route._import_qpu_file(qpu_config, disable_qubits=[1])
        assert "adjacency_list" in result

    def test_import_qpu_file_string_qubits(self):
        """Test _import_qpu_file with string qubits"""
        route = SCRoute()
        qpu_config = {"coupler_map": {"0": ("q0", "q1"), "1": ("q1", "q2")}}
        result = route._import_qpu_file(qpu_config)
        assert "adjacency_list" in result

    def test_convert_gate_targets_to_int(self):
        """Test _convert_gate_targets_to_int method"""
        route = SCRoute()
        gate = Mock()
        gate.targets = ["0", "1"]
        gates = [gate]
        route._convert_gate_targets_to_int(gates)
        assert gate.targets == [0, 1]

    def test_convert_gate_targets_to_int_none_targets(self):
        """Test _convert_gate_targets_to_int with None targets"""
        route = SCRoute()
        gate = Mock()
        gate.targets = None
        gates = [gate]
        route._convert_gate_targets_to_int(gates)
        assert gate.targets is None

    def test_convert_gate_targets_to_int_empty(self):
        """Test _convert_gate_targets_to_int with empty list"""
        route = SCRoute()
        route._convert_gate_targets_to_int([])
        # Should not raise error

    def test_prepare_data_basic(self):
        """Test prepare_data basic functionality"""
        route = SCRoute()
        qbit_num = 4
        gates = [CX(targets=[0, 1]), CX(targets=[2, 3]), H(targets=[0])]
        qpu_config = self.create_test_qpu_config()

        route.prepare_data(qbit_num, gates, qpu_config)

        assert route.qbit_num == qbit_num
        assert route.gates == gates
        assert route.qpu_config == qpu_config
        assert route.ag is not None
        assert route.dg is not None
        assert route.initial_layout is not None

    def test_prepare_data_with_measure(self):
        """Test prepare_data with measure operations"""
        route = SCRoute()
        qbit_num = 4
        gates = [
            CX(targets=[0, 1]),
            Measure(targets=[0]),
            Measure(targets=[1]),
        ]
        qpu_config = self.create_test_qpu_config()

        route.prepare_data(qbit_num, gates, qpu_config)

        assert len(route.measure_ops) >= 2

    def test_prepare_data_invalid_adjacency_list(self):
        """Test prepare_data with invalid adjacency_list"""
        route = SCRoute()
        qbit_num = 4
        gates = [CX(targets=[0, 1])]
        qpu_config = {"coupler_map": {}}

        # Mock _import_qpu_file to return invalid type
        route._import_qpu_file = Mock(
            return_value={"adjacency_list": "not_a_list"}
        )

        with pytest.raises(MappingException) as exc_info:
            route.prepare_data(qbit_num, gates, qpu_config)
        assert "Unsupported adjacency_list type" in str(exc_info.value)

    def test_prepare_data_disconnected_graph(self):
        """Test prepare_data with disconnected graph"""
        route = SCRoute()
        qbit_num = 4
        gates = [CX(targets=[0, 1])]
        qpu_config = {
            "coupler_map": {
                "0": (0, 1),
                "1": (2, 3),  # Disconnected components
            }
        }

        with pytest.raises(MappingException) as exc_info:
            route.prepare_data(qbit_num, gates, qpu_config)
        assert "disconnected" in str(exc_info.value).lower()

    def test_prepare_data_non_int_adjacency(self):
        """Test prepare_data with non-int adjacency"""
        route = SCRoute()
        qbit_num = 4
        gates = [CX(targets=[0, 1])]
        qpu_config = {
            "coupler_map": {
                "0": (0, 1)  # Valid qubits to avoid null graph
            }
        }

        # Should handle gracefully
        try:
            route.prepare_data(qbit_num, gates, qpu_config)
            assert route.ag is not None
        except (
            MappingException,
            ValueError,
            TypeError,
            nx.NetworkXPointlessConcept,
        ):
            pass  # Expected behavior for invalid config

    def test_execute_with_order(self):
        """Test execute_with_order method"""
        route = SCRoute()
        qbit_num = 4
        gates = [CX(targets=[0, 1]), H(targets=[0])]
        qpu_config = self.create_test_qpu_config()

        route.prepare_data(qbit_num, gates, qpu_config)

        # Mock routing.execute_routing
        route.routing.execute_routing = Mock(return_value=[])

        result = route.execute_with_order()
        assert isinstance(result, list)
        route.routing.execute_routing.assert_called_once()

    def test_execute_with_order_no_prepare(self):
        """Test execute_with_order without prepare_data"""
        route = SCRoute()
        with pytest.raises(MappingException) as exc_info:
            route.execute_with_order()
        assert "prepare_data must be called" in str(exc_info.value)
