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
#include <fstream>
#include <iostream>
#include <queue>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>

namespace qcos {

SABRE::SABRE(const std::vector<std::pair<int, int>>& coupling_list,
             int extention_size, double weight, double decay)
    : extention_size_(extention_size), weight_(weight), decay_(decay) {
  // Build physical coupling graph
  build_coupling_graph(coupling_list);
  // Initialize shortest-path distance matrix
  init_distance_matrix();
}

void SABRE::init_distance_matrix() {
  const int INF = 1000000;
  // Allocate and initialize distance matrix
  dist_.assign(phy_qubit_num_, std::vector<int>(phy_qubit_num_, INF));

  // Run BFS from each physical qubit
  for (const auto& [start_node, _] : adj_list_) {
    // Distance to itself is 0
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
    adj_list_[edge.first].insert(edge.second);
    adj_list_[edge.second].insert(edge.first);
    max_q = std::max({max_q, edge.first, edge.second});
  }
  phy_qubit_num_ = max_q + 1;
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
  int logic_qubit_num = get_qubit_num_from_ir(gates_list);

  // initialize logical to physical mapping
  if (initial_l2p.empty()) {
    cur_l2p_.resize(phy_qubit_num_);
    for (int i = 0; i < phy_qubit_num_; ++i) cur_l2p_[i] = i;
  } else {
    std::unordered_set<int> used_qubits(initial_l2p.begin(),
                                        initial_l2p.end());
    cur_l2p_ = initial_l2p;
    // add remaining unmapped qubits at the end
    for (int q = 0; q < phy_qubit_num_; ++q) {
      if (used_qubits.find(q) == used_qubits.end()) {
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
  std::vector<std::shared_ptr<Node>> pre_nodes(logic_qubit_num, nullptr);
  front_layer_.clear();
  phy_exe_gates_.clear();

  for (const auto& gate : gates_list) {
    auto node = std::make_shared<Node>(gate);
    int pre_number = 0;

    if (node->bits.size() == 1) {
      auto pre_node = pre_nodes[node->bits[0]];
      if (pre_node != nullptr) {
        pre_node->attach.push_back(node);
      } else {
        // can execute in physical
        phy_exe_gates_.push_back(phy_gate(node->gate));
      }
    } else if (node->bits.size() == 2) {
      for (int bit : node->bits) {
        auto pre_node = pre_nodes[bit];
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

    std::vector<std::shared_ptr<Node>> exe_gate_list;
    for (const auto& node : front_layer_) {
      // can execute in physical
      if (can_execute(node)) {
        exe_gate_list.push_back(node);
        phy_exe_gates_.push_back(phy_gate(node->gate));
        // the single qubit gate attached to the node
        for (const auto& gate_node : node->attach) {
          if (gate_node == nullptr)
            throw std::invalid_argument("The attached gate is not a Node");
          phy_exe_gates_.push_back(phy_gate(gate_node->gate));
        }
      }
    }
    if (!exe_gate_list.empty()) {
      for (const auto& node : exe_gate_list) {
        front_layer_.erase(
            std::remove(front_layer_.begin(), front_layer_.end(), node),
            front_layer_.end());
        for (const auto& successor : node->edges) {
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
      // no gate can be executed in physical
      // need to find the best swap
      auto candidate_list = obtain_swaps();
      std::pair<int, int> best_swap = {-1, -1};
      double best_score = 0;
      std::vector<int> cur_best_mapping;

      // calculate the base cost
      double base_cost;
      int actual_extend_size;
      std::unordered_map<int, std::vector<std::shared_ptr<Node>>>
          front_qubit_gate_map, extend_qubit_gate_map;
      heuristic_cost(cur_l2p_, base_cost, actual_extend_size,
                     front_qubit_gate_map, extend_qubit_gate_map);

      for (const auto& swap : candidate_list) {
        auto temp_mapping = get_temp_mapping(swap);
        // The cost change caused by the current candidate swap gate
        double delta = delta_heuristic_cost(
            cur_l2p_, temp_mapping, swap, actual_extend_size,
            front_qubit_gate_map, extend_qubit_gate_map);

        double H_score = base_cost + delta;
        H_score = H_score * std::max(decay_list[cur_p2l_[swap.first]],
                                     decay_list[cur_p2l_[swap.second]]);

        if (best_swap.first == -1 || H_score < best_score) {
          best_score = H_score;
          best_swap = swap;
          cur_best_mapping = temp_mapping;
        }
      }

      // update the current mapping
      std::swap(cur_p2l_[best_swap.first], cur_p2l_[best_swap.second]);
      cur_l2p_ = cur_best_mapping;

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

bool SABRE::can_execute(const std::shared_ptr<Node>& node) {
  if (node->bits.size() == 1)
    return true;
  else if (node->bits.size() == 2) {
    int logic0 = node->bits[0], logic1 = node->bits[1];
    int phy0 = cur_l2p_[logic0], phy1 = cur_l2p_[logic1];
    return adj_list_[phy0].count(phy1) > 0;
  }
  throw std::invalid_argument("The number of node.bits is not 1 or 2");
}

std::vector<std::pair<int, int>> SABRE::obtain_swaps() {
  std::vector<std::pair<int, int>> candidates;
  std::unordered_set<int> phy_bits;
  // Only consider SWAPs related to the front layer
  for (const auto& node : front_layer_) {
    if (node->bits.size() == 1) continue;
    // Extract logical qubits and map them to physical qubits
    for (int bit : node->bits) phy_bits.insert(cur_l2p_[bit]);
  }

  // Traverse all edges
  for (auto const& [u, neighbors] : adj_list_) {
    for (int v : neighbors) {
      // (u < v) prevents duplicate bidirectional edges
      if (u < v && (phy_bits.count(u) || phy_bits.count(v))) {
        candidates.push_back({u, v});
      }
    }
  }
  return candidates;
}

std::vector<int> SABRE::get_temp_mapping(const std::pair<int, int>& edge) {
  std::vector<int> new_mapping = cur_l2p_;
  int u = edge.first, v = edge.second;
  new_mapping[cur_p2l_[u]] = v;
  new_mapping[cur_p2l_[v]] = u;
  return new_mapping;
}

GateOperation SABRE::phy_gate(const GateOperation& logic_gate) {
  // TODO: Measure, Reset, Barrier...
  std::vector<int> physical_targets;
  for (int bit : logic_gate.targets) {
    physical_targets.push_back(cur_l2p_[bit]);
  }
  return GateOperation(logic_gate.name, physical_targets, logic_gate.arg_value,
                       logic_gate.operation_type, logic_gate.hermitian);
}

void SABRE::heuristic_cost(
    const std::vector<int>& logic2phy, double& h_total, int& e_count,
    std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
        front_qubit_gate_map,
    std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
        extend_qubit_gate_map) {
  // basic heuristic based on current front layer
  double h_basic = 0.0;
  // extend heuristic from lookahead set
  double h_extend = 0.0;

  // compute cost of front layer
  for (const auto& node : front_layer_) {
    int q0 = node->bits[0], q1 = node->bits[1];
    h_basic += dist_[logic2phy[q0]][logic2phy[q1]];
    front_qubit_gate_map[q0].push_back(node);
    front_qubit_gate_map[q1].push_back(node);
  }
  int f_count = front_layer_.size();
  if (f_count > 0) h_basic /= f_count;

  // lookahead extension set
  std::vector<std::shared_ptr<Node>> extend_set;
  // temporary queue to store nodes whose indegree is modified
  std::unordered_map<Node*, int> temp_indegree;
  std::deque<std::shared_ptr<Node>> extend_queue(front_layer_.begin(),
                                                 front_layer_.end());

  while (extend_set.size() < (size_t)extention_size_ &&
         !extend_queue.empty()) {
    auto node = extend_queue.front();
    extend_queue.pop_front();
    for (auto& successor : node->edges) {
      if (temp_indegree.find(successor.get()) == temp_indegree.end()) {
        temp_indegree[successor.get()] = successor->pre_number;
      }
      int new_deg = temp_indegree[successor.get()] - 1;
      temp_indegree[successor.get()] = new_deg;

      if (new_deg == 0) {
        extend_set.push_back(successor);
        extend_queue.push_back(successor);
        int q0 = successor->bits[0], q1 = successor->bits[1];
        extend_qubit_gate_map[q0].push_back(successor);
        extend_qubit_gate_map[q1].push_back(successor);
      }
    }
  }

  // compute cost of extension set
  e_count = extend_set.size();
  for (const auto& node : extend_set) {
    h_extend += dist_[logic2phy[node->bits[0]]][logic2phy[node->bits[1]]];
  }
  if (e_count > 0) h_extend /= e_count;

  h_total = h_basic + weight_ * h_extend;
}

double SABRE::delta_heuristic_cost(
    const std::vector<int>& old_l2p, const std::vector<int>& new_l2p,
    const std::pair<int, int>& swap, int extend_size,
    std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
        front_qubit_gate_map,
    std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
        extend_qubit_gate_map) {
  // Logical qubits corresponding to the candidate swap gate
  int logic_q0 = cur_p2l_[swap.first];
  int logic_q1 = cur_p2l_[swap.second];

  // Compute the incremental cost for a set of nodes
  auto _delta_sum =
      [&](const std::unordered_set<std::shared_ptr<Node>>& nodes) {
        double delta = 0.0;
        for (auto const& node : nodes) {
          int q0 = node->bits[0], q1 = node->bits[1];
          delta += dist_[new_l2p[q0]][new_l2p[q1]] -
                   dist_[old_l2p[q0]][old_l2p[q1]];
        }
        return delta;
      };

  // All front-layer gates affected by the two qubits of the swap
  std::unordered_set<std::shared_ptr<Node>> affected_front_nodes;
  if (front_qubit_gate_map.count(logic_q0)) {
    for (auto& n : front_qubit_gate_map[logic_q0])
      affected_front_nodes.insert(n);
  }
  if (front_qubit_gate_map.count(logic_q1)) {
    for (auto& n : front_qubit_gate_map[logic_q1])
      affected_front_nodes.insert(n);
  }

  double delta_front = _delta_sum(affected_front_nodes);
  int f_count = front_layer_.size();
  if (f_count > 0) delta_front /= f_count;

  // All extension-layer gates affected by the two qubits of the swap
  std::unordered_set<std::shared_ptr<Node>> affected_extend_nodes;
  if (extend_qubit_gate_map.count(logic_q0)) {
    for (auto& n : extend_qubit_gate_map[logic_q0])
      affected_extend_nodes.insert(n);
  }
  if (extend_qubit_gate_map.count(logic_q1)) {
    for (auto& n : extend_qubit_gate_map[logic_q1])
      affected_extend_nodes.insert(n);
  }

  double delta_extend = _delta_sum(affected_extend_nodes);
  delta_extend *= weight_;
  if (extend_size > 0) delta_extend /= extend_size;

  return delta_front + delta_extend;
}

}  // namespace qcos
