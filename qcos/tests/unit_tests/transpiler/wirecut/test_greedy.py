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

import unittest

from qcos.transpiler.cmss.wirecut.greedy import GreedyModel


class TestGreedyModel(unittest.TestCase):
    """Test GreedyModel class."""

    def setUp(self):
        """Set up test environment."""
        self.nvertex = 5
        self.edges = [(0, 1), (1, 2), (2, 3), (3, 4)]
        self.nsubcircuit = 2
        self.max_subcircuit_width = 5
        self.max_cuts = 2

    def test_greedy_model_init(self):
        """Testing GreedyModel initialization."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        assert model.nvertex == self.nvertex
        assert model.nedge == len(self.edges)
        assert model.nsubcircuit == self.nsubcircuit
        assert model.max_subcircuit_width == self.max_subcircuit_width
        assert model.max_cuts == self.max_cuts
        assert len(model.weight) == self.nvertex

    def test_greedy_model_solve_success(self):
        """Test GreedyModel successfully solved."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        success, cut_edges, subcircuits = model.solve()

        assert success
        assert isinstance(cut_edges, list)
        assert isinstance(subcircuits, list)
        assert len(subcircuits) == self.nsubcircuit

    def test_greedy_model_solve_failure(self):
        """Testing the case where the GreedyModel fails to find a solution."""
        # Using impossible-to-satisfy constraints
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=1,  # set excessively small width constraint
            max_cuts=0,
        )

        success, cut_edges, subcircuits = model.solve()
        assert isinstance(success, bool)
        if success:
            assert isinstance(cut_edges, list)
            assert isinstance(subcircuits, list)
        else:
            assert cut_edges is None
            assert subcircuits is None

    def test_greedy_by_degree(self):
        """Testing the Degree-Based Greedy Strategy."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        subcircuits = model._greedy_by_degree()
        assert len(subcircuits) == self.nsubcircuit
        assert all(len(sc) > 0 for sc in subcircuits)

    def test_greedy_by_weight(self):
        """Testing the Weight-Based Greedy Strategy."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        subcircuits = model._greedy_by_weight()
        assert len(subcircuits) == self.nsubcircuit
        assert all(len(sc) > 0 for sc in subcircuits)

    def test_greedy_by_balance(self):
        """Test the greedy strategy based on load balancing."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        subcircuits = model._greedy_by_balance()
        assert len(subcircuits) == self.nsubcircuit
        assert all(len(sc) > 0 for sc in subcircuits)

    def test_greedy_hybrid(self):
        """Testing Mixed Greedy Strategy."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        subcircuits = model._greedy_hybrid()
        assert len(subcircuits) == self.nsubcircuit
        assert all(len(sc) > 0 for sc in subcircuits)

    def test_compute_subcircuit_width(self):
        """Test subcircuit width calculation."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        # Testing the empty circuit
        width = model._compute_subcircuit_width([])
        assert width == 0

        # The test includes subcircuits with vertices
        width = model._compute_subcircuit_width([0, 1])
        assert width >= 0

    def test_is_valid_solution(self):
        """Test the validity check of the solution."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        # Test effective solution
        valid_subcircuits = [[0, 1, 2], [3, 4]]
        assert model._is_valid_solution(valid_subcircuits)

        # Test invalid solution (vertex count mismatch)
        invalid_subcircuits = [[0, 1], [2]]
        assert not model._is_valid_solution(invalid_subcircuits)

    def test_compute_cut_edges(self):
        """Test cutting edge calculation."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        subcircuits = [[0, 1, 2], [3, 4]]
        cut_edges = model._compute_cut_edges(subcircuits)
        assert isinstance(cut_edges, list)

    def test_greedy_with_backtracking(self):
        """Testing the backtracking greedy strategy."""
        model = GreedyModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

        result = model._greedy_with_backtracking()
        if result is not None:
            assert len(result) == self.nsubcircuit
            assert model._is_valid_solution(result)
