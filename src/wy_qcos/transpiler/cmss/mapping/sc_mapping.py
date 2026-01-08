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

from abc import ABC
import networkx as nx
from loguru import logger
from schema import And, Optional, Or

from wy_qcos.transpiler.cmss.common.gate_operation import BaseOperation
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.common.errors import MappingException
from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.transpiler.cmss.mapping.routing.mcts_routing import MCTree
from wy_qcos.transpiler.cmss.mapping.init_mapping.sc_initial_mapping import (
    get_initial_mapping,
)
from wy_qcos.transpiler.cmss.mapping.routing.sc_routing import (
    SCRoutingFactory,
)

# 默认 sc_mapping 配置参数
DEFAULT_SC_MAPPING_OPTIONS = {
    # 路由算法: "mct" (蒙特卡罗树搜索) 或 "sabre" (SABRE算法)
    "routing_algorithm": "mct",
    # 选择模式: ["KS", K值] 或其他模式
    "select_mode": ["KS", 15],
    # 是否启用剪枝
    "use_prune": 1,
    # 是否启用哈希
    "use_hash": 1,
    # 评分层数
    "score_layer": 5,
    # 模拟模式: ["fix_cx_num", [N_sim, G_sim]]
    "mode_sim": ["fix_cx_num", [500, 30]],
    # 大小评分衰减率
    "score_decay_rate_size": 0.7,
    # 深度评分衰减率
    "score_decay_rate_depth": 0.85,
    # SABRE算法参数
    "sabre_extention_size": 20,
    "sabre_weight": 0.5,
    "sabre_decay": 0.001,
}

# sc_mapping 配置选项的 schema（用于参数验证）
SC_MAPPING_OPTIONS_SCHEMA = {
    # 路由算法: "mct", "sc" 或 "sabre"
    Optional("routing_algorithm"): Or("mct", "sc", "sabre"),
    # 选择模式: ["KS", K值] 或其他模式
    Optional("select_mode"): And(list, lambda x: len(x) == 2),
    # 是否启用剪枝 (0 或 1)
    Optional("use_prune"): Or(0, 1),
    # 是否启用哈希 (0 或 1)
    Optional("use_hash"): Or(0, 1),
    # 评分层数
    Optional("score_layer"): And(int, lambda x: x > 0),
    # 模拟模式: ["fix_cx_num", [N_sim, G_sim]]
    Optional("mode_sim"): And(list, lambda x: len(x) == 2),
    # 大小评分衰减率 (0-1 之间)
    Optional("score_decay_rate_size"): And(
        Or(int, float), lambda x: 0 <= x <= 1
    ),
    # 深度评分衰减率 (0-1 之间)
    Optional("score_decay_rate_depth"): And(
        Or(int, float), lambda x: 0 <= x <= 1
    ),
    # SABRE算法参数
    Optional("sabre_extention_size"): And(int, lambda x: x > 0),
    Optional("sabre_weight"): And(Or(int, float), lambda x: 0 <= x <= 1),
    Optional("sabre_decay"): And(Or(int, float), lambda x: 0 <= x <= 1),
}


