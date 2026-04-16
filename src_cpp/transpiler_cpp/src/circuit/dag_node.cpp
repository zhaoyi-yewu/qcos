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

#include "circuit/dag_node.h"

#include <sstream>

namespace qcos {

std::string vector_to_string(const std::vector<int>& values) {
  std::ostringstream oss;
  oss << "[";
  for (size_t i = 0; i < values.size(); ++i) {
    if (i > 0) {
      oss << ", ";
    }
    oss << values[i];
  }
  oss << "]";
  return oss.str();
}

DAGOpNode::DAGOpNode(std::shared_ptr<BaseOperation> op_,
                     std::vector<int> qargs_, std::vector<int> cargs_)
    : op(std::move(op_)), qargs(std::move(qargs_)), cargs(std::move(cargs_)) {
  sort_key_ = vector_to_string(qargs);
}

std::string DAGOpNode::repr() const {
  std::ostringstream oss;
  oss << "DAGOpNode(op=" << op->name << ", qargs=" << vector_to_string(qargs)
      << ", cargs=" << vector_to_string(cargs) << ")";
  return oss.str();
}

}  // namespace qcos
