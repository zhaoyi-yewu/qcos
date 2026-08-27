/*
 * ----------------------------------------------------------------------
 * Copyright(c) 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 *      EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 *      MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include "optimizer/unitary_synthesis.h"

#include <algorithm>
#include <iostream>
#include <array>
#include <cassert>
#include <cmath>
#include <stdexcept>
#include <unordered_map>
#include <vector>

#include "circuit/gate_operation.h"
#include "optimizer/collect_block.h"

namespace qcos {

// ========================================================================
// decompose_unitary - 主接口函数
// ========================================================================

std::vector<std::shared_ptr<BaseOperation>> decompose_unitary(
    const CMatrix& unitary,
    const std::set<std::string>& basis_gates,
    const std::vector<int>& qubits) {

  if (unitary.empty() || unitary[0].empty()) {
    throw std::invalid_argument("decompose_unitary: empty matrix");
  }

  if (!matrix_utils::is_unitary(unitary, 1e-8)) {
    throw std::invalid_argument("decompose_unitary: matrix is not unitary");
  }

  size_t dim = unitary.size();
  if (dim != unitary[0].size()) {
    throw std::invalid_argument("decompose_unitary: matrix is not square");
  }

  std::optional<std::set<std::string>> bg_opt = basis_gates;

  if (dim == 2) {
    int qubit = qubits.empty() ? 0 : qubits[0];
    return single_qubit_unitary_to_basis(unitary, qubit, bg_opt);
  } else if (dim == 4) {
    int q0 = qubits.size() >= 1 ? qubits[0] : 0;
    int q1 = qubits.size() >= 2 ? qubits[1] : 1;
    return two_qubit_unitary_to_basis(unitary, q0, q1, bg_opt);
  } else {
    throw std::invalid_argument(
        "decompose_unitary: unsupported dimension " + std::to_string(dim) +
        " (only 2x2 and 4x4 are supported)");
  }
}

// ========================================================================
// UnitarySynthesis - 酉综合 Pass
// ========================================================================

UnitarySynthesis::UnitarySynthesis(
    const std::optional<std::set<std::string>>& basis_gates,
    double approximation_degree,
    size_t max_block_size,
    bool verbose)
    : basis_gates_(basis_gates),
      approximation_degree_(approximation_degree),
      max_block_size_(max_block_size),
      verbose_(verbose) {}

UnitarySynthesis::OpList UnitarySynthesis::synthesize_1q(
    const CMatrix& u, int qubit) {
  return single_qubit_unitary_to_basis(u, qubit, basis_gates_);
}

UnitarySynthesis::OpList UnitarySynthesis::synthesize_2q(
    const CMatrix& u, int q0, int q1) {
  return two_qubit_unitary_to_basis(u, q0, q1, basis_gates_);
}

UnitarySynthesis::OpList UnitarySynthesis::synthesize_block(
    const CMatrix& unitary, const std::vector<int>& qubits) {
  if (unitary.size() == 2 && unitary[0].size() == 2) {
    if (qubits.empty()) {
      throw std::invalid_argument("synthesize_block: 2x2 matrix requires 1 qubit");
    }
    return synthesize_1q(unitary, qubits[0]);
  } else if (unitary.size() == 4 && unitary[0].size() == 4) {
    if (qubits.size() < 2) {
      throw std::invalid_argument("synthesize_block: 4x4 matrix requires 2 qubits");
    }
    return synthesize_2q(unitary, qubits[0], qubits[1]);
  } else {
    throw std::invalid_argument(
        "synthesize_block: unsupported dimension " +
        std::to_string(unitary.size()));
  }
}

namespace {

struct BlockProcessor {
  DAGCircuit& dag;
  const std::optional<std::set<std::string>>& bg;
  size_t max_block_size;
  UnitarySynthesis& synth;

  int process_block(const std::vector<DAGOpNode*>& block) {
    std::vector<int> qubits;
    std::unordered_map<int, int> qubit_mapping;
    for (DAGOpNode* node : block) {
      for (int q : node->qargs) {
        if (qubit_mapping.find(q) == qubit_mapping.end()) {
          qubit_mapping[q] = static_cast<int>(qubits.size());
          qubits.push_back(q);
        }
      }
    }

    if (qubits.size() > max_block_size) return 0;

    CMatrix unitary = matrix_utils::compute_block_unitary(block, qubit_mapping);
    auto replacement = synth.synthesize_block(unitary, qubits);

    bool has_non_basis_gate = false;
    if (bg.has_value()) {
      for (DAGOpNode* node : block) {
        if (bg->count(node->name()) == 0) {
          has_non_basis_gate = true;
          break;
        }
      }
    }

    bool all_basis = true;
    if (bg.has_value()) {
      for (const auto& op : replacement) {
        if (bg->count(op->name) == 0) { all_basis = false; break; }
      }
    }

    bool should_replace = false;
    if (replacement.empty() && has_non_basis_gate) {
      should_replace = true;
    } else if (!replacement.empty()) {
      if (replacement.size() < block.size()) {
        should_replace = true;
      } else if (has_non_basis_gate && all_basis) {
        should_replace = true;
      }
    }

    if (should_replace) {
      DAGCircuit replacement_dag;
      replacement_dag.add_qubits(static_cast<int>(qubits.size()));
      for (const auto& op : replacement) {
        auto local_op = op->clone();
        std::vector<int> local_targets;
        for (int t : op->targets) {
          local_targets.push_back(qubit_mapping[t]);
        }
        local_op->setTargets(local_targets);
        replacement_dag.apply_operation_back(local_op);
      }

      std::unordered_map<int, int> local_to_global;
      for (const auto& [global_q, local_idx] : qubit_mapping) {
        local_to_global[local_idx] = global_q;
      }

      dag.replace_block_with_dag(block, replacement_dag, local_to_global);
      return static_cast<int>(block.size()) - static_cast<int>(replacement.size());
    }

    return 0;
  }
};

}  // namespace

int UnitarySynthesis::run(
    DAGCircuit& dag,
    const std::optional<std::set<std::string>>& basis_gates) {
  const auto& bg = basis_gates.has_value() ? basis_gates : basis_gates_;

  int total_replaced = 0;

  // Phase 1: Optimize 1Q gate runs
  std::set<std::string> collect_1q;
  for (const auto& g : Constant::SINGLE_QUBIT_GATE_LIST) {
    collect_1q.insert(g);
  }

  while (true) {
    auto blocks = collect_all_matching_blocks(dag, collect_1q, 2);
    if (blocks.empty()) break;

    bool any_replaced = false;
    for (const auto& block : blocks) {
      BlockProcessor proc{dag, bg, max_block_size_, *this};
      int diff = proc.process_block(block);
      if (diff != 0) {
        total_replaced += diff;
        any_replaced = true;
        break;
      }
    }
    if (!any_replaced) break;
  }

  // Phase 2: Optimize 2Q blocks
  std::set<std::string> collect_all;
  for (const auto& g : Constant::ALL_GATE_LIST) {
    collect_all.insert(g);
  }

  while (true) {
    auto blocks = collect_all_matching_blocks(dag, collect_all, 2);
    if (blocks.empty()) break;

    bool any_replaced = false;
    for (const auto& block : blocks) {
      BlockProcessor proc{dag, bg, max_block_size_, *this};
      int diff = proc.process_block(block);
      if (diff != 0) {
        total_replaced += diff;
        any_replaced = true;
        break;
      }
    }
    if (!any_replaced) break;
  }

  if (verbose_) {
    std::clog << name() << ": " << total_replaced << " gates reduced\n";
  }
  return total_replaced;
}

// ========================================================================
// ConsolidateBlocks Pass
// ========================================================================

ConsolidateBlocks::ConsolidateBlocks(
    const std::optional<std::set<std::string>>& basis_gates,
    double approximation_degree,
    size_t min_block_size)
    : basis_gates_(basis_gates),
      approximation_degree_(approximation_degree),
      min_block_size_(min_block_size) {}

int ConsolidateBlocks::run(
    DAGCircuit& dag,
    const std::optional<std::set<std::string>>& basis_gates) {
  const auto& bg = basis_gates.has_value() ? basis_gates : basis_gates_;

  std::set<std::string> collect_gates;
  for (const auto& g : Constant::ALL_GATE_LIST) {
    collect_gates.insert(g);
  }

  int total_replaced = 0;

  while (true) {
    auto blocks = collect_all_matching_blocks(dag, collect_gates, min_block_size_);
    if (blocks.empty()) break;

    bool any_replaced = false;

    for (const auto& block : blocks) {
      std::vector<int> qubits;
      std::unordered_map<int, int> qubit_mapping;
      for (DAGOpNode* node : block) {
        for (int q : node->qargs) {
          if (qubit_mapping.find(q) == qubit_mapping.end()) {
            qubit_mapping[q] = static_cast<int>(qubits.size());
            qubits.push_back(q);
          }
        }
      }

      if (qubits.size() > 2) continue;

      CMatrix unitary = matrix_utils::compute_block_unitary(block, qubit_mapping);

      UnitarySynthesis synthesizer(bg, approximation_degree_);
      auto replacement = synthesizer.synthesize_block(unitary, qubits);

      bool consolidate_has_non_basis = false;
      if (bg.has_value()) {
        for (DAGOpNode* node : block) {
          if (bg->count(node->name()) == 0) {
            consolidate_has_non_basis = true;
            break;
          }
        }
      }

      bool consolidate_should_replace = false;
      if (consolidate_has_non_basis) {
        consolidate_should_replace = true;
      } else if (!replacement.empty() && replacement.size() < block.size()) {
        consolidate_should_replace = true;
      }

      if (consolidate_should_replace) {
        DAGCircuit replacement_dag;
        replacement_dag.add_qubits(static_cast<int>(qubits.size()));
        for (const auto& op : replacement) {
          auto local_op = op->clone();
          std::vector<int> local_targets;
          for (int t : op->targets) {
            local_targets.push_back(qubit_mapping[t]);
          }
          local_op->setTargets(local_targets);
          replacement_dag.apply_operation_back(local_op);
        }

        std::unordered_map<int, int> local_to_global;
        for (const auto& [global_q, local_idx] : qubit_mapping) {
          local_to_global[local_idx] = global_q;
        }

        dag.replace_block_with_dag(block, replacement_dag, local_to_global);
        total_replaced += static_cast<int>(block.size()) -
                          static_cast<int>(replacement.size());
        any_replaced = true;
        break;
      }
    }

    if (!any_replaced) break;
  }

  return total_replaced;
}

}  // namespace qcos
