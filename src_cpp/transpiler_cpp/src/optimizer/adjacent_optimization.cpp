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

#include "optimizer/adjacent_optimization.h"

#include <algorithm>
#include <unordered_map>

#include "circuit/dag_node.h"

namespace qcos {

namespace {

bool has_any_gate(const std::unordered_map<std::string, int>& op_counts,
                  const std::set<std::string>& gate_names) {
  for (const std::string& gate_name : gate_names) {
    if (op_counts.find(gate_name) != op_counts.end()) {
      return true;
    }
  }
  return false;
}

DAGOpNode* as_op_node(DAGNode* node) { return dynamic_cast<DAGOpNode*>(node); }

}  // namespace

AdjacentPhaseOptPass::AdjacentPhaseOptPass()
    : phase_gates_({"rx", "ry", "rz", "crx", "cry", "crz", "u1"}) {}

int AdjacentPhaseOptPass::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  int reduced = 0;
  const std::set<std::string> rz_phase_gates = {"s", "sdg", "t", "tdg", "z"};

  const std::unordered_map<std::string, int> op_counts = dag.count_ops();
  // 电路中实际存在的相位门集合，后续仅优化这些门
  std::set<std::string> phase_gates;
  for (const std::string& gate_name : phase_gates_) {
    if (op_counts.find(gate_name) != op_counts.end()) {
      phase_gates.insert(gate_name);
    }
  }

  // 是否存在离散相位门s、sdg、t、tdg、z
  const bool has_discrete_rz_phase_gates =
      has_any_gate(op_counts, rz_phase_gates);
  if (has_discrete_rz_phase_gates) {
    phase_gates.insert("rz");
  }

  if (basis_gates) {
    // 若传参了 basis_gates，则仅优化这些门
    std::set<std::string> filtered_phase_gates;
    for (const std::string& gate_name : phase_gates) {
      if (basis_gates->count(gate_name) > 0) {
        filtered_phase_gates.insert(gate_name);
      }
    }
    phase_gates = std::move(filtered_phase_gates);
  }

  if (has_discrete_rz_phase_gates) {
    dag.parameterize_all_rz();
  }

  for (DAGOpNode* node : dag.topological_op_nodes()) {
    if (!node || phase_gates.count(node->name()) == 0) {
      continue;
    }

    const std::vector<DAGNode*> successors = dag.successors(node);
    if (successors.empty()) {
      continue;
    }

    DAGOpNode* next_node = as_op_node(successors.front());
    if (!next_node) {
      continue;
    }
    // 判断两个门是否相邻且作用在同一量子位上，若是则合并成一个门，并将参数相加。
    if (node->op->name == next_node->op->name &&
        node->op->targets == next_node->op->targets) {
      next_node->op->arg_value[0] += node->op->arg_value[0];
      dag.remove_op_node(node);
      ++reduced;
    }
  }

  const std::unordered_map<std::string, int> final_op_counts = dag.count_ops();
  // 将离散相位门重写回s, t, z等
  if (final_op_counts.find("rz") != final_op_counts.end() &&
      // 判断rz_phase_gates是否是basis_gates的子集
      (!basis_gates ||
       std::includes(basis_gates->begin(), basis_gates->end(),
                     rz_phase_gates.begin(), rz_phase_gates.end()))) {
    dag.deparameterize_all_rz();
  }

  return reduced;
}

}  // namespace qcos