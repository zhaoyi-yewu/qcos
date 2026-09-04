/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include "optimizer/collect_block.h"

#include <cstddef>
#include <set>
#include <unordered_map>
#include <utility>

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
 * @brief 计算每个 op 节点的 op 前驱数量(入度), 入度为 0 的入 pending_nodes
 */
void init_in_degrees(DAGCircuit& dag,
                     const std::vector<DAGOpNode*>& op_nodes,
                     std::unordered_map<DAGOpNode*, int>& in_degree,
                     std::vector<DAGOpNode*>& pending_nodes) {
  for (DAGOpNode* node : op_nodes) {
    int degree = 0;
    for (DAGNode* pred : dag.predecessors(node)) {
      if (dynamic_cast<DAGOpNode*>(pred)) ++degree;
    }
    in_degree[node] = degree;
    if (degree == 0) pending_nodes.push_back(node);
  }
}

/**
 * @brief 从 pending 节点中收集门名属于/不属于 collect_gates 的连续拓扑块
 *
 * 算法参照 qiskit BlockCollector.collect_matching_block: 迭代处理入度为 0
 * 的待处理节点。匹配的节点加入 current_block 并释放其 op 后继的入度,
 * 入度归零的后继被追加到当前队列尾部继续处理 (使块沿拓扑后继自然扩张)。
 * 不匹配的节点放回 pending_nodes, 由后续轮次处理。
 *
 * 当 max_block_width 有效时, 节点加入前还须满足「加入后块内 qubit 并集
 * 宽度 ≤ max_block_width」。匹配但超宽的节点会立即终止当前块收集 (块已
 * 达极大), 该节点连同队列中未处理节点退回 pending, 由下一轮以该节点为
 * 种子开新块。这样每轮调用必产出非空 block 或消费非匹配节点释放入度,
 * 拓扑必然推进, 不会死循环。
 *
 * @param max_block_width 块内 qubit 并集宽度上限; 为 SIZE_MAX 时不约束
 */
std::vector<DAGOpNode*> collect_matching_block(
    DAGCircuit& dag, std::unordered_map<DAGOpNode*, int>& in_degree,
    std::vector<DAGOpNode*>& pending_nodes,
    const std::set<std::string>& collect_gates, bool negate = false,
    size_t max_block_width = SIZE_MAX) {
  std::vector<DAGOpNode*> block;
  std::set<int> block_qargs;
  auto unprocessed = std::move(pending_nodes);
  pending_nodes.clear();

  while (!unprocessed.empty()) {
    DAGOpNode* node = unprocessed.back();
    unprocessed.pop_back();

    bool matches = (collect_gates.count(node->name()) > 0) != negate;

    // width_ok: 节点能否加入当前块而不超 max_block_width。含两种「不可加」:
    //  (a) 节点自身 qubit 数已超 max_block_width (self_too_wide, 如 max=2 下
    //      的 3-qubit ccx) — 永不可能被任何块收下;
    //  (b) 节点加入后块内 qubit 并集超 max_block_width (块已达极大)。
    // 两者都必须阻止节点进块, 否则块会被污染 (qubit 并集突破上限) 并
    // 连锁吞掉后续节点, 既无法合成又可能死循环。
    bool width_ok = true;
    if (matches && max_block_width != SIZE_MAX) {
      size_t new_width = block_qargs.size();
      for (int q : node->qargs) {
        if (!block_qargs.count(q)) {
          ++new_width;
          if (new_width > max_block_width) {
            width_ok = false;
            break;
          }
        }
      }
    }
    // 节点自身宽度 (去重 qubit 数); 与块的当前宽度独立判断。
    size_t node_qubits = 0;
    if (matches && max_block_width != SIZE_MAX) {
      std::set<int> seen;
      for (int q : node->qargs)
        if (seen.insert(q).second) ++node_qubits;
    }
    bool self_too_wide =
        max_block_width != SIZE_MAX && node_qubits > max_block_width;
    if (self_too_wide) width_ok = false;

    if (matches && width_ok) {
      block.push_back(node);
      if (max_block_width != SIZE_MAX) {
        for (int q : node->qargs) block_qargs.insert(q);
      }
      for (DAGOpNode* succ : get_active_op_successors(dag, node)) {
        --in_degree[succ];
        if (in_degree[succ] == 0) unprocessed.push_back(succ);
      }
    } else if (matches && self_too_wide) {
      // 节点自身就超宽 (如 max_block_width=2 下的 3-qubit ccx), 永不可被收。
      // 不可能进入任何结果块, 故直接释放入度跳过, 让其后继能继续被处理。
      // (后续 split_and_filter 仅处理已收块, 此节点保留在 DAG 中原样不动。)
      for (DAGOpNode* succ : get_active_op_successors(dag, node)) {
        --in_degree[succ];
        if (in_degree[succ] == 0) unprocessed.push_back(succ);
      }
    } else if (!matches) {
      // 非匹配节点: 退回 pending, 交后续轮次处理, 不释放入度。
      pending_nodes.push_back(node);
    } else {
      // 匹配且自身可收, 但加入当前块后超出 max_block_width: 块已达极大,
      // 终止收集。该节点退回 pending 作下一轮新块种子; 同时把 unprocessed
      // 中尚未处理的节点一并退回 pending, 避免丢失。每轮调用必产出 block
      // 或消费非匹配/超宽节点释放入度, 拓扑必然推进, 不会死循环。
      pending_nodes.push_back(node);
      for (DAGOpNode* rest : unprocessed) pending_nodes.push_back(rest);
      unprocessed.clear();
      break;
    }
  }
  return block;
}

