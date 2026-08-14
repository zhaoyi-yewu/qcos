/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#pragma once

#include <stdexcept>
#include <utility>
#include <vector>

#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @brief 使用 DenseLayout 算法计算初始逻辑到物理映射。
 *
 * 分两步完成初始映射：
 * 1. DenseLayout选区域:
 * 在物理耦合图中找到与逻辑比特数相同、内部连接最密集的连通子图
 * 2. SABRE 精化排列：以选出的子图为起点，通过 SABRE forward-backward routing
 * 优化排列
 *
 * 子图评分采用加权综合评分：
 *   density_score  = edge_count / max_edge_count
 *   fidelity_score = 子图内边平均保真度
 *
 * fidelity_weight=0.5 密度与保真度各占0.5的权重；
 * fidelity_weight=0.0 退化为纯密度优先；
 * fidelity_weight=1.0 退化为纯保真度优先。
 *
 * @param gates_list 逻辑门序列
 * @param coupling_list 物理耦合边列表（有向）
 * @param edge_fidelities 与 coupling_list 对应的边保真度
 * @param num_logical 电路声明的逻辑比特总数
 * @param fidelity_weight 保真度权重，取值 [0, 1]，默认 0.5
 * @return std::vector<int> 逻辑到物理映射
 */
std::vector<int> dense_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical,
    double fidelity_weight = 0.5);

}  // namespace qcos
