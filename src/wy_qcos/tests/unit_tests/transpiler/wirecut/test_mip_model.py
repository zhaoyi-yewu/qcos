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

import pulp
import unittest

from wy_qcos.transpiler.cmss.wirecut.mip_model import MIPModel


class TestMIPModel(unittest.TestCase):
    def setUp(self):
        """Set up the test environment for each test case."""
        # Example values for the test case
        self.nvertex = 5  # Number of vertices in the graph
        self.edges = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 4],
        ]  # Edges representing a simple DAG
        self.nsubcircuit = 2  # Number of subcircuits
        self.max_subcircuit_width = 5  # Max width (max qubits in a subcircuit)
        self.max_cuts = 2  # Max cuts allowed

        # Initialize the MIP Model
        self.model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )

    def test_add_variables(self):
        """Test the variable creation in the MIP model."""
        # Test that the variables are created correctly
        assert len(self.model.vertex_var) == self.nsubcircuit
        assert len(self.model.vertex_var[0]) == self.nvertex

        assert len(self.model.edge_var) == self.nsubcircuit
        assert len(self.model.edge_var[0]) == len(self.edges)

        assert all(
            isinstance(var, pulp.LpVariable)
            for var in self.model.vertex_var[0]
        )

        assert all(
            isinstance(var, pulp.LpVariable) for var in self.model.edge_var[0]
        )

    def test_constraints(self):
        """Test if the constraints are added correctly."""
        # Check that constraints are added properly for each vertex
        for v in range(self.nvertex):
            constraint_name = f"cons_vertex_{v}"
            constraint = [
                c
                for c in self.model.model.constraints.values()
                if c.name == constraint_name
            ]
            assert len(constraint) == 1

        # Check if symmetry breaking constraints exist for vertices
        for vertex in range(self.nsubcircuit):
            constraint_name = f"cons_symm_{vertex}"
            constraint = [
                c
                for c in self.model.model.constraints.values()
                if c.name == constraint_name
            ]
            assert len(constraint) == 1

    def test_solution(self):
        """Test if the MIP model can be solved and get a feasible solution."""
        success, cut_edges, _ = self.model.solve()

        assert success  # Check if the model was solved successfully
        assert isinstance(cut_edges, list)

    def test_invalid_solution(self):
        """Test the case where no feasible solution is found."""
        # Use invalid constraints or parameters to force an unsolvable problem
        invalid_model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=1,
            max_cuts=0,
        )
        success, _, _ = invalid_model.solve()
        assert not success  # The solution should be unsuccessful

    def test_sovle_1(self):
        # Example values for the test case
        self.nvertex = 5  # Number of vertices in the graph
        self.edges = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 4],
        ]  # Edges representing a simple DAG
        self.nsubcircuit = 3  # Number of subcircuits
        self.max_subcircuit_width = 3  # Max width (max qubits in a subcircuit)
        self.max_cuts = 2  # Max cuts allowed

        # Initialize the MIP Model
        self.model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )
        success, cut_edges, _ = self.model.solve()
        assert success
        assert len(cut_edges) == 2

    def test_sovle_2(self):
        # Example values for the test case
        self.nvertex = 5  # Number of vertices in the graph
        self.edges = [
            [0, 1],
            [1, 2],
            [0, 3],
            [3, 4],
        ]  # Edges representing a simple DAG
        self.nsubcircuit = 3  # Number of subcircuits
        self.max_subcircuit_width = 3  # Max width (max qubits in a subcircuit)
        self.max_cuts = 2  # Max cuts allowed

        # Initialize the MIP Model
        self.model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )
        success, cut_edges, _ = self.model.solve()
        assert success
        assert len(cut_edges) == 2

    def test_sovle_3(self):
        # Example values for the test case
        self.nvertex = 6  # Number of vertices in the graph
        self.edges = [
            [0, 1],
            [1, 2],
            [0, 3],
            [3, 4],
            [4, 5],
        ]  # Edges representing a simple DAG
        self.nsubcircuit = 3  # Number of subcircuits
        self.max_subcircuit_width = 3  # Max width (max qubits in a subcircuit)
        self.max_cuts = 2  # Max cuts allowed

        # Initialize the MIP Model
        self.model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )
        success, cut_edges, _ = self.model.solve()
        assert success
        assert len(cut_edges) == 2

    def test_sovle_4(self):
        # Example values for the test case
        self.nvertex = 6  # Number of vertices in the graph
        self.edges = [
            [0, 1],
            [1, 2],
            [0, 3],
            [3, 4],
            [4, 5],
        ]  # Edges representing a simple DAG
        self.nsubcircuit = 2  # Number of subcircuits
        self.max_subcircuit_width = 4  # Max width (max qubits in a subcircuit)
        self.max_cuts = 2  # Max cuts allowed

        # Initialize the MIP Model
        self.model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )
        success, cut_edges, _ = self.model.solve()
        assert success
        assert len(cut_edges) == 1

    def test_sovle_5(self):
        # Example values for the test case
        self.nvertex = 7  # Number of vertices in the graph
        self.edges = [
            [0, 1],
            [1, 2],
            [0, 3],
            [3, 4],
            [4, 5],
            [5, 6],
        ]  # Edges representing a simple DAG
        self.nsubcircuit = 4  # Number of subcircuits
        self.max_subcircuit_width = 3  # Max width (max qubits in a subcircuit)
        self.max_cuts = 4  # Max cuts allowed

        # Initialize the MIP Model
        self.model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )
        success, cut_edges, _ = self.model.solve()
        assert success
        assert len(cut_edges) == 3

    def test_sovle_6(self):
        # Example values for the test case
        self.nvertex = 14  # Number of vertices in the graph
        self.edges = [
            [0, 2],
            [0, 1],
            [1, 3],
            [1, 2],
            [2, 4],
            [3, 5],
            [3, 4],
            [4, 6],
            [5, 7],
            [5, 6],
            [6, 8],
            [7, 9],
            [7, 8],
            [8, 10],
            [9, 11],
            [9, 10],
            [10, 12],
            [11, 13],
            [11, 12],
            [12, 13],
        ]  # Edges representing a simple DAG
        self.nsubcircuit = 2  # Number of subcircuits
        self.max_subcircuit_width = 6  # Max width (max qubits in a subcircuit)
        self.max_cuts = 10  # Max cuts allowed

        # Initialize the MIP Model
        self.model = MIPModel(
            nvertex=self.nvertex,
            edges=self.edges,
            nsubcircuit=self.nsubcircuit,
            max_subcircuit_width=self.max_subcircuit_width,
            max_cuts=self.max_cuts,
        )
        success, cut_edges, _ = self.model.solve()
        assert success
        assert len(cut_edges) == 2
