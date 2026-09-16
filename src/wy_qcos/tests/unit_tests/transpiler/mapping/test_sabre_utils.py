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

from wy_qcos.transpiler.cmss.mapping.utils.sabre_utils import (
    extract_topology_data,
)


class TestExtractTopologyData:
    def test_coupler_map_only(self):
        qpu_cfg = {
            "coupler_map": {
                "CZ0_1": ["Q0", "Q1"],
                "CZ1_2": ["Q1", "Q2"],
            }
        }
        coupling_list, edge_fidelities, qubit_fidelities = (
            extract_topology_data(qpu_cfg)
        )
        assert coupling_list == [(0, 1), (1, 2)]
        assert edge_fidelities == []
        assert qubit_fidelities == []

    def test_full_fidelity_data(self):
        qpu_cfg = {
            "coupler_map": {
                "CZ0_1": ["Q0", "Q1"],
                "CZ1_2": ["Q1", "Q2"],
            },
            "coupler_error": {
                "CZ0_1": 0.014,
                "CZ1_2": 0.024,
            },
            "readout_error": {
                "Q0": 0.001,
                "Q1": 0.006,
                "Q2": 0.002,
            },
        }
        coupling_list, edge_fidelities, qubit_fidelities = (
            extract_topology_data(qpu_cfg)
        )

        assert coupling_list == [(0, 1), (1, 2)]
        # Error to fidelity: 1 - 0.014 = 0.986
        assert edge_fidelities == [0.986, 0.976]
        assert qubit_fidelities == [0.999, 0.994, 0.998]

    def test_coupler_error_only(self):
        qpu_cfg = {
            "coupler_map": {"CZ0_1": ["Q0", "Q1"]},
            "coupler_error": {"CZ0_1": 0.01},
        }
        coupling_list, edge_fidelities, qubit_fidelities = (
            extract_topology_data(qpu_cfg)
        )
        assert coupling_list == [(0, 1)]
        assert edge_fidelities == [0.99]
        assert qubit_fidelities == []

    def test_readout_error_only(self):
        qpu_cfg = {
            "coupler_map": {"CZ0_1": ["Q0", "Q1"]},
            "readout_error": {"Q0": 0.001, "Q1": 0.002},
        }
        coupling_list, edge_fidelities, qubit_fidelities = (
            extract_topology_data(qpu_cfg)
        )
        assert coupling_list == [(0, 1)]
        assert edge_fidelities == []
        assert qubit_fidelities == [0.999, 0.998]

    def test_coupler_error_key_mismatch_raises(self):
        qpu_cfg = {
            "coupler_map": {
                "CZ0_1": ["Q0", "Q1"],
                "CZ1_2": ["Q1", "Q2"],
            },
            # CZ1_2 missing from coupler_error
            "coupler_error": {"CZ0_1": 0.014},
        }
        with pytest.raises(ValueError, match="not in coupler_error"):
            extract_topology_data(qpu_cfg)

    def test_invalid_qubit_name_raises(self):
        qpu_cfg = {
            "coupler_map": {"CZ0_1": ["Q0", "Q1"]},
            "readout_error": {"Q0": 0.001, "invalid": 0.5},
        }
        with pytest.raises(ValueError, match="Invalid qubit identifier"):
            extract_topology_data(qpu_cfg)

    def test_non_numeric_readout_error_raises(self):
        qpu_cfg = {
            "coupler_map": {"CZ0_1": ["Q0", "Q1"]},
            "readout_error": {"Q0": "high", "Q1": 0.002},
        }
        with pytest.raises(TypeError, match="must be numeric"):
            extract_topology_data(qpu_cfg)
