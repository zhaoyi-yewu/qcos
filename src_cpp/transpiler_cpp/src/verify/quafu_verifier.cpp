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

#include "compiler/qasm_to_ir.hpp"
#include "mapping/mapping_utils.h"
#include "transpile/transpile.h"

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
    : max_qubits_(params.bits),
      coupling_list_(params.coupling_list),
      edge_fidelities_(params.edge_fidelities),
      single_qubit_fidelities_(params.single_qubit_fidelities),
      target_bits_(params.target_bits) {}

VerifyResult QuafuVerifier::verify(const std::string& qasm_string,
                                   bool verbose) const {
  result_ = VerifyResult{};
  if (check_qasm_syntax(qasm_string) && check_topology() &&
      check_depth_and_gate_count()) {
    return result_;
  } else {
    if (verbose) std::cout << result_.message << std::endl;
    return result_;
  }
}

bool QuafuVerifier::check_qasm_syntax(const std::string& qasm_string) const {
  // 找到 OPENQASM 声明行，判断版本号是否为 2.0
  auto pos = qasm_string.find("OPENQASM");
  if (pos == std::string::npos) {
    result_.add_failure("QASM syntax error: OPENQASM declaration not found");
    return false;
  }

  // 取 "OPENQASM" 后面到分号的子串，提取版本号
  auto line_end = qasm_string.find(';', pos);
  if (line_end == std::string::npos) {
    result_.add_failure("QASM syntax error: incomplete OPENQASM declaration");
    return false;
  }

  // pos + 8 跳过 "OPENQASM" 这 8 个字符
  auto version_part = qasm_string.substr(pos + 8, line_end - (pos + 8));
  // 跳过前导空格
  auto first_non_space = version_part.find_first_not_of(" \t");
  if (first_non_space == std::string::npos) {
    result_.add_failure("QASM syntax error: missing version number");
    return false;
  }

  if (version_part.substr(first_non_space, 3) != "2.0") {
    result_.add_failure("QASM syntax error: only OPENQASM 2.0 is supported");
    return false;
  }

  // 尝试解析，成功后缓存结果供后续 check 使用
  try {
    auto [ops, num_qubits] = qasm_to_ir(qasm_string);
    parsed_operations_ = std::move(ops);
    // 以实际操作中使用的去重比特数作为比特数，而非 QASM 声明值
    std::set<int> used_qubits;
    for (const auto& op : parsed_operations_) {
      // 跳过 barrier(sync)门
      if (op->operation_type == OperationType::SYNC) continue;
      for (int target : op->targets) {
        used_qubits.insert(target);
      }
    }
    parsed_num_qubits_ = static_cast<int>(used_qubits.size());
  } catch (const std::exception& exc) {
    std::cerr << "QASM parse error: " << exc.what() << std::endl;
    result_.add_failure("QASM syntax error: failed to parse circuit");
    return false;
  }
  return true;
}