/**
 * @brief DSU 按不相交 qubit 子集拆分 (qiskit BlockSplitter)
 *
 * 同一拓扑匹配块内可能存在量子比特互不相连的门组, 按连通性拆成独立子块。
 */
std::vector<std::vector<DAGOpNode*>> split_block_by_disjoint_qubits(
    const std::vector<DAGOpNode*>& block) {
  std::unordered_map<int, int> dsu_parent;
  auto find = [&](int qubit, auto&& find_ref) -> int {
    auto it = dsu_parent.find(qubit);
    if (it == dsu_parent.end()) {
      dsu_parent[qubit] = qubit;
      return qubit;
    }
    if (it->second != qubit) it->second = find_ref(it->second, find_ref);
    return it->second;
  };
  auto unite = [&](int q1, int q2, auto&& find_ref) {
    int r1 = find_ref(q1, find_ref);
    int r2 = find_ref(q2, find_ref);
    if (r1 != r2) dsu_parent[r1] = r2;
  };

  for (DAGOpNode* node : block) {
    if (node->qargs.empty()) continue;
    int first = node->qargs[0];
    for (size_t i = 1; i < node->qargs.size(); ++i)
      unite(first, node->qargs[i], find);
  }

  std::unordered_map<int, std::vector<DAGOpNode*>> groups;
  for (DAGOpNode* node : block) {
    if (node->qargs.empty()) continue;
    groups[find(node->qargs[0], find)].push_back(node);
  }

  std::vector<std::vector<DAGOpNode*>> result;
  result.reserve(groups.size());
  for (auto& [root, sub] : groups) result.push_back(std::move(sub));
  return result;
}

/**
 * @brief 对 matching_blocks 做 DSU 拆分并丢弃小于 min_block_size 的子块
 */
std::vector<std::vector<DAGOpNode*>> split_and_filter(
    std::vector<std::vector<DAGOpNode*>>& matching_blocks,
    size_t min_block_size) {
  std::vector<std::vector<DAGOpNode*>> result;
  for (auto& block : matching_blocks) {
    for (auto& sub : split_block_by_disjoint_qubits(block)) {
      if (sub.size() < min_block_size) continue;
      result.push_back(std::move(sub));
    }
  }
  return result;
}

}  // namespace

std::vector<std::vector<DAGOpNode*>> collect_all_matching_blocks(
    DAGCircuit& dag, const std::set<std::string>& collect_gates,
    size_t min_block_size) {
  auto op_nodes = dag.topological_op_nodes();

  std::unordered_map<DAGOpNode*, int> in_degree;
  std::vector<DAGOpNode*> pending_nodes;
  init_in_degrees(dag, op_nodes, in_degree, pending_nodes);

  // 交替收集非匹配段(释放入度)与匹配段(保留为结果块), 循环至处理完毕。
  std::vector<std::vector<DAGOpNode*>> matching_blocks;
  while (!pending_nodes.empty()) {
    collect_matching_block(dag, in_degree, pending_nodes, collect_gates,
                           /*negate=*/true);
    auto block = collect_matching_block(dag, in_degree, pending_nodes,
                                        collect_gates, /*negate=*/false);
    if (!block.empty()) matching_blocks.push_back(std::move(block));
  }

  return split_and_filter(matching_blocks, min_block_size);
}

std::vector<std::vector<DAGOpNode*>> collect_interacting_blocks(
    DAGCircuit& dag, const std::set<std::string>& collect_gates,
    size_t max_qubits, size_t min_block_size) {
  auto op_nodes = dag.topological_op_nodes();

  std::unordered_map<DAGOpNode*, int> in_degree;
  std::vector<DAGOpNode*> pending_nodes;
  init_in_degrees(dag, op_nodes, in_degree, pending_nodes);

  // 交替收集非匹配段(无 width 约束)与匹配段(逐节点强制 max_block_width,
  // 超限节点留池作新种子), 按 qubit 交互范围切出极大交互块。
  std::vector<std::vector<DAGOpNode*>> matching_blocks;
  while (!pending_nodes.empty()) {
    collect_matching_block(dag, in_degree, pending_nodes, collect_gates,
                           /*negate=*/true);
    auto block = collect_matching_block(dag, in_degree, pending_nodes,
                                         collect_gates, /*negate=*/false,
                                         /*max_block_width=*/max_qubits);
    if (!block.empty()) matching_blocks.push_back(std::move(block));
  }

  return split_and_filter(matching_blocks, min_block_size);
}

}  // namespace qcos
