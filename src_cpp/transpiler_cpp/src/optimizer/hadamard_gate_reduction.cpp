/*
 * Copyright header - see existing files for full text
 */

#include "optimizer/hadamard_gate_reduction.h"

#include <algorithm>
#include <unordered_map>

#include "circuit/dag_node.h"

namespace qcos {

namespace {

std::set<std::string> intersect_basis_with_counts(
    const std::set<std::string>& basis_gates,
    const std::unordered_map<std::string, int>& op_counts) {
  std::set<std::string> filtered;
  for (const std::string& gate_name : basis_gates) {
    if (op_counts.find(gate_name) != op_counts.end()) {
      filtered.insert(gate_name);
    }
  }
  return filtered;
}

}  // namespace

HadamardGateReduction::HadamardGateReduction(bool verbose)
    : hadamard_templates_(generate_hadamard_gate_templates()),
      verbose_(verbose) {}

int HadamardGateReduction::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const auto op_counts = dag.count_ops();
  auto h_it = op_counts.find("h");
  if (h_it == op_counts.end() || h_it->second <= 1) {
    return 0;
  }

  std::vector<const OptimizingTemplate*> templates;
  if (basis_gates) {
    templates = filter_templates_by_basis(
        hadamard_templates_,
        intersect_basis_with_counts(*basis_gates, op_counts));
  } else {
    templates.reserve(hadamard_templates_.size());
    for (const auto& tpl : hadamard_templates_) {
      templates.push_back(&tpl);
    }
  }

  if (templates.empty()) {
    return 0;
  }

  int reduced = 0;
  for (const OptimizingTemplate* tpl : templates) {
    // 遍历当前 DAG 中所有门节点，对每个节点尝试模板匹配与替换
    for (DAGOpNode* node : dag.topological_op_nodes()) {
      if (!node || node->flag == -1) continue;

      auto mapping = tpl->compare(dag, node, node->qargs[0]);
      if (mapping.empty()) continue;

      // 从匹配节点对中提取 block_nodes 和 qubit_mapping
      std::vector<DAGOpNode*> block_nodes;
      std::unordered_map<int, int> qubit_mapping;

      for (const auto& [t_id, c_node] : mapping) {
        block_nodes.push_back(c_node);
        // 从模板节点和电路节点的 qargs 对应关系重建 qubit_mapping
        const DAGNode* t_node_raw = tpl->template_dag_.node(t_id);
        const auto* t_op = dynamic_cast<const DAGOpNode*>(t_node_raw);
        if (t_op) {
          for (size_t i = 0; i < t_op->qargs.size(); i++) {
            qubit_mapping[t_op->qargs[i]] = c_node->qargs[i];
          }
        }
      }

      // 用 replacement DAG 替换匹配节点块
      if (tpl->replacement_dag_.has_value()) {
        dag.replace_block_with_dag(block_nodes, *tpl->replacement_dag_,
                                   qubit_mapping);
      }

      reduced += tpl->weight_;
    }
  }

  if (verbose_) {
    std::clog << name() << ": " << reduced << " gates reduced\n";
  }
  return reduced;
}

}  // namespace qcos