class SCRoute(ABC):
    """超导设备路由映射类.

    实现逻辑量子比特到物理量子比特的映射，支持单比特门和两比特门的路由。
    """

    # 默认 sc_mapping 配置参数（引用模块级常量）
    DEFAULT_SC_MAPPING_OPTIONS = DEFAULT_SC_MAPPING_OPTIONS

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
        self.routing = None  # 路由搜索实例，将在prepare_data中根据参数创建
        # sc_mapping 配置选项
        self.sc_mapping_options = DEFAULT_SC_MAPPING_OPTIONS.copy()

    def set_sc_mapping_options(self, options: dict):
        """设置 sc_mapping 配置选项.

        Args:
            options: sc_mapping 配置选项字典
        """
        if options:
            self.sc_mapping_options.update(options)

    def _create_routing(self):
        """根据配置选项创建路由算法实例."""
        routing_algorithm = self.sc_mapping_options.get(
            "routing_algorithm",
            DEFAULT_SC_MAPPING_OPTIONS["routing_algorithm"],
        )

        # 提取所有路由算法参数
        routing_kwargs = {}

        # SABRE算法参数
        if routing_algorithm == "sabre":
            routing_kwargs["extention_size"] = self.sc_mapping_options.get(
                "sabre_extention_size",
                DEFAULT_SC_MAPPING_OPTIONS["sabre_extention_size"],
            )
            routing_kwargs["weight"] = self.sc_mapping_options.get(
                "sabre_weight",
                DEFAULT_SC_MAPPING_OPTIONS["sabre_weight"],
            )
            routing_kwargs["decay"] = self.sc_mapping_options.get(
                "sabre_decay",
                DEFAULT_SC_MAPPING_OPTIONS["sabre_decay"],
            )
        # MCTS算法参数（如果需要，可以在这里添加 selec_times 等参数）

        # 统一使用工厂方法创建路由实例
        self.routing = SCRoutingFactory.create_routing(
            routing_algorithm=routing_algorithm,
            **routing_kwargs,
        )

    def _layout_dict_to_list(self, layout_dict):
        """将布局字典转换为列表."""
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
        """将布局列表转换为字典."""
        layout_dict = {}
        for i, v in enumerate(layout_list):
            layout_dict[i] = v
        return layout_dict

    def _layout_dict_reverse(self, layout_dict):
        """反转布局字典."""
        layout_dict_r = {v: k for k, v in layout_dict.items()}
        return layout_dict_r

    def _import_qpu_file(self, qpu_config, disable_qubits=[]):
        """硬件参数解析，获取一个包含耦合列表的字典.

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
        """确保门操作的目标索引为整数."""
        if not gates:
            return
        for gate in gates:
            if gate.targets is None:
                continue
            gate.targets = [int(q) for q in gate.targets]

    def prepare_data(
        self, qbit_num: int, gates: list[BaseOperation], qpu_configs: dict
    ):
        """准备数据，包括构建AG、DG等.

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

        # 初始化搜索树，从 sc_mapping_options 获取配置
        opts = self.sc_mapping_options
        select_mode = opts.get(
            "select_mode", DEFAULT_SC_MAPPING_OPTIONS["select_mode"]
        )
        use_prune = opts.get(
            "use_prune", DEFAULT_SC_MAPPING_OPTIONS["use_prune"]
        )
        use_hash = opts.get("use_hash", DEFAULT_SC_MAPPING_OPTIONS["use_hash"])
        score_layer = opts.get(
            "score_layer", DEFAULT_SC_MAPPING_OPTIONS["score_layer"]
        )
        mode_sim = opts.get("mode_sim", DEFAULT_SC_MAPPING_OPTIONS["mode_sim"])
        score_decay_rate_size = opts.get(
            "score_decay_rate_size",
            DEFAULT_SC_MAPPING_OPTIONS["score_decay_rate_size"],
        )
        score_decay_rate_depth = opts.get(
            "score_decay_rate_depth",
            DEFAULT_SC_MAPPING_OPTIONS["score_decay_rate_depth"],
        )

        # 根据配置创建路由算法实例
        self._create_routing()

        # 对于SABRE算法，不需要创建MCTree
        routing_algorithm = self.sc_mapping_options.get(
            "routing_algorithm",
            DEFAULT_SC_MAPPING_OPTIONS["routing_algorithm"],
        )
        if routing_algorithm in ("mct", "sc"):
            init_map = self._layout_dict_to_list(self.initial_layout)
            args = {
                "objective": self.objective,
                "select_mode": select_mode,
                "score_layer": score_layer,
                "use_prune": use_prune,
                "use_hash": use_hash,
                "init_mapping": init_map,
                "mode_sim": mode_sim,
                "score_decay_rate_size": score_decay_rate_size,
                "score_decay_rate_depth": score_decay_rate_depth,
            }
            self.search_tree = MCTree(
                self.ag,
                self.dg,
                **args,
            )
        else:
            # SABRE算法不需要search_tree
            self.search_tree = None

    def execute_with_order(self):
        """执行映射，返回映射后的门列表.

        Returns:
            映射后的门列表(mapped_ir)
        """
        if self.routing is None:
            raise MappingException(
                "prepare_data must be called before execute_with_order"
            )

        routing_algorithm = self.sc_mapping_options.get(
            "routing_algorithm",
            DEFAULT_SC_MAPPING_OPTIONS["routing_algorithm"],
        )

        # 对于MCT算法，需要search_tree
        if routing_algorithm in ("mct", "sc"):
            if self.search_tree is None:
                raise MappingException(
                    "search_tree must be initialized for MCT routing algorithm"
                )
            # 使用SCRouting执行路由搜索
            mapped_ir = self.routing.execute_routing(
                search_tree=self.search_tree,
                ag=self.ag,
                initial_layout=self.initial_layout,
                num_q_vir=self.num_q_vir,
                measure_ops=self.measure_ops,
            )
        else:
            # 对于SABRE算法，传递dg参数
            # self.routing 在 else 分支中一定是 SABRERouting 实例
            # pylint: disable-next=unexpected-keyword-arg
            mapped_ir = self.routing.execute_routing(
                search_tree=self.search_tree,
                ag=self.ag,
                initial_layout=self.initial_layout,
                num_q_vir=self.num_q_vir,
                measure_ops=self.measure_ops,
                dg=self.dg,
            )
        return mapped_ir
