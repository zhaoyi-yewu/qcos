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

import math
import networkx as nx
from abc import ABC
from copy import deepcopy
from itertools import zip_longest
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

from wy_qcos.common.cmss.move import Move
from wy_qcos.transpiler.common.errors import MappingException
from wy_qcos.transpiler.cmss.mapping.na.zac.placer.saplacer import SAPlacer
from wy_qcos.transpiler.cmss.mapping.na.zac.placer.vmplacer import (
    VertexMatchingPlacer,
)


class NA_ZAC_Route(ABC):
    def __init__(self):
        self.qids = None
        self.mapping = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.operate_area = None
        self.storage_area = None
        self.qpu_config = None
        self.reuse = True
        self.dynamic_placement = True
        self.initial_layout = None

    def prepare_data(self, qbit_num, gates, qpu_configs):
        """Prepare QPU configuration, gates and qubit num, build topo graph.

        Description:
            This method sets up internal data structures:
            - stores qpu_config, storage and operate areas
            - constructs an adjacency graph (ag) restricted to operate_area
            - precomputes all-pairs shortest path lengths on the operate graph
            - initializes scheduling lists and result container

        Args:
            qbit_num(int): Number of logical qubits.
            gates(list): List of gate objects (IR).
            qpu_configs: QPU configuration. Expected keys:
                - "storage_area": iterable of storage locations
                - "operate_area": iterable of operate locations
                - "coupler_map": mapping of couplers
                - "readout_error": dict of readout errors (used later)

        Raises:
            MappingException: If storage area size is smaller than qbit_num.
        """
        self.qpu_config = qpu_configs
        self.storage_area = self.qpu_config["storage_area"]
        self.operate_area = self.qpu_config["operate_area"]

        # Build operate-area adjacency graph from coupler_map entries that
        # fall into operate_area
        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config["coupler_map"].items():
            if (a not in self.operate_area) or (b not in self.operate_area):
                continue
            self.ag.add_edge(a, b)
        # Precompute shortest path lengths on operate graph (Dijkstra)
        self.ag.shortest_length = dict(
            nx.shortest_path_length(
                self.ag,
                source=None,
                target=None,
                weight=None,
                method="dijkstra",
            )
        )

        self.gates = gates
        self.qbit_num = qbit_num
        if len(self.storage_area) < self.qbit_num:
            raise MappingException(
                f"not enough qubits, need {self.qbit_num}, "
                f"but only{len(self.operate_area)}"
            )
        # Lists used for gate/qubit scheduling and final result
        self.g_q = []
        self.g_op = []
        self.measure_op = []

        self.dict_g_1q_parent = {-1: []}
        self.mapping_res = []

        list_qubit_last_2q_gate = [-1 for i in range(0, self.qbit_num)]
        n_single_qubit_gate = 0

        for gate in self.gates:
            if len(gate.targets) == 2:
                self.g_op.append(gate)
                q0 = gate.targets[0]
                q1 = gate.targets[1]
                list_qubit_last_2q_gate[q0] = len(self.g_q)
                list_qubit_last_2q_gate[q1] = len(self.g_q)
                if q0 < q1:
                    self.g_q.append([q0, q1])
                else:
                    self.g_q.append([q1, q0])
            elif gate.name != "measure" and gate.name != "barrier":
                q0 = gate.targets[0]
                if list_qubit_last_2q_gate[q0] not in self.dict_g_1q_parent:
                    self.dict_g_1q_parent[list_qubit_last_2q_gate[q0]] = []
                self.dict_g_1q_parent[list_qubit_last_2q_gate[q0]].append((
                    gate.name,
                    q0,
                    gate,
                ))
                n_single_qubit_gate += 1
            elif gate.name == "measure":
                self.measure_op.append(gate)

    def scheduling(self):
        """ASAP scheduling (As-Soon-As-Possible) for the given gates IR.

        This scheduler groups gates into time stages respecting device
        constraints:

        - single-qubit gates can be scheduled on their qubit's
          earliest available time.
        - two-qubit gates need a pair of operate-area atoms (Rydberg
          pair),and the number of parallel two-qubit gates per stage is
          limited by the number of available operate-area coupler edges

        It builds:

        - self.gate_scheduling_list: list of gate-lists per stage

        Returns:
            list: list of measurement gate objects encountered (measure
            operations).
        """
        # Gate scheduling bits idx are used to determine the reuse bit
        self.gate_scheduling = []
        # Gate scheduling bits idx for 2-qubit and single-bit gates
        self.gate_1q_scheduling = []
        self.gate_2q_scheduling = []
        # ASAP scheduling 2-qubit and single-bit gates result
        self.gate_scheduling_list = []

        # Limit on simultaneously executable 2-qubit gates determined by
        # number of operate edges
        na_ryd_limit = len(self.ag.edges())

        # get 2-qubit gate asap scheduling result
        asap_scheduling_res = self.asap()

        # Adjust the ASAP scheduling results  according to the qpu_cfg
        gate_scheduling_idx = []
        for gates in asap_scheduling_res:
            if len(gates) < na_ryd_limit:
                gate_scheduling_idx.append(gates)
            else:
                num_layer = math.ceil(len(gates) / na_ryd_limit)
                gates_per_layer = math.ceil(len(gates) / num_layer)
                for i in range(0, len(gates), gates_per_layer):
                    gate_scheduling_idx.append(gates[i : i + gates_per_layer])

        # Determine the scheduling results of 2-qubit and single-bit gate
        # based on the ASAP scheduling result.
        for gates in gate_scheduling_idx:
            # Use for collect reuse qubit
            tmp = [self.g_q[i] for i in gates]
            self.gate_scheduling.append(tmp)

            tmp_gate = [self.g_op[i] for i in gates]
            self.gate_2q_scheduling.append(tmp_gate)
            self.gate_1q_scheduling.append([])

            for gate_idx in gates:
                if gate_idx in self.dict_g_1q_parent:
                    for gate_1q in self.dict_g_1q_parent[gate_idx]:
                        self.gate_1q_scheduling[-1].append(gate_1q[2])
        # collect gate scheduling list(2-bit and single-bit gates) for routing
        if self.dict_g_1q_parent[-1] != []:
            tmp_a = []
            for tmp in self.dict_g_1q_parent[-1]:
                tmp_a.append(tmp[2])
            self.gate_scheduling_list.append(tmp_a)
        else:
            self.gate_scheduling_list.append([])

        for item1, item2 in zip_longest(
            self.gate_2q_scheduling,
            self.gate_1q_scheduling,
            fillvalue=[],
        ):
            if item1 is not None:
                self.gate_scheduling_list.append(item1)
            if item2 is not None:
                self.gate_scheduling_list.append(item2)

    def asap(self):
        """Scheduling 2-bit gate use asap strategy."""
        # as soon as possible algorithm for two qubit gate in IR
        gate_2q_scheduling = []
        list_qubit_time = [0 for i in range(self.qbit_num)]
        for i, gate in enumerate(self.g_q):
            tq0 = list_qubit_time[gate[0]]
            tq1 = list_qubit_time[gate[1]]
            tg = max(tq0, tq1)

            if tg >= len(gate_2q_scheduling):
                gate_2q_scheduling.append([])
            gate_2q_scheduling[tg].append(i)

            tg += 1
            list_qubit_time[gate[0]] = tg
            list_qubit_time[gate[1]] = tg

        return gate_2q_scheduling

    def collect_reuse_qubit(self):
        """Collect reuse qubits.

        Description:
            Collect qubits that will remain in Rydberg zone between two
            Rydberg stages.
        """
        self.reuse_qubit = []
        if self.gate_scheduling == []:
            return self.reuse_qubit
        qubit_is_used = [
            [-1 for i in range(self.qbit_num)]
            for j in range(len(self.gate_scheduling))
        ]
        for gate_idx, gate in enumerate(self.gate_scheduling[0]):
            for q in gate:
                qubit_is_used[0][q] = gate_idx

        extra_reuse_qubit = 0
        for i in range(1, len(self.gate_scheduling)):
            self.reuse_qubit.append(set())
            matrix = [
                [0 for k in range(len(self.gate_scheduling[i - 1]))]
                for j in range(len(self.gate_scheduling[i]))
            ]
            for gate_idx, gate in enumerate(self.gate_scheduling[i]):
                if (
                    qubit_is_used[i - 1][gate[0]] != -1
                    and qubit_is_used[i - 1][gate[0]]
                    == qubit_is_used[i - 1][gate[1]]
                ):
                    self.reuse_qubit[-1].add(gate[0])
                    self.reuse_qubit[-1].add(gate[1])
                else:
                    for q in gate:
                        if qubit_is_used[i - 1][q] > -1:
                            matrix[gate_idx][qubit_is_used[i - 1][q]] = 1
                            extra_reuse_qubit += 1
                for q in gate:
                    qubit_is_used[i][q] = gate_idx

            sparse_matrix = csr_matrix(matrix)
            matching = maximum_bipartite_matching(
                sparse_matrix, perm_type="column"
            )
            for gate_idx, reuse_gate in enumerate(matching):
                if reuse_gate == -1:
                    continue
                extra_reuse_qubit -= 1
                gate = self.gate_scheduling[i][gate_idx]
                for q in gate:
                    if qubit_is_used[i - 1][q] == reuse_gate:
                        self.reuse_qubit[-1].add(q)

        self.extra_reuse_qubit = extra_reuse_qubit

        self.reuse_qubit.append(set())

    def routing_asap(self, mapping, measure):
        """Convert the mapping plan into a sequence of Move and gates.

        Description:
            For each stage (except initial), create Move operations for atoms
            whose positions changed compared to previous stage. Then insert
            scheduled gates for that stage and finally append measurement
            operations (with updated physical positions).

        Args:
            mapping (list[dict]): mapping plan across stages.
            measure (list): list of measurement gate objects collected
            during scheduling.

        Returns:
            mapping_res (list): list of operations(Move and gate objects)ready
            for execution.

        """
        pre_stage = None

        for stage_id, stage in enumerate(mapping):
            # For each stage, first add move to reach the stage atom positions,
            # then append the gates scheduled for that stage.
            # Skip the initial stage (no moves necessary)
            if stage_id == 0:
                pre_stage = stage
                for gate in self.gate_scheduling_list[stage_id]:
                    qid_list = gate.targets
                    for key, id in enumerate(qid_list):
                        gate.targets[key] = int(stage[id][1:])

                    self.mapping_res.append(gate)
                continue
            if stage == mapping[-1]:
                for gate in self.gate_scheduling_list[stage_id]:
                    qid_list = gate.targets
                    for key, id in enumerate(qid_list):
                        gate.targets[key] = int(pre_stage[id][1:])

                    self.mapping_res.append(gate)
                continue

            for key, value in stage.items():
                # position differs from previous stage, add a Move operation.
                # Prefer moving atoms in operate area first.

                # After ppend gates of that stage, moves for the stage.
                if value != pre_stage[key]:
                    self.mapping_res.append(
                        Move(
                            targets=[key],
                            arg_value=[
                                int(pre_stage[key][1:]),
                                int(value[1:]),
                            ],
                        )
                    )

            if self.gate_scheduling_list[stage_id] != []:
                for gate in self.gate_scheduling_list[stage_id]:
                    qid_list = gate.targets
                    for key, id in enumerate(qid_list):
                        gate.targets[key] = int(stage[id][1:])

                    self.mapping_res.append(gate)

            pre_stage = stage

        # Update measurement gates to the final physical positions of
        # logical qubits.
        for idx in range(len(measure)):
            qid = measure[idx].targets[0]
            if len(mapping) > 2:
                measure[qid].targets = [int(mapping[-2][qid][1:])]
            else:
                measure[qid].targets = [int(mapping[-1][qid][1:])]

        # Append measurement operations to final result list.
        self.mapping_res += measure

        return self.mapping_res

    def execute_with_order(self):
        """Run scheduling, mapping and routing to produce final op list.

        Description:
            Workflow:
                1. scheduling() to generate gate stages and measure ops
                2. collect_reuse_qubit() collect the reuse qubit for next stage
                3. SAPlacer.run() to find a inital mapping plan use sa
                4. VertexMatchingPlacer.run() to place qubit for every stage
                5. routing_asap() to create Move and gate execution sequence

        Returns:
            mapping_res(list): ordered list of operations (Move and gates) map-
            ping logical qubits to physical qpu positions ready for execution.
        """
        self.gate_scheduling = None
        self.gate_1q_scheduling = None
        self.reuse_qubit = None
        self.qubit_mapping = []

        self.scheduling()

        if self.reuse:
            self.collect_reuse_qubit()
        else:
            self.reuse_qubit = [
                set() for _ in range(len(self.gate_scheduling))
            ]

        # place qubit initial use sa.
        saplacer = SAPlacer()
        saplacer.run(self.qpu_config, self.qbit_num, self.gate_scheduling)
        self.qubit_mapping.append(saplacer.best_mapping)

        # place qubit intermedeiate.
        intermediate_placer = VertexMatchingPlacer(
            deepcopy(self.qubit_mapping[0]), self.ag, saplacer.near
        )
        intermediate_placer.run(
            self.qpu_config,
            self.qubit_mapping,
            self.gate_scheduling,
            self.dynamic_placement,
            self.reuse_qubit,
        )

        self.qubit_mapping = intermediate_placer.mapping

        mapping_res = self.routing_asap(self.qubit_mapping, self.measure_op)

        return mapping_res, None
