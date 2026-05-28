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

#include "mapping/sabre_utils.h"

#include <stdexcept>
#include <string>

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

std::unique_ptr<BaseOperation> restore_base_operation(
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
    return std::make_unique<GateOperation>(
        routed_op.name, routed_op.targets, routed_op.arg_value,
        routed_op.operation_type, routed_op.hermitian);
  }
}

}  // namespace qcos