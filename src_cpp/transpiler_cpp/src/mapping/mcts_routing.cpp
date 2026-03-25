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

#include "mapping/mcts_routing.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <optional>
#include <random>
#include <stdexcept>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace qcos {
namespace {

using GateSpec = MCTSGateSpec;
using DGNodeInfo = MCTSDGNode;

struct SwapScores {
  std::vector<std::pair<int, int>> swaps;
  std::vector<double> scores;
  std::vector<double> front_scores;
};

}  // namespace

struct CppMCTSRouting::Impl {
  explicit Impl(int selec_times = 5)
      : selec_times_(selec_times), rng_(std::random_device{}()) {}

  MCTSRoutingResult execute_routing(
      const MCTSSearchConfig& search_config, const MCTSArchitectureGraph& ag,
      const std::unordered_map<int, int>& initial_layout, int num_q_vir) {
    initialize(search_config, ag);
    run_search();
    return build_routing_result(initial_layout, num_q_vir);
  }

  int selec_times() const { return selec_times_; }
  void set_selec_times(int selec_times) { selec_times_ = selec_times; }

  struct FrontCircuitState {
    const Impl* owner = nullptr;
    int num_remain_nodes = 0;
    std::vector<int> log_to_phy;
    std::vector<int> phy_to_log;
    std::vector<int> first_gates;
    std::vector<int> front_layer;

    FrontCircuitState() = default;
    explicit FrontCircuitState(const Impl* routing) : owner(routing) {
      init();
    }

    void init() {
      if (owner == nullptr) {
        throw std::runtime_error("FrontCircuitState owner is null");
      }
      num_remain_nodes = owner->dg_size_;
      log_to_phy.assign(owner->num_q_log_, -1);
      phy_to_log.assign(owner->num_q_phy_, -1);
      first_gates.assign(owner->num_q_log_, -1);
      front_layer.clear();

      std::vector<int> current_nodes;
      std::unordered_set<int> used_nodes;
      for (int node : owner->dg_node_ids_) {
        if (owner->dg_nodes_.at(node).predecessors.empty()) {
          current_nodes.push_back(node);
          front_layer.push_back(node);
        }
      }
      int i = 0;
      while (i < owner->num_q_log_ && !current_nodes.empty()) {
        std::sort(current_nodes.begin(), current_nodes.end());
        const int node = current_nodes.front();
        current_nodes.erase(current_nodes.begin());
        used_nodes.insert(node);
        for (int q : owner->dg_nodes_.at(node).qubits) {
          if (first_gates[q] == -1) {
            first_gates[q] = node;
            ++i;
          }
        }
        for (int node_new : owner->dg_nodes_.at(node).successors) {
          if (used_nodes.count(node_new) > 0) {
            continue;
          }
          bool ready = true;
          for (int node_pre : owner->dg_nodes_.at(node_new).predecessors) {
            if (used_nodes.count(node_pre) == 0) {
              ready = false;
              break;
            }
          }
          if (ready) {
            current_nodes.push_back(node_new);
          }
        }
      }
    }

    std::size_t hash() const {
      std::size_t seed = 0;
      auto combine = [&seed](int value) {
        seed ^= std::hash<int>{}(value) + 0x9e3779b9 + (seed << 6) +
                (seed >> 2);
      };
      for (int value : front_layer) combine(value);
      combine(-7);
      for (int value : log_to_phy) combine(value);
      return seed;
    }

    bool executable(int node) const {
      const auto& qubits = owner->dg_nodes_.at(node).qubits;
      if (qubits.size() == 1) {
        return true;
      }
      const int q_phy0 = log_to_phy[qubits[0]];
      const int q_phy1 = log_to_phy[qubits[1]];
      return q_phy0 >= 0 && q_phy1 >= 0 &&
             owner->shortest_length_[q_phy0][q_phy1] == 1;
    }

    void execute_gate_index(int front_layer_i) {
      --num_remain_nodes;
      const int exe_node = front_layer[front_layer_i];
      front_layer.erase(front_layer.begin() + front_layer_i);
      const auto& qubits = owner->dg_nodes_.at(exe_node).qubits;
      for (int q : qubits) {
        first_gates[q] = -1;
      }

      std::vector<int> nodes_next = owner->dg_nodes_.at(exe_node).successors;
      std::sort(nodes_next.begin(), nodes_next.end());
      for (int node : nodes_next) {
        for (int q : owner->dg_nodes_.at(node).qubits) {
          if (first_gates[q] == -1) {
            first_gates[q] = node;
          }
        }
        bool ready = true;
        for (int q : owner->dg_nodes_.at(node).qubits) {
          if (first_gates[q] != node) {
            ready = false;
            break;
          }
        }
        if (ready) {
          front_layer.push_back(node);
        }
      }
    }

    void execute_gate(int node) {
      auto it = std::find(front_layer.begin(), front_layer.end(), node);
      if (it == front_layer.end()) {
        throw std::runtime_error("node not found in front_layer");
      }
      execute_gate_index(static_cast<int>(it - front_layer.begin()));
    }

