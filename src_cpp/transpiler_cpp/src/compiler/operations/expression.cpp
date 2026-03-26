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

#include "compiler/operations/expression.hpp"

namespace sym {

Variable::Variable(const std::string& name) {
  const auto it = registered.find(name);
  if (it != registered.end()) {
    id = it->second;
  } else {
    registered[name] = nextId;
    names[nextId] = name;
    id = nextId;
    ++nextId;
  }
}

std::string Variable::getName() const { return names[id]; }

std::ostream& operator<<(std::ostream& os, const Variable& var) {
  os << var.getName();
  return os;
}
}  // namespace sym
