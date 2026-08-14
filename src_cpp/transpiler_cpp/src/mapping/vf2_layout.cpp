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
 *      WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include "mapping/vf2_layout.h"

#include <algorithm>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/vf2_sub_graph_iso.hpp>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <unordered_map>
#include <utility>
#include <vector>

#include "circuit/base_operation.h"

namespace qcos {

namespace {

using Graph =
    boost::adjacency_list<boost::vecS, boost::vecS, boost::undirectedS>;

/// 图的顶点编号属性(只读)，Boost 内部用来把顶点转成整数下标
using VertexIdMap =
    boost::property_map<Graph, boost::vertex_index_t>::const_type;

/// VF2 回调中的映射表: 交互图顶点 -> 耦合图顶点，可用 boost::get(f, v) 读写
using Vf2VertexMap = boost::iterator_property_map<
    std::vector<Graph::vertex_descriptor>::iterator, VertexIdMap,
    Graph::vertex_descriptor, Graph::vertex_descriptor&>;

// 默认最大搜索匹配数，防止解空间爆炸
constexpr int kMaxTrials = 10000;

using EdgeKey = std::pair<int, int>;

/**
 * @brief EdgeKey 的自定义哈希函数。
 *
 * std::pair<int,int> 没有默认的 std::hash 特化，无法直接用作
 * std::unordered_map 的键。此结构体提供哈希计算:
 * 将 first 和 second 的哈希值做异或(第二项左移16位以减少碰撞)。
 * 用于 edge_errors 无序表的键哈希。
 */
struct EdgeKeyHash {
  size_t operator()(const EdgeKey& k) const {
    return std::hash<int>()(k.first) ^ (std::hash<int>()(k.second) << 16);
  }
};

/**
 * @brief 原始编号与稠密编号的双向映射表。
 *
 * 用于把可能不连续的原始编号（逻辑比特或物理比特）映射为 Boost vecS
 * 要求的连续 0,1,2,... 顶点 ID。
 */
struct IdRemap {
  std::unordered_map<int, int> orig_to_dense;
  std::vector<int> dense_to_orig;  ///< dense_to_orig[i] = 原始编号
};

/**
 * @brief 对一组编号去重排序，建立稠密化映射表。
 *
 * @param ids 原始编号集合（已排序去重）
 * @return IdRemap 双向映射表
 */
IdRemap build_id_remap(const std::set<int>& ids) {
  IdRemap remap;
  remap.dense_to_orig.assign(ids.begin(), ids.end());
  remap.orig_to_dense.reserve(remap.dense_to_orig.size());
  for (int i = 0; i < static_cast<int>(remap.dense_to_orig.size()); ++i) {
    remap.orig_to_dense[remap.dense_to_orig[i]] = i;
  }
  return remap;
}

/**
 * @brief 交互图构建结果。
 *
 * 从电路两比特门提取的无向交互图，节点代表参与两比特门的逻辑比特，
 * 边代表两比特门交互对，edge_counts 记录每条边上的门计数用于评分。
 */
struct InteractionData {
  Graph graph;
  std::map<EdgeKey, int> edge_counts;  ///< (交互节点A, 交互节点B) -> 门数
  IdRemap remap;                       ///< 逻辑比特 <-> 交互图节点
};

/**
 * @brief 从电路两比特门提取交互图。
 *
 * 遍历门序列，收集所有两比特门涉及的逻辑比特并稠密化编号，
 * 构建 Boost 无向图（同一对比特多个门合并为一条边，门数记入 edge_counts）。
 *
 * @param gates_list 逻辑门序列
 * @return InteractionData 交互图 + 门计数 + 稠密化映射表
 */
InteractionData extract_interactions(
    const std::vector<GateOperation>& gates_list) {
  // 参与两比特门的逻辑比特集合
  std::set<int> coupled_logical;
  // 比特对上的两比特门数
  std::map<std::pair<int, int>, int> logical_pair_counts;
  for (const auto& gate : gates_list) {
    if (gate.operation_type == OperationType::DOUBLE_QUBIT_OPERATION) {
      int q0 = gate.targets[0];
      int q1 = gate.targets[1];
      coupled_logical.insert(q0);
      coupled_logical.insert(q1);
      logical_pair_counts[std::minmax(q0, q1)]++;
    }
  }

  InteractionData data;
  data.remap = build_id_remap(coupled_logical);
  data.graph = Graph(data.remap.dense_to_orig.size());
  for (const auto& [logical_edge, count] : logical_pair_counts) {
    int node_a = data.remap.orig_to_dense[logical_edge.first];
    int node_b = data.remap.orig_to_dense[logical_edge.second];
    boost::add_edge(node_a, node_b, data.graph);
    data.edge_counts[std::minmax(node_a, node_b)] = count;
  }
  return data;
}

/**
 * @brief 耦合图构建结果。
 *
 * 从芯片拓扑构建的无向耦合图，节点代表物理比特，边代表耦合连接。
 * edge_errors 存储每条物理边的错误率（1 - 保真度），供 VF2 评分使用。
 */
struct CouplingData {
  Graph graph;
  std::unordered_map<EdgeKey, double, EdgeKeyHash> edge_errors;
  IdRemap remap;  ///< 原始物理比特 <-> 稠密物理比特
};

/**
 * @brief 从芯片耦合边列表构建耦合图。
 *
 * 收集耦合边中出现的物理比特并稠密化编号，构建 Boost 无向图。
 * 当 edge_fidelities 非空时，跳过保真度 <= 0 的边，
 * 并记录每条边的错误率 = 1 - 保真度。
 *
 * @param coupling_list 物理耦合边列表（有向）
 * @param edge_fidelities 边保真度，与 coupling_list 对应，空则不使用保真度
 * @return CouplingData 耦合图 + 错误率表 + 稠密化映射表
 */
CouplingData build_coupling_graph(
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities) {
  // 耦合边中出现的物理比特集合(自动排序去重)
  std::set<int> physical_ids;
  for (const auto& e : coupling_list) {
    physical_ids.insert(e.first);
    physical_ids.insert(e.second);
  }

  CouplingData data;
  data.remap = build_id_remap(physical_ids);
  data.graph = Graph(data.remap.dense_to_orig.size());

  const bool use_fidelity = !edge_fidelities.empty();
  for (size_t i = 0; i < coupling_list.size(); ++i) {
    // 保真度 <= 0 的边不可用，跳过
    if (use_fidelity && edge_fidelities[i] <= 0.0) continue;
    // 原始物理比特编号 -> 稠密编号
    int node_a = data.remap.orig_to_dense[coupling_list[i].first];
    int node_b = data.remap.orig_to_dense[coupling_list[i].second];
    boost::add_edge(node_a, node_b, data.graph);
    if (use_fidelity && edge_fidelities[i] > 0.0) {
      // 错误率 = 1 - 保真度
      data.edge_errors[std::minmax(node_a, node_b)] = 1.0 - edge_fidelities[i];
    }
  }
  return data;
}

/**
 * @brief VF2 回调评分所需的只读上下文。
 *
 * 集中保存评分依赖的交互图、门计数、错误率表等引用，
 * 使 Vf2ScoringCallback 只需持有 ctx + state 两个 shared_ptr。
 */
struct Vf2Context {
  const Graph& interaction_graph;    ///< 交互图，从两比特门提取
  const IdRemap& interaction_remap;  ///< 逻辑比特 <-> 交互图节点 的映射表
  const std::map<EdgeKey, int>&
      interaction_edge_counts;  ///< 每条交互边的两比特门数
  const std::unordered_map<EdgeKey, double, EdgeKeyHash>&
      edge_errors;  ///< 每条物理边的错误率
  int num_logical;  ///< 电路声明的逻辑比特总数
};

/**
 * @brief VF2 搜索过程中的可写结果状态。
 *
 * 多个 callback 副本通过 shared_ptr 共享同一实例，
 * 任何一个副本找到更优解都会更新到同一块内存。
 */
struct Vf2ResultState {
  double best_score =
      std::numeric_limits<double>::max();  ///< 当前最优评分(越低越好)
  std::vector<int> best_mapping;           ///< 当前最优逻辑->物理映射
  int call_count = 0;                      ///< callback 被调用的次数
};

/**
 * @brief VF2 子图搜索的评分回调。
 *
 * Boost VF2 每找到一个合法嵌入就调用此对象。
 * 回调计算当前嵌入的总错误率(各交互边错误率 * 门数之和)，
 * 若优于已知最优则保存映射。
 * 返回 true 让 Boost 继续搜索下一个解，返回 false 终止搜索。
 *
 * 使用 shared_ptr 持有 ctx 和 state，因为 Boost VF2 内部会按值拷贝回调对象，
 * 共享指针确保所有副本读写同一份状态。
 */
struct Vf2ScoringCallback {
  std::shared_ptr<Vf2Context> ctx;        ///< 评分所需的只读上下文
  std::shared_ptr<Vf2ResultState> state;  ///< 搜索结果(可写)

