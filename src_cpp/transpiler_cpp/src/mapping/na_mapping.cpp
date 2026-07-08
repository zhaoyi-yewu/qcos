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
#include <cstddef>
#include <queue>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace qcos {

namespace {

/// 位置分隔符（"\0" 不可出现在位置名中，保证 key 解析无歧义）
constexpr char kEdgeSep = '\0';

/// 将位置字符串（如 "P27"、"S100"）去除首字母后转为整数
int pos_to_int(const std::string& pos) {
  if (pos.empty()) {
    throw std::invalid_argument("invalid position: empty string");
  }
  return std::stoi(pos.substr(1));
}

/// 判断字符串是否在 vector 中
bool contains(const std::vector<std::string>& vec, const std::string& v) {
  return std::find(vec.begin(), vec.end(), v) != vec.end();
}

/// 逻辑门是否为 Move
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

void NAGraph::build_shortest_length() {
  // 对每个有邻居的节点执行 BFS，计算到其它节点的最短路径距离
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

  // 选取 storage_area 中读出错误率最小的 qbit_num 个位置
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

// ===================== NARoute =====================

std::pair<std::string, std::string> NARoute::sorted_edge(const std::string& a,
                                                         const std::string& b) {
  return a <= b ? std::make_pair(a, b) : std::make_pair(b, a);
}

std::string NARoute::edge_key(const std::string& a, const std::string& b) {
  auto pr = sorted_edge(a, b);
  return pr.first + std::string(1, kEdgeSep) + pr.second;
}

std::pair<std::string, std::string> NARoute::parse_edge_key(
    const std::string& key) {
  auto pos = key.find(kEdgeSep);
  if (pos == std::string::npos) {
    return {key, ""};
  }
  return {key.substr(0, pos), key.substr(pos + 1)};
}

std::shared_ptr<BaseOperation> NARoute::make_move(int q,
                                                  const std::string& from,
                                                  const std::string& to) {
  auto op = std::make_shared<Move>(std::vector<int>{q},
                                   std::vector<double>{0.0, 0.0},
                                   OperationType::MOVE);
  move_positions_[op.get()] = {from, to};
  return op;
}

void NARoute::prepare_data(
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

std::tuple<std::vector<NADagNode>,
           std::vector<std::shared_ptr<BaseOperation>>,
           std::unordered_map<int, int>>
NARoute::get_rx_dag() {
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
          // 合并：将当前门加入前驱节点的门列表
          dg[prev_node_idx].gate.push_back(gate);
        } else {
          NADagNode node;
          node.gate = {gate};
          node.qubits = gate->targets;
          node.type = "single";
          node.original_idx = idx;
          node.in_degree = 1;  // 有一条来自 prev 的入边
          int node_idx = static_cast<int>(dg.size());
          // 注意：push_back 可能引发 dg 重分配，必须在此之后通过
          // dg[prev_node_idx] 访问前驱节点，避免悬垂引用
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

      // 注意：node 已 move 进 dg，后续对入边的修改需通过 dg[node_idx] 进行
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

void NARoute::get_init_mapping() {
  auto [dg, measure, node_indices] = get_rx_dag();
  dag_ = std::move(dg);
  measure_ = std::move(measure);
  node_indices_ = std::move(node_indices);

  has_pre_node_ = false;
  pre_node_idx_ = -1;
  dag_opt_ = dag_;  // 深拷贝用于节点删除与可执行节点查找

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

std::vector<int> NARoute::get_front_layer() const {
  std::vector<int> front_layer;
  for (int i = 0; i < static_cast<int>(dag_opt_.size()); ++i) {
    if (dag_opt_[i].in_degree == 0 && !dag_opt_[i].gate.empty()) {
      front_layer.push_back(i);
    }
  }
  return front_layer;
}

std::string NARoute::find_pos(int dis) const {
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

void NARoute::back(const std::string& o) {
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

void NARoute::put(int q, const std::string& o) {
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

void NARoute::mov(const std::string& o1, const std::string& o2) {
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

void NARoute::pre_back(const std::vector<NADagNode>& nodes) {
  std::unordered_set<int> all_q;
  for (const auto& node : nodes) {
    for (int q : node.qubits) all_q.insert(q);
  }
  // 拷贝当前已占用位置，避免在迭代中修改
  std::vector<std::string> ohas(op_occupied_.begin(), op_occupied_.end());
  for (const auto& o : ohas) {
    int logical = op_to_logical[o];
    if (all_q.find(logical) == all_q.end()) back(o);
  }
}

std::string NARoute::get_empty_neighbor(const std::string& p) const {
  std::unordered_set<std::string> n = ag_.neighbors(p);
  // 减去与 op_occupied_ 的交集
  for (const auto& o : op_occupied_) n.erase(o);
  if (n.empty()) return "";
  return *n.begin();
}

std::string NARoute::get_unlocked_neighbor(const std::string& p) const {
  for (const auto& nxt : ag_.neighbors(p)) {
    if (locked_.find(nxt) == locked_.end()) return nxt;
  }
  return "";
}

bool NARoute::mov_to_neighbors(const std::string& p1,
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

bool NARoute::put_to_neighbors1(const std::string& p1, int q) {
  std::string d = get_empty_neighbor(p1);
  if (d.empty()) return false;
  put(q, d);
  locked_.insert(p1);
  locked_.insert(d);
  return true;
}

bool NARoute::put_to_neighbors2(int q1, int q2) {
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

void NARoute::execute_multi_nodes(const std::vector<NADagNode>& nodes) {
  locked_.clear();
  std::vector<NADagNode> remain = mov_multi_nodes(nodes);
  for (const auto& node : remain) {
    for (int q : node.qubits) {
      const auto& op = logical_to_op[q];
      if (!op.empty()) back(op);
    }
  }
  for (const auto& node : nodes) {
    // 判断 node 是否在 remain 中（通过 original_idx 比较）
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
    // pre_node 记录当前节点对应 dag_ 中的索引（与 dag_opt_ 对齐）
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

std::vector<NADagNode> NARoute::mov_multi_nodes(
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

void NARoute::execute_single_node(const NADagNode& node) {
  for (const auto& g : node.gate) res_.push_back(g);
  int idx = node.original_idx;
  auto it = node_indices_.find(idx);
  if (it != node_indices_.end()) {
    remove_dag_opt_node(it->second);
  }
}

bool NARoute::overlap(int nd1, int nd2) const {
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

std::vector<std::shared_ptr<BaseOperation>> NARoute::add_put(
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
      // 若有直接相邻的 back 操作，且作用在同一比特上，可消除
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

void NARoute::adjust_pos(const std::vector<int>& pos,
                         const std::vector<int>& posq) {
  if (pos.empty()) return;
  int n = static_cast<int>(pos.size());
  // res_tail 对应 Python 中 self.res[-n:]（末尾 n 个 put/move 操作）
  std::vector<std::shared_ptr<BaseOperation>> res_tail(res_.end() - n,
                                                       res_.end());
  res_.erase(res_.end() - n, res_.end());
  // 此时 res_ 对应 Python 中 self.res[:-n]
  int total = static_cast<int>(res_.size());

  // 将 Python 的索引（可为负，表示从末尾倒数）归一化为非负下标
  auto norm = [&](int idx) -> int {
    if (idx >= 0) return idx;
    return total + idx;
  };

  std::vector<std::shared_ptr<BaseOperation>> new_res;
  int pre = 0;
  // targets 初始为 res_ 最后一个非 move 门的 targets 拷贝
  // （Python 中取 self.res[-1].targets.copy()）
  std::vector<int> targets;
  if (!res_.empty() && !is_move(*res_.back())) {
    targets = res_.back()->targets;
  }

  // 按 pos 升序排序 (p, r, q) 三元组
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

void NARoute::execute_single_node_opt() {
  std::vector<int> pos;
  std::vector<int> posq;
  std::vector<int> front_layer = front_layer_;  // 拷贝
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

std::pair<int, std::vector<int>> NARoute::get_max_common() {
  // 注意：Python 实现中 op_occupied 为位置字符串集合，而 multi_qubits /
  // qubits[0] 为逻辑比特整数，二者求交集恒为空集。这里忠实复刻该行为：
  // comm 始终为 0，单比特门总会被选中（取门列表最长者），仅当不存在单
  // 比特门时才返回两比特门集合。
  std::unordered_set<int> multi_qubits;
  std::vector<int> multi_nodes;
  int comm = 0;
  int execute_node = -1;
  for (int node : front_layer_) {
    const auto& qubits = dag_[node].qubits;
    if (qubits.size() == 1) {
      if (comm > 1) continue;
      // Python: qubits[0] (int) in op_occupied (str) 恒为 False，
      // 因此此处不会跳过、也不会将 comm 置为 1
      if (execute_node != -1 &&
          static_cast<int>(dag_[execute_node].gate.size()) >=
              static_cast<int>(dag_[node].gate.size())) {
        continue;
      }
      execute_node = node;
    } else {
      for (int q : qubits) multi_qubits.insert(q);
      // Python: len(multi_qubits & op_occupied) 恒为 0
      comm = std::max(comm, 0);
      multi_nodes.push_back(node);
    }
  }
  if (comm <= 1) {
    if (execute_node != -1) return {1, {execute_node}};
  }
  return {2, multi_nodes};
}

void NARoute::remove_dag_opt_node(int idx) {
  if (idx < 0 || idx >= static_cast<int>(dag_opt_.size())) return;
  NADagNode& node = dag_opt_[idx];
  // 将后继节点入度减 1
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
  node.in_degree = -1;  // 标记为已移除
}

void NARoute::finalize_gates(bool /*deep_copy_layout*/) {
  // operator_list: 逻辑比特 -> 当前所在物理位置字符串
  // 对应 Python 的 operator_list（execute_with_order 使用 self.logical_to_storage
  // 的引用、execute_with_opt 使用 deepcopy）。这里统一拷贝一份并按门顺序增量
  // 更新，二者行为一致。
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

std::pair<std::vector<std::shared_ptr<BaseOperation>>,
          std::unordered_map<int, int>>
NARoute::execute_with_order() {
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

std::vector<std::shared_ptr<BaseOperation>> NARoute::execute_with_opt() {
  get_init_mapping();

  front_layer_ = get_front_layer();
  int t = 0;
  while (!front_layer_.empty()) {
    if (has_pre_node_ && dag_[pre_node_idx_].qubits.size() == 1) {
      execute_single_node_opt();
      front_layer_ = get_front_layer();
    }

    if (!front_layer_.empty()) {
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

    front_layer_ = get_front_layer();
    ++t;
  }

  for (auto& g : measure_) res_.push_back(g);

  finalize_gates(true);
  return res_;
}

}  // namespace qcos
