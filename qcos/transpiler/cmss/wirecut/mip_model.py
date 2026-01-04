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

from loguru import logger


class MIPModel:
    """Represent a mixed integer problem (MIP) for optimal cutting wire.

    Find the optimal position of cutting the edges of given DAG that
    represents a quantum circuit. The problem is modeled and solved
    using PuLP.

    Attributes:
        nvertex: The number of vertices in the input DAG.
        edges: The edges of the input DAG.
        nedge: The number of edges.
        nsubcircuit: The number of parts to be partitioned.
        max_subcircuit_width: The max number of qubits allowed in subcircuit.
        max_cuts: The maximum number of cuts allowed.
        weight: The number of input qubits associated with a gate.
                Valid numbers are 0, 1, and 2.
        subcircuit_counter: The dictionaries for storing variables of each
                            subcircuit.
        model: The PuLP model.
        subcircuits: The vertices in each subcircuit.
        num_cuts: A variable that represents the number of cuts.
        optimal: Whether the solution is optimal.
        objective: The objective value of the solution.
    """

    def __init__(
        self,
        nvertex: int,
        edges: list[tuple[int, int]],
        nsubcircuit: int,
        max_subcircuit_width: int,
        max_cuts: int,
    ):
        """Create the MIP model and add variables and constraints.

        Args:
            nvertex (int): The number of vertices in the input DAG.
            edges (list[tuple[int, int]]): The edges of the input DAG.
            nsubcircuit (int): The number of parts to be partitioned.
            max_subcircuit_width (int): Max num of qubits allowed in subcircuit
            max_cuts (int): The maximum number of cuts allowed.
        """
        self.nvertex = nvertex
        self.edges = edges
        self.nedge = len(edges)
        self.nsubcircuit = nsubcircuit
        self.max_subcircuit_width = max_subcircuit_width
        self.max_cuts = max_cuts
        self.weight = [2] * nvertex
        for _, v in edges:
            self.weight[v] -= 1

        self.subcircuit_counter = [{}] * nsubcircuit
        self.model = pulp.LpProblem("Circuit_cut", pulp.LpMinimize)
        self._add_variables()
        self._add_constraints()
        self._set_objective()

    def _add_variables(self) -> None:
        """Add the necessary variables to the MIP model."""
        # Indicate if a vertex is in some subcircuit
        self.vertex_var = []
        for i in range(self.nsubcircuit):
            sub = []
            for j in range(self.nvertex):
                varName = "bin_sc_" + str(i) + "_vx_" + str(j)
                loc_var = pulp.LpVariable(varName, cat=pulp.const.LpBinary)
                sub.append(loc_var)
            self.vertex_var.append(sub)

        # Indicate if an edge has one and only one vertex in some subcircuit
        self.edge_var = []
        for i in range(self.nsubcircuit):
            subcircuit_x = []
            for j in range(self.nedge):
                varName = "bin_sc_" + str(i) + "_edg_" + str(j)
                loc_var = pulp.LpVariable(varName, cat=pulp.const.LpBinary)
                subcircuit_x.append(loc_var)
            self.edge_var.append(subcircuit_x)

        # Total number of cuts.
        # Add 0.1 for numerical stability.
        self.num_cuts = pulp.LpVariable(
            "num_cuts", 0, self.max_cuts + 0.1, pulp.const.LpInteger
        )

        for subcircuit in range(self.nsubcircuit):
            self.subcircuit_counter[subcircuit] = {}

            # original input qubits number of subcircuit
            self.subcircuit_counter[subcircuit]["original_input"] = (
                pulp.LpVariable(
                    f"original_input_{str(subcircuit)}",
                    0,
                    self.max_subcircuit_width,
                    pulp.const.LpInteger,
                )
            )

            # new input qubits number of subcircuit
            self.subcircuit_counter[subcircuit]["rho"] = pulp.LpVariable(
                f"rho_{str(subcircuit)}",
                0,
                self.max_subcircuit_width,
                pulp.const.LpInteger,
            )

            # new output qubits number of subcircuit
            self.subcircuit_counter[subcircuit]["O"] = pulp.LpVariable(
                f"O_{str(subcircuit)}",
                0,
                self.max_subcircuit_width,
                pulp.const.LpInteger,
            )

            # new measure qubit number of subcircuit
            self.subcircuit_counter[subcircuit]["d"] = pulp.LpVariable(
                f"d_{str(subcircuit)}",
                0.1,
                self.max_subcircuit_width,
                pulp.const.LpInteger,
            )

            self.subcircuit_counter[subcircuit]["rho_qubit_product"] = []
            self.subcircuit_counter[subcircuit]["O_qubit_product"] = []
            for i in range(self.nedge):
                # The edge is cut by the subcircuit, and the first vertex
                # belongs to the subcircuit.
                edge_var_downstream_vertex_var_product = pulp.LpVariable(
                    f"bin_edge_var_downstream_vertex_var_product_"
                    f"{str(subcircuit)}_{str(i)}",
                    cat=pulp.const.LpBinary,
                )
                self.subcircuit_counter[subcircuit][
                    "rho_qubit_product"
                ].append(edge_var_downstream_vertex_var_product)
                edge_var_upstream_vertex_var_product = pulp.LpVariable(
                    f"bin_edge_var_upstream_vertex_var_product_"
                    f"{str(subcircuit)}_{str(i)}",
                    cat=pulp.const.LpBinary,
                )
                self.subcircuit_counter[subcircuit]["O_qubit_product"].append(
                    edge_var_upstream_vertex_var_product
                )

    def _symmetry_breaking_constraints(self) -> None:
        """Add symmetry-breaking constraints.

        Force small-numbered vertices into small-numbered subcircuits:
            v0: in subcircuit 0
            v1: in subcircuit_0 or subcircuit_1
            v2: in subcircuit_0 or subcircuit_1 or subcircuit_2
            ...
        """
        for vertex in range(self.nsubcircuit):
            self.model += (
                pulp.lpSum(
                    self.vertex_var[subcircuit][vertex]
                    for subcircuit in range(vertex + 1)
                )
                == 1,
                f"cons_symm_{str(vertex)}",
            )

    def _add_constraints(self) -> None:
        """Add all contraints and objectives to MIP model."""
        # Each vertex in exactly one subcircuit
        for v in range(self.nvertex):
            self.model += (
                pulp.lpSum(
                    self.vertex_var[i][v] for i in range(self.nsubcircuit)
                )
                == 1,
                f"cons_vertex_{str(v)}",
            )

        for i in range(self.nsubcircuit):
            for e in range(self.nedge):
                u = self.edges[e][0]
                v = self.edges[e][-1]
                u_vertex_var = self.vertex_var[i][u]
                v_vertex_var = self.vertex_var[i][v]
                ctName = "cons_edge_" + str(e) + "_circ_" + str(i)
                self.model += (
                    self.edge_var[i][e] - u_vertex_var - v_vertex_var <= 0,
                    ctName + "_1",
                )
                self.model += (
                    self.edge_var[i][e] - u_vertex_var + v_vertex_var >= 0,
                    ctName + "_2",
                )
                self.model += (
                    self.edge_var[i][e] + u_vertex_var - v_vertex_var >= 0,
                    ctName + "_3",
                )
                self.model += (
                    self.edge_var[i][e] + u_vertex_var + v_vertex_var <= 2,
                    ctName + "_4",
                )

        self._symmetry_breaking_constraints()

        # Compute number of cuts
        self.model += (
            self.num_cuts
            == pulp.lpSum([
                self.edge_var[subcircuit][i]
                for i in range(self.nedge)
                for subcircuit in range(self.nsubcircuit)
            ])
            / 2,
            "num_cuts",
        )

        for subcircuit in range(self.nsubcircuit):
            self._compute_qubit_number(subcircuit)

    def _compute_qubit_number(self, subcircuit: int) -> None:
        """Compute number of different types of qubit in a subcircuit.

        Args:
            subcircuit: The index of the subcircuit
        """
        self.model += (
            self.subcircuit_counter[subcircuit]["original_input"]
            - pulp.lpSum(
                self.weight[i] * self.vertex_var[subcircuit][i]
                for i in range(self.nvertex)
            )
            == 0,
            f"cons_subcircuit_input_{str(subcircuit)}",
        )

        for i in range(self.nedge):
            self.model += (
                self.subcircuit_counter[subcircuit]["rho_qubit_product"][i]
                <= self.edge_var[subcircuit][i],
                f"cons_edge_var_downstream_vertex_var_"
                f"{str(subcircuit)}_{str(i)}_1",
            )
            self.model += (
                self.subcircuit_counter[subcircuit]["rho_qubit_product"][i]
                <= self.vertex_var[subcircuit][self.edges[i][-1]],
                f"cons_edge_var_downstream_vertex_var_"
                f"{str(subcircuit)}_{str(i)}_2",
            )
            self.model += (
                self.subcircuit_counter[subcircuit]["rho_qubit_product"][i]
                >= self.edge_var[subcircuit][i]
                + self.vertex_var[subcircuit][self.edges[i][-1]]
                - 1,
                f"cons_edge_var_downstream_vertex_var_"
                f"{str(subcircuit)}_{str(i)}_3",
            )

        # Calculate the number of additional input qubits for each subcircuit
        self.model += (
            self.subcircuit_counter[subcircuit]["rho"]
            - pulp.lpSum(
                self.subcircuit_counter[subcircuit]["rho_qubit_product"]
            )
            == 0,
            f"cons_subcircuit_rho_qubits_{str(subcircuit)}",
        )

        for i in range(self.nedge):
            self.model += (
                self.subcircuit_counter[subcircuit]["O_qubit_product"][i]
                <= self.edge_var[subcircuit][i],
                f"cons_edge_var_upstream_vertex_var_"
                f"{str(subcircuit)}_{str(i)}_1",
            )
            self.model += (
                self.subcircuit_counter[subcircuit]["O_qubit_product"][i]
                <= self.vertex_var[subcircuit][self.edges[i][0]],
                f"cons_edge_var_upstream_vertex_var_"
                f"{str(subcircuit)}_{str(i)}_2",
            )
            self.model += (
                self.subcircuit_counter[subcircuit]["O_qubit_product"][i]
                >= self.edge_var[subcircuit][i]
                + self.vertex_var[subcircuit][self.edges[i][0]]
                - 1,
                f"cons_edge_var_upstream_vertex_var_"
                f"{str(subcircuit)}_{str(i)}_3",
            )

        # Calculate the number of additional output qubits for each subcircuit
        self.model += (
            self.subcircuit_counter[subcircuit]["O"]
            - pulp.lpSum(
                self.subcircuit_counter[subcircuit]["O_qubit_product"]
            )
            == 0,
            f"cons_subcircuit_O_qubits_{str(subcircuit)}",
        )
        self.model += (
            self.subcircuit_counter[subcircuit]["d"]
            - self.subcircuit_counter[subcircuit]["original_input"]
            - self.subcircuit_counter[subcircuit]["rho"]
            == 0,
            f"cons_subcircuit_d_qubits_{str(subcircuit)}",
        )

    def _set_objective(self) -> None:
        """Set the objective for the MIP problem.

        A normal obejective for the MIP problem is the number of cuts.
        """
        obj = self.num_cuts
        self.model += (obj, "objective")

    def solve(self):
        """Solve the MIP model.

        Returns:
            Flag: bool denoting whether or not the model found a solution
            cut_edges: list[tuple[int, int]] denoting cut edges
        """
        self.model.solve(pulp.PULP_CBC_CMD(msg=0))
        if self.model.sol_status in (
            pulp.const.LpSolutionIntegerFeasible,
            pulp.const.LpSolutionOptimal,
        ):
            self.subcircuits = []
            self.optimal = (
                self.model.sol_status == pulp.const.LpSolutionOptimal
            )
            self.runtime = self.model.solutionTime

            for i in range(self.nsubcircuit):
                subcircuit = []
                for j in range(self.nvertex):
                    if abs(self.vertex_var[i][j].varValue) > 1e-4:
                        subcircuit.append(j)
                self.subcircuits.append(subcircuit)

            cut_edges_idx = []
            cut_edges = []
            for i in range(self.nsubcircuit):
                for j in range(self.nedge):
                    if (
                        abs(self.edge_var[i][j].value()) > 1e-4
                        and j not in cut_edges_idx
                    ):
                        cut_edges_idx.append(j)
                        cut_edges.append(self.edges[j])
            logger.info(
                f"Number of cutting edges: {len(cut_edges)}, "
                f"cut edges:{cut_edges}."
            )
            return True, cut_edges, self.subcircuits
        return False, None, None
