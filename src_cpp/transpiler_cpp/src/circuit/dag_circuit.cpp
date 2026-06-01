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

#include "circuit/dag_circuit.h"

#include <algorithm>
#include <cmath>
#include <queue>
#include <stdexcept>
#include <unordered_set>

#include "circuit/gate_operation.h"
#include "circuit/quantum_circuit.h"

namespace qcos {

namespace {

constexpr double kPi = 3.14159265358979323846;

std::shared_ptr<BaseOperation> make_shared_gate(
    const std::string& name, const std::vector<int>& targets,
    const std::vector<double>& arg_value = {}, bool allow_undefined = false) {
  return std::shared_ptr<BaseOperation>(
      create_gate(name, targets, arg_value, allow_undefined));
}

bool is_phase_gate_name(const std::string& name) {
  static const std::unordered_set<std::string> phase_gates = {"s", "sdg", "t",
                                                              "tdg", "z"};
  return phase_gates.count(name) > 0;
}

}  // namespace

DAGCircuit::DAGCircuit() = default;

void DAGCircuit::add_qubits(int num_qubits) {
  if (num_qubits <= 0) {
    return;
  }

  std::vector<int> new_wires;
  new_wires.reserve(static_cast<size_t>(num_qubits));
  for (int qubit = 0; qubit < num_qubits; ++qubit) {
    if (wires_set_.count(qubit)) {
      throw std::invalid_argument("duplicate wire " + std::to_string(qubit));
    }
    new_wires.push_back(qubit);
  }

  for (int wire : new_wires) {
    add_wire(wire);
    qubits_.push_back(wire);
  }
}

void DAGCircuit::add_wire(int wire) {
  if (wires_set_.count(wire)) {
    throw std::invalid_argument("duplicate wire " + std::to_string(wire));
  }
  wires_set_.insert(wire);

  auto input_node = std::make_unique<DAGInNode>(wire);
  auto output_node = std::make_unique<DAGOutNode>(wire);
  DAGInNode* input_ptr = input_node.get();
  DAGOutNode* output_ptr = output_node.get();
  auto [input_id, output_id] =
      multi_graph_.add_nodes(std::move(input_node), std::move(output_node));
  input_map[wire] = input_ptr;
  output_map[wire] = output_ptr;
  // 每条量子线初始只有input->output一条直连边，后续门节点都插入到这条线上。
  multi_graph_.add_edge(input_id, output_id, wire);
}

void DAGCircuit::increment_op(const std::shared_ptr<BaseOperation>& op) {
  ++op_names_[op->name];
}

void DAGCircuit::decrement_op(const std::shared_ptr<BaseOperation>& op) {
  auto iterator = op_names_.find(op->name);
  if (iterator == op_names_.end()) {
    return;
  }
  if (iterator->second <= 1) {
    // 计数归零后直接移除键。
    op_names_.erase(iterator);
    return;
  }
  --iterator->second;
}

void DAGCircuit::rename_op(const std::shared_ptr<BaseOperation>& old_op,
                           const std::shared_ptr<BaseOperation>& new_op) {
  const bool valid_conversion =
      (old_op->name == "rz" && is_phase_gate_name(new_op->name)) ||
      (new_op->name == "rz" && is_phase_gate_name(old_op->name));
  if (!valid_conversion) {
    throw std::invalid_argument("can not convert " + old_op->name + " to " +
                                new_op->name + ".");
  }
  if (op_names_.find(old_op->name) == op_names_.end()) {
    throw std::invalid_argument("no " + old_op->name + " in the dag.");
  }
  decrement_op(old_op);
  increment_op(new_op);
}

void DAGCircuit::parameterize_all_rz() {
  // 离散相位门到rz的标准角度映射。
  const std::unordered_map<std::string, double> angles = {{"s", kPi / 2.0},
                                                          {"t", kPi / 4.0},
                                                          {"sdg", -kPi / 2.0},
                                                          {"tdg", -kPi / 4.0},
                                                          {"z", kPi}};

  for (const auto& node : topological_op_nodes()) {
    if (!is_phase_gate_name(node->name())) {
      continue;
    }
    // 将离散相位门统一重写为rz(theta)，便于后续做参数化等价变换。
    auto new_op =
        make_shared_gate("rz", node->op->targets, {angles.at(node->name())});
    rename_op(node->op, new_op);
    node->op = new_op;
  }
}

void DAGCircuit::deparameterize_all_rz(double tolerance) {
  const std::unordered_map<int, std::string> deparameterize_map = {
      {1, "t"}, {2, "s"}, {4, "z"}, {6, "sdg"}, {7, "tdg"}};

  for (const auto& node : topological_op_nodes()) {
    if (node->name() != "rz" || node->op->arg_value.empty()) {
      continue;
    }
    // 先把角度折叠到2pi周期内，再映射到以pi/4为步长的8个槽位。
    const double turns =
        std::fmod(node->op->arg_value[0], 2.0 * kPi) / (kPi / 4.0);
    if (std::abs(turns - std::round(turns)) > tolerance) {
      continue;
    }
    const int slot = (static_cast<int>(std::llround(turns)) % 8 + 8) % 8;
    if (slot == 0) {
      // 旋转角等价于0时直接删点，保持线路语义不变。
      remove_op_node(node);
      continue;
    }
    auto iterator = deparameterize_map.find(slot);
    if (iterator == deparameterize_map.end()) {
      continue;
    }
    auto new_op = make_shared_gate(iterator->second, node->op->targets);
    rename_op(node->op, new_op);
    node->op = new_op;
  }
}

DAGOpNode* DAGCircuit::apply_operation_back(std::shared_ptr<BaseOperation> op,
                                            std::vector<int> qargs) {
  if (qargs.empty()) {
    qargs = op->targets;
  }
  auto node = std::make_unique<DAGOpNode>(op, qargs);
  DAGOpNode* node_ptr = node.get();
  int node_id = multi_graph_.add_node(std::move(node));
  increment_op(op);

  std::vector<int> output_ids;
  output_ids.reserve(qargs.size());
  for (int bit : qargs) {
    output_ids.push_back(output_map.at(bit)->node_id());
  }
  // 从每条量子线的输出端向前插入，相当于把门追加到线路尾部。
  multi_graph_.insert_node_on_in_edges_multiple(node_id, output_ids);
  return node_ptr;
}

DAGOpNode* DAGCircuit::apply_operation_front(std::shared_ptr<BaseOperation> op,
                                             std::vector<int> qargs) {
  if (qargs.empty()) {
    qargs = op->targets;
  }
  auto node = std::make_unique<DAGOpNode>(op, qargs);
  DAGOpNode* node_ptr = node.get();
  int node_id = multi_graph_.add_node(std::move(node));
  increment_op(op);

  std::vector<int> input_ids;
  input_ids.reserve(qargs.size());
  for (int bit : qargs) {
    input_ids.push_back(input_map.at(bit)->node_id());
  }
  // 从每条量子线的输入端向后插入，相当于把门压到线路最前面。
  multi_graph_.insert_node_on_out_edges_multiple(node_id, input_ids);
  return node_ptr;
}

int DAGCircuit::size() const {
  // 扣掉每条 wire 的 input/output 哨兵节点。
  return multi_graph_.num_nodes() - 2 * static_cast<int>(wires_set_.size());
}

int DAGCircuit::depth() const {
  // 最长路径额外包含端点哨兵，因此需要减1。
  const int computed_depth = multi_graph_.dag_longest_path_length() - 1;
  return computed_depth >= 0 ? computed_depth : 0;
}

int DAGCircuit::width() const { return static_cast<int>(wires_set_.size()); }

std::vector<DAGNode*> DAGCircuit::nodes_on_wire(int wire, bool only_ops) {
  auto iterator = input_map.find(wire);
  if (iterator == input_map.end()) {
    throw std::invalid_argument("The given wire " + std::to_string(wire) +
                                " is not present in the circuit");
  }

  std::vector<DAGNode*> result;
  DAGNode* current = iterator->second;
  while (current) {
    if (!only_ops || dynamic_cast<DAGOpNode*>(current)) {
      result.push_back(current);
    }
    current = multi_graph_.find_first_successor_by_edge(
        current->node_id(),
        [wire](int edge_wire) { return edge_wire == wire; });
  }
  return result;
}

std::vector<DAGNode*> DAGCircuit::topological_nodes(
    std::function<std::string(const DAGNode*)> key) {
  if (!key) {
    // 默认排序键用于在拓扑序存在多解时给出稳定输出。
    key = [](const DAGNode* current) { return current->sort_key(); };
  }
  return multi_graph_.lexicographical_topological_sort(key);
}

std::vector<DAGOpNode*> DAGCircuit::topological_op_nodes(
    std::function<std::string(const DAGNode*)> key) {
  std::vector<DAGOpNode*> result;
  for (const auto& current : topological_nodes(std::move(key))) {
    if (auto* op_node = dynamic_cast<DAGOpNode*>(current)) {
      result.push_back(op_node);
    }
  }
  return result;
}

DAGNode* DAGCircuit::node(int node_id) { return multi_graph_[node_id]; }

std::vector<DAGNode*> DAGCircuit::nodes() { return multi_graph_.nodes(); }

std::vector<DAGOpNode*> DAGCircuit::op_nodes() {
  std::vector<DAGOpNode*> result;
  for (const auto& current : multi_graph_.nodes()) {
    if (auto* op_node = dynamic_cast<DAGOpNode*>(current)) {
      result.push_back(op_node);
    }
  }
  return result;
}

std::vector<DAGOpNode*> DAGCircuit::two_qubit_ops() {
  std::vector<DAGOpNode*> result;
  for (const auto& current : op_nodes()) {
    if (current->qargs.size() == 2) {
      result.push_back(current);
    }
  }
  return result;
}

std::vector<DAGOpNode*> DAGCircuit::multi_qubit_ops() {
  std::vector<DAGOpNode*> result;
  for (const auto& current : op_nodes()) {
    if (current->qargs.size() >= 3) {
      result.push_back(current);
    }
  }
  return result;
}

std::vector<DAGNode*> DAGCircuit::longest_path() {
  std::vector<DAGNode*> result;
  for (int node_id : multi_graph_.dag_longest_path()) {
    // 将图内部的id路径转换成节点对象。
    if (auto* current = multi_graph_[node_id]) {
      result.push_back(current);
    }
  }
  return result;
}

std::vector<DAGNode*> DAGCircuit::successors(const DAGNode* node) const {
  return multi_graph_.successors(node->node_id());
}

std::vector<DAGNode*> DAGCircuit::predecessors(const DAGNode* node) const {
  return multi_graph_.predecessors(node->node_id());
}

bool DAGCircuit::is_successor(const DAGNode* node, const DAGNode* node_succ) {
  return multi_graph_.has_edge(node->node_id(), node_succ->node_id());
}

bool DAGCircuit::is_predecessor(const DAGNode* node,
                                const DAGNode* node_pred) {
  return multi_graph_.has_edge(node_pred->node_id(), node->node_id());
}

std::set<DAGNode*> DAGCircuit::ancestors(const DAGNode* node) {
  std::set<DAGNode*> result;
  std::queue<int> queue;
  std::unordered_set<int> visited;

  for (int predecessor_id :
       multi_graph_.predecessor_indices(node->node_id())) {
    queue.push(predecessor_id);
  }
  while (!queue.empty()) {
    int current = queue.front();
    queue.pop();
    if (!visited.insert(current).second) {
      continue;
    }
    if (auto* current_node = multi_graph_[current]) {
      result.insert(current_node);
    }
    for (int predecessor_id : multi_graph_.predecessor_indices(current)) {
      queue.push(predecessor_id);
    }
  }
  return result;
}

std::set<DAGNode*> DAGCircuit::descendants(const DAGNode* node) {
  std::set<DAGNode*> result;
  std::queue<int> queue;
  std::unordered_set<int> visited;

  for (int successor_id : multi_graph_.successor_indices(node->node_id())) {
    queue.push(successor_id);
  }
  while (!queue.empty()) {
    int current = queue.front();
    queue.pop();
    if (!visited.insert(current).second) {
      continue;
    }
    if (auto* current_node = multi_graph_[current]) {
      result.insert(current_node);
    }
    for (int successor_id : multi_graph_.successor_indices(current)) {
      queue.push(successor_id);
    }
  }
  return result;
}

void DAGCircuit::remove_op_node(DAGOpNode* node) {
  if (!node) {
    throw std::invalid_argument(
        "The method remove_op_node only works on DAGOpNodes.");
  }
  auto op = node->op;
  multi_graph_.remove_node_retain_edges(node->node_id());
  decrement_op(op);
  node->flag = -1;
}

std::set<std::vector<DAGNode*>> DAGCircuit::collect_runs(
    const std::vector<std::string>& namelist) {
  const std::unordered_set<std::string> name_set(namelist.begin(),
                                                 namelist.end());
  auto filter_fn = [&name_set](const DAGNode* current) {
    auto* op_node = dynamic_cast<const DAGOpNode*>(current);
    return op_node && name_set.count(op_node->op->name) > 0;
  };

  std::set<std::vector<DAGNode*>> result;
  for (auto& run : multi_graph_.collect_runs(filter_fn)) {
    // 用set去重，避免同一串连续门因不同遍历入口重复返回。
    result.insert(std::move(run));
  }
  return result;
}

std::unordered_map<std::string, int> DAGCircuit::count_ops() const {
  return op_names_;
}

void DAGCircuit::build_from_operations(
    const std::vector<std::shared_ptr<BaseOperation>>& ops) {
  std::set<int> qubits;
  for (const auto& gate : ops) {
    qubits.insert(gate->targets.begin(), gate->targets.end());
  }
  if (!qubits.empty()) {
    // 这里按最大量子位索引补齐[0, max]，保证后续可直接按下标访问wire。
    add_qubits(*qubits.rbegin() + 1);
  }
  for (const auto& gate : ops) {
    apply_operation_back(gate);
  }
}

DAGCircuit DAGCircuit::ir_to_dag(
    const std::vector<std::shared_ptr<BaseOperation>>& ir) {
  DAGCircuit dag;
  dag.build_from_operations(ir);
  return dag;
}

DAGCircuit DAGCircuit::circuit_to_dag(const QuantumCircuit& circ) {
  DAGCircuit dag;

  // 先根据实际存在的操作构建DAG
  dag.build_from_operations(circ.get_operations());

  // 再补齐线路中声明了但未被任何门操作使用的空闲量子位
  for (int qubit = dag.width(); qubit < circ.num_qubits(); ++qubit) {
    dag.add_wire(qubit);
    dag.qubits_.push_back(qubit);
  }
  return dag;
}

std::unique_ptr<QuantumCircuit> DAGCircuit::dag_to_circuit(int num_qubits) {
  auto circuit = num_qubits > 0 ? std::make_unique<QuantumCircuit>(num_qubits)
                                : std::make_unique<QuantumCircuit>(width());
  std::vector<std::shared_ptr<BaseOperation>> gate_list;
  for (const auto& current : topological_op_nodes()) {
    gate_list.push_back(current->op);
  }
  circuit->append_operations(gate_list);
  return circuit;
}

DAGCircuit DAGCircuit::two_qubit_ops_to_dag() {
  DAGCircuit result;
  result.add_qubits(static_cast<int>(qubits_.size()));
  for (const auto& current : two_qubit_ops()) {
    result.apply_operation_back(current->op);
  }
  return result;
}

std::vector<DAGCircuit::EdgeTriple> DAGCircuit::edges(
    const std::vector<DAGNode*>* nodes_ptr) {
  std::vector<DAGNode*> target_nodes =
      nodes_ptr ? *nodes_ptr : multi_graph_.nodes();

  std::vector<EdgeTriple> result;
  for (const auto& current : target_nodes) {
    for (const auto& [src, dst, wire] :
         multi_graph_.out_edges(current->node_id())) {
      auto* src_node = multi_graph_[src];
      auto* dst_node = multi_graph_[dst];
      if (src_node && dst_node) {
        result.push_back({src_node, dst_node, wire});
      }
    }
  }
  return result;
}

}  // namespace qcos
