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

#include <cassert>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "compiler/operations/classic_controlled_operation.hpp"
#include "compiler/permutation.hpp"
#include "compiler/qasm_compiler/parser/inst_visitor.hpp"
#include "compiler/qasm_compiler/parser/types.hpp"

namespace qasm {

struct DebugInfo {
  size_t line;
  size_t column;
  std::string filename;
  DebugInfo* parent;  // raw pointer — lifetime owned by the parse session pool

  DebugInfo(const size_t l, const size_t c, std::string file,
            DebugInfo* parentDebugInfo = nullptr)
      : line(l),
        column(c),
        filename(std::move(std::move(file))),
        parent(parentDebugInfo) {}

  [[nodiscard]] std::string toString() const {
    return filename + ":" + std::to_string(line) + ":" +
           std::to_string(column);
  }
};

// ExpressionKind is forward-declared in inst_visitor.hpp (included above).
// It is used for O(1) dispatch — replaces dynamic_pointer_cast chain.

// Expressions
class Expression {
 public:
  virtual ~Expression() = default;

  // Returns the ExpressionKind ordinal — used by ExpressionVisitor::visit()
  // for O(1) dispatch without requiring a full type definition at the call site.
  virtual int kindOrdinal() const = 0;

  virtual ExpressionKind kind() const = 0;
  virtual std::string getName() = 0;
};

class DeclarationExpression {
 public:
  std::shared_ptr<Expression> expression;

  explicit DeclarationExpression(std::shared_ptr<Expression> expr)
      : expression(std::move(expr)) {}

  virtual ~DeclarationExpression() = default;
};

class Constant : public Expression {
  std::variant<int64_t, double, bool> val;
  bool isSigned;
  bool isFp;
  bool isBoolean;

 public:
  Constant(int64_t value, const bool valueIsSigned)
      : val(value), isSigned(valueIsSigned), isFp(false), isBoolean(false) {}

  explicit Constant(double value)
      : val(value), isSigned(true), isFp(true), isBoolean(false) {}
  explicit Constant(bool value)
      : val(value), isSigned(false), isFp(false), isBoolean(true) {}

  int kindOrdinal() const override { return static_cast<int>(ExpressionKind::Constant); }
  ExpressionKind kind() const override { return ExpressionKind::Constant; }
  [[nodiscard]] bool isInt() const { return !isFp; }
  [[nodiscard]] bool isSInt() const { return !isFp && isSigned; }
  [[nodiscard]] bool isUInt() const { return !isFp && !isSigned; }
  [[nodiscard]] bool isFP() const { return isFp; }
  [[nodiscard]] bool isBool() const { return isBoolean; }
  [[nodiscard]] virtual int64_t getSInt() const { return std::get<0>(val); }
  [[nodiscard]] virtual uint64_t getUInt() const {
    return static_cast<uint64_t>(std::get<0>(val));
  }
  [[nodiscard]] virtual double getFP() const { return std::get<1>(val); }
  [[nodiscard]] virtual double asFP() const {
    if (isFp) {
      return getFP();
    }
    if (isSigned) {
      return static_cast<double>(getSInt());
    }
    return static_cast<double>(getUInt());
  }
  [[nodiscard]] virtual bool getBool() const { return std::get<2>(val); }

