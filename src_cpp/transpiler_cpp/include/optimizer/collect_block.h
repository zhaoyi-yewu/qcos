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

#include <set>
#include <string>
#include <vector>

#include "circuit/dag_node.h"

namespace qcos {

class DAGCircuit;

/**
 * @brief 从 DAG 中提取门名属于 collect_gates 的所有子电路块
 *
 * @param dag 待提取的 DAG
 * @param collect_gates 目标门名集合，门名在此集合中的节点被收集
 * @param min_block_size 最小块大小，小于此值的块被丢弃
 * @return 匹配块列表，每个块为拓扑有序的门节点向量
 */
std::vector<std::vector<DAGOpNode*>> collect_all_matching_blocks(
    DAGCircuit& dag, const std::set<std::string>& collect_gates,
    size_t min_block_size = 2);

}  // namespace qcos
