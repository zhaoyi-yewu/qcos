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
#include <string>
#include <vector>

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
  BaseOperation(
      const std::string& name_, const std::vector<int>& targets_ = {},
      const std::vector<double>& arg_value_ = {},
      OperationType op_type_ = OperationType::SINGLE_QUBIT_OPERATION);

  BaseOperation(
      const std::string& name_, const std::vector<int>& targets_,
      double single_arg,
      OperationType op_type_ = OperationType::SINGLE_QUBIT_OPERATION);
};

}  // namespace qcos
