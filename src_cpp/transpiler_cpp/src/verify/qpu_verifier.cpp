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

#include "verify/qpu_verifier.h"

#include <algorithm>
#include <iostream>
#include <set>
#include <string>
#include <unordered_map>

#include "compiler/qasm_to_ir.hpp"
#include "mapping/mapping_utils.h"
#include "transpile/transpile.h"

namespace qcos {

QPUVerifier::QPUVerifier(const VerifyParams& params)
    : max_qubits_(params.bits),
      coupling_list_(params.coupling_list),
      edge_fidelities_(params.edge_fidelities),
      single_qubit_fidelities_(params.single_qubit_fidelities),
      target_bits_(params.target_bits) {}

bool QPUVerifier::check_qasm_syntax2(const std::string& qasm_string) const {
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

  // Measure 门校验：必须在线路末尾，每个比特最多一次
  if (!check_measure_rules()) return false;
  return true;
}

bool QPUVerifier::check_measure_rules() const {
  // Measure 必须在电路末尾，每个比特最多一次
  bool seen_measure = false;
  std::set<int> measured_qubits;
  for (const auto& op : parsed_operations_) {
    if (op->operation_type == OperationType::MEASURE) {
      seen_measure = true;
      for (int target : op->targets) {
        if (!measured_qubits.insert(target).second) {
          result_.add_failure("QASM syntax error: qubit " +
                              std::to_string(target) +
                              " is measured more than once");
          return false;
        }
      }
    } else if (seen_measure) {
      // Measure 之后出现了非 Measure 门
      result_.add_failure(
          "QASM syntax error: Measure gates must be at the end of the "
          "circuit");
      return false;
    }
  }
  return true;
}

bool QPUVerifier::check_target_bits_range() const {
  for (int target_bit : target_bits_) {
    if (target_bit < 0 || target_bit >= max_qubits_) {
      result_.add_failure("Topology error: target_bit " +
                          std::to_string(target_bit) + " out of range [0, " +
                          std::to_string(max_qubits_) + ")");
      return false;
    }
  }
  return true;
}

bool QPUVerifier::check_target_bits_range_and_count() const {
  // 越界检查复用 check_target_bits_range
  if (!check_target_bits_range()) return false;

  // target_bits 非空时检查重复 + 数量校验
  if (!target_bits_.empty()) {
    std::set<int> seen;
    for (int bit : target_bits_) {
      if (!seen.insert(bit).second) {
        result_.add_failure("Topology error: duplicate target_bits");
        return false;
      }
    }
    if (static_cast<int>(target_bits_.size()) != parsed_num_qubits_) {
      result_.add_failure(
          "Topology error: target qubits number mismatch with circuit");
      return false;
    }
  }
  return true;
}

bool QPUVerifier::check_largest_component_sufficient(int required) const {
  auto component_edges = coupling_list_;
  select_largest_component(component_edges);

  std::set<int> component_qubits;
  for (const auto& [qubit_a, qubit_b] : component_edges) {
    component_qubits.insert(qubit_a);
    component_qubits.insert(qubit_b);
  }
  int largest_size = static_cast<int>(component_qubits.size());
  if (required > largest_size) {
    result_.add_failure("Topology error: circuit requires " +
                        std::to_string(required) +
                        " qubits, but largest connected component only has " +
                        std::to_string(largest_size));
    return false;
  }
  return true;
}

bool QPUVerifier::has_multi_qubit_gates() const {
  return std::any_of(parsed_operations_.begin(), parsed_operations_.end(),
                     [](const std::shared_ptr<BaseOperation>& op) {
                       return op->operation_type >=
                              OperationType::DOUBLE_QUBIT_OPERATION;
                     });
}

bool QPUVerifier::check_depth_and_gate_count(int max_depth, int max_2q_size,
                                             int max_size) const {
  // 第一次检查：统计多比特门数量（含 3 比特以上未分解门），超限直接拒绝
  if (max_2q_size != -1) {
    int multi_qubit_count = 0;
    for (const auto& op : parsed_operations_) {
      if (op->operation_type >= OperationType::DOUBLE_QUBIT_OPERATION) {
        ++multi_qubit_count;
      }
    }
    if (multi_qubit_count > max_2q_size) {
      result_.add_failure(
          "Gate count error: " + std::to_string(multi_qubit_count) +
          " multi-qubit gates exceed limit " + std::to_string(max_2q_size));
      return false;
    }
  }

  // 分解为基础门后，重新统计双比特门数量和总门数量
  auto decomposed = decompose_gates_to_1q2q(parsed_operations_);

  if (max_2q_size != -1) {
    int two_qubit_count = 0;
    for (const auto& op : decomposed) {
      if (op->operation_type == OperationType::DOUBLE_QUBIT_OPERATION) {
        ++two_qubit_count;
      }
    }
    if (two_qubit_count > max_2q_size) {
      result_.add_failure(
          "Gate count error: " + std::to_string(two_qubit_count) +
          " two-qubit gates after decomposition exceed limit " +
          std::to_string(max_2q_size));
      return false;
    }
  }

  if (max_size != -1) {
    int total_count = 0;
    for (const auto& op : decomposed) {
      if (op->operation_type >= OperationType::SINGLE_QUBIT_OPERATION) {
        ++total_count;
      }
    }
    if (total_count > max_size) {
      result_.add_failure("Gate count error: total gate count exceeds limit " +
                          std::to_string(max_size));
      return false;
    }
  }

  // 电路深度不超过 max_depth
  // 深度 = 关键路径长度，每个门使其所有目标比特的深度 +1
  if (max_depth != -1) {
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
    if (circuit_depth > max_depth) {
      result_.add_failure("Depth error: circuit depth " +
                          std::to_string(circuit_depth) + " exceeds limit " +
                          std::to_string(max_depth));
      return false;
    }
  }
  return true;
}

}  // namespace qcos
