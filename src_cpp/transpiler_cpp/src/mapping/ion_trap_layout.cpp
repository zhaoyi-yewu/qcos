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

#include "mapping/ion_trap_layout.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <unordered_map>

#include "mapping/mapping_utils.h"

namespace qcos {

int IonTrapLayout::count_physical_qubits(
    const std::vector<std::pair<int, int>>& coupling_list) {
  int max_id = -1;
  for (const auto& edge : coupling_list) {
    max_id = std::max(max_id, std::max(edge.first, edge.second));
  }
  return max_id + 1;
}

std::unordered_map<size_t, double> IonTrapLayout::build_fidelity_lookup(
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_physical) {
  std::unordered_map<size_t, double> lookup;
  lookup.reserve(coupling_list.size());
  if (edge_fidelities.empty()) return lookup;
  for (size_t i = 0; i < coupling_list.size(); ++i) {
    if (edge_fidelities[i] > 0.0) {
      // key = from * num_physical + to，行主序编码物理比特对
      size_t key = static_cast<size_t>(coupling_list[i].first) * num_physical +
                   coupling_list[i].second;
      lookup[key] = edge_fidelities[i];
    }
  }
  return lookup;
}

std::vector<TwoQubitPair> IonTrapLayout::extract_two_qubit_pairs(
    const std::vector<GateOperation>& gates_list) {
  std::map<std::pair<int, int>, int> freq;
  for (const auto& gate : gates_list) {
    if (gate.targets.size() != 2) continue;
    if (gate.operation_type != OperationType::DOUBLE_QUBIT_OPERATION) continue;
    freq[{gate.targets[0], gate.targets[1]}]++;
  }

  std::vector<TwoQubitPair> two_qubit_pairs;
  two_qubit_pairs.reserve(freq.size());
  for (const auto& [key, count] : freq) {
    two_qubit_pairs.push_back({key.first, key.second, count});
  }
  return two_qubit_pairs;
}

long long IonTrapLayout::count_permutations(int num_physical,
                                            int num_logical) {
  long long count = 1;
  for (int i = 0; i < num_logical; ++i) {
    // 乘之前预判溢出，避免溢出
    if (count > std::numeric_limits<long long>::max() / (num_physical - i)) {
      return std::numeric_limits<long long>::max();
    }
    count *= (num_physical - i);
  }
  return count;
}

IonTrapLayout::IonTrapLayout(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities,
    const std::vector<double>& single_qubit_fidelities, int num_logical)
    : single_qubit_fidelities_(single_qubit_fidelities),
      num_logical_(num_logical),
      num_physical_(count_physical_qubits(coupling_list)) {
  two_qubit_pairs_ = extract_two_qubit_pairs(gates_list);
  two_qubit_fidelities_ =
      build_fidelity_lookup(coupling_list, edge_fidelities, num_physical_);
}

std::vector<int> IonTrapLayout::solve() const {
  // 无双比特保真度数据时，退化为单比特保真度优化
  if (two_qubit_fidelities_.empty()) {
    if (single_qubit_fidelities_.empty()) {
      std::vector<int> identity(num_logical_);
      for (int i = 0; i < num_logical_; ++i) identity[i] = i;
      return identity;
    }
    std::set<int> used;
    return select_best_single_qubits(single_qubit_fidelities_, used,
                                     num_logical_);
  }

  // 无两比特门时，按单比特保真度选最优物理比特
  if (two_qubit_pairs_.empty()) {
    if (single_qubit_fidelities_.empty()) {
      std::vector<int> identity(num_logical_);
      for (int i = 0; i < num_logical_; ++i) identity[i] = i;
      return identity;
    }
    std::set<int> used;
    return select_best_single_qubits(single_qubit_fidelities_, used,
                                     num_logical_);
  }

  // 按排列数选择策略
  long long perm_count = count_permutations(num_physical_, num_logical_);
  if (perm_count <= kMaxBruteForcePermutations) {
    return brute_force_optimal();
  }
  return local_search(greedy_initial());
}

double IonTrapLayout::compute_score(const std::vector<int>& placement) const {
  double score = 0.0;

  for (const auto& pair : two_qubit_pairs_) {
    int p_ctrl = placement[pair.control];
    int p_targ = placement[pair.target];
    size_t key = static_cast<size_t>(p_ctrl) * num_physical_ + p_targ;
    auto it = two_qubit_fidelities_.find(key);
    // 查不到边或保真度为0 -> 映射不可行，返回-inf使该排列永不被选
    if (it == two_qubit_fidelities_.end() || it->second <= 0.0) {
      return -std::numeric_limits<double>::infinity();
    }
    // log域累加，count越大该对比特权重越大
    score += pair.count * std::log(it->second);
  }

  if (!single_qubit_fidelities_.empty()) {
    // f == 0 视为保真度数据缺失，跳过以避免 log(0)
    for (int i = 0; i < num_logical_; ++i) {
      double f = single_qubit_fidelities_[placement[i]];
      if (f > 0.0) {
        score += std::log(f);
      }
    }
  }

  return score;
}

void IonTrapLayout::enumerate_permutations(
    std::vector<int>& placement, int depth, double& best_score,
    std::vector<int>& best_mapping) const {
  if (depth == num_logical_) {
    double score = compute_score(placement);
    if (score > best_score) {
      best_score = score;
      best_mapping.assign(placement.begin(), placement.begin() + num_logical_);
    }
    return;
  }
  // 从所有物理比特中选，不只是前num_logical_个，否则漏掉高ID比特
  for (int i = depth; i < num_physical_; ++i) {
    std::swap(placement[depth], placement[i]);
    enumerate_permutations(placement, depth + 1, best_score, best_mapping);
    // swap回去，恢复状态供下一次尝试
    std::swap(placement[depth], placement[i]);
  }
}

std::vector<int> IonTrapLayout::brute_force_optimal() const {
  std::vector<int> placement(num_physical_);
  for (int i = 0; i < num_physical_; ++i) placement[i] = i;

  double best_score = -std::numeric_limits<double>::infinity();
  std::vector<int> best_mapping(num_logical_);

  enumerate_permutations(placement, 0, best_score, best_mapping);

  // 全部排列都不可行时回退恒等映射
  if (best_score == -std::numeric_limits<double>::infinity()) {
    for (int i = 0; i < num_logical_; ++i) best_mapping[i] = i;
  }

  return best_mapping;
}

int IonTrapLayout::find_best_partner(int fixed_physical,
                                     const std::vector<bool>& used) const {
  double best_rel = -1.0;
  int best_partner = -1;
  for (int p = 0; p < num_physical_; ++p) {
    if (p == fixed_physical || used[p]) continue;
    size_t key = static_cast<size_t>(fixed_physical) * num_physical_ + p;
    auto it = two_qubit_fidelities_.find(key);
    if (it != two_qubit_fidelities_.end() && it->second > best_rel) {
      best_rel = it->second;
      best_partner = p;
    }
  }
  return best_partner;
}

std::pair<int, int> IonTrapLayout::find_best_available_pair(
    const std::vector<bool>& used) const {
  double best_rel = -1.0;
  int best_p1 = -1, best_p2 = -1;
  for (int p1 = 0; p1 < num_physical_; ++p1) {
    if (used[p1]) continue;
    for (int p2 = 0; p2 < num_physical_; ++p2) {
      if (p1 == p2 || used[p2]) continue;
      size_t key = static_cast<size_t>(p1) * num_physical_ + p2;
      auto it = two_qubit_fidelities_.find(key);
      if (it != two_qubit_fidelities_.end() && it->second > best_rel) {
        best_rel = it->second;
        best_p1 = p1;
        best_p2 = p2;
      }
    }
  }
  return {best_p1, best_p2};
}

void IonTrapLayout::assign_any_available(std::vector<int>& placement,
                                         std::vector<bool>& used,
                                         int logical) {
  for (int p = 0; p < static_cast<int>(used.size()); ++p) {
    if (!used[p]) {
      placement[logical] = p;
      used[p] = true;
      return;
    }
  }
  // 所有物理比特已耗尽，正常不应触发
  throw std::runtime_error(
      "assign_any_available: no available physical qubit for logical qubit " +
      std::to_string(logical));
}

void IonTrapLayout::fill_remaining_qubits(std::vector<int>& placement,
                                          std::vector<bool>& used) const {
  if (!single_qubit_fidelities_.empty()) {
    std::vector<std::pair<double, int>> available;
    for (int p = 0; p < num_physical_; ++p) {
      if (!used[p]) {
        available.emplace_back(single_qubit_fidelities_[p], p);
      }
    }
    // 按单比特保真度降序排序，最好的在前
    std::sort(available.begin(), available.end(), std::greater<>());
    // avail_idx是游标，逐个分配保真度最高的可用物理比特
    int avail_idx = 0;
    for (int i = 0; i < num_logical_; ++i) {
      if (placement[i] == -1) {
        if (avail_idx < static_cast<int>(available.size())) {
          placement[i] = available[avail_idx].second;
          used[available[avail_idx].second] = true;
          ++avail_idx;
        } else {
          assign_any_available(placement, used, i);
        }
      }
    }
  } else {
    for (int i = 0; i < num_logical_; ++i) {
      if (placement[i] == -1) {
        assign_any_available(placement, used, i);
      }
    }
  }
}

std::vector<int> IonTrapLayout::greedy_initial() const {
  std::vector<int> placement(num_logical_, -1);
  std::vector<bool> used(num_physical_, false);

  // 第一步：按频率降序排列
  std::vector<TwoQubitPair> sorted = two_qubit_pairs_;
  std::sort(sorted.begin(), sorted.end(),
            [](const TwoQubitPair& a, const TwoQubitPair& b) {
              return a.count > b.count;
            });

  // 第二步：贪心放置每个门对
  for (const auto& pair : sorted) {
    int control = pair.control;
    int target = pair.target;
    bool control_placed = (placement[control] != -1);
    bool target_placed = (placement[target] != -1);

    if (control_placed && target_placed) continue;

    // 放了一个比特，为另一个比特找最好的位置
    if (control_placed) {
      int best = find_best_partner(placement[control], used);
      if (best >= 0) {
        placement[target] = best;
        used[best] = true;
      } else {
        // 全连通不会走到这里
        assign_any_available(placement, used, target);
      }
    } else if (target_placed) {
      int best = find_best_partner(placement[target], used);
      if (best >= 0) {
        placement[control] = best;
        used[best] = true;
      } else {
        assign_any_available(placement, used, control);
      }
    } else {
      // 两个都未分配：在可用物理比特中找最优对
      auto [p1, p2] = find_best_available_pair(used);
      if (p1 >= 0) {
        placement[control] = p1;
        placement[target] = p2;
        used[p1] = true;
        used[p2] = true;
      } else {
        // 全连接时不会走到这里
        assign_any_available(placement, used, control);
        assign_any_available(placement, used, target);
      }
    }
  }

  // 第三步：分配剩余未放置的逻辑比特
  fill_remaining_qubits(placement, used);

  return placement;
}

std::vector<int> IonTrapLayout::local_search(
    std::vector<int> placement) const {
  double current_score = compute_score(placement);

  bool improved = true;
  while (improved) {
    // 每轮开头重置为false，若整轮无提升则退出while
    improved = false;
    for (int i = 0; i < num_logical_; ++i) {
      for (int j = i + 1; j < num_logical_; ++j) {
        // 试探性交换两个逻辑比特的物理位置
        std::swap(placement[i], placement[j]);
        double new_score = compute_score(placement);
        if (new_score > current_score) {
          // 有提升 -> 保留交换，更新最优分
          current_score = new_score;
          improved = true;
        } else {
          // 无提升 -> 撤销交换，恢复原状
          std::swap(placement[i], placement[j]);
        }
      }
    }
  }

  return placement;
}

std::vector<int> ion_trap_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities,
    const std::vector<double>& single_qubit_fidelities, int num_logical) {
  validate_mapping_inputs(coupling_list, edge_fidelities, num_logical);
  if (num_logical == 0) return {};
  IonTrapLayout layout(gates_list, coupling_list, edge_fidelities,
                       single_qubit_fidelities, num_logical);
  return layout.solve();
}

}  // namespace qcos