  std::string getName() override { return "Constant"; }
};

class BinaryExpression
    : public Expression,
      public std::enable_shared_from_this<BinaryExpression> {
 public:
  enum Op {
    Power,
    Add,
    Subtract,
    Multiply,
    Divide,
    Modulo,
    LeftShift,
    RightShift,
    LessThan,
    LessThanOrEqual,
    GreaterThan,
    GreaterThanOrEqual,
    Equal,
    NotEqual,
    BitwiseAnd,
    BitwiseXor,
    BitwiseOr,
    LogicalAnd,
    LogicalOr,
  };

  Op op;
  std::shared_ptr<Expression> lhs;
  std::shared_ptr<Expression> rhs;

  BinaryExpression(const Op opcode, std::shared_ptr<Expression> l,
                   std::shared_ptr<Expression> r)
      : op(opcode), lhs(std::move(l)), rhs(std::move(r)) {}

  int kindOrdinal() const override { return static_cast<int>(ExpressionKind::Binary); }
  ExpressionKind kind() const override { return ExpressionKind::Binary; }
  std::string getName() override { return "BinaryExpr"; }
};

std::optional<qc::ComparisonKind> getComparisonKind(BinaryExpression::Op op);

class UnaryExpression : public Expression,
                        public std::enable_shared_from_this<UnaryExpression> {
 public:
  enum Op {
    BitwiseNot,
    LogicalNot,
    Negate,
    DurationOf,
    Sin,
    Cos,
    Tan,
    Exp,
    Ln,
    Sqrt,
  };

  std::shared_ptr<Expression> operand;
  Op op;

  UnaryExpression(const Op opcode, std::shared_ptr<Expression> expr)
      : operand(std::move(expr)), op(opcode) {}

  int kindOrdinal() const override { return static_cast<int>(ExpressionKind::Unary); }
  ExpressionKind kind() const override { return ExpressionKind::Unary; }
  std::string getName() override { return "UnaryExpr"; }
};

class IdentifierExpression
    : public Expression,
      public std::enable_shared_from_this<IdentifierExpression> {
 public:
  std::string identifier;

  explicit IdentifierExpression(std::string id) : identifier(std::move(id)) {}

  int kindOrdinal() const override { return static_cast<int>(ExpressionKind::Identifier); }
  ExpressionKind kind() const override { return ExpressionKind::Identifier; }
  std::string getName() override {
    return std::string{"IdentifierExpr ("} + identifier + ")";
  }
};

class IdentifierList : public Expression,
                       public std::enable_shared_from_this<IdentifierList> {
 public:
  std::vector<std::shared_ptr<IdentifierExpression>> identifiers{};

  explicit IdentifierList(
      std::vector<std::shared_ptr<IdentifierExpression>> ids)
      : identifiers(std::move(ids)) {}

  explicit IdentifierList() = default;

  int kindOrdinal() const override { return static_cast<int>(ExpressionKind::IdentifierList); }
  ExpressionKind kind() const override { return ExpressionKind::IdentifierList; }
  std::string getName() override { return "IdentifierList"; }
};

// TODO: physical qubits are currently not supported
class GateOperand {
 public:
  std::string identifier;
  std::shared_ptr<Expression> expression;

  GateOperand(std::string id, std::shared_ptr<Expression> expr)
      : identifier(std::move(id)), expression(std::move(expr)) {}
};

class MeasureExpression
    : public Expression,
      public std::enable_shared_from_this<MeasureExpression> {
 public:
  std::shared_ptr<GateOperand> gate;

  explicit MeasureExpression(std::shared_ptr<GateOperand> gateOperand)
      : gate(std::move(gateOperand)) {}

  int kindOrdinal() const override { return static_cast<int>(ExpressionKind::Measure); }
  ExpressionKind kind() const override { return ExpressionKind::Measure; }
  std::string getName() override { return "MeasureExpression"; }
};

// ── Deferred definition of ExpressionVisitor::visit() ───────────────
// Must be placed here, after all Expression subclasses are fully defined,
// because calling kindOrdinal() requires a complete Expression type.
template <typename T>
T ExpressionVisitor<T>::visit(const std::shared_ptr<Expression>& expression) {
  if (expression == nullptr) {
    throw std::runtime_error("Expression is null");
  }
  switch (expression->kindOrdinal()) {
    case static_cast<int>(ExpressionKind::Binary):
      return visitBinaryExpression(
          std::static_pointer_cast<BinaryExpression>(expression));
    case static_cast<int>(ExpressionKind::Unary):
      return visitUnaryExpression(
          std::static_pointer_cast<UnaryExpression>(expression));
    case static_cast<int>(ExpressionKind::Constant):
      return visitConstantExpression(
          std::static_pointer_cast<Constant>(expression));
    case static_cast<int>(ExpressionKind::Identifier):
      return visitIdentifierExpression(
          std::static_pointer_cast<IdentifierExpression>(expression));
    case static_cast<int>(ExpressionKind::IdentifierList):
      return visitIdentifierList(
          std::static_pointer_cast<IdentifierList>(expression));
    case static_cast<int>(ExpressionKind::Measure):
      return visitMeasureExpression(
          std::static_pointer_cast<MeasureExpression>(expression));
  }
  throw std::runtime_error("Unhandled expression type.");
}

// Statements

class Statement {
 public:
  DebugInfo debugInfo;  // inline — no heap allocation, no refcount
  explicit Statement(DebugInfo debug)
      : debugInfo(std::move(debug)) {}
  virtual ~Statement() = default;

