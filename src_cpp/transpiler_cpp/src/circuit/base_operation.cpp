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

#include "circuit/base_operation.h"

namespace qcos {

BaseOperation::BaseOperation(std::string name_, std::vector<int> targets_,
                             std::vector<double> arg_value_,
                             OperationType op_type_)
    : name(std::move(name_)),
      targets(std::move(targets_)),
      arg_value(std::move(arg_value_)),
      operation_type(op_type_) {}

std::string BaseOperation::targets_to_string() const {
  std::ostringstream oss;
  oss << "[";
  for (size_t i = 0; i < targets.size(); ++i) {
    if (i > 0) oss << ", ";
    oss << targets[i];
  }
  oss << "]";
  return oss.str();
}

std::string BaseOperation::arg_value_to_string() const {
  std::ostringstream oss;
  oss << "[";
  for (size_t i = 0; i < arg_value.size(); ++i) {
    if (i > 0) oss << ", ";

    double value = arg_value[i];

    if (std::abs(value - M_PI) < 1e-10) {
      oss << "π";
    } else if (std::abs(value + M_PI) < 1e-10) {
      oss << "-π";
    } else if (std::abs(value - M_PI / 2) < 1e-10) {
      oss << "π/2";
    } else if (std::abs(value + M_PI / 2) < 1e-10) {
      oss << "-π/2";
    } else if (std::abs(value - M_PI / 4) < 1e-10) {
      oss << "π/4";
    } else if (std::abs(value + M_PI / 4) < 1e-10) {
      oss << "-π/4";
    } else {
      oss << std::fixed << std::setprecision(4) << value;
    }
  }
  oss << "]";
  return oss.str();
}

std::string BaseOperation::to_openqasm(const std::string& qubit_prefix) const {
  // Ensure that the operation has at least one target qubit
  if (targets.empty()) {
    throw std::runtime_error(
        "targets cannot be empty when generating OpenQASM statement.");
  }

  // Build the argument part (e.g., rx(1.57))
  std::string arg_str = "";
  if (!arg_value.empty()) {
    std::ostringstream arg_oss;
    arg_oss << "(";
    for (size_t i = 0; i < arg_value.size(); ++i) {
      if (i > 0) arg_oss << ", ";

      double value = arg_value[i];
      if (std::abs(value - M_PI) < 1e-10) {
        arg_oss << "pi";
      } else if (std::abs(value + M_PI) < 1e-10) {
        arg_oss << "-pi";
      } else if (std::abs(value - M_PI / 2) < 1e-10) {
        arg_oss << "pi/2";
      } else if (std::abs(value + M_PI / 2) < 1e-10) {
        arg_oss << "-pi/2";
      } else if (std::abs(value - M_PI / 4) < 1e-10) {
        arg_oss << "pi/4";
      } else if (std::abs(value + M_PI / 4) < 1e-10) {
        arg_oss << "-pi/4";
      } else {
        arg_oss << std::fixed << std::setprecision(8) << value;
      }
    }
    arg_oss << ")";
    arg_str = arg_oss.str();
  }

  // Build the qubit target part (e.g., q[0], q[1])
  std::ostringstream targets_oss;
  for (size_t i = 0; i < targets.size(); ++i) {
    if (i > 0) targets_oss << ", ";
    targets_oss << qubit_prefix << "[" << targets[i] << "]";
  }
  std::string targets_str = targets_oss.str();

  // Construct the full OpenQASM instruction
  return name + arg_str + " " + targets_str + ";";
}

}  // namespace qcos
