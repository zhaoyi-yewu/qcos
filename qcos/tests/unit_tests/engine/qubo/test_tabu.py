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

import numpy as np
import pytest
from unittest.mock import patch

from qcos.engine.qubo.tabu import QUBOSolution, TabuSearch


class TestTabuSearch:
    """Unit testing for QUBOSolution class and TabuSearch class."""

    def test_initialization(self):
        """Test QUBOSolution initialization."""
        solution = np.array([1, 0, 1])
        energy = 5.0
        qubo_solution = QUBOSolution(solution=solution, energy=energy)
        assert np.array_equal(qubo_solution.solution, solution)
        assert qubo_solution.energy == energy

    def test_calculate_energy(self):
        """Test energy calculation."""
        qubo_matrix = np.array([[1, 0.5, 0.3], [0.5, 2, 0.4], [0.3, 0.4, 3]])

        # Test with solution
        solution = np.array([1, 0, 1])
        energy = QUBOSolution.calculate_energy(qubo_matrix, solution)

        # Manual calculation: x^T * Q * x
        expected_energy = solution.T @ qubo_matrix @ solution
        assert energy == pytest.approx(expected_energy)

        # Test with None solution (should use zeros)
        energy_zero = QUBOSolution.calculate_energy(qubo_matrix, None)
        assert energy_zero == 0.0

    def test_calculate_energy_edge_cases(self):
        """Test energy calculation with edge cases."""
        # Zero matrix
        zero_qubo = np.zeros((2, 2))
        solution = np.array([1, 1])
        energy = QUBOSolution.calculate_energy(zero_qubo, solution)
        assert energy == 0.0

        # Diagonal matrix
        diag_qubo = np.diag([1, 2])
        solution = np.array([1, 1])
        energy = QUBOSolution.calculate_energy(diag_qubo, solution)
        assert energy == 3.0  # 1 * 1 + 2 * 1

    def setup_method(self):
        """Setup test fixtures."""
        self.qubo_matrix = np.array([
            [1, 0.5, 0.3],
            [0.5, 2, 0.4],
            [0.3, 0.4, 3],
        ])
        self.init_solution = np.array([1, 0, 1])

    def test_tabu_initialization(self):
        """Test TabuSearch initialization."""
        # Test with custom initial solution
        tabu = TabuSearch(
            qubo=self.qubo_matrix, init_solution=self.init_solution
        )

        assert np.array_equal(tabu.qubo, self.qubo_matrix)
        assert np.array_equal(tabu.init_solution, self.init_solution)
        assert np.array_equal(tabu.sol, self.init_solution)
        assert tabu.size == 3
        assert tabu.alpha_factor == 0.1
        assert tabu.alpha == 0

        # Test energy calculation
        expected_energy = QUBOSolution.calculate_energy(
            self.qubo_matrix, self.init_solution
        )
        assert tabu.energy == pytest.approx(expected_energy)

        # Test best solution initialization
        assert np.array_equal(tabu.best_solution, self.init_solution)
        assert tabu.best_energy == pytest.approx(expected_energy)

    def test_initialization_random_solution(self):
        """Test initialization with random solution."""
        with patch("numpy.random.randint") as mock_randint:
            mock_randint.return_value = np.array([0, 1, 0])
            tabu = TabuSearch(qubo=self.qubo_matrix, init_solution=None)
            mock_randint.assert_called_once_with(0, 2, 3)
            assert np.array_equal(tabu.init_solution, np.array([0, 1, 0]))

    def test_determine_tabu_tenure(self):
        """Test tabu tenure determination."""
        # Test different problem sizes
        test_cases = [
            (10, 10),  # size < 20
            (50, 12),  # size < 100
            (150, 15),  # size < 250
            (300, 20),  # size < 500
            (800, 25),  # size < 1000
            (2000, 30),  # size < 2500
            (5000, 35),  # size < 8000
            (10000, 40),  # size >= 8000
        ]
        for size, expected_tenure in test_cases:
            qubo = np.zeros((size, size))
            tabu = TabuSearch(qubo=qubo, init_solution=np.zeros(size))
            assert tabu.n_tabu == expected_tenure

    def test_update_tabu(self):
        """Test tabu table update."""
        tabu = TabuSearch(
            qubo=self.qubo_matrix, init_solution=self.init_solution
        )
        # Set initial tabu tenure
        tabu.tabu_tenure = np.array([3, 0, 5], dtype=np.uint8)
        # Update tabu for index 1
        tabu.update_tabu(1)
        # Check that index 1 is set to n_tabu and others are decremented
        assert tabu.tabu_tenure[0] == 2
        assert tabu.tabu_tenure[2] == 4
        # Test with negative index (no update)
        tabu.update_tabu(-1)
        # All non-zero values should be decremented
        assert tabu.tabu_tenure[0] == 1
        assert tabu.tabu_tenure[2] == 3

    def test_update_impact(self):
        """Test impact calculation."""
        tabu = TabuSearch(
            qubo=self.qubo_matrix, init_solution=self.init_solution
        )
        impact = tabu.update_impact()
        assert isinstance(impact, list)
        assert len(impact) == tabu.size

        # Verify impact calculation for each variable
        for i in range(tabu.size):
            # Create neighbor solution by flipping bit i
            neighbor = tabu.sol.copy()
            neighbor[i] = 1 - neighbor[i]

            # Calculate energy difference
            current_energy = QUBOSolution.calculate_energy(tabu.qubo, tabu.sol)
            new_energy = QUBOSolution.calculate_energy(tabu.qubo, neighbor)
            expected_impact = new_energy - current_energy
            assert impact[i] == pytest.approx(expected_impact)

    def test_find_best_flip(self):
        """Test finding best flip."""
        tabu = TabuSearch(
            qubo=self.qubo_matrix, init_solution=self.init_solution
        )

        # Set up impact values
        tabu.impact = [-2.0, -1.0, 0.5]

        # Test normal case (no tabu restrictions)
        best_index = tabu.find_best_flip()
        assert best_index == 0

        # Test when best flip is tabu but gives global improvement
        tabu.tabu_tenure = np.array([1, 0, 0], dtype=np.uint8)
        tabu.best_energy = tabu.energy + tabu.impact[0] - 0.1
        best_index = tabu.find_best_flip()
        # Test when all variables are tabu and no global improvement
        tabu.tabu_tenure = np.array([1, 1, 1], dtype=np.uint8)
        tabu.best_energy = tabu.energy - 1.0
        best_index = tabu.find_best_flip()
        assert best_index == 0

    def test_solve_basic(self):
        """Test basic solve functionality."""
        # Use a simple QUBO that's easy to solve
        simple_qubo = np.array([[1, 0], [0, 2]])
        init_solution = np.array([1, 1])
        tabu = TabuSearch(qubo=simple_qubo, init_solution=init_solution)

        # Set small number of iterations for testing
        tabu.alpha = 5
        solution = tabu.solve()

        # Verify solution is valid
        assert isinstance(solution, np.ndarray)
        assert len(solution) == tabu.size
        assert np.all((solution == 0) | (solution == 1))

        # Verify best solution is updated
        assert np.array_equal(tabu.best_solution, solution)
        assert tabu.best_energy <= tabu.energy

    def test_solve_with_improvement(self):
        """Test solve when improvement is found."""
        # QUBO where [0,0] is optimal (energy = 0)
        qubo = np.array([[1, 0.5], [0.5, 1]])
        init_solution = np.array([1, 1])  # Energy = 3
        tabu = TabuSearch(qubo=qubo, init_solution=init_solution)
        tabu.alpha = 10
        solution = tabu.solve()
        assert np.array_equal(solution, np.array([0, 0]))

        # Best energy should be better or equal to initial
        assert tabu.best_energy <= 3.0