    std::vector<int> execute_gates() {
      std::vector<int> exe_gates;
      int i = 0;
      int max_i = static_cast<int>(front_layer.size()) - 1;
      while (i <= max_i) {
        const int current_node = front_layer[i];
        if (executable(current_node)) {
          execute_gate_index(i);
          exe_gates.push_back(current_node);
          max_i = static_cast<int>(front_layer.size()) - 1;
        } else {
          ++i;
        }
      }
      return exe_gates;
    }

    std::vector<int> assign_mapping_from_list(const std::vector<int>& map_list) {
      for (int q_log = 0; q_log < owner->num_q_log_; ++q_log) {
        const int q_phy = map_list[q_log];
        log_to_phy[q_log] = q_phy;
        phy_to_log[q_phy] = q_log;
      }
      return execute_gates();
    }

    std::vector<int> swap(const std::pair<int, int>& swap_phy) {
      const int q_phy0 = swap_phy.first;
      const int q_phy1 = swap_phy.second;
      const int q_log0 = phy_to_log[q_phy0];
      const int q_log1 = phy_to_log[q_phy1];
      phy_to_log[q_phy0] = q_log1;
      phy_to_log[q_phy1] = q_log0;
      if (q_log0 != -1) log_to_phy[q_log0] = q_phy1;
      if (q_log1 != -1) log_to_phy[q_log1] = q_phy0;
      return execute_gates();
    }

    SwapScores pertinent_swaps(int score_layer) const {
      SwapScores result;
      std::vector<int> qubits_phy_node(owner->num_q_phy_, -1);

      for (int node : front_layer) {
        const auto& qubits = owner->dg_nodes_.at(node).qubits;
        if (qubits.size() != 2) {
          continue;
        }
        const int q0_phy = log_to_phy[qubits[0]];
        const int q1_phy = log_to_phy[qubits[1]];
        qubits_phy_node[q0_phy] = node;
        qubits_phy_node[q1_phy] = node;
      }

      for (const auto& swap_pair : owner->ag_edges_) {
        const int q0 = swap_pair.first;
        const int q1 = swap_pair.second;
        std::vector<int> qubits_phy_other(owner->num_q_phy_);
        std::iota(qubits_phy_other.begin(), qubits_phy_other.end(), 0);
        qubits_phy_other[q0] = q1;
        qubits_phy_other[q1] = q0;

        std::vector<int> involve_nodes;
        if (qubits_phy_node[q0] != -1) involve_nodes.push_back(qubits_phy_node[q0]);
        if (qubits_phy_node[q1] != -1) involve_nodes.push_back(qubits_phy_node[q1]);
        if (involve_nodes.empty()) {
          continue;
        }

        result.swaps.push_back(swap_pair);
        int i = 0;
        double current_score = 0.0;
        double current_score_front = 0.0;
        double decay = 1.0;
        for (int layer_i = 0; layer_i < score_layer; ++layer_i) {
          const int i_max = static_cast<int>(involve_nodes.size());
          while (i <= i_max - 1) {
            const int node = involve_nodes[i++];
            const auto& qubits = owner->dg_nodes_.at(node).qubits;
            if (qubits.size() != 2) {
              continue;
            }
            const int q_phy0 = log_to_phy[qubits[0]];
            const int q_phy1 = log_to_phy[qubits[1]];
            if (q_phy0 == q0 || q_phy0 == q1 || q_phy1 == q0 || q_phy1 == q1) {
              const int dis_before = owner->shortest_length_[q_phy0][q_phy1];
              const int q0_after = qubits_phy_other[q_phy0];
              const int q1_after = qubits_phy_other[q_phy1];
              const int dis_after = owner->shortest_length_[q0_after][q1_after];
              const double score_add =
                  static_cast<double>(dis_before - dis_after);
              if (layer_i == 0) {
                current_score_front += score_add;
              }
              current_score += score_add * decay;
              for (int node_next : owner->dg_nodes_.at(node).successors) {
                if (std::find(involve_nodes.begin(), involve_nodes.end(),
                              node_next) == involve_nodes.end()) {
                  involve_nodes.push_back(node_next);
                }
              }
            }
          }
          decay *= 0.7;
        }
        result.scores.push_back(current_score);
        result.front_scores.push_back(current_score_front);
      }
      return result;
    }

    std::pair<std::vector<int>, std::vector<int>> get_future_cx_fix_num(
        int num_cx) const {
      FrontCircuitState temp = *this;
      std::vector<int> cx0;
      std::vector<int> cx1;
      int i = 0;
      while (i < num_cx && temp.num_remain_nodes > 0) {
        ++i;
        if (temp.front_layer.empty()) {
          throw std::runtime_error("Empty front layer");
        }
        const int node = temp.front_layer[0];
        const auto& qubits = owner->dg_nodes_.at(node).qubits;
        cx0.push_back(temp.log_to_phy[qubits[0]]);
        cx1.push_back(temp.log_to_phy[qubits[1]]);
        temp.execute_gate(node);
      }
      return {cx0, cx1};
    }

