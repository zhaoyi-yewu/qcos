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
#include <iostream>
#include <unordered_map>

#include "circuit/dag_node.h"

namespace qcos {

AdjacentPhaseOptPass::AdjacentPhaseOptPass(bool verbose)
    : verbose_(verbose),
      phase_gates_({"rx", "ry", "rz", "crx", "cry", "crz", "u1"}) {}

int AdjacentPhaseOptPass::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  int reduced = 0;
  const std::unordered_map<std::string, int> op_counts = dag.count_ops();
  // 电路中实际存在的相位门集合，后续仅优化这些门
  std::set<std::string> phase_gates;
  for (const std::string& gate_name : phase_gates_) {
    if (op_counts.find(gate_name) != op_counts.end()) {
      phase_gates.insert(gate_name);
    }
  }

  // 没有可优化的相位门时直接返回，避免全量拓扑遍历
  if (phase_gates.empty()) {
    return reduced;
  }

  for (DAGOpNode* node : dag.topological_op_nodes()) {
    if (!node || phase_gates.count(node->name()) == 0) {
      continue;
    }

    const std::vector<DAGNode*> successors = dag.successors(node);
    if (successors.empty()) {
      continue;
    }

    DAGOpNode* next_node = dynamic_cast<DAGOpNode*>(successors.front());
    if (!next_node) {
      continue;
    }
    // 判断两个门是否相邻且作用在同一量子位上，若是则合并成一个门，并将参数相加。
    if (node->op->name == next_node->op->name &&
        node->op->targets == next_node->op->targets) {
      next_node->op->arg_value[0] += node->op->arg_value[0];
      dag.remove_op_node(node);
      ++reduced;
      // Remove gate if merged angle is ~0 (mod 2π)
      constexpr double kTwoPi = 2.0 * M_PI;
      double mod_angle = std::fmod(next_node->op->arg_value[0], kTwoPi);
      if (mod_angle < 0) mod_angle += kTwoPi;
      if (mod_angle < 1e-8 || mod_angle > kTwoPi - 1e-8) {
        dag.remove_op_node(next_node);
        ++reduced;
      }
    }
  }

  if (verbose_) {
    std::clog << name() << ": " << reduced << " gates reduced\n";
  }
  return reduced;
}

}  // namespace qcos
