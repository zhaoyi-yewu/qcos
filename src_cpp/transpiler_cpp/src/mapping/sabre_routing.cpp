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

#include "mapping/sabre_routing.h"

#include <algorithm>
#include <queue>
#include <set>
#include <stdexcept>
#include <unordered_set>
#include <vector>

#include "mapping/chip_data.h"
#include "mapping/dense_layout.h"
#include "mapping/mapping_utils.h"
#include "mapping/sabre_mapping.h"

namespace qcos {

std::vector<std::shared_ptr<BaseOperation>> sabre_routing(
    const std::vector<std::shared_ptr<BaseOperation>>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities,
    const std::vector<double>& single_qubit_fidelities,
    double fidelity_threshold, int extension_size, double weight,
    double decay) {
  SABRE sabre(coupling_list, edge_fidelities, single_qubit_fidelities,
              fidelity_threshold, extension_size, weight, decay);
  sabre.execute(gates_list);
  return sabre.get_physical_gates();
}

SABRE::SABRE(const std::vector<std::pair<int, int>>& coupling_list,
             const std::vector<double>& edge_fidelities,
             const std::vector<double>& single_qubit_fidelities,
             double fidelity_threshold, int extension_size, double weight,
             double decay)
    : coupling_list_(coupling_list),
      edge_fidelities_(edge_fidelities),
      single_qubit_fidelities_(single_qubit_fidelities),
      fidelity_threshold_(fidelity_threshold),
      extension_size_(extension_size),
      weight_(weight),
      decay_(decay) {
  // 若提供了保真度数据且阈值 > 0, 则过滤
  if (!edge_fidelities_.empty() && fidelity_threshold_ > 0.0) {
    ChipCalibration chip(coupling_list_, edge_fidelities_,
                         single_qubit_fidelities_);
    filter_low_fidelity(chip, fidelity_threshold_);
    coupling_list_ = chip.coupling_list;
    edge_fidelities_ = chip.edge_fidelities;
    single_qubit_fidelities_ = chip.single_qubit_fidelities;
  }

  // 始终选择最大连通分量
  select_largest_component(coupling_list_, edge_fidelities_);

  build_coupling_graph(coupling_list_);
  init_distance_matrix();
}

void SABRE::execute(
    const std::vector<std::shared_ptr<BaseOperation>>& gates_list) {
  // 1. 分离 measure 门和普通门
  std::vector<std::shared_ptr<BaseOperation>> regular_gates;
  std::vector<std::shared_ptr<Measure>> measure_ops;

  for (const auto& op : gates_list) {
    if (op == nullptr) {
      throw std::invalid_argument(
          "SABRE routing does not accept null BaseOperation pointers");
    }
    if (op->name == "measure") {
      auto measure = std::dynamic_pointer_cast<Measure>(op);
      if (!measure) measure = std::make_shared<Measure>(op->targets);
      measure_ops.push_back(measure);
    } else {
      regular_gates.push_back(op);
    }
  }

  // 2. 转换为 GateOperation
  std::vector<GateOperation> gate_ops;
  gate_ops.reserve(regular_gates.size());
  for (const auto& op : regular_gates) {
    gate_ops.push_back(to_gate_operation(*op));
  }

  // 无 Measure 时为所有逻辑位补充 Measure
  // TODO: 补充Measure门的操作应该在 parse 中处理
  if (measure_ops.empty()) {
    int logical_qubit_num = get_qubit_num_from_ir(gate_ops);
    for (int i = 0; i < logical_qubit_num; ++i) {
      measure_ops.push_back(std::make_shared<Measure>(std::vector<int>{i}));
    }
  }

  // 计算完整的逻辑位数: gate_ops + measure_ops 中引用的最大逻辑位 ID + 1
  // (优化器可能消除某些位上的全部门, 但 measure 仍引用)
  logic_qubit_num_ = get_qubit_num_from_ir(gate_ops);
  for (const auto& measure_op : measure_ops) {
    int qubit_count = measure_op->targets[0] + 1;
    if (qubit_count > logic_qubit_num_) logic_qubit_num_ = qubit_count;
  }

  // 3. 计算初始映射并执行路由
  // DenseLayout 选区域 + SABRE 精化排列
  std::vector<int> initial_l2p = dense_layout_mapping(
      gate_ops, coupling_list_, edge_fidelities_, logic_qubit_num_);

  std::vector<GateOperation> routed_gate_ops =
      execute_routing(gate_ops, initial_l2p);

  const std::vector<int>& logic2phy = get_logic2phy();

  // 4. 转换为 BaseOperation
  phy_exe_gates_.clear();
  phy_exe_gates_.reserve(routed_gate_ops.size() + measure_ops.size());
  for (const auto& g : routed_gate_ops) {
    phy_exe_gates_.push_back(restore_base_operation(g));
  }

  // 5. 将 measure 门的逻辑位替换为物理位，保留原有 cbits
  for (const auto& measure_op : measure_ops) {
    int logic_q = measure_op->targets[0];
    int physical_q = (logic_q < static_cast<int>(logic2phy.size()))
                         ? logic2phy[logic_q]
                         : logic_q;
    phy_exe_gates_.push_back(std::make_shared<Measure>(
        std::vector<int>{physical_q}, measure_op->cbits));
  }
}

void SABRE::init_distance_matrix() {
  const int INF = 1000000;
  // dist_ 按 ID 索引, 大小为 max_phy_qubit_id_+1
  int array_size = max_phy_qubit_id_ + 1;
  dist_.assign(array_size, std::vector<int>(array_size, INF));

  for (int start_node = 0; start_node < array_size; ++start_node) {
    if (adj_list_[start_node].empty()) continue;
    dist_[start_node][start_node] = 0;
    std::queue<int> q;
    q.push(start_node);
    // BFS main loop
    while (!q.empty()) {
      int curr = q.front();
      q.pop();
      // Traverse neighbors
      for (int neighbor : adj_list_[curr]) {
        // Update if shorter path found
        if (dist_[start_node][neighbor] > dist_[start_node][curr] + 1) {
          dist_[start_node][neighbor] = dist_[start_node][curr] + 1;
          q.push(neighbor);
        }
      }
    }
  }
}

void SABRE::build_coupling_graph(
    const std::vector<std::pair<int, int>>& coupling_list) {
  int max_q = 0;
  std::unordered_set<int> unique_qubits;
  for (const auto& edge : coupling_list) {
    max_q = std::max({max_q, edge.first, edge.second});
    unique_qubits.insert(edge.first);
    unique_qubits.insert(edge.second);
  }
  // max_phy_qubit_id_: 用于按 ID 索引数组
  // (dist_/adj_list_/adj_matrix_/cur_l2p_/cur_p2l_)
  max_phy_qubit_id_ = max_q;
  // active_phy_qubit_num_: 活跃位数 (耦合图中出现的去重位数)
  active_phy_qubit_num_ = static_cast<int>(unique_qubits.size());

  int array_size = max_phy_qubit_id_ + 1;
  adj_list_.assign(array_size, {});
  adj_matrix_.assign(array_size, std::vector<bool>(array_size, false));

  for (const auto& edge : coupling_list) {
    int u = edge.first, v = edge.second;
    if (!adj_matrix_[u][v]) {
      adj_list_[u].push_back(v);
      adj_list_[v].push_back(u);
      adj_matrix_[u][v] = true;
      adj_matrix_[v][u] = true;
    }
  }
}

int SABRE::get_qubit_num_from_ir(
    const std::vector<GateOperation>& gates_list) const {
  int max_logic_id = -1;
  for (const auto& gate : gates_list) {
    for (int bit : gate.targets) {
      if (bit > max_logic_id) max_logic_id = bit;
    }
  }
  return max_logic_id + 1;
}

void SABRE::extend_l2p_with_unused_qubits(int old_size) {
  int array_size = max_phy_qubit_id_ + 1;
  std::vector<bool> used_phy(array_size, false);
  for (int i = 0; i < old_size; ++i) {
    if (cur_l2p_[i] >= 0 && cur_l2p_[i] < array_size)
      used_phy[cur_l2p_[i]] = true;
  }

  // 收集已分配位的未使用邻居
  std::vector<int> neighbors;
  for (int i = 0; i < old_size; ++i) {
    for (int neighbor : adj_list_[cur_l2p_[i]]) {
      if (!used_phy[neighbor]) neighbors.push_back(neighbor);
    }
  }
  std::sort(neighbors.begin(), neighbors.end());
  neighbors.erase(std::unique(neighbors.begin(), neighbors.end()),
                  neighbors.end());

  int assigned = old_size;
  for (int phy : neighbors) {
    if (assigned >= logic_qubit_num_) break;
    if (!used_phy[phy]) {
      cur_l2p_[assigned++] = phy;
      used_phy[phy] = true;
    }
  }

  // 邻居不够, 从耦合图中找其余未使用位
  for (int phy = 0; phy < array_size && assigned < logic_qubit_num_; ++phy) {
    if (!used_phy[phy] && !adj_list_[phy].empty()) {
      cur_l2p_[assigned++] = phy;
      used_phy[phy] = true;
    }
  }

  if (assigned < logic_qubit_num_) {
    throw std::runtime_error("Not enough physical qubits: need " +
                             std::to_string(logic_qubit_num_) +
                             " but chip has " + std::to_string(array_size));
  }
}

std::vector<GateOperation> SABRE::execute_routing(
    const std::vector<GateOperation>& gates_list,
    const std::vector<int>& initial_l2p) {
  if (logic_qubit_num_ <= 0) {
    logic_qubit_num_ = get_qubit_num_from_ir(gates_list);
  }

  // Node arena: all nodes owned here, stable pointers via reserve
  std::vector<Node> node_pool;
  node_pool.reserve(gates_list.size());

  // initialize logical to physical mapping
  // cur_l2p_: 大小 = logic_qubit_num_, 只包含有效逻辑位映射
  // cur_p2l_: 大小 = max_phy_qubit_id_+1, 按物理 ID 索引
  int array_size = max_phy_qubit_id_ + 1;
  if (initial_l2p.empty()) {
    // 优先分配在耦合图中有边的物理位，避免分配到孤立位导致路由卡死
    std::vector<int> graph_qubits;
    for (int i = 0; i < array_size; ++i) {
      if (!adj_list_[i].empty()) graph_qubits.push_back(i);
    }
    cur_l2p_.resize(logic_qubit_num_);
    for (int i = 0; i < logic_qubit_num_; ++i) {
      cur_l2p_[i] =
          (i < static_cast<int>(graph_qubits.size())) ? graph_qubits[i] : i;
    }
  } else {
    cur_l2p_ = initial_l2p;
    int old_size = static_cast<int>(cur_l2p_.size());
    cur_l2p_.resize(logic_qubit_num_);
    if (old_size < logic_qubit_num_) {
      extend_l2p_with_unused_qubits(old_size);
    }
  }

  // physical to logical mapping (-1 = physical qubit holds no logical qubit)
  cur_p2l_.assign(array_size, -1);
  for (int logical = 0; logical < logic_qubit_num_; ++logical) {
    cur_p2l_[cur_l2p_[logical]] = logical;
  }

  // list storing the latest node acting on each logical qubit
  std::vector<Node*> pre_nodes(logic_qubit_num_, nullptr);
  front_layer_.clear();
  std::vector<GateOperation> result;
  result.clear();
  result.reserve(gates_list.size() * 2);

  // Pre-allocate qubit-gate maps
  front_qubit_gate_map_.assign(logic_qubit_num_, {});
  extend_qubit_gate_map_.assign(logic_qubit_num_, {});

  // Pre-allocate temp_indegree buffer
  temp_indegree_.assign(gates_list.size(), -1);
  touched_indices_.clear();
  touched_indices_.reserve(extension_size_ * 4);

  for (const auto& gate : gates_list) {
    if (gate.name == "sync") {
      continue;
    }
    node_pool.emplace_back(gate);
    Node* node = &node_pool.back();
    node->index = (int)node_pool.size() - 1;
    int pre_number = 0;

    if (node->bits.size() == 1) {
      Node* pre_node = pre_nodes[node->bits[0]];
      if (pre_node != nullptr) {
        pre_node->attach.push_back(node);
      } else {
        // can execute in physical
        result.push_back(phy_gate(node->gate));
      }
    } else if (node->bits.size() == 2) {
      for (int bit : node->bits) {
        Node* pre_node = pre_nodes[bit];
        // add a edge from pre_node to node and add in-degree
        if (pre_node != nullptr) {
          auto it =
              std::find(pre_node->edges.begin(), pre_node->edges.end(), node);
          if (it == pre_node->edges.end()) {
            pre_node->edges.push_back(node);
            pre_number += 1;
          }
        }
      }
      // update pre_nodes
      for (int bit : node->bits) pre_nodes[bit] = node;

      node->pre_number = pre_number;
      // can execute in logical
      if (pre_number == 0) front_layer_.push_back(node);
    }
  }

  // The main process of the SABRE algorithm
  std::vector<double> decay_list(max_phy_qubit_id_ + 1, 1.0);
  int decay_cycle = 5;
  int decay_time = 0;

  while (!front_layer_.empty()) {
    decay_time += 1;
    // reset the decay parameters
    if (decay_time % decay_cycle == 0) {
      std::fill(decay_list.begin(), decay_list.end(), 1.0);
    }

    std::vector<Node*> exe_gate_list;
    for (auto* node : front_layer_) {
      // can execute in physical
      if (can_execute(node)) {
        exe_gate_list.push_back(node);
        result.push_back(phy_gate(node->gate));
        // the single qubit gate attached to the node
        for (auto* gate_node : node->attach) {
          if (gate_node == nullptr)
            throw std::invalid_argument("The attached gate is not a Node");
          result.push_back(phy_gate(gate_node->gate));
        }
      }
    }
    if (!exe_gate_list.empty()) {
      // Mark executed nodes for batch removal
      for (auto* node : exe_gate_list) {
        node->pre_number = -2;
      }
      front_layer_.erase(
          std::remove_if(front_layer_.begin(), front_layer_.end(),
                         [](const Node* n) { return n->pre_number == -2; }),
          front_layer_.end());
      // Process successors after removal
      for (auto* node : exe_gate_list) {
        for (auto* successor : node->edges) {
          successor->pre_number -= 1;
          if (successor->pre_number < 0)
            throw std::invalid_argument("The pre_number of node is < 0");
          if (successor->pre_number == 0) {
            front_layer_.push_back(successor);
          }
        }
      }
      std::fill(decay_list.begin(), decay_list.end(), 1.0);
    } else {
      // no gate can be executed, find the best swap
      obtain_swaps(candidate_swaps_);
      if (candidate_swaps_.empty()) {
        throw std::runtime_error(
            "SABRE routing stuck: no candidate SWAPs available. "
            "The coupling graph may be disconnected after edge filtering. "
            "Try lowering distance_fidelity_threshold.");
      }
      std::pair<int, int> best_swap = {-1, -1};
      double best_score = 0;

      // calculate the base cost
      double base_cost;
      int actual_extend_size;
      heuristic_cost(cur_l2p_, base_cost, actual_extend_size);

      for (const auto& swap : candidate_swaps_) {
        double delta =
            delta_heuristic_cost(cur_l2p_, swap, actual_extend_size);

        double H_score = base_cost + delta;
        H_score = H_score *
                  std::max(decay_list[swap.first], decay_list[swap.second]);

        if (best_swap.first == -1 || H_score < best_score) {
          best_score = H_score;
          best_swap = swap;
        }
      }

      // update the current mapping (inline, no temp vector copy)
      int lq0 = cur_p2l_[best_swap.first];
      int lq1 = cur_p2l_[best_swap.second];
      if (lq0 >= 0) cur_l2p_[lq0] = best_swap.second;
      if (lq1 >= 0) cur_l2p_[lq1] = best_swap.first;
      std::swap(cur_p2l_[best_swap.first], cur_p2l_[best_swap.second]);

      // insert a swap gate
      result.push_back(
          GateOperation("swap", {best_swap.first, best_swap.second}, {},
                        OperationType::DOUBLE_QUBIT_OPERATION, false));
      decay_list[best_swap.first] += decay_;
      decay_list[best_swap.second] += decay_;
    }
  }

  // final mapping
  logic2phy_ = cur_l2p_;
  return result;
}

void SABRE::obtain_swaps(std::vector<std::pair<int, int>>& candidates) {
  candidates.clear();
  // Only enumerate edges adjacent to front-layer physical qubits
  for (const auto* node : front_layer_) {
    if (node->bits.size() == 1) continue;
    for (int bit : node->bits) {
      int phy = cur_l2p_[bit];
      for (int neighbor : adj_list_[phy]) {
        int u = std::min(phy, neighbor);
        int v = std::max(phy, neighbor);
        candidates.emplace_back(u, v);
      }
    }
  }
  // Remove duplicates
  std::sort(candidates.begin(), candidates.end());
  candidates.erase(std::unique(candidates.begin(), candidates.end()),
                   candidates.end());
}

GateOperation SABRE::phy_gate(const GateOperation& logic_gate) {
  // TODO: Measure, Reset, Barrier...
  std::vector<int> physical_targets;
  physical_targets.reserve(logic_gate.targets.size());
  for (int bit : logic_gate.targets) {
    physical_targets.push_back(cur_l2p_[bit]);
  }
  return GateOperation(logic_gate.name, std::move(physical_targets),
                       logic_gate.arg_value, logic_gate.operation_type,
                       logic_gate.hermitian);
}

void SABRE::heuristic_cost(const std::vector<int>& logic2phy, double& h_total,
                           int& e_count) {
  double h_basic = 0.0;
  double h_extend = 0.0;

  // Clear qubit-gate maps
  for (auto& v : front_qubit_gate_map_) v.clear();
  for (auto& v : extend_qubit_gate_map_) v.clear();

  // compute cost of front layer
  for (const auto* node : front_layer_) {
    int q0 = node->bits[0], q1 = node->bits[1];
    h_basic += dist_[logic2phy[q0]][logic2phy[q1]];
    front_qubit_gate_map_[q0].push_back(const_cast<Node*>(node));
    front_qubit_gate_map_[q1].push_back(const_cast<Node*>(node));
  }
  int f_count = (int)front_layer_.size();
  if (f_count > 0) h_basic /= f_count;

  // Lookahead extension set using flat BFS queue
  // Reset temp_indegree for previously touched nodes
  for (int idx : touched_indices_) temp_indegree_[idx] = -1;
  touched_indices_.clear();

  std::vector<Node*> bfs_queue;
  bfs_queue.reserve(extension_size_ + front_layer_.size());
  bfs_queue.insert(bfs_queue.end(), front_layer_.begin(), front_layer_.end());
  int queue_pos = 0;
  e_count = 0;

  while (e_count < extension_size_ && queue_pos < (int)bfs_queue.size()) {
    Node* node = bfs_queue[queue_pos++];
    for (auto* successor : node->edges) {
      int idx = successor->index;
      if (temp_indegree_[idx] == -1) {
        temp_indegree_[idx] = successor->pre_number;
        touched_indices_.push_back(idx);
      }
      if (--temp_indegree_[idx] == 0) {
        bfs_queue.push_back(successor);
        e_count++;
        int q0 = successor->bits[0], q1 = successor->bits[1];
        h_extend += dist_[logic2phy[q0]][logic2phy[q1]];
        extend_qubit_gate_map_[q0].push_back(successor);
        extend_qubit_gate_map_[q1].push_back(successor);
      }
    }
  }

  if (e_count > 0) h_extend /= e_count;

  h_total = h_basic + weight_ * h_extend;
}

double SABRE::delta_heuristic_cost(const std::vector<int>& old_l2p,
                                   const std::pair<int, int>& swap,
                                   int extend_size) {
  int logic_q0 = cur_p2l_[swap.first];
  int logic_q1 = cur_p2l_[swap.second];

  // Compute new physical position after swap without copying the mapping
  auto new_phy = [&](int logical_q) -> int {
    if (logical_q == logic_q0) return swap.second;
    if (logical_q == logic_q1) return swap.first;
    return old_l2p[logical_q];
  };

  // Compute delta for affected nodes in a qubit-gate map
  auto compute_delta =
      [&](const std::vector<std::vector<Node*>>& qubit_gate_map) {
        double delta = 0.0;
        // Process nodes involving logic_q0
        if (logic_q0 >= 0 && logic_q0 < (int)qubit_gate_map.size()) {
          for (const auto* node : qubit_gate_map[logic_q0]) {
            int q0 = node->bits[0], q1 = node->bits[1];
            delta += dist_[new_phy(q0)][new_phy(q1)] -
                     dist_[old_l2p[q0]][old_l2p[q1]];
          }
        }
        // Process nodes involving logic_q1, skip already counted
        if (logic_q1 >= 0 && logic_q1 < (int)qubit_gate_map.size()) {
          for (const auto* node : qubit_gate_map[logic_q1]) {
            if (node->bits[0] == logic_q0 || node->bits[1] == logic_q0)
              continue;
            int q0 = node->bits[0], q1 = node->bits[1];
            delta += dist_[new_phy(q0)][new_phy(q1)] -
                     dist_[old_l2p[q0]][old_l2p[q1]];
          }
        }
        return delta;
      };

  double delta_front = compute_delta(front_qubit_gate_map_);
  int f_count = (int)front_layer_.size();
  if (f_count > 0) delta_front /= f_count;

  double delta_extend = compute_delta(extend_qubit_gate_map_);
  delta_extend *= weight_;
  if (extend_size > 0) delta_extend /= extend_size;

  return delta_front + delta_extend;
}

}  // namespace qcos
