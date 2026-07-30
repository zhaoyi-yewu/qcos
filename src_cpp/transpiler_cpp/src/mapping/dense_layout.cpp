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

#include "mapping/dense_layout.h"

#include <algorithm>
#include <limits>
#include <numeric>
#include <queue>
#include <set>
#include <unordered_map>
#include <unordered_set>

#include "mapping/sabre_mapping.h"

namespace qcos {

namespace {

/**
 * @brief 校验 dense_layout_mapping 的输入参数
 * @throw std::invalid_argument 当参数不合法时
 */
void validate_dense_layout_inputs(
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical,
    int num_physical) {
  if (coupling_list.empty()) {
    throw std::invalid_argument(
        "dense_layout_mapping: coupling_list is empty");
  }

  if (!edge_fidelities.empty() &&
      edge_fidelities.size() != coupling_list.size()) {
    throw std::invalid_argument(
        "dense_layout_mapping: edge_fidelities size (" +
        std::to_string(edge_fidelities.size()) + ") != coupling_list size (" +
        std::to_string(coupling_list.size()) + ")");
  }

  if (num_logical > num_physical) {
    throw std::invalid_argument(
        "dense_layout_mapping: num_logical (" + std::to_string(num_logical) +
        ") > num_physical (" + std::to_string(num_physical) + ")");
  }
}

/**
 * @brief 从 coupling_list 推断物理比特总数（最大节点 ID + 1）
 */
int count_physical_qubits(
    const std::vector<std::pair<int, int>>& coupling_list) {
  int max_id = -1;
  for (const auto& edge : coupling_list) {
    max_id = std::max(max_id, std::max(edge.first, edge.second));
  }
  return max_id + 1;
}

/**
 * @brief 构建双向邻接表（仅包含有效边）
 * @param coupling_list 有向耦合边列表
 * @param edge_fidelities 边保真度数组，空则包含所有边
 * @param num_physical 物理比特总数
 * @return neighbors[i] 为与节点 i 相邻的邻居列表（双向）
 *
 * 将输入的有向边转为无向邻接关系，用于 BFS 连通性分析。
 * 如果提供了 edge_fidelities，仅包含保真度 > 0 的边（过滤掉损坏/禁用的边）。
 * 这确保选出的子图在 SABRE 的 fidelity_threshold 过滤后仍然连通。
 */
std::vector<std::vector<int>> build_adj_list(
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_physical) {
  std::vector<std::set<int>> neighbors_set(num_physical);
  for (size_t i = 0; i < coupling_list.size(); ++i) {
    const auto& edge = coupling_list[i];
    if (!edge_fidelities.empty() && edge_fidelities[i] <= 0.0) {
      continue;
    }
    neighbors_set[edge.first].insert(edge.second);
    neighbors_set[edge.second].insert(edge.first);
  }
  std::vector<std::vector<int>> neighbors(num_physical);
  for (int i = 0; i < num_physical; ++i) {
    neighbors[i].assign(neighbors_set[i].begin(), neighbors_set[i].end());
  }
  return neighbors;
}

/**
 * @brief BFS 收集从 start 出发的 num_logical 个连通物理节点。
 *
 * 使用 std::queue 标准 BFS；若从 start 出发无法收集到 num_logical
 * 个节点（图不连通），返回空 vector。
 *
 * @param neighbors 有向邻接表
 * @param start BFS 起始节点
 * @param num_logical 需收集的节点数
 * @return BFS 顺序的节点列表，长度等于 num_logical 或为空
 */
std::vector<int> bfs_collect(const std::vector<std::vector<int>>& neighbors,
                             int start, int num_logical) {
  std::vector<int> result;
  std::unordered_set<int> visited;
  std::queue<int> queue;

  queue.push(start);
  visited.insert(start);

  while (!queue.empty() && static_cast<int>(result.size()) < num_logical) {
    int current = queue.front();
    queue.pop();
    result.push_back(current);

    for (int neighbor : neighbors[current]) {
      if (visited.find(neighbor) == visited.end()) {
        visited.insert(neighbor);
        queue.push(neighbor);
      }
    }
  }

  if (static_cast<int>(result.size()) < num_logical) {
    return {};
  }
  return result;
}

/**
 * @brief 统计子图内部有向边数（两端均在 subgraph_set 内的边）
 */
int count_internal_edges(const std::vector<std::vector<int>>& neighbors,
                         const std::unordered_set<int>& subgraph_set) {
  int count = 0;
  for (int node : subgraph_set) {
    for (int neighbor : neighbors[node]) {
      if (subgraph_set.count(neighbor) > 0) {
        ++count;
      }
    }
  }
  return count;
}

/**
 * @brief 生成恒等映射 [0, 1, 2, ..., num_logical-1]
 */
std::vector<int> make_identity_mapping(int num_logical) {
  std::vector<int> result(num_logical);
  std::iota(result.begin(), result.end(), 0);
  return result;
}

}  // namespace

std::vector<int> dense_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical) {
  const int num_physical = count_physical_qubits(coupling_list);

  // 在开头做严格校验
  validate_dense_layout_inputs(coupling_list, edge_fidelities, num_logical,
                               num_physical);

  if (num_logical == 0) return {};

  auto neighbors =
      build_adj_list(coupling_list, edge_fidelities, num_physical);

  // 判断是否有边保真度数据（用于子图错误率评分）
  const bool use_fidelity = !edge_fidelities.empty();

  // 构建边错误率映射：(src, dst) 到 1 - edge_fidelity
  std::unordered_map<size_t, double> edge_errors;
  if (!edge_fidelities.empty()) {
    for (size_t i = 0; i < coupling_list.size(); ++i) {
      // 保真度 > 0 视为有效数据，否则跳过
      if (edge_fidelities[i] > 0.0) {
        size_t key =
            static_cast<size_t>(coupling_list[i].first) * num_physical +
            coupling_list[i].second;
        edge_errors[key] = 1.0 - edge_fidelities[i];
      }
    }
  }

  // 统计 2-qubit 门数量
  int two_qubit_gate_count = 0;
  for (const auto& gate : gates_list) {
    if (gate.operation_type == OperationType::DOUBLE_QUBIT_OPERATION) {
      ++two_qubit_gate_count;
    }
  }

  // 遍历每个物理节点作为 BFS 起点，找最优子图（密度优先，错误率低优先）
  int best_count = -1;
  double best_error = std::numeric_limits<double>::max();
  std::vector<int> best_subgraph;

  for (int start = 0; start < num_physical; ++start) {
    auto subgraph = bfs_collect(neighbors, start, num_logical);
    if (subgraph.empty()) continue;

    std::unordered_set<int> subgraph_set(subgraph.begin(), subgraph.end());
    int edge_count = count_internal_edges(neighbors, subgraph_set);

    // 计算该子图的错误得分
    double error_score = 0.0;
    if (use_fidelity) {
      // 2-qubit 门错误：子图内边的平均错误率
      if (!edge_fidelities.empty() && edge_count > 0) {
        double two_qubit_error_sum = 0.0;
        int two_qubit_edge_count = 0;
        for (int node : subgraph) {
          for (int neighbor : neighbors[node]) {
            if (subgraph_set.count(neighbor) > 0) {
              size_t key = static_cast<size_t>(node) * num_physical + neighbor;
              auto it = edge_errors.find(key);
              if (it != edge_errors.end()) {  // 有效数据
                two_qubit_error_sum += it->second;
                ++two_qubit_edge_count;
              }
            }
          }
        }
        if (two_qubit_edge_count > 0) {
          double two_qubit_avg = two_qubit_error_sum / two_qubit_edge_count;
          error_score += two_qubit_gate_count * two_qubit_avg;
        }
      }
    }

    // 比较器：优先内部边多，其次错误率低
    bool is_better = false;
    if (edge_count > best_count) {
      is_better = true;
    } else if (edge_count == best_count && use_fidelity &&
               error_score < best_error) {
      is_better = true;
    }

    if (is_better) {
      best_count = edge_count;
      best_error = error_score;
      best_subgraph = std::move(subgraph);
    }
  }

  if (best_subgraph.empty()) {
    return make_identity_mapping(num_logical);
  }

  // 以 DenseLayout 选出的区域为起点，通过 SABRE forward-backward 精化排列
  return sabre_initial_mapping(gates_list, coupling_list, best_subgraph);
}

}  // namespace qcos
