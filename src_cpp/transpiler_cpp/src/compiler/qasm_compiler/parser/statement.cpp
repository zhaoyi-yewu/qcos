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

#include "compiler/qasm_compiler/parser/statement.hpp"

namespace qasm {

std::optional<qc::ComparisonKind> getComparisonKind(BinaryExpression::Op op) {
  switch (op) {
    case BinaryExpression::Op::LessThan:
      return qc::ComparisonKind::Lt;
    case BinaryExpression::Op::LessThanOrEqual:
      return qc::ComparisonKind::Leq;
    case BinaryExpression::Op::GreaterThan:
      return qc::ComparisonKind::Gt;
    case BinaryExpression::Op::GreaterThanOrEqual:
      return qc::ComparisonKind::Geq;
    case BinaryExpression::Op::Equal:
      return qc::ComparisonKind::Eq;
    case BinaryExpression::Op::NotEqual:
      return qc::ComparisonKind::Neq;
    default:
      return std::nullopt;
  }
}
}  // namespace qasm
