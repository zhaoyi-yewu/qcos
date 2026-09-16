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
#include <unordered_map>

namespace qcos {

constexpr int kInitialMappingPrefixLayers = 25;

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
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<int>& initial_layout) {
  SABRE sabre(coupling_list);
  auto prefix_gates =
      extract_two_qubit_layer_prefix(gates_list, kInitialMappingPrefixLayers);

  std::vector<GateOperation> reverse_gates = prefix_gates;
  std::reverse(reverse_gates.begin(), reverse_gates.end());

  // 以 initial_layout 作为正向路由起点（空则从零开始），1 次迭代
  sabre.execute_routing(prefix_gates, initial_layout);
  std::vector<int> reverse_mapping = sabre.get_final_mapping();

  sabre.execute_routing(reverse_gates, reverse_mapping);
  return sabre.get_final_mapping();
}

}  // namespace qcos
