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
 *      EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 *      MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#pragma once

#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "circuit/gate_operation.h"
#include "mapping/sabre_routing.h"

namespace qcos {

/**
 * @class GreedyRouting
 * @brief 朴素阻塞驱动 routing。
 *
 * 核心思想不是提前求全局 routing 方案，而是按前沿层推进：
 * - 能执行的门直接执行；
 * - 一旦遇到当前不可执行的双比特门，就在该门两端物理比特的最短路径上
 *   插入一个 SWAP，把其中一端朝另一端移动一步；
 * - 重复上述过程，直到该门可执行，再继续向前推进。
 *
 * 这种方法实现简单、行为直观，适合作为基线贪心 routing。
 */
class GreedyRouting {
 public:
  explicit GreedyRouting(const std::vector<std::pair<int, int>>& coupling_list);

  void execute(const std::vector<GateOperation>& gates_list,
               const std::vector<int>& initial_l2p = {});

  inline std::vector<GateOperation> get_physical_gates() const {
    return phy_exe_gates;
  }

  std::vector<int> logic2phy;
  std::vector<int> phy2logic;

 private:
  int phy_qubit_num{};
  std::unordered_map<int, std::unordered_set<int>> adj_list;
  std::vector<int> cur_l2p;
  std::vector<int> cur_p2l;
  std::vector<Node*> front_layer;
  std::vector<GateOperation> phy_exe_gates;

  void build_coupling_graph(
      const std::vector<std::pair<int, int>>& coupling_list);

  int get_qubit_num_from_ir(
      const std::vector<GateOperation>& gates_list) const;

  bool can_execute(const Node* node) const;

  std::vector<int> shortest_path_between(int start, int goal) const;

  std::pair<int, int> pick_swap_for_blocked_gate(const Node* node) const;

  void apply_swap_inplace(int u, int v);

  GateOperation phy_gate(const GateOperation& logic_gate) const;
};

}  // namespace qcos
