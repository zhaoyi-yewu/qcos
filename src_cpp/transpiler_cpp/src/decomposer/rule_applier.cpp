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

#include <cmath>
#include <cctype>
#include <cstdlib>
#include <functional>
#include <stdexcept>
#include <sstream>
#include <unordered_set>

#include "decomposer/rule_applier.h"

namespace qcos {

namespace {

enum class ExprTokenKind {
  kNumber,
  kVariable,
  kOperator
};

struct ExprToken {
  ExprTokenKind kind;
  double value = 0.0;
  std::string text;
  char op = '\0';
};

int precedence(char op) {
  if (op == '~') {
    return 3;
  }
  return (op == '*' || op == '/') ? 2 : 1;
}

void push_operator(
    std::vector<ExprToken>& output,
    std::vector<char>& ops,
    char op) {
  while (!ops.empty() && ops.back() != '(' &&
         precedence(ops.back()) >= precedence(op)) {
    output.push_back({ExprTokenKind::kOperator, 0.0, {}, ops.back()});
    ops.pop_back();
  }
  ops.push_back(op);
}

std::vector<ExprToken> compile_expr(const std::string& expr) {
  std::vector<ExprToken> output;
  std::vector<char> ops;
  bool expect_operand = true;

  for (size_t i = 0; i < expr.size();) {
    const char c = expr[i];

    if (std::isspace(static_cast<unsigned char>(c))) {
      ++i;
      continue;
    }

    if (std::isdigit(static_cast<unsigned char>(c)) || c == '.') {
      char* end = nullptr;
      const double value = std::strtod(expr.c_str() + i, &end);
      output.push_back({ExprTokenKind::kNumber, value});
      i = static_cast<size_t>(end - expr.c_str());
      expect_operand = false;
      continue;
    }

    if (std::isalpha(static_cast<unsigned char>(c)) || c == '_') {
      size_t j = i + 1;
      while (j < expr.size() &&
             (std::isalnum(static_cast<unsigned char>(expr[j])) ||
              expr[j] == '_')) {
        ++j;
      }
      output.push_back({
          ExprTokenKind::kVariable,
          0.0,
          expr.substr(i, j - i)});
      i = j;
      expect_operand = false;
      continue;
    }

    if (c == '(') {
      ops.push_back(c);
      ++i;
      expect_operand = true;
      continue;
    }

    if (c == ')') {
      while (!ops.empty() && ops.back() != '(') {
        output.push_back({ExprTokenKind::kOperator, 0.0, {}, ops.back()});
        ops.pop_back();
      }
      if (ops.empty()) {
        throw std::runtime_error("Expr parse error: " + expr);
      }
      ops.pop_back();
      ++i;
      expect_operand = false;
      continue;
    }

    if (c == '+' || c == '-' || c == '*' || c == '/') {
      if (expect_operand) {
        if (c == '+') {
          ++i;
          continue;
        }
        if (c == '-') {
          ops.push_back('~');
          ++i;
          continue;
        } else {
          throw std::runtime_error("Expr parse error: " + expr);
        }
      }
      push_operator(output, ops, c);
      ++i;
      expect_operand = true;
      continue;
    }

    throw std::runtime_error("Expr parse error: " + expr);
  }

  while (!ops.empty()) {
    if (ops.back() == '(') {
      throw std::runtime_error("Expr parse error: " + expr);
    }
    output.push_back({ExprTokenKind::kOperator, 0.0, {}, ops.back()});
    ops.pop_back();
  }

  return output;
}

double eval_compiled_expr(
    const std::vector<ExprToken>& tokens,
    const std::unordered_map<std::string, double>& env) {
  std::vector<double> stack;
  stack.reserve(tokens.size());

  for (const auto& token : tokens) {
    if (token.kind == ExprTokenKind::kNumber) {
      stack.push_back(token.value);
    } else if (token.kind == ExprTokenKind::kVariable) {
      if (token.text == "pi") {
        stack.push_back(M_PI);
      } else if (token.text == "e") {
        stack.push_back(M_E);
      } else {
        auto it = env.find(token.text);
        if (it == env.end()) {
          throw std::runtime_error("Unknown parameter: " + token.text);
        }
        stack.push_back(it->second);
      }
    } else {
      if (token.op == '~') {
        if (stack.empty()) {
          throw std::runtime_error("Expr evaluation stack underflow");
        }
        stack.back() = -stack.back();
        continue;
      }

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

  static thread_local std::unordered_map<
      std::string,
      std::vector<ExprToken>> expr_cache;

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
    const BaseOperation& op,
    const ParamGate& target,
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
  env["e"]  = M_E;

  OpList result;

  // ------------------------------------------------
  // Expand source gates
  // ------------------------------------------------

  for (const auto& src : sources) {

    // ---- Qubit remapping ----

    std::vector<int> qubits;

    for (const auto& q : src.qubits) {

      if (!qubit_map.count(q)) {
        throw std::runtime_error(
            "Unknown qubit: " + q);
      }

      qubits.push_back(qubit_map[q]);
    }

    // ---- Parameter evaluation ----

    std::vector<double> params;

    for (const auto& p : src.params) {
      params.push_back(eval_expr(p, env));
    }

    // ---- Construct decomposed gate ----

    result.push_back(
        create_gate(src.name, qubits, params));
  }

  return result;
}

/* ============================================================
 * Clone Helper
 * ============================================================ */

/**
 * @brief Deep-copy a vector of operations.
 *
 * Uses BaseOperation::clone() to preserve
 * polymorphic operation types.
 *
 * @param src Source operation vector
 * @return Cloned operation vector
 */
static std::vector<std::unique_ptr<BaseOperation>>
clone_vector(
    const std::vector<
        std::unique_ptr<BaseOperation>>& src) {

  std::vector<std::unique_ptr<BaseOperation>> dst;

  for (const auto& op : src) {
    dst.push_back(op->clone());
  }

  return dst;
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
std::vector<std::unique_ptr<BaseOperation>>
RuleApplier::apply_path(
    const std::vector<OpPtr>& circuit,
    const std::vector<std::string>& target,
    const std::unordered_map<
        std::string,
        EquivalenceRule>& rule_dict) {

  // ------------------------------------------------
  // Build target gate lookup set
  // ------------------------------------------------

  std::unordered_set<std::string> target_set(
      target.begin(),
      target.end());

  using OpVec =
      std::vector<std::unique_ptr<BaseOperation>>;

  // Memoization cache:
  // gate signature -> decomposed result
  std::unordered_map<std::string, OpVec> cache;

  // ------------------------------------------------
  // Generate unique gate signature
  // ------------------------------------------------

  auto make_signature =
      [](const BaseOperation& op) {

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

  std::function<OpVec(const BaseOperation&)> decompose =
      [&](const BaseOperation& gate) -> OpVec {

    std::string sig = make_signature(gate);

    // ---- Cache hit ----

    if (cache.count(sig)) {
      return clone_vector(cache[sig]);
    }

    OpVec result;

    // ---- Already target gate ----

    if (target_set.count(gate.name)) {

      result.push_back(gate.clone());

      cache[sig] = clone_vector(result);

      return result;
    }

    // ---- Missing decomposition rule ----

    if (!rule_dict.count(gate.name)) {

      throw std::runtime_error(
          "No rule for gate: " + gate.name);
    }

    const auto& rule =
        rule_dict.at(gate.name);

    // ---- Apply decomposition rule ----

    auto expanded = apply_one_rule(
        gate,
        rule.target,
        rule.sources);

    // ---- Recursively expand sub-gates ----

    for (const auto& op : expanded) {

      auto sub = decompose(*op);

      for (auto& x : sub) {
        result.push_back(std::move(x));
      }
    }

    // ---- Store into cache ----

    cache[sig] = clone_vector(result);

    return result;
  };

  // ------------------------------------------------
  // Expand entire circuit
  // ------------------------------------------------

  OpVec final_result;

  for (const auto& gate : circuit) {

    auto part = decompose(*gate);

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
RuleApplier::OpList
RuleApplier::apply_with_decomposition_table(
    const std::vector<OpPtr>& circuit,
    const DecompositionTable& table) {

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
      result.push_back(op->clone());
      continue;
    }

    // ------------------------------------------------
    // Search matching decomposition rule
    // ------------------------------------------------

    for (const auto& entry : candidates_it->second) {
      const auto& target = *entry.target;
      const auto& sources = *entry.sources;
      // ---- Qubit count mismatch ----

      if (target.qubits.size() !=
          op->targets.size()) {
        continue;
      }

      // ---- Parameter count mismatch ----

      if (target.params.size() !=
          op->arg_value.size()) {
        continue;
      }

      matched = true;

      // ------------------------------------------------
      // Build qubit mapping
      // ------------------------------------------------

      std::unordered_map<std::string, int>
          qubit_map;
      qubit_map.reserve(target.qubits.size());

      for (size_t i = 0;
           i < target.qubits.size();
           ++i) {

        qubit_map[target.qubits[i]] =
            op->targets[i];
      }

      // ------------------------------------------------
      // Build parameter environment
      //
      // Important bug fix:
      // parameters must be evaluated using
      // runtime gate arguments.
      // ------------------------------------------------

      std::unordered_map<std::string, double>
          env;
      env.reserve(target.params.size() + 2);

      for (size_t i = 0;
           i < target.params.size();
           ++i) {

        env[target.params[i]] =
            op->arg_value[i];
      }

      env["pi"] = M_PI;
      env["e"]  = M_E;

      // ------------------------------------------------
      // Expand decomposed source gates
      // ------------------------------------------------

      for (const auto& g : sources) {

        // ---- Qubit remapping ----

        std::vector<int> qubits;
        qubits.reserve(g.qubits.size());

        for (const auto& q : g.qubits) {

          if (!qubit_map.count(q)) {

            throw std::runtime_error(
                "Unknown qubit: " + q);
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

        result.push_back(
            create_gate(g.name, qubits, params));
      }

      break;
    }

    // ------------------------------------------------
    // Preserve original gate if no rule matches
    // ------------------------------------------------

    if (!matched) {
      result.push_back(op->clone());
    }
  }

  return result;
}

} // namespace qcos
