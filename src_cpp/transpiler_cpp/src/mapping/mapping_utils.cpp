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
 * MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include "mapping/mapping_utils.h"

#include <queue>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>

namespace qcos {

namespace {

bool is_special_base_operation(const std::string& name) {
  // 处理特殊BaseOperation, 临时当作单量子门处理,
  // 完成routing后再转换回BaseOperation
  return name == "measure" || name == "sync" || name == "reset" ||
         name == "move";
}

}  // namespace

GateOperation to_gate_operation(const BaseOperation& op) {
  // 如果已经是GateOperation了，直接转换
  if (const auto* gate_op = dynamic_cast<const GateOperation*>(&op)) {
    return *gate_op;
  }

  OperationType operation_type = op.operation_type;
  // 处理特殊门，暂时当作单量子门处理
  if (operation_type < OperationType::SINGLE_QUBIT_OPERATION) {
    if (!is_special_base_operation(op.name)) {
      throw std::invalid_argument(
          "Unsupported BaseOperation for SABRE routing: " + op.name);
    }
    operation_type = OperationType::SINGLE_QUBIT_OPERATION;
  }

  return GateOperation(op.name, op.targets, op.arg_value, operation_type);
}

std::shared_ptr<BaseOperation> restore_base_operation(
    const GateOperation& routed_op) {
  // 恢复特殊门为 BaseOperation, 其他门保持 GateOperation
  try {
    auto restored =
        create_gate(routed_op.name, routed_op.targets, routed_op.arg_value);
    if (auto* gate = dynamic_cast<GateOperation*>(restored.get())) {
      gate->hermitian = routed_op.hermitian;
    }
    return restored;
  } catch (const std::runtime_error&) {
    return std::make_shared<GateOperation>(
        routed_op.name, routed_op.targets, routed_op.arg_value,
        routed_op.operation_type, routed_op.hermitian);
  }
}

void filter_low_fidelity(ChipCalibration& chip, double fidelity_threshold) {
  if (fidelity_threshold <= 0.0) return;

  // 步骤 1: 低于阈值的单比特保真度置 0
  for (size_t i = 0; i < chip.single_qubit_fidelities.size(); ++i) {
    if (chip.single_qubit_fidelities[i] <= fidelity_threshold) {
      chip.single_qubit_fidelities[i] = 0.0;
    }
  }

  // 步骤 2: 移除边保真度或任一端点单比特保真度低于阈值的边
  if (!chip.edge_fidelities.empty()) {
    size_t write_idx = 0;
    for (size_t read_idx = 0; read_idx < chip.coupling_list.size();
         ++read_idx) {
      double edge_fid = (read_idx < chip.edge_fidelities.size())
                            ? chip.edge_fidelities[read_idx]
                            : 0.0;
      auto [u, v] = chip.coupling_list[read_idx];
      double u_fid =
          (u < static_cast<int>(chip.single_qubit_fidelities.size()))
              ? chip.single_qubit_fidelities[u]
              : 0.0;
      double v_fid =
          (v < static_cast<int>(chip.single_qubit_fidelities.size()))
              ? chip.single_qubit_fidelities[v]
              : 0.0;
      if (edge_fid > fidelity_threshold && u_fid > fidelity_threshold &&
          v_fid > fidelity_threshold) {
        chip.coupling_list[write_idx] = chip.coupling_list[read_idx];
        chip.edge_fidelities[write_idx] = chip.edge_fidelities[read_idx];
        ++write_idx;
      }
    }
    chip.coupling_list.resize(write_idx);
    chip.edge_fidelities.resize(write_idx);
  }
}

void select_largest_component(std::vector<std::pair<int, int>>& coupling_list,
                              std::vector<double>& edge_fidelities) {
  if (coupling_list.empty()) return;

  // 将耦合边展开为无向邻接表，用于后续 BFS 连通性分析
  std::unordered_map<int, std::vector<int>> adjacency;
  for (const auto& [src, tgt] : coupling_list) {
    adjacency[src].push_back(tgt);
    adjacency[tgt].push_back(src);
  }

  // 对每个未访问节点做 BFS，找出节点数最多的连通分量
  std::unordered_set<int> visited;
  std::vector<int> largest_component;
  for (const auto& [node, _] : adjacency) {
    if (visited.count(node)) continue;
    // 从当前节点出发，BFS 收集本连通分量的所有节点
    std::vector<int> component;
    std::queue<int> bfs_queue;
    bfs_queue.push(node);
    visited.insert(node);
    while (!bfs_queue.empty()) {
      int current = bfs_queue.front();
      bfs_queue.pop();
      component.push_back(current);
      for (int neighbor : adjacency[current]) {
        if (!visited.count(neighbor)) {
          visited.insert(neighbor);
          bfs_queue.push(neighbor);
        }
      }
    }
    // 更新最大连通分量
    if (component.size() > largest_component.size()) {
      largest_component = std::move(component);
    }
  }

  // 原地过滤：只保留两端均在最大连通分量内的边
  std::unordered_set<int> largest_component_set(largest_component.begin(),
                                                largest_component.end());
  size_t write_idx = 0;
  for (size_t read_idx = 0; read_idx < coupling_list.size(); ++read_idx) {
    // 边的两个端点都在最大分量中才保留
    if (largest_component_set.count(coupling_list[read_idx].first) &&
        largest_component_set.count(coupling_list[read_idx].second)) {
      coupling_list[write_idx] = coupling_list[read_idx];
      if (read_idx < edge_fidelities.size()) {
        edge_fidelities[write_idx] = edge_fidelities[read_idx];
      }
      ++write_idx;
    }
  }
  coupling_list.resize(write_idx);
  edge_fidelities.resize(write_idx);
}

PhysicalIdRemap densify_chip_topology(ChipCalibration& chip) {
  auto& coupling_list = chip.coupling_list;
  auto& single_qubit_fidelities = chip.single_qubit_fidelities;

  // 步骤 1: 收集耦合边中出现的量子位
  std::set<int> coupled_qubits;
  for (const auto& [source, target] : coupling_list) {
    coupled_qubits.insert(source);
    coupled_qubits.insert(target);
  }
  // 步骤 2: 加入保真度 > 0 的单比特（已由 filter_low_fidelity 过滤）
  std::set<int> available_qubits = coupled_qubits;
  for (size_t idx = 0; idx < single_qubit_fidelities.size(); ++idx) {
    if (single_qubit_fidelities[idx] > 0.0) {
      available_qubits.insert(static_cast<int>(idx));
    }
  }

  PhysicalIdRemap remap;
  if (available_qubits.empty()) {
    chip = ChipCalibration();
    return remap;
  }

  // 步骤 2: 建立双向映射表
  int max_orig_id = *available_qubits.rbegin();
  remap.orig_to_dense.assign(max_orig_id + 1, -1);
  remap.dense_to_orig.reserve(available_qubits.size());
  for (int orig_id : available_qubits) {
    remap.orig_to_dense[orig_id] =
        static_cast<int>(remap.dense_to_orig.size());
    remap.dense_to_orig.push_back(orig_id);
  }
  remap.dense_count = static_cast<int>(remap.dense_to_orig.size());

  // 步骤 3: 耦合边端点转稠密 ID
  for (auto& [source, target] : coupling_list) {
    source = remap.orig_to_dense[source];
    target = remap.orig_to_dense[target];
  }

  // 步骤 4: 重建单比特保真度数组
  std::vector<double> dense_qubit_fidelity(remap.dense_count, 0.0);
  for (int dense_id = 0; dense_id < remap.dense_count; ++dense_id) {
    int orig_id = remap.dense_to_orig[dense_id];
    if (orig_id < static_cast<int>(single_qubit_fidelities.size())) {
      dense_qubit_fidelity[dense_id] = single_qubit_fidelities[orig_id];
    }
  }
  single_qubit_fidelities = std::move(dense_qubit_fidelity);

  return remap;
}

/**
 * @brief 将稠密物理 ID 还原为原始物理 ID
 *
 * 两组数据均从稠密 0..N-1 空间映射回原始物理 ID 空间:
 *   - physical_gates: 每条门的目标位替换为原始 ID
 *   - logic2phy:      每个逻辑位对应的物理位替换为原始 ID
 */
void restore_physical_ids(const PhysicalIdRemap& remap,
                          std::vector<GateOperation>& physical_gates,
                          std::vector<int>& logic2phy) {
  // 门目标: dense_id → orig_id
  for (auto& gate : physical_gates) {
    for (int& target : gate.targets) {
      if (target >= 0 &&
          target < static_cast<int>(remap.dense_to_orig.size())) {
        target = remap.dense_to_orig[target];
      }
    }
  }

  // 逻辑→物理: dense_id → orig_id
  for (int& phy : logic2phy) {
    if (phy >= 0 && phy < static_cast<int>(remap.dense_to_orig.size())) {
      phy = remap.dense_to_orig[phy];
    }
  }
}

}  // namespace qcos