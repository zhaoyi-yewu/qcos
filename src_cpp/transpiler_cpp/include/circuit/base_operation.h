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

#pragma once
#include <cmath>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#ifndef M_E
#define M_E 2.71828182845904523536
#endif

namespace qcos {

enum class OperationType {
  MEASURE = 0,
  SINGLE_QUBIT_OPERATION = 1,
  DOUBLE_QUBIT_OPERATION = 2,
  TRIPLE_QUBIT_OPERATION = 3,
  FOUR_QUBIT_OPERATION = 4,
  FIVE_QUBIT_OPERATION = 5,
  SYNC = -1,
  MOVE = -2,
  RESET = -3
};

class BaseOperation {
 public:
  std::string name;
  std::vector<int> targets;
  std::vector<double> arg_value;
  OperationType operation_type;

 public:
  virtual ~BaseOperation() = default;

  BaseOperation(
      std::string name_, std::vector<int> targets_,
      std::vector<double> arg_value_ = {},
      OperationType op_type_ = OperationType::SINGLE_QUBIT_OPERATION);
  const std::vector<int>& getTargets() const { return targets; }
  const std::vector<double>& getArgValue() const { return arg_value; }

  void setTargets(const std::vector<int>& targets_) { targets = targets_; }

  void setArgValue(const std::vector<double>& arg_value_) {
    arg_value = arg_value_;
  }
  std::string targets_to_string() const;
  std::string arg_value_to_string() const;
  std::string to_openqasm(const std::string& qubit_prefix = "q") const;

  virtual std::shared_ptr<BaseOperation> clone() const {
    return std::make_shared<BaseOperation>(*this);
  }
};

}  // namespace qcos
