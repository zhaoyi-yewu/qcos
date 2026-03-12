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

import numpy as np
import networkx as nx

from copy import deepcopy
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import min_weight_full_bipartite_matching


class VertexMatchingPlacer:
    """Class to determine qubit layout using vertex matching.

    Description:
        This placer computes qubit-to-site mappings across circuit layers
        by solving a sequence of minimum-weight bipartite matching problems.
        It supports dynamic placement, qubit reuse, and lookahead-based
        cost estimation for neutral-atom architectures.
    """

    def __init__(self, mapping: list, ag: nx.Graph, near: dict):
        """Initialize the vertex matching placer.

        Args:
            mapping (list): Initial logical-to-physical qubit mapping.
            ag (nx.Graph): Adjacency graph of Rydberg interaction sites.
            near (dict): Mapping from Rydberg site to nearest storage site.
        """
        self.mapping = [mapping]
        self.n_qubit = len(mapping)
        self.ag = ag
        self.near = near
        # penalty factor for atom movement
        self.cost_atom_transfer = 0.9999

    def run(
        self,
        qpu_cfg,
        qubit_mapping,
        list_gate,
        dynamic_placement,
        list_reuse_qubits,
    ):
        """Run the placement algorithm layer by layer.

        Description:
            For each circuit layer, this method alternates between
            placing two-qubit gates onto Rydberg sites and placing idle
            qubits back to storage sites. Both dynamic placement and
            qubit reuse are supported.

        Args:
            qpu_cfg (dict):
                Hardware configuration, including:
                - storage_area: list of storage site IDs
                - operate_area: list of Rydberg site IDs
                - coupler_map: mapping from Rydberg coupler to site pairs

            qubit_mapping (dict):
                Initial logical-to-physical mapping at layer 0.

            list_gate (list[list[tuple]]):
                Circuit gates grouped by layer.
                list_gate[l] = [(q0, q1), ...] for layer l.

            dynamic_placement (bool):
                Whether qubits are allowed to move between layers.
                - True: dynamic remapping each layer
                - False: static placement

            list_reuse_qubits (list[list[int]]):
                For each layer, list of qubits reused in the next layer.
        """
        self.qpu_cfg = qpu_cfg
        self.list_reuse_qubit = list_reuse_qubits

        # trivial cases
        if len(list_gate) == 0:
            return
        elif len(list_gate) == 1:
            self.place_gate(qubit_mapping, list_gate, 0, False)
            self.place_qubit(list_gate[0:], 0, False)
            return

        # place first gate layer
        self.place_gate(qubit_mapping, list_gate[0:2], 0, False)

        for layer in range(len(list_gate)):
            # the case that don't reuse qubits
            if dynamic_placement:
                self.place_qubit(list_gate[layer:], layer, False)
            else:
                self.mapping.append(
                    deepcopy(self.mapping[0])
                )  # keep the initial mapping for static placement

            if layer + 1 < len(list_gate):
                self.place_gate(
                    self.mapping[-2:],
                    list_gate[layer + 1 : layer + 3],
                    layer + 1,
                    False,
                )
            # the case that reuse qubits
            if len(list_reuse_qubits[layer]) > 0:
                if dynamic_placement:
                    self.place_qubit(list_gate[layer:], layer, True)
                else:
                    self.mapping.append(
                        deepcopy(self.mapping[0])
                    )  # keep the initial mapping for static placement
                    for q in list_reuse_qubits[layer]:
                        self.mapping[-1][q] = self.mapping[-4][q]
                if layer + 1 < len(list_gate):
                    self.place_gate(
                        [self.mapping[-4], self.mapping[-1]],
                        list_gate[layer + 1 : layer + 3],
                        layer + 1,
                        True,
                    )
                    # keep the mapping with shorter distance
                    self.filter_mapping(layer)

    def filter_mapping(self, layer):
        """Compare reuse vs non-reuse mappings and keep the better one."""
        # cost for mapping without reuse
        last_gate_mapping = self.mapping[-5]
        qubit_mapping = self.mapping[-4]
        gate_mapping = self.mapping[-3]
        cost_no_reuse = 0

        for q_id, _ in enumerate(last_gate_mapping):
            cost_no_reuse += self.get_steps(
                last_gate_mapping[q_id], qubit_mapping[q_id]
            )
            cost_no_reuse += self.get_steps(
                qubit_mapping[q_id], gate_mapping[q_id]
            )

        # cost for mapping with reuse
        gate_mapping = self.mapping[-1]
        qubit_mapping = self.mapping[-2]
        cost_reuse = 0

        for q_id, _ in enumerate(last_gate_mapping):
            cost_reuse += self.get_steps(
                last_gate_mapping[q_id], qubit_mapping[q_id]
            )
            cost_reuse += self.get_steps(
                qubit_mapping[q_id], gate_mapping[q_id]
            )

        # compare transfer fidelity-like objective
        if self.cost_atom_transfer * pow(
            (1 - cost_no_reuse / 1.5e6), self.n_qubit
        ) > pow((1 - cost_reuse / 1.5e6), self.n_qubit):
            # discard reuse mapping
            self.list_reuse_qubit[layer] = []
            self.mapping.pop(-1)
            self.mapping.pop(-1)
        else:
            # discard non-reuse mapping
            self.mapping.pop(-3)
            self.mapping.pop(-3)

    def place_gate(
        self,
        list_qubit_mapping: list,
        list_two_gate_layer: list,
        layer: int,
        test_reuse: bool,
    ):
        """Place two-qubit gates onto Rydberg sites using bipartite matching.

        Description:
            Each gate is matched to a Rydberg site pair by minimizing
            total atom movement distance, optionally prioritizing
            qubit reuse.

        Args:
            list_qubit_mapping (list[dict]):
                Previous mapping(s):
                - layer == 0: [mapping]
                - otherwise: [gate_mapping, qubit_mapping]
            list_two_gate_layer (list[list[tuple]]):
                Current and (optional) next gate layer.
            layer (int):Current circuit layer index.
            test_reuse (bool):Whether qubit reuse is enforced in placement.
        """
        list_gate = list_two_gate_layer[0]
        dict_reuse_qubit_neighbor = dict()

        # record neighbors of reused qubits in the next layer
        if len(list_two_gate_layer) > 1 and test_reuse:
            for q in self.list_reuse_qubit[layer]:
                for gate in list_two_gate_layer[1]:
                    if q == gate[0]:
                        dict_reuse_qubit_neighbor[q] = gate[1]
                        break
                    elif q == gate[1]:
                        dict_reuse_qubit_neighbor[q] = gate[0]
                        break

        if layer > 0:
            gate_mapping = list_qubit_mapping[0]
            qubit_mapping = list_qubit_mapping[1]
        else:
            qubit_mapping = list_qubit_mapping[0]

        # COO matrix construction for bipartite matching
        site_Rydberg_to_idx = dict()
        list_Rydberg = []
        list_row_coo = []
        list_col_coo = []
        list_data = []

        for i, gate in enumerate(list_gate):
            q1, q2 = gate
            set_nearby_site = set()

            # === reuse case: fix one qubit if possible ===
            if test_reuse and (q1 in self.list_reuse_qubit[layer - 1]):
                location = gate_mapping[q1]
                neighbor = list(self.ag.neighbors(location))
                if location < neighbor[0]:
                    tmp = (location, neighbor[0])
                else:
                    tmp = (neighbor[0], location)
                set_nearby_site.add(tmp)

            elif test_reuse and (q2 in self.list_reuse_qubit[layer - 1]):
                location = gate_mapping[q2]
                neighbor = list(self.ag.neighbors(location))
                if location < neighbor[0]:
                    tmp = (location, neighbor[0])
                else:
                    tmp = (neighbor[0], location)
                set_nearby_site.add(tmp)
            else:
                # normal case: all coupler sites are candidates
                for k, (a, b) in self.qpu_cfg["coupler_map"].items():
                    set_nearby_site.add((a, b))

            for site in set_nearby_site:
                if site not in site_Rydberg_to_idx:
                    site_Rydberg_to_idx[site] = len(list_Rydberg)
                    list_Rydberg.append(site)

                idx_rydberg = site_Rydberg_to_idx[site]

                dis1, change = self.get_site_cost(
                    site,
                    gate,
                    qubit_mapping,
                )
                if change:
                    list_Rydberg[idx_rydberg] = (site[1], site[0])

                # lookahead cost for reused neighbor
                dis2 = 0
                q3 = -1
                if q1 in dict_reuse_qubit_neighbor:
                    q3 = dict_reuse_qubit_neighbor[q1]
                elif q2 in dict_reuse_qubit_neighbor:
                    q3 = dict_reuse_qubit_neighbor[q2]
                if q3 > -1:
                    dis2 = min(
                        self.get_steps(qubit_mapping[q3], site[0]),
                        self.get_steps(qubit_mapping[q3], site[1]),
                    )
                list_row_coo.append(idx_rydberg)
                list_col_coo.append(i)

                # prevent zero weights are removed before matching
                list_data.append(max(dis1 + dis2, 1e-10))

        np_data = np.array(list_data)
        np_col_coo = np.array(list_col_coo)
        np_row_coo = np.array(list_row_coo)
        matrix = coo_matrix(
            (np_data, (np_row_coo, np_col_coo)),
            shape=(len(list_Rydberg), len(list_gate)),
        )

        # solve minimal matching by scipy
        site_ind, gate_ind = min_weight_full_bipartite_matching(matrix)

        # update mapping according to matching result
        tmp_mapping = deepcopy(qubit_mapping)
        for idx_rydberg, idx_gate in zip(site_ind, gate_ind):
            q0 = list_gate[idx_gate][0]
            q1 = list_gate[idx_gate][1]
            site = list_Rydberg[idx_rydberg]

            if test_reuse and (q0 in self.list_reuse_qubit[layer - 1]):
                tmp_mapping[q0] = gate_mapping[q0]
                if site[0] == gate_mapping[q0]:
                    tmp_mapping[q1] = site[1]
                else:
                    tmp_mapping[q1] = site[0]
            elif test_reuse and (q1 in self.list_reuse_qubit[layer - 1]):
                tmp_mapping[q1] = gate_mapping[q1]
                if site[0] == gate_mapping[q1]:
                    tmp_mapping[q0] = site[1]
                else:
                    tmp_mapping[q0] = site[0]
            else:
                tmp_mapping[q0] = site[0]
                tmp_mapping[q1] = site[1]

        self.mapping.append(tmp_mapping)

    def get_steps(self, posa, posb):
        """Compute Manhattan distance between two physical sites."""
        pre_na_id = int(posa[1:])
        pre_coordinate = (int(pre_na_id / 20), pre_na_id % 20)

        na_id = int(posb[1:])
        coordinate = (int(na_id / 20), na_id % 20)

        return abs(pre_coordinate[0] - coordinate[0]) + abs(
            pre_coordinate[1] - coordinate[1]
        )

    def get_site_cost(self, site, gate, qubit_mapping):
        """Compute minimal assignment cost for a gate on a Rydberg site."""
        dis1_a = self.get_steps(qubit_mapping[gate[0]], site[0])
        dis1_b = self.get_steps(qubit_mapping[gate[0]], site[1])
        dis2_a = self.get_steps(qubit_mapping[gate[1]], site[0])
        dis2_b = self.get_steps(qubit_mapping[gate[1]], site[1])

        if dis1_a + dis2_b > dis1_b + dis2_a:
            return dis1_b + dis2_a, True
        else:
            return dis1_a + dis2_b, False

    def place_qubit(self, list_gate: list, layer: int, test_reuse: bool):
        """Place idle qubits back to storage sites using matching.

        Args:
            list_gate (list):The gate list to placement.
            layer (int):Current circuit layer index.
            test_reuse (bool):Whether qubit reuse is enforced in placement.
        """
        qubit_mapping = self.mapping[0]
        if test_reuse:
            last_gate_mapping = self.mapping[-3]
        else:
            last_gate_mapping = self.mapping[-1]

        is_empty_storage_site = dict()

        qubit_to_place = []
        for pos in self.qpu_cfg["storage_area"]:
            is_empty_storage_site[pos] = True

        # mark occupied storage sites
        for q, _ in enumerate(last_gate_mapping):
            pos_q = last_gate_mapping[q]

            if pos_q in is_empty_storage_site:
                is_empty_storage_site[pos_q] = False

            elif (not test_reuse) or (q not in self.list_reuse_qubit[layer]):
                qubit_to_place.append(q)

        # common sites from initial mapping
        common_site = set()
        for q, _ in enumerate(self.mapping[0]):
            pos_q = self.mapping[0][q]
            if pos_q in is_empty_storage_site:
                if is_empty_storage_site[pos_q]:
                    common_site.add(pos_q)
            else:
                is_empty_storage_site[pos_q] = True
                common_site.add(pos_q)

        # record future interactions for lookahead
        dict_qubit_interaction = dict()
        for q in qubit_to_place:
            dict_qubit_interaction[q] = []

        if len(list_gate) > 1:
            for gate in list_gate[1]:
                if gate[0] in dict_qubit_interaction and (
                    (not test_reuse)
                    or (gate[1] not in self.list_reuse_qubit[layer])
                ):
                    dict_qubit_interaction[gate[0]].append(gate[1])
                if gate[1] in dict_qubit_interaction and (
                    (not test_reuse)
                    or (gate[0] not in self.list_reuse_qubit[layer])
                ):
                    dict_qubit_interaction[gate[1]].append(gate[0])

        # construct bipartite matching matrix
        site_storage_to_idx = dict()
        list_storage = []
        list_row_coo = []
        list_col_coo = []
        list_data = []

        for i, q in enumerate(qubit_to_place):
            # add qubit's original location to the site candidate
            set_nearby_site = deepcopy(common_site)
            if is_empty_storage_site[qubit_mapping[q]]:
                set_nearby_site.add(qubit_mapping[q])

            # consider the nearest storage site for the rydberg
            gate_location = last_gate_mapping[q]

            # # local neighborhood with 4 distance
            near_rydberg_pos = self.near[gate_location]
            id = int(near_rydberg_pos[1:])
            row_id = int(id / 20)
            col_id = int(id % 20)

            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    if dx == 0 and dy == 0:
                        continue
                    if abs(dx) + abs(dy) <= 2:
                        qid = "P" + str((dx + row_id) * 20 + (col_id + dy))
                        if (
                            qid in self.qpu_cfg["storage_area"]
                            and is_empty_storage_site[qid]
                        ):
                            set_nearby_site.add(qid)

            # The positions of atoms that may interact in the future
            for neighbor_q in dict_qubit_interaction[q]:
                neighbor_q_pos = last_gate_mapping[neighbor_q]
                # If the neighbor is in Rydberg,map to nearest storage site
                if qid in self.qpu_cfg["operate_area"]:
                    neighbor_q_pos = self.near[neighbor_q_pos]

                # Looking for storage locations that are near each other
                # and available
                nb_id = int(neighbor_q_pos[1:])
                nb_row_id = int(nb_id / 20)
                nb_col_id = int(nb_id % 20)
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if dx == 0 and dy == 0:
                            continue
                        if abs(dx) + abs(dy) <= 1:
                            qid = "P" + str(
                                (dx + nb_row_id) * 20 + (nb_col_id + dy)
                            )
                            if (
                                qid in self.qpu_cfg["storage_area"]
                                and is_empty_storage_site[qid]
                            ):
                                set_nearby_site.add(qid)

            for site in set_nearby_site:
                if site not in site_storage_to_idx:
                    site_storage_to_idx[site] = len(list_storage)
                    list_storage.append(site)
                idx_storage = site_storage_to_idx[site]
                # calculate cost
                dis = self.get_steps(gate_location, site)
                lookahead_cost = 0
                for neighbor_q in dict_qubit_interaction[q]:
                    site_neighbor_q = last_gate_mapping[neighbor_q]
                    lookahead_cost += self.get_steps(site_neighbor_q, site)
                cost = dis + 0.1 * lookahead_cost
                list_row_coo.append(idx_storage)
                list_col_coo.append(i)
                list_data.append(cost)

        np_data = np.array(list_data)
        np_col_coo = np.array(list_col_coo)
        np_row_coo = np.array(list_row_coo)
        matrix = coo_matrix(
            (np_data, (np_row_coo, np_col_coo)),
            shape=(len(list_storage), len(qubit_to_place)),
        )
        # solve minimal matching by scipy
        site_ind, qubit_ind = min_weight_full_bipartite_matching(matrix)
        cost = matrix.toarray()[site_ind, qubit_ind].sum()
        # process the solution
        tmp_mapping = deepcopy(last_gate_mapping)

        for idx_storage, idx_qubit in zip(site_ind, qubit_ind):
            tmp_mapping[qubit_to_place[idx_qubit]] = list_storage[idx_storage]

        self.mapping.append(tmp_mapping)
