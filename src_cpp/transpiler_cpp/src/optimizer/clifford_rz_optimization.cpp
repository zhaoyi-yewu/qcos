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

#include "optimizer/clifford_rz_optimization.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <set>
#include <unordered_map>
#include <unordered_set>

#include "optimizer/collect_block.h"

namespace qcos {

namespace {

/**
 * @brief 取 basis_gates 与 DAG 中实际存在门集合的交集
 *
 * 提前剔除 DAG 中不存在的 basis gate，减少后续主循环中无效的模板匹配次数。
 * 例如 DAG 中没有 h 门时，所有依赖 h 的模板在过滤阶段就被排除，
 * 避免在 Rz 节点的内层循环中对每个模板做注定失败的 compare 调用。
 *
 * @param basis_gates 候选 basis gate 集合
 * @param op_counts DAG 中的门计数
 * @return basis_gates 中在 DAG 里实际存在的门集合
 */
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

/**
 * @brief 判断指定 qubit 是否在节点的量子比特参数列表中
 * @param qargs 节点的量子比特参数列表
 * @param qubit 待判断的量子比特编号
 * @return true qubit 在 qargs 中
 * @return false qubit 不在 qargs 中
 */
bool qubit_in_qargs(const std::vector<int>& qargs, int qubit) {
  return std::find(qargs.begin(), qargs.end(), qubit) != qargs.end();
}

}  // namespace

CliffordRzOptimization::CliffordRzOptimization(bool verbose)
    : hadamard_templates_(generate_hadamard_gate_templates()),
      single_qubit_gate_templates_(generate_single_qubit_gate_templates()),
      cnot_ctrl_template_(generate_cnot_ctrl_templates()),
      cnot_targ_template_(generate_cnot_targ_templates()),
      verbose_(verbose) {}

int CliffordRzOptimization::reduce_hadamard_gates(
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

  return reduced;
}

DAGOpNode* CliffordRzOptimization::get_next_node_on_specific_qubit(
    DAGCircuit& dag, DAGOpNode* cur_node, int qubit) const {
  // 参数检查：当前节点必须存在且包含指定 qubit
  if (!cur_node || !qubit_in_qargs(cur_node->qargs, qubit)) {
    throw std::invalid_argument(std::to_string(qubit) +
                                " is not in qargs of current node.");
  }

  // 沿指定 qubit 的出边查找第一个后继节点，DAGOutNode 返回 nullptr
  DAGNode* next_node = dag.get_multi_graph().find_first_successor_by_edge(
      cur_node->node_id(),
      [qubit](int edge_wire) { return edge_wire == qubit; });
  return dynamic_cast<DAGOpNode*>(next_node);
}

int CliffordRzOptimization::cancel_single_qubit_gates(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const auto op_counts = dag.count_ops();
  auto rz_iterator = op_counts.find("rz");
  // 少于 2 个 Rz 门则无对消可能
  if (rz_iterator == op_counts.end() || rz_iterator->second <= 1) {
    return 0;
  }

  std::vector<const OptimizingTemplate*> templates;
  if (basis_gates) {
    templates = filter_templates_by_basis(
        single_qubit_gate_templates_,
        intersect_basis_with_counts(*basis_gates, op_counts));
  } else {
    templates.reserve(single_qubit_gate_templates_.size());
    for (const auto& tpl : single_qubit_gate_templates_) {
      templates.push_back(&tpl);
    }
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
      DAGOpNode* next_node =
          get_next_node_on_specific_qubit(dag, current_node, qubit_idx);
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

  return reduced;
}

int CliffordRzOptimization::cancel_two_qubit_gates(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const auto op_counts = dag.count_ops();
  auto cx_iterator = op_counts.find("cx");
  if (cx_iterator == op_counts.end() || cx_iterator->second <= 1) {
    return 0;
  }

  // 根据 DAG 中实际存在的门过滤模板，减少无效匹配
  std::vector<const OptimizingTemplate*> ctrl_templates;
  std::vector<const OptimizingTemplate*> targ_templates;
  if (basis_gates) {
    const std::set<std::string> filtered_basis =
        intersect_basis_with_counts(*basis_gates, op_counts);
    ctrl_templates =
        filter_templates_by_basis(cnot_ctrl_template_, filtered_basis);
    targ_templates =
        filter_templates_by_basis(cnot_targ_template_, filtered_basis);
  } else {
    ctrl_templates.reserve(cnot_ctrl_template_.size());
    for (const auto& tpl : cnot_ctrl_template_) {
      ctrl_templates.push_back(&tpl);
    }
    targ_templates.reserve(cnot_targ_template_.size());
    for (const auto& tpl : cnot_targ_template_) {
      targ_templates.push_back(&tpl);
    }
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
      DAGOpNode* next_ctrl_node = get_next_node_on_specific_qubit(
          dag, current_ctrl_node, control_qubit);
      if (!next_ctrl_node) {
        // 控制位到达线路末端
        break;
      }
      // 沿目标位线路取下一个节点
      DAGOpNode* next_targ_node = get_next_node_on_specific_qubit(
          dag, current_targ_node, target_qubit);
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
          continue;  // 当前模板不匹配，尝试下一个
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

  return reduced;
}

int CliffordRzOptimization::merge_rotations(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const auto op_counts = dag.count_ops();
  auto rz_it = op_counts.find("rz");
  if (rz_it == op_counts.end() || rz_it->second <= 1) {
    return 0;
  }

  // 确定需要收集的门集合，与 basis_gates 取交集
  std::set<std::string> collect_gates = {"cx", "rz", "x"};
  if (basis_gates) {
    std::set<std::string> filtered;
    for (const auto& g : collect_gates) {
      if (basis_gates->count(g)) {
        filtered.insert(g);
      }
    }
    collect_gates = std::move(filtered);
  }
  if (collect_gates.size() <= 1) {
    return 0;
  }

  auto blocks = collect_all_matching_blocks(dag, collect_gates);

  int reduced = 0;
  for (auto& block : blocks) {
    reduced += parse_cnot_rz_circuit(block, dag);
  }

  return reduced;
}

int CliffordRzOptimization::parse_cnot_rz_circuit(
    const std::vector<DAGOpNode*>& node_list, DAGCircuit& dag) {
  // 相位多项式: 单项式 -> 累加相位
  std::unordered_map<int, double> phases;
  // 每个单项式的第一个 Rz 门: 单项式 -> (节点, 符号)
  std::unordered_map<int, std::pair<DAGOpNode*, int>> first_rz;
  // 每个量子位当前的线性函数
  std::unordered_map<int, int> cur_phases;
  // 待删除的重复 Rz 节点
  std::vector<DAGOpNode*> to_remove;
  int cnt = 0;

  for (DAGOpNode* node : node_list) {
    if (node->flag == -1) continue;

    // 初始化量子位的线性函数
    for (int qubit : node->qargs) {
      if (cur_phases.find(qubit) == cur_phases.end()) {
        cur_phases[qubit] = 1 << (qubit + 1);
      }
    }

    if (node->name() == "cx") {
      int control = node->qargs[0];
      int target = node->qargs[1];
      cur_phases[target] ^= cur_phases[control];
    } else if (node->name() == "x") {
      int qubit = node->qargs[0];
      // 翻转常数项
      cur_phases[qubit] ^= 1;
    } else if (node->name() == "rz") {
      int qubit_phase = cur_phases[node->qargs[0]];
      int sign = (qubit_phase & 1) ? -1 : 1;
      int mono = qubit_phase >> 1;
      double angle =
          node->op->arg_value.empty() ? 0.0 : node->op->arg_value[0];

      phases[mono] = sign * angle + (phases.count(mono) ? phases[mono] : 0.0);

      if (first_rz.find(mono) == first_rz.end()) {
        first_rz[mono] = {node, sign};
      } else {
        // 同一单项式已有 Rz 门，合并角度后删除当前节点
        to_remove.push_back(node);
      }
    }
  }

  // 更新或删除每个单项式的第一个 Rz 门
  for (auto& [mono, pack] : first_rz) {
    DAGOpNode* node = pack.first;
    int sign = pack.second;
    if (node->flag == -1) continue;

    if (std::abs(phases[mono]) <= 1e-8) {
      dag.remove_op_node(node);
      ++cnt;
    } else {
      node->op->arg_value = {sign * phases[mono]};
    }
  }

  // 删除重复的 Rz 门
  for (DAGOpNode* node : to_remove) {
    if (node->flag == -1) continue;
    dag.remove_op_node(node);
    ++cnt;
  }

  return cnt;
}

DAGCircuit& CliffordRzOptimization::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  // 将 S、SDG、T、TDG、Z 等离散相位门统一转为 Rz(theta) 参数化形式
  const std::set<std::string> rz_phase_gates = {"s", "sdg", "t", "tdg", "z"};
  const auto op_counts = dag.count_ops();
  bool has_phase_gate = false;
  for (const std::string& g : rz_phase_gates) {
    if (op_counts.find(g) != op_counts.end()) {
      has_phase_gate = true;
      break;
    }
  }
  if (has_phase_gate) {
    dag.parameterize_all_rz();
  }

  // 按 routine_ 中定义的顺序依次执行各个优化 pass
  int total_reduced = 0;
  for (int step : routine_) {
    const auto& [name, method] = step_methods_[step];
    const auto start = std::chrono::steady_clock::now();
    const int reduced = (this->*method)(dag, basis_gates);
    total_reduced += reduced;

    if (verbose_) {
      const auto elapsed = std::chrono::duration<double>(
          std::chrono::steady_clock::now() - start);
      std::clog << name << ": " << reduced << " gates reduced, cost "
                << elapsed.count() << " s\n";
    }
  }

  // 将合并后的 Rz 还原为离散相位门（仅当 basis_gates 包含所需离散门时）
  const auto final_counts = dag.count_ops();
  if (final_counts.find("rz") != final_counts.end() &&
      (!basis_gates ||
       std::includes(basis_gates->begin(), basis_gates->end(),
                     rz_phase_gates.begin(), rz_phase_gates.end()))) {
    dag.deparameterize_all_rz();
  }

  if (verbose_) {
    std::clog << "clifford_rz_optimization: reduced " << total_reduced
              << " gates\n";
  }
  return dag;
}

}  // namespace qcos
