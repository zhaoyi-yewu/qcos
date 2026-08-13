/*
 * Copyright header - see existing files for full text
 */

#include "optimizer/rz_commute_optimization.h"

#include <algorithm>
#include <cmath>
#include <unordered_map>

#include "circuit/dag_node.h"

namespace qcos {

RzCommuteOptimization::RzCommuteOptimization(bool verbose)
    : rz_commute_templates_(generate_rz_commute_templates()),
      verbose_(verbose) {}

int RzCommuteOptimization::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const auto op_counts = dag.count_ops();
  auto rz_iterator = op_counts.find("rz");
  // 少于 2 个 Rz 门则无对消可能
  if (rz_iterator == op_counts.end() || rz_iterator->second <= 1) {
    return 0;
  }

  std::vector<const OptimizingTemplate*> templates;
  templates.reserve(rz_commute_templates_.size());
  for (const auto& tpl : rz_commute_templates_) {
    templates.push_back(&tpl);
  }

  if (templates.empty()) {
    return 0;
  }

  int reduced = 0;
  for (DAGOpNode* node : dag.topological_op_nodes()) {
    // 跳过已删除节点、非 Rz 节点
    if (!node || node->flag == -1 || node->name() != "rz") {
      continue;
    }

    // 角度接近 0 的 Rz 等效于恒等门，直接删除
    if (!node->op->arg_value.empty() &&
        std::abs(node->op->arg_value[0]) <= 1e-8) {
      dag.remove_op_node(node);
      ++reduced;
      continue;
    }

    // 沿 Rz 所在量子比特向后继方向跟踪，尝试与下一个 Rz 合并
    DAGOpNode* current_node = node;
    const int qubit_idx = node->qargs[0];
    while (true) {
      DAGOpNode* next_node = dag.get_next_op_on_qubit(current_node, qubit_idx);
      // 到达线路末端，无法继续
      if (!next_node) {
        break;
      }

      // 下一个门也是 Rz：直接合并角度到 next_node，删除当前 Rz
      if (next_node->name() == "rz") {
        next_node->op->arg_value[0] += node->op->arg_value[0];
        dag.remove_op_node(node);
        ++reduced;
        break;
      }

      // 尝试模板匹配
      std::unordered_map<int, DAGOpNode*> mapping;
      for (const OptimizingTemplate* template_ptr : templates) {
        mapping = template_ptr->compare(dag, next_node, qubit_idx);
        if (mapping.empty()) {
          continue;
        }

        const std::map<int, DAGOutNode*>& output_map =
            template_ptr->template_dag_.get_output_map();
        DAGNode* last_template_node =
            template_ptr->template_dag_
                .predecessors(output_map.at(template_ptr->anchor_))
                .front();
        current_node = mapping.at(last_template_node->node_id());
        break;
      }

      if (mapping.empty()) {
        break;
      }
    }
  }

  if (verbose_) {
    std::clog << name() << ": " << reduced << " gates reduced\n";
  }
  return reduced;
}

}  // namespace qcos
