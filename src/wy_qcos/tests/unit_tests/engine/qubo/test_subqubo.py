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


from wy_qcos.engine.qubo import SubQUBOMultiSolution, QUBOSolution


class TestSubQUBOMultiSolution:
    """Unit testing for class SubQUBOMultiSolution."""

    @classmethod
    def setup_class(cls):
        # Creating a QUBO matrix for testing
        cls.qubo_matrix = np.array([
            [1, 0.5, 0.3],
            [0.5, 2, 0.4],
            [0.3, 0.4, 3],
        ])

        # Creating a test solution
        cls.test_solution = QUBOSolution(
            solution=np.array([1, 0, 1]),
            energy=4.3,
        )

    def setup_method(self):
        self.solver = SubQUBOMultiSolution(
            N_I=5,
            N_E=2,
            N_S=3,
            qubo_matrix=self.qubo_matrix,
            subqubo_size=2,
            max_converged_num=2,
        )

    def test_initialization(self):
        """Test class initialization."""
        # Testing default parameter initialization
        solver_default = SubQUBOMultiSolution()
        assert solver_default.N_I == 20
        assert solver_default.N_E == 1
        assert solver_default.N_S == 5
        assert isinstance(solver_default.qubo, np.ndarray)
        assert solver_default.subqubo_size == 100
        assert solver_default.max_converged_num == 3
        # Testing custom parameter initialization
        assert self.solver.N_I == 5
        assert self.solver.N_E == 2
        assert self.solver.N_S == 3
        assert np.array_equal(self.solver.qubo, self.qubo_matrix)
        assert self.solver.subqubo_size == 2
        assert self.solver.max_converged_num == 2

    def test_set_subqubo_size(self):
        """Test Settings subqubo size."""
        self.solver.set_subqubo_size(10)
        assert self.solver.subqubo_size == 10

    def test_set_qubo_matrix(self):
        """Test Settings QUBO Matrix."""
        new_qubo = np.array([[2, 0.1], [0.1, 1]])
        self.solver.set_qubo_matrix(new_qubo)
        assert np.array_equal(self.solver.qubo, new_qubo)

    def test_get_max_converged_num(self):
        """Test to obtain the maximum number of iterations."""
        result = self.solver.get_max_converged_num()
        assert result == 2

    def test_init_instance_pool(self):
        """Test initialization instance pool."""
        pool = self.solver.init_instance_pool()

        # Check pool size
        assert len(pool) == self.solver.N_I

        # Check the structure of each solution
        for solution in pool:
            assert isinstance(solution, QUBOSolution)
            assert isinstance(solution.solution, np.ndarray)
            assert isinstance(solution.energy, float)
            assert len(solution.solution) == self.qubo_matrix.shape[0]
            assert solution.energy == QUBOSolution.calculate_energy(
                self.qubo_matrix, solution.solution
            )

    def test_find_best_solution(self):
        """Testing to find the optimal solution."""
        # Create test solution pool
        pool = [
            QUBOSolution(np.array([0, 0, 0]), energy=0.0),  # Optimal
            QUBOSolution(np.array([1, 1, 1]), energy=10.0),  # Worst
            QUBOSolution(np.array([1, 0, 0]), energy=2.0),  # middle
        ]

        best_solution, order_idx = self.solver.find_best_solution(pool)

        # Check the optimal solution
        assert best_solution.energy == 0.0
        assert np.array_equal(best_solution.solution, np.array([0, 0, 0]))

        # Check sort index
        assert np.array_equal(order_idx, [0, 2, 1])

    def test_optimize_solution(self):
        """Test optimization of individual solutions."""
        original_solution = QUBOSolution(
            solution=np.array([1, 1, 1]), energy=10.0
        )
        optimized = self.solver._optimize_solution(original_solution)
        # Verification solution has been updated
        assert optimized.energy <= 10

    def test_optimize_solution_pool(self):
        """Test optimization solution pool."""
        # Create a test solution pool
        pool = [
            QUBOSolution(np.array([1, 1, 1]), energy=10.0),
            QUBOSolution(np.array([0, 0, 0]), energy=0.0),
        ]

        with patch.object(self.solver, "_optimize_solution") as mock_optimize:
            # Set mock return to improved solution
            mock_optimize.side_effect = [
                QUBOSolution(np.array([0, 1, 1]), energy=5.0),  # Improvement
                QUBOSolution(np.array([0, 0, 0]), energy=0.0),  # unchanged
            ]

            updated_pool = self.solver.optimize_solution_pool(pool)

            # Verify that each solution is optimized
            assert mock_optimize.call_count == 2
            assert len(updated_pool) == 2
            assert updated_pool[0].energy == 5.0
            assert updated_pool[1].energy == 0.0

    def test_extract_subqubo(self):
        """Test extraction of sub-QUBO."""
        tmp_solution = QUBOSolution(np.array([1, 0, 1]), energy=4.3)
        extracted_index = [0, 2]  # Extract the 0th and 2nd variables
        non_extracted_index = [1]  # Do not extract the first variable

        subqubo = self.solver._extract_subqubo(
            tmp_solution, extracted_index, non_extracted_index
        )

        # Verify the size of the sub-QUBO matrix
        assert len(subqubo) == 2
        assert len(subqubo[0]) == 2

        # Verify that the diagonal elements contain additional terms
        expected_00 = self.qubo_matrix[0, 0] + (
            self.qubo_matrix[0, 1] * tmp_solution.solution[1]
            + self.qubo_matrix[1, 0] * tmp_solution.solution[1]
        )
        assert subqubo[0][0] == pytest.approx(expected_00)

    def test_construct_subqubo(self):
        """Test building sub-QUBO."""
        # Create N_S solutions
        n_s_pool = [
            QUBOSolution(np.array([1, 0, 0]), energy=1.0),
            QUBOSolution(np.array([0, 1, 0]), energy=2.0),
            QUBOSolution(np.array([0, 0, 1]), energy=3.0),
        ]

        subqubo, tmp_solution, extracted_index = self.solver.construct_subqubo(
            n_s_pool
        )

        # Verification returned results
        assert isinstance(subqubo, list)
        assert isinstance(tmp_solution, QUBOSolution)
        assert isinstance(extracted_index, np.ndarray)
        assert len(extracted_index) == self.solver.subqubo_size
        assert len(subqubo) == self.solver.subqubo_size

    def test_merge_solution(self):
        """Test merge solution."""
        tmp_solution = QUBOSolution(np.array([1, 1, 1]), energy=10.0)
        sub_solution = [0, 1]
        extracted_index = [0, 2]

        merged = self.solver.merge_solution(
            tmp_solution, np.array(sub_solution), extracted_index
        )

        # Verify merge results
        expected_solution = np.array([0, 1, 1])
        assert np.array_equal(merged.solution, expected_solution)
        assert merged.energy == QUBOSolution.calculate_energy(
            self.qubo_matrix, expected_solution
        )

    def test_create_sub_solution_pools(self):
        """Test creating a sub-solution pool."""
        # Create the main solution pool
        main_pool = [
            QUBOSolution(np.array([1, 0, 0]), energy=1.0),
            QUBOSolution(np.array([0, 1, 0]), energy=2.0),
            QUBOSolution(np.array([0, 0, 1]), energy=3.0),
            QUBOSolution(np.array([1, 1, 0]), energy=4.0),
            QUBOSolution(np.array([0, 1, 1]), energy=5.0),
        ]

        n_e_pools = self.solver.create_sub_solution_pools(main_pool)

        # Verify the number of sub-pools
        assert len(n_e_pools) == self.solver.N_E

        # Verify the size of each subpool
        for pool in n_e_pools:
            assert len(pool) == self.solver.N_S

    def test_update_solution_pool(self):
        """Test update solution pool."""
        # Initial solution pool
        solution_pool = [
            QUBOSolution(np.array([1, 1, 1]), energy=10.0),  # 最差
            QUBOSolution(np.array([0, 0, 0]), energy=0.0),  # 最优
            QUBOSolution(np.array([1, 0, 0]), energy=2.0),  # 中间
        ]

        # New solution (better than the current best)
        new_solutions = [QUBOSolution(np.array([0, 0, 1]), energy=-1.0)]

        best_solution, updated_pool = self.solver.update_solution_pool(
            solution_pool, new_solutions
        )

        # Verify the optimal solution
        assert best_solution.energy == -1.0

        # Verification pools are ranked by energy
        energies = [sol.energy for sol in updated_pool]
        assert energies == sorted(energies)

    def test_update_solution_pool_overflow(self):
        """Testing the overflow condition of the solution pool."""
        # Create exactly N_I solutions
        solution_pool = [
            QUBOSolution(np.array([0, 0, 0]), energy=float(i))
            for i in range(self.solver.N_I)
        ]

        # Add more new solutions
        new_solutions = [
            QUBOSolution(np.array([1, 1, 1]), energy=100.0),
            QUBOSolution(np.array([1, 0, 1]), energy=200.0),
        ]

        best_solution, updated_pool = self.solver.update_solution_pool(
            solution_pool, new_solutions
        )

        # The size of the verification pool remains unchanged
        assert len(updated_pool) == self.solver.N_I

        # The worst solution is verified and removed
        # (the one with the highest energy)
        max_energy = max(sol.energy for sol in updated_pool)
        assert max_energy <= 200.0

    @patch("numpy.random.randint")
    def test_deterministic_initialization(self, mock_randint):
        """Test deterministic initialization."""
        mock_randint.return_value = np.array([1, 0, 1])

        pool = self.solver.init_instance_pool()

        # Verify that all solutions are the same
        for solution in pool:
            assert np.array_equal(solution.solution, np.array([1, 0, 1]))

    def test_empty_solution_pool(self):
        """Testing the situation of the empty solution pool."""
        empty_pool = []

        with pytest.raises(IndexError):
            self.solver.find_best_solution(empty_pool)

    def test_single_solution_pool(self):
        """Test for the case with only one solution."""
        single_pool = [QUBOSolution(np.array([1, 0, 1]), energy=5.0)]

        best, order = self.solver.find_best_solution(single_pool)

        assert best.energy == 5.0
        assert np.array_equal(order, [0])

    def test_large_qubo_matrix(self):
        """Testing large QUBO matrix."""
        large_qubo = np.random.rand(10, 10)
        large_qubo = (large_qubo + large_qubo.T) / 2

        solver = SubQUBOMultiSolution(qubo_matrix=large_qubo, subqubo_size=5)
        pool = solver.init_instance_pool()

        assert len(pool) == solver.N_I
        for solution in pool:
            assert len(solution.solution) == 10
