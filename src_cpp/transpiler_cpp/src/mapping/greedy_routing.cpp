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
 *      EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
 * NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE. See the
 * Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include "mapping/greedy_routing.h"

#include <algorithm>
#include <memory>
#include <queue>
#include <stdexcept>
#include <unordered_set>

namespace qcos {

GreedyRouting::GreedyRouting(
    const std::vector<std::pair<int, int>>& coupling_list) {
  build_coupling_graph(coupling_list);
}

void GreedyRouting::build_coupling_graph(
    const std::vector<std::pair<int, int>>& coupling_list) {
  int max_q = 0;
  for (const auto& edge : coupling_list) {
    adj_list[edge.first].insert(edge.second);
    adj_list[edge.second].insert(edge.first);
    max_q = std::max({max_q, edge.first, edge.second});
  }
  phy_qubit_num = max_q + 1;
}

int GreedyRouting::get_qubit_num_from_ir(
    const std::vector<GateOperation>& gates_list) const {
  int max_logic_id = -1;
  for (const auto& gate : gates_list) {
    for (int bit : gate.targets) {
      if (bit > max_logic_id) max_logic_id = bit;
    }
  }
  return max_logic_id + 1;
}

bool GreedyRouting::can_execute(const Node* node) const {
  if (node == nullptr) return false;
  if (node->bits.size() == 1) return true;
  if (node->bits.size() == 2) {
    const int logic0 = node->bits[0];
    const int logic1 = node->bits[1];
    const int phy0 = cur_l2p[logic0];
    const int phy1 = cur_l2p[logic1];
    auto it = adj_list.find(phy0);
    return it != adj_list.end() && it->second.count(phy1) > 0;
  }
  throw std::invalid_argument("The number of node.bits is not 1 or 2");
}

std::vector<int> GreedyRouting::shortest_path_between(int start,
                                                      int goal) const {
  if (start == goal) return {start};

  std::vector<int> parent(phy_qubit_num, -1);
  std::vector<char> visited(phy_qubit_num, 0);
  std::queue<int> q;
  q.push(start);
  visited[start] = 1;

  while (!q.empty()) {
    const int cur = q.front();
    q.pop();

    auto it = adj_list.find(cur);
    if (it == adj_list.end()) continue;

    for (int nxt : it->second) {
      if (visited[nxt]) continue;
      visited[nxt] = 1;
      parent[nxt] = cur;
      if (nxt == goal) {
        std::vector<int> path;
        for (int v = goal; v != -1; v = parent[v]) {
          path.push_back(v);
        }
        std::reverse(path.begin(), path.end());
        return path;
      }
      q.push(nxt);
    }
  }

  throw std::runtime_error(
      "GreedyRouting: no path between blocked gate physical qubits");
}

std::pair<int, int> GreedyRouting::pick_swap_for_blocked_gate(
    const Node* node) const {
  if (node == nullptr || node->bits.size() != 2) {
    throw std::invalid_argument(
        "GreedyRouting: blocked gate must be a two-qubit gate");
  }

  const int phy0 = cur_l2p[node->bits[0]];
  const int phy1 = cur_l2p[node->bits[1]];
  const std::vector<int> path = shortest_path_between(phy0, phy1);

  if (path.size() < 2) {
    throw std::runtime_error(
        "GreedyRouting: shortest path is too short for swap insertion");
  }

  return {path[0], path[1]};
}

void GreedyRouting::apply_swap_inplace(int u, int v) {
  const int lu = cur_p2l[u];
  const int lv = cur_p2l[v];
  std::swap(cur_p2l[u], cur_p2l[v]);
  cur_l2p[lu] = v;
  cur_l2p[lv] = u;
}

GateOperation GreedyRouting::phy_gate(const GateOperation& logic_gate) const {
  std::vector<int> physical_targets;
  physical_targets.reserve(logic_gate.targets.size());
  for (int bit : logic_gate.targets) {
    physical_targets.push_back(cur_l2p[bit]);
  }
  return GateOperation(logic_gate.name, physical_targets, logic_gate.arg_value,
                       logic_gate.operation_type, logic_gate.hermitian);
}

void GreedyRouting::execute(const std::vector<GateOperation>& gates_list,
                            const std::vector<int>& initial_l2p) {
  const int logic_qubit_num = get_qubit_num_from_ir(gates_list);

  if (initial_l2p.empty()) {
    cur_l2p.resize(phy_qubit_num);
    for (int i = 0; i < phy_qubit_num; ++i) cur_l2p[i] = i;
  } else {
    std::unordered_set<int> used_qubits(initial_l2p.begin(),
                                        initial_l2p.end());
    cur_l2p = initial_l2p;
    for (int q = 0; q < phy_qubit_num; ++q) {
      if (used_qubits.find(q) == used_qubits.end()) {
        cur_l2p.push_back(q);
      }
    }
  }

  cur_p2l.assign(phy_qubit_num, 0);
  for (int logical = 0; logical < static_cast<int>(cur_l2p.size());
       ++logical) {
    cur_p2l[cur_l2p[logical]] = logical;
  }

  std::vector<std::unique_ptr<Node>> node_pool;
  node_pool.reserve(gates_list.size());
  std::vector<Node*> pre_nodes(logic_qubit_num, nullptr);
  front_layer.clear();
  phy_exe_gates.clear();
  phy_exe_gates.reserve(std::max<size_t>(gates_list.size() * 2, 64));

  for (const auto& gate : gates_list) {
    node_pool.push_back(std::make_unique<Node>(gate));
    Node* node = node_pool.back().get();
    int pre_number = 0;

    if (node->bits.size() == 1) {
      Node* pre_node = pre_nodes[node->bits[0]];
      if (pre_node != nullptr) {
        pre_node->attach.push_back(node);
      } else {
        phy_exe_gates.push_back(phy_gate(node->gate));
      }
    } else if (node->bits.size() == 2) {
      for (int bit : node->bits) {
        Node* pre_node = pre_nodes[bit];
        if (pre_node != nullptr) {
          auto it =
              std::find(pre_node->edges.begin(), pre_node->edges.end(), node);
          if (it == pre_node->edges.end()) {
            pre_node->edges.push_back(node);
            pre_number += 1;
          }
        }
      }
      for (int bit : node->bits) pre_nodes[bit] = node;

      node->pre_number = pre_number;
      if (pre_number == 0) front_layer.push_back(node);
    }
  }

  std::unordered_set<Node*> executed;

  while (!front_layer.empty()) {
    std::vector<Node*> exe_gate_list;
    exe_gate_list.reserve(8);

    for (Node* node : front_layer) {
      if (can_execute(node)) {
        exe_gate_list.push_back(node);
        phy_exe_gates.push_back(phy_gate(node->gate));
        for (Node* gate_node : node->attach) {
          if (gate_node == nullptr) {
            throw std::invalid_argument(
                "The attached gate is not a valid Node");
          }
          phy_exe_gates.push_back(phy_gate(gate_node->gate));
        }
      }
    }

    if (!exe_gate_list.empty()) {
      executed.clear();
      executed.reserve(exe_gate_list.size() * 2 + 1);
      for (Node* node : exe_gate_list) executed.insert(node);

      std::vector<Node*> new_front;
      new_front.reserve(front_layer.size() + exe_gate_list.size() * 2);

      for (Node* node : front_layer) {
        if (!executed.count(node)) new_front.push_back(node);
      }
      for (Node* node : exe_gate_list) {
        for (Node* successor : node->edges) {
          successor->pre_number -= 1;
          if (successor->pre_number < 0) {
            throw std::invalid_argument("The pre_number of node is negative");
          }
          if (successor->pre_number == 0) {
            new_front.push_back(successor);
          }
        }
      }
      front_layer = std::move(new_front);
      continue;
    }

    Node* blocked_gate = nullptr;
    for (Node* node : front_layer) {
      if (node->bits.size() == 2) {
        blocked_gate = node;
        break;
      }
    }
    if (blocked_gate == nullptr) {
      throw std::runtime_error(
          "GreedyRouting: front layer is blocked but no two-qubit gate found");
    }

    const auto [u, v] = pick_swap_for_blocked_gate(blocked_gate);
    apply_swap_inplace(u, v);
    phy_exe_gates.push_back(GateOperation(
        "swap", {u, v}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false));
  }

  phy2logic = cur_p2l;
  logic2phy = cur_l2p;
}

}  // namespace qcos
