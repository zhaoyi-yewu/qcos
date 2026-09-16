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

#include "optimizer/inverse_cancellation.h"

#include <iostream>
#include <stdexcept>
#include <unordered_map>

#include "circuit/dag_node.h"

namespace qcos {

InverseCancellation::InverseGateRule::InverseGateRule(GateOperation gate)
    : gate_0(std::move(gate)) {}

InverseCancellation::InverseGateRule::InverseGateRule(GateOperation gate_0_in,
                                                      GateOperation gate_1_in)
    : gate_0(std::move(gate_0_in)), gate_1(std::move(gate_1_in)) {}

InverseCancellation::InverseCancellation(
    const std::vector<InverseGateRule>& gates_to_cancel, bool verbose)
    : verbose_(verbose) {
  for (const auto& gates : gates_to_cancel) {
    // 判断是否为自反门
    if (!gates.is_pair()) {
      // 判断 gate_0 是否为自反门
      if (!is_inverse(gates.gate_0)) {
        throw std::invalid_argument("Gate " + gates.gate_0.name +
                                    " is not self-inverse");
      }
      self_inverse_gate_names_.insert(gates.gate_0.name);
      continue;
    }

    // 判断 gate_0 和 gate_1 是否互逆
    if (!is_inverse(gates.gate_0, gates.gate_1)) {
      throw std::invalid_argument("Gate " + gates.gate_0.name + " and " +
                                  gates.gate_1->name + " are not inverse.");
    }
    inverse_gate_pairs_.push_back(gates);
    inverse_gate_pairs_names_.insert(gates.gate_0.name);
    inverse_gate_pairs_names_.insert(gates.gate_1->name);
  }
}

int InverseCancellation::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  int reduced = 0;
  // 入口算一次拓扑序，供所有规则复用，避免每次 collect_runs 重复排序
  const auto topo_order = dag.get_multi_graph().topo_order();
  if (!self_inverse_gate_names_.empty()) {
    // 处理自反门的成对消除逻辑
    reduced += run_on_self_inverse(dag, topo_order);
  }
  if (!inverse_gate_pairs_.empty()) {
    // 处理互逆门的成对消除逻辑
    reduced += run_on_inverse_pairs(dag, topo_order);
  }
  if (verbose_) {
    std::clog << name() << ": " << reduced << " gates reduced\n";
  }
  return reduced;
}

bool InverseCancellation::is_inverse(
    const GateOperation& gate_0,
    const std::optional<GateOperation>& gate_1) const {
  if (!gate_1) {
    return gate_0.hermitian;
  }
  if (gate_0.operation_type != gate_1->operation_type) {
    return false;
  }
  if (gate_0.name == gate_1->name) {
    return gate_0.hermitian;
  }

  // 目前仅支持 s, sdg, t, tdg 这两对显式互逆门
  // 其他门可通过设置 hermitian=true 来实现自反门对消。
  static const std::unordered_map<std::string, std::string> kInversePairs = {
      {"s", "sdg"}, {"sdg", "s"}, {"t", "tdg"}, {"tdg", "t"}};

  auto iterator = kInversePairs.find(gate_0.name);
  return iterator != kInversePairs.end() && iterator->second == gate_1->name;
}

int InverseCancellation::run_on_self_inverse(
    DAGCircuit& dag, const std::vector<int>& topo_order) const {
  const auto op_counts = dag.count_ops();
  int reduced = 0;

  for (const auto& gate_name : self_inverse_gate_names_) {
    auto count_iterator = op_counts.find(gate_name);
    // 如果电路中没有这个门，或者这个门只出现了一次（无法成对消去），则跳过。
    if (count_iterator == op_counts.end() || count_iterator->second <= 1) {
      continue;
    }

    // 收集所有同名门的连续串
    auto gate_runs = dag.collect_runs({gate_name}, &topo_order);
    for (const auto& gate_cancel_run : gate_runs) {
      // partition 用于将连续串切分成若干段，每段内门的 qargs 都相同
      std::vector<std::vector<DAGNode*>> partitions;
      // chunk 用于临时存储当前段的节点，遇到 qargs 变化或串尾时就切分出一段。
      std::vector<DAGNode*> chunk;
      const size_t max_index =
          gate_cancel_run.empty() ? 0u : gate_cancel_run.size() - 1;

      for (size_t index = 0; index < gate_cancel_run.size(); ++index) {
        auto* current = dynamic_cast<DAGOpNode*>(gate_cancel_run[index]);
        if (!current || current->name() != gate_name) {
          if (!chunk.empty()) {
            partitions.push_back(chunk);
            chunk.clear();
          }
          continue;
        }

        chunk.push_back(gate_cancel_run[index]);
        auto* next =
            index == max_index
                ? nullptr
                : dynamic_cast<DAGOpNode*>(gate_cancel_run[index + 1]);
        // 当 qargs
        // 变化时切分出一段，保证每段内的门都作用在同一组量子位上，才可成对消去。
        const bool qargs_changed =
            index == max_index || !next || current->qargs != next->qargs;
        if (qargs_changed) {
          partitions.push_back(chunk);
          chunk.clear();
        }
      }

      for (const auto& partition : partitions) {
        // 如果分区内的门数量为奇数，则保留第一个门，其余门成对消去。
        const size_t keep_prefix = partition.size() % 2 == 0 ? 0u : 1u;
        for (size_t index = keep_prefix; index < partition.size(); ++index) {
          dag.remove_op_node(dynamic_cast<DAGOpNode*>(partition[index]));
          ++reduced;
        }
      }
    }
  }

  return reduced;
}

int InverseCancellation::run_on_inverse_pairs(
    DAGCircuit& dag, const std::vector<int>& topo_order) const {
  const auto op_counts = dag.count_ops();
  int reduced = 0;

  for (const auto& pair : inverse_gate_pairs_) {
    const auto& gate_0_name = pair.gate_0.name;
    const auto& gate_1_name = pair.gate_1->name;
    if (op_counts.find(gate_0_name) == op_counts.end() ||
        op_counts.find(gate_1_name) == op_counts.end()) {
      continue;
    }

    auto gate_cancel_runs =
        dag.collect_runs({gate_0_name, gate_1_name}, &topo_order);
    for (const auto& dag_nodes : gate_cancel_runs) {
      size_t index = 0;
      while (index + 1 < dag_nodes.size()) {
        auto* first = dynamic_cast<DAGOpNode*>(dag_nodes[index]);
        auto* second = dynamic_cast<DAGOpNode*>(dag_nodes[index + 1]);
        if (!first || !second) {
          ++index;
          continue;
        }

        // 只有当两个门作用在同一组量子位上时才可成对消去。
        const bool same_qargs = first->qargs == second->qargs;
        const bool ordered_match = same_qargs &&
                                   first->name() == gate_0_name &&
                                   second->name() == gate_1_name;
        const bool reverse_match = same_qargs &&
                                   first->name() == gate_1_name &&
                                   second->name() == gate_0_name;
        if (ordered_match || reverse_match) {
          dag.remove_op_node(first);
          dag.remove_op_node(second);
          reduced += 2;
          index += 2;
          continue;
        }
        ++index;
      }
    }
  }

  return reduced;
}

}  // namespace qcos
