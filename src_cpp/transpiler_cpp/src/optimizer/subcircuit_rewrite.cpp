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

#include "optimizer/subcircuit_rewrite.h"

#include <memory>
#include <unordered_map>
#include <utility>

#include "circuit/gate_operation.h"

namespace qcos {

namespace {

bool contains_all(const std::unordered_map<std::string, int>& op_counts,
                  const std::set<std::string>& gates) {
  for (const std::string& gate_name : gates) {
    if (op_counts.find(gate_name) == op_counts.end()) {
      return false;
    }
  }
  return true;
}

}  // namespace

std::set<std::string> EquivalencePass::get_equivalence_circuits(
    const DAGCircuit& dag,
    const std::optional<std::set<std::string>>& basis_gates) const {
  const std::unordered_map<std::string, int> op_counts = dag.count_ops();
  std::set<std::string> templates;

  if (basis_gates) {
    if (basis_gates->count("h") > 0 && basis_gates->count("z") > 0 &&
        basis_gates->count("x") > 0) {
      templates.insert("h-z-h");
    }
    if (basis_gates->count("h") > 0 && basis_gates->count("x") > 0 &&
        basis_gates->count("z") > 0) {
      templates.insert("h-x-h");
    }
    if (basis_gates->count("x") > 0 && basis_gates->count("ry") > 0) {
      templates.insert("x-ry-x");
    }
    return templates;
  }

  if (contains_all(op_counts, {"h", "z"})) {
    templates.insert("h-z-h");
  }
  if (contains_all(op_counts, {"h", "x"})) {
    templates.insert("h-x-h");
  }
  if (contains_all(op_counts, {"x", "ry"})) {
    templates.insert("x-ry-x");
  }
  return templates;
}

int EquivalencePass::replace_equivalence_circuits(
    DAGCircuit& dag, const std::set<std::string>& enabled_templates) const {
  if (enabled_templates.empty()) {
    return 0;
  }

  const std::vector<DAGOpNode*> nodes = dag.topological_op_nodes();
  std::vector<std::shared_ptr<BaseOperation>> rewritten_ir;
  rewritten_ir.reserve(nodes.size());

  int reduced = 0;
  size_t index = 0;
  while (index < nodes.size()) {
    if (index + 2 < nodes.size()) {
      DAGOpNode* first = nodes[index];
      DAGOpNode* second = nodes[index + 1];
      DAGOpNode* third = nodes[index + 2];

      const bool same_single_qubit_targets = first->qargs.size() == 1 &&
                                             first->qargs == second->qargs &&
                                             second->qargs == third->qargs;
      if (same_single_qubit_targets) {
        const std::vector<int>& targets = first->op->targets;

        if (enabled_templates.count("h-z-h") > 0 && first->name() == "h" &&
            second->name() == "z" && third->name() == "h") {
          rewritten_ir.push_back(create_gate("x", targets));
          reduced += 2;
          index += 3;
          continue;
        }

        if (enabled_templates.count("h-x-h") > 0 && first->name() == "h" &&
            second->name() == "x" && third->name() == "h") {
          rewritten_ir.push_back(create_gate("z", targets));
          reduced += 2;
          index += 3;
          continue;
        }

        if (enabled_templates.count("x-ry-x") > 0 && first->name() == "x" &&
            second->name() == "ry" && third->name() == "x" &&
            !second->op->arg_value.empty()) {
          rewritten_ir.push_back(
              create_gate("ry", targets, {-second->op->arg_value[0]}));
          reduced += 2;
          index += 3;
          continue;
        }
      }
    }

    // The old DAG is discarded after a successful rewrite, so untouched
    // operations can be forwarded into the rebuilt IR without deep cloning.
    rewritten_ir.push_back(nodes[index]->op);
    ++index;
  }

  if (reduced > 0) {
    dag = DAGCircuit::ir_to_dag(rewritten_ir);
  }
  return reduced;
}

int EquivalencePass::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const std::set<std::string> enabled_templates =
      get_equivalence_circuits(dag, basis_gates);
  return replace_equivalence_circuits(dag, enabled_templates);
}

}  // namespace qcos