    std::tuple<std::vector<int>, std::vector<int>, std::vector<int>,
               std::vector<int>>
    get_future_cx_fix_num_with_single(int num_cx) const {
      FrontCircuitState temp = *this;
      std::vector<int> cx0;
      std::vector<int> cx1;
      std::vector<int> single_gate0;
      std::vector<int> single_gate1;
      int i = 0;
      while (i < num_cx && temp.num_remain_nodes > 0) {
        ++i;
        if (temp.front_layer.empty()) {
          throw std::runtime_error("Empty front layer");
        }
        const int node = temp.front_layer[0];
        const auto& qubits = owner->dg_nodes_.at(node).qubits;
        int d0 = -1;
        int d1 = -1;
        cx0.push_back(temp.log_to_phy[qubits[0]]);
        cx1.push_back(temp.log_to_phy[qubits[1]]);
        for (const auto& gate : owner->dg_nodes_.at(node).gates) {
          if (gate.qubits.size() == 1) {
            const int q = gate.qubits[0];
            if (q == qubits[0]) ++d0;
            if (q == qubits[1]) ++d1;
          } else if (gate.qubits.size() == 2) {
            const int depth_after = std::max(d0, d1) + 1;
            d0 = depth_after;
            d1 = depth_after;
          }
        }
        single_gate0.push_back(d0);
        single_gate1.push_back(d1);
        temp.execute_gate(node);
      }
      return {cx0, cx1, single_gate0, single_gate1};
    }
  };

  struct TreeNode {
    std::int64_t id = -1;
    std::int64_t father_node = -1;
    FrontCircuitState circuit;
    std::vector<std::int64_t> children;
    std::optional<std::pair<int, int>> added_swap;
    std::vector<int> executed_gates;
    int num_add_gates = 0;
    double local_score = 0.0;
    double global_score = 0.0;
    int visited_time = 0;
    int num_remain_gates = 0;
    std::vector<double> depth_phy_qubits;
    double depth_add = 0.0;
    double depth = 0.0;
  };

  int selec_times_ = 5;

  std::unordered_map<int, DGNodeInfo> dg_nodes_;
  std::vector<int> dg_node_ids_;
  int dg_size_ = 0;

  int num_q_log_ = 0;
  int num_q_phy_ = 0;
  int max_length_ = 0;
  int fallback_value_ = 0;
  int fallback_count_ = 0;
  int selec_count_ = 0;
  int node_count_ = 0;

  std::vector<std::vector<int>> adjacency_;
  std::vector<std::pair<int, int>> ag_edges_;
  std::vector<std::vector<int>> shortest_length_;
  std::vector<std::vector<std::vector<int>>> shortest_path_;

  std::vector<int> init_mapping_;
  std::string objective_ = "size";
  std::string select_mode_name_ = "KS";
  double select_mode_param_ = 20.0;
  std::string mode_bp_name_ = "globalscore";
  std::string mode_decision_name_ = "global_score";
  std::string mode_sim_name_ = "fix_cx_num";
  int mode_sim_times_ = 50;
  int mode_sim_num_cx_ = 10;
  int score_layer_ = 5;
  bool use_prune_ = true;
  bool use_hash_ = true;
  bool opt_depth_ = false;
  double score_decay_rate_size_ = 0.7;
  double score_decay_rate_depth_ = 0.85;
  double decay_ = 0.7;

  std::int64_t root_node_ = -1;
  std::int64_t init_node_ = -1;
  std::unordered_map<std::int64_t, TreeNode> nodes_;

  std::mt19937 rng_;

  void initialize(const MCTSSearchConfig& search_config,
                  const MCTSArchitectureGraph& ag) {
    objective_ = search_config.objective;
    select_mode_name_ = search_config.select_mode_name;
    select_mode_param_ = search_config.select_mode_param;
    mode_bp_name_ = search_config.mode_bp_name;
    mode_decision_name_ = search_config.mode_decision_name;
    mode_sim_name_ = search_config.mode_sim_name;
    mode_sim_times_ = search_config.mode_sim_times;
    mode_sim_num_cx_ = search_config.mode_sim_num_cx;
    score_layer_ = search_config.score_layer;
    use_prune_ = search_config.use_prune;
    use_hash_ = search_config.use_hash;
    init_mapping_ = search_config.init_mapping;
    score_decay_rate_size_ = search_config.score_decay_rate_size;
    score_decay_rate_depth_ = search_config.score_decay_rate_depth;

    opt_depth_ = objective_ == "depth";
    decay_ = opt_depth_ ? score_decay_rate_depth_ : score_decay_rate_size_;

    build_ag_cache(ag);
    build_dg_cache(search_config.dg);

    max_length_ = 0;
    for (int i = 0; i < num_q_phy_; ++i) {
      for (int j = 0; j < num_q_phy_; ++j) {
        if (shortest_length_[i][j] < std::numeric_limits<int>::max() / 8) {
          max_length_ = std::max(max_length_, shortest_length_[i][j]);
        }
      }
    }
    fallback_value_ = max_length_ * 2;
    fallback_count_ = 0;
    selec_count_ = 0;
    node_count_ = 0;
    nodes_.clear();

    root_node_ = add_node_mcts(-1, std::nullopt).value();
    init_node_ = root_node_;
  }

