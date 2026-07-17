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

#include <functional>
#include <iostream>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <vector>

#include "compiler/qasm_compiler/parser/exception.hpp"
#include "compiler/qasm_compiler/parser/scanner.hpp"
#include "compiler/qasm_compiler/parser/statement.hpp"
#include "compiler/qasm_compiler/parser/std_gates.hpp"

namespace qasm {
class Parser {
  struct ScannerState {
   private:
    std::unique_ptr<std::istream> is;
    std::string qasmBuffer_;

   public:
    Token last{0, 0};
    Token t{0, 0};
    Token next{0, 0};
    std::unique_ptr<Scanner> scanner;
    std::optional<std::string> filename;
    bool isImplicitInclude;

    bool scan() {
      last = t;
      t = next;
      next = scanner->next();

      return t.kind != Token::Kind::Eof;
    }

    explicit ScannerState(
        std::istream* in,
        std::optional<std::string> debugFilename = std::nullopt,
        const bool implicitInclude = false)
        : scanner(std::make_unique<Scanner>(in)),
          filename(std::move(debugFilename)),
          isImplicitInclude(implicitInclude) {
      scan();
    }

    explicit ScannerState(
        std::unique_ptr<std::istream> in,
        std::optional<std::string> debugFilename = std::nullopt,
        const bool implicitInclude = false)
        : is(std::move(in)),
          scanner(std::make_unique<Scanner>(is.get())),
          filename(std::move(debugFilename)),
          isImplicitInclude(implicitInclude) {
      scan();
    }

    explicit ScannerState(
        const std::string& qasm,
        std::optional<std::string> debugFilename = std::nullopt,
        const bool implicitInclude = false)
        : qasmBuffer_(qasm),
          scanner(std::make_unique<Scanner>(qasmBuffer_)),
          filename(std::move(debugFilename)),
          isImplicitInclude(implicitInclude) {
      scan();
    }
  };

  std::stack<ScannerState> scanner{};
  DebugInfo* includeDebugInfo{nullptr};  // raw pointer into debugInfoPool_

  // Pool allocator for DebugInfo — avoids per-statement make_shared overhead.
  // All DebugInfo objects share the parse session lifetime and are freed
  // together.
  std::vector<std::unique_ptr<DebugInfo>> debugInfoPool_;

  [[noreturn]] void error(const Token& token, const std::string& msg) {
    std::cerr << "Error at line " << token.line << ", column " << token.col
              << ": " << msg << '\n';
    throw CompilerError(msg,
                        DebugInfo(token.line, token.col,
                                  scanner.top().filename.value_or("<input>"),
                                  includeDebugInfo));
  }

  [[nodiscard]] Token last() const {
    if (scanner.empty()) {
      throw std::runtime_error("No scanner available");
    }
    return scanner.top().last;
  }

  [[nodiscard]] Token current() const {
    if (scanner.empty()) {
      throw std::runtime_error("No scanner available");
    }
    return scanner.top().t;
  }

  [[nodiscard]] Token peek() const {
    if (scanner.empty()) {
      throw std::runtime_error("No scanner available");
    }
    return scanner.top().next;
  }

  Token expect(const Token::Kind& expected,
               const std::optional<std::string>& context = std::nullopt) {
    if (current().kind != expected) {
      std::string message = "Expected '" + Token::kindToString(expected) +
                            "', got '" + Token::kindToString(current().kind) +
                            "'.";
      if (context.has_value()) {
        message += " " + context.value();
      }
      error(current(), message);
    }

    auto token = current();
    scan();
    return token;
  }

 public:
  explicit Parser(std::istream* is, bool implicitlyIncludeStdgates = true) {
    scanner.emplace(is);
    scan();
    if (implicitlyIncludeStdgates) {
      scanner.emplace(std::make_unique<std::istringstream>(STDGATES),
                      "stdgates.inc", true);
      scan();
    }
  }

  explicit Parser(const std::string& qasm,
                  bool implicitlyIncludeStdgates = true) {
    scanner.emplace(qasm);
    scan();
    if (implicitlyIncludeStdgates) {
      scanner.emplace(std::make_unique<std::istringstream>(STDGATES),
                      "stdgates.inc", true);
      scan();
    }
  }

