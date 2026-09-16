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

#include <vector>

#include "circuit/gate_operation.h"
#include "mapping/sabre_routing.h"

namespace qcos {

/**
 * @brief 使用 SABRE forward-backward routing 计算初始逻辑到物理映射。
 *
 * 从 initial_layout 出发，通过正向路由得到末尾排列，
 * 再反转门序列反向路由，得到更优的初始映射。
 *
 * @param gates_list 逻辑门序列
 * @param coupling_list 物理耦合边列表
 * @param initial_layout 起始映射（如 DenseLayout 选区域结果），空则从零开始
 * @return std::vector<int> 逻辑到物理映射
 */
std::vector<int> sabre_initial_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<int>& initial_layout = {});

}  // namespace qcos
