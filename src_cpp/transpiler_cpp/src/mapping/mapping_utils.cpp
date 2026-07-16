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

PhysicalIdRemap densify_chip_topology(ChipCalibration& chip,
                                      double fidelity_threshold) {
  auto& coupling_list = chip.coupling_list;
  auto& edge_fidelities = chip.edge_fidelities;
  auto& single_qubit_fidelities = chip.single_qubit_fidelities;

  // 步骤 1: 按 fidelity_threshold 移除低保真度边
  if (!edge_fidelities.empty() && fidelity_threshold > 0.0) {
    size_t write_idx = 0;
    for (size_t read_idx = 0; read_idx < coupling_list.size(); ++read_idx) {
      double fidelity = (read_idx < edge_fidelities.size())
                            ? edge_fidelities[read_idx]
                            : 0.0;
      if (fidelity > fidelity_threshold) {
        coupling_list[write_idx] = coupling_list[read_idx];
        edge_fidelities[write_idx] = edge_fidelities[read_idx];
        ++write_idx;
      }
    }
    coupling_list.resize(write_idx);
    edge_fidelities.resize(write_idx);
  }

  // 步骤 2: 收集可用量子位
  std::set<int> coupled_qubits;
  for (const auto& [source, target] : coupling_list) {
    coupled_qubits.insert(source);
    coupled_qubits.insert(target);
  }
  std::set<int> available_qubits = coupled_qubits;
  if (fidelity_threshold > 0.0) {
    for (size_t idx = 0; idx < single_qubit_fidelities.size(); ++idx) {
      if (single_qubit_fidelities[idx] > fidelity_threshold) {
        available_qubits.insert(static_cast<int>(idx));
      }
    }
  }

  PhysicalIdRemap remap;
  if (available_qubits.empty()) {
    chip = ChipCalibration();
    return remap;
  }

  // 步骤 3: 建立双向映射表
  int max_orig_id = *available_qubits.rbegin();
  remap.orig_to_dense.assign(max_orig_id + 1, -1);
  remap.dense_to_orig.reserve(available_qubits.size());
  for (int orig_id : available_qubits) {
    remap.orig_to_dense[orig_id] =
        static_cast<int>(remap.dense_to_orig.size());
    remap.dense_to_orig.push_back(orig_id);
  }
  remap.dense_count = static_cast<int>(remap.dense_to_orig.size());

  // 步骤 4: 耦合边端点转稠密 ID
  for (auto& [source, target] : coupling_list) {
    source = remap.orig_to_dense[source];
    target = remap.orig_to_dense[target];
  }

  // 步骤 5: 重建单比特保真度数组
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