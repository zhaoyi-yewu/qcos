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

#include "compiler/operations/classic_controlled_operation.hpp"

namespace qc {

std::string toString(const ComparisonKind& kind) {
  switch (kind) {
    case ComparisonKind::Eq:
      return "==";
    case ComparisonKind::Neq:
      return "!=";
    case ComparisonKind::Lt:
      return "<";
    case ComparisonKind::Leq:
      return "<=";
    case ComparisonKind::Gt:
      return ">";
    case ComparisonKind::Geq:
      return ">=";
    default:
      unreachable();
  }
}

std::ostream& operator<<(std::ostream& os, const ComparisonKind& kind) {
  os << toString(kind);
  return os;
}

ComparisonKind getInvertedComparsionKind(const ComparisonKind kind) {
  switch (kind) {
    case Lt:
      return Geq;
    case Leq:
      return Gt;
    case Gt:
      return Leq;
    case Geq:
      return Lt;
    case Eq:
      return Neq;
    case Neq:
      return Eq;
    default:
      unreachable();
  }
}
}  // namespace qc
