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

#include "circuit/gate_operation.h"

#include <stdexcept>

namespace qcos {

GateOperation::GateOperation(std::string name_, std::vector<int> targets_,
                             std::vector<double> arg_value_,
                             OperationType op_type_, bool hermitian_)
    : BaseOperation(std::move(name_), std::move(targets_),
                    std::move(arg_value_), op_type_),
      hermitian(hermitian_) {
  validate_params();
}

void GateOperation::validate_params() const {
  if (operation_type < OperationType::SINGLE_QUBIT_OPERATION) {
    throw std::invalid_argument("Unsupported operation type for gate: " +
                                name);
  }

  size_t expected_targets = static_cast<size_t>(operation_type);
  if (targets.size() != expected_targets) {
    throw std::invalid_argument("Invalid number of targets for gate: " + name);
  }
}

}  // namespace qcos
