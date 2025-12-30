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
from dataclasses import dataclass


@dataclass
class QUBOSolution:
    """Solution information.

    This class contains:
        - solution (np.ndarray): n-sized solution composed of binary variables
        - energy (float): energy value obtained from QUBO(QuadraticProgram)
          of all term
    """

    solution: np.ndarray
    energy: float

    @classmethod
    def calculate_energy(
        cls, qubo: np.ndarray, solution: np.ndarray | None = None
    ) -> float:
        """Calculate the energy from the QUBO-matrix & solution.

        Args:
            qubo (np.ndarray): n-by-n QUBO-matrix
            solution (np.ndarray): n-sized solution composed of
                                   binary variables
        Returns:
            float: Energy value.
        """
        if solution is None:
            solution = np.zeros(qubo.shape[0])
        energy = float(solution.T @ qubo @ solution)
        return energy


class TabuSearch:
    """tabu search algorithm."""

    def __init__(
        self,
        qubo: np.ndarray,
        init_solution: np.ndarray | None = None,
    ):
        """Initialize tabu search algorithm.

        Args:
            qubo(np.ndarray): qubo matrix
            init_solution(list): initial solution.
        """
        self.qubo = qubo
        self.size = self.qubo.shape[0]
        if init_solution is None:
            self.init_solution = np.random.randint(0, 2, self.size)
        else:
            self.init_solution = init_solution
        self.sol = self.init_solution
        self.energy = QUBOSolution.calculate_energy(self.qubo, self.sol)
        # The ratio when calculating the maximum number
        # of iterations based on size
        self.alpha_factor = 0.1
        self.n_tabu = self.determine_tabu_tenure()
        # Maximum number of cycles
        self.alpha = int(self.alpha_factor * self.size)
        self.impact = self.update_impact()
        self.tabu_tenure = np.zeros(self.size, dtype=np.uint8)
        self.best_solution = self.init_solution
        self.best_energy = self.energy

    def update_tabu(self, index):
        """Update tabu table.

        Args:
            index(int): index of the variable
        """
        if index >= 0:
            # If the variable is flipped, it must not be
            # flipped again in the next c+rand(10) cycles.
            self.tabu_tenure[index] = self.n_tabu
        # With each cycle, all items greater than 0 are
        # reduced by 1.
        self.tabu_tenure[self.tabu_tenure >= 1] -= 1

    def get_best_solution(self):
        """Obtain the optimal solution and Hamiltonian.

        Returns:
            tuple: (best_solution, best_energy).
        """
        return self.best_solution, self.best_energy

    def update_impact(self):
        """Compute and update the flip cost vector for each bit.

        Returns:
            np.ndarray: Change in objective value for
                        flipping each bit.
        """
        impact = []
        for i in range(self.size):
            value = self.sol[i] * (
                np.dot(self.qubo[i, :], self.sol)
                + np.dot(self.qubo[:, i], self.sol)
                - self.qubo[i, i] * self.sol[i]
            )
            neighbor = self.sol.copy()
            neighbor[i] = 1 - neighbor[i]
            new_value = neighbor[i] * (
                np.dot(self.qubo[i, :], neighbor)
                + np.dot(self.qubo[:, i], neighbor)
                - self.qubo[i, i] * neighbor[i]
            )
            tmp = new_value - value

            impact.append(tmp)

        return impact

    def find_best_flip(self):
        """Looking for the best flip.

        Returns:
            int: index of the best flip
        """
        j_val_global = np.min(self.impact)

        # If flipping results in a better outcome than the current best,
        # then even if the variable is in the tabu list, it will still
        # be flipped, returning the index.
        if self.energy + j_val_global < self.best_energy:
            j_star = np.random.choice(
                np.argwhere(self.impact == j_val_global).flatten()
            )
            return j_star

        if np.count_nonzero(self.tabu_tenure) == self.size:
            return -1
        masked_impact = np.ma.array(self.impact, mask=(self.tabu_tenure > 0))
        j_val = np.min(masked_impact)
        j_star = np.random.choice(
            np.argwhere(masked_impact == j_val).flatten()
        )
        return j_star

    def solve(self):
        """Solve the problem.

        Returns:
            np.ndarray: solution.
        """
        # iterations
        for _ in range(self.alpha):
            j_star = self.find_best_flip()
            if j_star >= 0:
                impact = self.impact[j_star]
                self.sol[j_star] = 1 - self.sol[j_star]
                self.energy += impact
                self.impact = self.update_impact()
                if self.energy < self.best_energy:
                    self.best_solution = self.sol.copy()
                    self.best_energy = self.energy
            elif np.count_nonzero(self.tabu_tenure) == 0:
                break
            self.update_tabu(j_star)

        return self.best_solution

    def determine_tabu_tenure(self):
        """Determine an appropriate tabu tenure based on problem size.

        Returns:
            int: Tabu tenure.
        """
        if self.size < 20:
            return 10
        elif self.size < 100:
            return 12
        elif self.size < 250:
            return 15
        elif self.size < 500:
            return 20
        elif self.size < 1000:
            return 25
        elif self.size < 2500:
            return 30
        elif self.size < 8000:
            return 35
        else:
            return 40