  void build_ag_cache(const MCTSArchitectureGraph& ag) {
    int max_node = -1;
    for (int node : ag.nodes) {
      max_node = std::max(max_node, node);
    }
    for (const auto& edge : ag.edges) {
      max_node = std::max(max_node, std::max(edge.first, edge.second));
    }
    if (max_node < 0) {
      throw std::runtime_error("Architecture graph is empty");
    }

    num_q_phy_ = max_node + 1;
    adjacency_.assign(num_q_phy_, {});
    ag_edges_ = ag.edges;

    for (const auto& edge : ag_edges_) {
      adjacency_[edge.first].push_back(edge.second);
      adjacency_[edge.second].push_back(edge.first);
    }

    const int inf = std::numeric_limits<int>::max() / 4;
    shortest_length_.assign(num_q_phy_, std::vector<int>(num_q_phy_, inf));
    shortest_path_.assign(
        num_q_phy_,
        std::vector<std::vector<int>>(num_q_phy_, std::vector<int>()));

    for (int start = 0; start < num_q_phy_; ++start) {
      std::vector<int> parent(num_q_phy_, -1);
      std::vector<int> queue;
      queue.push_back(start);
      shortest_length_[start][start] = 0;
      parent[start] = start;

      for (std::size_t idx = 0; idx < queue.size(); ++idx) {
        const int u = queue[idx];
        for (int v : adjacency_[u]) {
          if (shortest_length_[start][v] > shortest_length_[start][u] + 1) {
            shortest_length_[start][v] = shortest_length_[start][u] + 1;
            parent[v] = u;
            queue.push_back(v);
          }
        }
      }

      for (int target = 0; target < num_q_phy_; ++target) {
        if (parent[target] == -1) continue;
        std::vector<int> path;
        int current = target;
        while (current != start) {
          path.push_back(current);
          current = parent[current];
        }
        path.push_back(start);
        std::reverse(path.begin(), path.end());
        shortest_path_[start][target] = std::move(path);
      }
    }
  }

  void build_dg_cache(const MCTSDependencyGraph& dg) {
    dg_nodes_ = dg.nodes;
    dg_node_ids_.clear();
    dg_node_ids_.reserve(dg_nodes_.size());
    for (const auto& [node_id, _] : dg_nodes_) {
      dg_node_ids_.push_back(node_id);
    }
    std::sort(dg_node_ids_.begin(), dg_node_ids_.end());
    dg_size_ = static_cast<int>(dg_node_ids_.size());
    num_q_log_ = dg.num_q_log;
  }

  static double median(std::vector<double> values) {
    if (values.empty()) return -std::numeric_limits<double>::infinity();
    std::sort(values.begin(), values.end());
    const std::size_t mid = values.size() / 2;
    if (values.size() % 2 == 0) {
      return (values[mid - 1] + values[mid]) / 2.0;
    }
    return values[mid];
  }

  std::vector<std::int64_t> active_children(std::int64_t node_id) const {
    std::vector<std::int64_t> children;
    auto it = nodes_.find(node_id);
    if (it == nodes_.end()) return children;
    for (std::int64_t child : it->second.children) {
      if (nodes_.find(child) != nodes_.end()) {
        children.push_back(child);
      }
    }
    return children;
  }

  void remove_child_link(std::int64_t parent, std::int64_t child) {
    if (parent == -1) return;
    auto it = nodes_.find(parent);
    if (it == nodes_.end()) return;
    auto& children = it->second.children;
    children.erase(std::remove(children.begin(), children.end(), child),
                   children.end());
  }

  double node_cost(std::int64_t node_id) const {
    const auto& node = nodes_.at(node_id);
    return opt_depth_ ? node.depth : static_cast<double>(node.num_add_gates);
  }

