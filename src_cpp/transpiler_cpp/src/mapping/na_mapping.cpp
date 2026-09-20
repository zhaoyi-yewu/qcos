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

#include "mapping/na_mapping.h"

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <queue>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace qcos {

namespace {

/// Position separator ('\0' cannot appear in a position name, so the key
/// parses unambiguously).
constexpr char kEdgeSep = '\0';

/// Strip the leading character of a position string (e.g. "P27", "S100") and
/// convert the remainder to an integer.
int pos_to_int(const std::string& pos) {
  if (pos.empty()) {
    throw std::invalid_argument("invalid position: empty string");
  }
  return std::stoi(pos.substr(1));
}

/// Check whether a string is in a vector.
bool contains(const std::vector<std::string>& vec, const std::string& v) {
  return std::find(vec.begin(), vec.end(), v) != vec.end();
}

/// Build a position -> -1 occupancy map over the given position list.
std::unordered_map<std::string, int> make_empty_oloc(
    const std::vector<std::string>& positions) {
  std::unordered_map<std::string, int> oloc;
  oloc.reserve(positions.size());
  for (const auto& p : positions) oloc.emplace(p, -1);
  return oloc;
}

/// Lowercase a string in-place (ASCII); used for case-insensitive
/// na_mapping_type dispatch.
std::string to_lower(std::string s) {
  for (char& c : s) {
    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  }
  return s;
}

/// Whether the operation is a Move.
bool is_move(const BaseOperation& op) {
  return op.operation_type == OperationType::MOVE;
}

}  // namespace

// ===================== NAGraph =====================

void NAGraph::add_edge(const std::string& a, const std::string& b) {
  adj[a].insert(b);
  adj[b].insert(a);
}

const std::unordered_set<std::string>& NAGraph::neighbors(
    const std::string& p) const {
  static const std::unordered_set<std::string> k_empty;
  auto it = adj.find(p);
  if (it == adj.end()) return k_empty;
  return it->second;
}

bool NAGraph::is_adjacent(const std::string& a, const std::string& b) const {
  auto it = adj.find(a);
  return it != adj.end() && it->second.count(b) > 0;
}

/**
 * @brief For every node that has neighbors, run BFS to compute the hop-count
 *        distance to every other reachable node, stored in shortest_length.
 *        Powers all later "find a free spot near X" lookups.
 */
void NAGraph::build_shortest_length() {
  // For each node with neighbors, run BFS to compute shortest-path distances
  // to every other node.
  for (const auto& [src, nbrs] : adj) {
    auto& dist = shortest_length[src];
    dist[src] = 0;
    std::queue<std::string> q;
    q.push(src);
    while (!q.empty()) {
      std::string cur = q.front();
      q.pop();
      int d = dist[cur];
      auto it = adj.find(cur);
      if (it == adj.end()) continue;
      for (const auto& nxt : it->second) {
        if (dist.find(nxt) != dist.end()) continue;
        dist[nxt] = d + 1;
        q.push(nxt);
      }
    }
  }
}

// ===================== NASingleRoute =====================

/**
 * @brief Load the gate list and QPU topology and assign each logical qubit to
 *        the storage position with the lowest readout error (ties broken by
 *        position name), truncating to qbit_num positions.
 *
 * @throw std::runtime_error if storage_area has fewer than qbit_num positions.
 *
 * Only couplers whose both ends lie in operate_area are added to the graph.
 */
void NASingleRoute::prepare_data(
    int qbit_num,
    const std::vector<std::shared_ptr<BaseOperation>>& gates,
    const NAQpuConfig& qpu_config) {
  qpu_config_ = qpu_config;
  ag_ = NAGraph{};
  for (const auto& entry : qpu_config_.coupler_map) {
    const std::string& a = entry.second.first;
    const std::string& b = entry.second.second;
    if (!contains(qpu_config_.operate_area, a) ||
        !contains(qpu_config_.operate_area, b)) {
      continue;
    }
    ag_.add_edge(a, b);
  }
  ag_.build_shortest_length();

  gates_ = gates;
  qbit_num_ = qbit_num;
  if (static_cast<int>(qpu_config_.storage_area.size()) < qbit_num_) {
    throw std::runtime_error("not enough qubits, need " +
                              std::to_string(qbit_num_) + ", but only " +
                              std::to_string(qpu_config_.storage_area.size()));
  }

  // Pick the qbit_num positions in storage_area with the lowest readout error.
  std::vector<std::pair<std::string, double>> err_list;
  for (const auto& [pos, err] : qpu_config_.readout_error) {
    if (contains(qpu_config_.storage_area, pos)) {
      err_list.emplace_back(pos, err);
    }
  }
  std::sort(err_list.begin(), err_list.end(),
            [](const auto& lhs, const auto& rhs) {
              if (lhs.second != rhs.second) return lhs.second < rhs.second;
              return lhs.first < rhs.first;
            });
  if (static_cast<int>(err_list.size()) > qbit_num_) {
    err_list.resize(qbit_num_);
  }
  logical_to_storage.clear();
  for (int i = 0; i < static_cast<int>(err_list.size()); ++i) {
    logical_to_storage[i] = err_list[i].first;
  }
}

/**
 * @brief Execute the gate list in order for a single-route (no shuttling)
 *        layout: rewrite each gate's logical target to its storage position,
 *        run all non-measure gates grouped per qubit, then append measurements.
 *
 * @return {result, {}} — the rewritten gate list. The second element (layout
 *         map) is empty for this path.
 */
std::pair<std::vector<std::shared_ptr<BaseOperation>>,
          std::unordered_map<int, int>>
NASingleRoute::execute_with_order() {
  std::unordered_map<int, std::vector<std::shared_ptr<BaseOperation>>>
      gates_on_qubit;
  std::vector<std::shared_ptr<BaseOperation>> measure;

  for (auto& gate : gates_) {
    if (gate->targets.size() != 1) {
      throw std::runtime_error(
          "invalid targets num: " + std::to_string(gate->targets.size()) +
          ", Gate " + gate->name + " must have exactly one target");
    }
    std::vector<int> new_targets;
    new_targets.reserve(gate->targets.size());
    for (int q : gate->targets) {
      auto it = logical_to_storage.find(q);
      if (it == logical_to_storage.end()) {
        throw std::runtime_error("logical qubit " + std::to_string(q) +
                                 " has no storage mapping");
      }
      new_targets.push_back(pos_to_int(it->second));
    }
    gate->targets = std::move(new_targets);

    if (gate->name == "measure") {
      measure.push_back(gate);
      continue;
    }
    gates_on_qubit[gate->targets[0]].push_back(gate);
  }

  std::vector<std::shared_ptr<BaseOperation>> result;
  for (auto& entry : gates_on_qubit) {
    for (auto& g : entry.second) result.push_back(g);
  }
  for (auto& g : measure) result.push_back(g);
  return {result, {}};
}

// ===================== NARoute (base) =====================

std::vector<std::shared_ptr<BaseOperation>> NARoute::execute_with_opt() {
  auto [res, layout] = execute_with_order();
  (void)layout;
  return res;
}

// ===================== NADefaultRoute =====================

std::pair<std::string, std::string> NADefaultRoute::sorted_edge(const std::string& a,
                                                         const std::string& b) {
  return a <= b ? std::make_pair(a, b) : std::make_pair(b, a);
}

std::string NADefaultRoute::edge_key(const std::string& a, const std::string& b) {
  auto pr = sorted_edge(a, b);
  return pr.first + std::string(1, kEdgeSep) + pr.second;
}

std::pair<std::string, std::string> NADefaultRoute::parse_edge_key(
    const std::string& key) {
  auto pos = key.find(kEdgeSep);
  if (pos == std::string::npos) {
    return {key, ""};
  }
  return {key.substr(0, pos), key.substr(pos + 1)};
}

std::shared_ptr<BaseOperation> NADefaultRoute::make_move(int q,
                                                  const std::string& from,
                                                  const std::string& to) {
  auto op = std::make_shared<Move>(std::vector<int>{q},
                                   std::vector<double>{0.0, 0.0},
                                   OperationType::MOVE);
  move_positions_[op.get()] = {from, to};
  return op;
}

/**
 * @brief Load the logical gate list and QPU topology, then build the adjacency
 *        graph (with BFS shortest-path distances) that all later routing
 *        decisions use.
 *
 * @par Inputs:
 *        qbit_num   number of logical qubits to place;
 *        gates      the logical gate list to route;
 *        qpu_config QPU topology — operate_area, storage_area, coupler_map,
 *                   readout_error.
 *
 * @throw std::runtime_error if storage_area has fewer than qbit_num positions.
 *
 * Only couplers whose both ends lie in operate_area are added to the graph,
 * since two-qubit gates can only execute there.
 */
void NADefaultRoute::prepare_data(
    int qbit_num,
    const std::vector<std::shared_ptr<BaseOperation>>& gates,
    const NAQpuConfig& qpu_config) {
  qpu_config_ = qpu_config;
  ag_ = NAGraph{};
  for (const auto& entry : qpu_config_.coupler_map) {
    const std::string& a = entry.second.first;
    const std::string& b = entry.second.second;
    if (!contains(qpu_config_.operate_area, a) ||
        !contains(qpu_config_.operate_area, b)) {
      continue;
    }
    ag_.add_edge(a, b);
  }
  ag_.build_shortest_length();

  gates_ = gates;
  qbit_num_ = qbit_num;
  if (static_cast<int>(qpu_config_.storage_area.size()) < qbit_num_) {
    throw std::runtime_error("not enough qubits, need " +
                              std::to_string(qbit_num_) + ", but only " +
                              std::to_string(qpu_config_.operate_area.size()));
  }
}

/**
 * @brief Build the routing DAG: collapse the flat logical gate list into a
 *        dependency graph whose nodes are the schedulable units.
 *
 * @return (dag, measure_op, node_indices) where:
 *         dag          node vector — single-qubit gates on the same qubit are
 *                      chained by successor edges (and merged when consecutive);
 *                      two-qubit gates depend on the last node touching each
 *                      of their qubits;
 *         measure_op  measure gates, kept aside to append last;
 *         node_indices original gate index -> dag node index.
 *
 * Each node records qubits, type ("single"/"multi"), original_idx, in_degree,
 * and successors. "sync" gates are skipped.
 */
std::tuple<std::vector<NADagNode>,
           std::vector<std::shared_ptr<BaseOperation>>,
           std::unordered_map<int, int>>
NADefaultRoute::get_rx_dag() {
  std::vector<NADagNode> dg;
  std::vector<std::shared_ptr<BaseOperation>> measure_op;
  std::unordered_map<int, int> node_indices;
  std::unordered_map<int, int> pre_nodes;  // qubit -> last node index (-1 absent)

  for (int idx = 0; idx < static_cast<int>(gates_.size()); ++idx) {
    const auto& gate = gates_[idx];
    if (gate->name == "sync" || gate->name == "measure") {
      if (gate->name == "measure") measure_op.push_back(gate);
      continue;
    }

    if (gate->targets.size() == 1) {
      int qubit = gate->targets[0];
      auto it = pre_nodes.find(qubit);
      if (it == pre_nodes.end() || it->second == -1) {
        NADagNode node;
        node.gate = {gate};
        node.qubits = gate->targets;
        node.type = "single";
        node.original_idx = idx;
        node.in_degree = 0;
        int node_idx = static_cast<int>(dg.size());
        dg.push_back(std::move(node));
        pre_nodes[qubit] = node_idx;
        node_indices[idx] = node_idx;
      } else {
        int prev_node_idx = it->second;
        if (dg[prev_node_idx].type == "single" &&
            dg[prev_node_idx].qubits.size() == 1 &&
            dg[prev_node_idx].qubits[0] == qubit) {
          // Merge: append the current gate to the predecessor's gate list.
          dg[prev_node_idx].gate.push_back(gate);
        } else {
          NADagNode node;
          node.gate = {gate};
          node.qubits = gate->targets;
          node.type = "single";
          node.original_idx = idx;
          node.in_degree = 1;  // has one incoming edge from prev
          int node_idx = static_cast<int>(dg.size());
          // Note: push_back may reallocate dg, so the predecessor must be
          // accessed via dg[prev_node_idx] afterwards to avoid a dangling ref.
          dg.push_back(std::move(node));
          dg[prev_node_idx].successors.push_back(node_idx);
          pre_nodes[qubit] = node_idx;
          node_indices[idx] = node_idx;
        }
      }
    } else {
      NADagNode node;
      node.gate = {gate};
      node.qubits = gate->targets;
      node.type = "multi";
      node.original_idx = idx;
      node.in_degree = 0;
      int node_idx = static_cast<int>(dg.size());
      dg.push_back(std::move(node));
      node_indices[idx] = node_idx;

      // Note: node was moved into dg; subsequent edge updates must go through
      // dg[node_idx].
      for (int qid : gate->targets) {
        auto it = pre_nodes.find(qid);
        if (it != pre_nodes.end() && it->second != -1 &&
            it->second != node_idx) {
          dg[it->second].successors.push_back(node_idx);
          dg[node_idx].in_degree += 1;
        }
        pre_nodes[qid] = node_idx;
      }
    }
  }

  return {dg, measure_op, node_indices};
}

/**
 * @brief Reset all routing state to a clean starting point: build the DAG,
 *        assign each logical qubit to its initial storage position, and clear
 *        the operate-area layout, edge occupancy, and lock set.
 *
 * Initial placement picks the qbit_num storage positions with the lowest
 * readout error (ties broken by position name). Called at the start of every
 * execute path so each run begins from a deterministic mapping.
 */
void NADefaultRoute::get_init_mapping() {
  auto [dg, measure, node_indices] = get_rx_dag();
  dag_ = std::move(dg);
  measure_ = std::move(measure);
  node_indices_ = std::move(node_indices);

  has_pre_node_ = false;
  pre_node_idx_ = -1;
  dag_opt_ = dag_;  // deep copy for node removal and front-layer lookup

  std::vector<std::pair<std::string, double>> err_list;
  for (const auto& [pos, err] : qpu_config_.readout_error) {
    if (contains(qpu_config_.storage_area, pos)) {
      err_list.emplace_back(pos, err);
    }
  }
  std::sort(err_list.begin(), err_list.end(),
            [](const auto& lhs, const auto& rhs) {
              if (lhs.second != rhs.second) return lhs.second < rhs.second;
              return lhs.first < rhs.first;
            });
  if (static_cast<int>(err_list.size()) > qbit_num_) {
    err_list.resize(qbit_num_);
  }
  logical_to_storage.clear();
  for (int i = 0; i < static_cast<int>(err_list.size()); ++i) {
    logical_to_storage[i] = err_list[i].first;
  }

  logical_to_op.clear();
  for (int a = 0; a < qbit_num_; ++a) logical_to_op[a] = "";

  op_to_logical.clear();
  for (const auto& a : qpu_config_.operate_area) op_to_logical[a] = -1;

  op_occupied_.clear();
  free_edges_.clear();
  for (const auto& [src, nbrs] : ag_.adj) {
    for (const auto& nxt : nbrs) {
      free_edges_.insert(edge_key(src, nxt));
    }
  }
  locked_.clear();
  res_.clear();
}

/**
 * @brief Return the current front layer: dag_opt_ nodes whose in_degree is 0
 *        and whose gate list is non-empty — i.e. the gates ready to run now.
 */
std::vector<int> NADefaultRoute::get_front_layer() const {
  std::vector<int> front_layer;
  for (int i = 0; i < static_cast<int>(dag_opt_.size()); ++i) {
    if (dag_opt_[i].in_degree == 0 && !dag_opt_[i].gate.empty()) {
      front_layer.push_back(i);
    }
  }
  return front_layer;
}

/**
 * @brief Find an operate-area position whose nearest occupied neighbor is at
 *        least `dis` hops away — i.e. a spot with enough clearance to drop a
 *        qubit without crowding existing atoms.
 * @return the position name, or "" if none qualifies.
 */
std::string NADefaultRoute::find_pos(int dis) const {
  std::unordered_set<std::string> disable_pos;
  for (const auto& o : op_occupied_) {
    disable_pos.insert(o);
    auto it = ag_.shortest_length.find(o);
    if (it == ag_.shortest_length.end()) continue;
    for (const auto& [nxt, d] : it->second) {
      if (d < dis) disable_pos.insert(nxt);
    }
  }
  for (const auto& o : qpu_config_.operate_area) {
    if (disable_pos.find(o) == disable_pos.end()) return o;
  }
  return "";
}

/**
 * @brief Move qubit q out of operate-area position o back to its storage
 *        position: emit a MOVE op, clear the qubit's operate mapping, free o,
 *        and re-add edges incident to o (whose other end is also free) to
 *        free_edges_.
 */
void NADefaultRoute::back(const std::string& o) {
  int q = op_to_logical[o];
  auto storage_it = logical_to_storage.find(q);
  if (storage_it == logical_to_storage.end()) {
    throw std::runtime_error("back: qubit " + std::to_string(q) +
                             " has no storage mapping");
  }
  res_.push_back(make_move(q, o, storage_it->second));
  logical_to_op[q] = "";
  op_to_logical[o] = -1;
  op_occupied_.erase(o);
  for (const auto& nxt : ag_.neighbors(o)) {
    if (op_occupied_.find(nxt) == op_occupied_.end()) {
      free_edges_.insert(edge_key(o, nxt));
    }
  }
}

/**
 * @brief Move qubit q from its storage position into operate-area position o:
 *        emit a MOVE op, update logical_to_op / op_to_logical, mark o occupied,
 *        and remove all edges incident to o from free_edges_.
 */
void NADefaultRoute::put(int q, const std::string& o) {
  auto storage_it = logical_to_storage.find(q);
  if (storage_it == logical_to_storage.end()) {
    throw std::runtime_error("put: qubit " + std::to_string(q) +
                             " has no storage mapping");
  }
  res_.push_back(make_move(q, storage_it->second, o));
  logical_to_op[q] = o;
  op_to_logical[o] = q;
  op_occupied_.insert(o);
  for (const auto& nxt : ag_.neighbors(o)) {
    free_edges_.erase(edge_key(o, nxt));
  }
}

/**
 * @brief Relocate a qubit from operate-area position o1 to o2: emit a MOVE op
 *        and update op_occupied_ / op_to_logical_ / logical_to_op_, then refresh
 *        free_edges_ for both positions (free edges around o1, occupy edges
 *        around o2).
 */
void NADefaultRoute::mov(const std::string& o1, const std::string& o2) {
  int q = op_to_logical[o1];
  res_.push_back(make_move(q, o1, o2));
  logical_to_op[q] = o2;
  op_to_logical[o1] = -1;
  op_to_logical[o2] = q;
  op_occupied_.erase(o1);
  op_occupied_.insert(o2);
  for (const auto& nxt : ag_.neighbors(o1)) {
    if (op_occupied_.find(nxt) == op_occupied_.end()) {
      free_edges_.insert(edge_key(o1, nxt));
    }
  }
  for (const auto& nxt : ag_.neighbors(o2)) {
    free_edges_.erase(edge_key(o2, nxt));
  }
}

/**
 * @brief Back out every qubit that is currently in the operate area but is NOT
 *        needed by any node in `nodes`, freeing room for the upcoming gates.
 *
 * Iterates over a snapshot of op_occupied_ so backing out (which mutates the
 * set) does not invalidate the loop.
 */
void NADefaultRoute::pre_back(const std::vector<NADagNode>& nodes) {
  std::unordered_set<int> all_q;
  for (const auto& node : nodes) {
    for (int q : node.qubits) all_q.insert(q);
  }
  // Copy the currently occupied positions to avoid mutating during iteration.
  std::vector<std::string> ohas(op_occupied_.begin(), op_occupied_.end());
  for (const auto& o : ohas) {
    int logical = op_to_logical[o];
    if (all_q.find(logical) == all_q.end()) back(o);
  }
}

std::string NADefaultRoute::get_empty_neighbor(const std::string& p) const {
  std::unordered_set<std::string> n = ag_.neighbors(p);
  // Remove the intersection with op_occupied_.
  for (const auto& o : op_occupied_) n.erase(o);
  if (n.empty()) return "";
  return *n.begin();
}

std::string NADefaultRoute::get_unlocked_neighbor(const std::string& p) const {
  for (const auto& nxt : ag_.neighbors(p)) {
    if (locked_.find(nxt) == locked_.end()) return nxt;
  }
  return "";
}

/**
 * @brief Try to bring two already-placed qubits onto adjacent positions.
 * @return true if p1 and p2 ended up adjacent (or already were).
 *
 * Tries in order: (1) move p2 onto an empty neighbor of p1; (2) move p1 onto an
 * empty neighbor of p2; (3) back an unlocked neighbor of p1/p2 then move the
 * other qubit there. Each successful branch locks p1/p2 and the landing spot
 * so subsequent placements don't displace them.
 */
bool NADefaultRoute::mov_to_neighbors(const std::string& p1,
                               const std::string& p2) {
  if (ag_.is_adjacent(p1, p2)) return true;
  std::string d = get_empty_neighbor(p1);
  if (!d.empty()) {
    mov(p2, d);
    locked_.insert(p1);
    locked_.insert(d);
    return true;
  }
  d = get_empty_neighbor(p2);
  if (!d.empty()) {
    mov(p1, d);
    locked_.insert(p2);
    locked_.insert(d);
    return true;
  }
  d = get_unlocked_neighbor(p1);
  if (!d.empty()) {
    back(d);
    mov(p2, d);
    locked_.insert(p1);
    locked_.insert(d);
    return true;
  }
  d = get_unlocked_neighbor(p2);
  if (!d.empty()) {
    back(d);
    mov(p2, d);
    locked_.insert(p2);
    locked_.insert(d);
    return true;
  }
  return false;
}

/**
 * @brief Place a single qubit q onto an empty neighbor of an already-placed
 *        qubit at p1, locking p1 and the landing spot. @return false if p1 has
 *        no empty neighbor.
 */
bool NADefaultRoute::put_to_neighbors1(const std::string& p1, int q) {
  std::string d = get_empty_neighbor(p1);
  if (d.empty()) return false;
  put(q, d);
  locked_.insert(p1);
  locked_.insert(d);
  return true;
}

/**
 * @brief Place two not-yet-placed qubits onto a free edge (two adjacent
 *        operate-area positions), consuming that edge and locking both spots.
 * @return false if no free edge remains.
 */
bool NADefaultRoute::put_to_neighbors2(int q1, int q2) {
  if (free_edges_.empty()) return false;
  std::string key = *free_edges_.begin();
  auto [a, b] = parse_edge_key(key);
  free_edges_.erase(key);
  put(q1, a);
  put(q2, b);
  locked_.insert(a);
  locked_.insert(b);
  return true;
}

/**
 * @brief Execute a group of two-qubit nodes: move each pair onto an adjacent
 *        edge, back out the qubits of any node that could not be placed, emit
 *        the surviving gates into res_, and remove the executed nodes from
 *        dag_opt_.
 *
 * Two phases: mov_multi_nodes() attempts the placement and returns the nodes
 * it could not place (`remain`); those nodes' qubits are backed out, and the
 * remaining nodes are emitted and removed from the DAG. Updates pre_node_idx_ /
 * has_pre_node_ to the last executed node for the next overlap round.
 */
void NADefaultRoute::execute_multi_nodes(const std::vector<NADagNode>& nodes) {
  locked_.clear();
  std::vector<NADagNode> remain = mov_multi_nodes(nodes);
  for (const auto& node : remain) {
    for (int q : node.qubits) {
      const auto& op = logical_to_op[q];
      if (!op.empty()) back(op);
    }
  }
  for (const auto& node : nodes) {
    // Check whether node is in remain (compared via original_idx).
    bool in_remain = false;
    for (const auto& r : remain) {
      if (r.original_idx == node.original_idx) {
        in_remain = true;
        break;
      }
    }
    if (in_remain) continue;
    pre_node_idx_ = -1;
    has_pre_node_ = false;
    // pre_node records the current node's index into dag_ (aligned with dag_opt_).
    auto ni = node_indices_.find(node.original_idx);
    if (ni != node_indices_.end()) {
      pre_node_idx_ = ni->second;
      has_pre_node_ = true;
    }
    for (const auto& g : node.gate) res_.push_back(g);
    int idx = node.original_idx;
    auto it = node_indices_.find(idx);
    if (it != node_indices_.end()) {
      remove_dag_opt_node(it->second);
    }
  }
}

/**
 * @brief For each node, move/place its two qubits onto an adjacent edge.
 * @return the nodes that could not be placed (caller backs their qubits out).
 *
 * Dispatches by the qubits' current placement state: both placed ->
 * mov_to_neighbors; one placed -> put_to_neighbors1; neither placed ->
 * put_to_neighbors2.
 */
std::vector<NADagNode> NADefaultRoute::mov_multi_nodes(
    const std::vector<NADagNode>& nodes) {
  pre_back(nodes);
  std::vector<NADagNode> remain;
  for (const auto& node : nodes) {
    const auto& qubits = node.qubits;
    const std::string& p1 = logical_to_op[qubits[0]];
    const std::string& p2 = logical_to_op[qubits[1]];
    if (!p1.empty() && !p2.empty()) {
      if (!mov_to_neighbors(p1, p2)) remain.push_back(node);
    } else if (!p1.empty() && p2.empty()) {
      if (!put_to_neighbors1(p1, qubits[1])) remain.push_back(node);
    } else if (p1.empty() && !p2.empty()) {
      if (!put_to_neighbors1(p2, qubits[0])) remain.push_back(node);
    } else {
      if (!put_to_neighbors2(qubits[0], qubits[1])) remain.push_back(node);
    }
  }
  return remain;
}

/**
 * @brief Emit a single-qubit node's gates into res_ and remove it from
 *        dag_opt_. No placement logic — the qubit is already (or assumed) in
 *        the operate area.
 */
void NADefaultRoute::execute_single_node(const NADagNode& node) {
  for (const auto& g : node.gate) res_.push_back(g);
  int idx = node.original_idx;
  auto it = node_indices_.find(idx);
  if (it != node_indices_.end()) {
    remove_dag_opt_node(it->second);
  }
}

/**
 * @brief Whether node nd2's gate list is a suffix of node nd1's gate list (same
 *        gate-name sequence). Used to decide if a single-qubit node's puts can
 *        be overlapped behind the previous node's execution.
 */
bool NADefaultRoute::overlap(int nd1, int nd2) const {
  const auto& gt1 = dag_[nd1].gate;
  const auto& gt2 = dag_[nd2].gate;
  if (gt1.size() < gt2.size()) return false;
  int l = 0;
  for (int i = static_cast<int>(gt1.size() - gt2.size());
       i < static_cast<int>(gt1.size()); ++i) {
    if (gt1[i]->name != gt2[l]->name) return false;
    ++l;
  }
  return true;
}

/**
 * @brief Merge a put operation onto qubit q into the trailing move ops on `res`:
 *        if a back-op on q sits adjacent to the end, cancel it out (the put
 *        undoes the back); otherwise append the put.
 *
 * @return the rewritten operation list.
 */
std::vector<std::shared_ptr<BaseOperation>> NADefaultRoute::add_put(
    std::vector<std::shared_ptr<BaseOperation>> res,
    std::shared_ptr<BaseOperation> opt) {
  int q = opt->targets[0];
  int i = static_cast<int>(res.size()) - 1;
  while (i >= 0) {
    if (!is_move(*res[i])) break;
    auto& t = res[i];
    if (t->operation_type == OperationType::MOVE && t->targets[0] == q) {
      auto mp_it = move_positions_.find(t.get());
      if (mp_it == move_positions_.end()) {
        --i;
        continue;
      }
      // If there is an adjacent back operation on the same qubit, cancel it out.
      const std::string& op = mp_it->second.first;
      const std::string& p = logical_to_op[q];
      op_occupied_.erase(p);
      op_occupied_.insert(op);
      op_to_logical[p] = -1;
      op_to_logical[op] = q;
      logical_to_op[q] = op;
      res.erase(res.begin() + i);
      return res;
    }
    --i;
  }
  res.push_back(opt);
  return res;
}

/**
 * @brief Reorder the last n put/move ops (res_tail) by their target position
 *        index `pos`, splicing them back into res_ so that puts land before the
 *        gates they prepare, and rewrite non-move gate targets along the way.
 *
 * @param pos   per-op target insertion index (Python-style, may be negative);
 * @param posq  per-op logical qubit appended to the gate targets list.
 *
 * This mirrors the Python adjust_pos: overlapping puts are reordered to keep
 * each gate's operands consistent with the rearranged move sequence.
 */
void NADefaultRoute::adjust_pos(const std::vector<int>& pos,
                         const std::vector<int>& posq) {
  if (pos.empty()) return;
  int n = static_cast<int>(pos.size());
  // res_tail mirrors Python's self.res[-n:] (the last n put/move operations).
  std::vector<std::shared_ptr<BaseOperation>> res_tail(res_.end() - n,
                                                       res_.end());
  res_.erase(res_.end() - n, res_.end());
  // res_ now mirrors Python's self.res[:-n].
  int total = static_cast<int>(res_.size());

  // Normalize Python-style indices (may be negative, counting from the end)
  // to non-negative subscripts.
  auto norm = [&](int idx) -> int {
    if (idx >= 0) return idx;
    return total + idx;
  };

  std::vector<std::shared_ptr<BaseOperation>> new_res;
  int pre = 0;
  // targets is initialized as a copy of the last non-move gate's targets in res_
  // (Python takes self.res[-1].targets.copy()).
  std::vector<int> targets;
  if (!res_.empty() && !is_move(*res_.back())) {
    targets = res_.back()->targets;
  }

  // Sort the (p, r, q) triples by pos in ascending order.
  std::vector<std::tuple<int, std::shared_ptr<BaseOperation>, int>> triples;
  triples.reserve(pos.size());
  for (int i = 0; i < n; ++i) {
    triples.emplace_back(pos[i], res_tail[i], posq[i]);
  }
  std::sort(triples.begin(), triples.end(),
            [](const auto& a, const auto& b) {
              return std::get<0>(a) < std::get<0>(b);
            });

  for (const auto& [p, r, q] : triples) {
    if (p == pre) {
      new_res = add_put(std::move(new_res), r);
      targets.push_back(q);
    } else {
      int pre_n = norm(pre);
      int p_n = norm(p);
      if (pre > 0) {
        for (int gi = pre_n; gi < p_n; ++gi) {
          if (!is_move(*res_[gi])) {
            res_[gi]->targets = targets;
          }
        }
      }
      if (p_n > pre_n) {
        new_res.insert(new_res.end(), res_.begin() + pre_n,
                       res_.begin() + p_n);
      }
      new_res = add_put(std::move(new_res), r);
      targets.push_back(q);
    }
    pre = p;
  }

  int pre_n = norm(pre);
  for (int gi = pre_n; gi < static_cast<int>(res_.size()); ++gi) {
    if (!is_move(*res_[gi])) {
      res_[gi]->targets = targets;
    }
  }
  new_res.insert(new_res.end(), res_.begin() + pre_n, res_.end());
  res_ = std::move(new_res);
}

/**
 * @brief Overlap pre-placement: for each single-qubit node in front_layer_
 *        whose gate list is a suffix of the previous node's (overlap()), put
 *        its qubit onto a free spot near the operate area so the puts run
 *        alongside the in-flight two-qubit gate, hiding shuttling latency.
 *
 * Nodes that qualify are removed from dag_opt_ and excluded from front_layer_;
 * the put sequence is then reordered via adjust_pos() to keep gate operands
 * consistent. Non-overlapping nodes stay in front_layer_ for normal scheduling.
 */
void NADefaultRoute::execute_single_node_opt() {
  std::vector<int> pos;
  std::vector<int> posq;
  std::vector<int> front_layer = front_layer_;  // copy
  std::vector<int> remaining;
  remaining.reserve(front_layer.size());
  for (int node : front_layer) {
    if (dag_[node].qubits.size() == 1) {
      if (has_pre_node_ && overlap(pre_node_idx_, node)) {
        int q = dag_[node].qubits[0];
        std::string p = find_pos(1);
        if (!p.empty()) {
          put(q, p);
          pos.push_back(-1 * static_cast<int>(dag_[node].gate.size()));
          posq.push_back(q);
          remove_dag_opt_node(node);
        } else {
          remaining.push_back(node);
        }
      } else {
        remaining.push_back(node);
      }
    } else {
      remaining.push_back(node);
    }
  }
  front_layer_ = std::move(remaining);
  adjust_pos(pos, posq);
}

/**
 * @brief Select which gate(s) to run this round from front_layer_.
 * @return (kind, nodes):
 *         kind == 1 -> the single-qubit node with the longest gate list;
 *         kind == 2 -> every two-qubit node in the front layer.
 *
 * @note Faithfully reproduces the Python quirk where the logical-qubit integer
 *       is compared against the position-string set, so the "common" overlap
 *       count is always 0 — single-qubit gates are always preferred, and
 *       two-qubit gates are only returned when no single-qubit gate exists.
 */
std::pair<int, std::vector<int>> NADefaultRoute::get_max_common() {
  // Note: in the Python impl op_occupied is a set of position strings while
  // multi_qubits / qubits[0] are logical-qubit integers, so their intersection
  // is always empty. This faithfully reproduces that behavior: comm is always
  // 0, single-qubit gates are always selected (the one with the longest gate
  // list), and two-qubit gates are only returned when no single-qubit gate
  // exists.
  std::unordered_set<int> multi_qubits;
  std::vector<int> multi_nodes;
  int comm = 0;
  int execute_node = -1;
  for (int node : front_layer_) {
    const auto& qubits = dag_[node].qubits;
    if (qubits.size() == 1) {
      if (comm > 1) continue;
      // Python: qubits[0] (int) in op_occupied (str) is always False, so this
      // neither skips nor sets comm to 1.
      if (execute_node != -1 &&
          static_cast<int>(dag_[execute_node].gate.size()) >=
              static_cast<int>(dag_[node].gate.size())) {
        continue;
      }
      execute_node = node;
    } else {
      for (int q : qubits) multi_qubits.insert(q);
      // Python: len(multi_qubits & op_occupied) is always 0.
      comm = std::max(comm, 0);
      multi_nodes.push_back(node);
    }
  }
  if (comm <= 1) {
    if (execute_node != -1) return {1, {execute_node}};
  }
  return {2, multi_nodes};
}

/**
 * @brief Mark a node as executed in dag_opt_: decrement each successor's
 *        in_degree and clear the node's gate/successors/qubits (in_degree set
 *        to -1) so it drops out of future front-layer lookups. The node is not
 *        erased (indices must stay stable).
 */
void NADefaultRoute::remove_dag_opt_node(int idx) {
  if (idx < 0 || idx >= static_cast<int>(dag_opt_.size())) return;
  NADagNode& node = dag_opt_[idx];
  // Decrement the in-degree of successor nodes.
  for (int succ : node.successors) {
    if (succ >= 0 && succ < static_cast<int>(dag_opt_.size())) {
      if (dag_opt_[succ].in_degree > 0) {
        dag_opt_[succ].in_degree -= 1;
      }
    }
  }
  node.gate.clear();
  node.successors.clear();
  node.qubits.clear();
  node.in_degree = -1;  // mark as removed
}

/**
 * @brief Final pass over res_: rewrite every logical qubit in each gate's
 *        targets to its current physical operate-area coordinate, and fill
 *        each MOVE op's arg_value with its (from, to) positions.
 *
 * Tracks a per-qubit position map (operator_list) updated as MOVEs are seen, so
 * every gate resolves to the coordinate its qubit occupied at that point in the
 * sequence. @throw std::runtime_error if a qubit has no mapping.
 */
void NADefaultRoute::finalize_gates(bool /*deep_copy_layout*/) {
  // operator_list: logical qubit -> current physical position string.
  // Mirrors Python's operator_list (execute_with_order uses a reference to
  // self.logical_to_storage, execute_with_opt uses a deepcopy). Here we copy
  // once and update incrementally per gate; both paths behave identically.
  std::unordered_map<int, std::string> operator_list = logical_to_storage;

  for (auto& gate : res_) {
    if (is_move(*gate)) {
      auto mp_it = move_positions_.find(gate.get());
      if (mp_it == move_positions_.end()) continue;
      const std::string& to_pos = mp_it->second.second;
      operator_list[gate->targets[0]] = to_pos;
      gate->arg_value = {static_cast<double>(pos_to_int(mp_it->second.first)),
                         static_cast<double>(pos_to_int(to_pos))};
    } else {
      std::vector<int> new_targets;
      new_targets.reserve(gate->targets.size());
      for (int q : gate->targets) {
        auto it = operator_list.find(q);
        if (it == operator_list.end()) {
          throw std::runtime_error("finalize: qubit " + std::to_string(q) +
                                   " has no physical mapping");
        }
        new_targets.push_back(pos_to_int(it->second));
      }
      gate->targets = std::move(new_targets);
    }
  }
}

/**
 * @brief In-order execution: walk the DAG node by node in topological order,
 *        running each single-qubit node directly and each two-qubit node
 *        through execute_multi_nodes, with no overlap optimization.
 *
 * @return {res_, {}} — the routed gate list with logical qubits rewritten to
 *         physical coordinates and MOVE arg_value populated by finalize_gates.
 *
 * Measurement gates are appended last. This is the simpler, stricter path; the
 * overlap-optimized variant is execute_with_opt().
 */
std::pair<std::vector<std::shared_ptr<BaseOperation>>,
          std::unordered_map<int, int>>
NADefaultRoute::execute_with_order() {
  get_init_mapping();

  for (const auto& node : dag_) {
    if (node.qubits.size() == 1) {
      execute_single_node(node);
    } else {
      execute_multi_nodes({node});
    }
  }

  for (auto& g : measure_) res_.push_back(g);

  finalize_gates(false);
  return {res_, {}};
}

/**
 * @brief Overlap-optimized execution: schedule gates in topological order while
 *        overlapping atom shuttling with gate execution, to cut total routing
 *        time vs. the strict in-order path (execute_with_order).
 *
 * @par Inputs (member state populated by prepare_data / get_rx_dag):
 *        gates_         the logical gate list to route;
 *        qpu_config_    QPU topology — operate_area, storage_area, coupler_map;
 *        dag_ / dag_opt_ the dependency graph and its optimization-tracking copy;
 *        logical_to_storage / logical_to_op / op_to_logical  qubit<->position
 *                       mapping tables maintained incrementally during the run.
 *
 * @return The routed gate list res_: every gate's logical qubits are rewritten
 *         to physical operate-area coordinates, and each MOVE op carries its
 *         (from, to) positions in arg_value.
 *
 * Key principle — walk the DAG one front_layer_ (in-degree == 0 nodes) at a time.
 * Each iteration:
 *   1. If the previous node was single-qubit, call execute_single_node_opt() to
 *      pre-place single-qubit gates whose gate list is a suffix of the previous
 *      node's; their put moves run alongside the in-flight two-qubit gate,
 *      hiding shuttling latency — this is the "overlap".
 *   2. Select this round's gate(s) via get_max_common() -> (kind, nodes):
 *        kind == 1: the single-qubit gate with the longest gate list;
 *        kind == 2: a group of two-qubit gates executed together.
 *   3. Run the chosen node(s), refresh front_layer_, and repeat until empty.
 * Measurement gates are appended last; finalize_gates() then resolves every
 * logical qubit to its physical coordinate before returning.
 */
std::vector<std::shared_ptr<BaseOperation>> NADefaultRoute::execute_with_opt() {
  get_init_mapping();

  front_layer_ = get_front_layer();
  int t = 0;
  while (!front_layer_.empty()) {
    // Step 1: pre-overlap single-qubit puts when the prior node was single-qubit.
    if (has_pre_node_ && dag_[pre_node_idx_].qubits.size() == 1) {
      execute_single_node_opt();
      front_layer_ = get_front_layer();
    }

    if (!front_layer_.empty()) {
      // Step 2: pick this round's gate(s): single (kind==1) or multi (kind==2).
      auto [i, node_list] = get_max_common();
      if (i == 1) {
        execute_single_node(dag_[node_list[0]]);
      } else {
        std::vector<NADagNode> nodes;
        nodes.reserve(node_list.size());
        for (int idx : node_list) nodes.push_back(dag_[idx]);
        execute_multi_nodes(nodes);
      }
    }

    // Step 3: refresh front_layer_ and advance.
    front_layer_ = get_front_layer();
    ++t;
  }

  for (auto& g : measure_) res_.push_back(g);

  finalize_gates(true);
  return res_;
}

// ===================== NAZAPRoute =====================

void NAZAPRoute::prepare_data(
    int qbit_num,
    const std::vector<std::shared_ptr<BaseOperation>>& gates,
    const NAQpuConfig& qpu_config) {
  qpu_config_ = qpu_config;
  ag_ = NAGraph{};
  edges_.clear();
  for (const auto& entry : qpu_config_.coupler_map) {
    const std::string& a = entry.second.first;
    const std::string& b = entry.second.second;
    if (!contains(qpu_config_.operate_area, a) ||
        !contains(qpu_config_.operate_area, b)) {
      continue;
    }
    ag_.add_edge(a, b);
    edges_.emplace_back(a, b);
  }
  ag_.build_shortest_length();

  gates_ = gates;
  qbit_num_ = qbit_num;
  if (static_cast<int>(qpu_config_.storage_area.size()) < qbit_num_) {
    throw std::runtime_error("not enough qubits, need " +
                             std::to_string(qbit_num_) + ", but only " +
                             std::to_string(qpu_config_.operate_area.size()));
  }
  gate_scheduling_list_.clear();
  qubit_scheduling_list_.clear();
  storage_area_oloc_.clear();
  operate_area_oloc_.clear();
  measure_.clear();
  res_.clear();
  movement_.clear();
}

std::vector<std::shared_ptr<BaseOperation>> NAZAPRoute::scheduling() {
  std::vector<std::shared_ptr<BaseOperation>> measure_op;
  const int na_ryd_limit = static_cast<int>(edges_.size());

  // per-logical-qubit available time index (initialized to 0)
  std::vector<int> list_qubit_time(gates_.size(), 0);
  // count of two-qubit gates scheduled per stage
  std::vector<int> two_qubit_gate_list(gates_.size(), 0);

  auto ensure_stage = [&](int tg) {
    while (static_cast<int>(gate_scheduling_list_.size()) <= tg) {
      gate_scheduling_list_.emplace_back();
      qubit_scheduling_list_.emplace_back();
    }
  };

  for (const auto& gate : gates_) {
    if (gate->name == "barrier" || gate->name == "measure") {
      if (gate->name == "measure") measure_op.push_back(gate);
      continue;
    }

    if (gate->targets.size() == 1) {
      int q = gate->targets[0];
      int tg = list_qubit_time[q];
      ensure_stage(tg);
      gate_scheduling_list_[tg].push_back(gate);
      if (std::find(qubit_scheduling_list_[tg].begin(),
                    qubit_scheduling_list_[tg].end(),
                    q) == qubit_scheduling_list_[tg].end()) {
        qubit_scheduling_list_[tg].push_back(q);
      }
      // single-qubit gate does not advance time (keeps same tg)
      list_qubit_time[q] = tg;
    } else {
      int q0 = gate->targets[0];
      int q1 = gate->targets[1];
      int tg = std::max(list_qubit_time[q0], list_qubit_time[q1]);
      while (true) {
        ensure_stage(tg);
        if (two_qubit_gate_list[tg] < na_ryd_limit) {
          gate_scheduling_list_[tg].push_back(gate);
          two_qubit_gate_list[tg] += 1;
          for (int qid : gate->targets) {
            if (std::find(qubit_scheduling_list_[tg].begin(),
                          qubit_scheduling_list_[tg].end(),
                          qid) == qubit_scheduling_list_[tg].end()) {
              qubit_scheduling_list_[tg].push_back(qid);
            }
          }
          ++tg;
          list_qubit_time[q0] = tg;
          list_qubit_time[q1] = tg;
          break;
        }
        ++tg;
      }
    }
  }

  int stage_num = static_cast<int>(gate_scheduling_list_.size());
  storage_area_oloc_.assign(stage_num + 1,
                            make_empty_oloc(qpu_config_.storage_area));
  operate_area_oloc_.assign(stage_num + 1,
                            make_empty_oloc(qpu_config_.operate_area));

  return measure_op;
}

int NAZAPRoute::get_steps(const std::string& posa,
                          const std::string& posb) const {
  int pre_id = pos_to_int(posa);
  int pre_row = pre_id / kGridCols;
  int pre_col = pre_id % kGridCols;
  int id = pos_to_int(posb);
  int row = id / kGridCols;
  int col = id % kGridCols;
  return std::abs(pre_row - row) + std::abs(pre_col - col);
}

int NAZAPRoute::get_cost(const StageMap& mapping) const {
  int cost = 0;
  for (size_t idx = 1; idx < mapping.size(); ++idx) {
    const auto& pre = mapping[idx - 1];
    const auto& cur = mapping[idx];
    for (int qid = 0; qid < qbit_num_; ++qid) {
      auto it_a = pre.find(qid);
      auto it_b = cur.find(qid);
      if (it_a != pre.end() && it_b != cur.end()) {
        cost += get_steps(it_a->second, it_b->second);
      }
    }
  }
  return cost;
}

int NAZAPRoute::get_affect_cost(const std::vector<int>& affect_qubit_id,
                                 int idx, const StageMap& mapping) const {
  int cost = 0;
  const auto& stage = mapping[idx];
  const auto& last_stage = mapping[idx + 1];
  const auto* pre_stage = (idx > 0) ? &mapping[idx - 1] : nullptr;
  for (int qid : affect_qubit_id) {
    auto it_s = stage.find(qid);
    auto it_l = last_stage.find(qid);
    if (it_s == stage.end() || it_l == last_stage.end()) continue;
    if (pre_stage != nullptr) {
      auto it_p = pre_stage->find(qid);
      if (it_p != pre_stage->end()) {
        cost += get_steps(it_p->second, it_s->second) +
                get_steps(it_s->second, it_l->second);
      }
    } else {
      cost += get_steps(it_s->second, it_l->second);
    }
  }
  return cost;
}

std::pair<std::string, std::string> NAZAPRoute::find_ryd_pos(int stage) {
  // Randomly sample edges until both endpoints are free at this stage.
  while (true) {
    std::uniform_int_distribution<int> dist(0, edges_.size() - 1);
    const auto& edge = edges_[dist(rng_)];
    if (operate_area_oloc_[stage][edge.first] == -1 &&
        operate_area_oloc_[stage][edge.second] == -1) {
      return edge;
    }
  }
}

std::string NAZAPRoute::find_pos(int stage) {
  while (true) {
    std::uniform_int_distribution<int> dist(
        0, qpu_config_.storage_area.size() - 1);
    std::string pos = qpu_config_.storage_area[dist(rng_)];
    if (storage_area_oloc_[stage][pos] == -1) {
      return pos;
    }
  }
}

void NAZAPRoute::get_init_mapping_and_placing(StageMap& mapping) {
  for (size_t idx = 0; idx < mapping.size(); ++idx) {
    auto& stage = mapping[idx];
    if (idx == 0) {
      // Initial stage: place all logical qubits in storage area, ranked by
      // readout error (lowest first), ties broken by position name.
      std::vector<std::pair<std::string, double>> err_list;
      for (const auto& [pos, err] : qpu_config_.readout_error) {
        if (contains(qpu_config_.storage_area, pos)) {
          err_list.emplace_back(pos, err);
        }
      }
      std::sort(err_list.begin(), err_list.end(),
                [](const auto& lhs, const auto& rhs) {
                  if (lhs.second != rhs.second) return lhs.second < rhs.second;
                  return lhs.first < rhs.first;
                });
      if (static_cast<int>(err_list.size()) > qbit_num_) {
        err_list.resize(qbit_num_);
      }
      for (int i = 0; i < static_cast<int>(err_list.size()); ++i) {
        stage[i] = err_list[i].first;
        storage_area_oloc_[idx][stage[i]] = i;
      }
    } else {
      const auto& pre = mapping[idx - 1];
      // First handle two-qubit gates of the previous stage.
      for (const auto& gate : gate_scheduling_list_[idx - 1]) {
        if (gate->targets.size() != 2) continue;
        int q0 = gate->targets[0];
        int q1 = gate->targets[1];
        const std::string& p0 = pre.at(q0);
        const std::string& p1 = pre.at(q1);
        bool q0_stor = contains(qpu_config_.storage_area, p0);
        bool q1_stor = contains(qpu_config_.storage_area, p1);
        bool q0_op = contains(qpu_config_.operate_area, p0);
        bool q1_op = contains(qpu_config_.operate_area, p1);

        auto place_pair = [&](int a, int b) {
          auto pos = find_ryd_pos(static_cast<int>(idx));
          stage[a] = pos.first;
          stage[b] = pos.second;
          operate_area_oloc_[idx][pos.first] = a;
          operate_area_oloc_[idx][pos.second] = b;
        };

        // Case: q0 in storage, q1 in operate
        if (q0_stor && q1_op) {
          const auto& nbrs = ag_.neighbors(p1);
          if (!nbrs.empty()) {
            const std::string& nbr = *nbrs.begin();
            if (operate_area_oloc_[idx][nbr] > -1) {
              place_pair(q0, q1);
            } else {
              stage[q0] = nbr;
              operate_area_oloc_[idx][nbr] = q0;
              stage[q1] = p1;
              operate_area_oloc_[idx][p1] = q1;
            }
          }
        }
        // Case: q0 in operate, q1 in storage
        if (q0_op && q1_stor) {
          const auto& nbrs = ag_.neighbors(p0);
          if (!nbrs.empty()) {
            const std::string& nbr = *nbrs.begin();
            if (operate_area_oloc_[idx][nbr] > -1) {
              place_pair(q0, q1);
            } else {
              stage[q1] = nbr;
              operate_area_oloc_[idx][nbr] = q1;
              stage[q0] = p0;
              operate_area_oloc_[idx][p0] = q0;
            }
          }
        }
        // Case: both in storage
        if (q0_stor && q1_stor) {
          place_pair(q0, q1);
        }
        // Case: both in operate
        if (q0_op && q1_op) {
          if (!ag_.is_adjacent(p0, p1)) {
            // not adjacent -> find a free pair
            place_pair(q0, q1);
          } else {
            stage[q0] = p0;
            operate_area_oloc_[idx][p0] = q0;
            stage[q1] = p1;
            operate_area_oloc_[idx][p1] = q1;
          }
        }
      }

      // Handle single-qubit gates whose position is still unset.
      for (const auto& gate : gate_scheduling_list_[idx - 1]) {
        if (gate->targets.size() != 1) continue;
        int q = gate->targets[0];
        if (stage.find(q) != stage.end()) continue;
        const std::string& prev = pre.at(q);
        if (contains(qpu_config_.operate_area, prev)) {
          std::string pos = find_pos(static_cast<int>(idx));
          stage[q] = pos;
          storage_area_oloc_[idx][pos] = q;
        } else {
          stage[q] = prev;
          storage_area_oloc_[idx][prev] = q;
        }
      }

      // For qubits not involved in this stage, assign storage.
      for (int qid = 0; qid < qbit_num_; ++qid) {
        if (stage.find(qid) != stage.end()) continue;
        const std::string& prev = pre.at(qid);
        if (contains(qpu_config_.storage_area, prev)) {
          stage[qid] = prev;
          storage_area_oloc_[idx][prev] = qid;
        } else {
          std::string pos = find_pos(static_cast<int>(idx));
          stage[qid] = pos;
          storage_area_oloc_[idx][pos] = qid;
        }
      }
    }
  }
}

int NAZAPRoute::update_mapping(StageMap& mapping) {
  movement_.clear();
  int stage_num = static_cast<int>(gate_scheduling_list_.size());
  if (stage_num <= 0) return 0;

  std::uniform_int_distribution<int> stage_dist(0, stage_num - 1);
  int idx = stage_dist(rng_);
  auto& stage = mapping[idx];
  std::uniform_int_distribution<int> qid_dist(0, qbit_num_ - 1);
  int qid = qid_dist(rng_);

  int current_cost = 0;
  int new_cost = 0;
  std::vector<int> affect_qubit_id = {qid};

  if (contains(qpu_config_.operate_area, stage.at(qid))) {
    std::uniform_int_distribution<int> up_dist(0, 5);
    int up_id = up_dist(rng_);
    if (up_id == 0) {
      // Swap with a neighbor operate position.
      const auto& nbrs = ag_.neighbors(stage.at(qid));
      if (nbrs.empty()) return 0;
      std::string nbr = *nbrs.begin();
      int neighbor_id = operate_area_oloc_[idx][nbr];
      affect_qubit_id.push_back(neighbor_id);
      current_cost = get_affect_cost(affect_qubit_id, idx, mapping);
      movement_.emplace_back(idx, qid, stage.at(qid));
      movement_.emplace_back(idx, neighbor_id, nbr);
      stage[neighbor_id] = stage.at(qid);
      stage[qid] = nbr;
      new_cost = get_affect_cost(affect_qubit_id, idx, mapping);
    } else {
      // Swap with another Rydberg pair in operate area.
      std::uniform_int_distribution<int> edge_dist(0, edges_.size() - 1);
      auto edge = edges_[edge_dist(rng_)];
      const std::string& node_a = edge.first;
      const std::string& node_b = edge.second;
      if (operate_area_oloc_[idx][node_a] == -1 &&
          operate_area_oloc_[idx][node_b] == -1) {
        const auto& nbrs = ag_.neighbors(stage.at(qid));
        if (nbrs.empty()) return 0;
        std::string nbr = *nbrs.begin();
        int neighbor_id = operate_area_oloc_[idx][nbr];
        affect_qubit_id.push_back(neighbor_id);
        current_cost = get_affect_cost(affect_qubit_id, idx, mapping);
        movement_.emplace_back(idx, qid, stage.at(qid));
        movement_.emplace_back(idx, neighbor_id, nbr);
        stage[qid] = node_a;
        stage[neighbor_id] = node_b;
        new_cost = get_affect_cost(affect_qubit_id, idx, mapping);
      } else {
        const auto& nbrs = ag_.neighbors(stage.at(qid));
        if (nbrs.empty()) return 0;
        std::string nbr = *nbrs.begin();
        int neighbor_id = operate_area_oloc_[idx][nbr];
        affect_qubit_id.push_back(neighbor_id);
        int swap_id_a = operate_area_oloc_[idx][node_a];
        int swap_id_b = operate_area_oloc_[idx][node_b];
        affect_qubit_id.push_back(swap_id_a);
        affect_qubit_id.push_back(swap_id_b);
        current_cost = get_affect_cost(affect_qubit_id, idx, mapping);
        movement_.emplace_back(idx, qid, stage.at(qid));
        movement_.emplace_back(idx, neighbor_id, nbr);
        movement_.emplace_back(idx, swap_id_a, node_a);
        movement_.emplace_back(idx, swap_id_b, node_b);
        stage[swap_id_a] = stage.at(qid);
        stage[swap_id_b] = stage.at(neighbor_id);
        stage[qid] = node_a;
        stage[neighbor_id] = node_b;
        new_cost = get_affect_cost(affect_qubit_id, idx, mapping);
      }
    }
  } else {
    // Qubit is in storage area: swap/move to a random storage position.
    std::uniform_int_distribution<int> s_dist(
        0, qpu_config_.storage_area.size() - 1);
    std::string up_local = qpu_config_.storage_area[s_dist(rng_)];
    if (storage_area_oloc_[idx][up_local] >= 0) {
      int tmp_id = storage_area_oloc_[idx][up_local];
      affect_qubit_id.push_back(tmp_id);
      current_cost = get_affect_cost(affect_qubit_id, idx, mapping);
      movement_.emplace_back(idx, qid, stage.at(qid));
      movement_.emplace_back(idx, tmp_id, up_local);
      stage[tmp_id] = stage.at(qid);
      stage[qid] = up_local;
      new_cost = get_affect_cost(affect_qubit_id, idx, mapping);
    } else {
      current_cost = get_affect_cost(affect_qubit_id, idx, mapping);
      movement_.emplace_back(idx, qid, stage.at(qid));
      stage[qid] = up_local;
      new_cost = get_affect_cost(affect_qubit_id, idx, mapping);
    }
  }
  return new_cost - current_cost;
}

void NAZAPRoute::recover(StageMap& mapping) {
  if (movement_.empty()) return;
  int stage_id = std::get<0>(movement_[0]);
  auto& stage = mapping[stage_id];
  for (const auto& mv : movement_) {
    int qid = std::get<1>(mv);
    std::string pos = std::get<2>(mv);
    stage[qid] = pos;
  }
}

void NAZAPRoute::update_storage_and_operate_area_oloc(const StageMap& mapping) {
  int stage_num = static_cast<int>(gate_scheduling_list_.size());
  storage_area_oloc_.assign(stage_num + 1,
                            make_empty_oloc(qpu_config_.storage_area));
  operate_area_oloc_.assign(stage_num + 1,
                            make_empty_oloc(qpu_config_.operate_area));
  for (size_t idx = 0; idx < mapping.size(); ++idx) {
    for (const auto& [qid, value] : mapping[idx]) {
      if (contains(qpu_config_.storage_area, value)) {
        storage_area_oloc_[idx][value] = qid;
      }
      if (contains(qpu_config_.operate_area, value)) {
        operate_area_oloc_[idx][value] = qid;
      }
    }
  }
}

NAZAPRoute::StageMap NAZAPRoute::validate_mapping(const StageMap& mapping) const {
  StageMap new_mapping = mapping;
  for (size_t stage_id = 1; stage_id < new_mapping.size(); ++stage_id) {
    auto& stage = new_mapping[stage_id];
    const auto& pre = new_mapping[stage_id - 1];
    for (int qid = 0; qid < qbit_num_; ++qid) {
      auto it_s = stage.find(qid);
      auto it_p = pre.find(qid);
      if (it_s == stage.end() || it_p == pre.end()) continue;
      if (contains(qpu_config_.storage_area, it_s->second) &&
          contains(qpu_config_.storage_area, it_p->second)) {
        stage[qid] = it_p->second;
      }
    }
  }
  return new_mapping;
}

NAZAPRoute::StageMap NAZAPRoute::sa_mapping_and_placing() {
  // mapping[stage][qid] = position string.
  StageMap mapping(gate_scheduling_list_.size() + 1);
  get_init_mapping_and_placing(mapping);
  int cur_cost = get_cost(mapping);
  int best_cost = cur_cost;
  StageMap best_mapping = mapping;

  const double alpha = 0.98;
  const double t_min = 1.0;
  double t_init = 100.0;
  const int markovlen = 200;

  std::uniform_real_distribution<double> uniform(0.0, 1.0);
  double t = t_init;
  while (t > t_min) {
    for (int i = 0; i < markovlen; ++i) {
      int delta_cost = update_mapping(mapping);
      if (delta_cost <= 0) {
        cur_cost += delta_cost;
        update_storage_and_operate_area_oloc(mapping);
        if (cur_cost < best_cost) {
          best_cost = cur_cost;
          best_mapping = mapping;
        }
      } else {
        double accept_prob = std::exp(-delta_cost * 2.0);
        if (uniform(rng_) < accept_prob) {
          cur_cost += delta_cost;
          update_storage_and_operate_area_oloc(mapping);
        } else {
          recover(mapping);
        }
      }
    }
    t *= alpha;
  }
  return validate_mapping(best_mapping);
}

void NAZAPRoute::routing_asap(const StageMap& mapping) {
  for (size_t stage_id = 1; stage_id < mapping.size(); ++stage_id) {
    const auto& pre = mapping[stage_id - 1];
    const auto& stage = mapping[stage_id];
    for (const auto& [qid, value] : stage) {
      auto it = pre.find(qid);
      if (it == pre.end()) continue;
      if (value != it->second) {
        auto move_op = std::make_shared<Move>(
            std::vector<int>{qid},
            std::vector<double>{static_cast<double>(pos_to_int(it->second)),
                                static_cast<double>(pos_to_int(value))},
            OperationType::MOVE);
        res_.push_back(move_op);
      }
    }
    for (const auto& gate : gate_scheduling_list_[stage_id - 1]) {
      // Rewrite targets to physical coords from this stage.
      std::vector<int> new_targets;
      new_targets.reserve(gate->targets.size());
      for (int qid : gate->targets) {
        auto it = stage.find(qid);
        if (it == stage.end()) {
          throw std::runtime_error("routing_asap: qubit " +
                                   std::to_string(qid) +
                                   " has no stage mapping");
        }
        new_targets.push_back(pos_to_int(it->second));
      }
      gate->targets = std::move(new_targets);
      res_.push_back(gate);
    }
  }
  // Update measurement targets to the final physical positions.
  for (auto& m : measure_) {
    int qid = m->targets[0];
    auto it = mapping.back().find(qid);
    if (it != mapping.back().end()) {
      m->targets = {pos_to_int(it->second)};
    }
  }
  for (auto& m : measure_) res_.push_back(m);
}

std::pair<std::vector<std::shared_ptr<BaseOperation>>,
          std::unordered_map<int, int>>
NAZAPRoute::execute_with_order() {
  measure_ = scheduling();
  StageMap mapping = sa_mapping_and_placing();
  routing_asap(mapping);
  return {res_, {}};
}

// ===================== na_mapping (unified entry) =====================

std::vector<std::shared_ptr<BaseOperation>> na_mapping(
    const std::vector<std::shared_ptr<BaseOperation>>& gates_list,
    const NAQpuConfig& qpu_config, int qbit_num, bool na_support_move,
    const std::string& na_mapping_type, bool optimize) {
  std::unique_ptr<NARoute> router;

  if (na_support_move) {
    // Case-insensitive: "default"/"DEFAULT"/"Default" -> default route,
    // "zap"/"ZAP"/"Zap" -> ZAP route.
    std::string type_key = to_lower(na_mapping_type);
    if (type_key == "default") {
      router = std::make_unique<NADefaultRoute>();
    } else if (type_key == "zap") {
      router = std::make_unique<NAZAPRoute>();
    } else {
      throw std::invalid_argument(
          "na_mapping_type '" + na_mapping_type +
          "' is not supported by the C++ backend; only 'default' and 'ZAP' "
          "are available");
    }
  } else {
    router = std::make_unique<NASingleRoute>();
  }

  router->prepare_data(qbit_num, gates_list, qpu_config);
  if (optimize) {
    return router->execute_with_opt();
  }
  auto [res, layout] = router->execute_with_order();
  (void)layout;
  return res;
}

}  // namespace qcos
