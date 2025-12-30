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
from loguru import logger

from qcos.transpiler.common.errors import MappingException


class SCRouting(ABC):
    """超导设备路由搜索类.

    负责执行基于蒙特卡罗树搜索的量子比特路由，插入SWAP门以满足硬件拓扑约束。
    """

    def __init__(self):
        self.selec_times = 50  # MCT搜索选择次数

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

    def execute_routing(
        self, search_tree, ag, initial_layout, num_q_vir, measure_ops
    ):
        """执行路由搜索，返回映射后的门列表.

        Args:
            search_tree: MCTree 搜索树实例
            ag: 架构图(Architecture Graph)
            initial_layout: 初始布局字典 {逻辑比特: 物理比特}
            num_q_vir: 虚拟量子比特数
            measure_ops: 测量操作列表

        Returns:
            mapped_ir: 映射后的门列表(包含插入的SWAP门和更新后的measure操作)
        """
        if search_tree is None:
            raise MappingException("search_tree cannot be None")
        if ag is None:
            raise MappingException("ag cannot be None")
        if initial_layout is None:
            raise MappingException("initial_layout cannot be None")

        # MCT搜索过程
        while search_tree.nodes[search_tree.root_node]["num_remain_gates"] > 0:
            while search_tree.selec_count < self.selec_times:
                # selection: 选择一个节点进行扩展
                exp_node, _ = search_tree.selection()
                # expansion: 扩展选中的节点
                search_tree.expansion(exp_node)
            # decision: 做出决策，选择最优路径
            search_tree.decision()

        # 生成映射后的依赖图
        dg_qct = search_tree.to_dg()
        dg_qct.num_q = max(list(ag.nodes)) + 1

        # 获取映射后的IR（分解SWAP门）
        mapped_ir = dg_qct.to_ir(decompose_swap=True)

        # 计算SWAP映射
        swaps = search_tree.get_swaps()

        # 初始化swap映射为恒等映射
        swap_mapping = list(range(max(list(ag.nodes)) + 1))

        logger.info(f"number of swaps: {len(swaps)}")
        logger.info(f"swap scheme: {swaps}")
        # 应用每个SWAP操作
        for swap in swaps:
            t0, t1 = swap_mapping[swap[0]], swap_mapping[swap[1]]
            swap_mapping[swap[0]], swap_mapping[swap[1]] = t1, t0

        # 反转映射：从物理比特到交换后的物理比特
        swap_mapping = self._layout_dict_reverse(
            self._layout_list_to_dict(swap_mapping)
        )

        # 确保swap_mapping是字典
        if not isinstance(swap_mapping, dict):
            raise MappingException(
                f"swap_mapping should be a dict, but got {type(swap_mapping)}"
            )

        # 计算虚拟比特到最终物理比特的映射
        mapping_virtual_to_final = {}
        for i in range(len(ag)):
            if i not in initial_layout:
                continue
            phy_q = initial_layout[i]
            # 确保phy_q是swap_mapping的键
            if phy_q in swap_mapping:
                mapping_virtual_to_final[i] = swap_mapping[phy_q]
            else:
                # 如果phy_q不在swap_mapping中，使用phy_q本身
                mapping_virtual_to_final[i] = phy_q

        # 删除冗余量子比特（超出虚拟比特数的部分）
        for q in list(initial_layout.keys()):
            if q >= num_q_vir:
                initial_layout.pop(q)
                if q in mapping_virtual_to_final:
                    mapping_virtual_to_final.pop(q)

        # 更新测量操作的目标比特
        for gate in measure_ops:
            gate.targets = [mapping_virtual_to_final[q] for q in gate.targets]
            mapped_ir.append(gate)

        logger.info(
            f"routing completed，mapped_ir contains {len(mapped_ir)} gates"
        )
        logger.info(f"final layout: {mapping_virtual_to_final}")

        return mapped_ir