  void add_depth(TreeNode& node) {
    const auto& log_to_phy = node.circuit.log_to_phy;
    if (node.father_node == -1) {
      node.depth_add = 0.0;
      node.depth_phy_qubits.assign(num_q_phy_, 0.0);
    } else {
      const auto& father = nodes_.at(node.father_node);
      node.depth_phy_qubits = father.depth_phy_qubits;
      double depth_after = *std::max_element(node.depth_phy_qubits.begin(),
                                             node.depth_phy_qubits.end());
      if (node.added_swap.has_value()) {
        const int q0 = node.added_swap->first;
        const int q1 = node.added_swap->second;
        const double max_depth =
            std::max(node.depth_phy_qubits[q0], node.depth_phy_qubits[q1]) + 3.0;
        node.depth_phy_qubits[q0] = max_depth;
        node.depth_phy_qubits[q1] = max_depth;
        depth_after = *std::max_element(node.depth_phy_qubits.begin(),
                                        node.depth_phy_qubits.end());
      }
      node.depth_add =
          std::max(depth_after -
                       *std::max_element(father.depth_phy_qubits.begin(),
                                         father.depth_phy_qubits.end()),
                   0.0);
    }

    for (int node_dg : node.executed_gates) {
      for (const auto& gate : dg_nodes_.at(node_dg).gates) {
        if (gate.qubits.size() == 1) {
          const int q_phy = log_to_phy[gate.qubits[0]];
          node.depth_phy_qubits[q_phy] += 1.0;
        } else if (gate.qubits.size() == 2) {
          const int q_phy0 = log_to_phy[gate.qubits[0]];
          const int q_phy1 = log_to_phy[gate.qubits[1]];
          const double depth_after =
              std::max(node.depth_phy_qubits[q_phy0], node.depth_phy_qubits[q_phy1]) +
              1.0;
          node.depth_phy_qubits[q_phy0] = depth_after;
          node.depth_phy_qubits[q_phy1] = depth_after;
        }
      }
    }
    node.depth = *std::max_element(node.depth_phy_qubits.begin(),
                                   node.depth_phy_qubits.end());
  }

  std::optional<std::int64_t> add_node_mcts(
      std::int64_t father_node, std::optional<std::pair<int, int>> added_swap) {
    TreeNode new_node;
    new_node.father_node = father_node;
    new_node.circuit = FrontCircuitState(this);

    if (father_node == -1) {
      new_node.executed_gates =
          new_node.circuit.assign_mapping_from_list(init_mapping_);
      new_node.num_add_gates = 0;
      if (objective_ == "no_swap" && new_node.circuit.num_remain_nodes > 0) {
        throw std::runtime_error("Fail to find a mapping requiring no swaps.");
      }
    } else {
      new_node.circuit = nodes_.at(father_node).circuit;
      if (!added_swap.has_value()) {
        throw std::runtime_error("Either added_swap must be provided");
      }
      new_node.added_swap = added_swap;
      new_node.executed_gates = new_node.circuit.swap(*added_swap);
      new_node.num_add_gates = nodes_.at(father_node).num_add_gates + 3;
    }

    new_node.local_score = static_cast<double>(new_node.executed_gates.size());
    new_node.global_score = new_node.local_score;
    new_node.visited_time = 0;
    new_node.num_remain_gates = new_node.circuit.num_remain_nodes;
    add_depth(new_node);

    std::int64_t new_id = use_hash_
                              ? static_cast<std::int64_t>(new_node.circuit.hash())
                              : static_cast<std::int64_t>(node_count_);

    if (use_hash_ && nodes_.find(new_id) != nodes_.end()) {
      if (opt_depth_ ? (new_node.depth < nodes_.at(new_id).depth)
                     : (new_node.num_add_gates < nodes_.at(new_id).num_add_gates)) {
        auto old_children = nodes_.at(new_id).children;
        const std::int64_t old_father = nodes_.at(new_id).father_node;
        const double old_global =
            nodes_.at(new_id).global_score - nodes_.at(new_id).local_score;
        remove_child_link(old_father, new_id);
        new_node.id = new_id;
        new_node.children = old_children;
        new_node.global_score = old_global + new_node.local_score;
        nodes_[new_id] = std::move(new_node);
        if (father_node != -1) {
          auto& children = nodes_.at(father_node).children;
          if (std::find(children.begin(), children.end(), new_id) ==
              children.end()) {
            children.push_back(new_id);
          }
        }
        for (auto child : old_children) {
          nodes_.at(child).father_node = new_id;
        }
        delete_false_leaf(old_father);
        selec_count_ +=
            std::min(static_cast<int>(nodes_.at(new_id).local_score), 1);
        return new_id;
      }
      return std::nullopt;
    }

    if (!use_hash_) {
      ++node_count_;
    }
    new_node.id = new_id;
    nodes_[new_id] = std::move(new_node);
    if (father_node != -1) {
      nodes_.at(father_node).children.push_back(new_id);
    }
    selec_count_ +=
        std::min(static_cast<int>(nodes_.at(new_id).local_score), 1);
    return new_id;
  }

  std::pair<std::int64_t, double> pick_best_son(std::int64_t node_id,
                                                bool decision_mode) const {
    const auto children = active_children(node_id);
    if (children.empty()) return {-1, 0.0};

    std::int64_t picked_node = -1;
    double picked_value = -std::numeric_limits<double>::infinity();

    for (std::int64_t son : children) {
      const auto& son_node = nodes_.at(son);
      double score = son_node.global_score;
      if (opt_depth_) {
        score *= std::pow(score_decay_rate_depth_, son_node.depth_add);
      }

      double value = score;
      if (!decision_mode && select_mode_name_ == "KS") {
        const double parent_visit = std::max(1, nodes_.at(node_id).visited_time);
        const double sqrt_term = std::sqrt(
            std::log(parent_visit) / (son_node.visited_time + 0.001));
        value = score + select_mode_param_ * sqrt_term;
      }

      if (picked_node == -1 || value > picked_value) {
        picked_node = son;
        picked_value = value;
      }
    }
    return {picked_node, picked_value};
  }