  Vf2ScoringCallback(std::shared_ptr<Vf2Context> c,
                     std::shared_ptr<Vf2ResultState> s)
      : ctx(std::move(c)), state(std::move(s)) {}

  /**
   * @brief Boost VF2 每找到一个合法嵌入时调用。
   * @param interaction_to_coupling 当前嵌入: 交互图顶点 -> 耦合图顶点
   * @param g 耦合图自身的恒等映射(VF2 协议要求，未使用)
   * @return true 继续搜索，false 终止搜索
   */
  bool operator()(Vf2VertexMap interaction_to_coupling, Vf2VertexMap /*g*/) {
    // 累加所有交互边的错误贡献: 错误率 * 门数
    double score = 0.0;
    for (const auto& [ipair, count] : ctx->interaction_edge_counts) {
      // 查出该交互边两个端点映射到的物理比特
      int p0 = static_cast<int>(
          boost::get(interaction_to_coupling,
                     boost::vertex(ipair.first, ctx->interaction_graph)));
      int p1 = static_cast<int>(
          boost::get(interaction_to_coupling,
                     boost::vertex(ipair.second, ctx->interaction_graph)));
      // 查该物理边的错误率并累加
      auto it = ctx->edge_errors.find(std::minmax(p0, p1));
      if (it != ctx->edge_errors.end()) {
        score += it->second * count;
      }
    }

    // 当前嵌入评分优于已知最优，保存映射
    if (score < state->best_score) {
      state->best_score = score;
      // 初始化为全 -1，只有参与两比特门的逻辑比特会被赋值
      state->best_mapping.assign(ctx->num_logical, -1);
      for (size_t i = 0; i < ctx->interaction_remap.dense_to_orig.size();
           ++i) {
        // 查出交互图节点 i 映射到的物理比特(稠密编号)
        int physical = static_cast<int>(
            boost::get(interaction_to_coupling,
                       boost::vertex(i, ctx->interaction_graph)));
        // dense_to_orig[i] = 原始逻辑比特编号，用它作为映射数组索引
        state->best_mapping[ctx->interaction_remap.dense_to_orig[i]] =
            physical;
      }
    }

    // 控制最大搜索次数，防止解空间爆炸
    ++state->call_count;
    return state->call_count < kMaxTrials;
  }
};

/**
 * @brief 执行 VF2 子图单态搜索，返回评分最优的逻辑->物理映射。
 *
 * 将交互图嵌入耦合图中，每找到一个合法嵌入就评分，
 * 最终返回错误率最低的映射。
 *
 * @param interaction 交互图数据
 * @param coupling 耦合图数据
 * @param num_logical 逻辑比特总数
 * @return 逻辑->物理映射(稠密编号)，参与两比特门的逻辑比特已赋值，其余为 -1
 */
std::vector<int> run_vf2_search(const InteractionData& interaction,
                                const CouplingData& coupling,
                                int num_logical) {
  // 打包评分所需的只读引用到 shared_ptr，供 callback 共享
  auto ctx = std::make_shared<Vf2Context>(
      Vf2Context{interaction.graph, interaction.remap, interaction.edge_counts,
                 coupling.edge_errors, num_logical});
  // 搜索结果状态，callback 通过 shared_ptr 写入最优解
  auto state = std::make_shared<Vf2ResultState>();
  Vf2ScoringCallback callback(ctx, state);

  // 子图单态搜索: 在耦合图中找交互图的嵌入，每个解调 callback 评分
  boost::vf2_subgraph_mono(interaction.graph, coupling.graph, callback);
  return state->best_mapping;
}

/**
 * @brief 将未参与两比特门的逻辑比特分配到空闲物理比特上。
 *
 * 这些逻辑比特只参与单比特门，物理位置不影响路由，直接按序分配空闲物理比特。
 *
 * @param mapping 逻辑->物理映射(输入输出)，未分配的位置为 -1
 * @param coupling 耦合图数据
 * @param num_logical 逻辑比特总数
 */
void assign_remaining_qubits(std::vector<int>& mapping,
                             const CouplingData& coupling, int num_logical) {
  const int num_physical =
      static_cast<int>(coupling.remap.dense_to_orig.size());

  // 收集已被 VF2 映射占用的物理比特(稠密编号)
  std::set<int> used_physical;
  for (int mapped_phy : mapping) {
    if (mapped_phy >= 0) used_physical.insert(mapped_phy);
  }

  // 遍历物理比特，将空闲的分配给未映射的逻辑比特
  int logical_idx = 0;
  for (int candidate_phy = 0; candidate_phy < num_physical; ++candidate_phy) {
    if (used_physical.count(candidate_phy)) continue;
    // 跳过已映射的逻辑比特，找到下一个待分配位置
    while (logical_idx < num_logical && mapping[logical_idx] >= 0)
      ++logical_idx;
    if (logical_idx >= num_logical) break;
    mapping[logical_idx] = candidate_phy;
    ++logical_idx;
  }
}

/**
 * @brief 将映射中的稠密物理编号还原为原始物理比特编号。
 *
 * @param mapping 逻辑->物理映射(输入输出)
 * @param remap 稠密编号<->原始编号映射表
 */
void restore_original_ids(std::vector<int>& mapping, const IdRemap& remap) {
  for (int& p : mapping) {
    if (p >= 0) p = remap.dense_to_orig[p];
  }
}

}  // namespace

std::vector<int> vf2_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical) {
  if (coupling_list.empty() || num_logical <= 0) return {};

  // 1. 提取交互图
  auto interaction = extract_interactions(gates_list);
  if (interaction.remap.dense_to_orig.empty()) return {};

  // 2. 构建耦合图
  auto coupling = build_coupling_graph(coupling_list, edge_fidelities);
  const int num_physical =
      static_cast<int>(coupling.remap.dense_to_orig.size());
  if (num_logical > num_physical) return {};

  // 3. VF2 搜索完美嵌入
  auto mapping = run_vf2_search(interaction, coupling, num_logical);
  if (mapping.empty()) return {};

  // 4. 分配未参与两比特门的逻辑比特
  assign_remaining_qubits(mapping, coupling, num_logical);

  // 5. 还原原始物理编号
  restore_original_ids(mapping, coupling.remap);

  return mapping;
}

}  // namespace qcos
