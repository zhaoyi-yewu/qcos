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

#include "circuit/multi_graph.h"

#include <algorithm>
#include <deque>
#include <queue>
#include <stdexcept>
#include <unordered_set>

namespace qcos {

std::shared_ptr<DAGNode> MultiGraph::clone_node(
    const std::shared_ptr<DAGNode>& node) {
  if (auto op = std::dynamic_pointer_cast<DAGOpNode>(node)) {
    auto copy = std::make_shared<DAGOpNode>(op->op, op->qargs, op->cargs);
    copy->flag = op->flag;
    return copy;
  }
  if (auto in = std::dynamic_pointer_cast<DAGInNode>(node)) {
    return std::make_shared<DAGInNode>(in->wire());
  }
  if (auto out = std::dynamic_pointer_cast<DAGOutNode>(node)) {
    return std::make_shared<DAGOutNode>(out->wire());
  }
  throw std::invalid_argument("Unsupported DAGNode subtype");
}

int MultiGraph::add_node(std::shared_ptr<DAGNode> node) {
  int id = static_cast<int>(slots_.size());
  slots_.push_back({std::move(node), {}, {}, true});
  slots_.back().node->set_node_id(id);
  ++num_active_;
  return id;
}

std::pair<int, int> MultiGraph::add_nodes(std::shared_ptr<DAGNode> first,
                                          std::shared_ptr<DAGNode> second) {
  return {add_node(std::move(first)), add_node(std::move(second))};
}

void MultiGraph::add_edge(int src, int dst, int wire) {
  slots_[src].out_edges.push_back({dst, wire});
  slots_[dst].in_edges.push_back({src, wire});
}

bool MultiGraph::has_edge(int src, int dst) const {
  if (src < 0 || dst < 0 || src >= static_cast<int>(slots_.size()) ||
      dst >= static_cast<int>(slots_.size()) || !slots_[src].active ||
      !slots_[dst].active) {
    return false;
  }
  for (const auto& edge : slots_[src].out_edges) {
    if (edge.target == dst) {
      return true;
    }
  }
  return false;
}

std::shared_ptr<DAGNode>& MultiGraph::operator[](int id) {
  return slots_[id].node;
}

const std::shared_ptr<DAGNode>& MultiGraph::operator[](int id) const {
  return slots_[id].node;
}

std::vector<std::shared_ptr<DAGNode>> MultiGraph::nodes() const {
  std::vector<std::shared_ptr<DAGNode>> result;
  result.reserve(num_active_);
  for (const auto& slot : slots_) {
    if (slot.active) {
      result.push_back(slot.node);
    }
  }
  return result;
}

std::vector<std::shared_ptr<DAGNode>> MultiGraph::successors(
    int node_id) const {
  std::vector<std::shared_ptr<DAGNode>> result;
  for (const auto& edge : slots_[node_id].out_edges) {
    if (slots_[edge.target].active) {
      result.push_back(slots_[edge.target].node);
    }
  }
  return result;
}

std::vector<std::shared_ptr<DAGNode>> MultiGraph::predecessors(
    int node_id) const {
  std::vector<std::shared_ptr<DAGNode>> result;
  for (const auto& edge : slots_[node_id].in_edges) {
    if (slots_[edge.target].active) {
      result.push_back(slots_[edge.target].node);
    }
  }
  return result;
}

std::vector<int> MultiGraph::successor_indices(int node_id) const {
  std::vector<int> result;
  for (const auto& edge : slots_[node_id].out_edges) {
    if (slots_[edge.target].active) {
      result.push_back(edge.target);
    }
  }
  return result;
}

std::vector<int> MultiGraph::predecessor_indices(int node_id) const {
  std::vector<int> result;
  for (const auto& edge : slots_[node_id].in_edges) {
    if (slots_[edge.target].active) {
      result.push_back(edge.target);
    }
  }
  return result;
}

std::vector<std::tuple<int, int, int>> MultiGraph::out_edges(
    int node_id) const {
  std::vector<std::tuple<int, int, int>> result;
  for (const auto& edge : slots_[node_id].out_edges) {
    if (slots_[edge.target].active) {
      result.emplace_back(node_id, edge.target, edge.wire);
    }
  }
  return result;
}

std::shared_ptr<DAGNode> MultiGraph::find_first_successor_by_edge(
    int node_id, const std::function<bool(int)>& predicate) const {
  for (const auto& edge : slots_[node_id].out_edges) {
    if (slots_[edge.target].active && predicate(edge.wire)) {
      return slots_[edge.target].node;
    }
  }
  return nullptr;
}

std::vector<std::shared_ptr<DAGNode>> MultiGraph::find_predecessors_by_edge(
    int node_id, const std::function<bool(int)>& predicate) const {
  std::vector<std::shared_ptr<DAGNode>> result;
  for (const auto& edge : slots_[node_id].in_edges) {
    if (slots_[edge.target].active && predicate(edge.wire)) {
      result.push_back(slots_[edge.target].node);
    }
  }
  return result;
}

std::vector<std::shared_ptr<DAGNode>> MultiGraph::find_successors_by_edge(
    int node_id, const std::function<bool(int)>& predicate) const {
  std::vector<std::shared_ptr<DAGNode>> result;
  for (const auto& edge : slots_[node_id].out_edges) {
    if (slots_[edge.target].active && predicate(edge.wire)) {
      result.push_back(slots_[edge.target].node);
    }
  }
  return result;
}

void MultiGraph::insert_node_on_in_edges_multiple(
    int new_node_id, const std::vector<int>& target_ids) {
  for (int target_id : target_ids) {
    std::vector<Edge> moved_edges = slots_[target_id].in_edges;
    slots_[target_id].in_edges.clear();

    for (const auto& edge : moved_edges) {
      auto& pred_out = slots_[edge.target].out_edges;
      pred_out.erase(std::remove_if(pred_out.begin(), pred_out.end(),
                                    [target_id, &edge](const Edge& item) {
                                      return item.target == target_id &&
                                             item.wire == edge.wire;
                                    }),
                     pred_out.end());
      slots_[edge.target].out_edges.push_back({new_node_id, edge.wire});
      slots_[new_node_id].in_edges.push_back({edge.target, edge.wire});
      slots_[new_node_id].out_edges.push_back({target_id, edge.wire});
      slots_[target_id].in_edges.push_back({new_node_id, edge.wire});
    }
  }
}

void MultiGraph::insert_node_on_out_edges_multiple(
    int new_node_id, const std::vector<int>& source_ids) {
  for (int source_id : source_ids) {
    std::vector<Edge> moved_edges = slots_[source_id].out_edges;
    slots_[source_id].out_edges.clear();

    for (const auto& edge : moved_edges) {
      auto& succ_in = slots_[edge.target].in_edges;
      succ_in.erase(std::remove_if(succ_in.begin(), succ_in.end(),
                                   [source_id, &edge](const Edge& item) {
                                     return item.target == source_id &&
                                            item.wire == edge.wire;
                                   }),
                    succ_in.end());
      slots_[new_node_id].out_edges.push_back({edge.target, edge.wire});
      slots_[edge.target].in_edges.push_back({new_node_id, edge.wire});
      slots_[source_id].out_edges.push_back({new_node_id, edge.wire});
      slots_[new_node_id].in_edges.push_back({source_id, edge.wire});
    }
  }
}

void MultiGraph::remove_node_retain_edges(int node_id) {
  for (const auto& in_edge : slots_[node_id].in_edges) {
    for (const auto& out_edge : slots_[node_id].out_edges) {
      if (in_edge.wire == out_edge.wire) {
        add_edge(in_edge.target, out_edge.target, in_edge.wire);
      }
    }
  }

  for (const auto& in_edge : slots_[node_id].in_edges) {
    auto& pred_out = slots_[in_edge.target].out_edges;
    pred_out.erase(std::remove_if(pred_out.begin(), pred_out.end(),
                                  [node_id](const Edge& edge) {
                                    return edge.target == node_id;
                                  }),
                   pred_out.end());
  }
  for (const auto& out_edge : slots_[node_id].out_edges) {
    auto& succ_in = slots_[out_edge.target].in_edges;
    succ_in.erase(std::remove_if(succ_in.begin(), succ_in.end(),
                                 [node_id](const Edge& edge) {
                                   return edge.target == node_id;
                                 }),
                  succ_in.end());
  }

  slots_[node_id].in_edges.clear();
  slots_[node_id].out_edges.clear();
  slots_[node_id].active = false;
  slots_[node_id].node.reset();
  --num_active_;
}

std::vector<int> MultiGraph::topo_order() const {
  std::unordered_map<int, int> in_degree;
  for (size_t index = 0; index < slots_.size(); ++index) {
    if (slots_[index].active) {
      in_degree[static_cast<int>(index)] =
          static_cast<int>(slots_[index].in_edges.size());
    }
  }

  std::vector<int> stack;
  std::vector<int> ready;
  ready.reserve(in_degree.size());
  for (const auto& [index, degree] : in_degree) {
    if (degree == 0) {
      ready.push_back(index);
    }
  }
  std::sort(ready.begin(), ready.end());
  for (int node_id : ready) {
    stack.push_back(node_id);
  }

  std::vector<int> order;
  order.reserve(num_active_);
  while (!stack.empty()) {
    int current = stack.back();
    stack.pop_back();
    order.push_back(current);
    std::vector<int> unlocked;
    for (const auto& edge : slots_[current].out_edges) {
      --in_degree[edge.target];
      if (in_degree[edge.target] == 0) {
        unlocked.push_back(edge.target);
      }
    }
    std::sort(unlocked.begin(), unlocked.end());
    for (int node_id : unlocked) {
      stack.push_back(node_id);
    }
  }
  return order;
}

std::vector<std::shared_ptr<DAGNode>>
MultiGraph::lexicographical_topological_sort(
    const std::function<std::string(const std::shared_ptr<DAGNode>&)>& key)
    const {
  std::unordered_map<int, int> in_degree;
  for (size_t index = 0; index < slots_.size(); ++index) {
    if (slots_[index].active) {
      in_degree[static_cast<int>(index)] =
          static_cast<int>(slots_[index].in_edges.size());
    }
  }

  auto cmp = [&](int lhs, int rhs) {
    const auto lhs_key = key(slots_[lhs].node);
    const auto rhs_key = key(slots_[rhs].node);
    if (lhs_key == rhs_key) {
      return lhs > rhs;
    }
    return lhs_key > rhs_key;
  };
  std::priority_queue<int, std::vector<int>, decltype(cmp)> pq(cmp);
  for (const auto& [index, degree] : in_degree) {
    if (degree == 0) {
      pq.push(index);
    }
  }

  std::vector<std::shared_ptr<DAGNode>> result;
  result.reserve(num_active_);
  while (!pq.empty()) {
    int current = pq.top();
    pq.pop();
    result.push_back(slots_[current].node);
    for (const auto& edge : slots_[current].out_edges) {
      --in_degree[edge.target];
      if (in_degree[edge.target] == 0) {
        pq.push(edge.target);
      }
    }
  }
  return result;
}

int MultiGraph::dag_longest_path_length() const {
  auto order = topo_order();
  std::unordered_map<int, int> distance;
  for (int node_id : order) {
    distance[node_id] = 0;
  }

  int max_distance = 0;
  for (int node_id : order) {
    for (const auto& edge : slots_[node_id].out_edges) {
      distance[edge.target] =
          std::max(distance[edge.target], distance[node_id] + 1);
      max_distance = std::max(max_distance, distance[edge.target]);
    }
  }
  return max_distance;
}

std::vector<int> MultiGraph::dag_longest_path() const {
  auto order = topo_order();
  if (order.empty()) {
    return {};
  }

  std::unordered_map<int, int> distance;
  std::unordered_map<int, int> previous;
  for (int node_id : order) {
    distance[node_id] = 0;
    previous[node_id] = -1;
  }

  int end_node = order.front();
  int max_distance = 0;
  for (int node_id : order) {
    for (const auto& edge : slots_[node_id].out_edges) {
      if (distance[edge.target] < distance[node_id] + 1) {
        distance[edge.target] = distance[node_id] + 1;
        previous[edge.target] = node_id;
        if (distance[edge.target] > max_distance) {
          max_distance = distance[edge.target];
          end_node = edge.target;
        }
      }
    }
  }

  std::vector<int> path;
  for (int current = end_node; current != -1; current = previous[current]) {
    path.push_back(current);
  }
  std::reverse(path.begin(), path.end());
  return path;
}

std::vector<std::vector<std::shared_ptr<DAGNode>>> MultiGraph::collect_runs(
    const std::function<bool(const std::shared_ptr<DAGNode>&)>& filter_fn)
    const {
  std::vector<std::vector<std::shared_ptr<DAGNode>>> runs;
  std::unordered_set<int> visited;

  for (int node_id : topo_order()) {
    if (visited.count(node_id) || !filter_fn(slots_[node_id].node)) {
      continue;
    }

    std::vector<std::shared_ptr<DAGNode>> run;
    int current = node_id;
    while (current >= 0 && !visited.count(current) &&
           filter_fn(slots_[current].node)) {
      visited.insert(current);
      run.push_back(slots_[current].node);

      int next = -1;
      std::unordered_set<int> active_successors;
      for (const auto& edge : slots_[current].out_edges) {
        if (slots_[edge.target].active) {
          active_successors.insert(edge.target);
        }
      }
      if (active_successors.size() == 1) {
        int candidate = *active_successors.begin();
        if (filter_fn(slots_[candidate].node)) {
          next = candidate;
        }
      }
      current = next;
    }
    if (!run.empty()) {
      runs.push_back(std::move(run));
    }
  }

  return runs;
}

}  // namespace qcos