#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from abc import ABC
import networkx as nx

from qcos.transpiler.common.errors import MappingException


class NASingleRoute(ABC):
    """NASingleRoute"""

    def __init__(self):
        self.qids = None
        self.mapping = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.operate_area = None
        self.storage_area = None
        self.qpu_config = None

    def prepare_data(self, qbit_num, gates, qpu_configs):
        """配置qpu_config、gates、qbit_num，量子比特映射

        Args:
            qbit_num: 比特数
            gates: 门列表
            qpu_configs: 拓扑
        """

        self.qpu_config = qpu_configs
        self.storage_area = self.qpu_config["storage_area"]
        self.operate_area = self.qpu_config["operate_area"]
        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config["coupler_map"].items():
            if (a not in self.operate_area) or (b not in self.operate_area):
                continue
            self.ag.add_edge(a, b)
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
                f"but only{len(self.storage_area)}"
            )

        err_dict = {}
        for k, v in self.qpu_config["readout_error"].items():
            if k in self.storage_area:
                err_dict[k] = v
        sq = sorted(err_dict.items(), key=lambda e: e[1])[: self.qbit_num]
        self.mapping = {a: b[0] for a, b in zip(range(self.qbit_num), sq)}
        self.qids = [int(q[0][1:]) for q in sq]

    def execute_with_order(self):
        """遍历比特门，将逻辑量子比特映射到物理量子比特.

        Returns:
            从逻辑映射到物理量子比特的门列表
        """

        gates_on_qubit = {}
        measure = []
        for gate in self.gates:
            assert len(gate.targets) == 1  # noqa: S101  # TODO: to be fixed
            gate.targets = [
                int(self.mapping[int(q)][1:]) for q in gate.targets
            ]
            if gate.name == "measure":
                measure.append(gate)
                continue
            if gate.targets[0] not in gates_on_qubit:
                gates_on_qubit[gate.targets[0]] = []
            gates_on_qubit[gate.targets[0]].append(gate)

        gates = []
        for value in gates_on_qubit.values():
            gates += value
        gates += measure
        return gates
