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
from loguru import logger

from wy_qcos.transpiler.common.errors import MappingException
from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE
from wy_qcos.transpiler.cmss.mapping.utils.dg import DG


class SABRERouting(ABC):
    """SABRE路由搜索包装类.

    负责执行基于SABRE算法的量子比特路由，插入SWAP门以满足硬件拓扑约束。
    该包装类使SABRE算法与SCRouting接口保持一致。
    """

    def __init__(
        self,
        extention_size: int = 20,
        weight: float = 0.5,
        decay: float = 0.001,
    ):
        """初始化SABRE路由算法.

        Args:
            extention_size: 扩展集大小，用于前瞻策略. Defaults to 20.
            weight: 用于组合基本和扩展启发式成本的权重参数.
                Defaults to 0.5.
            decay: 用于减少频繁交换量子比特影响的衰减因子.
                Defaults to 0.001.
        """
        self.extention_size = extention_size
        self.weight = weight
        self.decay = decay

    def _layout_list_to_dict(self, layout_list):
        """将布局列表转换为字典."""
        layout_dict = {}
        for i, v in enumerate(layout_list):
            layout_dict[i] = v
        return layout_dict

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

    def _dg_to_gates_list(self, dg: DG):
        """将DG转换为门列表.

        Args:
            dg: 依赖图

        Returns:
            门列表
        """
        # 使用to_ir方法将DG转换为IR（门列表）
        gates_list = dg.to_ir(decompose_swap=False)
        return gates_list

    def execute_routing(
        self, search_tree, ag, initial_layout, num_q_vir, measure_ops, dg=None
    ):
        """执行路由搜索，返回映射后的门列表.

        Args:
            search_tree: 未使用（为保持接口一致性保留）
            ag: 架构图(Architecture Graph)
            initial_layout: 初始布局字典 {逻辑比特: 物理比特}
            num_q_vir: 虚拟量子比特数
            measure_ops: 测量操作列表
            dg: 依赖图（可选，如果未提供则从search_tree获取）

        Returns:
            mapped_ir: 映射后的门列表(包含插入的SWAP门和更新后的measure操作)
        """
        if ag is None:
            raise MappingException("ag cannot be None")
        if initial_layout is None:
            raise MappingException("initial_layout cannot be None")

        # 获取DG：优先使用传入的dg，否则从search_tree获取
        if dg is None:
            if hasattr(self, "dg") and self.dg is not None:
                dg = self.dg
            elif search_tree is not None and hasattr(search_tree, "DG"):
                dg = search_tree.DG
            else:
                raise MappingException(
                    "dg must be provided or set before calling execute_routing"
                )

        # 将初始布局字典转换为列表
        initial_l2p = self._layout_dict_to_list(initial_layout)
        # 确保initial_l2p的长度不超过物理量子比特数
        max_phy_qubit = max(list(ag.nodes)) + 1
        if len(initial_l2p) > max_phy_qubit:
            initial_l2p = initial_l2p[:max_phy_qubit]

        # 从DG获取门列表
        gates_list = self._dg_to_gates_list(dg)

        # 初始化SABRE算法
        sabre = SABRE(
            coupling_graph=ag,
            extention_size=self.extention_size,
            weight=self.weight,
            decay=self.decay,
        )

        # 执行SABRE映射
        sabre.execute(gates_list, initial_l2p)

        # 获取映射后的门列表
        mapped_ir = sabre.phy_exe_gates

        # 获取最终映射
        logic2phy = sabre.logic2phy

        # 构建虚拟比特到最终物理比特的映射
        mapping_virtual_to_final = {}
        for logical_q in range(min(len(logic2phy), num_q_vir)):
            if logical_q < len(logic2phy):
                mapping_virtual_to_final[logical_q] = logic2phy[logical_q]

        # 更新测量操作的目标比特
        for gate in measure_ops:
            if gate.targets:
                gate.targets = [
                    mapping_virtual_to_final.get(q, q) for q in gate.targets
                ]
            mapped_ir.append(gate)

        logger.info(
            f"SABRE routing completed, "
            f"mapped_ir contains {len(mapped_ir)} gates"
        )
        logger.info(f"final layout: {mapping_virtual_to_final}")

        return mapped_ir
