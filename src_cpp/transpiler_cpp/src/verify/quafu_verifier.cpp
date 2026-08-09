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

#include "verify/quafu_verifier.h"

#include <algorithm>
#include <iostream>
#include <set>
#include <string>
#include <unordered_map>
#include <unordered_set>

#include "mapping/mapping_utils.h"

namespace qcos {

namespace {

/**
 * @brief 回溯放置电路连通分量（bin-packing 核心递归）
 *
 * 逐个将电路连通分量放入 target 连通区，每个分量尝试所有箱子，
 * 放不下则回退。本质是带容量约束的装箱回溯。
 *
 * 术语对照（组合优化标准术语）：
 *   - item（物品）= 电路交互图某连通分量的大小，即一组互相耦合的比特数
 *   - bin（箱子）= target_bits 诱导子图某连通分量的容量
 *
 * @param items 电路各连通分量大小，已降序排列
 * @param bins  target 各连通区容量，已降序排列
 * @param bin_load 各 bin 当前已放入量，递归过程中原地修改
 * @param idx   当前正在放置的 item 下标
 * @return true 所有 item 都成功放入
 */
bool backtrack_place_component(const std::vector<int>& items,
                               const std::vector<int>& bins,
                               std::vector<int>& bin_load, size_t idx) {
  if (idx == items.size()) return true;
  for (size_t j = 0; j < bins.size(); ++j) {
    if (bin_load[j] + items[idx] <= bins[j]) {
      bin_load[j] += items[idx];
      if (backtrack_place_component(items, bins, bin_load, idx + 1))
        return true;
      bin_load[j] -= items[idx];
    }
  }
  return false;
}

/**
 * @brief 检查电路连通分量能否分配到 target 连通区（bin-packing 可行性）
 *
 * 将问题建模为装箱：电路每个连通分量（item）需放入 target 某个连通区
 * （bin），约束为每箱放入量 <= 容量。总量相等时自动收紧为恰好放满。
 *
 * 优化：大小为 1 的离散单比特（孤立逻辑比特）不参与回溯，只在大分量
 * 放完后检查剩余总容量是否足够，因为任何容量 >= 1 的箱子都能接纳它们。
 * 连通分量数极小时回溯 + 剪枝即可求解。
 *
 * @param items 电路各连通分量大小
 * @param bins  target 各连通区容量
 * @return true 存在合法分配方案
 */
bool can_place_components(std::vector<int> items, std::vector<int> bins) {
  if (items.empty()) return true;
  std::sort(items.begin(), items.end(), [](int a, int b) { return a > b; });
  std::sort(bins.begin(), bins.end(), [](int a, int b) { return a > b; });
  // 大小为 1 的离散物品（孤立单比特）无需回溯：只要大分量放完后，
  // 剩余总容量足够即可，因为任何容量 >= 1 的箱子都能接纳它们。
  std::vector<int> big_items;
  int single_count = 0;
  for (int item : items) {
    if (item == 1) {
      ++single_count;
    } else {
      big_items.push_back(item);
    }
  }
  // 大物品放不进最大 bin，直接否决
  if (!big_items.empty() && big_items.front() > bins.front()) return false;
  std::vector<int> bin_load(bins.size(), 0);
  if (!backtrack_place_component(big_items, bins, bin_load, 0)) return false;
  // 离散单比特：检查剩余总容量是否足够
  int remaining = 0;
  for (size_t j = 0; j < bins.size(); ++j) {
    remaining += bins[j] - bin_load[j];
  }
  return remaining >= single_count;
}

/**
 * @brief 计算图的各连通分量大小
 *
 * @param edges 图的边列表
 * @param nodes 需要纳入统计的所有节点（含孤立节点）
 * @return 各连通分量的大小列表
 */
std::vector<int> compute_component_sizes(
    const std::vector<std::pair<int, int>>& edges,
    const std::set<int>& nodes) {
  auto comp_map = find_connected_components(edges);
  std::unordered_map<int, int> size_by_root;
  for (const auto& [node, root] : comp_map) {
    ++size_by_root[root];
  }
  std::vector<int> sizes;
  for (const auto& [root, sz] : size_by_root) {
    sizes.push_back(sz);
  }
  for (int node : nodes) {
    if (comp_map.find(node) == comp_map.end()) {
      sizes.push_back(1);
    }
  }
  return sizes;
}

}  // namespace

QuafuVerifier::QuafuVerifier(const VerifyParams& params)
    : QPUVerifier(params) {}

VerifyResult QuafuVerifier::verify(const std::string& qasm_string,
                                   bool verbose) const {
  result_ = VerifyResult{};
  if (check_qasm_syntax2(qasm_string) && check_topology() &&
      check_depth_and_gate_count()) {
    return result_;
  } else {
    if (verbose) std::cout << result_.message << std::endl;
    return result_;
  }
}

bool QuafuVerifier::check_qasm_syntax2(const std::string& qasm_string) const {
  return QPUVerifier::check_qasm_syntax2(qasm_string);
}

bool QuafuVerifier::check_topology() const {
  if (parsed_num_qubits_ <= 0) {
    result_.add_failure("Topology error: circuit has no qubits");
    return false;
  }

  // target_bits 越界检查 + 去重 + 数量校验（基类公共逻辑）
  if (!check_target_bits_range_and_count()) return false;

  // 全是单比特门，有足够比特即可
  if (!has_multi_qubit_gates()) {
    if (parsed_num_qubits_ > max_qubits_) {
      result_.add_failure("Topology error: circuit requires " +
                          std::to_string(parsed_num_qubits_) +
                          " qubits, but chip only has " +
                          std::to_string(max_qubits_));
      return false;
    }
    return true;
  }

  // 含多比特门
  if (target_bits_.empty()) {
    // 用户未指定：判断最大连通分量节点数是否足够
    return check_largest_component_sufficient(parsed_num_qubits_);
  } else {
    // 用户指定了 target_bits：检查电路交互图的连通分量能否装入
    // target_bits 诱导子图的连通分量中（bin-packing）。

    // 1. 电路交互图：多比特门产生交互边，统计实际使用比特
    std::vector<std::pair<int, int>> interaction_edges;
    std::set<int> used_qubits;
    for (const auto& op : parsed_operations_) {
      if (op->operation_type == OperationType::SYNC) continue;
      for (int t : op->targets) used_qubits.insert(t);
      if (op->operation_type >= OperationType::DOUBLE_QUBIT_OPERATION) {
        for (size_t i = 0; i + 1 < op->targets.size(); ++i) {
          interaction_edges.emplace_back(op->targets[i], op->targets[i + 1]);
        }
      }
    }
    auto circuit_items =
        compute_component_sizes(interaction_edges, used_qubits);

    // 2. target_bits 诱导子图：只保留两端都在 target_bits 中的耦合边
    std::unordered_set<int> target_set(target_bits_.begin(),
                                       target_bits_.end());
    std::vector<std::pair<int, int>> induced_edges;
    for (const auto& [qubit_a, qubit_b] : coupling_list_) {
      if (target_set.count(qubit_a) && target_set.count(qubit_b)) {
        induced_edges.emplace_back(qubit_a, qubit_b);
      }
    }
    std::set<int> target_nodes(target_bits_.begin(), target_bits_.end());
    auto target_bins = compute_component_sizes(induced_edges, target_nodes);

    // 3. bin-packing 可行性：每个电路分量放入某 target 分量，放入量 <= 容量
    if (!can_place_components(std::move(circuit_items),
                              std::move(target_bins))) {
      result_.add_failure(
          "Topology error: circuit topology cannot be mapped onto "
          "target_bits");
      return false;
    }
    return true;
  }
}

bool QuafuVerifier::check_depth_and_gate_count() const {
  return QPUVerifier::check_depth_and_gate_count(200, 200, -1);
}

}  // namespace qcos