  void back_propagation(std::int64_t start_node) {
    if (mode_bp_name_ != "globalscore") {
      throw std::runtime_error("Unsupported BP method");
    }
    double discount = decay_;
    double new_value = nodes_.at(start_node).global_score;
    std::int64_t current_node = nodes_.at(start_node).father_node;
    if (opt_depth_) {
      discount = std::pow(decay_, nodes_.at(start_node).depth_add);
    }
    while (current_node != -1 && current_node != root_node_) {
      auto& node = nodes_.at(current_node);
      const double old_value = node.global_score;
      new_value = node.local_score + new_value * discount;
      if (new_value > old_value) {
        node.global_score = new_value;
        if (opt_depth_) {
          discount = std::pow(decay_, node.depth_add);
        }
        current_node = node.father_node;
      } else {
        break;
      }
    }
  }

  int sim_function_size(const std::vector<int>& gate0,
                        const std::vector<int>& gate1,
                        const std::vector<int>& mapping, int times_sim) {
    if (gate0.empty()) return 0;
    int min_num_swaps = std::numeric_limits<int>::max();

    for (int sim = 0; sim < times_sim; ++sim) {
      std::vector<int> sim_mapping = mapping;
      int num_swaps = 0;
      int current_gate_idx = 0;

      while (current_gate_idx < static_cast<int>(gate0.size())) {
        while (current_gate_idx < static_cast<int>(gate0.size())) {
          const int u = sim_mapping[gate0[current_gate_idx]];
          const int v = sim_mapping[gate1[current_gate_idx]];
          if (shortest_length_[u][v] == 1) {
            ++current_gate_idx;
          } else {
            break;
          }
        }
        if (current_gate_idx >= static_cast<int>(gate0.size())) break;

        const int u = sim_mapping[gate0[current_gate_idx]];
        const int v = sim_mapping[gate1[current_gate_idx]];
        const int old_dist = shortest_length_[u][v];
        std::vector<int> if_values;
        std::vector<std::pair<int, int>> valid_swaps;
        for (const auto& edge : ag_edges_) {
          const int p = edge.first;
          const int q = edge.second;
          if (p == u || p == v || q == u || q == v) {
            const int new_u = (u == p ? q : (u == q ? p : u));
            const int new_v = (v == p ? q : (v == q ? p : v));
            const int new_dist = shortest_length_[new_u][new_v];
            if_values.push_back(new_dist < old_dist ? 1 : 0);
            valid_swaps.push_back(edge);
          }
        }

        std::pair<int, int> best_swap{-1, -1};
        if (valid_swaps.empty()) {
          const auto& path = shortest_path_[u][v];
          if (path.size() > 1) {
            best_swap = {u, path[1]};
          } else {
            break;
          }
        } else {
          const int total_if =
              std::accumulate(if_values.begin(), if_values.end(), 0);
          int idx = 0;
          if (total_if == 0) {
            std::uniform_int_distribution<int> dist(
                0, static_cast<int>(valid_swaps.size()) - 1);
            idx = dist(rng_);
          } else {
            std::discrete_distribution<int> dist(if_values.begin(),
                                                 if_values.end());
            idx = dist(rng_);
          }
          best_swap = valid_swaps[idx];
        }

        const int p = best_swap.first;
        const int q = best_swap.second;
        for (int& value : sim_mapping) {
          if (value == p) {
            value = q;
          } else if (value == q) {
            value = p;
          }
        }
        ++num_swaps;
      }

      min_num_swaps = std::min(min_num_swaps, num_swaps);
    }

    return min_num_swaps == std::numeric_limits<int>::max() ? 0
                                                            : min_num_swaps;
  }

