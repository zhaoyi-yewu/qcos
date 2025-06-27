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


class NASingleRoute(ABC):
    """
    NASingleRoute
    """

    def __init__(self, qnum, gates, qpu_configs):
        """
        初始化，配置qpu_config、gates、qnum，量子比特映射

        :param qnum: 比特数
		:param gates: 门列表
		:param qpu_config: 拓扑
        """

        self.qpu_config = qpu_configs
        self.storage_area = self.qpu_config['storage_area']
        self.operate_area = self.qpu_config['operate_area']
        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config['coupler_map'].items():
            if (a not in self.operate_area) or (
                    b not in self.operate_area): continue
            self.ag.add_edge(a, b)
        self.ag.shortest_length = dict(
            nx.shortest_path_length(self.ag, source=None,
                                    target=None,
                                    weight=None,
                                    method='dijkstra'))

        self.gates = gates
        self.qnum = qnum
        if len(self.storage_area) < self.qnum:
            raise ValueError(
                f"not enough qubits, need {self.qnum}, "
                f"but only{len(self.storage_area)}")

        err_dict = {}
        for k, v in self.qpu_config['readout_error'].items():
            if k in self.storage_area:
                err_dict[k] = v
        sq = sorted(err_dict.items(), key=lambda e: e[1])[:self.qnum]
        self.mapping = dict([(a, b[0])
                             for a, b in zip(range(self.qnum), sq)])
        self.qids = [int(q[0][1:]) for q in sq]

    def execute_with_order(self):
        """
        遍历比特门，将逻辑量子比特映射到物理量子比特.

        :return: gates 从逻辑映射到物理量子比特的门列表
        """

        gates_on_qubit = {}
        measure = []
        for gate in self.gates:
            assert len(gate.targets) == 1
            gate.targets = [int(self.mapping[int(q)][1:])
                            for q in gate.targets]
            if gate.name == 'measure':
                measure.append(gate)
                continue
            if gate.targets[0] not in gates_on_qubit:
                gates_on_qubit[gate.targets[0]] = []
            gates_on_qubit[gate.targets[0]].append(gate)

        gates = []
        for q in gates_on_qubit:
            gates += gates_on_qubit[q]
        gates += measure
        return gates