bool QuafuVerifier::check_topology() const {
  if (parsed_num_qubits_ <= 0) {
    result_.add_failure("Topology error: circuit has no qubits");
    return false;
  }

  // target_bits 越界检查（无论单比特还是多比特门，都必须合法）
  for (int target_bit : target_bits_) {
    if (target_bit < 0 || target_bit >= max_qubits_) {
      result_.add_failure("Topology error: target_bit " +
                          std::to_string(target_bit) + " out of range [0, " +
                          std::to_string(max_qubits_) + ")");
      return false;
    }
  }

  // target_bits 非空时去重，并校验去重后的数量与电路实际使用比特数一致
  if (!target_bits_.empty()) {
    std::set<int> unique_set(target_bits_.begin(), target_bits_.end());
    target_bits_.assign(unique_set.begin(), unique_set.end());
    if (static_cast<int>(target_bits_.size()) != parsed_num_qubits_) {
      result_.add_failure(
          "Topology error: target qubits number mismatch with circuit");
      return false;
    }
  }

  // 检查是否存在多比特门（双比特及以上）
  bool has_multi_qubit_gate = std::any_of(
      parsed_operations_.begin(), parsed_operations_.end(),
      [](const std::shared_ptr<BaseOperation>& op) {
        return op->operation_type >= OperationType::DOUBLE_QUBIT_OPERATION;
      });

  // 规则1：全是单比特门，有足够比特即可
  if (!has_multi_qubit_gate) {
    if (parsed_num_qubits_ > max_qubits_) {
      result_.add_failure("Topology error: circuit requires " +
                          std::to_string(parsed_num_qubits_) +
                          " qubits, but chip only has " +
                          std::to_string(max_qubits_));
      return false;
    }
    return true;
  }

  // 规则2：含多比特门
  if (target_bits_.empty()) {
    // 用户未指定：判断最大连通分量节点数是否足够
    auto component_edges = coupling_list_;
    select_largest_component(component_edges);

    std::set<int> component_qubits;
    for (const auto& [qubit_a, qubit_b] : component_edges) {
      component_qubits.insert(qubit_a);
      component_qubits.insert(qubit_b);
    }
    int largest_size = static_cast<int>(component_qubits.size());
    if (parsed_num_qubits_ > largest_size) {
      result_.add_failure(
          "Topology error: circuit requires " +
          std::to_string(parsed_num_qubits_) +
          " qubits, but largest connected component only has " +
          std::to_string(largest_size));
      return false;
    }
    return true;
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
  // 限制双比特门数量 <= 200
  static constexpr int kMaxTwoQubitGates = 200;
  // 限制深度（含单比特门、双比特门）<= 200
  static constexpr int kMaxDepth = 200;

  // 第一次检查：统计多比特门数量（含 3 比特以上未分解门），超限直接拒绝
  int multi_qubit_count = 0;
  for (const auto& op : parsed_operations_) {
    if (op->operation_type >= OperationType::DOUBLE_QUBIT_OPERATION) {
      ++multi_qubit_count;
    }
  }
  if (multi_qubit_count > kMaxTwoQubitGates) {
    result_.add_failure(
        "Gate count error: " + std::to_string(multi_qubit_count) +
        " multi-qubit gates exceed limit " +
        std::to_string(kMaxTwoQubitGates));
    return false;
  }

  // 第二次检查：分解为基础门后，重新统计双比特门数量
  auto decomposed = decompose_gates_to_1q2q(parsed_operations_);
  int two_qubit_count = 0;
  for (const auto& op : decomposed) {
    if (op->operation_type == OperationType::DOUBLE_QUBIT_OPERATION) {
      ++two_qubit_count;
    }
  }
  if (two_qubit_count > kMaxTwoQubitGates) {
    result_.add_failure(
        "Gate count error: " + std::to_string(two_qubit_count) +
        " two-qubit gates after decomposition exceed limit " +
        std::to_string(kMaxTwoQubitGates));
    return false;
  }

  // 第三次检查：电路深度不超过 kMaxDepth
  // 深度 = 关键路径长度，每个门使其所有目标比特的深度 +1
  std::unordered_map<int, int> depth_per_qubit;
  for (const auto& op : decomposed) {
    // 跳过非门操作
    if (op->operation_type < OperationType::SINGLE_QUBIT_OPERATION) continue;

    // 当前门的深度 = 所有目标比特中最大深度 + 1
    int gate_depth = 0;
    for (int target : op->targets) {
      gate_depth = std::max(gate_depth, depth_per_qubit[target] + 1);
    }
    for (int target : op->targets) {
      depth_per_qubit[target] = gate_depth;
    }
  }

  int circuit_depth = 0;
  for (const auto& [qubit_id, depth] : depth_per_qubit) {
    circuit_depth = std::max(circuit_depth, depth);
  }
  if (circuit_depth > kMaxDepth) {
    result_.add_failure("Depth error: circuit depth " +
                        std::to_string(circuit_depth) + " exceeds limit " +
                        std::to_string(kMaxDepth));
    return false;
  }
  return true;
}

}  // namespace qcos
