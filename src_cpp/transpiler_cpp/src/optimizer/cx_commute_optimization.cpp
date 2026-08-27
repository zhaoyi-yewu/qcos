/*
 * Copyright header - see existing files for full text
 */

#include "optimizer/cx_commute_optimization.h"

#include <algorithm>
#include <unordered_map>

#include "circuit/dag_node.h"

namespace qcos {

namespace {

bool qubit_in_qargs(const std::vector<int>& qargs, int qubit) {
  return std::find(qargs.begin(), qargs.end(), qubit) != qargs.end();
}

}  // namespace

CxCommuteOptimization::CxCommuteOptimization(bool verbose)
    : cx_commute_ctrl_templates_(generate_cx_commute_ctrl_templates()),
      cx_commute_targ_templates_(generate_cx_commute_targ_templates()),
      verbose_(verbose) {}

int CxCommuteOptimization::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const auto op_counts = dag.count_ops();
  auto cx_iterator = op_counts.find("cx");
  if (cx_iterator == op_counts.end() || cx_iterator->second <= 1) {
    return 0;
  }

  std::vector<const OptimizingTemplate*> ctrl_templates;
  std::vector<const OptimizingTemplate*> targ_templates;
  ctrl_templates.reserve(cx_commute_ctrl_templates_.size());
  for (const auto& tpl : cx_commute_ctrl_templates_) {
    ctrl_templates.push_back(&tpl);
  }
  targ_templates.reserve(cx_commute_targ_templates_.size());
  for (const auto& tpl : cx_commute_targ_templates_) {
    targ_templates.push_back(&tpl);
  }

  if (ctrl_templates.empty() && targ_templates.empty()) {
    return 0;
  }

  int reduced = 0;
  for (DAGOpNode* node : dag.topological_op_nodes()) {
    // 跳过已删除节点、非 CX 节点
    if (!node || node->flag == -1 || node->name() != "cx") {
      continue;
    }

    DAGOpNode* current_ctrl_node = node;
    DAGOpNode* current_targ_node = node;
    const int control_qubit = node->qargs[0];
    const int target_qubit = node->qargs[1];

    while (true) {
      // 沿控制位线路取下一个节点
      DAGOpNode* next_ctrl_node =
          dag.get_next_op_on_qubit(current_ctrl_node, control_qubit);
      if (!next_ctrl_node) {
        // 控制位到达线路末端
        break;
      }
      // 沿目标位线路取下一个节点
      DAGOpNode* next_targ_node =
          dag.get_next_op_on_qubit(current_targ_node, target_qubit);
      if (!next_targ_node) {
        // 目标位到达线路末端
        break;
      }

      // 相邻的 CX 门且 qargs 相同：直接删除这两个 CX
      if (next_ctrl_node == next_targ_node && next_ctrl_node->name() == "cx" &&
          next_ctrl_node->qargs == node->qargs) {
        dag.remove_op_node(next_ctrl_node);
        dag.remove_op_node(node);
        reduced += 2;
        break;
      }

      std::unordered_map<int, DAGOpNode*> mapping;

      // 尝试控制位模板匹配
      for (const OptimizingTemplate* template_ptr : ctrl_templates) {
        mapping = template_ptr->compare(dag, next_ctrl_node, control_qubit);
        if (mapping.empty()) {
          continue;
        }

        // 控制位的模版中不能包括 CX 门的目标位
        bool reach_target = false;
        for (const auto& [_, mapped_node] : mapping) {
          if (qubit_in_qargs(mapped_node->qargs, target_qubit)) {
            reach_target = true;
            break;
          }
        }
        if (reach_target) {
          mapping.clear();
          continue;
        }

        // 模板匹配成功：找到模板出口节点，更新控制位跟踪指针
        const std::map<int, DAGOutNode*>& ctrl_output_map =
            template_ptr->template_dag_.get_output_map();
        DAGNode* ctrl_last =
            template_ptr->template_dag_
                .predecessors(ctrl_output_map.at(template_ptr->anchor_))
                .front();
        current_ctrl_node = mapping.at(ctrl_last->node_id());
        break;
      }

      if (!mapping.empty()) {
        continue;
      }

      // 尝试目标位模板匹配
      for (const OptimizingTemplate* template_ptr : targ_templates) {
        mapping = template_ptr->compare(dag, next_targ_node, target_qubit);
        if (mapping.empty()) {
          continue;
        }

        bool reach_control = false;
        for (const auto& [_, mapped_node] : mapping) {
          if (qubit_in_qargs(mapped_node->qargs, control_qubit)) {
            reach_control = true;
            break;
          }
        }
        if (reach_control) {
          mapping.clear();
          continue;
        }

        // 模板匹配成功：更新目标位跟踪指针
        const std::map<int, DAGOutNode*>& targ_output_map =
            template_ptr->template_dag_.get_output_map();
        DAGNode* targ_last =
            template_ptr->template_dag_
                .predecessors(targ_output_map.at(template_ptr->anchor_))
                .front();
        current_targ_node = mapping.at(targ_last->node_id());
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