  void simulation(std::int64_t sim_node) {
    if (sim_node == root_node_) {
      return;
    }
    auto& node = nodes_.at(sim_node);
    if (mode_sim_name_ != "fix_cx_num") {
      throw std::runtime_error("Unsupported simulation method");
    }

    if (!opt_depth_) {
      auto [gate0, gate1] =
          node.circuit.get_future_cx_fix_num(mode_sim_num_cx_);
      if (static_cast<int>(gate0.size()) < mode_sim_num_cx_) {
        return;
      }
      std::vector<int> mapping(num_q_phy_);
      std::iota(mapping.begin(), mapping.end(), 0);
      const int num_swap_sim =
          sim_function_size(gate0, gate1, mapping, mode_sim_times_);
      const double sim_score =
          static_cast<double>(gate0.size()) * std::pow(decay_, num_swap_sim / 2.0);
      const double new_value = node.local_score + sim_score;
      if (new_value > node.global_score) {
        node.global_score = new_value;
        back_propagation(sim_node);
      }
      return;
    }

    auto [gate0, gate1, single_gate0, single_gate1] =
        node.circuit.get_future_cx_fix_num_with_single(mode_sim_num_cx_);
    if (static_cast<int>(gate0.size()) < mode_sim_num_cx_) {
      return;
    }
    std::vector<int> mapping(num_q_phy_);
    std::iota(mapping.begin(), mapping.end(), 0);
    const int num_swap_sim =
        sim_function_size(gate0, gate1, mapping, mode_sim_times_);
    const double num_depth_swap = static_cast<double>(num_swap_sim * 2);
    const double num_gates = static_cast<double>(gate0.size());
    const double h_score =
        num_gates *
        std::pow(std::pow(0.85, num_depth_swap / std::max(num_swap_sim, 1)),
                 num_swap_sim / 2.0);
    const double new_value = node.local_score + h_score;
    if (new_value > node.global_score) {
      node.global_score = new_value;
      back_propagation(sim_node);
    }
  }

  std::vector<std::int64_t> expansion(std::int64_t node_id) {
    if (!active_children(node_id).empty()) {
      throw std::runtime_error("Expanded node already has son nodes.");
    }
    if (nodes_.at(node_id).num_remain_gates == 0) {
      ++selec_count_;
      return {};
    }

    const auto swap_scores =
        nodes_.at(node_id).circuit.pertinent_swaps(score_layer_);
    const double score_threshold =
        use_prune_ ? std::min(0.0, median(swap_scores.scores))
                   : -std::numeric_limits<double>::infinity();

    std::vector<std::int64_t> added_nodes;
    for (std::size_t i = 0; i < swap_scores.swaps.size(); ++i) {
      if (swap_scores.scores[i] < score_threshold &&
          swap_scores.front_scores[i] <= 0.0) {
        continue;
      }
      auto add_node = add_node_mcts(node_id, swap_scores.swaps[i]);
      if (!add_node.has_value()) {
        continue;
      }
      added_nodes.push_back(*add_node);
      if (score_layer_ == 0) continue;
      const double h_score = swap_scores.scores[i] * decay_;
      nodes_.at(*add_node).global_score += h_score;
      nodes_.at(*add_node).local_score += h_score;
    }

    for (auto add_node : added_nodes) {
      simulation(add_node);
    }

    if (!active_children(node_id).empty()) {
      auto [best_son, _] = pick_best_son(node_id, true);
      if (best_son != -1) {
        back_propagation(best_son);
      }
    } else {
      delete_false_leaf(node_id);
    }
    return added_nodes;
  }

  std::pair<std::int64_t, int> selection() {
    std::int64_t current_node = root_node_;
    int search_depth = 0;
    while (!active_children(current_node).empty()) {
      ++search_depth;
      auto [next_node, _] = pick_best_son(current_node, false);
      current_node = next_node;
      ++nodes_.at(current_node).visited_time;
    }
    return {current_node, search_depth};
  }

  void erase_subtree(std::int64_t node_id) {
    auto it = nodes_.find(node_id);
    if (it == nodes_.end()) return;
    auto children = it->second.children;
    for (auto child : children) {
      erase_subtree(child);
    }
    remove_child_link(it->second.father_node, node_id);
    nodes_.erase(node_id);
  }

  void delete_false_leaf(std::int64_t node_id) {
    std::int64_t current = node_id;
    while (current != -1 && current != root_node_) {
      auto it = nodes_.find(current);
      if (it == nodes_.end() || !active_children(current).empty()) {
        break;
      }
      const std::int64_t father = it->second.father_node;
      remove_child_link(father, current);
      nodes_.erase(current);
      current = father;
    }
  }

  void fallback() {
    std::int64_t start_node = root_node_;
    std::int64_t deleted_node = -1;
    while (start_node != init_node_ &&
           nodes_.at(start_node).local_score == 0.0) {
      deleted_node = start_node;
      start_node = nodes_.at(start_node).father_node;
    }

    const auto& circuit = nodes_.at(start_node).circuit;
    int min_cx_dis = std::numeric_limits<int>::max();
    std::pair<int, int> chosen_cx_phy{-1, -1};
    for (int v : circuit.front_layer) {
      const auto& cx = dg_nodes_.at(v).qubits;
      const std::pair<int, int> cx_phy{circuit.log_to_phy[cx[0]],
                                       circuit.log_to_phy[cx[1]]};
      const int current_dis = shortest_length_[cx_phy.first][cx_phy.second];
      if (current_dis < min_cx_dis) {
        min_cx_dis = current_dis;
        chosen_cx_phy = cx_phy;
      }
    }
    if (chosen_cx_phy.first == -1) {
      throw std::runtime_error("No executable vertex found");
    }

    auto path = shortest_path_[chosen_cx_phy.first][chosen_cx_phy.second];
    const int num_swap = min_cx_dis - 1;
    root_node_ = start_node;
    if (deleted_node != -1) {
      erase_subtree(deleted_node);
    }

    bool from_front = true;
    for (int i = 0; i < num_swap; ++i) {
      std::pair<int, int> added_swap;
      if (from_front) {
        added_swap = {path.front(), path[1]};
        path.erase(path.begin());
      } else {
        added_swap = {path.back(), path[path.size() - 2]};
        path.pop_back();
      }
      from_front = !from_front;
      auto added_node = add_node_mcts(root_node_, added_swap);
      if (!added_node.has_value()) {
        throw std::runtime_error("Fallback expansion failed");
      }
      root_node_ = *added_node;
    }

    if (nodes_.at(root_node_).local_score == 0.0) {
      throw std::runtime_error("Fallback error!");
    }
  }

