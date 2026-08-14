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

#include "verify/cmss_verifier.h"

#include <iostream>
#include <unordered_set>

#include "mapping/mapping_utils.h"

namespace qcos {

CMSSVerifier::CMSSVerifier(const VerifyParams& params) : QPUVerifier(params) {}

VerifyResult CMSSVerifier::verify(const std::string& qasm_string,
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

bool CMSSVerifier::check_qasm_syntax2(const std::string& qasm_string) const {
  return QPUVerifier::check_qasm_syntax2(qasm_string);
}

bool CMSSVerifier::check_topology() const {
  // 比特数校验：电路实际使用比特数不超过真机可用比特数
  if (parsed_num_qubits_ > max_qubits_) {
    result_.add_failure("Topology error: circuit requires " +
                        std::to_string(parsed_num_qubits_) +
                        " qubits, but chip only has " +
                        std::to_string(max_qubits_));
    return false;
  }

  // target_bits 越界 + 去重 + 数量校验（target_bits 为空时自动跳过）
  if (!check_target_bits_range_and_count()) return false;

  // 全单比特门：比特数 + target_bits 上面已校验，直接通过（不检查连通性）
  if (!has_multi_qubit_gates()) return true;

  // 含多比特门
  if (target_bits_.empty()) {
    // 无 target_bits：最大连通分量节点数 >= 电路比特数
    return check_largest_component_sufficient(parsed_num_qubits_);
  }

  // 有 target_bits: target_bits 必须构成单一连通图
  {
    std::unordered_set<int> target_set(target_bits_.begin(),
                                       target_bits_.end());
    std::vector<std::pair<int, int>> induced_edges;
    for (const auto& [qubit_a, qubit_b] : coupling_list_) {
      if (target_set.count(qubit_a) && target_set.count(qubit_b)) {
        induced_edges.emplace_back(qubit_a, qubit_b);
      }
    }
    auto comp_map = find_connected_components(induced_edges);
    // 所有 target_bits 必须属于同一连通分量
    int root = -1;
    for (int bit : target_bits_) {
      auto it = comp_map.find(bit);
      if (it == comp_map.end()) {
        // 该比特在诱导子图中无邻接边 -> 不连通
        result_.add_failure(
            "Topology error: target_bits do not form a connected graph");
        return false;
      }
      if (root == -1) {
        root = it->second;
      } else if (it->second != root) {
        result_.add_failure(
            "Topology error: target_bits do not form a connected graph");
        return false;
      }
    }
  }
  return true;
}

bool CMSSVerifier::check_depth_and_gate_count() const {
  return QPUVerifier::check_depth_and_gate_count(200, 200, 500);
}

}  // namespace qcos
