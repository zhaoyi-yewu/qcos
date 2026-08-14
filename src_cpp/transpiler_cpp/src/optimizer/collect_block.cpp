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

#include "optimizer/collect_block.h"

#include <algorithm>
#include <unordered_map>

#include "circuit/dag_circuit.h"

namespace qcos {

namespace {

/**
 * @brief 返回指定节点的所有活跃 op 后继节点
 *
 * @param dag 所属 DAG
 * @param node 查询起点
 * @return 活跃 op 后继节点列表
 */
std::vector<DAGOpNode*> get_active_op_successors(DAGCircuit& dag,
                                                 DAGOpNode* node) {
  std::vector<DAGOpNode*> op_successors;
  for (DAGNode* succ : dag.successors(node)) {
    auto* op_node = dynamic_cast<DAGOpNode*>(succ);
    if (op_node) op_successors.push_back(op_node);
  }
  return op_successors;
}

/**
 * @brief 从 pending 节点中收集门名属于/不属于 collect_gates 的连续拓扑块
 *
 * 使用拓扑 BFS：满足条件的节点加入结果块并释放其所有后继的入度；
 * 不满足的节点放回 pending_nodes，由后续轮次处理。
 *
 * @param dag 所属 DAG
 * @param in_degree 各节点当前入度（会被修改）
 * @param pending_nodes 当前可处理的节点队列（会被清空并回填不匹配节点）
 * @param collect_gates 目标门名集合
 * @param negate 为 false 时收集门名在集合中的节点，为 true
 * 时收集不在集合中的节点
 * @return 收集到的匹配节点块
 */
std::vector<DAGOpNode*> collect_matching_block(
    DAGCircuit& dag, std::unordered_map<DAGOpNode*, int>& in_degree,
    std::vector<DAGOpNode*>& pending_nodes,
    const std::set<std::string>& collect_gates, bool negate = false) {
  std::vector<DAGOpNode*> block;
  auto unprocessed = std::move(pending_nodes);
  pending_nodes.clear();

  while (!unprocessed.empty()) {
    std::vector<DAGOpNode*> next_round;
    for (DAGOpNode* node : unprocessed) {
      bool in_set = collect_gates.count(node->name()) > 0;
      if (in_set != negate) {
        block.push_back(node);
        for (DAGOpNode* succ : get_active_op_successors(dag, node)) {
          --in_degree[succ];
          if (in_degree[succ] == 0) next_round.push_back(succ);
        }
      } else {
        pending_nodes.push_back(node);
      }
    }
    unprocessed = std::move(next_round);
  }
  return block;
}

}  // namespace

std::vector<std::vector<DAGOpNode*>> collect_all_matching_blocks(
    DAGCircuit& dag, const std::set<std::string>& collect_gates,
    size_t min_block_size) {
  auto op_nodes = dag.topological_op_nodes();

  // 计算每个 op 节点的 op 前驱数量（入度）
  std::unordered_map<DAGOpNode*, int> in_degree;
  std::vector<DAGOpNode*> pending_nodes;

  for (DAGOpNode* node : op_nodes) {
    int degree = 0;
    for (DAGNode* pred : dag.predecessors(node)) {
      if (dynamic_cast<DAGOpNode*>(pred)) ++degree;
    }
    in_degree[node] = degree;
    if (degree == 0) pending_nodes.push_back(node);
  }

  // 交替收集非匹配块和匹配块
  // 先收集一轮非匹配节点（negate=true，丢弃结果，仅释放入度），
  // 再收集紧跟其后的匹配节点（negate=false，保留为结果块），
  // 循环直到所有节点处理完毕。
  std::vector<std::vector<DAGOpNode*>> matching_blocks;
  while (!pending_nodes.empty()) {
    collect_matching_block(dag, in_degree, pending_nodes, collect_gates,
                           /*negate=*/true);
    auto block = collect_matching_block(dag, in_degree, pending_nodes,
                                        collect_gates, /*negate=*/false);
    if (!block.empty()) matching_blocks.push_back(std::move(block));
  }

  // 按 qubit 连通性拆分 (DSU 并查集)
  // 同一个拓扑匹配块中，可能存在量子比特互不相连的门组，
  // 需要按连通性拆成独立子块。
  std::unordered_map<int, int> dsu_parent;
  std::unordered_map<int, std::vector<DAGOpNode*>> dsu_groups;

  auto dsu_find = [&](int qubit, auto&& find_ref) -> int {
    auto it = dsu_parent.find(qubit);
    if (it == dsu_parent.end()) {
      dsu_parent[qubit] = qubit;
      return qubit;
    }
    if (it->second != qubit) it->second = find_ref(it->second, find_ref);
    return it->second;
  };

  auto dsu_unite = [&](int qubit_first, int qubit_second, auto&& find_ref) {
    int root_first = find_ref(qubit_first, find_ref);
    int root_second = find_ref(qubit_second, find_ref);
    if (root_first != root_second) dsu_parent[root_first] = root_second;
  };

  std::vector<std::vector<DAGOpNode*>> result;
  for (auto& block : matching_blocks) {
    dsu_parent.clear();
    dsu_groups.clear();

    // 将每个门涉及的所有 qubit 合并到同一 DSU 集合
    for (DAGOpNode* node : block) {
      if (node->qargs.empty()) continue;
      int first_qubit = node->qargs[0];
      for (size_t idx = 1; idx < node->qargs.size(); ++idx)
        dsu_unite(first_qubit, node->qargs[idx], dsu_find);
    }

    // 按根 qubit 分组
    for (DAGOpNode* node : block) {
      if (node->qargs.empty()) continue;
      int group_root = dsu_find(node->qargs[0], dsu_find);
      dsu_groups[group_root].push_back(node);
    }

    // 过滤过小块，恢复拓扑序后加入结果
    for (auto& [group_root, sub_block] : dsu_groups) {
      if (sub_block.size() < min_block_size) continue;
      // collect_matching_block 返回的已经是拓扑序，直接添加到 result
      result.push_back(std::move(sub_block));
    }
  }

  return result;
}

}  // namespace qcos
