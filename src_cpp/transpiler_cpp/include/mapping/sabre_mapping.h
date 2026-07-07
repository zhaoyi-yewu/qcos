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
 * @brief 选择耦合图的最大连通分量
 *
 * 通过 BFS 找出所有连通分量，只保留节点数最多的那个分量。
 *
 * @param coupling_list [in/out] 耦合边列表，原地过滤为最大连通分量
 * @param edge_fidelities [in/out] 边保真度列表，与 coupling_list 同步过滤
 */
void select_largest_component(std::vector<std::pair<int, int>>& coupling_list,
                              std::vector<double>& edge_fidelities);

/**
 * @brief Compute an initial logical->physical mapping using SABRE heuristic.
 * @param gates_list logical gate sequence
 * @param coupling_list physical coupling list
 * @return std::vector<int> logic->physical mapping
 */
std::vector<int> sabre_initial_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list);

}  // namespace qcos
