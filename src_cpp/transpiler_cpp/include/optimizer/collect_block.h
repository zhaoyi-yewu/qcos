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

/**
 * @brief 按 qubit 交互范围提取子电路块(合成友好)
 *
 * 算法参照 qiskit BlockCollector.collect_all_matching_blocks:以入度
 * 拓扑 BFS 交替收集「非匹配段」与「匹配段」。区别于
 * collect_all_matching_blocks 之处在于, 收集匹配段时逐节点强制
 * max_block_width 约束:节点加入当前块后,块内 qubit 并集宽度须
 * ≤ max_qubits 才吸收并释放入度, 否则该节点留在 pending 池中,
 * 待下一轮非匹配段释放入度后成为新块种子。这样天然按 qubit 交互
 * 范围切分出极大连通交互块, 每块 qubit 并集严格 ≤ max_qubits,
 * 可被 2^max_qubits 酉合成器整块处理。
 *
 * 各匹配块收集后再用 DSU (BlockSplitter) 按不相交 qubit 子集拆分,
 * 拆出的子块 qubit 并集仍 ≤ max_qubits。不足 min_block_size 的块
 * 被丢弃(其门不进入任何块)。
 *
 * @param dag 待提取的 DAG
 * @param collect_gates 目标门名集合
 * @param max_qubits 块内 qubit 并集上限(合成器维度 2^max_qubits)
 * @param min_block_size 最小块大小,小于此值丢弃
 * @return 匹配块列表,每个块为拓扑有序的门节点向量
 */
std::vector<std::vector<DAGOpNode*>> collect_interacting_blocks(
    DAGCircuit& dag, const std::set<std::string>& collect_gates,
    size_t max_qubits, size_t min_block_size = 2);

}  // namespace qcos
