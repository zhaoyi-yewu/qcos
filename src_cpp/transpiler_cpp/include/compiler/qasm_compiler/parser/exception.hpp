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

#include "compiler/qasm_compiler/parser/statement.hpp"

namespace qasm {
class CompilerError final : public std::exception {
 public:
  std::string message{};
  DebugInfo debugInfo;  // inline — no heap allocation

  CompilerError(std::string msg, DebugInfo debug)
      : message(std::move(msg)), debugInfo(std::move(debug)) {}

  [[nodiscard]] std::string toString() const {
    std::stringstream ss{};
    ss << debugInfo.toString();

    auto* parentDebugInfo = debugInfo.parent;
    while (parentDebugInfo != nullptr) {
      ss << "\n  (included from " << parentDebugInfo->toString() << ")";
      parentDebugInfo = parentDebugInfo->parent;
    }

    ss << ":\n" << message;

    return ss.str();
  }
};
}  // namespace qasm

class ConstEvalError final : public std::exception {
 public:
  std::string message{};

  explicit ConstEvalError(std::string msg) : message(std::move(msg)) {}

  [[nodiscard]] std::string toString() const {
    return "Constant Evaluation: " + message;
  }
};

class TypeCheckError final : public std::exception {
 public:
  std::string message{};

  explicit TypeCheckError(std::string msg) : message(std::move(msg)) {}

  [[nodiscard]] std::string toString() const {
    return "Type Check Error: " + message;
  }
};
