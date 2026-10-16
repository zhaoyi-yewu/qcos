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
from wy_qcos.transpiler.cmss.mapping.utils.mapping_utils import (
    build_id_remap,
    build_logical_remap,
    apply_logical_remap,
    restore_logical_mapping,
    restore_physical_ids,
    select_best_single_qubits,
    validate_mapping_inputs,
    find_connected_components,
    compute_adaptive_fidelity_threshold,
)


class TestBuildIdRemap:
    """Tests for build_id_remap."""

    def test_empty_set(self):
        """Empty input should return empty remap."""
        remap = build_id_remap(set())
        assert remap.dense_count == 0
        assert not remap.orig_to_dense
        assert not remap.dense_to_orig

    def test_contiguous_ids(self):
        """Contiguous IDs should produce identity mapping."""
        remap = build_id_remap({0, 1, 2})
        assert remap.dense_count == 3
        assert remap.dense_to_orig == [0, 1, 2]
        assert remap.orig_to_dense == {0: 0, 1: 1, 2: 2}

    def test_sparse_ids(self):
        """Sparse IDs should be densified correctly."""
        remap = build_id_remap({0, 3, 7})
        assert remap.dense_count == 3
        assert remap.dense_to_orig == [0, 3, 7]
        assert remap.orig_to_dense == {0: 0, 3: 1, 7: 2}


class TestBuildLogicalRemap:
    """Tests for build_logical_remap."""

    def test_no_gaps(self):
        """No gaps in qubit IDs should return empty remap."""
        gates = [CX([0, 1]), H([2])]
        remap = build_logical_remap(gates, [])
        assert remap.dense_count == 0

    def test_with_gaps(self):
        """Gaps in qubit IDs should produce correct remap."""
        gates = [CX([0, 3]), H([5])]
        remap = build_logical_remap(gates, [])
        assert remap.dense_count == 3
        assert remap.dense_to_orig == [0, 3, 5]


class TestApplyAndRestoreLogicalRemap:
    """Tests for apply_logical_remap and restore_logical_mapping."""

    def test_roundtrip(self):
        """Apply then restore should roundtrip correctly."""
        gates = [CX([0, 5]), H([10])]
        remap = build_logical_remap(gates, [])
        apply_logical_remap(gates, [], remap)
        assert gates[0].targets == [0, 1]
        assert gates[1].targets == [2]

        dense_mapping = [2, 0, 1]
        restored = restore_logical_mapping(remap, dense_mapping)
        assert restored[0] == 2
        assert restored[5] == 0
        assert restored[10] == 1


class TestRestorePhysicalIds:
    """Tests for restore_physical_ids."""

    def test_basic(self):
        """Basic dense-to-original ID restoration."""
        remap = build_id_remap({10, 20, 30})
        mapping = [0, 2, 1]
        restore_physical_ids(mapping, remap)
        assert mapping == [10, 30, 20]

    def test_negative_entries(self):
        """Negative entries (-1) should be left untouched."""
        remap = build_id_remap({0, 1, 2})
        mapping = [0, -1, 2]
        restore_physical_ids(mapping, remap)
        assert mapping == [0, -1, 2]


class TestSelectBestSingleQubits:
    """Tests for select_best_single_qubits."""

    def test_basic_selection(self):
        """Should select top-N by fidelity descending."""
        fids = [0.9, 0.5, 0.99, 0.1]
        result = select_best_single_qubits(fids, used=set(), count=2)
        assert len(result) == 2
        assert result[0] == 2
        assert result[1] == 0

    def test_with_used_set(self):
        """Used qubits should be excluded from selection."""
        fids = [0.9, 0.5, 0.99, 0.1]
        result = select_best_single_qubits(fids, used={2}, count=2)
        assert len(result) == 2
        assert 2 not in result

    def test_zero_fidelity_excluded(self):
        """Zero fidelity qubits should be excluded."""
        fids = [0.0, 0.9, 0.0, 0.5]
        result = select_best_single_qubits(fids, used=set(), count=3)
        assert len(result) == 2


class TestValidateMappingInputs:
    """Tests for validate_mapping_inputs."""

    def test_empty_coupling_raises(self):
        """Empty coupling list should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            validate_mapping_inputs([], [], 2)

    def test_length_mismatch_raises(self):
        """Mismatched lengths should raise ValueError."""
        with pytest.raises(ValueError, match="size"):
            validate_mapping_inputs([(0, 1)], [0.9, 0.8], 2)

    def test_too_many_logical_raises(self):
        """Too many logical qubits should raise."""
        with pytest.raises(ValueError, match="num_logical"):
            validate_mapping_inputs([(0, 1)], [], 5)

    def test_valid_inputs(self):
        """Valid inputs should not raise."""
        validate_mapping_inputs([(0, 1), (1, 2)], [0.9, 0.8], 2)


class TestFindConnectedComponents:
    """Tests for find_connected_components."""

    def test_single_component(self):
        """Single connected component should have one root."""
        edges = [(0, 1), (1, 2), (2, 3)]
        components = find_connected_components(edges)
        roots = set(components.values())
        assert len(roots) == 1

    def test_multiple_components(self):
        """Disconnected graph should have multiple roots."""
        edges = [(0, 1), (3, 4)]
        components = find_connected_components(edges)
        roots = set(components.values())
        assert len(roots) == 2


class TestComputeAdaptiveFidelityThreshold:
    """Tests for compute_adaptive_fidelity_threshold."""

    def test_empty_fidelities(self):
        """Empty fidelities should return 0.0."""
        assert compute_adaptive_fidelity_threshold([]) == 0.0

    def test_clamp_lower(self):
        """Low fidelities should clamp threshold to lower bound 0.3."""
        fids = [0.1, 0.1, 0.1]
        threshold = compute_adaptive_fidelity_threshold(fids)
        # mean=0.1, std=0, raw=0.1, clamped to lower bound 0.3
        assert threshold == 0.3

    def test_clamp_upper(self):
        """High fidelities should clamp threshold to upper bound 0.9."""
        fids = [0.99] * 100
        threshold = compute_adaptive_fidelity_threshold(fids)
        # mean=0.99, std=0, raw=0.99, clamped to upper bound 0.9
        assert threshold == 0.9

    def test_skips_zero_fidelities(self):
        """Zero fidelity entries should be excluded from calculation."""
        fids = [0.0, 0.9, 0.8, 0.0, 0.7]
        threshold = compute_adaptive_fidelity_threshold(fids)
        # valid=[0.9, 0.8, 0.7], mean=0.8, std≈0.08165, raw≈0.71835
        assert abs(threshold - 0.71835) < 0.001
