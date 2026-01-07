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
import random

from wy_qcos.engine.qubo.tabu import QUBOSolution, TabuSearch


class SubQUBOMultiSolution:
    """Implement subQUBO with multiple solution instances."""

    def __init__(
        self,
        N_I=20,
        N_E=1,
        N_S=5,
        qubo_matrix: np.ndarray | None = None,
        subqubo_size=100,
        max_converged_num=3,
    ) -> None:
        """Initialize the SubQUBOMultiSolution.

        Args:
            N_I (int): Number of solutions in instance pool. Defaults to 20.
            N_E (int): Number of extractions for subQUBO. Defaults to 5.
            N_S (int): Number of solutions extracted from the instance pool.
                    Defaults to 2.
            qubo_matrix (np.ndarray): qubo matrix
            subqubo_size (int): Number of qubits in subQUBO. Defaults to 50.
            max_converged_num (int): Convergence after how many consecutive
                                    times the optimal value is not updated.
                                    Defaults to 2.
        """
        self.N_I = N_I
        self.N_E = N_E
        self.N_S = N_S
        if qubo_matrix is None:
            qubo_matrix = np.zeros((10, 10))
        self.qubo = qubo_matrix
        self.subqubo_size = subqubo_size
        self.max_converged_num = max_converged_num
        self.pool = None

    def set_subqubo_size(self, subqubo_size):
        """Set subqubo size.

        Args:
            subqubo_size (int): new_subqubo_size
        """
        self.subqubo_size = subqubo_size

    def set_qubo_matrix(self, qubo_matrix: np.ndarray):
        """Set QUBO matrix and convert to binary quadratic model.

        Args:
            qubo_matrix (np.ndarray): n-by-n QUBO-matrix
        """
        self.qubo = qubo_matrix

    def get_max_converged_num(self):
        """Get max converged num.

        Returns:
            max_converged_num (int): converged num
        """
        return self.max_converged_num

    def _extract_subqubo(
        self, tmp_solution, extracted_index, non_extracted_index
    ):
        """Extract subQUBO model.

        Args:
            tmp_solution(np.ndarray): temporary solution in QUBO-matrix
            extracted_index(list): extracted index in QUBO-matrix
            non_extracted_index (list): no extracted index in QUBO-matrix.

        Returns:
            list(list): subQUBO matrix

        """
        # Extract subQUBO model from extracted_index
        subqubo_mat = [
            [self.qubo[j, k] for k in extracted_index] for j in extracted_index
        ]

        # Extract subQUBO model from non_extracted_index
        for idx_i in range(self.subqubo_size):
            subqubo_mat[idx_i][idx_i] += sum(
                (
                    self.qubo[extracted_index[idx_i], idx_j]
                    * tmp_solution.solution[idx_j]
                    + self.qubo[idx_j, extracted_index[idx_i]]
                    * tmp_solution.solution[idx_j]
                )
                for idx_j in non_extracted_index
            )

        return subqubo_mat

    def init_instance_pool(self):
        """Initialize the instance solutions pool include N_I solution.

        Returns:
            np.ndarray: solution pool
        """
        pool = []
        num_of_variables = self.qubo.shape[0]

        for _ in range(self.N_I):
            x = np.random.randint(
                0, 2, num_of_variables
            )  # generate random solutions
            energy = QUBOSolution.calculate_energy(self.qubo, x)
            pool.append(QUBOSolution(x, energy))
        return pool

    def find_best_solution(self, pool):
        """Find the best solution.

        Returns:
            QUBOSolution: best solution
            np.ndarray: ascending order index
        """
        ascending_order_idx = np.argsort(
            np.array(list(map(lambda sol: sol.energy, pool)))
        )
        best = pool[ascending_order_idx[0]]
        return best, ascending_order_idx

    def _optimize_solution(self, solution_i):
        """Optimize a single solution using TabuSearch.

        Args:
            solution_i (QUBOSolution): solution to be optimized
        Returns:
            QUBOSolution: optimized solution.
        """
        tmp_solution = solution_i.solution.setflags(write=False)
        tabu = TabuSearch(self.qubo, tmp_solution)
        solution = tabu.solve()
        energy = QUBOSolution.calculate_energy(self.qubo, solution)
        # If a better solution is found through the search,
        # update the solution information.
        if energy < solution_i.energy:
            solution_i.solution = solution
            solution_i.energy = energy
        return solution_i

    def optimize_solution_pool(self, pool):
        """Optimize all solutions.

        Args:
            pool (list): list of solutions
        Returns:
            list: list of optimized solutions.
        """
        updated_pool = []
        for solution_i in pool:
            solution = self._optimize_solution(solution_i)
            updated_pool.append(solution)
        return updated_pool

    def construct_subqubo(self, n_s_solutions_pool):
        """Construct subqubo matrix from N_S solutions pool.

        Args:
            n_s_solutions_pool (list): N_S solutions pool

        Returns:
            np.ndarray: subqubo matrix
            np.ndarray: temporary solution in QUBO-matrix
            np.ndarray: extracted index
        """
        vars_of_x = np.array([
            abs(
                sum(
                    n_s_solutions_pool[k].solution[j]
                    for k in range(len(n_s_solutions_pool))
                )
                - len(n_s_solutions_pool) / 2
            )
            for j in range(self.qubo.shape[0])
        ])
        # Select a solution randomly as the tentative solution
        tmp_solution = random.choice(n_s_solutions_pool)
        extracted_index = np.argsort(vars_of_x)[: self.subqubo_size]
        non_extracted_index = np.argsort(vars_of_x)[self.subqubo_size :]
        subqubo = self._extract_subqubo(
            tmp_solution, extracted_index, non_extracted_index
        )
        return subqubo, tmp_solution, extracted_index

    def merge_solution(self, tmp_solution, sub_solution, extracted_index):
        """Merge the sub solution into the tentative solution.

        Args:
            tmp_solution (QUBOSolution): tmp solution
            sub_solution (np.ndarray): sub solution to be merged
            extracted_index (list): extracted index of sub solution
        Returns:
            QUBOSolution: merged solution
        """
        solution_x = tmp_solution.solution.copy()
        for idx, val in enumerate(extracted_index):
            solution_x[val] = sub_solution[idx]
        energy = QUBOSolution.calculate_energy(self.qubo, solution_x)
        return QUBOSolution(solution_x, energy)

    def create_sub_solution_pools(self, solution_pool):
        """Create N_E sub-solution pools.

        Create N_E sub-solution pools from the main solution pool,
        each formed by randomly selecting N_S solution instances.

        Args:
            solution_pool (list): solutions pool.

        Returns:
            list: A list of N_E sub solution pools.
        """
        n_e_pools = []
        for _ in range(self.N_E):
            # Select N_S solution instances randomly from the pool
            n_s_pool = random.sample(solution_pool, self.N_S)
            n_e_pools.append(n_s_pool)
        return n_e_pools

    def update_solution_pool(self, solution_pool, new_solutions):
        """Update the solution pool.

        Update the solution pool by replacing the worst solutions
        with the best solution.

        Args:
            solution_pool (list): The current solution pool.
            new_solutions (list): A list of new solutions to be
                                  added to the pool.

        Returns:
            QUBOSolution: The best solution found in the updated pool.
            list: The updated solution pool.
        """
        solution_pool.extend(new_solutions)
        x_best, ascending_order_idx = self.find_best_solution(solution_pool)
        sorted_pool = [solution_pool[i] for i in ascending_order_idx]
        solution_pool = sorted_pool[: self.N_I]
        return x_best, solution_pool