  virtual ~Parser() = default;

  std::shared_ptr<VersionDeclaration> parseVersionDeclaration();

  using StatementCallback = std::function<void(std::shared_ptr<Statement>)>;

  std::vector<std::shared_ptr<Statement>> parseProgram(
      StatementCallback callback = nullptr);

  std::shared_ptr<Statement> parseStatement();

  std::shared_ptr<QuantumStatement> parseQuantumStatement();

  void parseInclude();

  std::shared_ptr<AssignmentStatement> parseAssignmentStatement();

  std::shared_ptr<AssignmentStatement> parseMeasureStatement();

  std::shared_ptr<ResetStatement> parseResetStatement();

  std::shared_ptr<BarrierStatement> parseBarrierStatement();

  std::shared_ptr<Statement> parseDeclaration(bool isConst);

  std::shared_ptr<GateDeclaration> parseGateDefinition();

  std::shared_ptr<GateDeclaration> parseOpaqueGateDefinition();

  std::shared_ptr<GateCallStatement> parseGateCallStatement();

  std::shared_ptr<GateModifier> parseGateModifier();

  std::shared_ptr<GateOperand> parseGateOperand();

  std::shared_ptr<DeclarationExpression> parseDeclarationExpression();

  std::shared_ptr<MeasureExpression> parseMeasureExpression();

  std::shared_ptr<Expression> exponentiation();

  std::shared_ptr<Expression> factor();

  std::shared_ptr<Expression> term();

  std::shared_ptr<Expression> comparison();

  std::shared_ptr<Expression> parseExpression();

  std::shared_ptr<IdentifierList> parseIdentifierList();

  std::pair<std::shared_ptr<TypeExpr>, bool> parseType();

  std::shared_ptr<Expression> parseTypeDesignator();

  static qc::Permutation parsePermutation(std::string s);

  void scan();

  // Allocate a DebugInfo without heap-allocating a string for well-known
  // filenames. QASM 2.0 files go through the implicit stdgates.inc/qelib1.inc
  // include, so the filename is always one of three strings — cache them.
  DebugInfo makeDebugInfo(Token const& begin, Token const& /*end*/) {
    // Parameter `end` is currently not used.
    static const std::string s_stdgates{"stdgates.inc"};
    static const std::string s_qelib1{"qelib1.inc"};
    static const std::string s_input{"<input>"};
    const auto& fn = scanner.top().filename.has_value()
                         ? (scanner.top().filename.value() == "stdgates.inc")
                               ? s_stdgates
                           : (scanner.top().filename.value() == "qelib1.inc")
                               ? s_qelib1
                               : scanner.top().filename.value()
                         : s_input;
    return DebugInfo(begin.line, begin.col, fn, includeDebugInfo);
  }

  DebugInfo makeDebugInfo(Token const& token) {
    static const std::string s_stdgates{"stdgates.inc"};
    static const std::string s_qelib1{"qelib1.inc"};
    static const std::string s_input{"<input>"};
    const auto& fn = scanner.top().filename.has_value()
                         ? (scanner.top().filename.value() == "stdgates.inc")
                               ? s_stdgates
                           : (scanner.top().filename.value() == "qelib1.inc")
                               ? s_qelib1
                               : scanner.top().filename.value()
                         : s_input;
    return DebugInfo(token.line, token.col, fn, includeDebugInfo);
  }

  // Allocate a long-lived DebugInfo into the pool (for includeDebugInfo
  // chain). Returns a raw pointer that is valid for the entire parse session.
  DebugInfo* allocDebugInfo(size_t line, size_t col, std::string filename,
                            DebugInfo* parent = nullptr) {
    debugInfoPool_.push_back(
        std::make_unique<DebugInfo>(line, col, std::move(filename), parent));
    return debugInfoPool_.back().get();
  }

  [[nodiscard]] bool isAtEnd() const {
    return current().kind == Token::Kind::Eof;
  }
  std::shared_ptr<IfStatement> parseIfStatement();
  std::vector<std::shared_ptr<Statement>> parseBlockOrStatement();
};

}  // namespace qasm
