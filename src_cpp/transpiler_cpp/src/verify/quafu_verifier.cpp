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

#include "compiler/qasm_to_ir.hpp"
#include "mapping/mapping_utils.h"
#include "transpile/transpile.h"

namespace qcos {

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
      for (int target : op->targets) {
        used_qubits.insert(target);
      }
    }
    parsed_num_qubits_ = static_cast<int>(used_qubits.size());
  } catch (...) {
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
    // 用户指定了 target_bits：判断是否都在同一个连通分量上
    auto component_map = find_connected_components(coupling_list_);
    auto first_target_entry = component_map.find(target_bits_[0]);
    if (first_target_entry == component_map.end()) {
      result_.add_failure("Topology error: target_bit " +
                          std::to_string(target_bits_[0]) +
                          " not found in coupling graph");
      return false;
    }
    int expected_component_id = first_target_entry->second;
    for (size_t i = 1; i < target_bits_.size(); ++i) {
      auto entry = component_map.find(target_bits_[i]);
      if (entry == component_map.end()) {
        result_.add_failure("Topology error: target_bit " +
                            std::to_string(target_bits_[i]) +
                            " not found in coupling graph");
        return false;
      }
      if (entry->second != expected_component_id) {
        result_.add_failure("Topology error: target_bits " +
                            std::to_string(target_bits_[0]) + " and " +
                            std::to_string(target_bits_[i]) +
                            " are in different connected components");
        return false;
      }
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
