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

#include "circuit/base_operation.h"

namespace qcos {

class GateOperation : public BaseOperation {
 public:
  bool hermitian;

  GateOperation(std::string name_, std::vector<int> targets_,
                std::vector<double> arg_value_ = {},
                OperationType op_type_ = OperationType::SINGLE_QUBIT_OPERATION,
                bool hermitian_ = true);

 private:
  void validate_params() const;
};

}  // namespace qcos
