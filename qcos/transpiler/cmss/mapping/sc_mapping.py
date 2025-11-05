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
from qcos.transpiler.cmss.common.gate_operation import GateOperation
from qcos.transpiler.cmss.common.measure import Measure
from qcos.transpiler.cmss.common.base_operation import OperationType


class SCRoute(ABC):
    """超导设备路由映射类

    实现逻辑量子比特到物理量子比特的映射，支持单比特门和两比特门的路由。
    """

    def __init__(self):
        self.qids = None
        self.mapping = None
        self.qbit_num = None
        self.gates = None
        self.ag = None
        self.qpu_config = None

    def prepare_data(self, qbit_num, gates, qpu_configs):
        """配置qpu_config、gates、qbit_num，量子比特映射

        Args:
            qbit_num: 比特数
            gates: 门列表
            qpu_configs: 硬件拓扑配置（字典格式，包含 coupler_map, readout_error 等）
        """
        # 现在 qpu_configs 始终是字典格式（从服务器返回完整的 qpu_configs）
        if not isinstance(qpu_configs, dict):
            raise MappingException(
                f"Invalid qpu_configs type: {type(qpu_configs)}, "
                f"expected dict. Please ensure remote server returns "
                f"complete qpu_configs (dict format)."
            )

        self.qpu_config = qpu_configs.copy()
        self.gates = gates
        self.qbit_num = qbit_num

        # 构建硬件拓扑图
        self.ag = nx.Graph()
        coupler_map = self.qpu_config.get("coupler_map", {})
        for coupler_name, qubit_pair in coupler_map.items():
            if len(qubit_pair) == 2:
                q0, q1 = qubit_pair[0], qubit_pair[1]
                self.ag.add_edge(q0, q1)

        # 计算最短路径长度（用于路由）
        self.ag.shortest_length = dict(
            nx.shortest_path_length(
                self.ag,
                source=None,
                target=None,
                weight=None,
                method="dijkstra",
            )
        )

        # 获取所有可用的物理量子比特
        all_qubits = set()
        for coupler_name, qubit_pair in coupler_map.items():
            if len(qubit_pair) == 2:
                all_qubits.add(qubit_pair[0])
                all_qubits.add(qubit_pair[1])

        # 如果配置中有 qubits 字段，也添加对应的量子比特
        if "qubits" in self.qpu_config:
            num_qubits = self.qpu_config["qubits"]
            for i in range(num_qubits):
                all_qubits.add(f"Q{i}")

        # 检查是否有足够的量子比特
        available_qubits = list(all_qubits)
        if len(available_qubits) < self.qbit_num:
            raise MappingException(
                f"not enough qubits, need {self.qbit_num}, "
                f"but only {len(available_qubits)}"
            )

        # 根据 readout_error 选择最好的量子比特
        readout_error = self.qpu_config.get("readout_error", {})
        err_dict = {}
        for q in available_qubits:
            if q in readout_error:
                err_dict[q] = readout_error[q]
            else:
                # 如果没有错误率信息，使用默认值（较大的值）
                err_dict[q] = 1.0

        # 按错误率排序，选择错误率最低的量子比特
        sorted_qubits = sorted(err_dict.items(), key=lambda e: e[1])[
            : self.qbit_num
        ]

        # 创建逻辑到物理的映射
        # mapping: 逻辑比特索引 -> 物理比特名称（如 "Q0"）
        self.mapping = {i: q[0] for i, q in enumerate(sorted_qubits)}

        # qids: 物理比特索引列表（从 "Q0" 提取数字）
        self.qids = [int(q[0][1:]) for q in sorted_qubits]

    def execute_with_order(self):
        """遍历比特门，将逻辑量子比特映射到物理量子比特.

        Returns:
            从逻辑映射到物理量子比特的门列表
        """
        mapped_gates = []
        measures = []

        for gate in self.gates:
            # 处理测量操作
            if isinstance(gate, Measure):
                # 映射测量目标
                mapped_targets = []
                for logical_q in gate.targets:
                    # 确保逻辑量子比特索引是整数
                    logical_q_int = int(logical_q)
                    if logical_q_int in self.mapping:
                        physical_q = self.mapping[logical_q_int]
                        # 转换为数字索引（从 "Q0" 格式提取数字）
                        mapped_targets.append(int(physical_q[1:]))
                    else:
                        raise MappingException(
                            f"Logical qubit {logical_q_int} not in mapping. "
                            f"Available mappings: {list(self.mapping.keys())}"
                        )
                gate.targets = mapped_targets
                measures.append(gate)
                continue

            # 处理门操作
            if isinstance(gate, GateOperation):
                # 获取逻辑量子比特
                logical_targets = gate.targets
                operation_type = gate.operation_type

                if (
                    operation_type
                    == OperationType.SINGLE_QUBIT_OPERATION.value
                ):
                    # 单比特门：直接映射
                    if len(logical_targets) != 1:
                        raise MappingException(
                            f"Single qubit gate {gate.name} must have "
                            f"exactly 1 target, got {len(logical_targets)}"
                        )
                    # 确保逻辑量子比特索引是整数
                    logical_q = int(logical_targets[0])
                    if logical_q not in self.mapping:
                        raise MappingException(
                            f"Logical qubit {logical_q} not in mapping. "
                            f"Available mappings: {list(self.mapping.keys())}"
                        )
                    physical_q = self.mapping[logical_q]
                    # 转换为数字索引
                    gate.targets = [int(physical_q[1:])]
                    mapped_gates.append(gate)

                elif (
                    operation_type
                    == OperationType.DOUBLE_QUBIT_OPERATION.value
                ):
                    # 两比特门：映射并检查耦合约束
                    if len(logical_targets) != 2:
                        raise MappingException(
                            f"Two qubit gate {gate.name} must have "
                            f"exactly 2 targets, got {len(logical_targets)}"
                        )
                    # 确保逻辑量子比特索引是整数
                    logical_q0 = int(logical_targets[0])
                    logical_q1 = int(logical_targets[1])

                    if (
                        logical_q0 not in self.mapping
                        or logical_q1 not in self.mapping
                    ):
                        raise MappingException(
                            f"Logical qubits {logical_q0}, {logical_q1} "
                            f"not in mapping. Available mappings: "
                            f"{list(self.mapping.keys())}"
                        )
                    physical_q0 = self.mapping[logical_q0]
                    physical_q1 = self.mapping[logical_q1]

                    # 检查两个物理比特是否在拓扑中直接相连
                    if not self.ag.has_edge(physical_q0, physical_q1):
                        # 如果不在拓扑中直接相连，尝试找到最短路径
                        if (
                            physical_q0 in self.ag.shortest_length
                            and physical_q1
                            in self.ag.shortest_length[physical_q0]
                        ):
                            distance = self.ag.shortest_length[physical_q0][
                                physical_q1
                            ]
                            if distance > 1:
                                # 需要路由，但为了简化，这里先抛出异常
                                # 在实际应用中，可以插入 SWAP 门进行路由
                                raise MappingException(
                                    f"Physical qubits {physical_q0} and "
                                    f"{physical_q1} are not directly "
                                    f"connected (distance: {distance}). "
                                    f"Routing is required but not "
                                    f"implemented in this simple version."
                                )
                        else:
                            raise MappingException(
                                f"Physical qubits {physical_q0} and "
                                f"{physical_q1} are not connected in the "
                                f"topology graph."
                            )

                    # 转换为数字索引
                    gate.targets = [int(physical_q0[1:]), int(physical_q1[1:])]
                    mapped_gates.append(gate)

                else:
                    raise MappingException(
                        f"Unsupported operation type: {operation_type}"
                    )
            else:
                # 未知类型的操作
                raise MappingException(f"Unknown gate type: {type(gate)}")

        # 合并门和测量操作
        result = mapped_gates + measures
        return result
