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

#include "decomposer/rule_applier.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <functional>
#include <sstream>
#include <stdexcept>
#include <unordered_set>
#include <vector>

namespace qcos {

namespace {

// Token types used in expression parsing
enum class ExprTokenKind {
  kNumber,    // Numeric literal, e.g. 3.14
  kVariable,  // Variable name, e.g. theta
  kOperator   // Operator, e.g. + - * /
};

// Token representation for expression parsing
struct ExprToken {
  ExprTokenKind kind;

  // Used when kind == kNumber
  double value = 0.0;

  // Used when kind == kVariable
  std::string text;

  // Used when kind == kOperator
  char op = '\0';
};

// Return operator precedence
//
// Priority:
//   ~  : unary minus
//   * /: multiplication/division
//   + -: addition/subtraction
int precedence(char op) {
  if (op == '~') {
    return 3;
  }

  return (op == '*' || op == '/') ? 2 : 1;
}

// Push an operator into the operator stack
//
// Implements the Shunting-yard algorithm.
// Operators with higher or equal precedence
// are popped before inserting the new operator.
void push_operator(std::vector<ExprToken>& output, std::vector<char>& ops,
                   char op) {
  while (!ops.empty() && ops.back() != '(' &&
         precedence(ops.back()) >= precedence(op)) {
    output.push_back({ExprTokenKind::kOperator, 0.0, {}, ops.back()});

    ops.pop_back();
  }

  ops.push_back(op);
}

// Compile an infix expression into Reverse Polish Notation (RPN)
//
// Example:
//   Input:
//     2*pi + theta/4
//
//   Output:
//     2 pi * theta 4 / +
std::vector<ExprToken> compile_expr(const std::string& expr) {
  // Output RPN token sequence
  std::vector<ExprToken> output;

  // Operator stack
  std::vector<char> ops;

  // Indicates whether the parser currently expects an operand
  //
  // true:
  //   expecting number / variable / '('
  //
  // false:
  //   expecting operator
  bool expect_operand = true;

  for (size_t i = 0; i < expr.size();) {
    const char c = expr[i];

    // Skip whitespace
    if (std::isspace(static_cast<unsigned char>(c))) {
      ++i;
      continue;
    }

    // =========================================================
    // Parse numeric literals
    // =========================================================
    if (std::isdigit(static_cast<unsigned char>(c)) || c == '.') {
      char* end = nullptr;

      // Parse floating-point number
      const double value = std::strtod(expr.c_str() + i, &end);

      output.push_back({ExprTokenKind::kNumber, value});

      i = static_cast<size_t>(end - expr.c_str());

      expect_operand = false;
      continue;
    }

    // =========================================================
    // Parse variables
    // =========================================================
    if (std::isalpha(static_cast<unsigned char>(c)) || c == '_') {
      size_t j = i + 1;

      // Variable names may contain:
      //   letters
      //   digits
      //   underscores
      while (j < expr.size() &&
             (std::isalnum(static_cast<unsigned char>(expr[j])) ||
              expr[j] == '_')) {
        ++j;
      }

      output.push_back({ExprTokenKind::kVariable, 0.0, expr.substr(i, j - i)});

      i = j;

      expect_operand = false;
      continue;
    }

    // =========================================================
    // Left parenthesis
    // =========================================================
    if (c == '(') {
      ops.push_back(c);

      ++i;

      expect_operand = true;
      continue;
    }

    // =========================================================
    // Right parenthesis
    // =========================================================
    if (c == ')') {
      // Pop operators until matching '('
      while (!ops.empty() && ops.back() != '(') {
        output.push_back({ExprTokenKind::kOperator, 0.0, {}, ops.back()});

        ops.pop_back();
      }

      // Missing matching '('
      if (ops.empty()) {
        throw std::runtime_error("Expr parse error: " + expr);
      }

      // Remove '('
      ops.pop_back();

      ++i;

      expect_operand = false;
      continue;
    }

    // =========================================================
    // Parse operators
    // =========================================================
    if (c == '+' || c == '-' || c == '*' || c == '/') {
      // Unary operator handling
      //
      // Examples:
      //   -x
      //   +y
      if (expect_operand) {
        // Unary plus is ignored
        if (c == '+') {
          ++i;
          continue;
        }

        // Unary minus
        if (c == '-') {
          // Use '~' internally for unary minus
          ops.push_back('~');

          ++i;
          continue;
        }

        throw std::runtime_error("Expr parse error: " + expr);
      }

      // Binary operator
      push_operator(output, ops, c);

      ++i;

      expect_operand = true;
      continue;
    }

    // Invalid character
    throw std::runtime_error("Expr parse error: " + expr);
  }

  // Flush remaining operators
  while (!ops.empty()) {
    // Unmatched '('
    if (ops.back() == '(') {
      throw std::runtime_error("Expr parse error: " + expr);
    }

    output.push_back({ExprTokenKind::kOperator, 0.0, {}, ops.back()});

    ops.pop_back();
  }

  return output;
}

// Evaluate a compiled RPN expression
//
// Input:
//   tokens : compiled RPN tokens
//   env    : variable environment
//
// Example:
//   expr = "2*pi + theta"
//   env = {theta: 1.5}
double eval_compiled_expr(const std::vector<ExprToken>& tokens,
                          const std::unordered_map<std::string, double>& env) {
  // Evaluation stack
  std::vector<double> stack;

  stack.reserve(tokens.size());

  for (const auto& token : tokens) {
    // =========================================================
    // Numeric literal
    // =========================================================
    if (token.kind == ExprTokenKind::kNumber) {
      stack.push_back(token.value);
    }

    // =========================================================
    // Variable lookup
    // =========================================================
    else if (token.kind == ExprTokenKind::kVariable) {
      // Built-in constant pi
      if (token.text == "pi") {
        stack.push_back(M_PI);
      }

      // Built-in constant e
      else if (token.text == "e") {
        stack.push_back(M_E);
      }

      // User-defined variable
      else {
        auto it = env.find(token.text);

        if (it == env.end()) {
          throw std::runtime_error("Unknown parameter: " + token.text);
        }

        stack.push_back(it->second);
      }
    }

    // =========================================================
    // Operator evaluation
    // =========================================================
    else {
      // Unary minus
      if (token.op == '~') {
        if (stack.empty()) {
          throw std::runtime_error("Expr evaluation stack underflow");
        }

        stack.back() = -stack.back();

        continue;
      }

      // Binary operators require two operands
      if (stack.size() < 2) {
        throw std::runtime_error("Expr evaluation stack underflow");
      }

      const double rhs = stack.back();
      stack.pop_back();

      const double lhs = stack.back();
      stack.pop_back();

      switch (token.op) {
        case '+':
          stack.push_back(lhs + rhs);
          break;

        case '-':
          stack.push_back(lhs - rhs);
          break;

        case '*':
          stack.push_back(lhs * rhs);
          break;

        case '/':
          stack.push_back(lhs / rhs);
          break;

        default:
          throw std::runtime_error("Unknown expression operator");
      }
    }
  }

  // Final stack must contain exactly one value
  if (stack.size() != 1) {
    throw std::runtime_error("Expr evaluation error");
  }

  return stack.back();
}

}  // namespace

/* ============================================================
 * Expression Evaluation
 * ============================================================ */

/**
 * @brief Evaluate a symbolic mathematical expression.
 *
 * Uses ExprTk to evaluate expressions with variable
 * substitution support.
 *
 * Supported features:
 * - symbolic variables
 * - arithmetic operations
 * - built-in constants
 * - nested expressions
 *
 * Example:
 *   "theta / 2"
 *   "pi + lambda"
 *
 * The environment provides runtime values for
 * symbolic parameters.
 *
 * @param expr Expression string
 * @param env Variable environment
 *
 * @return Evaluated numeric result
 *
 * @throws std::runtime_error
 * Thrown if expression parsing fails.
 */
double RuleApplier::eval_expr(
    const std::string& expr,
    const std::unordered_map<std::string, double>& env) {
  static thread_local std::unordered_map<std::string, std::vector<ExprToken>>
      expr_cache;

  auto it = expr_cache.find(expr);

  if (it == expr_cache.end()) {
    it = expr_cache.emplace(expr, compile_expr(expr)).first;
  }

  return eval_compiled_expr(it->second, env);
}

/* ============================================================
 * Apply Single Rule
 * ============================================================ */

/**
 * @brief Apply a single decomposition rule.
 *
 * Converts:
 *   target gate
 *
 * Into:
 *   equivalent source gate sequence
 *
 * Performs:
 * - qubit remapping
 * - parameter substitution
 * - symbolic expression evaluation
 *
 * Example:
 *   RX(theta)
 *     ->
 *   RZ(theta/2) + X + RZ(theta/2)
 *
 * @param op Original operation
 * @param target Target gate pattern
 * @param sources Replacement gate sequence
 *
 * @return Expanded operation list
 *
 * @throws std::runtime_error
 * Thrown if:
 * - qubit counts mismatch
 * - parameter counts mismatch
 * - unknown qubit mapping appears
 */
RuleApplier::OpList RuleApplier::apply_one_rule(
    const BaseOperation& op, const ParamGate& target,
    const std::vector<ParamGate>& sources) {
  // ------------------------------------------------
  // Validate qubit count
  // ------------------------------------------------

  if (target.qubits.size() != op.targets.size()) {
    throw std::runtime_error("Qubit size mismatch");
  }

  // ------------------------------------------------
  // Validate parameter count
  // ------------------------------------------------

  if (target.params.size() != op.arg_value.size()) {
    throw std::runtime_error("Param size mismatch");
  }

  // ------------------------------------------------
  // Build qubit mapping
  // symbolic qubit -> physical qubit
  // ------------------------------------------------

  std::unordered_map<std::string, int> qubit_map;

  for (size_t i = 0; i < target.qubits.size(); ++i) {
    qubit_map[target.qubits[i]] = op.targets[i];
  }

  // ------------------------------------------------
  // Build parameter environment
  // symbolic parameter -> runtime value
  // ------------------------------------------------

  std::unordered_map<std::string, double> env;

  for (size_t i = 0; i < target.params.size(); ++i) {
    env[target.params[i]] = op.arg_value[i];
  }

  // Add mathematical constants
  env["pi"] = M_PI;
  env["e"] = M_E;

  OpList result;

  // ------------------------------------------------
  // Expand source gates
  // ------------------------------------------------

  for (const auto& src : sources) {
    // ---- Qubit remapping ----

    std::vector<int> qubits;

    for (const auto& q : src.qubits) {
      if (!qubit_map.count(q)) {
        throw std::runtime_error("Unknown qubit: " + q);
      }

      qubits.push_back(qubit_map[q]);
    }

    // ---- Parameter evaluation ----

    std::vector<double> params;

    for (const auto& p : src.params) {
      params.push_back(eval_expr(p, env));
    }

    // ---- Construct decomposed gate ----

    result.push_back(create_gate(src.name, qubits, params));
  }

  return result;
}


/* ============================================================
 * Recursive Path Expansion
 * ============================================================ */

/**
 * @brief Recursively apply decomposition rules.
 *
 * Expands all non-target gates into equivalent
 * target gate sequences.
 *
 * Features:
 * - recursive decomposition
 * - memoization cache
 * - automatic rule lookup
 *
 * Gates already inside the target gate set
 * remain unchanged.
 *
 * @param circuit Input quantum circuit
 * @param target Allowed target gate set
 * @param rule_dict Optimal decomposition rules
 *
 * @return Fully decomposed circuit
 *
 * @throws std::runtime_error
 * Thrown if a required decomposition rule
 * cannot be found.
 */
std::vector<std::shared_ptr<BaseOperation>> RuleApplier::apply_path(
    const std::vector<OpPtr>& circuit, const std::vector<std::string>& target,
    const std::unordered_map<std::string, EquivalenceRule>& rule_dict) {
  // ------------------------------------------------
  // Build target gate lookup set
  // ------------------------------------------------

  std::unordered_set<std::string> target_set(target.begin(), target.end());

  using OpVec = std::vector<std::shared_ptr<BaseOperation>>;

  // Memoization cache:
  // gate signature -> decomposed result
  std::unordered_map<std::string, OpVec> cache;

  // ------------------------------------------------
  // Generate shared gate signature
  // ------------------------------------------------

  auto make_signature = [](const BaseOperation& op) {
    std::ostringstream oss;

    oss << op.name << "|";

    for (auto t : op.targets) {
      oss << t << ",";
    }

    oss << "|";

    for (auto a : op.arg_value) {
      oss << a << ",";
    }

    return oss.str();
  };

  // ------------------------------------------------
  // Recursive decomposition function
  // ------------------------------------------------

  std::function<OpVec(const OpPtr&)> decompose =
      [&](const OpPtr& gate) -> OpVec {
    std::string sig = make_signature(*gate);

    // ---- Cache hit ----

    if (cache.count(sig)) {
      return cache[sig];
    }

    OpVec result;

    // ---- Already target gate ----

    if (target_set.count(gate->name)) {
      result.push_back(gate);

      cache[sig] = result;

      return result;
    }

    // ---- Missing decomposition rule ----

    if (!rule_dict.count(gate->name)) {
      std::vector<std::string> target_sorted(
          target_set.begin(), target_set.end());
      std::sort(target_sorted.begin(), target_sorted.end());
      std::ostringstream target_ss;
      for (size_t i = 0; i < target_sorted.size(); ++i) {
        if (i) target_ss << ", ";
        target_ss << target_sorted[i];
      }
      std::ostringstream msg;
      msg << "Cannot decompose gate '" << gate->name
          << "' into target basis [" << target_ss.str()
          << "]: no decomposition rule found";
      throw std::runtime_error(msg.str());
    }

    const auto& rule = rule_dict.at(gate->name);

    // ---- Apply decomposition rule ----

    auto expanded = apply_one_rule(*gate, rule.target, rule.sources);

    // ---- Recursively expand sub-gates ----

    for (const auto& op : expanded) {
      auto sub = decompose(op);

      for (auto& x : sub) {
        result.push_back(std::move(x));
      }
    }

    // ---- Store into cache ----

    cache[sig] = result;

    return result;
  };

  // ------------------------------------------------
  // Expand entire circuit
  // ------------------------------------------------

  OpVec final_result;

  for (const auto& gate : circuit) {
    auto part = decompose(gate);

    for (auto& op : part) {
      final_result.push_back(std::move(op));
    }
  }

  return final_result;
}

/* ============================================================
 * Table-driven Decomposition
 * ============================================================ */

/**
 * @brief Apply decomposition using a decomposition table.
 *
 * This is the final optimized implementation for
 * decomposition table driven expansion.
 *
 * Features:
 * - direct table lookup
 * - parameter substitution
 * - symbolic expression evaluation
 * - qubit remapping
 *
 * If no matching decomposition rule exists,
 * the original gate is preserved.
 *
 * @param circuit Input quantum circuit
 * @param table Decomposition lookup table
 *
 * @return Decomposed circuit
 */
RuleApplier::OpList RuleApplier::apply_with_decomposition_table(
    const std::vector<OpPtr>& circuit, const DecompositionTable& table) {
  OpList result;
  result.reserve(circuit.size());

  struct TableEntry {
    const ParamGate* target;
    const std::vector<ParamGate>* sources;
  };

  std::unordered_map<std::string, std::vector<TableEntry>> table_index;
  table_index.reserve(table.size());

  for (const auto& item : table) {
    table_index[item.first.name].push_back({&item.first, &item.second});
  }

  // ------------------------------------------------
  // Iterate through circuit operations
  // ------------------------------------------------

  for (const auto& op : circuit) {
    bool matched = false;

    auto candidates_it = table_index.find(op->name);

    if (candidates_it == table_index.end()) {
      result.push_back(op);
      continue;
    }

    // ------------------------------------------------
    // Search matching decomposition rule
    // ------------------------------------------------

    for (const auto& entry : candidates_it->second) {
      const auto& target = *entry.target;
      const auto& sources = *entry.sources;
      // ---- Qubit count mismatch ----

      if (target.qubits.size() != op->targets.size()) {
        continue;
      }

      // ---- Parameter count mismatch ----

      if (target.params.size() != op->arg_value.size()) {
        continue;
      }

      matched = true;

      // ------------------------------------------------
      // Build qubit mapping
      // ------------------------------------------------

      std::unordered_map<std::string, int> qubit_map;
      qubit_map.reserve(target.qubits.size());

      for (size_t i = 0; i < target.qubits.size(); ++i) {
        qubit_map[target.qubits[i]] = op->targets[i];
      }

      // ------------------------------------------------
      // Build parameter environment
      //
      // Important bug fix:
      // parameters must be evaluated using
      // runtime gate arguments.
      // ------------------------------------------------

      std::unordered_map<std::string, double> env;
      env.reserve(target.params.size() + 2);

      for (size_t i = 0; i < target.params.size(); ++i) {
        env[target.params[i]] = op->arg_value[i];
      }

      env["pi"] = M_PI;
      env["e"] = M_E;

      // ------------------------------------------------
      // Expand decomposed source gates
      // ------------------------------------------------

      for (const auto& g : sources) {
        // ---- Qubit remapping ----

        std::vector<int> qubits;
        qubits.reserve(g.qubits.size());

        for (const auto& q : g.qubits) {
          if (!qubit_map.count(q)) {
            throw std::runtime_error("Unknown qubit: " + q);
          }

          qubits.push_back(qubit_map[q]);
        }

        // ---- Parameter evaluation ----

        std::vector<double> params;
        params.reserve(g.params.size());

        for (const auto& p : g.params) {
          params.push_back(eval_expr(p, env));
        }

        // ---- Construct decomposed gate ----

        result.push_back(create_gate(g.name, qubits, params));
      }

      break;
    }

    // ------------------------------------------------
    // Preserve original gate if no rule matches
    // ------------------------------------------------

    if (!matched) {
      result.push_back(op);
    }
  }

  return result;
}

}  // namespace qcos
