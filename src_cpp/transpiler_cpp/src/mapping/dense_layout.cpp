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
#include <numeric>
#include <queue>
#include <set>
#include <unordered_map>
#include <unordered_set>

#include "mapping/sabre_mapping.h"

namespace qcos {

namespace {

/**
 * @brief 从 coupling_list 推断物理比特总数（最大节点 ID + 1）
 *
 * 用于按物理 ID 索引数组 (邻接表、保真度映射等)。
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
 * @brief 统计 coupling_list 中去重后的物理比特数
 *
 * 调用方 (SABRE) 已通过 select_largest_component 过滤为单连通分量,
 * 因此去重节点数即为最大连通分量的实际可用比特数, 用于容量校验。
 */
int count_unique_physical_qubits(
    const std::vector<std::pair<int, int>>& coupling_list) {
  std::unordered_set<int> qubits;
  for (const auto& edge : coupling_list) {
    qubits.insert(edge.first);
    qubits.insert(edge.second);
  }
  return static_cast<int>(qubits.size());
}

/**
 * @brief 校验 dense_layout_mapping 的输入参数
 * @throw std::invalid_argument 当参数不合法时
 *
 * 物理比特数用去重节点数 (而非 max_id+1), 排除不连通的孤立比特,
 * 避免过滤后图分裂时校验失效导致后续 SABRE 死循环。
 */
void validate_dense_layout_inputs(
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical) {
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

  const int num_unique_physical = count_unique_physical_qubits(coupling_list);
  if (num_logical > num_unique_physical) {
    throw std::invalid_argument("dense_layout_mapping: num_logical (" +
                                std::to_string(num_logical) +
                                ") > available physical qubits (" +
                                std::to_string(num_unique_physical) +
                                "); if fidelity filtering is enabled, try "
                                "lowering fidelity_threshold");
  }
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
 * @param neighbors 双向邻接表
 * @param start BFS 起始节点
 * @param num_logical 需收集的节点数
 * @return BFS 顺序的节点列表，长度等于 num_logical 或为空
 */
std::vector<int> bfs_gather_subgraph(
    const std::vector<std::vector<int>>& neighbors, int start,
    int num_logical) {
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
 * @brief 生成恒等映射 [0, 1, 2, ..., num_logical-1]
 */
std::vector<int> make_identity_mapping(int num_logical) {
  std::vector<int> result(num_logical);
  std::iota(result.begin(), result.end(), 0);
  return result;
}

/**
 * @brief 子图候选结构，包含 BFS 收集到的节点集合、内部有向边数和平均保真度
 */
struct SubgraphCandidate {
  std::vector<int> nodes;
  int edge_count;
  double fidelity_score;
};

/**
 * @brief 子图枚举结果，包含所有候选和最大内部边数（用于密度归一化）
 */
struct SubgraphEnumerationResult {
  std::vector<SubgraphCandidate> candidates;
  int max_edge_count;
};

/**
 * @brief BFS 枚举所有候选子图，同时统计边数和保真度
 *
 * 以每个物理节点为起点做 BFS，收集 num_logical 个连通节点。
 * 对每个子图一次性遍历内部边，同时统计边数和保真度。
 *
 * @param neighbors 双向邻接表
 * @param num_logical 需收集的节点数
 * @param edge_fidelity_map 边保真度映射（key = src * num_physical +
 * dst），可为空
 * @param num_physical 物理比特总数
 * @return SubgraphEnumerationResult 候选列表和最大内部边数
 */
SubgraphEnumerationResult enumerate_subgraph_candidates(
    const std::vector<std::vector<int>>& neighbors, int num_logical,
    const std::unordered_map<size_t, double>& edge_fidelity_map,
    int num_physical) {
  const bool use_fidelity = !edge_fidelity_map.empty();
  SubgraphEnumerationResult result;
  result.candidates.reserve(num_physical);
  result.max_edge_count = 0;

  for (int start = 0; start < num_physical; ++start) {
    auto subgraph = bfs_gather_subgraph(neighbors, start, num_logical);
    if (subgraph.empty()) continue;

    std::unordered_set<int> subgraph_set(subgraph.begin(), subgraph.end());

    // 一次遍历同时统计边数和保真度累加
    int edge_count = 0;
    double fidelity_sum = 0.0;
    int fidelity_edge_count = 0;
    for (int node : subgraph) {
      for (int neighbor : neighbors[node]) {
        if (subgraph_set.count(neighbor) > 0) {
          ++edge_count;
          if (use_fidelity) {
            size_t key = static_cast<size_t>(node) * num_physical + neighbor;
            auto it = edge_fidelity_map.find(key);
            if (it != edge_fidelity_map.end()) {
              fidelity_sum += it->second;
              ++fidelity_edge_count;
            }
          }
        }
      }
    }

    result.max_edge_count = std::max(result.max_edge_count, edge_count);
    double fidelity_score =
        (fidelity_edge_count > 0) ? fidelity_sum / fidelity_edge_count : 0.0;

    result.candidates.push_back(
        {std::move(subgraph), edge_count, fidelity_score});
  }

  return result;
}

}  // namespace

std::vector<int> dense_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical,
    double fidelity_weight) {
  const int num_physical = count_physical_qubits(coupling_list);

  // 在开头做严格校验
  validate_dense_layout_inputs(coupling_list, edge_fidelities, num_logical);

  if (num_logical == 0) return {};

  auto neighbors =
      build_adj_list(coupling_list, edge_fidelities, num_physical);

  // 判断是否有边保真度数据（用于子图保真度评分）
  const bool use_fidelity = !edge_fidelities.empty() && fidelity_weight != 0.0;

  // 构建边保真度映射：(src, dst) 到 fidelity
  std::unordered_map<size_t, double> edge_fidelity_map;
  if (use_fidelity) {
    for (size_t i = 0; i < coupling_list.size(); ++i) {
      if (edge_fidelities[i] > 0.0) {
        size_t key =
            static_cast<size_t>(coupling_list[i].first) * num_physical +
            coupling_list[i].second;
        edge_fidelity_map[key] = edge_fidelities[i];
      }
    }
  }

  // BFS 枚举所有候选子图，一次遍历同时统计边数和保真度
  auto enumeration = enumerate_subgraph_candidates(
      neighbors, num_logical, edge_fidelity_map, num_physical);

  // 分母用于密度归一化
  const double density_denom =
      (enumeration.max_edge_count > 0)
          ? static_cast<double>(enumeration.max_edge_count)
          : 1.0;

  // 遍历候选：计算加权综合评分，选最优子图
  // fidelity_weight=0 时退化为纯密度优先；
  // edge_fidelities 为空时，fidelity_score=0
  double best_combined_score = -1.0;
  std::vector<int> best_subgraph;

  for (auto& candidate : enumeration.candidates) {
    double density_score =
        static_cast<double>(candidate.edge_count) / density_denom;
    double combined_score = fidelity_weight * candidate.fidelity_score +
                            (1.0 - fidelity_weight) * density_score;

    if (combined_score > best_combined_score) {
      best_combined_score = combined_score;
      best_subgraph = std::move(candidate.nodes);
    }
  }

  if (best_subgraph.empty()) {
    return make_identity_mapping(num_logical);
  }

  // 以 DenseLayout 选出的区域为起点，通过 SABRE forward-backward 精化排列
  return sabre_initial_mapping(gates_list, coupling_list, best_subgraph);
}

}  // namespace qcos
