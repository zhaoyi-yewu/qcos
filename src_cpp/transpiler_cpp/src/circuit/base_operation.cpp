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

BaseOperation::BaseOperation(const std::string& name_,
                             const std::vector<int>& targets_,
                             const std::vector<double>& arg_value_,
                             OperationType op_type_)
    : name(name_),
      targets(targets_),
      arg_value(arg_value_),
      operation_type(op_type_) {}

BaseOperation::BaseOperation(const std::string& name_,
                             const std::vector<int>& targets_,
                             double single_arg, OperationType op_type_)
    : name(name_),
      targets(targets_),
      arg_value{single_arg},
      operation_type(op_type_) {}

}  // namespace qcos