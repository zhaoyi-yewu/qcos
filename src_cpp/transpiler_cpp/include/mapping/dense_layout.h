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
 * 当 edge_fidelities 为空时，选区域阶段退化为纯密度优先策略；
 * 否则在密度优先的基础上，同时考虑边的保真度：
 * 子图的评分 = (内部边数, -错误得分)，优先选内部边多且错误率低的子图。
 *
 * @param gates_list 逻辑门序列
 * @param coupling_list 物理耦合边列表（有向）
 * @param edge_fidelities 与 coupling_list 对应的边保真度
 * @param num_logical 电路声明的逻辑比特总数
 * @return std::vector<int> 逻辑到物理映射
 */
std::vector<int> dense_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical);

}  // namespace qcos
