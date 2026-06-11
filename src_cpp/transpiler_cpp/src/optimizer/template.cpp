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

#include "optimizer/template.h"

#include <algorithm>
#include <queue>
#include <utility>

#include "circuit/gate_operation.h"

namespace qcos {

namespace {

DAGOpNode* as_op_node(DAGNode* node) { return dynamic_cast<DAGOpNode*>(node); }

}  // namespace

OptimizingTemplate::OptimizingTemplate(DAGCircuit template_dag_in,
                                       std::optional<DAGCircuit> replacement,
                                       int anchor_in, int weight_in)
    : template_dag_(std::move(template_dag_in)),
      replacement_dag_(std::move(replacement)),
      anchor_(anchor_in),
      weight_(weight_in) {}

std::unordered_map<int, DAGOpNode*> OptimizingTemplate::compare(
    DAGCircuit& dag, DAGOpNode* start_node, int anchor_qubit) const {
  std::unordered_map<int, DAGOpNode*> mapping;
  if (!start_node) {
    return mapping;
  }

  // 获取模板锚定量子比特线路上的第一个门节点作为比较起点
  const std::map<int, DAGInNode*>& input_map = template_dag_.get_input_map();
  std::map<int, DAGInNode*>::const_iterator input_it = input_map.find(anchor_);
  if (input_it == input_map.end()) {
    return mapping;
  }

  DAGOpNode* t_node = nullptr;
  for (DAGNode* successor : template_dag_.successors(input_it->second)) {
    t_node = as_op_node(successor);
    if (t_node) break;
  }
  if (!t_node) {
    return mapping;
  }

  DAGOpNode* node = start_node;

  // 初始化量子比特映射：模板量子比特 → 电路量子比特
  int t_qubit = anchor_;
  std::unordered_map<int, int> qubit_mapping = {{t_qubit, anchor_qubit}};

  // 首节点门名称必须一致
  if (node->name() != t_node->name()) {
    return {};
  }

  // 为首节点逐量子比特建立映射，同时检测冲突
  for (size_t i = 0; i < t_node->qargs.size(); i++) {
    int u_qubit = t_node->qargs[i];
    int v_qubit = node->qargs[i];
    if (qubit_mapping.find(u_qubit) == qubit_mapping.end()) {
      qubit_mapping[u_qubit] = v_qubit;
    }
    if (qubit_mapping[u_qubit] != v_qubit) {
      return {};
    }
  }

  // 记录首节点匹配，初始化 BFS 队列
  mapping.emplace(t_node->node_id(), node);
  std::queue<std::pair<DAGOpNode*, DAGOpNode*>> queue;
  queue.push({t_node, node});

  while (!queue.empty()) {
    std::pair<DAGOpNode*, DAGOpNode*> front = queue.front();
    queue.pop();
    DAGOpNode* u = front.first;
    DAGOpNode* v = front.second;

    // 同时向"前驱"和"后继"两个方向扩展匹配
    const bool directions[2] = {true, false};
    for (bool walk_preds : directions) {
      const std::vector<DAGNode*>& u_nxts = walk_preds
                                                ? template_dag_.predecessors(u)
                                                : template_dag_.successors(u);
      const std::vector<DAGNode*>& v_nxts =
          walk_preds ? dag.predecessors(v) : dag.successors(v);

      // 逐量子比特比较：在相同量子比特上找下一个门节点
      for (int qubit : u->qargs) {
        // 在模板邻居中搜索作用于当前量子比特的下一个门
        DAGOpNode* u_nxt = nullptr;
        for (DAGNode* candidate : u_nxts) {
          DAGOpNode* op = as_op_node(candidate);
          if (!op) continue;
          if (std::find(op->qargs.begin(), op->qargs.end(), qubit) !=
              op->qargs.end()) {
            u_nxt = op;
            if (op->qargs.size() == 1) break;
          }
        }
        if (!u_nxt) continue;

        // 通过量子比特映射，在电路邻居中搜索对应量子比特上的下一个门
        std::unordered_map<int, int>::iterator qm_it =
            qubit_mapping.find(qubit);
        if (qm_it == qubit_mapping.end()) continue;

        DAGOpNode* v_nxt = nullptr;
        for (DAGNode* candidate : v_nxts) {
          DAGOpNode* op = as_op_node(candidate);
          if (!op) continue;
          if (std::find(op->qargs.begin(), op->qargs.end(), qm_it->second) !=
              op->qargs.end()) {
            v_nxt = op;
            if (op->qargs.size() == 1) break;
          }
        }

        // 若模板节点已匹配过，则当前电路节点必须与历史记录一致
        std::unordered_map<int, DAGOpNode*>::iterator map_it =
            mapping.find(u_nxt->node_id());
        if (map_it != mapping.end()) {
          if (map_it->second != v_nxt) return {};
          continue;
        }

        // 新匹配的节点对：电路侧节点必须存在且门名称一致
        if (!v_nxt || u_nxt->name() != v_nxt->name()) return {};

        // 为新节点对建立量子比特映射，检测冲突
        for (size_t i = 0; i < u_nxt->qargs.size(); i++) {
          int u_qubit = u_nxt->qargs[i];
          int v_qubit = v_nxt->qargs[i];
          if (qubit_mapping.find(u_qubit) == qubit_mapping.end()) {
            qubit_mapping[u_qubit] = v_qubit;
          }
          if (qubit_mapping[u_qubit] != v_qubit) {
            return {};
          }
        }

        // 记录新匹配，加入 BFS 队列继续扩展
        mapping.emplace(u_nxt->node_id(), v_nxt);
        queue.push({u_nxt, v_nxt});
      }
    }
  }

  return mapping;
}

/*
 * 单量子比特 Rz 交换模板。
 * Rz 门可以跨过这些模版，用于 cancel_single_qubit_gates。
 * 模板无 replacement（仅用于模式匹配，不做替换）。
 */
std::vector<OptimizingTemplate> generate_single_qubit_gate_templates() {
  std::vector<OptimizingTemplate> templates;

  /*
   * tpl[0]: H(1) CX(0,1) H(1), anchor=1
   * Rz 可跨过 H-CX-H 模式从目标位一侧移动到另一侧。
   *
   * q_0:  ──────■──────
   *      ┌───┐┌─┴─┐┌───┐
   * q_1: ┤ H ├┤ X ├┤ H ├
   *      └───┘└───┘└───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("h", {1}), create_gate("cx", {0, 1}),
        create_gate("h", {1})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 1, 0);
  }

  /*
   * tpl[1]: CX(0,1) RZ(1) CX(0,1), anchor=1
   * Rz 在目标位方向可跨过 CX 对。
   *
   * q_0: ──■─────────■──
   *      ┌─┴─┐┌───┐┌─┴─┐
   * q_1: ┤ X ├┤ Rz├┤ X ├
   *      └───┘└───┘└───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("cx", {0, 1}), create_gate("rz", {1}),
        create_gate("cx", {0, 1})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 1, 0);
  }

  /*
   * tpl[2]: CX(0,1), anchor=0
   * 控制位上的单个 CX 门。
   *
   * q_0: ──■──
   *      ┌─┴─┐
   * q_1: ┤ X ├
   *      └───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("cx", {0, 1})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 0, 0);
  }

  /*
   * tpl[3]: CX(1,0) CX(0,2) CX(1,0), anchor=0
   * CNOT sandwich: Rz 在两端 CX 之间可跨过中间 CX。
   *
   *      ┌───┐     ┌───┐
   * q_0: ┤ X ├──■──┤ X ├
   *      └─┬─┘  │  └─┬─┘
   * q_1: ──■────┼────■──
   *           ┌─┴─┐
   * q_2: ─────┤ X ├─────
   *           └───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("cx", {1, 0}), create_gate("cx", {0, 2}),
        create_gate("cx", {1, 0})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 0, 0);
  }

  /*
   * tpl[4]: H(0) X(0) H(0), anchor=0
   * H-X-H，Rz 可以跨过此模式。
   *
   *      ┌───┐┌───┐┌───┐
   * q_0: ┤ H ├┤ X ├┤ H ├
   *      └───┘└───┘└───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("h", {0}), create_gate("x", {0}), create_gate("h", {0})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 0, 0);
  }

  return templates;
}

/*
 * CNOT 控制位对消模板。
 * 用于 cancel_two_qubit_gates 中识别控制位线路上可跨过的门模式。
 * 模板跨过的子图不能包含目标位（否则双指针失去同步）。
 */
std::vector<OptimizingTemplate> generate_cnot_ctrl_templates() {
  std::vector<OptimizingTemplate> templates;

  /*
   * tpl[0]: CX(0,1), anchor=0
   * 控制位上的 CX 本身作为线路参考点。
   *
   * q_0: ──■──
   *      ┌─┴─┐
   * q_1: ┤ X ├
   *      └───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("cx", {0, 1})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 0, 0);
  }

  /*
   * tpl[1]: RZ(0), anchor=0
   * 控制位上的 Rz 可被模板跨过，不影响后续 CX 对消。
   *
   *      ┌───┐
   * q_0: ┤ Rz├
   *      └───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("rz", {0})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 0, 0);
  }

  return templates;
}

/*
 * CNOT 目标位对消模板。
 * 用于 cancel_two_qubit_gates 中识别目标位线路上可跨过的门模式。
 * 模板跨过的子图不能包含控制位。
 */
std::vector<OptimizingTemplate> generate_cnot_targ_templates() {
  std::vector<OptimizingTemplate> templates;

  /*
   * tpl[0]: CX(0,1), anchor=1
   * 目标位上的 CX 本身作为线路参考点。
   *
   * q_0: ──■──
   *      ┌─┴─┐
   * q_1: ┤ X ├
   *      └───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("cx", {0, 1})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 1, 0);
  }

  /*
   * tpl[1]: H(0) CX(0,1) H(0), anchor=0
   * H-CX-H 恒等式可在目标位上被跨过。
   *
   *      ┌───┐     ┌───┐
   * q_0: ┤ H ├──■──┤ H ├
   *      └───┘┌─┴─┐└───┘
   * q_1: ─────┤ X ├─────
   *           └───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("h", {0}), create_gate("cx", {0, 1}),
        create_gate("h", {0})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 0, 0);
  }

  /*
   * tpl[2]: X(0), anchor=0
   * 目标位上的 X 门可被跨过。
   *
   *      ┌───┐
   * q_0: ┤ X ├
   *      └───┘
   */
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("x", {0})};
    templates.emplace_back(DAGCircuit::ir_to_dag(ir), std::nullopt, 0, 0);
  }

  return templates;
}

std::vector<const OptimizingTemplate*> filter_templates_by_basis(
    const std::vector<OptimizingTemplate>& templates,
    const std::set<std::string>& basis_gates, bool ignore_replacement) {
  std::vector<const OptimizingTemplate*> filtered_templates;
  filtered_templates.reserve(templates.size());

  for (const OptimizingTemplate& current : templates) {
    std::set<std::string> gate_names;
    const auto template_counts = current.template_dag_.count_ops();
    for (const auto& [name, _] : template_counts) {
      gate_names.insert(name);
    }

    if (!ignore_replacement && current.replacement_dag_.has_value()) {
      const auto replacement_counts = current.replacement_dag_->count_ops();
      for (const auto& [name, _] : replacement_counts) {
        gate_names.insert(name);
      }
    }

    if (std::includes(basis_gates.begin(), basis_gates.end(),
                      gate_names.begin(), gate_names.end())) {
      filtered_templates.push_back(&current);
    }
  }

  return filtered_templates;
}

}  // namespace qcos