  std::int64_t decision() {
    const std::int64_t father_node = root_node_;
    auto [best_son, _] = pick_best_son(father_node, true);
    if (best_son == -1) {
      return root_node_;
    }

    selec_count_ = 0;
    auto children = active_children(father_node);
    for (auto child : children) {
      if (child != best_son) {
        erase_subtree(child);
      }
    }
    nodes_.at(father_node).children = {best_son};

    if (nodes_.at(best_son).local_score == 0.0) {
      ++fallback_count_;
    } else {
      fallback_count_ = 0;
    }

    if (fallback_count_ >= fallback_value_) {
      fallback();
      fallback_count_ = 0;
      return root_node_;
    }

    root_node_ = best_son;
    return root_node_;
  }

  void run_search() {
    while (nodes_.at(root_node_).num_remain_gates > 0) {
      while (selec_count_ < selec_times_) {
        auto [exp_node, _] = selection();
        expansion(exp_node);
      }
      decision();
    }
  }

  void append_decomposed_swap(std::vector<GateSpec>& mapped_ir, int q0,
                              int q1) const {
    mapped_ir.push_back({"cx", {q0, q1}, {}});
    mapped_ir.push_back({"cx", {q1, q0}, {}});
    mapped_ir.push_back({"cx", {q0, q1}, {}});
  }

  MCTSRoutingResult build_routing_result(
      const std::unordered_map<int, int>& initial_layout, int num_q_vir) const {
    MCTSRoutingResult result;
    std::vector<std::pair<int, int>> swaps;
    std::int64_t node_id = init_node_;
    while (true) {
      const auto& node = nodes_.at(node_id);
      if (node.added_swap.has_value()) {
        const auto [q0, q1] = *node.added_swap;
        swaps.push_back(*node.added_swap);
        append_decomposed_swap(result.mapped_ir, q0, q1);
      }

      for (int node_dg : node.executed_gates) {
        for (const auto& gate : dg_nodes_.at(node_dg).gates) {
          std::vector<int> qubits_phy;
          qubits_phy.reserve(gate.qubits.size());
          for (int q_log : gate.qubits) {
            qubits_phy.push_back(node.circuit.log_to_phy[q_log]);
          }
          result.mapped_ir.push_back(
              {gate.name, std::move(qubits_phy), gate.params});
        }
      }

      auto children = active_children(node_id);
      if (children.empty()) {
        break;
      }
      if (children.size() > 1) {
        throw std::runtime_error("Multiple successors found");
      }
      node_id = children[0];
    }

    std::vector<int> swap_mapping(num_q_phy_);
    std::iota(swap_mapping.begin(), swap_mapping.end(), 0);
    for (const auto& swap : swaps) {
      std::swap(swap_mapping[swap.first], swap_mapping[swap.second]);
    }

    std::unordered_map<int, int> swap_mapping_reverse;
    for (int i = 0; i < static_cast<int>(swap_mapping.size()); ++i) {
      swap_mapping_reverse[swap_mapping[i]] = i;
    }

    for (const auto& [logical, physical] : initial_layout) {
      if (logical >= num_q_vir) {
        continue;
      }
      auto it = swap_mapping_reverse.find(physical);
      result.mapping_virtual_to_final[logical] =
          it != swap_mapping_reverse.end() ? it->second : physical;
    }

    return result;
  }
};

CppMCTSRouting::CppMCTSRouting(int selec_times)
    : impl_(std::make_unique<Impl>(selec_times)) {}

CppMCTSRouting::~CppMCTSRouting() = default;

CppMCTSRouting::CppMCTSRouting(CppMCTSRouting&&) noexcept = default;

CppMCTSRouting& CppMCTSRouting::operator=(CppMCTSRouting&&) noexcept = default;

MCTSRoutingResult CppMCTSRouting::execute_routing(
    const MCTSSearchConfig& search_config, const MCTSArchitectureGraph& ag,
    const std::unordered_map<int, int>& initial_layout, int num_q_vir) {
  return impl_->execute_routing(search_config, ag, initial_layout, num_q_vir);
}

int CppMCTSRouting::selec_times() const { return impl_->selec_times(); }

void CppMCTSRouting::set_selec_times(int selec_times) {
  impl_->set_selec_times(selec_times);
}

}  // namespace qcos