  virtual void accept(InstVisitor* visitor) = 0;
};

class QuantumStatement : public Statement {
 protected:
  explicit QuantumStatement(DebugInfo debug)
      : Statement(std::move(debug)) {}
};

class GateDeclaration : public Statement,
                        public std::enable_shared_from_this<GateDeclaration> {
 public:
  std::string identifier;
  std::shared_ptr<IdentifierList> parameters;
  std::shared_ptr<IdentifierList> qubits;
  std::vector<std::shared_ptr<QuantumStatement>> statements;
  bool isOpaque;

  explicit GateDeclaration(
      DebugInfo debug, std::string id,
      std::shared_ptr<IdentifierList> params,
      std::shared_ptr<IdentifierList> qbits,
      std::vector<std::shared_ptr<QuantumStatement>> stmts,
      const bool opaque = false)
      : Statement(std::move(debug)),
        identifier(std::move(id)),
        parameters(std::move(params)),
        qubits(std::move(qbits)),
        statements(std::move(stmts)),
        isOpaque(opaque) {
    if (opaque) {
      assert(statements.empty() && "Opaque gate should not have statements.");
    }
  }

  void accept(InstVisitor* visitor) override {
    visitor->visitGateStatement(shared_from_this());
  }
};

class VersionDeclaration
    : public Statement,
      public std::enable_shared_from_this<VersionDeclaration> {
 public:
  double version;

  explicit VersionDeclaration(DebugInfo debug,
                              const double versionNum)
      : Statement(std::move(debug)), version(versionNum) {}

  void accept(InstVisitor* visitor) override {
    visitor->visitVersionDeclaration(shared_from_this());
  }
};

class InitialLayout : public Statement,
                      public std::enable_shared_from_this<InitialLayout> {
 public:
  qc::Permutation permutation;

  explicit InitialLayout(DebugInfo debug,
                         qc::Permutation perm)
      : Statement(std::move(debug)), permutation(std::move(perm)) {}

 private:
  void accept(InstVisitor* visitor) override {
    visitor->visitInitialLayout(shared_from_this());
  }
};

class OutputPermutation
    : public Statement,
      public std::enable_shared_from_this<OutputPermutation> {
 public:
  qc::Permutation permutation;

  explicit OutputPermutation(DebugInfo debug,
                             qc::Permutation perm)
      : Statement(std::move(debug)), permutation(std::move(perm)) {}

 private:
  void accept(InstVisitor* visitor) override {
    visitor->visitOutputPermutation(shared_from_this());
  }
};

class DeclarationStatement
    : public Statement,
      public std::enable_shared_from_this<DeclarationStatement> {
 public:
  bool isConst;
  std::variant<std::shared_ptr<TypeExpr>, std::shared_ptr<ResolvedType>> type;
  std::string identifier;
  std::shared_ptr<DeclarationExpression> expression;

  DeclarationStatement(DebugInfo debug,
                       const bool declIsConst, std::shared_ptr<TypeExpr> ty,
                       std::string id,
                       std::shared_ptr<DeclarationExpression> expr)
      : Statement(std::move(debug)),
        isConst(declIsConst),
        type(ty),
        identifier(std::move(id)),
        expression(std::move(expr)) {}

  void accept(InstVisitor* visitor) override {
    visitor->visitDeclarationStatement(shared_from_this());
  }
};

class GateModifier : public std::enable_shared_from_this<GateModifier> {
 protected:
  GateModifier() {}

