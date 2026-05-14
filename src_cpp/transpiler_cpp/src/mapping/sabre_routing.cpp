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
#include <stdexcept>
#include <vector>

#include "mapping/sabre_mapping.h"

namespace qcos {

std::vector<GateOperation> sabre_routing(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<int>& initial_l2p, int extention_size, double weight,
    double decay) {
  SABRE sabre(coupling_list, extention_size, weight, decay);
  sabre.execute(gates_list, initial_l2p);
  return sabre.get_physical_gates();
}

SABRE::SABRE(const std::vector<std::pair<int, int>>& coupling_list,
             int extention_size, double weight, double decay)
    : extention_size_(extention_size),
      weight_(weight),
      decay_(decay),
      coupling_list_(coupling_list) {
  // Build physical coupling graph
  build_coupling_graph(coupling_list);
  // Initialize shortest-path distance matrix
  init_distance_matrix();
}

void SABRE::init_distance_matrix() {
  const int INF = 1000000;
  // Allocate and initialize distance matrix
  dist_.assign(phy_qubit_num_, std::vector<int>(phy_qubit_num_, INF));

  for (int start_node = 0; start_node < phy_qubit_num_; ++start_node) {
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
  for (const auto& edge : coupling_list) {
    max_q = std::max({max_q, edge.first, edge.second});
  }
  phy_qubit_num_ = max_q + 1;

  adj_list_.assign(phy_qubit_num_, {});
  adj_matrix_.assign(phy_qubit_num_, std::vector<bool>(phy_qubit_num_, false));

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

void SABRE::execute(const std::vector<GateOperation>& gates_list,
                    const std::vector<int>& initial_l2p) {
  if (initial_l2p.empty()) {
    execute_routing(gates_list,
                    sabre_initial_mapping(gates_list, coupling_list_));
    return;
  }

  execute_routing(gates_list, initial_l2p);
}

void SABRE::execute_routing(const std::vector<GateOperation>& gates_list,
                            const std::vector<int>& initial_l2p) {
  int logic_qubit_num = get_qubit_num_from_ir(gates_list);

  // Node arena: all nodes owned here, stable pointers via reserve
  std::vector<Node> node_pool;
  node_pool.reserve(gates_list.size());

  // initialize logical to physical mapping
  if (initial_l2p.empty()) {
    cur_l2p_.resize(phy_qubit_num_);
    for (int i = 0; i < phy_qubit_num_; ++i) cur_l2p_[i] = i;
  } else {
    std::vector<bool> used_qubits(phy_qubit_num_, false);
    for (int q : initial_l2p) {
      if (q >= 0 && q < phy_qubit_num_) used_qubits[q] = true;
    }
    cur_l2p_ = initial_l2p;
    // add remaining unmapped qubits at the end
    for (int q = 0; q < phy_qubit_num_; ++q) {
      if (!used_qubits[q]) {
        cur_l2p_.push_back(q);
      }
    }
  }

  // physical to logical mapping
  cur_p2l_.assign(phy_qubit_num_, 0);
  for (int logical = 0; logical < (int)cur_l2p_.size(); ++logical) {
    cur_p2l_[cur_l2p_[logical]] = logical;
  }

  // list storing the latest node acting on each logical qubit
  std::vector<Node*> pre_nodes(logic_qubit_num, nullptr);
  front_layer_.clear();
  phy_exe_gates_.clear();
  phy_exe_gates_.reserve(gates_list.size() * 2);

  // Pre-allocate qubit-gate maps
  front_qubit_gate_map_.assign(logic_qubit_num, {});
  extend_qubit_gate_map_.assign(logic_qubit_num, {});

  // Pre-allocate temp_indegree buffer
  temp_indegree_.assign(gates_list.size(), -1);
  touched_indices_.clear();
  touched_indices_.reserve(extention_size_ * 4);

  for (const auto& gate : gates_list) {
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
        phy_exe_gates_.push_back(phy_gate(node->gate));
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
  std::vector<double> decay_list(phy_qubit_num_, 1.0);
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
        phy_exe_gates_.push_back(phy_gate(node->gate));
        // the single qubit gate attached to the node
        for (auto* gate_node : node->attach) {
          if (gate_node == nullptr)
            throw std::invalid_argument("The attached gate is not a Node");
          phy_exe_gates_.push_back(phy_gate(gate_node->gate));
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
        H_score = H_score * std::max(decay_list[cur_p2l_[swap.first]],
                                     decay_list[cur_p2l_[swap.second]]);

        if (best_swap.first == -1 || H_score < best_score) {
          best_score = H_score;
          best_swap = swap;
        }
      }

      // update the current mapping (inline, no temp vector copy)
      int lq0 = cur_p2l_[best_swap.first];
      int lq1 = cur_p2l_[best_swap.second];
      cur_l2p_[lq0] = best_swap.second;
      cur_l2p_[lq1] = best_swap.first;
      std::swap(cur_p2l_[best_swap.first], cur_p2l_[best_swap.second]);

      // insert a swap gate
      phy_exe_gates_.push_back(
          GateOperation("swap", {best_swap.first, best_swap.second}, {},
                        OperationType::DOUBLE_QUBIT_OPERATION, false));
      decay_list[cur_p2l_[best_swap.first]] += decay_;
      decay_list[cur_p2l_[best_swap.second]] += decay_;
    }
  }

  // final mapping
  phy2logic_ = cur_p2l_;
  logic2phy_ = cur_l2p_;
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
  bfs_queue.reserve(extention_size_ + front_layer_.size());
  bfs_queue.insert(bfs_queue.end(), front_layer_.begin(), front_layer_.end());
  int queue_pos = 0;
  e_count = 0;

  while (e_count < extention_size_ && queue_pos < (int)bfs_queue.size()) {
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
        if (logic_q0 < (int)qubit_gate_map.size()) {
          for (const auto* node : qubit_gate_map[logic_q0]) {
            int q0 = node->bits[0], q1 = node->bits[1];
            delta += dist_[new_phy(q0)][new_phy(q1)] -
                     dist_[old_l2p[q0]][old_l2p[q1]];
          }
        }
        // Process nodes involving logic_q1, skip already counted
        if (logic_q1 < (int)qubit_gate_map.size()) {
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
