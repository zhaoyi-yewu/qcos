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

from loguru import logger


class GreedyModel:
    """Quantum circuit cutting solver using greedy strategy."""

    def __init__(
        self,
        nvertex: int,
        edges: list[tuple[int, int]],
        nsubcircuit: int,
        max_subcircuit_width: int,
        max_cuts: int,
    ):
        """Initialize greedy solver.

        Args:
            nvertex (int): Number of vertices in DAG.
            edges (list[tuple[int, int]]): Edge list in DAG.
            nsubcircuit (int): Number of sub-circuits to be divided.
            max_subcircuit_width (int): Maximum width of subcircuit.
            max_cuts (int): Maximum cutting value.
        """
        self.nvertex = nvertex
        self.edges = edges
        self.nedge = len(edges)
        self.nsubcircuit = nsubcircuit
        self.max_subcircuit_width = max_subcircuit_width
        self.max_cuts = max_cuts
        # Calculate vertex weights (input number of qubits)
        self.weight = [2] * nvertex
        for _, v in edges:
            self.weight[v] -= 1
        # Building adjacency relationships of graph
        self._build_graph()

    def _build_graph(self):
        """Construct adjacency relationships of the graph."""
        self.adj_list = [[] for _ in range(self.nvertex)]
        self.vertex_degree = [0] * self.nvertex
        for u, v in self.edges:
            self.adj_list[u].append(v)
            self.adj_list[v].append(u)
            self.vertex_degree[u] += 1
            self.vertex_degree[v] += 1

    def solve(self):
        """Solving the circuit cutting problem using a greedy strategy.

        Returns:
            success: Whether a feasible solution is found.
            cut_edges: Cut edge list.
            subcircuits: list of vertices contained in each subcircuit.
        """
        # Try various greedy strategies and select the optimal result
        strategies = [
            self._greedy_by_degree,
            self._greedy_by_weight,
            self._greedy_by_balance,
            self._greedy_hybrid,
        ]

        best_solution = None
        best_cuts = float("inf")

        for strategy in strategies:
            subcircuits = strategy()
            if subcircuits and self._is_valid_solution(subcircuits):
                cut_edges = self._compute_cut_edges(subcircuits)
                if (
                    len(cut_edges) < best_cuts
                    and len(cut_edges) <= self.max_cuts
                ):
                    best_solution = subcircuits
                    best_cuts = len(cut_edges)
        if best_solution:
            cut_edges = self._compute_cut_edges(best_solution)
            logger.info(
                f"Number of cutting edges:{len(cut_edges)}, cut edges: "
                f"{cut_edges}, best solution for subcircuit: {best_solution}."
            )
            return True, cut_edges, best_solution
        else:
            # Backtracking greedy strategy ensures that as long as the MIP has
            # solution, the greedy approach can also find a feasible solution.
            backtrack_solution = self._greedy_with_backtracking()
            if backtrack_solution is not None:
                cut_edges = self._compute_cut_edges(backtrack_solution)
                logger.info(
                    f"[Retrospective allocation]: Greedy algorithm "
                    f"cuts the number of edges: {len(cut_edges)}, "
                    f"cutting edges:{cut_edges}, "
                    f"subcircuit: {backtrack_solution}."
                )
                return True, cut_edges, backtrack_solution
            else:
                return False, None, None

    def _greedy_with_backtracking(self):
        """Backtracking greedy strategy, ensuring feasible solutions.

        Returns:
            list[int]: subcircuits.
        """
        # Sort vertices in descending order of vertex degree (greedy order).
        vertices = sorted(
            range(self.nvertex),
            key=lambda v: self.vertex_degree[v],
            reverse=True,
        )
        subcircuits = [[] for _ in range(self.nsubcircuit)]
        assigned = [False] * self.nvertex

        def backtrack(idx):
            if idx == len(vertices):
                # Checking if the solution is valid.
                if self._is_valid_solution(subcircuits):
                    return True
                return False
            v = vertices[idx]
            for sc_idx in range(self.nsubcircuit):
                subcircuits[sc_idx].append(v)
                assigned[v] = True
                if (
                    self._compute_subcircuit_width(subcircuits[sc_idx])
                    <= self.max_subcircuit_width
                ):
                    if backtrack(idx + 1):
                        return True
                # Backtrack
                subcircuits[sc_idx].pop()
                assigned[v] = False
            return False

        found = backtrack(0)
        if found:
            return subcircuits
        else:
            return None

    def _compute_subcircuit_width(self, subcircuit: list[int]) -> int:
        """Calculate the actual width of the subcircuit.

        Args:
            subcircuit (list): list of vertices contained in the subcircuit.

        Returns:
            int: The actual width of the subcircuit.
        """
        if not subcircuit:
            return 0
        # Calculate the number of original input qubits
        original_input = sum(self.weight[v] for v in subcircuit)
        # Calculate the number of additional input qubits
        rho = 0
        subcircuit_set = set(subcircuit)
        for u, v in self.edges:
            # If the edge is cut and the target vertex is in the subcircuit
            if v in subcircuit_set and u not in subcircuit_set:
                rho += 1
        # Total width = Original input + Additional input
        return original_input + rho

    def _greedy_by_degree(self):
        """Degree-based greedy strategy.

        Returns:
            list[list[int]]: list of vertices contained in each subcircuit.
        """
        subcircuits = [[] for _ in range(self.nsubcircuit)]
        subcircuit_weights = [0] * self.nsubcircuit
        assigned = [False] * self.nvertex

        # Sort vertices in descending order by degree
        vertices_by_degree = sorted(
            range(self.nvertex),
            key=lambda v: self.vertex_degree[v],
            reverse=True,
        )
        for vertex in vertices_by_degree:
            if assigned[vertex]:
                continue
            # Select the sub-circuit with the lightest current load that
            # can accommodate the vertex
            best_subcircuit = -1
            min_weight = float("inf")
            for sc_idx in range(self.nsubcircuit):
                if (
                    subcircuit_weights[sc_idx] + self.weight[vertex]
                    <= self.max_subcircuit_width
                    and subcircuit_weights[sc_idx] < min_weight
                ):
                    min_weight = subcircuit_weights[sc_idx]
                    best_subcircuit = sc_idx
            if best_subcircuit != -1:
                subcircuits[best_subcircuit].append(vertex)
                subcircuit_weights[best_subcircuit] += self.weight[vertex]
                assigned[vertex] = True
                # Try assigning adjacent vertices to the same subcircuit
                # to reduce cuts
                self._assign_neighbors(
                    vertex,
                    best_subcircuit,
                    subcircuits,
                    subcircuit_weights,
                    assigned,
                )
        return subcircuits

    def _greedy_by_weight(self):
        """Vertex-weights based greedy strategy.

        Returns:
            (list[list[int]]): list of vertices contained in each subcircuit.
        """
        subcircuits = [[] for _ in range(self.nsubcircuit)]
        subcircuit_weights = [0] * self.nsubcircuit
        assigned = [False] * self.nvertex
        # Sort vertices in descending order by weight
        vertices_by_weight = sorted(
            range(self.nvertex), key=lambda v: self.weight[v], reverse=True
        )
        for vertex in vertices_by_weight:
            if assigned[vertex]:
                continue
            # Select the sub-circuit that minimizes the number of cuts
            best_subcircuit = self._find_best_subcircuit_for_cuts(
                vertex, subcircuits, subcircuit_weights, assigned
            )
            if best_subcircuit != -1:
                subcircuits[best_subcircuit].append(vertex)
                subcircuit_weights[best_subcircuit] += self.weight[vertex]
                assigned[vertex] = True
        return subcircuits

    def _greedy_by_balance(self):
        """Load-balanced greedy strategy.

        Returns:
            (list[list[int]]): list of vertices contained in each subcircuit.
        """
        subcircuits = [[] for _ in range(self.nsubcircuit)]
        subcircuit_weights = [0] * self.nsubcircuit
        assigned = [False] * self.nvertex

        # Process vertices in topological order
        for vertex in range(self.nvertex):
            if assigned[vertex]:
                continue
            # Select the feasible subcircuit with the lightest current load
            best_subcircuit = -1
            min_weight = float("inf")
            for sc_idx in range(self.nsubcircuit):
                if (
                    subcircuit_weights[sc_idx] + self.weight[vertex]
                    <= self.max_subcircuit_width
                    and subcircuit_weights[sc_idx] < min_weight
                ):
                    min_weight = subcircuit_weights[sc_idx]
                    best_subcircuit = sc_idx
            if best_subcircuit != -1:
                subcircuits[best_subcircuit].append(vertex)
                subcircuit_weights[best_subcircuit] += self.weight[vertex]
                assigned[vertex] = True
        return subcircuits

    def _greedy_hybrid(self):
        """Hybrid Greedy Strategy.

        Returns:
            (list[list[int]]): list of vertices contained in each subcircuit.
        """
        subcircuits = [[] for _ in range(self.nsubcircuit)]
        subcircuit_weights = [0] * self.nsubcircuit
        assigned = [False] * self.nvertex

        # Calculate the priority score for each vertex
        vertex_scores = []
        for v in range(self.nvertex):
            score = (
                self.vertex_degree[v] * 2  # Degree weight
                + self.weight[v] * 1.5  # Vertex weights
                + len(self.adj_list[v]) * 0.5  # Number of adjacent vertices
            )
            vertex_scores.append((score, v))

        # Sort by score in descending order
        vertex_scores.sort(reverse=True)

        for score, vertex in vertex_scores:
            if assigned[vertex]:
                continue
            # Select the best subcircuit by comprehensive evaluation
            best_subcircuit = self._comprehensive_subcircuit_selection(
                vertex, subcircuits, subcircuit_weights, assigned
            )
            if best_subcircuit != -1:
                subcircuits[best_subcircuit].append(vertex)
                subcircuit_weights[best_subcircuit] += self.weight[vertex]
                assigned[vertex] = True

        return subcircuits

    def _assign_neighbors(
        self, vertex, subcircuit_idx, subcircuits, subcircuit_weights, assigned
    ):
        """Try assigning neighboring vertices to the same sub-circuit.

        Args:
            vertex (int): The vertex to be assigned
            subcircuit_idx (int): The index of the sub-circuit
            subcircuits (list[list[int]]): The list of sub-circuits
            subcircuit_weights (list[int]): The list of weights of sub-circuits
            assigned (list[bool]): The list of assigned vertices
        """
        for neighbor in self.adj_list[vertex]:
            if (
                not assigned[neighbor]
                and subcircuit_weights[subcircuit_idx] + self.weight[neighbor]
                <= self.max_subcircuit_width
            ):
                subcircuits[subcircuit_idx].append(neighbor)
                subcircuit_weights[subcircuit_idx] += self.weight[neighbor]
                assigned[neighbor] = True

    def _find_best_subcircuit_for_cuts(
        self, vertex, subcircuits, subcircuit_weights, assigned
    ):
        """Find the sub-circuit that minimizes the number of cuts.

        Args:
            vertex (int): The vertex to be assigned
            subcircuits (list[list[int]]): The list of sub-circuits
            subcircuit_weights (list[int]): The list of weights of sub-circuits
            assigned (list[bool]): The list of assigned vertices

        Returns:
            int: The index of the best sub-circuit
        """
        best_subcircuit = -1
        min_new_cuts = float("inf")

        for sc_idx in range(self.nsubcircuit):
            if (
                subcircuit_weights[sc_idx] + self.weight[vertex]
                > self.max_subcircuit_width
            ):
                continue
            # Calculate the new number of cuts that would result from
            # assigning this vertex to this subcircuit.
            new_cuts = 0
            for neighbor in self.adj_list[vertex]:
                if assigned[neighbor] and neighbor not in subcircuits[sc_idx]:
                    new_cuts += 1

            if new_cuts < min_new_cuts:
                min_new_cuts = new_cuts
                best_subcircuit = sc_idx

        return best_subcircuit

    def _comprehensive_subcircuit_selection(
        self, vertex, subcircuits, subcircuit_weights, assigned
    ):
        """Comprehensive evaluation to select the optimal sub-circuit.

        Args:
            vertex (int): The vertex to be assigned.
            subcircuits (list[list[int]]): The list of subcircuits.
            subcircuit_weights (list[int]): The weights of each subcircuit.
            assigned (list[bool]): The assignment status of each vertex.

        Returns:
            int: The index of the best sub-circuit.
        """
        best_subcircuit = -1
        best_score = float("-inf")

        for sc_idx in range(self.nsubcircuit):
            if (
                subcircuit_weights[sc_idx] + self.weight[vertex]
                > self.max_subcircuit_width
            ):
                continue

            # Comprehensive score: considering load balancing, minimized
            # segmentation, and connectivity
            load_balance_score = (
                self.max_subcircuit_width - subcircuit_weights[sc_idx]
            )

            cut_reduction_score = 0
            for neighbor in self.adj_list[vertex]:
                if assigned[neighbor] and neighbor in subcircuits[sc_idx]:
                    cut_reduction_score += 2

            connectivity_score = len([
                n for n in self.adj_list[vertex] if n in subcircuits[sc_idx]
            ])

            total_score = (
                load_balance_score * 0.3
                + cut_reduction_score * 0.5
                + connectivity_score * 0.2
            )

            if total_score > best_score:
                best_score = total_score
                best_subcircuit = sc_idx

        return best_subcircuit

    def _is_valid_solution(self, subcircuits):
        """Check if the solution is valid.

        Args:
            subcircuits: list of vertices contained in each subcircuit.

        Returns:
            bool: True if the solution is valid, False otherwise.
        """
        # Check if all vertices are assigned
        total_vertices = sum(len(sc) for sc in subcircuits)
        if total_vertices != self.nvertex:
            return False

        # Check the weight constraints for each sub-circuit
        for sc in subcircuits:
            weight = sum(self.weight[v] for v in sc)
            if weight > self.max_subcircuit_width:
                return False

        return True

    def _compute_cut_edges(self, subcircuits):
        """Calculate the cutting edge.

        Args:
            subcircuits: list of vertices contained in each subcircuit.

        Returns:
            list of cut edges.
        """
        # Create a mapping from vertices to subcircuits
        vertex_to_subcircuit = {}
        for sc_idx, vertices in enumerate(subcircuits):
            for vertex in vertices:
                vertex_to_subcircuit[vertex] = sc_idx

        # Find the edges across subcircuits
        cut_edges = []
        for u, v in self.edges:
            if vertex_to_subcircuit[u] != vertex_to_subcircuit[v]:
                cut_edges.append((u, v))

        return cut_edges