 public:
  virtual ~GateModifier() = default;
};

class InvGateModifier : public GateModifier,
                        public std::enable_shared_from_this<InvGateModifier> {
 public:
  explicit InvGateModifier() = default;
};

class PowGateModifier : public GateModifier,
                        public std::enable_shared_from_this<PowGateModifier> {
 public:
  std::shared_ptr<Expression> expression;

  explicit PowGateModifier(std::shared_ptr<Expression> expr)
      : expression(std::move(expr)) {}
};

class CtrlGateModifier
    : public GateModifier,
      public std::enable_shared_from_this<CtrlGateModifier> {
 public:
  bool ctrlType;
  std::shared_ptr<Expression> expression;

  explicit CtrlGateModifier(const bool ty, std::shared_ptr<Expression> expr)
      : ctrlType(ty), expression(std::move(expr)) {}
};

class GateCallStatement
    : public QuantumStatement,
      public std::enable_shared_from_this<GateCallStatement> {
 public:
  std::string identifier;
  std::vector<std::shared_ptr<GateModifier>> modifiers;
  std::vector<std::shared_ptr<Expression>> arguments;
  std::vector<std::shared_ptr<GateOperand>> operands;

  GateCallStatement(DebugInfo debug, std::string id,
                    std::vector<std::shared_ptr<GateModifier>> modifierList,
                    std::vector<std::shared_ptr<Expression>> argumentList,
                    std::vector<std::shared_ptr<GateOperand>> operandList)
      : QuantumStatement(std::move(debug)),
        identifier(std::move(id)),
        modifiers(std::move(modifierList)),
        arguments(std::move(argumentList)),
        operands(std::move(operandList)) {}

  void accept(InstVisitor* visitor) override {
    visitor->visitGateCallStatement(shared_from_this());
  }
};

class AssignmentStatement
    : public Statement,
      public std::enable_shared_from_this<AssignmentStatement> {
 public:
  enum Type {
    Assignment,
    PlusAssignment,
    MinusAssignment,
    TimesAssignment,
    DivAssignment,
    BitwiseAndAssignment,
    BitwiseOrAssignment,
    BitwiseNotAssignment,
    BitwiseXorAssignment,
    LeftShiftAssignment,
    RightShiftAssignment,
    ModuloAssignment,
    PowerAssignment,
  } type;
  std::shared_ptr<IdentifierExpression> identifier;
  std::shared_ptr<Expression> indexExpression;
  std::shared_ptr<DeclarationExpression> expression;

  AssignmentStatement(DebugInfo debug, const Type ty,
                      std::shared_ptr<IdentifierExpression> id,
                      std::shared_ptr<Expression> indexExpr,
                      std::shared_ptr<DeclarationExpression> expr)
      : Statement(std::move(debug)),
        type(ty),
        identifier(std::move(id)),
        indexExpression(std::move(indexExpr)),
        expression(std::move(expr)) {}

  void accept(InstVisitor* visitor) override {
    visitor->visitAssignmentStatement(shared_from_this());
  }
};

class BarrierStatement
    : public QuantumStatement,
      public std::enable_shared_from_this<BarrierStatement> {
 public:
  std::vector<std::shared_ptr<GateOperand>> gates;

  explicit BarrierStatement(DebugInfo debug,
                            std::vector<std::shared_ptr<GateOperand>> gateList)
      : QuantumStatement(std::move(debug)), gates(std::move(gateList)) {}

  void accept(InstVisitor* visitor) override {
    visitor->visitBarrierStatement(shared_from_this());
  }
};

class ResetStatement : public QuantumStatement,
                       public std::enable_shared_from_this<ResetStatement> {
 public:
  std::shared_ptr<GateOperand> gate;

  explicit ResetStatement(DebugInfo debug,
                          std::shared_ptr<GateOperand> g)
      : QuantumStatement(std::move(debug)), gate(std::move(g)) {}

  void accept(InstVisitor* visitor) override {
    visitor->visitResetStatement(shared_from_this());
  }
};

class IfStatement : public Statement,
                    public std::enable_shared_from_this<IfStatement> {
 public:
  std::shared_ptr<Expression> condition;
  std::vector<std::shared_ptr<Statement>> thenStatements;
  std::vector<std::shared_ptr<Statement>> elseStatements;

  IfStatement(const std::shared_ptr<Expression>& cond,
              const std::vector<std::shared_ptr<Statement>>& thenStmts,
              const std::vector<std::shared_ptr<Statement>>& elseStmts,
              DebugInfo debug)
      : Statement(std::move(debug)),
        condition(cond),
        thenStatements(thenStmts),
        elseStatements(elseStmts) {}

  void accept(InstVisitor* visitor) override {
    visitor->visitIfStatement(shared_from_this());
  }
};
}  // namespace qasm
