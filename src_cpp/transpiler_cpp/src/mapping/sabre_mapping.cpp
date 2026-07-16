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

#include "mapping/sabre_mapping.h"

#include <algorithm>
#include <queue>
#include <unordered_map>
#include <unordered_set>

namespace qcos {

void select_largest_component(std::vector<std::pair<int, int>>& coupling_list,
                              std::vector<double>& edge_fidelities) {
  if (coupling_list.empty()) return;

  // 将耦合边展开为无向邻接表，用于后续 BFS 连通性分析
  std::unordered_map<int, std::vector<int>> adjacency;
  for (const auto& [src, tgt] : coupling_list) {
    adjacency[src].push_back(tgt);
    adjacency[tgt].push_back(src);
  }

  // 对每个未访问节点做 BFS，找出节点数最多的连通分量
  std::unordered_set<int> visited;
  std::vector<int> largest_component;
  for (const auto& [node, _] : adjacency) {
    if (visited.count(node)) continue;
    // 从当前节点出发，BFS 收集本连通分量的所有节点
    std::vector<int> component;
    std::queue<int> bfs_queue;
    bfs_queue.push(node);
    visited.insert(node);
    while (!bfs_queue.empty()) {
      int current = bfs_queue.front();
      bfs_queue.pop();
      component.push_back(current);
      for (int neighbor : adjacency[current]) {
        if (!visited.count(neighbor)) {
          visited.insert(neighbor);
          bfs_queue.push(neighbor);
        }
      }
    }
    // 更新最大连通分量
    if (component.size() > largest_component.size()) {
      largest_component = std::move(component);
    }
  }

  // 原地过滤：只保留两端均在最大连通分量内的边
  std::unordered_set<int> largest_component_set(largest_component.begin(),
                                                largest_component.end());
  size_t write_idx = 0;
  for (size_t read_idx = 0; read_idx < coupling_list.size(); ++read_idx) {
    // 边的两个端点都在最大分量中才保留
    if (largest_component_set.count(coupling_list[read_idx].first) &&
        largest_component_set.count(coupling_list[read_idx].second)) {
      coupling_list[write_idx] = coupling_list[read_idx];
      if (read_idx < edge_fidelities.size()) {
        edge_fidelities[write_idx] = edge_fidelities[read_idx];
      }
      ++write_idx;
    }
  }
  coupling_list.resize(write_idx);
  edge_fidelities.resize(write_idx);
}

constexpr int k_initial_mapping_prefix_layers = 25;

std::vector<qcos::GateOperation> extract_two_qubit_layer_prefix(
    const std::vector<qcos::GateOperation>& gates_list, int prefix_layers) {
  if (prefix_layers <= 0 || gates_list.empty()) return gates_list;

  std::unordered_map<int, int> last_layer_by_qubit;
  int last_prefix_index = -1;
  int max_layer = -1;

  for (int index = 0; index < static_cast<int>(gates_list.size()); ++index) {
    const auto& gate = gates_list[index];
    if (gate.operation_type != qcos::OperationType::DOUBLE_QUBIT_OPERATION) {
      continue;
    }

    int q0 = gate.targets[0];
    int q1 = gate.targets[1];
    int layer =
        std::max(
            last_layer_by_qubit.count(q0) ? last_layer_by_qubit[q0] : -1,
            last_layer_by_qubit.count(q1) ? last_layer_by_qubit[q1] : -1) +
        1;
    last_layer_by_qubit[q0] = layer;
    last_layer_by_qubit[q1] = layer;
    max_layer = std::max(max_layer, layer);
    if (layer < prefix_layers) last_prefix_index = index;
  }

  if (max_layer < prefix_layers || last_prefix_index < 0) return gates_list;

  return std::vector<qcos::GateOperation>(
      gates_list.begin(), gates_list.begin() + last_prefix_index + 1);
}

std::vector<int> sabre_initial_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list) {
  SABRE sabre(coupling_list);
  auto prefix_gates = extract_two_qubit_layer_prefix(
      gates_list, k_initial_mapping_prefix_layers);

  // reverse gates
  std::vector<GateOperation> reverse_gates = prefix_gates;
  std::reverse(reverse_gates.begin(), reverse_gates.end());

  // get initial mapping for reverse ir
  sabre.execute_routing(prefix_gates, {});
  std::vector<int> reverse_mapping = sabre.get_logic2phy();

  // get the initial mapping for original ir using reverse mapping
  sabre.execute_routing(reverse_gates, reverse_mapping);
  std::vector<int> mapping = sabre.get_logic2phy();
  return mapping;
}

}  // namespace qcos
