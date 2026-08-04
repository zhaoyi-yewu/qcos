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
 *      WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#pragma once

#include <utility>
#include <vector>

#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @brief 使用 VF2 子图同构算法计算初始逻辑到物理映射。
 *
 * 将电路的两比特门交互图作为 needle，物理耦合图作为 haystack，
 * 通过子图单态(subgraph monomorphism)搜索完美嵌入。
 * 找到完美嵌入意味着电路中所有两比特门均可在拓扑上直接执行，
 * 无需任何 SWAP。
 *
 * 当存在多个有效嵌入时，选择保真度最高(错误率最低)的映射。
 * 找不到完美嵌入时返回空 vector，调用方可回退到 DenseLayout。
 *
 * @param gates_list 逻辑门序列
 * @param coupling_list 物理耦合边列表（有向，内部按无向处理）
 * @param edge_fidelities 与 coupling_list 对应的边保真度，空则不使用保真度评分
 * @param num_logical 电路声明的逻辑比特总数
 * @return std::vector<int> 逻辑到物理映射，空表示未找到完美嵌入
 */
std::vector<int> vf2_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical);

}  // namespace qcos
