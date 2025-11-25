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

from abc import ABC
import networkx as nx
from loguru import logger

from qcos.transpiler.cmss.common.gate_operation import BaseOperation
from qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from qcos.transpiler.common.errors import MappingException
from qcos.transpiler.cmss.mapping.utils.dg import DG
from qcos.transpiler.cmss.mapping.routing.mt_tree import MCTree
from qcos.transpiler.cmss.mapping.initial_mapping.sc_initial_mapping import (
    get_initial_mapping,
)
from qcos.transpiler.cmss.mapping.routing.sc_routing import SCRouting


class SCRoute(ABC):
    """超导设备路由映射类

    实现逻辑量子比特到物理量子比特的映射，支持单比特门和两比特门的路由。
    """

    def __init__(self):
        self.qpu_config = None
        self.initial_layout = None
        self.qids = None
        self.mapping = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.dg = None
        self.measure_ops = None
        self.num_q_vir = None
        self.search_tree = None
        self.method_init_mapping = "topgraph"
        self.objective = "size"
        self.routing = SCRouting()  # 路由搜索实例

    def _layout_dict_to_list(self, layout_dict):
        """将布局字典转换为列表"""
        if not isinstance(layout_dict, dict):
            raise MappingException(
                f"layout_dict must be a dict, but got {type(layout_dict)}"
            )
        # 确保所有键都是整数
        int_keys = [k for k in layout_dict.keys() if isinstance(k, int)]
        if len(int_keys) == 0:
            raise MappingException(
                "layout_dict must have at least one integer key"
            )
        num_q_log = max(int_keys) + 1
        layout_list = [-1] * num_q_log
        for key in layout_dict.keys():
            if isinstance(key, int):
                layout_list[key] = layout_dict[key]
        return layout_list

    def _layout_list_to_dict(self, layout_list):
        """将布局列表转换为字典"""
        layout_dict = {}
        for i, v in enumerate(layout_list):
            layout_dict[i] = v
        return layout_dict

    def _layout_dict_reverse(self, layout_dict):
        """反转布局字典"""
        layout_dict_r = {v: k for k, v in layout_dict.items()}
        return layout_dict_r

    def _import_qpu_file(self, qpu_config, disable_qubits=[]):
        """硬件参数解析，获取一个包含耦合列表的字典

        Args:
            qpu_config: 硬件配置字典
            disable_qubits: 不可用比特列表. Defaults to [].
        """
        qpu_config_dice = {}
        if "coupler_map" not in qpu_config:
            raise MappingException("Cannot find 'coupler_map' in qpu_config")
        coupler_map = qpu_config["coupler_map"]
        adjacency_list = []
        if not isinstance(coupler_map, dict):
            raise MappingException(
                f"coupler_map must be a dict, but got {type(coupler_map)}"
            )
        # 如果是字典，遍历values
        for value in coupler_map.values():
            # value可能是元组、列表或其他结构
            if isinstance(value, (list, tuple)) and len(value) == 2:
                Q1, Q2 = value
            else:
                # 如果value不是预期的格式，跳过
                continue
            # 处理Q1和Q2可能是字符串（如"q0"）或整数的情况
            try:
                if isinstance(Q1, str) and len(Q1) > 1:
                    q1 = int(Q1[1:])
                elif isinstance(Q1, (int, float)):
                    q1 = int(Q1)
                else:
                    # 如果Q1不是预期的类型，跳过
                    continue
                if isinstance(Q2, str) and len(Q2) > 1:
                    q2 = int(Q2[1:])
                elif isinstance(Q2, (int, float)):
                    q2 = int(Q2)
                else:
                    # 如果Q2不是预期的类型，跳过
                    continue
            except (ValueError, TypeError, IndexError):
                # 如果转换失败，跳过这个条目
                continue
            if Q1 in disable_qubits or Q2 in disable_qubits:
                continue
            adjacency_list.append([q1, q2])
        qpu_config_dice["adjacency_list"] = adjacency_list
        return qpu_config_dice

    def _convert_gate_targets_to_int(self, gates):
        """确保门操作的目标索引为整数"""
        if not gates:
            return
        for gate in gates:
            if gate.targets is None:
                continue
            gate.targets = [int(q) for q in gate.targets]

    def prepare_data(
        self, qbit_num: int, gates: list[BaseOperation], qpu_configs: dict
    ):
        """准备数据，包括构建AG、DG等

        Args:
            qbit_num: 比特数
            gates: 门列表
            qpu_configs: 拓扑配置
        """
        self.qbit_num = qbit_num
        self.gates = gates
        self.qpu_config = qpu_configs
        # 解析QPU配置，获取耦合列表
        qpu_config_dice = self._import_qpu_file(self.qpu_config)
        adjacency_list = qpu_config_dice["adjacency_list"]

        # 检查并构建架构图(AG)
        if isinstance(adjacency_list, list):
            qubits = []
            for edge in adjacency_list:
                qubits.extend(edge)
                if not isinstance(edge[0], int) or not isinstance(
                    edge[1], int
                ):
                    raise MappingException(
                        "adjacency_list can only contain int"
                    )
            # 生成AG
            self.ag = nx.Graph()
            self.ag.add_edges_from(adjacency_list)
        elif isinstance(adjacency_list, nx.Graph):
            self.ag = adjacency_list
        else:
            raise MappingException(
                f"Unsupported adjacency_list type {adjacency_list}."
            )
        if not nx.is_connected(self.ag):
            raise MappingException("The adjacency_list is disconnected.")

        # 计算最短路径
        self.ag.shortest_length = dict(
            nx.shortest_path_length(
                self.ag,
                source=None,
                target=None,
                weight=None,
                method="dijkstra",
            )
        )
        self.ag.shortest_length_weight = self.ag.shortest_length
        self.ag.shortest_path = nx.shortest_path(
            self.ag, source=None, target=None, weight=None, method="dijkstra"
        )
        # 生成依赖图(DG)
        self.dg = DG()
        self.dg.num_q = qbit_num
        self.dg.num_q_log = qbit_num
        # 从gates构建DG，分离measure操作
        measure_ops = []
        non_measure_gates = []
        for gate in self.gates:
            if gate.name == "measure":
                measure_ops.append(gate)
            else:
                non_measure_gates.append(gate)

        # 保证所有门的目标索引为整数，避免后续处理时出现字符串下标
        self._convert_gate_targets_to_int(non_measure_gates)
        self._convert_gate_targets_to_int(measure_ops)
        # 使用from_ir方法构建DG
        qc = QuantumCircuit()
        qc.append_operations(non_measure_gates)
        self.measure_ops = self.dg.from_ir(qc, absorb=True)
        # 合并measure操作
        self.measure_ops.extend(measure_ops)
        self.num_q_vir = self.dg.num_q
        # 初始映射
        init_map = get_initial_mapping(
            self.dg, self.ag, self.method_init_mapping
        )
        logger.info(f"init_map: {init_map}")
        self.initial_layout = self._layout_list_to_dict(init_map)

        # 初始化搜索树
        select_mode = ["KS", 15]
        use_prune = 1
        use_hash = 1
        score_layer = 5

        init_map = self._layout_dict_to_list(self.initial_layout)
        self.search_tree = MCTree(
            self.ag,
            self.dg,
            objective=self.objective,
            select_mode=select_mode,
            score_layer=score_layer,
            use_prune=use_prune,
            use_hash=use_hash,
            init_mapping=init_map,
        )

    def execute_with_order(self):
        """执行映射，返回映射后的门列表

        Returns:
            映射后的门列表(mapped_ir)
        """
        if self.search_tree is None:
            raise MappingException(
                "prepare_data must be called before execute_with_order"
            )

        # 使用SCRouting执行路由搜索
        mapped_ir = self.routing.execute_routing(
            search_tree=self.search_tree,
            ag=self.ag,
            initial_layout=self.initial_layout,
            num_q_vir=self.num_q_vir,
            measure_ops=self.measure_ops,
        )
        return mapped_ir
